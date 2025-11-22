"""
结构化日志记录器 - 提供统一的日志记录接口和格式化功能
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, asdict

from ..config import get_settings


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """日志上下文"""
    task_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class LogEntry:
    """结构化日志条目"""
    timestamp: str
    level: str
    message: str
    context: LogContext
    details: Dict[str, Any]
    error: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        if self.context:
            result['context'] = asdict(self.context)
        return result


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_stack_trace: bool = True):
        super().__init__()
        self.include_stack_trace = include_stack_trace

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 创建日志条目
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            context=self._extract_context(record),
            details=getattr(record, 'details', {}),
            error=self._extract_error_info(record),
            duration_ms=getattr(record, 'duration_ms', None),
            stack_trace=traceback.format_exc() if record.exc_info and self.include_stack_trace else None
        )

        # 转换为JSON格式
        return json.dumps(log_entry.to_dict(), ensure_ascii=False, default=str)

    def _extract_context(self, record: logging.LogRecord) -> LogContext:
        """提取日志上下文"""
        return LogContext(
            task_id=getattr(record, 'task_id', None),
            request_id=getattr(record, 'request_id', None),
            user_id=getattr(record, 'user_id', None),
            session_id=getattr(record, 'session_id', None),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            extra=getattr(record, 'extra', {})
        )

    def _extract_error_info(self, record: logging.LogRecord) -> Optional[Dict[str, Any]]:
        """提取错误信息"""
        if not record.exc_info:
            return None

        exc_type, exc_value, _ = record.exc_info
        return {
            'type': exc_type.__name__ if exc_type else None,
            'message': str(exc_value) if exc_value else None,
            'module': getattr(exc_type, '__module__', None) if exc_type else None
        }


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str = "1688sync"):
        self.name = name
        self.settings = get_settings()
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 清除现有处理器
        self.logger.handlers.clear()

        # 设置日志级别
        log_level = getattr(logging, self.settings.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # 创建格式化器
        formatter = StructuredFormatter(include_stack_trace=self.settings.debug)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器
        if self.settings.storage_path:
            self._setup_file_handlers(formatter)

        # 错误文件处理器
        if self.settings.sentry_dsn or self.settings.debug:
            self._setup_error_handler(formatter)

    def _setup_file_handlers(self, formatter: StructuredFormatter):
        """设置文件处理器"""
        log_dir = Path(self.settings.storage_path) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # 主日志文件（按日期轮转）
        main_log = log_dir / f"{self.name}.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            main_log,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        # 调试日志文件
        debug_log = log_dir / f"{self.name}-debug.log"
        debug_handler = logging.handlers.TimedRotatingFileHandler(
            debug_log,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(debug_handler)

    def _setup_error_handler(self, formatter: StructuredFormatter):
        """设置错误处理器"""
        log_dir = Path(self.settings.storage_path) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        error_log = log_dir / f"{self.name}-error.log"
        error_handler = logging.handlers.TimedRotatingFileHandler(
            error_log,
            when='midnight',
            interval=1,
            backupCount=90,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        self.logger.addHandler(error_handler)

    def _log(self, level: LogLevel, message: str, **kwargs):
        """内部日志记录方法"""
        # 创建日志记录
        extra = {
            'task_id': kwargs.get('task_id'),
            'request_id': kwargs.get('request_id'),
            'user_id': kwargs.get('user_id'),
            'session_id': kwargs.get('session_id'),
            'details': kwargs.get('details', {}),
            'duration_ms': kwargs.get('duration_ms'),
            'extra': kwargs.get('extra', {})
        }

        # 获取对应的logging级别
        log_level = getattr(logging, level.value)

        # 记录日志
        if level in [LogLevel.ERROR, LogLevel.CRITICAL] and kwargs.get('exc_info'):
            self.logger.log(log_level, message, exc_info=True, extra=extra)
        else:
            self.logger.log(log_level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """记录一般信息"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = True, **kwargs):
        """记录错误"""
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """记录严重错误"""
        self._log(LogLevel.CRITICAL, message, exc_info=exc_info, **kwargs)

    def log_task_start(self, task_id: str, task_name: str, **kwargs):
        """记录任务开始"""
        self.info(
            f"任务开始: {task_name}",
            task_id=task_id,
            details={
                'task_name': task_name,
                'event': 'task_start',
                **kwargs.get('details', {})
            },
            **kwargs
        )

    def log_task_complete(self, task_id: str, task_name: str, duration_ms: float, **kwargs):
        """记录任务完成"""
        self.info(
            f"任务完成: {task_name}",
            task_id=task_id,
            duration_ms=duration_ms,
            details={
                'task_name': task_name,
                'event': 'task_complete',
                'duration_seconds': duration_ms / 1000,
                **kwargs.get('details', {})
            },
            **kwargs
        )

    def log_task_error(self, task_id: str, task_name: str, error: Exception, **kwargs):
        """记录任务错误"""
        self.error(
            f"任务失败: {task_name} - {str(error)}",
            task_id=task_id,
            details={
                'task_name': task_name,
                'event': 'task_error',
                'error_type': type(error).__name__,
                'error_message': str(error),
                **kwargs.get('details', {})
            },
            exc_info=True,
            **kwargs
        )

    def log_api_request(self, method: str, path: str, status_code: int,
                       duration_ms: float, **kwargs):
        """记录API请求"""
        level = LogLevel.INFO if status_code < 400 else LogLevel.WARNING if status_code < 500 else LogLevel.ERROR

        self._log(
            level,
            f"API请求: {method} {path} - {status_code}",
            details={
                'event': 'api_request',
                'method': method,
                'path': path,
                'status_code': status_code,
                'duration_ms': duration_ms,
                **kwargs.get('details', {})
            },
            duration_ms=duration_ms,
            **kwargs
        )

    def log_database_operation(self, operation: str, table: str, duration_ms: float,
                             affected_rows: int = None, **kwargs):
        """记录数据库操作"""
        self.info(
            f"数据库操作: {operation} on {table}",
            details={
                'event': 'database_operation',
                'operation': operation,
                'table': table,
                'affected_rows': affected_rows,
                **kwargs.get('details', {})
            },
            duration_ms=duration_ms,
            **kwargs
        )

    def log_queue_operation(self, operation: str, queue_name: str, task_count: int = None,
                          **kwargs):
        """记录队列操作"""
        self.info(
            f"队列操作: {operation} on {queue_name}",
            details={
                'event': 'queue_operation',
                'operation': operation,
                'queue_name': queue_name,
                'task_count': task_count,
                **kwargs.get('details', {})
            },
            **kwargs
        )

    def log_performance_metric(self, metric_name: str, value: float, unit: str = None,
                             **kwargs):
        """记录性能指标"""
        self.info(
            f"性能指标: {metric_name} = {value}{' ' + unit if unit else ''}",
            details={
                'event': 'performance_metric',
                'metric_name': metric_name,
                'value': value,
                'unit': unit,
                **kwargs.get('details', {})
            },
            **kwargs
        )

    def log_business_event(self, event_name: str, **kwargs):
        """记录业务事件"""
        self.info(
            f"业务事件: {event_name}",
            details={
                'event': 'business_event',
                'event_name': event_name,
                **kwargs.get('details', {})
            },
            **kwargs
        )

    def create_child_logger(self, module_name: str) -> 'StructuredLogger':
        """创建子日志记录器"""
        child_name = f"{self.name}.{module_name}"
        child_logger = StructuredLogger(child_name)
        return child_logger

    def set_level(self, level: LogLevel):
        """设置日志级别"""
        log_level = getattr(logging, level.value)
        self.logger.setLevel(log_level)

    def get_log_files(self) -> List[str]:
        """获取日志文件列表"""
        log_dir = Path(self.settings.storage_path) / "logs"
        if not log_dir.exists():
            return []

        return [str(f) for f in log_dir.glob("*.log")]

    def get_recent_logs(self, lines: int = 100, level: LogLevel = None) -> List[str]:
        """获取最近的日志"""
        log_files = self.get_log_files()
        if not log_files:
            return []

        # 读取最新的日志文件
        latest_log = max(log_files, key=os.path.getctime)

        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            # 过滤级别
            if level:
                all_lines = [line for line in all_lines if level.value in line]

            # 返回最后N行
            return all_lines[-lines:] if len(all_lines) > lines else all_lines

        except Exception as e:
            self.error(f"读取日志文件失败: {e}")
            return []

    def cleanup_old_logs(self, days: int = 30):
        """清理旧日志文件"""
        log_dir = Path(self.settings.storage_path) / "logs"
        if not log_dir.exists():
            return

        cutoff_time = time.time() - (days * 24 * 3600)
        cleaned_count = 0

        for log_file in log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    self.error(f"删除日志文件失败 {log_file}: {e}")

        self.info(f"清理了 {cleaned_count} 个旧日志文件", details={'cleaned_files': cleaned_count})


# 全局日志记录器实例
structured_logger = StructuredLogger()

# 便捷函数
def get_logger(name: str = None) -> StructuredLogger:
    """获取日志记录器实例"""
    if name:
        return structured_logger.create_child_logger(name)
    return structured_logger