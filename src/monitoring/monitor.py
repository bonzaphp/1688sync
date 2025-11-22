"""
性能监控模块 - 监控系统性能指标和资源使用情况
"""

import gc
import os
import psutil
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器


@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]
    timestamp: datetime


@dataclass
class ApplicationMetrics:
    """应用指标"""
    active_requests: int
    total_requests: int
    request_rate: float
    error_rate: float
    avg_response_time: float
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    queue_depth: Dict[str, int]
    timestamp: datetime


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, collection_interval: int = 30, history_size: int = 1000):
        self.collection_interval = collection_interval
        self.history_size = history_size
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 指标存储
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)

        # 系统信息
        self.process = psutil.Process()
        self.start_time = datetime.now()

        # 回调函数
        self.metric_callbacks: List[Callable[[MetricValue], None]] = []

        self._lock = threading.Lock()

    def start_monitoring(self):
        """启动监控"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("性能监控器已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("性能监控器已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._cleanup_old_data()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error("性能监控循环异常", exc_info=True)
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存信息
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            memory_available_mb = memory.available / 1024 / 1024

            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            disk_used_gb = disk.used / 1024 / 1024 / 1024
            disk_free_gb = disk.free / 1024 / 1024 / 1024

            # 网络IO
            network_io = psutil.net_io_counters()._asdict()

            # 进程数量
            process_count = len(psutil.pids())

            # 负载平均值
            load_average = list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0]

            # 创建系统指标对象
            system_metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average,
                timestamp=datetime.now()
            )

            # 记录指标
            self._record_metrics("system", system_metrics)

        except Exception as e:
            logger.error("收集系统指标失败", exc_info=True)

    def _collect_application_metrics(self):
        """收集应用指标"""
        try:
            # 进程信息
            process_memory = self.process.memory_info()
            process_cpu = self.process.cpu_percent()

            # 应用自定义指标
            with self._lock:
                active_requests = self.gauges.get('active_requests', 0)
                total_requests = self.counters.get('total_requests', 0)
                error_count = self.counters.get('error_count', 0)
                completed_tasks = self.counters.get('completed_tasks', 0)
                failed_tasks = self.counters.get('failed_tasks', 0)

            # 计算速率
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            request_rate = total_requests / uptime_seconds if uptime_seconds > 0 else 0
            error_rate = error_count / total_requests if total_requests > 0 else 0

            # 计算平均响应时间
            response_times = self.timers.get('request_duration', [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            # 队列深度
            queue_depth = {
                'default': self.gauges.get('queue_default_depth', 0),
                'crawler': self.gauges.get('queue_crawler_depth', 0),
                'image_processing': self.gauges.get('queue_image_processing_depth', 0),
                'data_sync': self.gauges.get('queue_data_sync_depth', 0)
            }

            # 创建应用指标对象
            app_metrics = ApplicationMetrics(
                active_requests=int(active_requests),
                total_requests=int(total_requests),
                request_rate=request_rate,
                error_rate=error_rate,
                avg_response_time=avg_response_time,
                active_tasks=self.gauges.get('active_tasks', 0),
                completed_tasks=int(completed_tasks),
                failed_tasks=int(failed_tasks),
                queue_depth=queue_depth,
                timestamp=datetime.now()
            )

            # 记录指标
            self._record_metrics("application", app_metrics)

            # 记录进程指标
            self.set_gauge("process_memory_mb", process_memory.rss / 1024 / 1024)
            self.set_gauge("process_cpu_percent", process_cpu)

        except Exception as e:
            logger.error("收集应用指标失败", exc_info=True)

    def _record_metrics(self, category: str, metrics: Any):
        """记录指标"""
        try:
            timestamp = datetime.now()
            metrics_dict = asdict(metrics)

            for key, value in metrics_dict.items():
                if isinstance(value, (int, float)):
                    metric_name = f"{category}.{key}"
                    metric_value = MetricValue(
                        name=metric_name,
                        value=float(value),
                        timestamp=timestamp,
                        tags={"category": category},
                        metric_type=MetricType.GAUGE
                    )

                    self.metrics_history[metric_name].append(metric_value)

                    # 调用回调函数
                    for callback in self.metric_callbacks:
                        try:
                            callback(metric_value)
                        except Exception as e:
                            logger.error(f"指标回调函数执行失败: {e}")

        except Exception as e:
            logger.error("记录指标失败", exc_info=True)

    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)

            for metric_name, history in self.metrics_history.items():
                # 移除24小时前的数据
                while history and history[0].timestamp < cutoff_time:
                    history.popleft()

        except Exception as e:
            logger.error("清理旧数据失败", exc_info=True)

    def increment_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """增加计数器"""
        with self._lock:
            self.counters[name] += value
            self._record_counter_metric(name, self.counters[name], tags)

    def _record_counter_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录计数器指标"""
        metric_value = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.COUNTER
        )
        self.metrics_history[name].append(metric_value)

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表盘值"""
        with self._lock:
            self.gauges[name] = value
            self._record_gauge_metric(name, value, tags)

    def _record_gauge_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录仪表盘指标"""
        metric_value = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.GAUGE
        )
        self.metrics_history[name].append(metric_value)

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图数据"""
        with self._lock:
            self.histograms[name].append(value)
            # 限制历史数据大小
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            self._record_histogram_metric(name, value, tags)

    def _record_histogram_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图指标"""
        metric_value = MetricValue(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.HISTOGRAM
        )
        self.metrics_history[name].append(metric_value)

    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """记录计时器数据"""
        with self._lock:
            self.timers[name].append(duration_ms)
            # 限制历史数据大小
            if len(self.timers[name]) > 1000:
                self.timers[name] = self.timers[name][-1000:]
            self._record_timer_metric(name, duration_ms, tags)

    def _record_timer_metric(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """记录计时器指标"""
        metric_value = MetricValue(
            name=name,
            value=duration_ms,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=MetricType.TIMER
        )
        self.metrics_history[name].append(metric_value)

    def get_metric(self, name: str, since: datetime = None) -> List[MetricValue]:
        """获取指标数据"""
        with self._lock:
            if name not in self.metrics_history:
                return []

            history = self.metrics_history[name]
            if since is None:
                return list(history)

            return [metric for metric in history if metric.timestamp >= since]

    def get_metric_summary(self, name: str, hours: int = 1) -> Dict[str, Any]:
        """获取指标摘要"""
        since = datetime.now() - timedelta(hours=hours)
        metrics = self.get_metric(name, since)

        if not metrics:
            return {}

        values = [m.value for m in metrics]
        return {
            'name': name,
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1],
            'time_range': f"Last {hours} hours"
        }

    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 获取最新系统指标
            cpu_metrics = self.get_metric("system.cpu_percent", datetime.now() - timedelta(minutes=5))
            memory_metrics = self.get_metric("system.memory_percent", datetime.now() - timedelta(minutes=5))
            disk_metrics = self.get_metric("system.disk_usage_percent", datetime.now() - timedelta(minutes=5))

            # 计算平均值
            cpu_avg = sum(m.value for m in cpu_metrics) / len(cpu_metrics) if cpu_metrics else 0
            memory_avg = sum(m.value for m in memory_metrics) / len(memory_metrics) if memory_metrics else 0
            disk_avg = sum(m.value for m in disk_metrics) / len(disk_metrics) if disk_metrics else 0

            # 确定健康状态
            health_status = "healthy"
            alerts = []

            if cpu_avg > 80:
                health_status = "critical" if cpu_avg > 90 else "warning"
                alerts.append(f"CPU使用率过高: {cpu_avg:.1f}%")

            if memory_avg > 80:
                health_status = "critical" if memory_avg > 90 else "warning"
                alerts.append(f"内存使用率过高: {memory_avg:.1f}%")

            if disk_avg > 85:
                health_status = "critical" if disk_avg > 95 else "warning"
                alerts.append(f"磁盘使用率过高: {disk_avg:.1f}%")

            return {
                'status': health_status,
                'cpu_percent': cpu_avg,
                'memory_percent': memory_avg,
                'disk_percent': disk_avg,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("获取系统健康状态失败", exc_info=True)
            return {
                'status': 'unknown',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        try:
            report = {
                'time_range': f"Last {hours} hours",
                'generated_at': datetime.now().isoformat(),
                'system_metrics': {},
                'application_metrics': {},
                'custom_metrics': {}
            }

            # 系统指标
            system_metric_names = [
                'system.cpu_percent',
                'system.memory_percent',
                'system.disk_usage_percent',
                'system.process_count'
            ]

            for name in system_metric_names:
                report['system_metrics'][name] = self.get_metric_summary(name, hours)

            # 应用指标
            app_metric_names = [
                'total_requests',
                'error_count',
                'process_memory_mb',
                'process_cpu_percent'
            ]

            for name in app_metric_names:
                report['application_metrics'][name] = self.get_metric_summary(name, hours)

            # 自定义指标
            custom_names = [name for name in self.metrics_history.keys()
                          if not name.startswith(('system.', 'application.'))]

            for name in custom_names[:10]:  # 限制数量
                report['custom_metrics'][name] = self.get_metric_summary(name, hours)

            return report

        except Exception as e:
            logger.error("生成性能报告失败", exc_info=True)
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def add_metric_callback(self, callback: Callable[[MetricValue], None]):
        """添加指标回调函数"""
        self.metric_callbacks.append(callback)

    def reset_metrics(self):
        """重置所有指标"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.metrics_history.clear()
        logger.info("所有指标已重置")

    def export_metrics(self, format: str = "json") -> str:
        """导出指标数据"""
        try:
            if format.lower() == "json":
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'counters': dict(self.counters),
                    'gauges': dict(self.gauges),
                    'histograms': {k: v[-100:] for k, v in self.histograms.items()},  # 最近100个值
                    'timers': {k: v[-100:] for k, v in self.timers.items()}  # 最近100个值
                }
                import json
                return json.dumps(export_data, indent=2, default=str)

            else:
                raise ValueError(f"不支持的导出格式: {format}")

        except Exception as e:
            logger.error("导出指标数据失败", exc_info=True)
            return f"导出失败: {e}"


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()

# 便捷函数
def increment_counter(name: str, value: float = 1, tags: Dict[str, str] = None):
    """增加计数器"""
    performance_monitor.increment_counter(name, value, tags)

def set_gauge(name: str, value: float, tags: Dict[str, str] = None):
    """设置仪表盘值"""
    performance_monitor.set_gauge(name, value, tags)

def record_histogram(name: str, value: float, tags: Dict[str, str] = None):
    """记录直方图数据"""
    performance_monitor.record_histogram(name, value, tags)

def record_timer(name: str, duration_ms: float, tags: Dict[str, str] = None):
    """记录计时器数据"""
    performance_monitor.record_timer(name, duration_ms, tags)