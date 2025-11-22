# CLI Utilities
# CLI 工具函数

import os
import sys
import time
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta

import click
from click import echo, style, secho


class ProgressSpinner:
    """进度旋转器"""

    def __init__(self, message: str = "处理中..."):
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current = 0
        self.running = False
        self.thread = None

    def start(self):
        """启动旋转器"""
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """停止旋转器"""
        self.running = False
        if self.thread:
            self.thread.join()
        # 清除当前行
        echo("\r" + " " * (len(self.message) + 10) + "\r", nl=False)

    def _spin(self):
        """旋转动画"""
        while self.running:
            char = self.spinner_chars[self.current]
            echo(f"\r{char} {self.message}", nl=False)
            self.current = (self.current + 1) % len(self.spinner_chars)
            time.sleep(0.1)


class ProgressBar:
    """进度条"""

    def __init__(self, total: int, width: int = 50, show_percent: bool = True, show_eta: bool = True):
        self.total = total
        self.width = width
        self.show_percent = show_percent
        self.show_eta = show_eta
        self.current = 0
        self.start_time = time.time()

    def update(self, current: int, message: str = ""):
        """更新进度"""
        self.current = current
        self._render(message)

    def _render(self, message: str = ""):
        """渲染进度条"""
        if self.total <= 0:
            return

        percent = min(self.current / self.total, 1.0)
        filled_width = int(self.width * percent)
        bar = "█" * filled_width + "░" * (self.width - filled_width)

        parts = [f"\r[{bar}]"]

        if self.show_percent:
            parts.append(f" {percent:.1%}")

        if self.show_eta and self.current > 0:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            eta = str(timedelta(seconds=int(remaining)))
            parts.append(f" ETA: {eta}")

        if message:
            parts.append(f" {message}")

        echo("".join(parts), nl=False)

    def finish(self, message: str = "完成"):
        """完成进度条"""
        self.update(self.total, message)
        echo()  # 换行


class TaskMonitor:
    """任务监控器"""

    def __init__(self, task_id: str, update_interval: float = 1.0):
        self.task_id = task_id
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.last_progress = None

    def start(self, callback: Optional[Callable] = None):
        """启动监控"""
        self.running = True
        self.callback = callback
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor(self):
        """监控任务"""
        try:
            from ...queue.manager import get_queue_manager
        except ImportError:
            # 处理相对导入问题
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from src.queue.manager import get_queue_manager

        manager = get_queue_manager()

        while self.running:
            try:
                task_info = manager.task_manager.get_task_info(self.task_id)
                if task_info:
                    progress = task_info.get('progress')
                    if progress and progress != self.last_progress:
                        if self.callback:
                            self.callback(progress)
                        self.last_progress = progress

                    # 如果任务完成，停止监控
                    status = task_info.get('status')
                    if status in ['completed', 'failed', 'cancelled']:
                        break

                time.sleep(self.update_interval)
            except Exception:
                time.sleep(self.update_interval)


class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
        """格式化表格"""
        if not data:
            return "无数据"

        # 确定表头
        if headers is None:
            headers = list(data[0].keys())

        # 计算列宽
        col_widths = {}
        for header in headers:
            col_widths[header] = len(header)

        for row in data:
            for header in headers:
                value = str(row.get(header, ''))
                col_widths[header] = max(col_widths[header], len(value))

        # 构建表格
        lines = []

        # 表头
        header_line = " | ".join(
            header.ljust(col_widths[header]) for header in headers
        )
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # 数据行
        for row in data:
            data_line = " | ".join(
                str(row.get(header, '')).ljust(col_widths[header]) for header in headers
            )
            lines.append(data_line)

        return "\n".join(lines)

    @staticmethod
    def format_dict(data: Dict[str, Any], indent: int = 0) -> str:
        """格式化字典"""
        lines = []
        prefix = "  " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(OutputFormatter.format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        lines.append(OutputFormatter.format_dict(item, indent + 2))
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")

        return "\n".join(lines)

    @staticmethod
    def format_json(data: Any) -> str:
        """格式化JSON"""
        import json
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def format_yaml(data: Any) -> str:
        """格式化YAML"""
        import yaml
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)


class ColorFormatter:
    """颜色格式化器"""

    @staticmethod
    def status_color(status: str) -> str:
        """根据状态返回颜色"""
        status_colors = {
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'pending': 'yellow',
            'cancelled': 'magenta'
        }
        color = status_colors.get(status.lower(), 'white')
        return style(status, fg=color)

    @staticmethod
    def priority_color(priority: str) -> str:
        """根据优先级返回颜色"""
        priority_colors = {
            'high': 'red',
            'medium': 'yellow',
            'low': 'green'
        }
        color = priority_colors.get(priority.lower(), 'white')
        return style(priority, fg=color)

    @staticmethod
    def progress_color(percent: float) -> str:
        """根据进度百分比返回颜色"""
        if percent >= 80:
            color = 'green'
        elif percent >= 50:
            color = 'yellow'
        else:
            color = 'red'
        return style(f"{percent:.1f}%", fg=color)


class InteractivePrompts:
    """交互式提示"""

    @staticmethod
    def confirm_action(message: str, default: bool = False) -> bool:
        """确认操作"""
        return click.confirm(message, default=default)

    @staticmethod
    def select_option(message: str, options: List[str], default: Optional[str] = None) -> str:
        """选择选项"""
        return click.prompt(
            message,
            type=click.Choice(options),
            default=default
        )

    @staticmethod
    def input_text(message: str, default: str = "", required: bool = False) -> str:
        """输入文本"""
        return click.prompt(
            message,
            default=default,
            show_default=True,
            type=str if required else click.STRING
        )

    @staticmethod
    def input_number(message: str, default: Optional[int] = None, min_val: Optional[int] = None) -> int:
        """输入数字"""
        return click.prompt(
            message,
            default=default,
            type=click.IntRange(min=min_val) if min_val else click.INT
        )

    @staticmethod
    def input_password(message: str) -> str:
        """输入密码"""
        return click.prompt(message, hide_input=True)


class FileOperations:
    """文件操作"""

    @staticmethod
    def ensure_dir(path: str) -> bool:
        """确保目录存在"""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def backup_file(file_path: str) -> str:
        """备份文件"""
        if not os.path.exists(file_path):
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"

        try:
            import shutil
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception:
            return ""

    @staticmethod
    def safe_write(file_path: str, content: str, backup: bool = True) -> bool:
        """安全写入文件"""
        try:
            if backup and os.path.exists(file_path):
                FileOperations.backup_file(file_path)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False


class ValidationHelpers:
    """验证辅助函数"""

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return email_pattern.match(email) is not None

    @staticmethod
    def validate_json(json_str: str) -> bool:
        """验证JSON格式"""
        try:
            import json
            json.loads(json_str)
            return True
        except Exception:
            return False

    @staticmethod
    def validate_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """验证日期格式"""
        try:
            datetime.strptime(date_str, format)
            return True
        except Exception:
            return False


# 便捷函数
def print_success(message: str):
    """打印成功消息"""
    secho(f"✓ {message}", fg='green', bold=True)


def print_error(message: str):
    """打印错误消息"""
    secho(f"✗ {message}", fg='red', bold=True)


def print_warning(message: str):
    """打印警告消息"""
    secho(f"⚠ {message}", fg='yellow', bold=True)


def print_info(message: str):
    """打印信息消息"""
    secho(f"ℹ {message}", fg='blue')


def print_header(message: str):
    """打印标题"""
    echo()
    secho("=" * 50, fg='blue')
    secho(f"  {message}", fg='blue', bold=True)
    secho("=" * 50, fg='blue')


def print_section(message: str):
    """打印章节"""
    echo()
    secho(f"--- {message} ---", fg='cyan')