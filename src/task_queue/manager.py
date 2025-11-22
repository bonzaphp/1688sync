# Queue Manager
# 队列管理器 - 统一的队列管理接口

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .celery_app import celery_app, celery_manager
from .task_manager import task_manager
from .scheduler import queue_scheduler, ScheduleConfig, ScheduleType
from .monitors.progress_monitor import progress_monitor
from .monitors.status_monitor import status_monitor
from .recovery.checkpoint_manager import checkpoint_manager
from .recovery.task_recovery import task_recovery
from .recovery.resume_manager import resume_manager

logger = logging.getLogger(__name__)


class QueueManager:
    """队列管理器 - 统一管理所有队列相关功能"""

    def __init__(self):
        self.celery_app = celery_app
        self.task_manager = task_manager
        self.scheduler = queue_scheduler
        self.progress_monitor = progress_monitor
        self.status_monitor = status_monitor
        self.checkpoint_manager = checkpoint_manager
        self.task_recovery = task_recovery
        self.resume_manager = resume_manager

        self._initialized = False

    def initialize(self):
        """初始化队列管理器"""
        if self._initialized:
            return

        try:
            # 启动监控
            self.progress_monitor.start_monitoring()
            self.status_monitor.start_monitoring()

            # 更新调度器配置
            self.scheduler.update_celery_beat_config()

            self._initialized = True
            logger.info("队列管理器初始化完成")

        except Exception as e:
            logger.error(f"队列管理器初始化失败: {e}")
            raise

    def shutdown(self):
        """关闭队列管理器"""
        try:
            # 停止监控
            self.progress_monitor.stop_monitoring()
            self.status_monitor.stop_monitoring()

            self._initialized = False
            logger.info("队列管理器已关闭")

        except Exception as e:
            logger.error(f"队列管理器关闭失败: {e}")

    # 任务管理方法
    def create_task(self, task_name: str, **kwargs) -> str:
        """创建任务"""
        return self.task_manager.create_task(task_name, **kwargs)

    def get_task_status(self, task_id: str):
        """获取任务状态"""
        return self.task_manager.get_task_status(task_id)

    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """取消任务"""
        return self.task_manager.cancel_task(task_id, terminate)

    def get_active_tasks(self):
        """获取活跃任务"""
        return self.task_manager.get_active_tasks()

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计"""
        return self.task_manager.get_task_statistics()

    # 调度管理方法
    def add_schedule(self, config: ScheduleConfig) -> bool:
        """添加调度任务"""
        return self.scheduler.add_schedule(config)

    def remove_schedule(self, schedule_name: str) -> bool:
        """移除调度任务"""
        return self.scheduler.remove_schedule(schedule_name)

    def list_schedules(self) -> List[Dict[str, Any]]:
        """列出调度任务"""
        return self.scheduler.list_schedules()

    def create_batch_schedule(self, base_config: ScheduleConfig, items: List[Any], **kwargs) -> str:
        """创建批量调度"""
        return self.scheduler.create_batch_schedule(base_config, items, **kwargs)

    # 监控方法
    def get_system_health(self):
        """获取系统健康状态"""
        return self.status_monitor.get_current_health()

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        return self.status_monitor.get_health_summary()

    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return self.progress_monitor.get_progress_summary()

    def get_running_tasks_progress(self) -> List[Dict[str, Any]]:
        """获取正在运行任务的进度"""
        return self.progress_monitor.get_running_tasks_progress()

    # 恢复和检查点方法
    def create_checkpoint(self, task_id: str, progress_data: Dict[str, Any], state_data: Dict[str, Any]) -> str:
        """创建检查点"""
        return self.checkpoint_manager.create_checkpoint(
            task_id=task_id,
            task_name="",  # 将从任务信息中获取
            progress_data=progress_data,
            state_data=state_data
        )

    def resume_task(self, task_id: str, **kwargs):
        """恢复任务"""
        return self.resume_manager.resume_task(task_id, **kwargs)

    def get_resume_options(self, task_id: str) -> List[Dict[str, Any]]:
        """获取恢复选项"""
        return self.resume_manager.get_resume_options(task_id)

    # Worker管理方法
    def get_worker_stats(self) -> Dict[str, Any]:
        """获取Worker统计"""
        return celery_manager.get_worker_stats()

    def get_active_tasks_by_worker(self) -> Dict[str, Any]:
        """获取每个Worker的活跃任务"""
        return celery_manager.get_active_tasks()

    def scale_workers(self, worker_name: str, pool_size: int) -> bool:
        """调整Worker池大小"""
        return celery_manager.scale_workers(worker_name, pool_size)

    # 批量操作方法
    def create_batch_task(self, task_name: str, items: List[Any], **kwargs) -> List[str]:
        """创建批量任务"""
        return self.task_manager.create_batch_task(task_name, items, **kwargs)

    def cancel_batch_schedule(self, batch_id: str) -> bool:
        """取消批量调度"""
        return self.scheduler.cancel_batch_schedule(batch_id)

    # 维护方法
    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        try:
            # 清理旧任务记录
            self.task_manager.cleanup_old_tasks(days)

            # 清理旧检查点
            self.checkpoint_manager.cleanup_old_checkpoints(days)

            # 清理旧恢复历史
            self.task_recovery.clear_old_recovery_history(days)

            # 清理已完成的恢复任务
            self.resume_manager.cleanup_completed_resumes()

            logger.info(f"清理了 {days} 天前的旧数据")

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")

    # 报告方法
    def generate_system_report(self) -> Dict[str, Any]:
        """生成系统报告"""
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'system_health': self.get_health_summary(),
                'task_statistics': self.get_task_statistics(),
                'progress_summary': self.get_progress_summary(),
                'worker_stats': self.get_worker_stats(),
                'scheduler_stats': self.scheduler.get_scheduler_statistics(),
                'checkpoint_stats': self.checkpoint_manager.get_checkpoint_statistics(),
                'recovery_stats': self.task_recovery.get_recovery_statistics(),
                'resume_stats': self.resume_manager.get_resume_statistics(),
                'active_schedules': len(self.list_schedules()),
                'running_tasks': len(self.get_running_tasks_progress())
            }

            return report

        except Exception as e:
            logger.error(f"生成系统报告失败: {e}")
            return {'error': str(e)}

    # 健康检查方法
    def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_status = {
                'overall': 'healthy',
                'components': {},
                'timestamp': datetime.utcnow().isoformat()
            }

            # 检查Celery连接
            try:
                celery_stats = self.get_worker_stats()
                health_status['components']['celery'] = {
                    'status': 'healthy' if celery_stats else 'warning',
                    'message': f'{len(celery_stats)} workers active' if celery_stats else 'No workers found'
                }
            except Exception as e:
                health_status['components']['celery'] = {
                    'status': 'error',
                    'message': str(e)
                }

            # 检查Redis连接（通过Celery）
            try:
                self.celery_app.control.inspect().stats()
                health_status['components']['redis'] = {
                    'status': 'healthy',
                    'message': 'Connection OK'
                }
            except Exception as e:
                health_status['components']['redis'] = {
                    'status': 'error',
                    'message': str(e)
                }

            # 检查监控状态
            health_status['components']['progress_monitor'] = {
                'status': 'healthy' if self.progress_monitor.monitoring_active else 'warning',
                'message': 'Active' if self.progress_monitor.monitoring_active else 'Inactive'
            }

            health_status['components']['status_monitor'] = {
                'status': 'healthy' if self.status_monitor.monitoring_active else 'warning',
                'message': 'Active' if self.status_monitor.monitoring_active else 'Inactive'
            }

            # 检查系统健康状态
            system_health = self.get_system_health()
            if system_health:
                health_status['components']['system_health'] = {
                    'status': system_health.overall_status.value,
                    'message': f'Error rate: {system_health.error_rate:.2%}'
                }

            # 确定整体状态
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if 'error' in component_statuses:
                health_status['overall'] = 'critical'
            elif 'warning' in component_statuses:
                health_status['overall'] = 'warning'

            return health_status

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                'overall': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    # 配置方法
    def update_thresholds(self, thresholds: Dict[str, float]):
        """更新监控阈值"""
        self.status_monitor.update_thresholds(thresholds)

    def get_configuration(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'celery_broker_url': self.celery_app.conf.broker_url,
            'celery_result_backend': self.celery_app.conf.result_backend,
            'task_time_limit': self.celery_app.conf.task_time_limit,
            'task_soft_time_limit': self.celery_app.conf.task_soft_time_limit,
            'worker_prefetch_multiplier': self.celery_app.conf.worker_prefetch_multiplier,
            'monitoring': {
                'progress_monitor_active': self.progress_monitor.monitoring_active,
                'status_monitor_active': self.status_monitor.monitoring_active,
                'update_interval': self.status_monitor.check_interval
            },
            'thresholds': self.status_monitor.thresholds,
            'checkpoint': {
                'max_checkpoints': self.checkpoint_manager.max_checkpoints,
                'checkpoint_dir': str(self.checkpoint_manager.checkpoint_dir)
            }
        }


# 全局队列管理器实例
queue_manager = QueueManager()