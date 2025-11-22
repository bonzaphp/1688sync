# Base Task
# 基础任务类 - 定义任务的通用接口和行为

import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from celery import Task as CeleryTask
from celery.exceptions import Retry

from ..celery_app import celery_app
from ..task_manager import task_manager

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseTask(CeleryTask, ABC):
    """基础任务类"""

    def __init__(self):
        super().__init__()
        self.task_id = None
        self.start_time = None
        self.metadata = {}

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功回调"""
        try:
            logger.info(f"任务成功完成: {task_id}")

            # 更新任务管理器中的状态
            task_info = task_manager.get_task_status(task_id)
            if task_info:
                task_info.status = task_manager.TaskStatus.SUCCESS
                task_info.completed_at = datetime.utcnow()
                task_info.result = retval

        except Exception as e:
            logger.error(f"处理成功回调失败: {e}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败回调"""
        try:
            error_msg = f"任务失败: {task_id} - {str(exc)}"
            logger.error(error_msg)
            logger.error(f"错误详情: {traceback.format_exc()}")

            # 更新任务管理器中的状态
            task_info = task_manager.get_task_status(task_id)
            if task_info:
                task_info.status = task_manager.TaskStatus.FAILURE
                task_info.completed_at = datetime.utcnow()
                task_info.error = str(exc)

        except Exception as e:
            logger.error(f"处理失败回调失败: {e}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试回调"""
        try:
            logger.warning(f"任务重试: {task_id} - {str(exc)}")

            # 更新任务管理器中的状态
            task_info = task_manager.get_task_status(task_id)
            if task_info:
                task_info.status = task_manager.TaskStatus.RETRY

        except Exception as e:
            logger.error(f"处理重试回调失败: {e}")

    def update_progress(self, current: int, total: int, description: str = ""):
        """更新任务进度"""
        try:
            progress = {
                'current': current,
                'total': total,
                'percent': int((current / total) * 100) if total > 0 else 0,
                'description': description,
                'timestamp': datetime.utcnow().isoformat()
            }

            self.update_state(
                state='PROGRESS',
                meta=progress
            )

            # 更新任务管理器中的进度
            if self.request.id:
                task_manager.update_task_progress(self.request.id, progress)

        except Exception as e:
            logger.error(f"更新进度失败: {e}")

    def run(self, *args, **kwargs):
        """执行任务"""
        self.task_id = self.request.id
        self.start_time = datetime.utcnow()

        try:
            # 更新任务状态为开始
            task_info = task_manager.get_task_status(self.task_id)
            if task_info:
                task_info.status = task_manager.TaskStatus.STARTED
                task_info.started_at = self.start_time

            # 执行具体任务逻辑
            result = self.execute(*args, **kwargs)

            return result

        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            logger.error(f"错误详情: {traceback.format_exc()}")
            raise

    @abstractmethod
    def execute(self, *args, **kwargs) -> TaskResult:
        """执行具体任务逻辑 - 子类必须实现"""
        pass

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def prepare_resources(self, *args, **kwargs) -> bool:
        """准备资源"""
        return True

    def cleanup_resources(self):
        """清理资源"""
        pass

    def get_task_config(self) -> Dict[str, Any]:
        """获取任务配置"""
        return {
            'task_name': self.name,
            'task_id': self.task_id,
            'start_time': self.start_time,
            'metadata': self.metadata
        }


class TaskRegistry:
    """任务注册表"""

    def __init__(self):
        self.tasks: Dict[str, BaseTask] = {}

    def register(self, name: str, task_class: type):
        """注册任务"""
        if not issubclass(task_class, BaseTask):
            raise ValueError("任务类必须继承自BaseTask")

        # 创建任务实例并注册到Celery
        task_instance = task_class()
        task_instance.name = name

        # 注册到Celery应用
        celery_app.tasks.register(task_instance)

        # 保存到注册表
        self.tasks[name] = task_instance

        logger.info(f"任务已注册: {name}")

    def get_task(self, name: str) -> Optional[BaseTask]:
        """获取任务"""
        return self.tasks.get(name)

    def list_tasks(self) -> List[str]:
        """列出所有注册的任务"""
        return list(self.tasks.keys())

    def unregister(self, name: str) -> bool:
        """注销任务"""
        if name in self.tasks:
            del self.tasks[name]
            if name in celery_app.tasks:
                del celery_app.tasks[name]
            logger.info(f"任务已注销: {name}")
            return True
        return False


# 全局任务注册表
task_registry = TaskRegistry()


def register_task(name: str):
    """任务注册装饰器"""
    def decorator(task_class: type):
        task_registry.register(name, task_class)
        return task_class
    return decorator


class TaskChain:
    """任务链管理器"""

    def __init__(self):
        self.chains: Dict[str, List[str]] = {}

    def create_chain(self, chain_name: str, task_names: List[str]) -> str:
        """创建任务链"""
        # 验证所有任务都已注册
        for task_name in task_names:
            if task_name not in task_registry.tasks:
                raise ValueError(f"任务未注册: {task_name}")

        chain_id = f"{chain_name}_{datetime.utcnow().timestamp()}"
        self.chains[chain_id] = task_names

        logger.info(f"任务链已创建: {chain_id}")
        return chain_id

    def execute_chain(self, chain_id: str, initial_args: tuple = (), initial_kwargs: dict = None):
        """执行任务链"""
        if chain_id not in self.chains:
            raise ValueError(f"任务链不存在: {chain_id}")

        task_names = self.chains[chain_id]
        initial_kwargs = initial_kwargs or {}

        # 创建Celery任务链
        from celery import chain as celery_chain

        tasks = []
        for task_name in task_names:
            task = celery_app.tasks.get(task_name)
            if task:
                tasks.append(task.s(**initial_kwargs))

        if tasks:
            result = celery_chain(*tasks).apply_async(args=initial_args)
            logger.info(f"任务链已启动: {chain_id} (任务ID: {result.id})")
            return result.id

        return None


class TaskGroup:
    """任务组管理器"""

    def __init__(self):
        self.groups: Dict[str, List[str]] = {}

    def create_group(self, group_name: str, task_names: List[str]) -> str:
        """创建任务组"""
        # 验证所有任务都已注册
        for task_name in task_names:
            if task_name not in task_registry.tasks:
                raise ValueError(f"任务未注册: {task_name}")

        group_id = f"{group_name}_{datetime.utcnow().timestamp()}"
        self.groups[group_id] = task_names

        logger.info(f"任务组已创建: {group_id}")
        return group_id

    def execute_group(self, group_id: str, args_list: List[tuple] = None, kwargs_list: List[dict] = None):
        """执行任务组"""
        if group_id not in self.groups:
            raise ValueError(f"任务组不存在: {group_id}")

        task_names = self.groups[group_id]
        args_list = args_list or [() for _ in task_names]
        kwargs_list = kwargs_list or [{} for _ in task_names]

        if len(task_names) != len(args_list) or len(task_names) != len(kwargs_list):
            raise ValueError("任务名称列表与参数列表长度不匹配")

        # 创建Celery任务组
        from celery import group as celery_group

        tasks = []
        for i, task_name in enumerate(task_names):
            task = celery_app.tasks.get(task_name)
            if task:
                tasks.append(task.s(*args_list[i], **kwargs_list[i]))

        if tasks:
            result = celery_group(*tasks).apply_async()
            logger.info(f"任务组已启动: {group_id}")
            return result.id

        return None


# 全局任务链和任务组管理器
task_chain_manager = TaskChain()
task_group_manager = TaskGroup()