"""
性能监控模块
提供全面的性能监控、指标收集和报告功能
"""
import asyncio
import json
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Union
from pathlib import Path
import psutil
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    unit: str
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestMetrics:
    """请求指标"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    timestamp: float
    request_size: int = 0
    response_size: int = 0
    user_agent: str = ""
    ip_address: str = ""


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io_sent: int
    network_io_recv: int
    process_count: int
    timestamp: float


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_metrics: int = 10000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict] = None):
        """记录计数器"""
        with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value

    def record_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """记录仪表盘指标"""
        with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value

    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """记录直方图"""
        with self._lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)
            # 限制直方图大小
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    def record_metric(self, metric: PerformanceMetric):
        """记录通用指标"""
        with self._lock:
            self.metrics[metric.name].append(metric)

    def _make_key(self, name: str, tags: Optional[Dict] = None) -> str:
        """生成指标键"""
        if not tags:
            return name

        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def get_counter(self, name: str, tags: Optional[Dict] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, tags)
        with self._lock:
            return self.counters.get(key, 0.0)

    def get_gauge(self, name: str, tags: Optional[Dict] = None) -> float:
        """获取仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            return self.gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, tags: Optional[Dict] = None) -> Dict[str, float]:
        """获取直方图统计"""
        key = self._make_key(name, tags)
        with self._lock:
            values = self.histograms.get(key, [])
            if not values:
                return {}

            return {
                "count": len(values),
                "sum": sum(values),
                "min": min(values),
                "max": max(values),
                "mean": np.mean(values),
                "median": np.median(values),
                "p95": np.percentile(values, 95),
                "p99": np.percentile(values, 99)
            }

    def get_metric_history(
        self,
        name: str,
        since: Optional[float] = None,
        limit: int = 100
    ) -> List[PerformanceMetric]:
        """获取指标历史"""
        with self._lock:
            history = list(self.metrics.get(name, []))

        if since:
            history = [m for m in history if m.timestamp >= since]

        return history[-limit:]

    def reset_metrics(self):
        """重置所有指标"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.metrics.clear()


class SystemMonitor:
    """系统监控器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, interval: int = 30):
        """启动系统监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("系统监控已启动")

    async def stop_monitoring(self):
        """停止系统监控"""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("系统监控已停止")

    async def _monitor_loop(self, interval: int):
        """监控循环"""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"系统监控错误: {e}")
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        timestamp = time.time()

        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=1)
        self.collector.record_gauge("system_cpu_percent", cpu_percent)

        # 内存指标
        memory = psutil.virtual_memory()
        self.collector.record_gauge("system_memory_percent", memory.percent)
        self.collector.record_gauge("system_memory_available_mb", memory.available / 1024 / 1024)

        # 磁盘指标
        disk = psutil.disk_usage('/')
        self.collector.record_gauge("system_disk_percent", disk.percent)
        self.collector.record_gauge("system_disk_free_gb", disk.free / 1024 / 1024 / 1024)

        # 网络指标
        network = psutil.net_io_counters()
        self.collector.record_counter("system_network_sent_bytes", network.bytes_sent)
        self.collector.record_counter("system_network_recv_bytes", network.bytes_recv)

        # 进程指标
        process_memory = self.process.memory_info()
        self.collector.record_gauge("process_memory_rss_mb", process_memory.rss / 1024 / 1024)
        self.collector.record_gauge("process_memory_vms_mb", process_memory.vms / 1024 / 1024)
        self.collector.record_gauge("process_cpu_percent", self.process.cpu_percent())

        # 文件描述符
        try:
            num_fds = self.process.num_fds()
            self.collector.record_gauge("process_fd_count", num_fds)
        except (AttributeError, psutil.AccessDenied):
            pass

        # 线程数
        num_threads = self.process.num_threads()
        self.collector.record_gauge("process_thread_count", num_threads)


class RequestMonitor:
    """请求监控器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.requests: List[RequestMetrics] = []
        self._max_requests = 10000
        self._lock = threading.Lock()

    def record_request(self, metrics: RequestMetrics):
        """记录请求指标"""
        with self._lock:
            self.requests.append(metrics)

            # 限制列表大小
            if len(self.requests) > self._max_requests:
                self.requests = self.requests[-self._max_requests:]

        # 记录到指标收集器
        self.collector.record_histogram(
            "request_response_time",
            metrics.response_time,
            tags={"endpoint": metrics.endpoint, "method": metrics.method}
        )

        self.collector.record_counter(
            "request_count",
            tags={"endpoint": metrics.endpoint, "method": metrics.method, "status": str(metrics.status_code)}
        )

        self.collector.record_histogram(
            "request_size",
            metrics.request_size,
            tags={"endpoint": metrics.endpoint, "method": metrics.method}
        )

        self.collector.record_histogram(
            "response_size",
            metrics.response_size,
            tags={"endpoint": metrics.endpoint, "method": metrics.method}
        )

    def get_request_stats(
        self,
        endpoint: Optional[str] = None,
        minutes: int = 5
    ) -> Dict[str, Any]:
        """获取请求统计"""
        cutoff_time = time.time() - (minutes * 60)

        with self._lock:
            recent_requests = [
                req for req in self.requests
                if req.timestamp >= cutoff_time and (endpoint is None or req.endpoint == endpoint)
            ]

        if not recent_requests:
            return {}

        response_times = [req.response_time for req in recent_requests]
        status_codes = defaultdict(int)
        for req in recent_requests:
            status_codes[req.status_code] += 1

        return {
            "total_requests": len(recent_requests),
            "requests_per_minute": len(recent_requests) / minutes,
            "avg_response_time": np.mean(response_times),
            "p95_response_time": np.percentile(response_times, 95),
            "p99_response_time": np.percentile(response_times, 99),
            "status_codes": dict(status_codes),
            "success_rate": sum(1 for req in recent_requests if 200 <= req.status_code < 400) / len(recent_requests)
        }

    def get_slow_requests(
        self,
        threshold: float = 1.0,
        limit: int = 10
    ) -> List[RequestMetrics]:
        """获取慢请求"""
        with self._lock:
            slow_requests = [
                req for req in self.requests
                if req.response_time >= threshold
            ]

        return sorted(slow_requests, key=lambda x: x.response_time, reverse=True)[:limit]


class PerformanceMonitor:
    """性能监控器主类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.collector = MetricsCollector(max_metrics=self.config.get("max_metrics", 10000))
        self.system_monitor = SystemMonitor(self.collector)
        self.request_monitor = RequestMonitor(self.collector)
        self._monitoring = False
        self._alerts: List[Dict] = []
        self._alert_callbacks: List[Callable] = []

    async def start_monitoring(self, system_interval: int = 30):
        """启动性能监控"""
        if self._monitoring:
            logger.warning("性能监控已在运行")
            return

        self._monitoring = True
        await self.system_monitor.start_monitoring(system_interval)
        logger.info("性能监控已启动")

    async def stop_monitoring(self):
        """停止性能监控"""
        if not self._monitoring:
            return

        self._monitoring = False
        await self.system_monitor.stop_monitoring()
        logger.info("性能监控已停止")

    async def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time: float,
        request_size: int = 0,
        response_size: int = 0,
        user_agent: str = "",
        ip_address: str = ""
    ):
        """记录请求指标"""
        metrics = RequestMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            timestamp=time.time(),
            request_size=request_size,
            response_size=response_size,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.request_monitor.record_request(metrics)

        # 检查告警
        await self._check_alerts(metrics)

    async def _check_alerts(self, request_metrics: RequestMetrics):
        """检查告警条件"""
        alerts = []

        # 响应时间告警
        if request_metrics.response_time > 5.0:
            alerts.append({
                "type": "slow_response",
                "severity": "warning",
                "message": f"慢请求: {request_metrics.endpoint} 响应时间 {request_metrics.response_time:.2f}s",
                "timestamp": time.time(),
                "data": asdict(request_metrics)
            })

        # 错误率告警
        if request_metrics.status_code >= 500:
            alerts.append({
                "type": "server_error",
                "severity": "critical",
                "message": f"服务器错误: {request_metrics.endpoint} 状态码 {request_metrics.status_code}",
                "timestamp": time.time(),
                "data": asdict(request_metrics)
            })

        # 触发告警回调
        for alert in alerts:
            self._alerts.append(alert)
            for callback in self._alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {e}")

    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self._alert_callbacks.append(callback)

    def get_performance_report(self, minutes: int = 5) -> Dict[str, Any]:
        """获取性能报告"""
        cutoff_time = time.time() - (minutes * 60)

        # 系统指标
        cpu_gauge = self.collector.get_gauge("system_cpu_percent")
        memory_gauge = self.collector.get_gauge("system_memory_percent")
        disk_gauge = self.collector.get_gauge("system_disk_percent")

        # 请求指标
        request_stats = self.request_monitor.get_request_stats(minutes=minutes)
        slow_requests = self.request_monitor.get_slow_requests(limit=5)

        # 响应时间分布
        response_time_stats = self.collector.get_histogram_stats("request_response_time")

        return {
            "report_time": time.time(),
            "period_minutes": minutes,
            "system": {
                "cpu_percent": cpu_gauge,
                "memory_percent": memory_gauge,
                "disk_percent": disk_gauge
            },
            "requests": request_stats,
            "response_time": response_time_stats,
            "slow_requests": [asdict(req) for req in slow_requests],
            "alerts": self._alerts[-10:]  # 最近10个告警
        }

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "counters": dict(self.collector.counters),
            "gauges": dict(self.collector.gauges),
            "histograms": {
                key: self.collector.get_histogram_stats(key)
                for key in self.collector.histograms.keys()
            }
        }

    async def export_metrics(
        self,
        filepath: Union[str, Path],
        format: str = "json"
    ):
        """导出指标数据"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "export_time": time.time(),
            "metrics_summary": self.get_metrics_summary(),
            "performance_report": self.get_performance_report()
        }

        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

        logger.info(f"指标数据已导出到: {filepath}")

    def reset_all_metrics(self):
        """重置所有指标"""
        self.collector.reset_metrics()
        self.request_monitor.requests.clear()
        self._alerts.clear()
        logger.info("所有指标已重置")


# 装饰器
def performance_monitor(endpoint: str = ""):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            start_time = time.time()
            status_code = 200

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                logger.error(f"函数 {func.__name__} 执行失败: {e}")
                raise
            finally:
                response_time = time.time() - start_time
                await monitor.record_request(
                    endpoint=endpoint or func.__name__,
                    method="FUNCTION",
                    status_code=status_code,
                    response_time=response_time
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            start_time = time.time()
            status_code = 200

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = 500
                logger.error(f"函数 {func.__name__} 执行失败: {e}")
                raise
            finally:
                response_time = time.time() - start_time
                # 同步记录（需要异步上下文）
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果在异步上下文中，创建任务
                        asyncio.create_task(
                            monitor.record_request(
                                endpoint=endpoint or func.__name__,
                                method="FUNCTION",
                                status_code=status_code,
                                response_time=response_time
                            )
                        )
                    else:
                        # 如果不在异步上下文中，运行新的事件循环
                        asyncio.run(
                            monitor.record_request(
                                endpoint=endpoint or func.__name__,
                                method="FUNCTION",
                                status_code=status_code,
                                response_time=response_time
                            )
                        )
                except Exception as e:
                    logger.error(f"记录性能指标失败: {e}")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(config: Optional[Dict] = None) -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor

    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(config)

    return _performance_monitor


async def initialize_performance_monitoring(config: Optional[Dict] = None):
    """初始化性能监控"""
    monitor = get_performance_monitor(config)
    await monitor.start_monitoring()
    logger.info("性能监控器已初始化")


async def shutdown_performance_monitor():
    """关闭性能监控"""
    monitor = get_performance_monitor()
    await monitor.stop_monitoring()
    logger.info("性能监控器已关闭")


# 导入wraps
from functools import wraps