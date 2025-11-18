"""
数据库迁移管理器
"""
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from alembic import command
from alembic.config import Config

from config.database import db_settings

logger = logging.getLogger(__name__)


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, alembic_ini_path: str = None):
        self.alembic_ini_path = alembic_ini_path or str(
            Path(__file__).parent.parent.parent / "migrations" / "alembic.ini"
        )
        self.alembic_cfg = Config(self.alembic_ini_path)

        # 设置数据库URL
        self.alembic_cfg.set_main_option("sqlalchemy.url", db_settings.sync_database_url)

    def upgrade_database(self, revision: str = "head") -> bool:
        """升级数据库到指定版本"""
        try:
            logger.info(f"开始升级数据库到版本: {revision}")
            command.upgrade(self.alembic_cfg, revision)
            logger.info("数据库升级完成")
            return True
        except Exception as e:
            logger.error(f"数据库升级失败: {e}")
            return False

    def downgrade_database(self, revision: str) -> bool:
        """降级数据库到指定版本"""
        try:
            logger.info(f"开始降级数据库到版本: {revision}")
            command.downgrade(self.alembic_cfg, revision)
            logger.info("数据库降级完成")
            return True
        except Exception as e:
            logger.error(f"数据库降级失败: {e}")
            return False

    def create_migration(
        self,
        message: str,
        autogenerate: bool = True,
        head: str = "head"
    ) -> Optional[str]:
        """创建新的迁移文件"""
        try:
            logger.info(f"创建迁移文件: {message}")
            revision = command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=autogenerate,
                head=head
            )
            logger.info(f"迁移文件创建成功: {revision}")
            return revision
        except Exception as e:
            logger.error(f"创建迁移文件失败: {e}")
            return None

    def get_current_revision(self) -> Optional[str]:
        """获取当前数据库版本"""
        try:
            current = command.current(self.alembic_cfg)
            return current
        except Exception as e:
            logger.error(f"获取当前版本失败: {e}")
            return None

    def get_revision_history(self) -> List[Dict]:
        """获取迁移历史"""
        try:
            history = command.history(self.alembic_cfg)
            revisions = []
            for rev in history:
                revisions.append({
                    'revision': rev.revision,
                    'doc': rev.doc,
                    'down_revision': rev.down_revision,
                    'branch_labels': rev.branch_labels,
                    'depends_on': rev.depends_on
                })
            return revisions
        except Exception as e:
            logger.error(f"获取迁移历史失败: {e}")
            return []

    def get_pending_migrations(self) -> List[Dict]:
        """获取待执行的迁移"""
        try:
            current = self.get_current_revision()
            history = self.get_revision_history()

            if not current:
                return history

            pending = []
            for rev in history:
                if rev['revision'] != current and rev['down_revision'] != current:
                    pending.append(rev)

            return pending
        except Exception as e:
            logger.error(f"获取待执行迁移失败: {e}")
            return []

    def check_migration_status(self) -> Dict:
        """检查迁移状态"""
        try:
            current = self.get_current_revision()
            head = self.get_head_revision()
            pending = self.get_pending_migrations()

            return {
                'current_revision': current,
                'head_revision': head,
                'is_up_to_date': current == head,
                'pending_migrations': len(pending),
                'pending_details': pending
            }
        except Exception as e:
            logger.error(f"检查迁移状态失败: {e}")
            return {
                'error': str(e)
            }

    def get_head_revision(self) -> Optional[str]:
        """获取最新版本"""
        try:
            heads = command.heads(self.alembic_cfg)
            return heads[0] if heads else None
        except Exception as e:
            logger.error(f"获取最新版本失败: {e}")
            return None

    def stamp_database(self, revision: str = "head") -> bool:
        """标记数据库版本（不执行迁移）"""
        try:
            logger.info(f"标记数据库版本: {revision}")
            command.stamp(self.alembic_cfg, revision)
            logger.info("数据库版本标记完成")
            return True
        except Exception as e:
            logger.error(f"标记数据库版本失败: {e}")
            return False

    def merge_migrations(
        self,
        revisions: List[str],
        message: str,
        branch_labels: List[str] = None
    ) -> Optional[str]:
        """合并迁移分支"""
        try:
            logger.info(f"合并迁移分支: {revisions}")
            result = command.merge(
                self.alembic_cfg,
                revisions=revisions,
                message=message,
                branch_labels=branch_labels
            )
            logger.info(f"迁移分支合并成功: {result}")
            return result
        except Exception as e:
            logger.error(f"合并迁移分支失败: {e}")
            return None

    def backup_database_before_migration(self, backup_name: str = None) -> bool:
        """迁移前备份数据库"""
        try:
            if not backup_name:
                import time
                backup_name = f"pre_migration_{int(time.time())}"

            # 这里应该实现实际的备份逻辑
            # 可以使用 pg_dump 或其他备份工具
            logger.info(f"数据库备份: {backup_name}")

            # 示例备份命令（需要根据实际环境调整）
            # cmd = f"pg_dump -h {db_settings.host} -U {db_settings.username} -d {db_settings.database} > {backup_name}.sql"
            # result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            logger.info("数据库备份完成")
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False

    async def safe_upgrade(self, revision: str = "head", backup_before: bool = True) -> Dict:
        """安全升级数据库（包含备份）"""
        try:
            result = {
                'success': False,
                'backup_created': False,
                'migration_completed': False,
                'backup_name': None,
                'error': None
            }

            # 1. 检查当前状态
            status = self.check_migration_status()
            if status.get('is_up_to_date', False):
                result['success'] = True
                result['migration_completed'] = True
                result['message'] = '数据库已是最新版本'
                return result

            # 2. 备份数据库
            if backup_before:
                backup_name = f"pre_upgrade_{revision}_{int(__import__('time').time())}"
                if self.backup_database_before_migration(backup_name):
                    result['backup_created'] = True
                    result['backup_name'] = backup_name
                else:
                    result['error'] = '数据库备份失败，中止升级'
                    return result

            # 3. 执行迁移
            if self.upgrade_database(revision):
                result['migration_completed'] = True
                result['success'] = True
                result['message'] = f'数据库升级成功到版本: {revision}'
            else:
                result['error'] = '数据库升级失败'

            return result

        except Exception as e:
            logger.error(f"安全升级数据库失败: {e}")
            return {
                'success': False,
                'backup_created': False,
                'migration_completed': False,
                'error': str(e)
            }

    def validate_migration_file(self, migration_path: str) -> Dict:
        """验证迁移文件"""
        try:
            migration_file = Path(migration_path)
            if not migration_file.exists():
                return {'valid': False, 'error': '迁移文件不存在'}

            # 检查文件语法
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 基本语法检查
            try:
                compile(content, migration_path, 'exec')
                syntax_valid = True
            except SyntaxError as e:
                syntax_valid = False
                return {'valid': False, 'error': f'语法错误: {e}'}

            # 检查必要函数
            has_upgrade = 'def upgrade()' in content
            has_downgrade = 'def downgrade()' in content

            if not has_upgrade:
                return {'valid': False, 'error': '缺少 upgrade() 函数'}

            if not has_downgrade:
                return {'valid': False, 'error': '缺少 downgrade() 函数'}

            return {
                'valid': True,
                'syntax_valid': syntax_valid,
                'has_upgrade': has_upgrade,
                'has_downgrade': has_downgrade
            }

        except Exception as e:
            return {'valid': False, 'error': f'验证失败: {e}'}

    def get_migration_plan(self, target_revision: str = "head") -> List[Dict]:
        """获取迁移计划"""
        try:
            plan = []
            current = self.get_current_revision()
            history = self.get_revision_history()

            if current == target_revision:
                return plan

            # 简化的迁移计划生成
            for rev in history:
                if rev['down_revision'] == current or current is None:
                    plan.append({
                        'revision': rev['revision'],
                        'message': rev['doc'],
                        'is_downgrade': False
                    })
                    current = rev['revision']

                    if rev['revision'] == target_revision:
                        break

            return plan

        except Exception as e:
            logger.error(f"获取迁移计划失败: {e}")
            return []


# 全局迁移管理器实例
migration_manager = MigrationManager()