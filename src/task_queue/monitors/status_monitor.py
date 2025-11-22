# Status Monitor
# 状态监控器 - 监控队列系统整体状态和健康度

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum

from ..celery_app import celery_manager
from ..task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """系统状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentStatus(Enum):
    """组件状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class WorkerStatus:
    """Worker状态"""
    worker_name: str
    status: ComponentStatus
    active_tasks: int
    total_tasks: int
    load_average: List[float]
    memory_usage: Dict[str, float]
    last_heartbeat: datetime
    queues: List[str]


@dataclass
class QueueStatus:
    """队列状态"""
    queue_name: str
    pending_tasks: int
    active_tasks: int
    failed_tasks: int
    avg_wait_time: float
    max_wait_time: float
    throughput: float


@dataclass
class SystemHealth:
    """系统健康状态"""
    overall_status: SystemStatus
    workers: List[WorkerStatus]
    queues: List[QueueStatus]
    error_rate: float
    success_rate: float
    avg_response_time: float
    timestamp: datetime
    alerts: List[str]


class StatusMonitor:
    """状态监控器"""

    def __init__(self, check_interval: int = 30, history_size: int = 1000):
        self.check_interval = check_interval
        self.history_size = history_size
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

        # 历史数据
        self.health_history: deque = deque(maxlen=history_size)
        self.worker_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.queue_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # 状态缓存
        self.current_health: Optional[SystemHealth] = None
        self.worker_status: Dict[str, WorkerStatus] = {}
        self.queue_status: Dict[str, QueueStatus] = {}

        # 阈值配置
        self.thresholds = {
            'error_rate_warning': 0.05,  # 5%
            'error_rate_critical': 0.15,  # 15%
            'avg_response_time_warning': 60,  # 60秒
            'avg_response_time_critical': 180,  # 180秒
            'queue_depth_warning': 1000,
            'queue_depth_critical': 5000,
            'worker_unresponsive_time': 120,  # 120秒
        }

        self._lock = threading.Lock()

    def start_monitoring(self):
        """启动监控"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("状态监控器已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("状态监控器已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._collect_system_status()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"状态监控循环异常: {e}")
                time.sleep(self.check_interval)

    def _collect_system_status(self):
        """收集系统状态"""
        try:
            # 收集Worker状态
            self._collect_worker_status()

            # 收集队列状态
            self._collect_queue_status()

            # 计算系统健康状态
            self._calculate_system_health()

            # 保存历史数据
            self._save_history()

        except Exception as e:
            logger.error(f"收集系统状态失败: {e}")

    def _collect_worker_status(self):
        """收集Worker状态"""
        try:
            # 获取Worker统计信息
            worker_stats = celery_manager.get_worker_stats()

            for worker_name, stats in worker_stats.items():
                # 获取活跃任务
                active_tasks_info = celery_manager.get_active_tasks()
                active_tasks_count = len(active_tasks_info.get(worker_name, []))

                # 计算负载平均值
                load_average = [
                    stats.get('loadavg', [0, 0, 0])[i] if i < len(stats.get('loadavg', [])) else 0
                    for i in range(3)
                ]

                # 内存使用情况
                memory_usage = {
                    'rss': stats.get('rusage', {}).get('maxrss', 0),
                    'vsz': stats.get('rusage', {}).get('maxrss', 0) * 1024,  # Convert to bytes
                }

                # 队列信息
                queues = stats.get('pool', {}).get('max-concurrency', [])

                # 检查心跳时间
                last_heartbeat = datetime.utcnow()
                if 'pool' in stats and 'timeouts' in stats['pool']:
                    # 这里应该有实际的心跳时间，现在使用当前时间
                    pass

                worker_status = WorkerStatus(
                    worker_name=worker_name,
                    status=self._determine_worker_status(worker_name, active_tasks_count),
                    active_tasks=active_tasks_count,
                    total_tasks=stats.get('total', 0),
                    load_average=load_average,
                    memory_usage=memory_usage,
                    last_heartbeat=last_heartbeat,
                    queues=queues
                )

                self.worker_status[worker_name] = worker_status

        except Exception as e:
            logger.error(f"收集Worker状态失败: {e}")

    def _determine_worker_status(self, worker_name: str, active_tasks: int) -> ComponentStatus:
        """确定Worker状态"""
        try:
            # 检查Worker是否响应
            worker_stats = celery_manager.get_worker_stats()
            if worker_name not in worker_stats:
                return ComponentStatus.STOPPED

            # 检查任务负载
            if active_tasks > 100:  # 假设超过100个任务为高负载
                return ComponentStatus.DEGRADED

            return ComponentStatus.RUNNING

        except Exception:
            return ComponentStatus.ERROR

    def _collect_queue_status(self):
        """收集队列状态"""
        try:
            # 定义要监控的队列
            queue_names = ['default', 'crawler', 'image_processing', 'data_sync', 'batch_processing']

            for queue_name in queue_names:
                # 这里应该从Redis或其他消息代理获取队列信息
                # 现在使用模拟数据
                queue_status = QueueStatus(
                    queue_name=queue_name,
                    pending_tasks=self._get_pending_tasks(queue_name),
                    active_tasks=self._get_active_tasks(queue_name),
                    failed_tasks=self._get_failed_tasks(queue_name),
                    avg_wait_time=self._calculate_avg_wait_time(queue_name),
                    max_wait_time=self._calculate_max_wait_time(queue_name),
                    throughput=self._calculate_throughput(queue_name)
                )

                self.queue_status[queue_name] = queue_status

        except Exception as e:
            logger.error(f"收集队列状态失败: {e}")

    def _get_pending_tasks(self, queue_name: str) -> int:
        """获取待处理任务数（模拟）"""
        # 这里应该从实际的队列系统获取数据
        import random
        return random.randint(0, 500)

    def _get_active_tasks(self, queue_name: str) -> int:
        """获取活跃任务数（模拟）"""
        import random
        return random.randint(0, 50)

    def _get_failed_tasks(self, queue_name: str) -> int:
        """获取失败任务数（模拟）"""
        import random
        return random.randint(0, 10)

    def _calculate_avg_wait_time(self, queue_name: str) -> float:
        """计算平均等待时间（模拟）"""
        import random
        return random.uniform(0, 120)

    def _calculate_max_wait_time(self, queue_name: str) -> float:
        """计算最大等待时间（模拟）"""
        import random
        return random.uniform(60, 300)

    def _calculate_throughput(self, queue_name: str) -> float:
        """计算吞吐量（模拟）"""
        import random
        return random.uniform(10, 100)

    def _calculate_system_health(self):
        """计算系统健康状态"""
        try:
            # 收集指标
            total_active_tasks = sum(worker.active_tasks for worker in self.worker_status.values())
            total_pending_tasks = sum(queue.pending_tasks for queue in self.queue_status.values())
            total_failed_tasks = sum(queue.failed_tasks for queue in self.queue_status.values())

            # 计算成功率
            total_tasks = total_active_tasks + total_pending_tasks + total_failed_tasks
            success_rate = (total_active_tasks + total_pending_tasks) / total_tasks if total_tasks > 0 else 1.0
            error_rate = total_failed_tasks / total_tasks if total_tasks > 0 else 0.0

            # 计算平均响应时间
            avg_wait_times = [queue.avg_wait_time for queue in self.queue_status.values()]
            avg_response_time = sum(avg_wait_times) / len(avg_wait_times) if avg_wait_times else 0.0

            # 收集告警
            alerts = self._generate_alerts(error_rate, avg_response_time, total_pending_tasks)

            # 确定整体状态
            overall_status = self._determine_overall_status(error_rate, avg_response_time, total_pending_tasks)

            # 创建健康状态对象
            system_health = SystemHealth(
                overall_status=overall_status,
                workers=list(self.worker_status.values()),
                queues=list(self.queue_status.values()),
                error_rate=error_rate,
                success_rate=success_rate,
                avg_response_time=avg_response_time,
                timestamp=datetime.utcnow(),
                alerts=alerts
            )

            self.current_health = system_health

        except Exception as e:
            logger.error(f"计算系统健康状态失败: {e}")

    def _generate_alerts(self, error_rate: float, avg_response_time: float, pending_tasks: int) -> List[str]:
        """生成告警"""
        alerts = []

        # 错误率告警
        if error_rate > self.thresholds['error_rate_critical']:
            alerts.append(f"错误率过高: {error_rate:.2%}")
        elif error_rate > self.thresholds['error_rate_warning']:
            alerts.append(f"错误率警告: {error_rate:.2%}")

        # 响应时间告警
        if avg_response_time > self.thresholds['avg_response_time_critical']:
            alerts.append(f"响应时间过长: {avg_response_time:.1f}秒")
        elif avg_response_time > self.thresholds['avg_response_time_warning']:
            alerts.append(f"响应时间警告: {avg_response_time:.1f}秒")

        # 队列深度告警
        if pending_tasks > self.thresholds['queue_depth_critical']:
            alerts.append(f"队列积压严重: {pending_tasks} 个任务")
        elif pending_tasks > self.thresholds['queue_depth_warning']:
            alerts.append(f"队列积压警告: {pending_tasks} 个任务")

        # Worker状态告警
        stopped_workers = [w for w in self.worker_status.values() if w.status == ComponentStatus.STOPPED]
        if stopped_workers:
            alerts.append(f"Worker离线: {', '.join(w.worker_name for w in stopped_workers)}")

        return alerts

    def _determine_overall_status(self, error_rate: float, avg_response_time: float, pending_tasks: int) -> SystemStatus:
        """确定整体系统状态"""
        # 检查关键指标
        if (error_rate > self.thresholds['error_rate_critical'] or
            avg_response_time > self.thresholds['avg_response_time_critical'] or
            pending_tasks > self.thresholds['queue_depth_critical']):
            return SystemStatus.CRITICAL

        # 检查警告指标
        if (error_rate > self.thresholds['error_rate_warning'] or
            avg_response_time > self.thresholds['avg_response_time_warning'] or
            pending_tasks > self.thresholds['queue_depth_warning']):
            return SystemStatus.WARNING

        # 检查Worker状态
        stopped_workers = [w for w in self.worker_status.values() if w.status == ComponentStatus.STOPPED]
        if stopped_workers:
            return SystemStatus.WARNING

        return SystemStatus.HEALTHY

    def _save_history(self):
        """保存历史数据"""
        try:
            if self.current_health:
                self.health_history.append(self.current_health)

            # 保存Worker历史
            for worker_name, worker_status in self.worker_status.items():
                self.worker_history[worker_name].append(worker_status)

            # 保存队列历史
            for queue_name, queue_status in self.queue_status.items():
                self.queue_history[queue_name].append(queue_status)

        except Exception as e:
            logger.error(f"保存历史数据失败: {e}")

    def get_current_health(self) -> Optional[SystemHealth]:
        """获取当前健康状态"""
        with self._lock:
            return self.current_health

    def get_worker_status(self, worker_name: str) -> Optional[WorkerStatus]:
        """获取Worker状态"""
        with self._lock:
            return self.worker_status.get(worker_name)

    def get_queue_status(self, queue_name: str) -> Optional[QueueStatus]:
        """获取队列状态"""
        with self._lock:
            return self.queue_status.get(queue_name)

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        with self._lock:
            if not self.current_health:
                return {'status': 'unknown', 'message': 'No health data available'}

            health = self.current_health

            return {
                'overall_status': health.overall_status.value,
                'timestamp': health.timestamp.isoformat(),
                'workers': {
                    'total': len(health.workers),
                    'running': len([w for w in health.workers if w.status == ComponentStatus.RUNNING]),
                    'stopped': len([w for w in health.workers if w.status == ComponentStatus.STOPPED]),
                    'error': len([w for w in health.workers if w.status == ComponentStatus.ERROR]),
                },
                'queues': {
                    'total': len(health.queues),
                    'pending_tasks': sum(q.pending_tasks for q in health.queues),
                    'active_tasks': sum(q.active_tasks for q in health.queues),
                    'failed_tasks': sum(q.failed_tasks for q in health.queues),
                },
                'metrics': {
                    'error_rate': f"{health.error_rate:.2%}",
                    'success_rate': f"{health.success_rate:.2%}",
                    'avg_response_time': f"{health.avg_response_time:.1f}s",
                },
                'alerts': health.alerts
            }

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能趋势"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # 筛选历史数据
            recent_health = [
                h for h in self.health_history
                if h.timestamp > cutoff_time
            ]

            if not recent_health:
                return {'message': 'No recent data available'}

            # 计算趋势
            error_rates = [h.error_rate for h in recent_health]
            response_times = [h.avg_response_time for h in recent_health]

            return {
                'time_range': f"Last {hours} hours",
                'data_points': len(recent_health),
                'error_rate': {
                    'current': error_rates[-1] if error_rates else 0,
                    'avg': sum(error_rates) / len(error_rates) if error_rates else 0,
                    'max': max(error_rates) if error_rates else 0,
                    'min': min(error_rates) if error_rates else 0,
                    'trend': 'increasing' if len(error_rates) > 1 and error_rates[-1] > error_rates[0] else 'decreasing'
                },
                'response_time': {
                    'current': response_times[-1] if response_times else 0,
                    'avg': sum(response_times) / len(response_times) if response_times else 0,
                    'max': max(response_times) if response_times else 0,
                    'min': min(response_times) if response_times else 0,
                    'trend': 'increasing' if len(response_times) > 1 and response_times[-1] > response_times[0] else 'decreasing'
                }
            }

    def export_status_report(self) -> Dict[str, Any]:
        """导出状态报告"""
        with self._lock:
            if not self.current_health:
                return {'error': 'No health data available'}

            health = self.current_health

            return {
                'report_timestamp': datetime.utcnow().isoformat(),
                'system_health': asdict(health),
                'worker_details': {
                    worker.worker_name: asdict(worker)
                    for worker in health.workers
                },
                'queue_details': {
                    queue.queue_name: asdict(queue)
                    for queue in health.queues
                },
                'performance_trends': self.get_performance_trends(),
                'thresholds': self.thresholds
            }

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """更新阈值配置"""
        self.thresholds.update(new_thresholds)
        logger.info(f"阈值配置已更新: {new_thresholds}")


# 全局状态监控器实例
status_monitor = StatusMonitor()