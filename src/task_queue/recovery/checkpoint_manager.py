# Checkpoint Manager
# 检查点管理器 - 实现任务断点续传的检查点保存和恢复

import json
import os
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from ...database.connection import get_db_session
from ...models.sync_record import SyncRecord

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """检查点数据结构"""
    task_id: str
    task_name: str
    checkpoint_id: str
    timestamp: datetime
    progress_data: Dict[str, Any]
    state_data: Dict[str, Any]
    metadata: Dict[str, Any]
    checksum: str


class CheckpointManager:
    """检查点管理器"""

    def __init__(self, checkpoint_dir: str = "checkpoints", max_checkpoints: int = 100):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_checkpoints = max_checkpoints
        self.checkpoint_index: Dict[str, List[str]] = {}  # task_id -> [checkpoint_ids]

        # 确保检查点目录存在
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 加载现有检查点索引
        self._load_checkpoint_index()

    def _load_checkpoint_index(self):
        """加载检查点索引"""
        try:
            index_file = self.checkpoint_dir / "index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.checkpoint_index = json.load(f)
        except Exception as e:
            logger.error(f"加载检查点索引失败: {e}")
            self.checkpoint_index = {}

    def _save_checkpoint_index(self):
        """保存检查点索引"""
        try:
            index_file = self.checkpoint_dir / "index.json"
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint_index, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存检查点索引失败: {e}")

    def create_checkpoint(
        self,
        task_id: str,
        task_name: str,
        progress_data: Dict[str, Any],
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建检查点

        Args:
            task_id: 任务ID
            task_name: 任务名称
            progress_data: 进度数据
            state_data: 状态数据
            metadata: 元数据

        Returns:
            检查点ID
        """
        try:
            # 生成检查点ID
            checkpoint_id = f"{task_id}_{datetime.utcnow().timestamp()}"

            # 创建检查点对象
            checkpoint = Checkpoint(
                task_id=task_id,
                task_name=task_name,
                checkpoint_id=checkpoint_id,
                timestamp=datetime.utcnow(),
                progress_data=progress_data,
                state_data=state_data,
                metadata=metadata or {},
                checksum=""
            )

            # 计算校验和
            checkpoint.checksum = self._calculate_checksum(checkpoint)

            # 保存检查点文件
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(checkpoint), f, indent=2, default=str)

            # 更新索引
            if task_id not in self.checkpoint_index:
                self.checkpoint_index[task_id] = []

            self.checkpoint_index[task_id].append(checkpoint_id)

            # 清理旧检查点
            self._cleanup_old_checkpoints(task_id)

            # 保存索引
            self._save_checkpoint_index()

            # 保存到数据库
            self._save_checkpoint_to_db(checkpoint)

            logger.info(f"检查点已创建: {checkpoint_id}")
            return checkpoint_id

        except Exception as e:
            logger.error(f"创建检查点失败: {e}")
            raise

    def _calculate_checksum(self, checkpoint: Checkpoint) -> str:
        """计算检查点校验和"""
        try:
            # 创建用于计算校验和的数据
            checksum_data = {
                'task_id': checkpoint.task_id,
                'task_name': checkpoint.task_name,
                'timestamp': checkpoint.timestamp.isoformat(),
                'progress_data': checkpoint.progress_data,
                'state_data': checkpoint.state_data
            }

            # 计算MD5校验和
            checksum_str = json.dumps(checksum_data, sort_keys=True, default=str)
            return hashlib.md5(checksum_str.encode('utf-8')).hexdigest()

        except Exception as e:
            logger.error(f"计算校验和失败: {e}")
            return ""

    def _cleanup_old_checkpoints(self, task_id: str):
        """清理旧检查点"""
        try:
            if task_id not in self.checkpoint_index:
                return

            checkpoint_ids = self.checkpoint_index[task_id]
            if len(checkpoint_ids) <= self.max_checkpoints:
                return

            # 按时间排序，保留最新的检查点
            checkpoint_ids.sort(key=lambda cid: self._get_checkpoint_timestamp(cid), reverse=True)

            # 删除多余的检查点
            to_remove = checkpoint_ids[self.max_checkpoints:]
            for checkpoint_id in to_remove:
                self._remove_checkpoint_file(checkpoint_id)

            # 更新索引
            self.checkpoint_index[task_id] = checkpoint_ids[:self.max_checkpoints]

        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")

    def _get_checkpoint_timestamp(self, checkpoint_id: str) -> datetime:
        """获取检查点时间戳"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['timestamp'])
        except Exception:
            pass
        return datetime.min

    def _remove_checkpoint_file(self, checkpoint_id: str):
        """删除检查点文件"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
        except Exception as e:
            logger.error(f"删除检查点文件失败: {e}")

    def _save_checkpoint_to_db(self, checkpoint: Checkpoint):
        """保存检查点到数据库"""
        try:
            with get_db_session() as session:
                sync_record = SyncRecord(
                    entity_type=f"checkpoint_{checkpoint.task_name}",
                    source_system='checkpoint_manager',
                    sync_type='checkpoint',
                    status='completed',
                    started_at=checkpoint.timestamp,
                    completed_at=checkpoint.timestamp,
                    result_data=json.dumps({
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'task_id': checkpoint.task_id,
                        'checksum': checkpoint.checksum
                    })
                )
                session.add(sync_record)
                session.commit()

        except Exception as e:
            logger.error(f"保存检查点到数据库失败: {e}")

    def get_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """获取任务的最新检查点"""
        try:
            if task_id not in self.checkpoint_index:
                return None

            checkpoint_ids = self.checkpoint_index[task_id]
            if not checkpoint_ids:
                return None

            # 获取最新的检查点
            latest_id = max(checkpoint_ids, key=lambda cid: self._get_checkpoint_timestamp(cid))
            return self.load_checkpoint(latest_id)

        except Exception as e:
            logger.error(f"获取最新检查点失败: {e}")
            return None

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            if not checkpoint_file.exists():
                return None

            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 验证校验和
            checkpoint = Checkpoint(**data)
            if not self._verify_checkpoint(checkpoint):
                logger.warning(f"检查点校验失败: {checkpoint_id}")
                return None

            return checkpoint

        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None

    def _verify_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """验证检查点完整性"""
        try:
            # 重新计算校验和
            calculated_checksum = self._calculate_checksum(checkpoint)
            return calculated_checksum == checkpoint.checksum

        except Exception as e:
            logger.error(f"验证检查点失败: {e}")
            return False

    def list_checkpoints(self, task_id: str) -> List[Checkpoint]:
        """列出任务的所有检查点"""
        try:
            if task_id not in self.checkpoint_index:
                return []

            checkpoint_ids = self.checkpoint_index[task_id]
            checkpoints = []

            for checkpoint_id in checkpoint_ids:
                checkpoint = self.load_checkpoint(checkpoint_id)
                if checkpoint:
                    checkpoints.append(checkpoint)

            # 按时间排序
            checkpoints.sort(key=lambda cp: cp.timestamp, reverse=True)
            return checkpoints

        except Exception as e:
            logger.error(f"列出检查点失败: {e}")
            return []

    def remove_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint = self.load_checkpoint(checkpoint_id)
            if not checkpoint:
                return False

            # 删除文件
            self._remove_checkpoint_file(checkpoint_id)

            # 更新索引
            task_id = checkpoint.task_id
            if task_id in self.checkpoint_index:
                if checkpoint_id in self.checkpoint_index[task_id]:
                    self.checkpoint_index[task_id].remove(checkpoint_id)

                # 如果没有检查点了，删除任务条目
                if not self.checkpoint_index[task_id]:
                    del self.checkpoint_index[task_id]

            # 保存索引
            self._save_checkpoint_index()

            logger.info(f"检查点已删除: {checkpoint_id}")
            return True

        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False

    def clear_task_checkpoints(self, task_id: str) -> int:
        """清除任务的所有检查点"""
        try:
            if task_id not in self.checkpoint_index:
                return 0

            checkpoint_ids = self.checkpoint_index[task_id].copy()
            removed_count = 0

            for checkpoint_id in checkpoint_ids:
                if self.remove_checkpoint(checkpoint_id):
                    removed_count += 1

            logger.info(f"已清除任务 {task_id} 的 {removed_count} 个检查点")
            return removed_count

        except Exception as e:
            logger.error(f"清除任务检查点失败: {e}")
            return 0

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """清理旧的检查点"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            removed_count = 0

            # 遍历所有检查点
            for task_id in list(self.checkpoint_index.keys()):
                checkpoint_ids_to_remove = []

                for checkpoint_id in self.checkpoint_index[task_id]:
                    timestamp = self._get_checkpoint_timestamp(checkpoint_id)
                    if timestamp < cutoff_time:
                        checkpoint_ids_to_remove.append(checkpoint_id)

                for checkpoint_id in checkpoint_ids_to_remove:
                    if self.remove_checkpoint(checkpoint_id):
                        removed_count += 1

            logger.info(f"清理了 {removed_count} 个旧检查点")
            return removed_count

        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")
            return 0

    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """获取检查点统计信息"""
        try:
            total_checkpoints = sum(len(ids) for ids in self.checkpoint_index.values())
            total_tasks = len(self.checkpoint_index)

            # 计算存储大小
            total_size = 0
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                if checkpoint_file.name != "index.json":
                    total_size += checkpoint_file.stat().st_size

            return {
                'total_checkpoints': total_checkpoints,
                'total_tasks': total_tasks,
                'storage_size_bytes': total_size,
                'storage_size_mb': round(total_size / (1024 * 1024), 2),
                'checkpoint_directory': str(self.checkpoint_dir),
                'max_checkpoints_per_task': self.max_checkpoints
            }

        except Exception as e:
            logger.error(f"获取检查点统计失败: {e}")
            return {}

    def export_checkpoints(self, task_id: str, output_file: str) -> bool:
        """导出任务的检查点"""
        try:
            checkpoints = self.list_checkpoints(task_id)
            if not checkpoints:
                return False

            export_data = {
                'task_id': task_id,
                'export_timestamp': datetime.utcnow().isoformat(),
                'checkpoints': [asdict(cp) for cp in checkpoints]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"检查点已导出到: {output_file}")
            return True

        except Exception as e:
            logger.error(f"导出检查点失败: {e}")
            return False

    def import_checkpoints(self, import_file: str) -> int:
        """导入检查点"""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            task_id = import_data['task_id']
            imported_count = 0

            for checkpoint_data in import_data['checkpoints']:
                checkpoint = Checkpoint(**checkpoint_data)

                # 保存检查点文件
                checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(checkpoint), f, indent=2, default=str)

                # 更新索引
                if task_id not in self.checkpoint_index:
                    self.checkpoint_index[task_id] = []

                if checkpoint.checkpoint_id not in self.checkpoint_index[task_id]:
                    self.checkpoint_index[task_id].append(checkpoint.checkpoint_id)
                    imported_count += 1

            # 保存索引
            self._save_checkpoint_index()

            logger.info(f"已导入 {imported_count} 个检查点")
            return imported_count

        except Exception as e:
            logger.error(f"导入检查点失败: {e}")
            return 0


# 全局检查点管理器实例
checkpoint_manager = CheckpointManager()