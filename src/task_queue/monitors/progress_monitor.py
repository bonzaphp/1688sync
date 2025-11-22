# Progress Monitor
# 进度监控器 - 实时监控任务进度和状态

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from ..task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """进度更新"""
    task_id: str
    current: int
    total: int
    percent: int
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    progress_history: List[ProgressUpdate] = None
    current_progress: Optional[ProgressUpdate] = None
    estimated_completion: Optional[datetime] = None
    speed_metrics: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.progress_history is None:
            self.progress_history = []
        if self.speed_metrics is None:
            self.speed_metrics = {}


class ProgressMonitor:
    """进度监控器"""

    def __init__(self, max_history: int = 1000, update_interval: int = 5):
        self.max_history = max_history
        self.update_interval = update_interval
        self.task_progress: Dict[str, TaskProgress] = {}
        self.progress_callbacks: List[Callable[[ProgressUpdate], None]] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start_monitoring(self):
        """启动监控"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("进度监控器已启动")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("进度监控器已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring_active:
            try:
                self._update_task_progress()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                time.sleep(self.update_interval)

    def add_progress_callback(self, callback: Callable[[ProgressUpdate], None]):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[ProgressUpdate], None]):
        """移除进度回调函数"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)

    def notify_progress_update(self, task_id: str, progress_data: Dict[str, Any]):
        """通知进度更新"""
        try:
            progress_update = ProgressUpdate(
                task_id=task_id,
                current=progress_data.get('current', 0),
                total=progress_data.get('total', 0),
                percent=progress_data.get('percent', 0),
                description=progress_data.get('description', ''),
                timestamp=datetime.fromisoformat(progress_data.get('timestamp', datetime.utcnow().isoformat())),
                metadata=progress_data.get('metadata')
            )

            self._handle_progress_update(progress_update)

        except Exception as e:
            logger.error(f"处理进度更新失败: {e}")

    def _handle_progress_update(self, progress_update: ProgressUpdate):
        """处理进度更新"""
        with self._lock:
            # 获取或创建任务进度
            if progress_update.task_id not in self.task_progress:
                task_info = task_manager.get_task_status(progress_update.task_id)
                if task_info:
                    self.task_progress[progress_update.task_id] = TaskProgress(
                        task_id=progress_update.task_id,
                        task_name=task_info.task_name,
                        status=task_info.status,
                        created_at=task_info.created_at,
                        started_at=task_info.started_at
                    )
                else:
                    return

            task_progress = self.task_progress[progress_update.task_id]

            # 更新进度历史
            task_progress.progress_history.append(progress_update)
            if len(task_progress.progress_history) > self.max_history:
                task_progress.progress_history.pop(0)

            # 更新当前进度
            task_progress.current_progress = progress_update

            # 计算速度指标
            self._calculate_speed_metrics(task_progress)

            # 估算完成时间
            self._estimate_completion_time(task_progress)

            # 调用回调函数
            for callback in self.progress_callbacks:
                try:
                    callback(progress_update)
                except Exception as e:
                    logger.error(f"进度回调异常: {e}")

    def _calculate_speed_metrics(self, task_progress: TaskProgress):
        """计算速度指标"""
        history = task_progress.progress_history
        if len(history) < 2:
            return

        # 获取最近10个进度点
        recent_history = list(history)[-10:]

        if len(recent_history) < 2:
            return

        # 计算平均速度
        total_progress = recent_history[-1].current - recent_history[0].current
        time_diff = (recent_history[-1].timestamp - recent_history[0].timestamp).total_seconds()

        if time_diff > 0:
            avg_speed = total_progress / time_diff  # 项目/秒
            task_progress.speed_metrics['avg_speed'] = avg_speed

            # 计算瞬时速度（最近3个点）
            if len(recent_history) >= 3:
                recent_total = recent_history[-1].current - recent_history[-3].current
                recent_time = (recent_history[-1].timestamp - recent_history[-3].timestamp).total_seconds()
                if recent_time > 0:
                    instant_speed = recent_total / recent_time
                    task_progress.speed_metrics['instant_speed'] = instant_speed

    def _estimate_completion_time(self, task_progress: TaskProgress):
        """估算完成时间"""
        current_progress = task_progress.current_progress
        if not current_progress or current_progress.total <= 0:
            return

        speed_metrics = task_progress.speed_metrics
        if 'avg_speed' not in speed_metrics or speed_metrics['avg_speed'] <= 0:
            return

        remaining = current_progress.total - current_progress.current
        avg_speed = speed_metrics['avg_speed']

        if remaining > 0 and avg_speed > 0:
            estimated_seconds = remaining / avg_speed
            task_progress.estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)

    def _update_task_progress(self):
        """更新任务进度"""
        try:
            # 获取活跃任务
            active_tasks = task_manager.get_active_tasks()

            for task_info in active_tasks:
                task_id = task_info.task_id

                # 如果任务不在监控中，添加到监控
                if task_id not in self.task_progress:
                    self.task_progress[task_id] = TaskProgress(
                        task_id=task_id,
                        task_name=task_info.task_name,
                        status=task_info.status,
                        created_at=task_info.created_at,
                        started_at=task_info.started_at
                    )

                # 更新任务状态
                self.task_progress[task_id].status = task_info.status

            # 清理已完成或失败的任务
            cleanup_threshold = datetime.utcnow() - timedelta(hours=1)
            tasks_to_remove = []

            for task_id, task_progress in self.task_progress.items():
                if (task_progress.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED] and
                    task_progress.current_progress and
                    task_progress.current_progress.timestamp < cleanup_threshold):
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.task_progress[task_id]

        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")

    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务进度"""
        with self._lock:
            return self.task_progress.get(task_id)

    def get_all_progress(self) -> List[TaskProgress]:
        """获取所有任务进度"""
        with self._lock:
            return list(self.task_progress.values())

    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        with self._lock:
            total_tasks = len(self.task_progress)
            if total_tasks == 0:
                return {
                    'total_tasks': 0,
                    'status_distribution': {},
                    'avg_progress': 0,
                    'estimated_completion_times': []
                }

            # 状态分布
            status_counts = defaultdict(int)
            total_progress = 0
            completion_times = []

            for task_progress in self.task_progress.values():
                status_counts[task_progress.status.value] += 1

                if task_progress.current_progress:
                    total_progress += task_progress.current_progress.percent

                if task_progress.estimated_completion:
                    completion_times.append({
                        'task_id': task_progress.task_id,
                        'task_name': task_progress.task_name,
                        'estimated_completion': task_progress.estimated_completion.isoformat()
                    })

            avg_progress = total_progress / total_tasks if total_tasks > 0 else 0

            return {
                'total_tasks': total_tasks,
                'status_distribution': dict(status_counts),
                'avg_progress': round(avg_progress, 2),
                'estimated_completion_times': completion_times[:10],  # 只返回前10个
                'monitoring_active': self.monitoring_active
            }

    def get_running_tasks_progress(self) -> List[Dict[str, Any]]:
        """获取正在运行任务的进度"""
        with self._lock:
            running_tasks = []

            for task_progress in self.task_progress.values():
                if task_progress.status == TaskStatus.STARTED and task_progress.current_progress:
                    progress_data = {
                        'task_id': task_progress.task_id,
                        'task_name': task_progress.task_name,
                        'current': task_progress.current_progress.current,
                        'total': task_progress.current_progress.total,
                        'percent': task_progress.current_progress.percent,
                        'description': task_progress.current_progress.description,
                        'speed_metrics': task_progress.speed_metrics,
                        'estimated_completion': task_progress.estimated_completion.isoformat() if task_progress.estimated_completion else None
                    }
                    running_tasks.append(progress_data)

            return running_tasks

    def get_task_speed_analysis(self, task_id: str) -> Dict[str, Any]:
        """获取任务速度分析"""
        with self._lock:
            task_progress = self.task_progress.get(task_id)
            if not task_progress or not task_progress.progress_history:
                return {}

            history = task_progress.progress_history
            if len(history) < 2:
                return {}

            # 计算速度趋势
            speeds = []
            for i in range(1, len(history)):
                progress_diff = history[i].current - history[i-1].current
                time_diff = (history[i].timestamp - history[i-1].timestamp).total_seconds()
                if time_diff > 0:
                    speed = progress_diff / time_diff
                    speeds.append(speed)

            if not speeds:
                return {}

            return {
                'avg_speed': sum(speeds) / len(speeds),
                'max_speed': max(speeds),
                'min_speed': min(speeds),
                'speed_variance': sum((s - sum(speeds)/len(speeds))**2 for s in speeds) / len(speeds),
                'speed_trend': 'increasing' if speeds[-1] > speeds[0] else 'decreasing' if speeds[-1] < speeds[0] else 'stable',
                'data_points': len(speeds)
            }

    def export_progress_report(self, task_id: str) -> Dict[str, Any]:
        """导出任务进度报告"""
        with self._lock:
            task_progress = self.task_progress.get(task_id)
            if not task_progress:
                return {'error': 'Task not found'}

            report = {
                'task_info': {
                    'task_id': task_progress.task_id,
                    'task_name': task_progress.task_name,
                    'status': task_progress.status.value,
                    'created_at': task_progress.created_at.isoformat(),
                    'started_at': task_progress.started_at.isoformat() if task_progress.started_at else None
                },
                'current_progress': asdict(task_progress.current_progress) if task_progress.current_progress else None,
                'speed_metrics': task_progress.speed_metrics,
                'estimated_completion': task_progress.estimated_completion.isoformat() if task_progress.estimated_completion else None,
                'progress_history': [asdict(update) for update in task_progress.progress_history[-20:]],  # 最近20个更新
                'speed_analysis': self.get_task_speed_analysis(task_id)
            }

            return report

    def cleanup_old_progress(self, days: int = 7):
        """清理旧的进度数据"""
        with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            tasks_to_remove = []

            for task_id, task_progress in self.task_progress.items():
                if (task_progress.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED] and
                    task_progress.current_progress and
                    task_progress.current_progress.timestamp < cutoff_time):
                    tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.task_progress[task_id]

            logger.info(f"清理了 {len(tasks_to_remove)} 个旧任务进度记录")


# 全局进度监控器实例
progress_monitor = ProgressMonitor()