"""
数据版本控制系统
"""
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """变更类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"


@dataclass
class DataVersion:
    """数据版本信息"""
    version_id: str
    entity_type: str
    entity_id: str
    change_type: ChangeType
    data: Dict[str, Any]
    previous_data: Optional[Dict[str, Any]]
    changed_fields: List[str]
    created_at: str
    created_by: str
    checksum: str
    metadata: Dict[str, Any]


@dataclass
class VersionDiff:
    """版本差异信息"""
    field: str
    old_value: Any
    new_value: Any
    change_type: str


class VersionManager:
    """数据版本管理器"""

    def __init__(self):
        """初始化版本管理器"""
        self.versions: Dict[str, List[DataVersion]] = {}  # entity_key -> versions
        self.current_versions: Dict[str, str] = {}  # entity_key -> current_version_id

    def create_version(self, entity_type: str, entity_id: str,
                      data: Dict[str, Any], change_type: ChangeType,
                      previous_data: Optional[Dict[str, Any]] = None,
                      created_by: str = 'system',
                      metadata: Dict[str, Any] = None) -> DataVersion:
        """创建新版本"""
        try:
            # 生成版本ID
            version_id = self._generate_version_id(entity_type, entity_id)

            # 计算数据校验和
            checksum = self._calculate_checksum(data)

            # 识别变更字段
            changed_fields = []
            if previous_data:
                changed_fields = self._find_changed_fields(previous_data, data)

            # 创建版本对象
            version = DataVersion(
                version_id=version_id,
                entity_type=entity_type,
                entity_id=entity_id,
                change_type=change_type,
                data=data.copy(),
                previous_data=previous_data.copy() if previous_data else None,
                changed_fields=changed_fields,
                created_at=datetime.now().isoformat(),
                created_by=created_by,
                checksum=checksum,
                metadata=metadata or {}
            )

            # 存储版本
            entity_key = f"{entity_type}:{entity_id}"
            if entity_key not in self.versions:
                self.versions[entity_key] = []

            self.versions[entity_key].append(version)
            self.current_versions[entity_key] = version_id

            logger.debug(f"创建版本 {version_id} for {entity_key}")
            return version

        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            raise

    def get_current_version(self, entity_type: str, entity_id: str) -> Optional[DataVersion]:
        """获取当前版本"""
        entity_key = f"{entity_type}:{entity_id}"
        version_id = self.current_versions.get(entity_key)

        if not version_id:
            return None

        return self._get_version_by_id(entity_key, version_id)

    def get_version_history(self, entity_type: str, entity_id: str,
                           limit: int = 50) -> List[DataVersion]:
        """获取版本历史"""
        entity_key = f"{entity_type}:{entity_id}"
        versions = self.versions.get(entity_key, [])

        # 返回最新的版本
        return versions[-limit:] if len(versions) > limit else versions

    def get_version_by_id(self, entity_type: str, entity_id: str,
                         version_id: str) -> Optional[DataVersion]:
        """根据版本ID获取版本"""
        entity_key = f"{entity_type}:{entity_id}"
        return self._get_version_by_id(entity_key, version_id)

    def compare_versions(self, entity_type: str, entity_id: str,
                        version_id1: str, version_id2: str) -> List[VersionDiff]:
        """比较两个版本"""
        try:
            version1 = self.get_version_by_id(entity_type, entity_id, version_id1)
            version2 = self.get_version_by_id(entity_type, entity_id, version_id2)

            if not version1 or not version2:
                raise ValueError("版本不存在")

            diffs = []
            all_fields = set(version1.data.keys()) | set(version2.data.keys())

            for field in all_fields:
                old_value = version1.data.get(field)
                new_value = version2.data.get(field)

                if old_value != new_value:
                    change_type = self._determine_change_type(old_value, new_value)
                    diffs.append(VersionDiff(
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                        change_type=change_type
                    ))

            return diffs

        except Exception as e:
            logger.error(f"比较版本失败: {e}")
            raise

    def revert_to_version(self, entity_type: str, entity_id: str,
                         version_id: str, created_by: str = 'system') -> DataVersion:
        """回滚到指定版本"""
        try:
            target_version = self.get_version_by_id(entity_type, entity_id, version_id)
            if not target_version:
                raise ValueError(f"版本 {version_id} 不存在")

            if target_version.change_type == ChangeType.DELETE:
                raise ValueError("不能回滚到删除版本")

            # 获取当前数据
            current_version = self.get_current_version(entity_type, entity_id)
            current_data = current_version.data if current_version else {}

            # 创建回滚版本
            revert_version = self.create_version(
                entity_type=entity_type,
                entity_id=entity_id,
                data=target_version.data.copy(),
                change_type=ChangeType.UPDATE,
                previous_data=current_data,
                created_by=created_by,
                metadata={'revert_from_version': version_id}
            )

            logger.info(f"回滚 {entity_type}:{entity_id} 到版本 {version_id}")
            return revert_version

        except Exception as e:
            logger.error(f"回滚版本失败: {e}")
            raise

    def get_diff_summary(self, diffs: List[VersionDiff]) -> Dict[str, Any]:
        """获取差异摘要"""
        if not diffs:
            return {'total_changes': 0, 'change_types': {}, 'field_changes': []}

        change_types = {}
        field_changes = []

        for diff in diffs:
            # 统计变更类型
            change_type = diff.change_type
            change_types[change_type] = change_types.get(change_type, 0) + 1

            # 记录字段变更
            field_changes.append({
                'field': diff.field,
                'type': change_type,
                'old_value': str(diff.old_value)[:100] if diff.old_value else None,
                'new_value': str(diff.new_value)[:100] if diff.new_value else None
            })

        return {
            'total_changes': len(diffs),
            'change_types': change_types,
            'field_changes': field_changes
        }

    def cleanup_old_versions(self, entity_type: str = None, entity_id: str = None,
                           keep_count: int = 10, days_old: int = 30) -> int:
        """清理旧版本"""
        try:
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days_old)
            cleaned_count = 0

            # 确定要清理的实体
            entity_keys_to_clean = []
            if entity_type and entity_id:
                entity_keys_to_clean = [f"{entity_type}:{entity_id}"]
            elif entity_type:
                entity_keys_to_clean = [key for key in self.versions.keys()
                                      if key.startswith(f"{entity_type}:")]
            else:
                entity_keys_to_clean = list(self.versions.keys())

            for entity_key in entity_keys_to_clean:
                versions = self.versions.get(entity_key, [])
                if len(versions) <= keep_count:
                    continue

                # 保留最新的版本
                versions_to_keep = versions[-keep_count:]
                versions_to_remove = []

                for version in versions:
                    if version not in versions_to_keep:
                        # 检查日期
                        version_date = datetime.fromisoformat(version.created_at)
                        if version_date < cutoff_date:
                            versions_to_remove.append(version)

                # 移除版本
                for version in versions_to_remove:
                    versions.remove(version)
                    cleaned_count += 1

                # 更新版本列表
                if versions:
                    self.versions[entity_key] = versions
                else:
                    del self.versions[entity_key]
                    if entity_key in self.current_versions:
                        del self.current_versions[entity_key]

            logger.info(f"清理了 {cleaned_count} 个旧版本")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理旧版本失败: {e}")
            raise

    def export_versions(self, entity_type: str = None, entity_id: str = None,
                       output_file: str = None) -> str:
        """导出版本数据"""
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'versions': []
            }

            # 确定要导出的版本
            for entity_key, versions in self.versions.items():
                e_type, e_id = entity_key.split(':', 1)

                # 过滤条件
                if entity_type and e_type != entity_type:
                    continue
                if entity_id and e_id != entity_id:
                    continue

                for version in versions:
                    version_data = asdict(version)
                    # 转换枚举
                    version_data['change_type'] = version.change_type.value
                    export_data['versions'].append(version_data)

            export_content = json.dumps(export_data, ensure_ascii=False, indent=2)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(export_content)
                logger.info(f"版本数据已导出到: {output_file}")

            return export_content

        except Exception as e:
            logger.error(f"导出版本数据失败: {e}")
            raise

    def import_versions(self, import_data: str, overwrite: bool = False) -> int:
        """导入版本数据"""
        try:
            data = json.loads(import_data)
            imported_count = 0

            for version_data in data['versions']:
                # 转换枚举
                version_data['change_type'] = ChangeType(version_data['change_type'])

                # 重建版本对象
                version = DataVersion(**version_data)
                entity_key = f"{version.entity_type}:{version.entity_id}"

                # 检查是否已存在
                if not overwrite and entity_key in self.versions:
                    existing_version_ids = {v.version_id for v in self.versions[entity_key]}
                    if version.version_id in existing_version_ids:
                        continue

                # 添加版本
                if entity_key not in self.versions:
                    self.versions[entity_key] = []

                self.versions[entity_key].append(version)
                self.current_versions[entity_key] = version.version_id
                imported_count += 1

            logger.info(f"导入了 {imported_count} 个版本")
            return imported_count

        except Exception as e:
            logger.error(f"导入版本数据失败: {e}")
            raise

    def _generate_version_id(self, entity_type: str, entity_id: str) -> str:
        """生成版本ID"""
        timestamp = datetime.now().isoformat()
        content = f"{entity_type}:{entity_id}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        # 排序字段以确保一致性
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_data.encode()).hexdigest()[:16]

    def _find_changed_fields(self, old_data: Dict[str, Any],
                           new_data: Dict[str, Any]) -> List[str]:
        """找出变更的字段"""
        changed_fields = []
        all_fields = set(old_data.keys()) | set(new_data.keys())

        for field in all_fields:
            old_value = old_data.get(field)
            new_value = new_data.get(field)

            if old_value != new_value:
                changed_fields.append(field)

        return changed_fields

    def _determine_change_type(self, old_value: Any, new_value: Any) -> str:
        """确定变更类型"""
        if old_value is None and new_value is not None:
            return 'added'
        elif old_value is not None and new_value is None:
            return 'removed'
        else:
            return 'modified'

    def _get_version_by_id(self, entity_key: str, version_id: str) -> Optional[DataVersion]:
        """根据ID获取版本"""
        versions = self.versions.get(entity_key, [])
        for version in versions:
            if version.version_id == version_id:
                return version
        return None

    def get_version_statistics(self) -> Dict[str, Any]:
        """获取版本统计信息"""
        total_versions = sum(len(versions) for versions in self.versions.values())
        total_entities = len(self.versions)

        # 按实体类型统计
        type_stats = {}
        for entity_key, versions in self.versions.items():
            entity_type = entity_key.split(':')[0]
            type_stats[entity_type] = type_stats.get(entity_type, 0) + len(versions)

        # 按变更类型统计
        change_stats = {}
        for versions in self.versions.values():
            for version in versions:
                change_type = version.change_type.value
                change_stats[change_type] = change_stats.get(change_type, 0) + 1

        return {
            'total_versions': total_versions,
            'total_entities': total_entities,
            'average_versions_per_entity': total_versions / total_entities if total_entities > 0 else 0,
            'type_distribution': type_stats,
            'change_type_distribution': change_stats
        }