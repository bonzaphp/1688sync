"""
错误追踪系统 - 捕获、分析和追踪应用程序错误
"""

import hashlib
import inspect
import threading
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from functools import wraps

from .logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorStatus(Enum):
    """错误状态"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"


@dataclass
class ErrorContext:
    """错误上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    task_id: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class ErrorEvent:
    """错误事件"""
    id: str
    fingerprint: str
    error_type: str
    message: str
    severity: ErrorSeverity
    status: ErrorStatus
    context: ErrorContext
    stack_trace: str
    timestamp: datetime
    occurrence_count: int = 1
    first_seen: datetime = None
    last_seen: datetime = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.first_seen is None:
            self.first_seen = self.timestamp
        if self.last_seen is None:
            self.last_seen = self.timestamp
        if self.tags is None:
            self.tags = []


@dataclass
class ErrorPattern:
    """错误模式"""
    fingerprint: str
    error_type: str
    pattern_message: str
    severity: ErrorSeverity
    total_occurrences: int
    first_occurrence: datetime
    last_occurrence: datetime
    affected_modules: Set[str]
    affected_functions: Set[str]
    frequency_trend: str  # increasing, decreasing, stable
    suggested_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['affected_modules'] = list(self.affected_modules)
        result['affected_functions'] = list(self.affected_functions)
        return result


class ErrorTracker:
    """错误追踪器"""

    def __init__(self, max_events: int = 10000, cleanup_interval: int = 3600):
        self.max_events = max_events
        self.cleanup_interval = cleanup_interval
        self.cleanup_active = False
        self.cleanup_thread: Optional[threading.Thread] = None

        # 错误存储
        self.error_events: Dict[str, ErrorEvent] = {}  # fingerprint -> ErrorEvent
        self.error_history: deque = deque(maxlen=max_events)
        self.error_patterns: Dict[str, ErrorPattern] = {}

        # 统计信息
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_counts_by_type: Dict[str, int] = defaultdict(int)
        self.error_counts_by_severity: Dict[ErrorSeverity, int] = defaultdict(int)

        # 回调函数
        self.error_callbacks: List[Callable[[ErrorEvent], None]] = []
        self.pattern_callbacks: List[Callable[[ErrorPattern], None]] = []

        # 忽略的错误模式
        self.ignored_patterns: Set[str] = set()

        self._lock = threading.Lock()

        # 启动清理线程
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """启动清理线程"""
        self.cleanup_active = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_loop(self):
        """清理循环"""
        while self.cleanup_active:
            try:
                self._cleanup_old_errors()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error("错误追踪清理循环异常", exc_info=True)

    def _cleanup_old_errors(self):
        """清理旧错误"""
        try:
            cutoff_time = datetime.now() - timedelta(days=30)

            with self._lock:
                # 清理历史事件
                while (self.error_history and
                       self.error_history[0].timestamp < cutoff_time):
                    self.error_history.popleft()

                # 清理已解决的错误事件
                resolved_fingerprints = [
                    fp for fp, event in self.error_events.items()
                    if event.status == ErrorStatus.RESOLVED and
                    event.resolved_at and event.resolved_at < cutoff_time
                ]

                for fp in resolved_fingerprints:
                    del self.error_events[fp]

            logger.debug(f"清理了 {len(resolved_fingerprints)} 个已解决的错误事件")

        except Exception as e:
            logger.error("清理旧错误失败", exc_info=True)

    def capture_exception(self, exception: Exception, context: ErrorContext = None,
                         severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                         tags: List[str] = None) -> ErrorEvent:
        """捕获异常"""
        try:
            # 生成错误指纹
            fingerprint = self._generate_fingerprint(exception)

            # 检查是否应该忽略
            if self._should_ignore_error(fingerprint, exception):
                return None

            # 获取堆栈跟踪
            stack_trace = traceback.format_exc()

            # 提取调用信息
            frame_info = self._extract_frame_info()

            # 创建上下文
            if context is None:
                context = ErrorContext()

            context.module = context.module or frame_info.get('module')
            context.function = context.function or frame_info.get('function')
            context.line_number = context.line_number or frame_info.get('line_number')

            timestamp = datetime.now()

            # 检查是否为重复错误
            if fingerprint in self.error_events:
                existing_event = self.error_events[fingerprint]
                existing_event.occurrence_count += 1
                existing_event.last_seen = timestamp
                existing_event.status = ErrorStatus.OPEN  # 重新打开
                existing_event.tags.extend(tags or [])

                # 更新统计
                self.error_counts[fingerprint] += 1
                self.error_counts_by_type[exception.__class__.__name__] += 1
                self.error_counts_by_severity[severity] += 1

                # 调用回调
                self._trigger_error_callbacks(existing_event)

                return existing_event

            # 创建新的错误事件
            error_event = ErrorEvent(
                id=self._generate_event_id(),
                fingerprint=fingerprint,
                error_type=exception.__class__.__name__,
                message=str(exception),
                severity=severity,
                status=ErrorStatus.OPEN,
                context=context,
                stack_trace=stack_trace,
                timestamp=timestamp,
                tags=tags or []
            )

            # 存储错误事件
            with self._lock:
                self.error_events[fingerprint] = error_event
                self.error_history.append(error_event)
                self.error_counts[fingerprint] = 1
                self.error_counts_by_type[exception.__class__.__name__] += 1
                self.error_counts_by_severity[severity] += 1

            # 更新错误模式
            self._update_error_pattern(error_event)

            # 调用回调
            self._trigger_error_callbacks(error_event)

            # 记录日志
            logger.error(
                f"捕获异常: {error_event.error_type} - {error_event.message}",
                details={
                    'error_id': error_event.id,
                    'fingerprint': fingerprint,
                    'severity': severity.value,
                    'occurrence_count': error_event.occurrence_count
                }
            )

            return error_event

        except Exception as e:
            logger.error("捕获异常失败", exc_info=True)
            return None

    def _generate_fingerprint(self, exception: Exception) -> str:
        """生成错误指纹"""
        try:
            # 使用异常类型、消息和堆栈跟踪的前几行生成指纹
            stack_lines = traceback.format_exc().split('\n')[:10]
            fingerprint_data = {
                'type': exception.__class__.__name__,
                'message': str(exception)[:200],  # 限制消息长度
                'stack': '\n'.join(stack_lines)
            }

            fingerprint_str = str(sorted(fingerprint_data.items()))
            return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]

        except Exception:
            # 降级处理
            return hashlib.md5(f"{type(exception).__name__}{str(exception)}".encode()).hexdigest()[:16]

    def _should_ignore_error(self, fingerprint: str, exception: Exception) -> bool:
        """检查是否应该忽略错误"""
        # 检查忽略模式
        if fingerprint in self.ignored_patterns:
            return True

        # 检查特定错误类型
        ignored_types = ['KeyboardInterrupt', 'SystemExit']
        if exception.__class__.__name__ in ignored_types:
            return True

        # 检查特定消息模式
        message_patterns = ['Connection aborted', 'Connection reset by peer']
        for pattern in message_patterns:
            if pattern in str(exception):
                return True

        return False

    def _extract_frame_info(self) -> Dict[str, Any]:
        """提取调用栈信息"""
        try:
            frame = inspect.currentframe()
            # 跳过当前帧和几个内部帧
            for _ in range(3):
                frame = frame.f_back
                if frame is None:
                    break

            if frame:
                return {
                    'module': frame.f_globals.get('__name__'),
                    'function': frame.f_code.co_name,
                    'line_number': frame.f_lineno
                }

        except Exception:
            pass

        return {}

    def _generate_event_id(self) -> str:
        """生成事件ID"""
        return f"error_{int(time.time() * 1000)}_{hash(str(time.time())) % 10000}"

    def _update_error_pattern(self, error_event: ErrorEvent):
        """更新错误模式"""
        try:
            fingerprint = error_event.fingerprint

            if fingerprint not in self.error_patterns:
                self.error_patterns[fingerprint] = ErrorPattern(
                    fingerprint=fingerprint,
                    error_type=error_event.error_type,
                    pattern_message=self._extract_pattern_message(error_event.message),
                    severity=error_event.severity,
                    total_occurrences=1,
                    first_occurrence=error_event.timestamp,
                    last_occurrence=error_event.timestamp,
                    affected_modules=set(),
                    affected_functions=set(),
                    frequency_trend="stable",
                    suggested_actions=self._generate_suggested_actions(error_event)
                )

            pattern = self.error_patterns[fingerprint]
            pattern.total_occurrences += 1
            pattern.last_occurrence = error_event.timestamp

            if error_event.context.module:
                pattern.affected_modules.add(error_event.context.module)
            if error_event.context.function:
                pattern.affected_functions.add(error_event.context.function)

            # 更新频率趋势
            pattern.frequency_trend = self._calculate_frequency_trend(fingerprint)

            # 调用模式回调
            self._trigger_pattern_callbacks(pattern)

        except Exception as e:
            logger.error("更新错误模式失败", exc_info=True)

    def _extract_pattern_message(self, message: str) -> str:
        """提取模式消息"""
        # 移除具体的ID、数字等，保留通用模式
        import re
        pattern = re.sub(r'\d+', '{N}', message)  # 替换数字
        pattern = re.sub(r'[a-f0-9]{8,}', '{ID}', pattern)  # 替换ID
        return pattern[:200]  # 限制长度

    def _calculate_frequency_trend(self, fingerprint: str) -> str:
        """计算频率趋势"""
        try:
            # 获取最近24小时和前24小时的错误数量
            now = datetime.now()
            recent_24h = now - timedelta(hours=24)
            previous_24h = now - timedelta(hours=48)

            recent_count = sum(
                1 for event in self.error_history
                if event.fingerprint == fingerprint and event.timestamp >= recent_24h
            )
            previous_count = sum(
                1 for event in self.error_history
                if (event.fingerprint == fingerprint and
                    previous_24h <= event.timestamp < recent_24h)
            )

            if recent_count > previous_count * 1.2:
                return "increasing"
            elif recent_count < previous_count * 0.8:
                return "decreasing"
            else:
                return "stable"

        except Exception:
            return "stable"

    def _generate_suggested_actions(self, error_event: ErrorEvent) -> List[str]:
        """生成建议操作"""
        actions = []

        error_type = error_event.error_type
        message = error_event.message.lower()

        # 基于错误类型的建议
        if error_type == 'ConnectionError':
            actions.extend([
                "检查网络连接",
                "验证服务端点可用性",
                "考虑添加重试机制"
            ])
        elif error_type == 'TimeoutError':
            actions.extend([
                "增加超时时间",
                "检查网络延迟",
                "优化查询性能"
            ])
        elif error_type == 'ValueError':
            actions.extend([
                "验证输入参数",
                "添加参数校验",
                "检查数据格式"
            ])
        elif error_type == 'KeyError':
            actions.extend([
                "检查字典键是否存在",
                "使用get()方法",
                "添加默认值处理"
            ])

        # 基于消息模式的建议
        if 'database' in message or 'sql' in message:
            actions.extend([
                "检查数据库连接",
                "验证SQL语法",
                "检查数据库权限"
            ])

        if 'memory' in message:
            actions.extend([
                "检查内存使用",
                "优化内存管理",
                "考虑增加内存"
            ])

        if not actions:
            actions.append("分析错误上下文和堆栈跟踪")

        return actions

    def _trigger_error_callbacks(self, error_event: ErrorEvent):
        """触发错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error_event)
            except Exception as e:
                logger.error(f"错误回调函数执行失败: {e}")

    def _trigger_pattern_callbacks(self, error_pattern: ErrorPattern):
        """触发模式回调"""
        for callback in self.pattern_callbacks:
            try:
                callback(error_pattern)
            except Exception as e:
                logger.error(f"模式回调函数执行失败: {e}")

    def get_error(self, error_id: str) -> Optional[ErrorEvent]:
        """获取错误事件"""
        with self._lock:
            for event in self.error_events.values():
                if event.id == error_id:
                    return event
        return None

    def get_errors_by_status(self, status: ErrorStatus, limit: int = 100) -> List[ErrorEvent]:
        """根据状态获取错误"""
        with self._lock:
            errors = [
                event for event in self.error_events.values()
                if event.status == status
            ]
            # 按最后发生时间排序
            errors.sort(key=lambda x: x.last_seen, reverse=True)
            return errors[:limit]

    def get_errors_by_severity(self, severity: ErrorSeverity, limit: int = 100) -> List[ErrorEvent]:
        """根据严重程度获取错误"""
        with self._lock:
            errors = [
                event for event in self.error_events.values()
                if event.severity == severity
            ]
            errors.sort(key=lambda x: x.last_seen, reverse=True)
            return errors[:limit]

    def get_error_patterns(self, min_occurrences: int = 5) -> List[ErrorPattern]:
        """获取错误模式"""
        with self._lock:
            patterns = [
                pattern for pattern in self.error_patterns.values()
                if pattern.total_occurrences >= min_occurrences
            ]
            # 按发生次数排序
            patterns.sort(key=lambda x: x.total_occurrences, reverse=True)
            return patterns

    def resolve_error(self, error_id: str, resolved_by: str, resolution_notes: str = None):
        """解决错误"""
        try:
            error_event = self.get_error(error_id)
            if not error_event:
                logger.warning(f"错误事件不存在: {error_id}")
                return False

            error_event.status = ErrorStatus.RESOLVED
            error_event.resolved_at = datetime.now()
            error_event.resolved_by = resolved_by
            error_event.resolution_notes = resolution_notes

            logger.info(f"错误已解决: {error_id}", details={
                'resolved_by': resolved_by,
                'resolution_notes': resolution_notes
            })

            return True

        except Exception as e:
            logger.error(f"解决错误失败: {e}")
            return False

    def ignore_error_pattern(self, fingerprint: str):
        """忽略错误模式"""
        self.ignored_patterns.add(fingerprint)
        logger.info(f"错误模式已忽略: {fingerprint}")

    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误统计"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            with self._lock:
                recent_errors = [
                    event for event in self.error_history
                    if event.timestamp >= cutoff_time
                ]

            # 按严重程度统计
            severity_counts = defaultdict(int)
            type_counts = defaultdict(int)
            status_counts = defaultdict(int)

            for error in recent_errors:
                severity_counts[error.severity.value] += 1
                type_counts[error.error_type] += 1
                status_counts[error.status.value] += 1

            # 计算错误率
            total_errors = len(recent_errors)
            error_rate = total_errors / hours if hours > 0 else 0

            return {
                'time_range_hours': hours,
                'total_errors': total_errors,
                'error_rate_per_hour': error_rate,
                'by_severity': dict(severity_counts),
                'by_type': dict(type_counts),
                'by_status': dict(status_counts),
                'top_errors': [
                    {
                        'error_type': error_type,
                        'count': count
                    }
                    for error_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
            }

        except Exception as e:
            logger.error("获取错误统计失败", exc_info=True)
            return {'error': str(e)}

    def add_error_callback(self, callback: Callable[[ErrorEvent], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)

    def add_pattern_callback(self, callback: Callable[[ErrorPattern], None]):
        """添加模式回调函数"""
        self.pattern_callbacks.append(callback)

    def export_errors(self, format: str = "json", status: ErrorStatus = None) -> str:
        """导出错误数据"""
        try:
            with self._lock:
                errors = list(self.error_events.values())

                if status:
                    errors = [e for e in errors if e.status == status]

            if format.lower() == "json":
                import json
                export_data = {
                    'exported_at': datetime.now().isoformat(),
                    'total_errors': len(errors),
                    'errors': [asdict(error) for error in errors]
                }
                return json.dumps(export_data, indent=2, default=str)

            else:
                raise ValueError(f"不支持的导出格式: {format}")

        except Exception as e:
            logger.error("导出错误数据失败", exc_info=True)
            return f"导出失败: {e}"

    def cleanup(self):
        """清理资源"""
        self.cleanup_active = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=10)
        logger.info("错误追踪器已清理")


# 全局错误追踪器实例
error_tracker = ErrorTracker()

# 便捷装饰器
def track_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM, tags: List[str] = None):
    """错误追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 创建上下文
                context = ErrorContext(
                    module=func.__module__,
                    function=func.__name__,
                    additional_data={
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
                error_tracker.capture_exception(e, context, severity, tags)
                raise
        return wrapper
    return decorator

# 便捷函数
def capture_exception(exception: Exception, context: ErrorContext = None,
                     severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                     tags: List[str] = None) -> ErrorEvent:
    """捕获异常"""
    return error_tracker.capture_exception(exception, context, severity, tags)