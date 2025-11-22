"""
内存管理模块
提供内存监控、自动清理、内存泄漏检测等功能
"""
import asyncio
import gc
import logging
import os
import psutil
import resource
import sys
import threading
import time
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """内存统计信息"""
    rss_mb: float  # 物理内存 (MB)
    vms_mb: float  # 虚拟内存 (MB)
    percent: float  # 内存使用百分比
    available_mb: float  # 可用内存 (MB)
    gc_counts: tuple  # 垃圾回收统计
    object_count: int  # 对象总数
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemoryThresholds:
    """内存阈值配置"""
    warning_percent: float = 70.0  # 警告阈值
    critical_percent: float = 85.0  # 严重阈值
    max_objects: int = 1000000  # 最大对象数
    gc_frequency: int = 100  # 垃圾回收频率
    cleanup_interval: int = 60  # 清理间隔（秒）


class ObjectTracker:
    """对象跟踪器"""

    def __init__(self):
        self._objects: Dict[type, Set[int]] = defaultdict(set)
        self._object_refs: Dict[int, weakref.ref] = {}
        self._lock = threading.Lock()
        self._enabled = False

    def enable(self):
        """启用对象跟踪"""
        self._enabled = True

    def disable(self):
        """禁用对象跟踪"""
        self._enabled = False

    def track_object(self, obj: Any):
        """跟踪对象"""
        if not self._enabled:
            return

        obj_id = id(obj)
        obj_type = type(obj)

        with self._lock:
            self._objects[obj_type].add(obj_id)
            self._object_refs[obj_id] = weakref.ref(obj, self._object_deleted)

    def _object_deleted(self, weak_ref):
        """对象删除回调"""
        obj_id = id(weak_ref)
        with self._lock:
            # 找到并删除对象记录
            for obj_type, obj_ids in self._objects.items():
                if obj_id in obj_ids:
                    obj_ids.remove(obj_id)
                    break

            self._object_refs.pop(obj_id, None)

    def get_object_counts(self) -> Dict[str, int]:
        """获取对象计数"""
        with self._lock:
            return {obj_type.__name__: len(obj_ids)
                   for obj_type, obj_ids in self._objects.items()}

    def get_total_object_count(self) -> int:
        """获取对象总数"""
        with self._lock:
            return sum(len(obj_ids) for obj_ids in self._objects.values())

    def clear_tracking(self):
        """清理跟踪数据"""
        with self._lock:
            self._objects.clear()
            self._object_refs.clear()


class MemoryManager:
    """内存管理器"""

    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        self.thresholds = thresholds or MemoryThresholds()
        self.process = psutil.Process()
        self.object_tracker = ObjectTracker()
        self._memory_history: List[MemoryStats] = []
        self._max_history_size = 1000
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_callbacks: List[Callable] = []
        self._lock = asyncio.Lock()

        # 设置垃圾回收阈值
        gc.set_threshold(self.thresholds.gc_frequency, 10, 10)

    def get_memory_stats(self) -> MemoryStats:
        """获取当前内存统计"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        memory_available = psutil.virtual_memory().available

        return MemoryStats(
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            available_mb=memory_available / 1024 / 1024,
            gc_counts=gc.get_count(),
            object_count=len(gc.get_objects())
        )

    async def start_monitoring(self, interval: int = 30):
        """启动内存监控"""
        if self._monitoring:
            logger.warning("内存监控已在运行")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("内存监控已启动")

    async def stop_monitoring(self):
        """停止内存监控"""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("内存监控已停止")

    async def _monitor_loop(self, interval: int):
        """监控循环"""
        while self._monitoring:
            try:
                stats = self.get_memory_stats()
                await self._record_memory_stats(stats)

                # 检查内存阈值
                await self._check_memory_thresholds(stats)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"内存监控错误: {e}")
                await asyncio.sleep(interval)

    async def _record_memory_stats(self, stats: MemoryStats):
        """记录内存统计"""
        async with self._lock:
            self._memory_history.append(stats)

            # 限制历史记录大小
            if len(self._memory_history) > self._max_history_size:
                self._memory_history = self._memory_history[-self._max_history_size:]

    async def _check_memory_thresholds(self, stats: MemoryStats):
        """检查内存阈值"""
        if stats.percent >= self.thresholds.critical_percent:
            logger.critical(
                f"内存使用严重! {stats.percent:.1f}% (>={self.thresholds.critical_percent}%)"
            )
            await self.emergency_cleanup()
        elif stats.percent >= self.thresholds.warning_percent:
            logger.warning(
                f"内存使用较高! {stats.percent:.1f}% (>={self.thresholds.warning_percent}%)"
            )
            await self.garbage_collect()

        # 检查对象数量
        if stats.object_count >= self.thresholds.max_objects:
            logger.warning(
                f"对象数量过多! {stats.object_count} (>={self.thresholds.max_objects})"
            )
            await self.garbage_collect()

    async def emergency_cleanup(self):
        """紧急清理"""
        logger.info("执行紧急内存清理...")

        # 强制垃圾回收
        collected = await self.garbage_collect()

        # 调用清理回调
        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"清理回调执行失败: {e}")

        # 清理内存历史
        async with self._lock:
            self._memory_history = self._memory_history[-100:]

        logger.info(f"紧急清理完成，回收了 {collected} 个对象")

    async def garbage_collect(self) -> int:
        """执行垃圾回收"""
        # 执行多代垃圾回收
        collected_objects = 0
        for generation in range(3):
            collected = gc.collect()
            collected_objects += collected

        if collected_objects > 0:
            logger.info(f"垃圾回收完成，回收了 {collected_objects} 个对象")

        return collected_objects

    def add_cleanup_callback(self, callback: Callable):
        """添加清理回调"""
        self._cleanup_callbacks.append(callback)

    def remove_cleanup_callback(self, callback: Callable):
        """移除清理回调"""
        if callback in self._cleanup_callbacks:
            self._cleanup_callbacks.remove(callback)

    def get_memory_history(self, limit: int = 100) -> List[MemoryStats]:
        """获取内存历史记录"""
        return self._memory_history[-limit:]

    def get_memory_trend(self, minutes: int = 30) -> Dict[str, Any]:
        """获取内存使用趋势"""
        cutoff_time = time.time() - (minutes * 60)
        recent_stats = [
            stats for stats in self._memory_history
            if stats.timestamp >= cutoff_time
        ]

        if len(recent_stats) < 2:
            return {"trend": "insufficient_data"}

        # 计算趋势
        start_memory = recent_stats[0].rss_mb
        end_memory = recent_stats[-1].rss_mb
        memory_change = end_memory - start_memory
        memory_change_rate = memory_change / minutes  # MB per minute

        if memory_change_rate > 1.0:
            trend = "increasing"
        elif memory_change_rate < -1.0:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "memory_change_mb": memory_change,
            "memory_change_rate_mb_per_min": memory_change_rate,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "data_points": len(recent_stats)
        }

    async def optimize_memory(self):
        """内存优化"""
        logger.info("开始内存优化...")

        # 1. 垃圾回收
        collected = await self.garbage_collect()

        # 2. 清理对象跟踪数据
        self.object_tracker.clear_tracking()

        # 3. 压缩内存历史
        async with self._lock:
            if len(self._memory_history) > 100:
                # 保留最近的数据，中间的数据采样
                recent = self._memory_history[-50:]
                older = self._memory_history[:-50]
                sampled = older[::max(1, len(older) // 50)]
                self._memory_history = sampled + recent

        # 4. 调用垃圾回收器优化
        gc.set_debug(gc.DEBUG_STATS)

        logger.info(f"内存优化完成，回收了 {collected} 个对象")

    def get_system_memory_info(self) -> Dict[str, Any]:
        """获取系统内存信息"""
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()

        return {
            "total_mb": virtual_memory.total / 1024 / 1024,
            "available_mb": virtual_memory.available / 1024 / 1024,
            "used_mb": virtual_memory.used / 1024 / 1024,
            "percent": virtual_memory.percent,
            "swap_total_mb": swap_memory.total / 1024 / 1024,
            "swap_used_mb": swap_memory.used / 1024 / 1024,
            "swap_percent": swap_memory.percent
        }

    def enable_object_tracking(self):
        """启用对象跟踪"""
        self.object_tracker.enable()

    def disable_object_tracking(self):
        """禁用对象跟踪"""
        self.object_tracker.disable()

    def get_object_stats(self) -> Dict[str, Any]:
        """获取对象统计"""
        return {
            "total_objects": self.object_tracker.get_total_object_count(),
            "object_counts": self.object_tracker.get_object_counts()
        }


class MemoryProfiler:
    """内存分析器"""

    def __init__(self):
        self.snapshots: List[Dict[str, Any]] = []

    def take_snapshot(self, label: str = ""):
        """拍取内存快照"""
        import tracemalloc

        if not tracemalloc.is_tracing():
            tracemalloc.start()

        current, peak = tracemalloc.get_traced_memory()
        snapshot = {
            "label": label,
            "timestamp": time.time(),
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024
        }

        self.snapshots.append(snapshot)
        return snapshot

    def get_memory_diff(self, snapshot1: int, snapshot2: int) -> Dict[str, Any]:
        """获取两个快照之间的内存差异"""
        if snapshot1 >= len(self.snapshots) or snapshot2 >= len(self.snapshots):
            raise ValueError("快照索引超出范围")

        snap1 = self.snapshots[snapshot1]
        snap2 = self.snapshots[snapshot2]

        return {
            "time_diff": snap2["timestamp"] - snap1["timestamp"],
            "current_diff_mb": snap2["current_mb"] - snap1["current_mb"],
            "peak_diff_mb": snap2["peak_mb"] - snap1["peak_mb"]
        }

    def clear_snapshots(self):
        """清理快照"""
        self.snapshots.clear()


# 装饰器
def memory_monitor(func: Callable) -> Callable:
    """内存监控装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        manager = get_memory_manager()
        start_stats = manager.get_memory_stats()

        try:
            result = await func(*args, **kwargs)

            end_stats = manager.get_memory_stats()
            memory_diff = end_stats.rss_mb - start_stats.rss_mb

            if memory_diff > 10:  # 如果内存增长超过10MB
                logger.warning(
                    f"函数 {func.__name__} 内存增长: {memory_diff:.2f}MB"
                )

            return result

        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            # 执行清理
            await manager.garbage_collect()
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        manager = get_memory_manager()
        start_stats = manager.get_memory_stats()

        try:
            result = func(*args, **kwargs)

            end_stats = manager.get_memory_stats()
            memory_diff = end_stats.rss_mb - start_stats.rss_mb

            if memory_diff > 10:
                logger.warning(
                    f"函数 {func.__name__} 内存增长: {memory_diff:.2f}MB"
                )

            return result

        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            # 同步垃圾回收
            gc.collect()
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def memory_limit(max_memory_mb: float):
    """内存限制装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_memory_manager()

            # 检查当前内存使用
            stats = manager.get_memory_stats()
            if stats.rss_mb > max_memory_mb:
                logger.warning(f"当前内存使用 {stats.rss_mb:.2f}MB 超过限制 {max_memory_mb}MB")
                await manager.emergency_cleanup()

            result = await func(*args, **kwargs)

            # 再次检查
            final_stats = manager.get_memory_stats()
            if final_stats.rss_mb > max_memory_mb:
                logger.error(f"函数执行后内存使用 {final_stats.rss_mb:.2f}MB 超过限制")
                await manager.emergency_cleanup()

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_memory_manager()

            stats = manager.get_memory_stats()
            if stats.rss_mb > max_memory_mb:
                logger.warning(f"当前内存使用 {stats.rss_mb:.2f}MB 超过限制 {max_memory_mb}MB")
                # 同步清理
                gc.collect()

            result = func(*args, **kwargs)

            final_stats = manager.get_memory_stats()
            if final_stats.rss_mb > max_memory_mb:
                logger.error(f"函数执行后内存使用 {final_stats.rss_mb:.2f}MB 超过限制")
                gc.collect()

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 全局内存管理器实例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(thresholds: Optional[MemoryThresholds] = None) -> MemoryManager:
    """获取全局内存管理器"""
    global _memory_manager

    if _memory_manager is None:
        _memory_manager = MemoryManager(thresholds)

    return _memory_manager


async def initialize_memory_monitoring(start_monitoring: bool = True):
    """初始化内存监控"""
    manager = get_memory_manager()

    if start_monitoring:
        await manager.start_monitoring()

    logger.info("内存管理器已初始化")


async def shutdown_memory_manager():
    """关闭内存管理器"""
    manager = get_memory_manager()
    await manager.stop_monitoring()
    await manager.optimize_memory()


# 内存泄漏检测
class MemoryLeakDetector:
    """内存泄漏检测器"""

    def __init__(self):
        self.baseline_stats: Optional[MemoryStats] = None
        self.manager = get_memory_manager()

    async def start_detection(self):
        """开始泄漏检测"""
        self.baseline_stats = self.manager.get_memory_stats()
        logger.info("内存泄漏检测已开始")

    async def check_leak(self, threshold_mb: float = 50.0) -> Dict[str, Any]:
        """检查内存泄漏"""
        if self.baseline_stats is None:
            raise RuntimeError("请先调用 start_detection()")

        current_stats = self.manager.get_memory_stats()
        memory_increase = current_stats.rss_mb - self.baseline_stats.rss_mb
        object_increase = current_stats.object_count - self.baseline_stats.object_count

        is_leak = memory_increase > threshold_mb

        return {
            "is_leak": is_leak,
            "memory_increase_mb": memory_increase,
            "object_increase": object_increase,
            "threshold_mb": threshold_mb,
            "current_memory_mb": current_stats.rss_mb,
            "baseline_memory_mb": self.baseline_stats.rss_mb
        }