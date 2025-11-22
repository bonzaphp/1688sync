# Resume Manager
# 恢复管理器 - 提供任务断点续传的高级接口

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict

from .checkpoint_manager import checkpoint_manager, Checkpoint
from .task_recovery import task_recovery, RecoveryStrategy
from ..task_manager import task_manager, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class ResumeContext:
    """恢复上下文"""
    original_task_id: str
    task_name: str
    checkpoint_id: str
    resume_data: Dict[str, Any]
    progress_data: Dict[str, Any]
    metadata: Dict[str, Any]
    resume_timestamp: datetime


@dataclass
class ResumeResult:
    """恢复结果"""
    success: bool
    new_task_id: Optional[str] = None
    resumed_from_checkpoint: bool = False
    error_message: Optional[str] = None
    resume_context: Optional[ResumeContext] = None


class ResumeManager:
    """恢复管理器"""

    def __init__(self):
        self.resume_callbacks: List[Callable[[ResumeResult], None]] = []
        self.active_resumes: Dict[str, ResumeContext] = {}  # new_task_id -> ResumeContext

    def add_resume_callback(self, callback: Callable[[ResumeResult], None]):
        """添加恢复回调函数"""
        self.resume_callbacks.append(callback)

    def remove_resume_callback(self, callback: Callable[[ResumeResult], None]):
        """移除恢复回调函数"""
        if callback in self.resume_callbacks:
            self.resume_callbacks.remove(callback)

    def can_resume_task(self, task_id: str) -> bool:
        """检查任务是否可以恢复"""
        try:
            # 检查是否有检查点
            checkpoint = checkpoint_manager.get_latest_checkpoint(task_id)
            if not checkpoint:
                return False

            # 检查任务状态
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                return False

            # 只有失败、取消或超时的任务才能恢复
            resumable_statuses = [TaskStatus.FAILURE, TaskStatus.REVOKED]
            return task_info.status in resumable_statuses

        except Exception as e:
            logger.error(f"检查任务可恢复性失败: {e}")
            return False

    def get_resume_options(self, task_id: str) -> List[Dict[str, Any]]:
        """获取恢复选项"""
        try:
            if not self.can_resume_task(task_id):
                return []

            checkpoints = checkpoint_manager.list_checkpoints(task_id)
            options = []

            for checkpoint in checkpoints:
                option = {
                    'checkpoint_id': checkpoint.checkpoint_id,
                    'timestamp': checkpoint.timestamp.isoformat(),
                    'progress': checkpoint.progress_data,
                    'strategy': self._recommend_resume_strategy(checkpoint),
                    'estimated_recovery_time': self._estimate_recovery_time(checkpoint)
                }
                options.append(option)

            return options

        except Exception as e:
            logger.error(f"获取恢复选项失败: {e}")
            return []

    def _recommend_resume_strategy(self, checkpoint: Checkpoint) -> str:
        """推荐恢复策略"""
        # 根据检查点数据推荐策略
        progress = checkpoint.progress_data

        # 如果进度很高，建议从检查点恢复
        if progress.get('percent', 0) > 50:
            return 'resume_from_checkpoint'

        # 如果进度很低，建议重新开始
        elif progress.get('percent', 0) < 20:
            return 'restart'

        # 中等进度，根据任务类型决定
        task_type = checkpoint.task_name
        if 'crawler' in task_type or 'data_sync' in task_type:
            return 'resume_from_checkpoint'
        else:
            return 'restart'

    def _estimate_recovery_time(self, checkpoint: Checkpoint) -> int:
        """估算恢复时间（秒）"""
        try:
            progress = checkpoint.progress_data
            total = progress.get('total', 0)
            current = progress.get('current', 0)

            if total <= 0 or current >= total:
                return 0

            # 简单的线性估算
            remaining = total - current
            # 假设每秒处理10个项目
            estimated_seconds = remaining / 10

            return max(60, int(estimated_seconds))  # 至少1分钟

        except Exception:
            return 300  # 默认5分钟

    def resume_task(
        self,
        task_id: str,
        checkpoint_id: Optional[str] = None,
        strategy: str = 'auto',
        force_restart: bool = False
    ) -> ResumeResult:
        """
        恢复任务

        Args:
            task_id: 原任务ID
            checkpoint_id: 指定检查点ID（可选）
            strategy: 恢复策略 ('auto', 'checkpoint', 'restart')
            force_restart: 强制重新开始

        Returns:
            恢复结果
        """
        try:
            # 获取任务信息
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                return ResumeResult(
                    success=False,
                    error_message=f"任务不存在: {task_id}"
                )

            # 如果强制重新开始，直接重启
            if force_restart:
                return self._restart_task(task_info)

            # 检查是否可以恢复
            if not self.can_resume_task(task_id):
                return ResumeResult(
                    success=False,
                    error_message=f"任务无法恢复: {task_id}"
                )

            # 选择检查点
            if checkpoint_id:
                checkpoint = checkpoint_manager.load_checkpoint(checkpoint_id)
                if not checkpoint:
                    return ResumeResult(
                        success=False,
                        error_message=f"检查点不存在: {checkpoint_id}"
                    )
            else:
                checkpoint = checkpoint_manager.get_latest_checkpoint(task_id)
                if not checkpoint:
                    return ResumeResult(
                        success=False,
                        error_message=f"任务没有可用检查点: {task_id}"
                    )

            # 决定恢复策略
            if strategy == 'auto':
                strategy = self._recommend_resume_strategy(checkpoint)

            # 执行恢复
            if strategy == 'resume_from_checkpoint':
                return self._resume_from_checkpoint(task_info, checkpoint)
            elif strategy == 'restart':
                return self._restart_task(task_info)
            else:
                return ResumeResult(
                    success=False,
                    error_message=f"不支持的恢复策略: {strategy}"
                )

        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return ResumeResult(
                success=False,
                error_message=str(e)
            )

    def _resume_from_checkpoint(self, task_info, checkpoint: Checkpoint) -> ResumeResult:
        """从检查点恢复任务"""
        try:
            # 创建恢复上下文
            resume_context = ResumeContext(
                original_task_id=task_info.task_id,
                task_name=task_info.task_name,
                checkpoint_id=checkpoint.checkpoint_id,
                resume_data=checkpoint.state_data,
                progress_data=checkpoint.progress_data,
                metadata=checkpoint.metadata,
                resume_timestamp=datetime.utcnow()
            )

            # 准备恢复参数
            resume_kwargs = {
                'checkpoint_id': checkpoint.checkpoint_id,
                'original_task_id': task_info.task_id,
                'resume_timestamp': resume_context.resume_timestamp.isoformat(),
                **checkpoint.state_data
            }

            # 创建恢复任务
            new_task_id = task_manager.create_task(
                task_name=f"{task_info.task_name}_resume",
                kwargs=resume_kwargs,
                priority=task_info.priority,
                queue=task_info.metadata.get('queue', 'default'),
                metadata={
                    'resumed_from': task_info.task_id,
                    'checkpoint_id': checkpoint.checkpoint_id,
                    'resume_strategy': 'checkpoint'
                }
            )

            if new_task_id:
                # 记录活跃恢复
                self.active_resumes[new_task_id] = resume_context

                result = ResumeResult(
                    success=True,
                    new_task_id=new_task_id,
                    resumed_from_checkpoint=True,
                    resume_context=resume_context
                )

                # 调用回调函数
                self._call_resume_callbacks(result)

                return result
            else:
                return ResumeResult(
                    success=False,
                    error_message="创建恢复任务失败"
                )

        except Exception as e:
            logger.error(f"从检查点恢复失败: {e}")
            return ResumeResult(
                success=False,
                error_message=str(e)
            )

    def _restart_task(self, task_info) -> ResumeResult:
        """重新开始任务"""
        try:
            # 清理检查点
            checkpoint_manager.clear_task_checkpoints(task_info.task_id)

            # 创建恢复上下文
            resume_context = ResumeContext(
                original_task_id=task_info.task_id,
                task_name=task_info.task_name,
                checkpoint_id="",
                resume_data={},
                progress_data={},
                metadata={},
                resume_timestamp=datetime.utcnow()
            )

            # 创建新任务
            new_task_id = task_manager.create_task(
                task_name=task_info.task_name,
                args=task_info.metadata.get('args', ()),
                kwargs=task_info.metadata.get('kwargs', {}),
                priority=task_info.priority,
                queue=task_info.metadata.get('queue', 'default'),
                metadata={
                    'restarted_from': task_info.task_id,
                    'resume_strategy': 'restart'
                }
            )

            if new_task_id:
                # 记录活跃恢复
                self.active_resumes[new_task_id] = resume_context

                result = ResumeResult(
                    success=True,
                    new_task_id=new_task_id,
                    resumed_from_checkpoint=False,
                    resume_context=resume_context
                )

                # 调用回调函数
                self._call_resume_callbacks(result)

                return result
            else:
                return ResumeResult(
                    success=False,
                    error_message="创建重启任务失败"
                )

        except Exception as e:
            logger.error(f"重新开始任务失败: {e}")
            return ResumeResult(
                success=False,
                error_message=str(e)
            )

    def _call_resume_callbacks(self, result: ResumeResult):
        """调用恢复回调函数"""
        for callback in self.resume_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"恢复回调异常: {e}")

    def get_resume_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取恢复状态"""
        try:
            # 检查是否是恢复任务
            if task_id in self.active_resumes:
                resume_context = self.active_resumes[task_id]
                task_info = task_manager.get_task_status(task_id)

                return {
                    'is_resumed_task': True,
                    'original_task_id': resume_context.original_task_id,
                    'checkpoint_id': resume_context.checkpoint_id,
                    'resume_timestamp': resume_context.resume_timestamp.isoformat(),
                    'current_status': task_info.status.value if task_info else 'unknown',
                    'current_progress': task_info.progress if task_info else None
                }

            # 检查原任务是否有恢复任务
            for new_task_id, context in self.active_resumes.items():
                if context.original_task_id == task_id:
                    new_task_info = task_manager.get_task_status(new_task_id)
                    return {
                        'is_resumed_task': False,
                        'has_resumed_task': True,
                        'resumed_task_id': new_task_id,
                        'checkpoint_id': context.checkpoint_id,
                        'resume_timestamp': context.resume_timestamp.isoformat(),
                        'resumed_task_status': new_task_info.status.value if new_task_info else 'unknown',
                        'resumed_task_progress': new_task_info.progress if new_task_info else None
                    }

            return None

        except Exception as e:
            logger.error(f"获取恢复状态失败: {e}")
            return None

    def list_active_resumes(self) -> List[Dict[str, Any]]:
        """列出活跃的恢复任务"""
        try:
            active_resumes = []

            for new_task_id, context in self.active_resumes.items():
                task_info = task_manager.get_task_status(new_task_id)

                resume_info = {
                    'new_task_id': new_task_id,
                    'original_task_id': context.original_task_id,
                    'task_name': context.task_name,
                    'checkpoint_id': context.checkpoint_id,
                    'resume_timestamp': context.resume_timestamp.isoformat(),
                    'status': task_info.status.value if task_info else 'unknown',
                    'progress': task_info.progress if task_info else None
                }

                active_resumes.append(resume_info)

            return active_resumes

        except Exception as e:
            logger.error(f"列出活跃恢复失败: {e}")
            return []

    def cleanup_completed_resumes(self):
        """清理已完成的恢复任务"""
        try:
            completed_tasks = []

            for new_task_id, context in self.active_resumes.items():
                task_info = task_manager.get_task_status(new_task_id)
                if task_info and task_info.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE]:
                    completed_tasks.append(new_task_id)

            for task_id in completed_tasks:
                del self.active_resumes[task_id]

            if completed_tasks:
                logger.info(f"清理了 {len(completed_tasks)} 个已完成的恢复任务")

        except Exception as e:
            logger.error(f"清理恢复任务失败: {e}")

    def create_manual_resume_point(
        self,
        task_id: str,
        progress_data: Dict[str, Any],
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建手动恢复点"""
        try:
            task_info = task_manager.get_task_status(task_id)
            if not task_info:
                raise ValueError(f"任务不存在: {task_id}")

            checkpoint_id = checkpoint_manager.create_checkpoint(
                task_id=task_id,
                task_name=task_info.task_name,
                progress_data=progress_data,
                state_data=state_data,
                metadata=metadata or {'manual': True}
            )

            logger.info(f"已创建手动恢复点: {checkpoint_id}")
            return checkpoint_id

        except Exception as e:
            logger.error(f"创建手动恢复点失败: {e}")
            raise

    def get_resume_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        try:
            total_resumes = len(self.active_resumes)
            completed_resumes = 0
            failed_resumes = 0

            for new_task_id, context in self.active_resumes.items():
                task_info = task_manager.get_task_status(new_task_id)
                if task_info:
                    if task_info.status == TaskStatus.SUCCESS:
                        completed_resumes += 1
                    elif task_info.status == TaskStatus.FAILURE:
                        failed_resumes += 1

            # 统计检查点使用情况
            checkpoint_resumes = sum(
                1 for context in self.active_resumes.values()
                if context.checkpoint_id
            )

            return {
                'active_resumes': total_resumes,
                'completed_resumes': completed_resumes,
                'failed_resumes': failed_resumes,
                'checkpoint_resumes': checkpoint_resumes,
                'restart_resumes': total_resumes - checkpoint_resumes,
                'success_rate': completed_resumes / total_resumes if total_resumes > 0 else 0
            }

        except Exception as e:
            logger.error(f"获取恢复统计失败: {e}")
            return {}

    def export_resume_report(self, task_id: str) -> Dict[str, Any]:
        """导出恢复报告"""
        try:
            # 获取恢复历史
            recovery_history = task_recovery.get_recovery_history(task_id)

            # 获取检查点信息
            checkpoints = checkpoint_manager.list_checkpoints(task_id)

            # 获取恢复状态
            resume_status = self.get_resume_status(task_id)

            report = {
                'task_id': task_id,
                'report_timestamp': datetime.utcnow().isoformat(),
                'can_resume': self.can_resume_task(task_id),
                'resume_options': self.get_resume_options(task_id),
                'checkpoints': [asdict(cp) for cp in checkpoints],
                'recovery_history': [asdict(attempt) for attempt in recovery_history],
                'resume_status': resume_status,
                'statistics': {
                    'total_checkpoints': len(checkpoints),
                    'recovery_attempts': len(recovery_history),
                    'successful_recoveries': len([a for a in recovery_history if a.success])
                }
            }

            return report

        except Exception as e:
            logger.error(f"导出恢复报告失败: {e}")
            return {'error': str(e)}


# 全局恢复管理器实例
resume_manager = ResumeManager()