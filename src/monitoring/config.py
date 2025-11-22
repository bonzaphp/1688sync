"""
监控配置模块 - 提供默认配置和配置加载功能
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


def get_default_monitoring_config() -> Dict[str, Any]:
    """获取默认监控配置"""
    return {
        'logging': {
            'level': 'INFO',
            'structured_format': True,
            'include_stack_trace': True,
            'file_rotation': True,
            'retention_days': 30
        },
        'performance': {
            'collection_interval': 30,
            'history_size': 1000,
            'auto_start': True,
            'metrics': {
                'system': True,
                'application': True,
                'custom': True
            }
        },
        'error_tracking': {
            'max_events': 10000,
            'cleanup_interval': 3600,
            'auto_capture': True,
            'ignored_patterns': [],
            'max_stack_trace_lines': 50
        },
        'alerting': {
            'max_alerts': 10000,
            'auto_start': True,
            'evaluation_interval': 60,
            'default_cooldown': 300,
            'notifications': {
                'email': {
                    'enabled': False,
                    'smtp_host': '',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_email': '',
                    'to_emails': [],
                    'use_tls': True
                },
                'webhook': {
                    'enabled': False,
                    'url': '',
                    'headers': {},
                    'timeout': 30
                }
            }
        },
        'log_analysis': {
            'analysis_interval': 300,
            'max_patterns': 1000,
            'auto_start': True,
            'pattern_min_occurrences': 5,
            'anomaly_threshold': 2.0,
            'trend_window': 100
        }
    }


def load_monitoring_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载监控配置"""
    default_config = get_default_monitoring_config()

    if not config_file:
        # 尝试从环境变量获取配置文件路径
        config_file = os.getenv('MONITORING_CONFIG_FILE')

    if not config_file:
        # 尝试默认位置
        possible_paths = [
            'monitoring_config.json',
            'config/monitoring.json',
            'src/monitoring/config.json',
            os.path.expanduser('~/.1688sync/monitoring.json')
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config_file = path
                break

    if not config_file or not os.path.exists(config_file):
        print(f"监控配置文件未找到，使用默认配置")
        return default_config

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            user_config = json.load(f)

        # 合并配置
        merged_config = merge_configs(default_config, user_config)
        print(f"监控配置已加载: {config_file}")
        return merged_config

    except Exception as e:
        print(f"加载监控配置失败: {e}，使用默认配置")
        return default_config


def merge_configs(default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """合并配置"""
    result = default.copy()

    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def save_monitoring_config(config: Dict[str, Any], config_file: str):
    """保存监控配置"""
    try:
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"监控配置已保存: {config_file}")

    except Exception as e:
        print(f"保存监控配置失败: {e}")


def create_sample_config(config_file: str = "monitoring_config.json"):
    """创建示例配置文件"""
    sample_config = get_default_monitoring_config()

    # 添加示例配置
    sample_config['alerting']['notifications']['email'].update({
        'enabled': True,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'your-email@gmail.com',
        'password': 'your-app-password',
        'from_email': 'monitoring@yourcompany.com',
        'to_emails': ['admin@yourcompany.com']
    })

    sample_config['alerting']['notifications']['webhook'].update({
        'enabled': True,
        'url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK',
        'headers': {
            'Content-Type': 'application/json'
        }
    })

    save_monitoring_config(sample_config, config_file)
    print(f"示例配置文件已创建: {config_file}")
    print("请根据实际环境修改配置文件中的参数")


def validate_config(config: Dict[str, Any]) -> bool:
    """验证配置"""
    try:
        # 验证必需的配置项
        required_sections = ['logging', 'performance', 'error_tracking', 'alerting', 'log_analysis']
        for section in required_sections:
            if section not in config:
                print(f"缺少配置节: {section}")
                return False

        # 验证日志配置
        logging_config = config['logging']
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if logging_config.get('level') not in valid_levels:
            print(f"无效的日志级别: {logging_config.get('level')}")
            return False

        # 验证性能监控配置
        performance_config = config['performance']
        if performance_config.get('collection_interval', 0) <= 0:
            print("collection_interval 必须大于 0")
            return False

        # 验证告警配置
        alerting_config = config['alerting']
        if alerting_config.get('evaluation_interval', 0) <= 0:
            print("evaluation_interval 必须大于 0")
            return False

        # 验证邮件配置（如果启用）
        email_config = alerting_config.get('notifications', {}).get('email', {})
        if email_config.get('enabled'):
            required_email_fields = ['smtp_host', 'smtp_port', 'username', 'password', 'from_email', 'to_emails']
            for field in required_email_fields:
                if not email_config.get(field):
                    print(f"邮件通知启用但缺少配置: {field}")
                    return False

        # 验证Webhook配置（如果启用）
        webhook_config = alerting_config.get('notifications', {}).get('webhook', {})
        if webhook_config.get('enabled') and not webhook_config.get('url'):
            print("Webhook通知启用但缺少URL配置")
            return False

        print("配置验证通过")
        return True

    except Exception as e:
        print(f"配置验证失败: {e}")
        return False


def get_env_overrides() -> Dict[str, Any]:
    """从环境变量获取配置覆盖"""
    overrides = {}

    # 日志级别覆盖
    if 'MONITORING_LOG_LEVEL' in os.environ:
        overrides.setdefault('logging', {})['level'] = os.environ['MONITORING_LOG_LEVEL']

    # 性能监控间隔覆盖
    if 'MONITORING_COLLECTION_INTERVAL' in os.environ:
        try:
            interval = int(os.environ['MONITORING_COLLECTION_INTERVAL'])
            overrides.setdefault('performance', {})['collection_interval'] = interval
        except ValueError:
            pass

    # 告警评估间隔覆盖
    if 'MONITORING_EVALUATION_INTERVAL' in os.environ:
        try:
            interval = int(os.environ['MONITORING_EVALUATION_INTERVAL'])
            overrides.setdefault('alerting', {})['evaluation_interval'] = interval
        except ValueError:
            pass

    # 邮件配置覆盖
    email_vars = {
        'MONITORING_SMTP_HOST': ('notifications', 'email', 'smtp_host'),
        'MONITORING_SMTP_PORT': ('notifications', 'email', 'smtp_port'),
        'MONITORING_SMTP_USERNAME': ('notifications', 'email', 'username'),
        'MONITORING_SMTP_PASSWORD': ('notifications', 'email', 'password'),
        'MONITORING_FROM_EMAIL': ('notifications', 'email', 'from_email'),
    }

    for env_var, config_path in email_vars.items():
        if env_var in os.environ:
            value = os.environ[env_var]
            if env_var.endswith('_PORT'):
                try:
                    value = int(value)
                except ValueError:
                    continue

            current = overrides.setdefault('alerting', {})
            for key in config_path[:-1]:
                current = current.setdefault(key, {})
            current[config_path[-1]] = value

    return overrides


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """应用环境变量覆盖"""
    env_overrides = get_env_overrides()
    if env_overrides:
        config = merge_configs(config, env_overrides)
        print("已应用环境变量覆盖")
    return config