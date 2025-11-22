"""
性能管理器 - 集成所有性能优化模块
提供统一的性能管理接口和自动化优化功能
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable, Union
from pathlib import Path

from .concurrency import (
    ConcurrencyController, ConcurrencyConfig, get_concurrency_controller,
    close_concurrency_controller
)
from .cache import (
    MultiLevelCache, CacheConfig, get_cache_manager, close_cache_manager
)
from .database_optimizer import (
    DatabaseOptimizer, get_database_optimizer
)
from .memory_manager import (
    MemoryManager, MemoryThresholds, get_memory_manager,
    initialize_memory_monitoring, shutdown_memory_manager
)
from .performance_monitor import (
    PerformanceMonitor, get_performance_monitor,
    initialize_performance_monitoring, shutdown_performance_monitor
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceConfig:
    """性能配置"""
    # 并发配置
    concurrency_config: ConcurrencyConfig = None

    # 缓存配置
    cache_config: CacheConfig = None

    # 内存配置
    memory_thresholds: MemoryThresholds = None

    # 监控配置
    monitoring_enabled: bool = True
    monitoring_interval: int = 30
    auto_optimization: bool = True
    optimization_interval: int = 300  # 5分钟

    # 告警配置
    alert_enabled: bool = True
    slow_request_threshold: float = 2.0
    high_memory_threshold: float = 80.0
    high_cpu_threshold: float = 80.0

    def __post_init__(self):
        if self.concurrency_config is None:
            self.concurrency_config = ConcurrencyConfig()
        if self.cache_config is None:
            self.cache_config = CacheConfig()
        if self.memory_thresholds is None:
            self.memory_thresholds = MemoryThresholds()


class PerformanceManager:
    """性能管理器主类"""

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self.is_initialized = False
        self.is_running = False

        # 子管理器
        self.concurrency_controller: Optional[ConcurrencyController] = None
        self.cache_manager: Optional[MultiLevelCache] = None
        self.database_optimizer: Optional[DatabaseOptimizer] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None

        # 优化任务
        self._optimization_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """初始化性能管理器"""
        if self.is_initialized:
            logger.warning("性能管理器已初始化")
            return

        logger.info("开始初始化性能管理器...")

        try:
            # 1. 初始化并发控制
            self.concurrency_controller = get_concurrency_controller(self.config.concurrency_config)

            # 2. 初始化缓存管理
            self.cache_manager = get_cache_manager(self.config.cache_config)

            # 3. 初始化数据库优化器
            self.database_optimizer = get_database_optimizer()

            # 4. 初始化内存管理器
            self.memory_manager = get_memory_manager(self.config.memory_thresholds)
            await initialize_memory_monitoring(start_monitoring=self.config.monitoring_enabled)

            # 5. 初始化性能监控
            if self.config.monitoring_enabled:
                self.performance_monitor = get_performance_monitor()
                await initialize_performance_monitoring()

                # 设置告警回调
                if self.config.alert_enabled:
                    self._setup_alerts()

            # 6. 启动自动优化
            if self.config.auto_optimization:
                await self.start_auto_optimization()

            self.is_initialized = True
            logger.info("性能管理器初始化完成")

        except Exception as e:
            logger.error(f"性能管理器初始化失败: {e}")
            raise

    def _setup_alerts(self):
        """设置告警"""
        if self.performance_monitor:
            self.performance_monitor.add_alert_callback(self._handle_alert)

    def _handle_alert(self, alert: Dict[str, Any]):
        """处理告警"""
        alert_type = alert.get("type")
        severity = alert.get("severity")
        message = alert.get("message")

        if severity == "critical":
            logger.critical(f"性能告警: {message}")
        elif severity == "warning":
            logger.warning(f"性能警告: {message}")
        else:
            logger.info(f"性能信息: {message}")

        # 自动处理某些告警
        if alert_type == "high_memory":
            asyncio.create_task(self._handle_high_memory_alert())
        elif alert_type == "slow_response":
            asyncio.create_task(self._handle_slow_response_alert(alert))

    async def _handle_high_memory_alert(self):
        """处理高内存告警"""
        if self.memory_manager:
            await self.memory_manager.emergency_cleanup()
            logger.info("已执行紧急内存清理")

    async def _handle_slow_response_alert(self, alert: Dict[str, Any]):
        """处理慢响应告警"""
        # 可以在这里实现自动优化策略
        logger.info("检测到慢响应，建议检查数据库查询和缓存策略")

    async def start_auto_optimization(self):
        """启动自动优化"""
        if self._optimization_task:
            return

        self._optimization_task = asyncio.create_task(self._auto_optimization_loop())
        logger.info("自动优化已启动")

    async def stop_auto_optimization(self):
        """停止自动优化"""
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            self._optimization_task = None
            logger.info("自动优化已停止")

    async def _auto_optimization_loop(self):
        """自动优化循环"""
        while True:
            try:
                await asyncio.sleep(self.config.optimization_interval)
                await self.perform_auto_optimization()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动优化失败: {e}")

    async def perform_auto_optimization(self):
        """执行自动优化"""
        logger.info("开始自动性能优化...")

        optimization_results = {
            "timestamp": time.time(),
            "optimizations": []
        }

        try:
            # 1. 内存优化
            if self.memory_manager:
                await self.memory_manager.optimize_memory()
                optimization_results["optimizations"].append("内存优化完成")

            # 2. 数据库优化分析
            if self.database_optimizer:
                db_analysis = await self.database_optimizer.analyze_performance()
                optimization_results["database_analysis"] = db_analysis

            # 3. 缓存统计检查
            if self.cache_manager:
                cache_stats = self.cache_manager.get_stats()
                optimization_results["cache_stats"] = cache_stats

            # 4. 并发控制调整建议
            if self.concurrency_controller:
                concurrency_stats = self.concurrency_controller.get_stats()
                optimization_results["concurrency_stats"] = concurrency_stats

                # 动态调整并发参数
                await self._adjust_concurrency_if_needed(concurrency_stats)

            logger.info("自动性能优化完成")
            return optimization_results

        except Exception as e:
            logger.error(f"自动优化失败: {e}")
            optimization_results["error"] = str(e)
            return optimization_results

    async def _adjust_concurrency_if_needed(self, stats: Dict[str, Any]):
        """根据统计信息调整并发参数"""
        cpu_percent = stats.get("cpu_percent", 0)
        active_requests = stats.get("active_requests", 0)
        max_concurrent = stats.get("config", {}).get("max_concurrent_requests", 100)

        # 如果CPU使用率过高，降低并发数
        if cpu_percent > self.config.high_cpu_threshold:
            new_concurrent = max(max_concurrent // 2, 10)
            self.concurrency_controller.adjust_concurrency(new_concurrent)
            logger.info(f"CPU使用率过高({cpu_percent:.1f}%)，降低并发数至 {new_concurrent}")

        # 如果CPU使用率很低且队列积压，可以增加并发数
        elif cpu_percent < 50 and active_requests >= max_concurrent * 0.9:
            new_concurrent = min(max_concurrent * 2, 200)
            self.concurrency_controller.adjust_concurrency(new_concurrent)
            logger.info(f"资源充足，增加并发数至 {new_concurrent}")

    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取全面的性能统计"""
        stats = {
            "timestamp": time.time(),
            "manager_initialized": self.is_initialized,
            "auto_optimization": self.config.auto_optimization
        }

        try:
            # 并发控制统计
            if self.concurrency_controller:
                stats["concurrency"] = self.concurrency_controller.get_stats()

            # 缓存统计
            if self.cache_manager:
                stats["cache"] = self.cache_manager.get_stats()

            # 数据库统计
            if self.database_optimizer:
                stats["database"] = await self.database_optimizer.analyze_performance()

            # 内存统计
            if self.memory_manager:
                memory_stats = self.memory_manager.get_memory_stats()
                stats["memory"] = {
                    "rss_mb": memory_stats.rss_mb,
                    "percent": memory_stats.percent,
                    "object_count": memory_stats.object_count,
                    "gc_counts": memory_stats.gc_counts
                }
                stats["memory_trend"] = self.memory_manager.get_memory_trend()

            # 系统统计
            if self.memory_manager:
                stats["system"] = self.memory_manager.get_system_memory_info()

            # 性能监控统计
            if self.performance_monitor:
                stats["performance"] = self.performance_monitor.get_performance_report()
                stats["metrics_summary"] = self.performance_monitor.get_metrics_summary()

        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            stats["error"] = str(e)

        return stats

    async def execute_optimized_task(
        self,
        func: Callable,
        *args,
        use_cache: bool = True,
        cache_key: Optional[str] = None,
        cache_ttl: int = 300,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """执行优化任务"""
        # 生成缓存键
        if use_cache and self.cache_manager:
            if not cache_key:
                import hashlib
                content = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = f"task:{hashlib.md5(content.encode()).hexdigest()}"

            # 尝试从缓存获取结果
            if cache_key:
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"任务命中缓存: {func.__name__}")
                    return cached_result

        # 执行任务
        if self.concurrency_controller:
            result = await self.concurrency_controller.submit_task(
                func, *args, timeout=timeout, **kwargs
            )
        else:
            # 直接执行
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

        # 缓存结果
        if use_cache and self.cache_manager and cache_key:
            await self.cache_manager.set(cache_key, result, cache_ttl)

        return result

    async def cleanup_resources(self):
        """清理资源"""
        logger.info("开始清理性能管理器资源...")

        try:
            # 停止自动优化
            await self.stop_auto_optimization()

            # 关闭性能监控
            if self.performance_monitor:
                await shutdown_performance_monitor()

            # 关闭内存管理
            if self.memory_manager:
                await shutdown_memory_manager()

            # 关闭缓存管理
            if self.cache_manager:
                await close_cache_manager()

            # 关闭并发控制
            if self.concurrency_controller:
                close_concurrency_controller()

            self.is_initialized = False
            logger.info("性能管理器资源清理完成")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")

    async def export_performance_report(
        self,
        filepath: Union[str, Path],
        include_recommendations: bool = True
    ):
        """导出性能报告"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 收集所有统计数据
        stats = await self.get_comprehensive_stats()

        # 生成建议
        if include_recommendations:
            stats["recommendations"] = await self._generate_recommendations(stats)

        # 导出为JSON
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"性能报告已导出到: {filepath}")

    async def _generate_recommendations(self, stats: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成性能优化建议"""
        recommendations = []

        try:
            # 内存建议
            if "memory" in stats:
                memory_percent = stats["memory"]["percent"]
                if memory_percent > self.config.high_memory_threshold:
                    recommendations.append({
                        "category": "内存",
                        "priority": "高",
                        "recommendation": f"内存使用率过高({memory_percent:.1f}%)，建议增加内存或优化内存使用"
                    })

            # CPU建议
            if "concurrency" in stats:
                cpu_percent = stats["concurrency"]["cpu_percent"]
                if cpu_percent > self.config.high_cpu_threshold:
                    recommendations.append({
                        "category": "CPU",
                        "priority": "高",
                        "recommendation": f"CPU使用率过高({cpu_percent:.1f}%)，建议降低并发数或优化算法"
                    })

            # 缓存建议
            if "cache" in stats:
                cache_backends = stats["cache"].get("backends", [])
                for backend in cache_backends:
                    hit_rate = backend["stats"].get("hit_rate", 0)
                    if hit_rate < 0.5:
                        recommendations.append({
                            "category": "缓存",
                            "priority": "中",
                            "recommendation": f"{backend['name']} 缓存命中率过低({hit_rate:.1%})，建议调整缓存策略"
                        })

            # 数据库建议
            if "database" in stats:
                db_stats = stats["database"].get("query_stats", {})
                avg_execution_time = db_stats.get("avg_execution_time", 0)
                if avg_execution_time > 1.0:
                    recommendations.append({
                        "category": "数据库",
                        "priority": "高",
                        "recommendation": f"数据库查询平均响应时间过长({avg_execution_time:.3f}s)，建议优化查询"
                    })

        except Exception as e:
            logger.error(f"生成建议失败: {e}")

        return recommendations


# 全局性能管理器实例
_performance_manager: Optional[PerformanceManager] = None


def get_performance_manager(config: Optional[PerformanceConfig] = None) -> PerformanceManager:
    """获取全局性能管理器"""
    global _performance_manager

    if _performance_manager is None:
        _performance_manager = PerformanceManager(config)

    return _performance_manager


async def initialize_performance_system(config: Optional[PerformanceConfig] = None):
    """初始化性能系统"""
    manager = get_performance_manager(config)
    await manager.initialize()
    logger.info("性能系统初始化完成")


async def shutdown_performance_system():
    """关闭性能系统"""
    manager = get_performance_manager()
    await manager.cleanup_resources()
    logger.info("性能系统已关闭")


# 便捷装饰器
def optimized_execution(
    use_cache: bool = True,
    cache_ttl: int = 300,
    timeout: Optional[float] = None
):
    """优化执行装饰器"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            manager = get_performance_manager()
            return await manager.execute_optimized_task(
                func, *args,
                use_cache=use_cache,
                cache_ttl=cache_ttl,
                timeout=timeout,
                **kwargs
            )

        if asyncio.iscoroutinefunction(func):
            return wrapper
        else:
            # 同步函数转为异步执行
            async def async_wrapper(*args, **kwargs):
                return await wrapper(*args, **kwargs)
            return async_wrapper

    return decorator