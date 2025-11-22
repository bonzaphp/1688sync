# Queue Scheduler
# 任务调度器 - 管理任务的定时调度和批量处理

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from celery.schedules import crontab
from celery.app.task import Task
from celery.beat import Scheduler, PersistentScheduler

from .celery_app import celery_app
from .task_manager import task_manager, TaskPriority

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """调度类型枚举"""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DELAYED = "delayed"


@dataclass
class ScheduleConfig:
    """调度配置"""
    name: str
    task: str
    schedule_type: ScheduleType
    args: tuple = ()
    kwargs: dict = None
    priority: TaskPriority = TaskPriority.NORMAL
    queue: str = 'default'
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 300
    metadata: dict = None

    # 调度时间配置
    start_time: Optional[datetime] = None
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.metadata is None:
            self.metadata = {}


class QueueScheduler:
    """队列调度器"""

    def __init__(self):
        self.app = celery_app
        self.scheduled_tasks: Dict[str, ScheduleConfig] = {}
        self.running_schedules: Dict[str, str] = {}  # schedule_name -> task_id
        self._setup_default_schedules()

    def _setup_default_schedules(self):
        """设置默认调度任务"""
        # 每小时健康检查
        self.add_schedule(ScheduleConfig(
            name='health_check_hourly',
            task='src.queue.tasks.health_check',
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,  # 1小时
            priority=TaskPriority.LOW,
            queue='default'
        ))

        # 每日凌晨数据同步
        self.add_schedule(ScheduleConfig(
            name='daily_data_sync',
            task='src.queue.tasks.data_sync.sync_products',
            schedule_type=ScheduleType.CRON,
            cron_expression='0 2 * * *',  # 凌晨2点
            kwargs={'sync_type': 'incremental'},
            priority=TaskPriority.NORMAL,
            queue='data_sync'
        ))

        # 每周数据清理
        self.add_schedule(ScheduleConfig(
            name='weekly_cleanup',
            task='src.queue.tasks.data_sync.cleanup_duplicates',
            schedule_type=ScheduleType.CRON,
            cron_expression='0 3 * * 0',  # 周日凌晨3点
            kwargs={'dry_run': False},
            priority=TaskPriority.LOW,
            queue='data_sync'
        ))

    def add_schedule(self, config: ScheduleConfig) -> bool:
        """
        添加调度任务

        Args:
            config: 调度配置

        Returns:
            是否添加成功
        """
        try:
            # 验证配置
            if not self._validate_schedule_config(config):
                return False

            # 添加到调度列表
            self.scheduled_tasks[config.name] = config

            # 如果是立即执行的调度，立即启动
            if config.schedule_type == ScheduleType.ONCE:
                self._schedule_once(config)
            elif config.schedule_type == ScheduleType.DELAYED:
                self._schedule_delayed(config)

            logger.info(f"调度任务已添加: {config.name}")
            return True

        except Exception as e:
            logger.error(f"添加调度任务失败: {e}")
            return False

    def _validate_schedule_config(self, config: ScheduleConfig) -> bool:
        """验证调度配置"""
        if not config.name or not config.task:
            logger.error("调度配置缺少名称或任务")
            return False

        # 验证调度类型
        if config.schedule_type == ScheduleType.INTERVAL and not config.interval_seconds:
            logger.error("间隔调度需要设置 interval_seconds")
            return False

        if config.schedule_type == ScheduleType.CRON and not config.cron_expression:
            logger.error("Cron调度需要设置 cron_expression")
            return False

        if config.schedule_type == ScheduleType.DELAYED and not config.start_time:
            logger.error("延迟调度需要设置 start_time")
            return False

        return True

    def _schedule_once(self, config: ScheduleConfig):
        """调度一次性任务"""
        try:
            task_id = task_manager.create_task(
                task_name=config.task,
                args=config.args,
                kwargs=config.kwargs,
                priority=config.priority,
                queue=config.queue
            )

            self.running_schedules[config.name] = task_id
            logger.info(f"一次性任务已调度: {config.name} (任务ID: {task_id})")

        except Exception as e:
            logger.error(f"调度一次性任务失败: {e}")

    def _schedule_delayed(self, config: ScheduleConfig):
        """调度延迟任务"""
        try:
            # 计算延迟时间
            now = datetime.utcnow()
            if config.start_time <= now:
                delay_seconds = 0
            else:
                delay_seconds = (config.start_time - now).total_seconds()

            task_id = task_manager.create_task(
                task_name=config.task,
                args=config.args,
                kwargs=config.kwargs,
                priority=config.priority,
                queue=config.queue,
                countdown=int(delay_seconds)
            )

            self.running_schedules[config.name] = task_id
            logger.info(f"延迟任务已调度: {config.name} (任务ID: {task_id})")

        except Exception as e:
            logger.error(f"调度延迟任务失败: {e}")

    def remove_schedule(self, schedule_name: str) -> bool:
        """移除调度任务"""
        try:
            if schedule_name in self.scheduled_tasks:
                # 取消正在运行的任务
                if schedule_name in self.running_schedules:
                    task_id = self.running_schedules[schedule_name]
                    task_manager.cancel_task(task_id)
                    del self.running_schedules[schedule_name]

                # 从调度列表中移除
                del self.scheduled_tasks[schedule_name]

                logger.info(f"调度任务已移除: {schedule_name}")
                return True

            return False

        except Exception as e:
            logger.error(f"移除调度任务失败: {e}")
            return False

    def enable_schedule(self, schedule_name: str) -> bool:
        """启用调度任务"""
        if schedule_name in self.scheduled_tasks:
            self.scheduled_tasks[schedule_name].enabled = True
            logger.info(f"调度任务已启用: {schedule_name}")
            return True
        return False

    def disable_schedule(self, schedule_name: str) -> bool:
        """禁用调度任务"""
        if schedule_name in self.scheduled_tasks:
            self.scheduled_tasks[schedule_name].enabled = False

            # 取消正在运行的任务
            if schedule_name in self.running_schedules:
                task_id = self.running_schedules[schedule_name]
                task_manager.cancel_task(task_id)
                del self.running_schedules[schedule_name]

            logger.info(f"调度任务已禁用: {schedule_name}")
            return True
        return False

    def get_schedule_status(self, schedule_name: str) -> Optional[Dict[str, Any]]:
        """获取调度任务状态"""
        if schedule_name not in self.scheduled_tasks:
            return None

        config = self.scheduled_tasks[schedule_name]
        status = {
            'name': config.name,
            'task': config.task,
            'schedule_type': config.schedule_type.value,
            'enabled': config.enabled,
            'priority': config.priority.name,
            'queue': config.queue
        }

        # 添加运行状态
        if schedule_name in self.running_schedules:
            task_id = self.running_schedules[schedule_name]
            task_info = task_manager.get_task_status(task_id)
            if task_info:
                status['running'] = True
                status['task_id'] = task_id
                status['task_status'] = task_info.status.value
            else:
                status['running'] = False
        else:
            status['running'] = False

        return status

    def list_schedules(self) -> List[Dict[str, Any]]:
        """列出所有调度任务"""
        return [
            self.get_schedule_status(name)
            for name in self.scheduled_tasks.keys()
        ]

    def create_batch_schedule(
        self,
        base_config: ScheduleConfig,
        items: List[Any],
        batch_size: int = 100,
        delay_between_batches: int = 60
    ) -> str:
        """
        创建批量调度

        Args:
            base_config: 基础调度配置
            items: 要处理的项目列表
            batch_size: 批次大小
            delay_between_batches: 批次间延迟（秒）

        Returns:
            批量调度ID
        """
        try:
            batch_id = f"batch_{base_config.name}_{datetime.utcnow().timestamp()}"
            total_batches = (len(items) + batch_size - 1) // batch_size

            for i in range(0, len(items), batch_size):
                batch_items = items[i:i + batch_size]
                batch_index = i // batch_size

                # 创建批次配置
                batch_config = ScheduleConfig(
                    name=f"{batch_id}_batch_{batch_index}",
                    task=base_config.task,
                    schedule_type=ScheduleType.DELAYED,
                    start_time=datetime.utcnow() + timedelta(seconds=batch_index * delay_between_batches),
                    kwargs={'items': batch_items, **base_config.kwargs},
                    priority=base_config.priority,
                    queue=base_config.queue,
                    metadata={
                        'batch_id': batch_id,
                        'batch_index': batch_index,
                        'total_batches': total_batches,
                        'batch_size': len(batch_items)
                    }
                )

                self.add_schedule(batch_config)

            logger.info(f"批量调度已创建: {batch_id} ({total_batches} 个批次)")
            return batch_id

        except Exception as e:
            logger.error(f"创建批量调度失败: {e}")
            return ""

    def cancel_batch_schedule(self, batch_id: str) -> bool:
        """取消批量调度"""
        try:
            cancelled_count = 0
            schedules_to_remove = []

            for schedule_name, config in self.scheduled_tasks.items():
                if (config.metadata and
                    config.metadata.get('batch_id') == batch_id):
                    schedules_to_remove.append(schedule_name)

            for schedule_name in schedules_to_remove:
                if self.remove_schedule(schedule_name):
                    cancelled_count += 1

            logger.info(f"批量调度已取消: {batch_id} ({cancelled_count} 个批次)")
            return cancelled_count > 0

        except Exception as e:
            logger.error(f"取消批量调度失败: {e}")
            return False

    def get_batch_schedule_status(self, batch_id: str) -> Dict[str, Any]:
        """获取批量调度状态"""
        try:
            batch_schedules = []
            completed_count = 0
            failed_count = 0
            running_count = 0

            for schedule_name, config in self.scheduled_tasks.items():
                if (config.metadata and
                    config.metadata.get('batch_id') == batch_id):

                    status = self.get_schedule_status(schedule_name)
                    batch_schedules.append(status)

                    # 统计状态
                    if not status['running']:
                        task_status = status.get('task_status')
                        if task_status == 'SUCCESS':
                            completed_count += 1
                        elif task_status in ['FAILURE', 'REVOKED']:
                            failed_count += 1
                    else:
                        running_count += 1

            return {
                'batch_id': batch_id,
                'total_batches': len(batch_schedules),
                'completed_batches': completed_count,
                'failed_batches': failed_count,
                'running_batches': running_count,
                'progress': int((completed_count + failed_count) / len(batch_schedules) * 100) if batch_schedules else 0,
                'schedules': batch_schedules
            }

        except Exception as e:
            logger.error(f"获取批量调度状态失败: {e}")
            return {}

    def schedule_recurring_task(
        self,
        name: str,
        task: str,
        schedule_type: ScheduleType,
        **kwargs
    ) -> bool:
        """
        调度周期性任务

        Args:
            name: 任务名称
            task: 任务名称
            schedule_type: 调度类型
            **kwargs: 其他参数

        Returns:
            是否调度成功
        """
        config = ScheduleConfig(
            name=name,
            task=task,
            schedule_type=schedule_type,
            **kwargs
        )

        return self.add_schedule(config)

    def create_celery_beat_schedule(self, config: ScheduleConfig) -> Dict[str, Any]:
        """创建Celery Beat调度配置"""
        schedule_config = {
            'task': config.task,
            'args': config.args,
            'kwargs': config.kwargs,
            'options': {
                'queue': config.queue,
                'priority': config.priority.value,
                'time_limit': config.timeout,
            }
        }

        # 根据调度类型设置schedule
        if config.schedule_type == ScheduleType.INTERVAL:
            schedule_config['schedule'] = timedelta(seconds=config.interval_seconds)
        elif config.schedule_type == ScheduleType.CRON:
            # 解析cron表达式
            cron_parts = config.cron_expression.split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                schedule_config['schedule'] = crontab(
                    minute=minute,
                    hour=hour,
                    day_of_month=day,
                    month_of_year=month,
                    day_of_week=day_of_week
                )

        return {config.name: schedule_config}

    def update_celery_beat_config(self):
        """更新Celery Beat配置"""
        try:
            beat_schedule = {}

            for config in self.scheduled_tasks.values():
                if config.enabled and config.schedule_type in [ScheduleType.INTERVAL, ScheduleType.CRON]:
                    schedule = self.create_celery_beat_schedule(config)
                    beat_schedule.update(schedule)

            # 更新Celery配置
            self.app.conf.beat_schedule = beat_schedule

            logger.info(f"Celery Beat配置已更新，包含 {len(beat_schedule)} 个调度任务")

        except Exception as e:
            logger.error(f"更新Celery Beat配置失败: {e}")

    def get_scheduler_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        try:
            stats = {
                'total_schedules': len(self.scheduled_tasks),
                'enabled_schedules': sum(1 for config in self.scheduled_tasks.values() if config.enabled),
                'disabled_schedules': sum(1 for config in self.scheduled_tasks.values() if not config.enabled),
                'running_schedules': len(self.running_schedules),
                'schedule_types': {},
                'queue_distribution': {}
            }

            # 统计调度类型分布
            for config in self.scheduled_tasks.values():
                schedule_type = config.schedule_type.value
                stats['schedule_types'][schedule_type] = stats['schedule_types'].get(schedule_type, 0) + 1

            # 统计队列分布
            for config in self.scheduled_tasks.values():
                queue = config.queue
                stats['queue_distribution'][queue] = stats['queue_distribution'].get(queue, 0) + 1

            return stats

        except Exception as e:
            logger.error(f"获取调度器统计失败: {e}")
            return {}


# 全局调度器实例
queue_scheduler = QueueScheduler()