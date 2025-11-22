"""
数据备份和恢复机制
"""
import gzip
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config.database import db_settings
from config.settings import app_settings

logger = logging.getLogger(__name__)


class BackupRestoreManager:
    """备份恢复管理器"""

    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir or "./backups")
        self.backup_dir.mkdir(exist_ok=True)

        # 创建子目录
        (self.backup_dir / "database").mkdir(exist_ok=True)
        (self.backup_dir / "images").mkdir(exist_ok=True)
        (self.backup_dir / "config").mkdir(exist_ok=True)

    def create_database_backup(
        self,
        backup_name: str = None,
        compressed: bool = True,
        include_schema: bool = True,
        include_data: bool = True
    ) -> Dict:
        """创建数据库备份"""
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"db_backup_{timestamp}"

            backup_file = self.backup_dir / "database" / f"{backup_name}.sql"
            if compressed:
                backup_file = backup_file.with_suffix('.sql.gz')

            # 构建 pg_dump 命令
            cmd_parts = [
                "pg_dump",
                f"--host={db_settings.host}",
                f"--port={db_settings.port}",
                f"--username={db_settings.username}",
                f"--dbname={db_settings.database}",
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists",
                "--disable-triggers",
            ]

            if include_schema:
                cmd_parts.append("--schema=public")

            if not include_data:
                cmd_parts.append("--schema-only")

            if compressed:
                cmd_parts.extend(["--format=custom", "--compress=9"])

            cmd_parts.extend(["--file", str(backup_file)])

            # 设置环境变量（避免密码提示）
            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings.password

            logger.info(f"开始数据库备份: {backup_name}")
            start_time = time.time()

            # 执行备份命令
            result = subprocess.run(
                cmd_parts,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                file_size = backup_file.stat().st_size
                backup_info = {
                    'success': True,
                    'backup_name': backup_name,
                    'backup_file': str(backup_file),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'duration_seconds': round(duration, 2),
                    'created_at': datetime.now().isoformat(),
                    'compressed': compressed,
                    'include_schema': include_schema,
                    'include_data': include_data
                }

                # 创建备份元数据文件
                metadata_file = backup_file.with_suffix('.meta.json')
                import json
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_info, f, indent=2, ensure_ascii=False)

                logger.info(f"数据库备份完成: {backup_name} ({backup_info['file_size_mb']} MB)")
                return backup_info
            else:
                logger.error(f"数据库备份失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            logger.error("数据库备份超时")
            return {
                'success': False,
                'error': 'Backup timeout after 1 hour'
            }
        except Exception as e:
            logger.error(f"数据库备份异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def restore_database_backup(
        self,
        backup_name: str,
        force: bool = False,
        drop_existing: bool = False
    ) -> Dict:
        """恢复数据库备份"""
        try:
            backup_file = self._find_backup_file(backup_name)
            if not backup_file:
                return {
                    'success': False,
                    'error': f'备份文件不存在: {backup_name}'
                }

            # 检查备份文件完整性
            metadata = self._read_backup_metadata(backup_file)
            if not metadata:
                return {
                    'success': False,
                    'error': '无法读取备份元数据'
                }

            # 确认操作
            if not force:
                logger.warning(f"准备恢复数据库备份: {backup_name}")
                logger.warning("这将删除现有数据！使用 force=True 强制执行")
                return {
                    'success': False,
                    'error': '需要 force=True 参数确认恢复操作',
                    'metadata': metadata
                }

            # 备份当前数据（安全措施）
            current_backup = self.create_database_backup(
                f"pre_restore_{int(time.time())}",
                compressed=True
            )
            if not current_backup['success']:
                return {
                    'success': False,
                    'error': '无法创建当前数据备份'
                }

            logger.info(f"开始恢复数据库备份: {backup_name}")
            start_time = time.time()

            # 如果需要，先删除现有数据库
            if drop_existing:
                drop_result = self._drop_database()
                if not drop_result['success']:
                    return drop_result

                create_result = self._create_database()
                if not create_result['success']:
                    return create_result

            # 构建 pg_restore 命令
            cmd_parts = [
                "pg_restore",
                f"--host={db_settings.host}",
                f"--port={db_settings.port}",
                f"--username={db_settings.username}",
                f"--dbname={db_settings.database}",
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists",
                "--disable-triggers",
                "--no-owner",
                "--no-privileges",
            ]

            # 根据备份类型选择参数
            if backup_file.suffix == '.gz':
                # 解压的备份文件
                cmd_parts.extend(["--format=directory", str(backup_file)])
            else:
                # 标准SQL文件
                cmd_parts.extend(["--format=custom", str(backup_file)])

            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings.password

            result = subprocess.run(
                cmd_parts,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )

            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                restore_info = {
                    'success': True,
                    'backup_name': backup_name,
                    'restored_from': str(backup_file),
                    'duration_seconds': round(duration, 2),
                    'restored_at': datetime.now().isoformat(),
                    'previous_backup': current_backup['backup_name'] if current_backup['success'] else None
                }

                logger.info(f"数据库恢复完成: {backup_name} ({duration:.2f}s)")
                return restore_info
            else:
                logger.error(f"数据库恢复失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except Exception as e:
            logger.error(f"数据库恢复异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_images_backup(
        self,
        backup_name: str = None,
        compressed: bool = True
    ) -> Dict:
        """创建图片文件备份"""
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"images_backup_{timestamp}"

            source_dir = Path(app_settings.storage_path)
            if not source_dir.exists():
                return {
                    'success': False,
                    'error': f'源目录不存在: {source_dir}'
                }

            backup_file = self.backup_dir / "images" / f"{backup_name}"
            if compressed:
                backup_file = backup_file.with_suffix('.tar.gz')
            else:
                backup_file = backup_file.with_suffix('.tar')

            logger.info(f"开始图片备份: {backup_name}")
            start_time = time.time()

            # 使用 tar 创建备份
            cmd = ["tar", "-cf", str(backup_file)]
            if compressed:
                cmd.insert(1, "-czf")  # gzip压缩
                cmd[1] = "-czf"  # 修复参数位置

            cmd.append("-C")  # 更改到源目录
            cmd.append(str(source_dir.parent))  # 源目录的父目录
            cmd.append(source_dir.name)  # 只备份源目录

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30分钟超时
            )

            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                file_size = backup_file.stat().st_size
                backup_info = {
                    'success': True,
                    'backup_name': backup_name,
                    'backup_file': str(backup_file),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'duration_seconds': round(duration, 2),
                    'created_at': datetime.now().isoformat(),
                    'compressed': compressed,
                    'source_directory': str(source_dir)
                }

                # 创建备份元数据
                metadata_file = backup_file.with_suffix('.meta.json')
                import json
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_info, f, indent=2, ensure_ascii=False)

                logger.info(f"图片备份完成: {backup_name} ({backup_info['file_size_mb']} MB)")
                return backup_info
            else:
                logger.error(f"图片备份失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except Exception as e:
            logger.error(f"图片备份异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def restore_images_backup(
        self,
        backup_name: str,
        force: bool = False,
        backup_existing: bool = True
    ) -> Dict:
        """恢复图片文件备份"""
        try:
            backup_file = self._find_images_backup_file(backup_name)
            if not backup_file:
                return {
                    'success': False,
                    'error': f'图片备份文件不存在: {backup_name}'
                }

            target_dir = Path(app_settings.storage_path)

            # 备份现有文件
            if backup_existing and target_dir.exists():
                existing_backup = self.create_images_backup(
                    f"pre_images_restore_{int(time.time())}"
                )
                if existing_backup['success']:
                    logger.info(f"现有图片已备份: {existing_backup['backup_name']}")

            # 确认操作
            if not force:
                logger.warning(f"准备恢复图片备份: {backup_name}")
                logger.warning("这将覆盖现有图片文件！使用 force=True 强制执行")
                return {
                    'success': False,
                    'error': '需要 force=True 参数确认恢复操作'
                }

            logger.info(f"开始恢复图片备份: {backup_name}")
            start_time = time.time()

            # 确保目标目录存在
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # 使用 tar 解压
            cmd = ["tar", "-xf", str(backup_file), "-C", str(target_dir.parent)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )

            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                restore_info = {
                    'success': True,
                    'backup_name': backup_name,
                    'restored_from': str(backup_file),
                    'target_directory': str(target_dir),
                    'duration_seconds': round(duration, 2),
                    'restored_at': datetime.now().isoformat()
                }

                logger.info(f"图片恢复完成: {backup_name} ({duration:.2f}s)")
                return restore_info
            else:
                logger.error(f"图片恢复失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except Exception as e:
            logger.error(f"图片恢复异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_full_backup(
        self,
        backup_name: str = None,
        include_images: bool = True,
        include_config: bool = True
    ) -> Dict:
        """创建完整备份"""
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"full_backup_{timestamp}"

            logger.info(f"开始完整备份: {backup_name}")
            start_time = time.time()

            backup_results = {
                'backup_name': backup_name,
                'started_at': datetime.now().isoformat(),
                'components': {}
            }

            # 1. 数据库备份
            db_backup = self.create_database_backup(f"{backup_name}_db")
            backup_results['components']['database'] = db_backup

            # 2. 图片备份
            if include_images:
                images_backup = self.create_images_backup(f"{backup_name}_images")
                backup_results['components']['images'] = images_backup

            # 3. 配置备份
            if include_config:
                config_backup = self.create_config_backup(f"{backup_name}_config")
                backup_results['components']['config'] = config_backup

            end_time = time.time()
            duration = end_time - start_time

            # 计算总体积
            total_size = sum(
                comp.get('file_size_bytes', 0)
                for comp in backup_results['components'].values()
                if comp.get('success')
            )

            backup_results.update({
                'success': all(comp.get('success', False) for comp in backup_results['components'].values()),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.now().isoformat()
            })

            # 保存完整备份元数据
            metadata_file = self.backup_dir / f"{backup_name}_full.meta.json"
            import json
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(backup_results, f, indent=2, ensure_ascii=False)

            if backup_results['success']:
                logger.info(f"完整备份完成: {backup_name} ({backup_results['total_size_mb']} MB)")
            else:
                logger.error(f"完整备份部分失败: {backup_name}")

            return backup_results

        except Exception as e:
            logger.error(f"完整备份异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_config_backup(self, backup_name: str = None) -> Dict:
        """创建配置文件备份"""
        try:
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"config_backup_{timestamp}"

            config_dir = Path("./config")
            env_file = Path(".env")
            backup_file = self.backup_dir / "config" / f"{backup_name}.tar.gz"

            logger.info(f"开始配置备份: {backup_name}")
            start_time = time.time()

            cmd = ["tar", "-czf", str(backup_file)]
            if config_dir.exists():
                cmd.append(config_dir.name)
            if env_file.exists():
                cmd.append(env_file.name)

            # 在项目根目录执行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            end_time = time.time()
            duration = end_time - start_time

            if result.returncode == 0:
                file_size = backup_file.stat().st_size
                backup_info = {
                    'success': True,
                    'backup_name': backup_name,
                    'backup_file': str(backup_file),
                    'file_size_bytes': file_size,
                    'file_size_mb': round(file_size / (1024 * 1024), 2),
                    'duration_seconds': round(duration, 2),
                    'created_at': datetime.now().isoformat()
                }

                logger.info(f"配置备份完成: {backup_name}")
                return backup_info
            else:
                logger.error(f"配置备份失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode
                }

        except Exception as e:
            logger.error(f"配置备份异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def list_backups(self, backup_type: str = "all") -> Dict:
        """列出所有备份"""
        try:
            backups = {
                'database': [],
                'images': [],
                'config': [],
                'full': []
            }

            # 扫描备份目录
            for backup_file in self.backup_dir.rglob("*"):
                if backup_file.is_file() and backup_file.suffix in ['.sql', '.gz', '.meta.json']:
                    # 读取元数据文件
                    meta_file = backup_file.with_suffix('.meta.json')
                    if meta_file.exists():
                        import json
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        # 分类备份
                        if 'db' in backup_file.name.lower():
                            backups['database'].append(metadata)
                        elif 'images' in backup_file.name.lower():
                            backups['images'].append(metadata)
                        elif 'config' in backup_file.name.lower():
                            backups['config'].append(metadata)
                        elif 'full' in backup_file.name.lower():
                            backups['full'].append(metadata)

            # 排序（按创建时间倒序）
            for category in backups:
                backups[category].sort(
                    key=lambda x: x.get('created_at', ''), reverse=True
                )

            if backup_type != "all":
                return {backup_type: backups[backup_type]}

            return backups

        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return {'error': str(e)}

    def cleanup_old_backups(self, days_to_keep: int = 30) -> Dict:
        """清理旧备份"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_files = []
            total_size_freed = 0

            # 扫描所有备份文件
            for backup_file in self.backup_dir.rglob("*"):
                if backup_file.is_file():
                    # 获取文件修改时间
                    file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        deleted_files.append(str(backup_file))
                        total_size_freed += file_size

            cleanup_info = {
                'success': True,
                'deleted_files_count': len(deleted_files),
                'deleted_files': deleted_files,
                'size_freed_bytes': total_size_freed,
                'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
                'cutoff_date': cutoff_date.isoformat()
            }

            logger.info(f"清理旧备份完成: 删除 {len(deleted_files)} 个文件，释放 {cleanup_info['size_freed_mb']} MB")
            return cleanup_info

        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _find_backup_file(self, backup_name: str) -> Optional[Path]:
        """查找数据库备份文件"""
        db_dir = self.backup_dir / "database"
        for suffix in ['.sql', '.sql.gz']:
            backup_file = db_dir / f"{backup_name}{suffix}"
            if backup_file.exists():
                return backup_file
        return None

    def _find_images_backup_file(self, backup_name: str) -> Optional[Path]:
        """查找图片备份文件"""
        images_dir = self.backup_dir / "images"
        for suffix in ['.tar', '.tar.gz']:
            backup_file = images_dir / f"{backup_name}{suffix}"
            if backup_file.exists():
                return backup_file
        return None

    def _read_backup_metadata(self, backup_file: Path) -> Optional[Dict]:
        """读取备份元数据"""
        meta_file = backup_file.with_suffix('.meta.json')
        if not meta_file.exists():
            return None

        try:
            import json
            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取备份元数据失败: {e}")
            return None

    def _drop_database(self) -> Dict:
        """删除数据库"""
        try:
            cmd = [
                "dropdb",
                f"--host={db_settings.host}",
                f"--port={db_settings.port}",
                f"--username={db_settings.username}",
                "--if-exists",
                db_settings.database
            ]

            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _create_database(self) -> Dict:
        """创建数据库"""
        try:
            cmd = [
                "createdb",
                f"--host={db_settings.host}",
                f"--port={db_settings.port}",
                f"--username={db_settings.username}",
                db_settings.database
            ]

            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 全局备份恢复管理器实例
backup_restore_manager = BackupRestoreManager()