# Task Manager
# 任务管理器 - 统一管理任务的创建、调度和监控

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict

from .celery_app import celery_app, celery_manager
from ..database.connection import get_db_session
from ..models.sync_record import SyncRecord

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"
    PROGRESS = "progress"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    task_name: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.app = celery_app
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.task_history: List[TaskInfo] = []

    def create_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        queue: str = 'default',
        eta: Optional[datetime] = None,
        countdown: Optional[int] = None,
        expires: Optional[Union[datetime, int]] = None,
        retry: bool = True,
        retry_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建并调度任务

        Args:
            task_name: 任务名称
            args: 位置参数
            kwargs: 关键字参数
            priority: 任务优先级
            queue: 队列名称
            eta: 预计执行时间
            countdown: 延迟执行秒数
            expires: 过期时间
            retry: 是否重试
            retry_policy: 重试策略
            metadata: 任务元数据

        Returns:
            任务ID
        """
        try:
            kwargs = kwargs or {}
            retry_policy = retry_policy or {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 0.2,
                'interval_max': 0.2,
            }

            # 创建任务
            task = self.app.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                priority=priority.value,
                queue=queue,
                eta=eta,
                countdown=countdown,
                expires=expires,
                retry=retry,
                retry_policy=retry_policy,
            )

            # 记录任务信息
            task_info = TaskInfo(
                task_id=task.id,
                task_name=task_name,
                status=TaskStatus.PENDING,
                priority=priority,
                created_at=datetime.utcnow(),
                metadata=metadata
            )

            self.active_tasks[task.id] = task_info

            logger.info(f"任务已创建: {task_name} (ID: {task.id})")
            return task.id

        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            raise

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务状态"""
        try:
            # 首先检查本地缓存
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]

            # 从Celery获取任务状态
            result = self.app.AsyncResult(task_id)

            task_info = TaskInfo(
                task_id=task_id,
                task_name=result.name or 'unknown',
                status=self._convert_celery_status(result.status),
                priority=TaskPriority.NORMAL,
                created_at=datetime.utcnow(),
                result=result.result if result.successful() else None,
                error=str(result.result) if result.failed() else None
            )

            # 更新本地缓存
            self.active_tasks[task_id] = task_info

            return task_info

        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None

    def _convert_celery_status(self, celery_status: str) -> TaskStatus:
        """转换Celery状态到TaskStatus"""
        status_mapping = {
            'PENDING': TaskStatus.PENDING,
            'STARTED': TaskStatus.STARTED,
            'SUCCESS': TaskStatus.SUCCESS,
            'FAILURE': TaskStatus.FAILURE,
            'RETRY': TaskStatus.RETRY,
            'REVOKED': TaskStatus.REVOKED,
            'PROGRESS': TaskStatus.PROGRESS,
        }
        return status_mapping.get(celery_status, TaskStatus.PENDING)

    def update_task_progress(self, task_id: str, progress: Dict[str, Any]):
        """更新任务进度"""
        try:
            if task_id in self.active_tasks:
                self.active_tasks[task_id].progress = progress

            # 更新数据库中的同步记录
            with get_db_session() as session:
                sync_record = session.query(SyncRecord).filter_by(
                    task_id=task_id
                ).first()

                if sync_record:
                    sync_record.progress = json.dumps(progress)
                    sync_record.updated_at = datetime.utcnow()
                    session.commit()

        except Exception as e:
            logger.error(f"更新任务进度失败: {e}")

    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """取消任务"""
        try:
            success = celery_manager.revoke_task(task_id, terminate)

            if success and task_id in self.active_tasks:
                self.active_tasks[task_id].status = TaskStatus.REVOKED

            logger.info(f"任务已取消: {task_id}")
            return success

        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False

    def get_active_tasks(self) -> List[TaskInfo]:
        """获取所有活跃任务"""
        try:
            # 从Celery获取活跃任务
            celery_active = celery_manager.get_active_tasks()

            # 更新本地缓存
            for worker, tasks in celery_active.items():
                for task in tasks:
                    if task['id'] not in self.active_tasks:
                        task_info = TaskInfo(
                            task_id=task['id'],
                            task_name=task['name'],
                            status=TaskStatus.STARTED,
                            priority=TaskPriority.NORMAL,
                            created_at=datetime.utcnow()
                        )
                        self.active_tasks[task['id']] = task_info

            return list(self.active_tasks.values())

        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            return list(self.active_tasks.values())

    def get_completed_tasks(self, hours: int = 24) -> List[TaskInfo]:
        """获取已完成的任务"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # 从历史记录中获取
            completed = [
                task for task in self.task_history
                if task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
                and task.completed_at
                and task.completed_at > cutoff_time
            ]

            # 从活跃任务中筛选已完成的
            for task in self.active_tasks.values():
                if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
                    and task.completed_at
                    and task.completed_at > cutoff_time):
                    completed.append(task)

            return completed

        except Exception as e:
            logger.error(f"获取已完成任务失败: {e}")
            return []

    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务记录"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)

            # 清理历史记录
            original_count = len(self.task_history)
            self.task_history = [
                task for task in self.task_history
                if task.created_at > cutoff_time
            ]

            # 清理活跃任务中的已完成任务
            completed_tasks = [
                task_id for task_id, task in self.active_tasks.items()
                if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
                    and task.completed_at
                    and task.completed_at < cutoff_time)
            ]

            for task_id in completed_tasks:
                del self.active_tasks[task_id]

            cleaned_count = original_count - len(self.task_history) + len(completed_tasks)
            logger.info(f"清理了 {cleaned_count} 个旧任务记录")

        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        try:
            stats = {
                'total_tasks': len(self.active_tasks),
                'status_counts': {},
                'queue_counts': {},
                'priority_counts': {},
                'recent_success_rate': 0.0,
            }

            # 统计状态分布
            for task in self.active_tasks.values():
                status_name = task.status.value
                stats['status_counts'][status_name] = stats['status_counts'].get(status_name, 0) + 1

            # 统计优先级分布
            for task in self.active_tasks.values():
                priority_name = task.priority.name
                stats['priority_counts'][priority_name] = stats['priority_counts'].get(priority_name, 0) + 1

            # 计算最近成功率
            recent_tasks = self.get_completed_tasks(24)
            if recent_tasks:
                success_count = sum(1 for task in recent_tasks if task.status == TaskStatus.SUCCESS)
                stats['recent_success_rate'] = success_count / len(recent_tasks)

            # 获取Worker统计
            worker_stats = celery_manager.get_worker_stats()
            stats['worker_stats'] = worker_stats

            return stats

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}

    def create_batch_task(
        self,
        task_name: str,
        items: List[Any],
        batch_size: int = 100,
        **task_kwargs
    ) -> List[str]:
        """
        创建批量任务

        Args:
            task_name: 任务名称
            items: 要处理的项目列表
            batch_size: 批次大小
            **task_kwargs: 其他任务参数

        Returns:
            任务ID列表
        """
        task_ids = []

        try:
            # 将项目分批
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]

                task_id = self.create_task(
                    task_name=task_name,
                    kwargs={'items': batch, **task_kwargs},
                    queue='batch_processing',
                    metadata={'batch_index': i // batch_size, 'total_batches': (len(items) + batch_size - 1) // batch_size}
                )

                task_ids.append(task_id)

            logger.info(f"创建了 {len(task_ids)} 个批量任务")
            return task_ids

        except Exception as e:
            logger.error(f"创建批量任务失败: {e}")
            return []

    def monitor_task(self, task_id: str, timeout: int = 300) -> bool:
        """
        监控任务直到完成或超时

        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）

        Returns:
            是否成功完成
        """
        start_time = datetime.utcnow()

        while True:
            task_info = self.get_task_status(task_id)

            if not task_info:
                logger.error(f"任务不存在: {task_id}")
                return False

            if task_info.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]:
                return task_info.status == TaskStatus.SUCCESS

            # 检查超时
            if (datetime.utcnow() - start_time).total_seconds() > timeout:
                logger.warning(f"任务监控超时: {task_id}")
                return False

            # 等待后重试
            import time
            time.sleep(5)

    def export_task_report(self, task_id: str) -> Dict[str, Any]:
        """导出任务报告"""
        try:
            task_info = self.get_task_status(task_id)

            if not task_info:
                return {'error': 'Task not found'}

            report = {
                'task_info': asdict(task_info),
                'execution_time': None,
                'performance_metrics': {},
            }

            # 计算执行时间
            if task_info.started_at and task_info.completed_at:
                report['execution_time'] = (task_info.completed_at - task_info.started_at).total_seconds()

            # 添加性能指标
            if task_info.progress:
                report['performance_metrics'] = task_info.progress

            return report

        except Exception as e:
            logger.error(f"导出任务报告失败: {e}")
            return {'error': str(e)}


# 全局任务管理器实例
task_manager = TaskManager()