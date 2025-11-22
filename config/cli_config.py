# CLI Configuration
# CLI 工具配置文件

import os
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import json

from .settings import get_settings


class CLIConfig:
    """CLI 配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _get_default_config_file(self) -> str:
        """获取默认配置文件路径"""
        # 按优先级查找配置文件
        config_paths = [
            os.environ.get('CLICONFIG_FILE'),
            os.path.expanduser('~/.1688sync/cli.yaml'),
            os.path.expanduser('~/.1688sync/cli.json'),
            './cli.yaml',
            './cli.json',
            './config/cli.yaml',
            './config/cli.json'
        ]

        for path in config_paths:
            if path and os.path.exists(path):
                return path

        # 如果配置文件不存在，返回默认路径
        return './config/cli.yaml'

    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            self._config = self._get_default_config()
            self._save_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    self._config = yaml.safe_load(f) or {}
                else:
                    self._config = json.load(f)
        except Exception as e:
            print(f"警告: 加载配置文件失败 {self.config_file}: {e}")
            self._config = self._get_default_config()

    def _save_config(self):
        """保存配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"警告: 保存配置文件失败 {self.config_file}: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'cli': {
                'version': '1.0.0',
                'default_batch_size': 100,
                'default_page_size': 50,
                'max_products': 1000,
                'progress_update_interval': 1,
                'timeout': 300,
                'retry_attempts': 3,
                'retry_delay': 5
            },
            'sync': {
                'default_source': '1688',
                'default_type': 'incremental',
                'auto_cleanup': False,
                'validate_after_sync': True
            },
            'crawl': {
                'default_delay': 1,
                'max_concurrent_requests': 5,
                'user_agent': '1688sync-cli/1.0.0',
                'timeout': 30,
                'respect_robots_txt': True
            },
            'queue': {
                'worker_concurrency': 4,
                'task_timeout': 3600,
                'result_expires': 86400,
                'max_retries': 3,
                'default_queue': 'default'
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': None,
                'max_size': '10MB',
                'backup_count': 5
            },
            'output': {
                'format': 'table',  # table, json, yaml
                'colors': True,
                'compact': False,
                'show_progress': True
            },
            'database': {
                'url': None,  # 从环境变量获取
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30
            },
            'redis': {
                'url': None,  # 从环境变量获取
                'max_connections': 20,
                'retry_on_timeout': True
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        self._save_config()

    def reset(self):
        """重置为默认配置"""
        self._config = self._get_default_config()
        self._save_config()

    def merge_with_env(self):
        """与环境变量合并配置"""
        # 数据库配置
        if not self.get('database.url'):
            db_url = os.environ.get('DATABASE_URL')
            if db_url:
                self.set('database.url', db_url)

        # Redis配置
        if not self.get('redis.url'):
            redis_url = os.environ.get('REDIS_URL')
            if redis_url:
                self.set('redis.url', redis_url)

        # 日志级别
        log_level = os.environ.get('LOG_LEVEL')
        if log_level:
            self.set('logging.level', log_level.upper())

        # 其他环境变量
        env_mappings = {
            'CLIBATCH_SIZE': 'cli.default_batch_size',
            'CLIPAGE_SIZE': 'cli.default_page_size',
            'CLIMAX_PRODUCTS': 'cli.max_products',
            'CLITIMEOUT': 'cli.timeout',
            'CLIWORKER_CONCURRENCY': 'queue.worker_concurrency'
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value:
                try:
                    # 尝试转换为数字
                    if env_value.isdigit():
                        self.set(config_key, int(env_value))
                    else:
                        # 尝试转换为浮点数
                        self.set(config_key, float(env_value))
                except ValueError:
                    self.set(config_key, env_value)


# 全局配置实例
cli_config: Optional[CLIConfig] = None


def get_cli_config(config_file: Optional[str] = None) -> CLIConfig:
    """获取CLI配置实例"""
    global cli_config
    if cli_config is None:
        cli_config = CLIConfig(config_file)
        cli_config.merge_with_env()
    return cli_config


def create_default_config_file(path: str):
    """创建默认配置文件"""
    config = CLIConfig()
    config.config_file = path
    config.save()


# 配置验证函数
def validate_config(config: CLIConfig) -> list:
    """验证配置文件，返回错误列表"""
    errors = []

    # 检查必需配置
    required_configs = [
        'cli.default_batch_size',
        'cli.default_page_size',
        'queue.worker_concurrency'
    ]

    for key in required_configs:
        if config.get(key) is None:
            errors.append(f"缺少必需配置: {key}")

    # 检查数值范围
    batch_size = config.get('cli.default_batch_size', 0)
    if not isinstance(batch_size, int) or batch_size <= 0:
        errors.append("cli.default_batch_size 必须是正整数")

    page_size = config.get('cli.default_page_size', 0)
    if not isinstance(page_size, int) or page_size <= 0:
        errors.append("cli.default_page_size 必须是正整数")

    worker_concurrency = config.get('queue.worker_concurrency', 0)
    if not isinstance(worker_concurrency, int) or worker_concurrency <= 0:
        errors.append("queue.worker_concurrency 必须是正整数")

    # 检查日志级别
    log_level = config.get('logging.level', '').upper()
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if log_level not in valid_levels:
        errors.append(f"logging.level 必须是以下之一: {', '.join(valid_levels)}")

    return errors


# 配置模板生成
def generate_config_template(format_type: str = 'yaml') -> str:
    """生成配置模板"""
    config = CLIConfig()

    if format_type.lower() == 'json':
        return json.dumps(config._config, indent=2, ensure_ascii=False)
    else:
        return yaml.dump(config._config, default_flow_style=False, allow_unicode=True)