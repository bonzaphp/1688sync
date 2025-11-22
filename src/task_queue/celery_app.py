# Celery Application Configuration
# Celery应用配置和连接管理

import os
import logging
from celery import Celery
from kombu import Queue
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Celery配置
CELERY_CONFIG = {
    'broker_url': os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30分钟
    'task_soft_time_limit': 25 * 60,  # 25分钟
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'worker_disable_rate_limits': False,
    'task_default_queue': 'default',
    'task_queues': (
        Queue('default', routing_key='default'),
        Queue('crawler', routing_key='crawler'),
        Queue('image_processing', routing_key='image_processing'),
        Queue('data_sync', routing_key='data_sync'),
        Queue('batch_processing', routing_key='batch_processing'),
    ),
    'task_routes': {
        'src.queue.tasks.crawler.*': {'queue': 'crawler'},
        'src.queue.tasks.image_processing.*': {'queue': 'image_processing'},
        'src.queue.tasks.data_sync.*': {'queue': 'data_sync'},
        'src.queue.tasks.batch_processing.*': {'queue': 'batch_processing'},
    },
    'task_default_exchange': 'tasks',
    'task_default_exchange_type': 'direct',
    'task_default_routing_key': 'default',
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    'beat_scheduler': 'src.queue.schedulers.DatabaseScheduler',
    'beat_schedule_filename': os.path.join(os.getcwd(), 'celerybeat-schedule'),
}

# 创建Celery应用
celery_app = Celery('1688sync')
celery_app.config_from_object(CELERY_CONFIG)


class CeleryManager:
    """Celery管理器"""

    def __init__(self):
        self.app = celery_app
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def get_active_tasks(self) -> Dict[str, Any]:
        """获取活跃任务"""
        try:
            inspect = self.app.control.inspect()
            active = inspect.active()
            return active or {}
        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            return {}

    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """获取已调度任务"""
        try:
            inspect = self.app.control.inspect()
            scheduled = inspect.scheduled()
            return scheduled or {}
        except Exception as e:
            logger.error(f"获取已调度任务失败: {e}")
            return {}

    def get_reserved_tasks(self) -> Dict[str, Any]:
        """获取预留任务"""
        try:
            inspect = self.app.control.inspect()
            reserved = inspect.reserved()
            return reserved or {}
        except Exception as e:
            logger.error(f"获取预留任务失败: {e}")
            return {}

    def revoke_task(self, task_id: str, terminate: bool = False) -> bool:
        """撤销任务"""
        try:
            self.app.control.revoke(task_id, terminate=terminate)
            logger.info(f"任务 {task_id} 已撤销")
            return True
        except Exception as e:
            logger.error(f"撤销任务失败: {e}")
            return False

    def get_worker_stats(self) -> Dict[str, Any]:
        """获取Worker统计信息"""
        try:
            inspect = self.app.control.inspect()
            stats = inspect.stats()
            return stats or {}
        except Exception as e:
            logger.error(f"获取Worker统计失败: {e}")
            return {}

    def get_worker_pool_info(self) -> Dict[str, Any]:
        """获取Worker池信息"""
        try:
            inspect = self.app.control.inspect()
            pool_info = inspect.active()
            return pool_info or {}
        except Exception as e:
            logger.error(f"获取Worker池信息失败: {e}")
            return {}

    def scale_workers(self, worker_name: str, pool_size: int) -> bool:
        """调整Worker池大小"""
        try:
            self.app.control.pool_grow(pool_size, reply=True, destination=[worker_name])
            logger.info(f"Worker {worker_name} 池大小已调整为 {pool_size}")
            return True
        except Exception as e:
            logger.error(f"调整Worker池大小失败: {e}")
            return False

    def enable_events(self):
        """启用事件监控"""
        try:
            self.app.control.enable_events()
            logger.info("事件监控已启用")
        except Exception as e:
            logger.error(f"启用事件监控失败: {e}")

    def disable_events(self):
        """禁用事件监控"""
        try:
            self.app.control.disable_events()
            logger.info("事件监控已禁用")
        except Exception as e:
            logger.error(f"禁用事件监控失败: {e}")


# 全局Celery管理器实例
celery_manager = CeleryManager()


# 健康检查任务
@celery_app.task(bind=True, name='src.queue.tasks.health_check')
def health_check(self):
    """健康检查任务"""
    try:
        return {
            'status': 'healthy',
            'worker': self.request.hostname,
            'timestamp': self.request.timestamp
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise


# 心跳任务
@celery_app.task(bind=True, name='src.queue.tasks.heartbeat')
def heartbeat(self):
    """心跳任务"""
    try:
        return {
            'worker': self.request.hostname,
            'task_id': self.request.id,
            'timestamp': self.request.timestamp
        }
    except Exception as e:
        logger.error(f"心跳任务失败: {e}")
        raise


if __name__ == '__main__':
    # 启动Celery worker
    celery_app.start()