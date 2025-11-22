# Task Recovery
# 任务恢复管理器 - 处理任务失败后的恢复和重试逻辑

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .checkpoint_manager import checkpoint_manager, Checkpoint
from ..task_manager import task_manager, TaskStatus, TaskPriority
from ..celery_app import celery_manager

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    RETRY = "retry"
    RESUME = "resume"
    RESTART = "restart"
    SKIP = "skip"
    MANUAL = "manual"


@dataclass
class RecoveryConfig:
    """恢复配置"""
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    backoff_factor: float = 2.0
    max_retry_delay: int = 3600  # 1小时
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    use_checkpoint: bool = True
    retry_on_exceptions: List[str] = None
    stop_on_exceptions: List[str] = None

    def __post_init__(self):
        if self.retry_on_exceptions is None:
            self.retry_on_exceptions = [
                'ConnectionError',
                'TimeoutError',
                'NetworkError',
                'TemporaryError'
            ]
        if self.stop_on_exceptions is None:
            self.stop_on_exceptions = [
                'AuthenticationError',
                'PermissionError',
                'InvalidDataError'
            ]


@dataclass
class RecoveryAttempt:
    """恢复尝试记录"""
    attempt_id: str
    task_id: str
    original_task_id: str
    strategy: RecoveryStrategy
    timestamp: datetime
    error_message: str
    success: bool
    next_retry_time: Optional[datetime] = None
    checkpoint_used: bool = False


class TaskRecovery:
    """任务恢复管理器"""

    def __init__(self):
        self.recovery_configs: Dict[str, RecoveryConfig] = {}
        self.recovery_history: Dict[str, List[RecoveryAttempt]] = {}
        self.pending_recoveries: Dict[str, RecoveryAttempt] = {}
        self.recovery_callbacks: List[Callable[[RecoveryAttempt], None]] = []

        # 设置默认恢复配置
        self._setup_default_configs()

    def _setup_default_configs(self):
        """设置默认恢复配置"""
        # 爬虫任务配置
        self.recovery_configs['crawler'] = RecoveryConfig(
            max_retries=5,
            retry_delay=30,
            backoff_factor=1.5,
            recovery_strategy=RecoveryStrategy.RESUME,
            use_checkpoint=True
        )

        # 图片处理任务配置
        self.recovery_configs['image_processing'] = RecoveryConfig(
            max_retries=3,
            retry_delay=60,
            backoff_factor=2.0,
            recovery_strategy=RecoveryStrategy.RESTART,
            use_checkpoint=False
        )

        # 数据同步任务配置
        self.recovery_configs['data_sync'] = RecoveryConfig(
            max_retries=10,
            retry_delay=120,
            backoff_factor=2.0,
            recovery_strategy=RecoveryStrategy.RESUME,
            use_checkpoint=True
        )

        # 批量处理任务配置
        self.recovery_configs['batch_processing'] = RecoveryConfig(
            max_retries=3,
            retry_delay=300,
            backoff_factor=2.0,
            recovery_strategy=RecoveryStrategy.RESTART,
            use_checkpoint=True
        )

    def register_recovery_config(self, task_type: str, config: RecoveryConfig):
        """注册任务类型的恢复配置"""
        self.recovery_configs[task_type] = config
        logger.info(f"已注册 {task_type} 的恢复配置")

    def handle_task_failure(self, task_id: str, error_message: str, exception_type: str = None) -> bool:
        """
        处理任务失败

        Args:
            task_id: 任务ID
            error_message: 错误消息
            exception_type: 异常类型

        Returns:
            是否启动了恢复流程
        """
        try:
            # 获取任务信息
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                logger.error(f"任务不存在: {task_id}")
                return False

            # 确定任务类型
            task_type = self._get_task_type(task_info.task_name)
            config = self.recovery_configs.get(task_type, RecoveryConfig())

            # 检查是否应该停止恢复
            if self._should_stop_recovery(exception_type, config):
                logger.info(f"任务 {task_id} 触发停止条件，跳过恢复")
                return False

            # 检查重试次数
            if not self._can_retry(task_id, config):
                logger.info(f"任务 {task_id} 已达到最大重试次数")
                return False

            # 选择恢复策略
            strategy = self._select_recovery_strategy(task_info, config, exception_type)

            # 执行恢复
            recovery_attempt = self._execute_recovery(task_id, strategy, error_message, config)

            if recovery_attempt:
                # 记录恢复尝试
                self._record_recovery_attempt(recovery_attempt)

                # 调用回调函数
                for callback in self.recovery_callbacks:
                    try:
                        callback(recovery_attempt)
                    except Exception as e:
                        logger.error(f"恢复回调异常: {e}")

                return True

            return False

        except Exception as e:
            logger.error(f"处理任务失败异常: {e}")
            return False

    def _get_task_type(self, task_name: str) -> str:
        """获取任务类型"""
        if 'crawler' in task_name:
            return 'crawler'
        elif 'image_processing' in task_name:
            return 'image_processing'
        elif 'data_sync' in task_name:
            return 'data_sync'
        elif 'batch_processing' in task_name:
            return 'batch_processing'
        else:
            return 'default'

    def _should_stop_recovery(self, exception_type: str, config: RecoveryConfig) -> bool:
        """检查是否应该停止恢复"""
        if not exception_type:
            return False

        return any(stop_type in exception_type for stop_type in config.stop_on_exceptions)

    def _can_retry(self, task_id: str, config: RecoveryConfig) -> bool:
        """检查是否可以重试"""
        # 获取历史恢复记录
        history = self.recovery_history.get(task_id, [])
        retry_count = len([attempt for attempt in history if attempt.strategy != RecoveryStrategy.SKIP])

        return retry_count < config.max_retries

    def _select_recovery_strategy(
        self, task_info, config: RecoveryConfig, exception_type: str
    ) -> RecoveryStrategy:
        """选择恢复策略"""
        # 检查是否有检查点可用
        has_checkpoint = bool(checkpoint_manager.get_latest_checkpoint(task_info.task_id))

        # 根据配置和条件选择策略
        if config.recovery_strategy == RecoveryStrategy.MANUAL:
            return RecoveryStrategy.MANUAL
        elif config.use_checkpoint and has_checkpoint:
            return RecoveryStrategy.RESUME
        elif exception_type and any(retry_type in exception_type for retry_type in config.retry_on_exceptions):
            return RecoveryStrategy.RETRY
        else:
            return config.recovery_strategy

    def _execute_recovery(
        self, task_id: str, strategy: RecoveryStrategy, error_message: str, config: RecoveryConfig
    ) -> Optional[RecoveryAttempt]:
        """执行恢复"""
        try:
            attempt_id = f"recovery_{task_id}_{datetime.utcnow().timestamp()}"
            success = False
            next_retry_time = None
            checkpoint_used = False

            if strategy == RecoveryStrategy.RESUME:
                # 从检查点恢复
                success, checkpoint_used = self._resume_from_checkpoint(task_id)

            elif strategy == RecoveryStrategy.RETRY:
                # 简单重试
                success = self._retry_task(task_id, config.retry_delay)
                if success:
                    next_retry_time = datetime.utcnow() + timedelta(seconds=config.retry_delay)

            elif strategy == RecoveryStrategy.RESTART:
                # 重新开始
                success = self._restart_task(task_id)

            elif strategy == RecoveryStrategy.SKIP:
                # 跳过任务
                success = self._skip_task(task_id)

            recovery_attempt = RecoveryAttempt(
                attempt_id=attempt_id,
                task_id=task_id,
                original_task_id=task_id,
                strategy=strategy,
                timestamp=datetime.utcnow(),
                error_message=error_message,
                success=success,
                next_retry_time=next_retry_time,
                checkpoint_used=checkpoint_used
            )

            return recovery_attempt

        except Exception as e:
            logger.error(f"执行恢复失败: {e}")
            return None

    def _resume_from_checkpoint(self, task_id: str) -> tuple[bool, bool]:
        """从检查点恢复"""
        try:
            checkpoint = checkpoint_manager.get_latest_checkpoint(task_id)
            if not checkpoint:
                logger.warning(f"任务 {task_id} 没有可用检查点")
                return False, False

            # 获取原始任务信息
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                return False, False

            # 创建恢复任务
            new_task_id = task_manager.create_task(
                task_name=f"{task_info.task_name}_resume",
                kwargs={
                    'checkpoint_id': checkpoint.checkpoint_id,
                    'original_task_id': task_id,
                    **checkpoint.state_data
                },
                priority=task_info.priority,
                queue=task_info.metadata.get('queue', 'default')
            )

            if new_task_id:
                logger.info(f"任务 {task_id} 已从检查点恢复，新任务ID: {new_task_id}")
                return True, True

            return False, False

        except Exception as e:
            logger.error(f"从检查点恢复失败: {e}")
            return False, False

    def _retry_task(self, task_id: str, delay: int) -> bool:
        """重试任务"""
        try:
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                return False

            # 创建重试任务
            new_task_id = task_manager.create_task(
                task_name=task_info.task_name,
                args=task_info.metadata.get('args', ()),
                kwargs=task_info.metadata.get('kwargs', {}),
                priority=task_info.priority,
                queue=task_info.metadata.get('queue', 'default'),
                countdown=delay
            )

            if new_task_id:
                logger.info(f"任务 {task_id} 已安排重试，新任务ID: {new_task_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"重试任务失败: {e}")
            return False

    def _restart_task(self, task_id: str) -> bool:
        """重新开始任务"""
        try:
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                return False

            # 清理检查点
            checkpoint_manager.clear_task_checkpoints(task_id)

            # 创建新任务
            new_task_id = task_manager.create_task(
                task_name=task_info.task_name,
                args=task_info.metadata.get('args', ()),
                kwargs=task_info.metadata.get('kwargs', {}),
                priority=task_info.priority,
                queue=task_info.metadata.get('queue', 'default')
            )

            if new_task_id:
                logger.info(f"任务 {task_id} 已重新开始，新任务ID: {new_task_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"重新开始任务失败: {e}")
            return False

    def _skip_task(self, task_id: str) -> bool:
        """跳过任务"""
        try:
            # 标记任务为跳过状态
            task_info = task_manager.get_task_status(task_id)
            if task_info:
                task_info.status = TaskStatus.REVOKED
                logger.info(f"任务 {task_id} 已跳过")
                return True

            return False

        except Exception as e:
            logger.error(f"跳过任务失败: {e}")
            return False

    def _record_recovery_attempt(self, attempt: RecoveryAttempt):
        """记录恢复尝试"""
        if attempt.original_task_id not in self.recovery_history:
            self.recovery_history[attempt.original_task_id] = []

        self.recovery_history[attempt.original_task_id].append(attempt)

        # 如果需要后续重试，添加到待处理列表
        if attempt.next_retry_time:
            self.pending_recoveries[attempt.attempt_id] = attempt

    def get_recovery_history(self, task_id: str) -> List[RecoveryAttempt]:
        """获取任务的恢复历史"""
        return self.recovery_history.get(task_id, [])

    def get_pending_recoveries(self) -> List[RecoveryAttempt]:
        """获取待处理的恢复"""
        return list(self.pending_recoveries.values())

    def process_pending_recoveries(self):
        """处理待处理的恢复"""
        current_time = datetime.utcnow()
        processed_attempts = []

        for attempt_id, attempt in self.pending_recoveries.items():
            if attempt.next_retry_time and attempt.next_retry_time <= current_time:
                # 执行重试
                success = self._retry_task(attempt.task_id, 0)
                if success:
                    processed_attempts.append(attempt_id)

        # 清理已处理的恢复
        for attempt_id in processed_attempts:
            del self.pending_recoveries[attempt_id]

        if processed_attempts:
            logger.info(f"处理了 {len(processed_attempts)} 个待处理恢复")

    def add_recovery_callback(self, callback: Callable[[RecoveryAttempt], None]):
        """添加恢复回调函数"""
        self.recovery_callbacks.append(callback)

    def remove_recovery_callback(self, callback: Callable[[RecoveryAttempt], None]):
        """移除恢复回调函数"""
        if callback in self.recovery_callbacks:
            self.recovery_callbacks.remove(callback)

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        try:
            total_attempts = sum(len(attempts) for attempts in self.recovery_history.values())
            successful_recoveries = sum(
                len([a for a in attempts if a.success])
                for attempts in self.recovery_history.values()
            )
            failed_recoveries = total_attempts - successful_recoveries

            # 按策略统计
            strategy_counts = {}
            for attempts in self.recovery_history.values():
                for attempt in attempts:
                    strategy = attempt.strategy.value
                    strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

            return {
                'total_tasks_with_recovery': len(self.recovery_history),
                'total_recovery_attempts': total_attempts,
                'successful_recoveries': successful_recoveries,
                'failed_recoveries': failed_recoveries,
                'success_rate': successful_recoveries / total_attempts if total_attempts > 0 else 0,
                'pending_recoveries': len(self.pending_recoveries),
                'strategy_distribution': strategy_counts,
                'configured_task_types': list(self.recovery_configs.keys())
            }

        except Exception as e:
            logger.error(f"获取恢复统计失败: {e}")
            return {}

    def clear_old_recovery_history(self, days: int = 30):
        """清理旧的恢复历史"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            removed_count = 0

            for task_id in list(self.recovery_history.keys()):
                attempts = self.recovery_history[task_id]
                recent_attempts = [
                    attempt for attempt in attempts
                    if attempt.timestamp > cutoff_time
                ]

                if len(recent_attempts) != len(attempts):
                    self.recovery_history[task_id] = recent_attempts
                    removed_count += len(attempts) - len(recent_attempts)

                    # 如果没有 recent attempts，删除条目
                    if not recent_attempts:
                        del self.recovery_history[task_id]

            logger.info(f"清理了 {removed_count} 条旧恢复记录")

        except Exception as e:
            logger.error(f"清理恢复历史失败: {e}")


# 全局任务恢复管理器实例
task_recovery = TaskRecovery()