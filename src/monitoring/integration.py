"""
监控集成模块 - 提供装饰器、中间件等集成工具
"""

import functools
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from .logger import get_logger
from .monitor import record_timer, increment_counter, set_gauge
from .error_tracker import capture_exception, ErrorSeverity, track_errors


logger = get_logger(__name__)


def monitor_execution(metric_name: str = None, log_args: bool = False,
                    track_errors: bool = True, include_result: bool = False):
    """监控函数执行的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成指标名称
            if metric_name is None:
                name = f"{func.__module__}.{func.__name__}"
            else:
                name = metric_name

            # 开始计时
            start_time = time.time()
            request_id = str(uuid.uuid4())

            # 记录函数开始
            details = {}
            if log_args:
                details['args_count'] = len(args)
                details['kwargs_keys'] = list(kwargs.keys())

            logger.info(
                f"函数开始执行: {func.__name__}",
                function=func.__name__,
                module=func.__module__,
                request_id=request_id,
                details=details
            )

            # 增加调用计数
            increment_counter(f"{name}_calls")

            try:
                # 执行函数
                result = func(*args, **kwargs)

                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录执行时间
                record_timer(f"{name}_duration", duration_ms)

                # 记录成功
                logger.info(
                    f"函数执行完成: {func.__name__}",
                    function=func.__name__,
                    module=func.__module__,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    details={
                        'success': True,
                        'result_type': type(result).__name__ if include_result else None
                    }
                )

                return result

            except Exception as e:
                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录失败
                increment_counter(f"{name}_errors")

                logger.error(
                    f"函数执行失败: {func.__name__} - {str(e)}",
                    function=func.__name__,
                    module=func.__module__,
                    request_id=request_id,
                    duration_ms=duration_ms,
                    exc_info=True
                )

                # 错误追踪
                if track_errors:
                    from .error_tracker import ErrorContext
                    context = ErrorContext(
                        module=func.__module__,
                        function=func.__name__,
                        additional_data={
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys()),
                            'execution_time_ms': duration_ms
                        }
                    )
                    capture_exception(e, context, ErrorSeverity.MEDIUM)

                raise

        return wrapper
    return decorator


def monitor_api_request(endpoint: str = None, method: str = None):
    """监控API请求的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 确定端点和方法
            if endpoint is None:
                ep = f"/{func.__name__}"
            else:
                ep = endpoint

            if method is None:
                m = "GET"
            else:
                m = method.upper()

            start_time = time.time()
            request_id = str(uuid.uuid4())

            try:
                # 增加活跃请求计数
                increment_counter('active_requests')
                set_gauge('active_requests', increment_counter('active_requests'))

                # 记录请求开始
                logger.info(
                    f"API请求开始: {m} {ep}",
                    request_id=request_id,
                    details={
                        'method': m,
                        'endpoint': ep,
                        'event': 'api_request_start'
                    }
                )

                # 执行函数
                result = func(*args, **kwargs)

                # 计算响应时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录成功响应
                status_code = getattr(result, 'status_code', 200) if hasattr(result, 'status_code') else 200
                logger.log_api_request(m, ep, status_code, duration_ms, request_id=request_id)

                # 记录性能指标
                record_timer('api_response_time', duration_ms, {'endpoint': ep, 'method': m})
                increment_counter('api_requests', 1, {'endpoint': ep, 'method': m, 'status': 'success'})

                return result

            except Exception as e:
                # 计算响应时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录错误响应
                logger.log_api_request(m, ep, 500, duration_ms, request_id=request_id)

                # 记录错误指标
                increment_counter('api_requests', 1, {'endpoint': ep, 'method': m, 'status': 'error'})
                increment_counter('api_errors', 1, {'endpoint': ep, 'method': m})

                # 错误追踪
                from .error_tracker import ErrorContext
                context = ErrorContext(
                    request_id=request_id,
                    additional_data={
                        'method': m,
                        'endpoint': ep,
                        'execution_time_ms': duration_ms
                    }
                )
                capture_exception(e, context, ErrorSeverity.HIGH)

                raise

            finally:
                # 减少活跃请求计数
                increment_counter('active_requests', -1)

        return wrapper
    return decorator


def monitor_database_operation(operation: str = None, table: str = None):
    """监控数据库操作的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 确定操作和表名
            op = operation or func.__name__
            tbl = table or 'unknown'

            start_time = time.time()

            try:
                # 执行数据库操作
                result = func(*args, **kwargs)

                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 确定影响的行数
                affected_rows = None
                if isinstance(result, (list, tuple)):
                    affected_rows = len(result)
                elif hasattr(result, 'rowcount'):
                    affected_rows = result.rowcount

                # 记录数据库操作
                logger.log_database_operation(op, tbl, duration_ms, affected_rows)

                # 记录性能指标
                record_timer(f'db_{op}_duration', duration_ms, {'table': tbl})
                increment_counter(f'db_{op}_operations', 1, {'table': tbl})

                return result

            except Exception as e:
                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录失败的数据库操作
                logger.error(
                    f"数据库操作失败: {op} on {tbl} - {str(e)}",
                    details={
                        'operation': op,
                        'table': tbl,
                        'duration_ms': duration_ms
                    },
                    exc_info=True
                )

                # 记录错误指标
                increment_counter(f'db_{op}_errors', 1, {'table': tbl})

                # 错误追踪
                from .error_tracker import ErrorContext
                context = ErrorContext(
                    additional_data={
                        'operation': op,
                        'table': tbl,
                        'execution_time_ms': duration_ms
                    }
                )
                capture_exception(e, context, ErrorSeverity.MEDIUM)

                raise

        return wrapper
    return decorator


def monitor_task_execution(task_name: str = None):
    """监控任务执行的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成任务ID和名称
            task_id = str(uuid.uuid4())
            name = task_name or func.__name__

            start_time = time.time()

            # 记录任务开始
            logger.log_task_start(task_id, name, details={
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys())
            })

            # 增加活跃任务计数
            increment_counter('active_tasks')
            set_gauge('active_tasks', increment_counter('active_tasks'))

            try:
                # 执行任务
                result = func(*args, **kwargs)

                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录任务完成
                logger.log_task_complete(task_id, name, duration_ms, details={
                    'success': True,
                    'result_type': type(result).__name__
                })

                # 记录性能指标
                record_timer('task_duration', duration_ms, {'task_name': name})
                increment_counter('completed_tasks', 1, {'task_name': name})

                return result

            except Exception as e:
                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000

                # 记录任务失败
                logger.log_task_error(task_id, name, e, details={
                    'execution_time_ms': duration_ms
                })

                # 记录错误指标
                increment_counter('failed_tasks', 1, {'task_name': name})

                # 错误追踪
                from .error_tracker import ErrorContext
                context = ErrorContext(
                    task_id=task_id,
                    additional_data={
                        'task_name': name,
                        'execution_time_ms': duration_ms
                    }
                )
                capture_exception(e, context, ErrorSeverity.HIGH)

                raise

            finally:
                # 减少活跃任务计数
                increment_counter('active_tasks', -1)

        return wrapper
    return decorator


class MonitoringContext:
    """监控上下文管理器"""

    def __init__(self, operation_name: str, **tags):
        self.operation_name = operation_name
        self.tags = tags
        self.start_time = None
        self.request_id = str(uuid.uuid4())

    def __enter__(self):
        self.start_time = time.time()
        increment_counter(f"{self.operation_name}_started", 1, self.tags)

        logger.info(
            f"操作开始: {self.operation_name}",
            request_id=self.request_id,
            details={
                'operation': self.operation_name,
                'tags': self.tags,
                'event': 'operation_start'
            }
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            # 成功完成
            increment_counter(f"{self.operation_name}_completed", 1, self.tags)
            record_timer(f"{self.operation_name}_duration", duration_ms, self.tags)

            logger.info(
                f"操作完成: {self.operation_name}",
                request_id=self.request_id,
                duration_ms=duration_ms,
                details={
                    'operation': self.operation_name,
                    'tags': self.tags,
                    'event': 'operation_complete'
                }
            )
        else:
            # 发生异常
            increment_counter(f"{self.operation_name}_failed", 1, self.tags)

            logger.error(
                f"操作失败: {self.operation_name} - {str(exc_val)}",
                request_id=self.request_id,
                duration_ms=duration_ms,
                details={
                    'operation': self.operation_name,
                    'tags': self.tags,
                    'event': 'operation_error'
                },
                exc_info=True
            )

            # 错误追踪
            from .error_tracker import ErrorContext
            context = ErrorContext(
                request_id=self.request_id,
                additional_data={
                    'operation': self.operation_name,
                    'tags': self.tags,
                    'execution_time_ms': duration_ms
                }
            )
            capture_exception(exc_val, context, ErrorSeverity.MEDIUM)

        return False  # 不抑制异常


def monitor_queue_operation(operation: str, queue_name: str):
    """监控队列操作"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)

                # 确定任务数量
                task_count = None
                if isinstance(result, int):
                    task_count = result
                elif isinstance(result, (list, tuple)):
                    task_count = len(result)

                # 记录队列操作
                logger.log_queue_operation(operation, queue_name, task_count)

                # 记录指标
                increment_counter(f'queue_{operation}', 1, {'queue': queue_name})

                # 更新队列深度
                if operation in ['get', 'receive', 'dequeue']:
                    increment_counter(f'queue_{queue_name}_depth', -1)
                elif operation in ['put', 'send', 'enqueue']:
                    increment_counter(f'queue_{queue_name}_depth', 1)

                return result

            except Exception as e:
                # 记录失败的队列操作
                logger.error(
                    f"队列操作失败: {operation} on {queue_name} - {str(e)}",
                    details={
                        'operation': operation,
                        'queue_name': queue_name
                    },
                    exc_info=True
                )

                increment_counter(f'queue_{operation}_errors', 1, {'queue': queue_name})
                raise

        return wrapper
    return decorator


def track_business_metric(metric_name: str, value: float, unit: str = None, **tags):
    """追踪业务指标"""
    set_gauge(f"business_{metric_name}", value, {'unit': unit or '', **tags})
    logger.log_performance_metric(f"business.{metric_name}", value, unit, details=tags)


def track_user_action(user_id: str, action: str, **details):
    """追踪用户行为"""
    logger.log_business_event(
        f"user_action:{action}",
        user_id=user_id,
        details={
            'action': action,
            'user_id': user_id,
            **details
        }
    )

    increment_counter('user_actions', 1, {'action': action, 'user_id': user_id})


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self, name: str):
        self.name = name
        self.measurements = []

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.start_memory = self._get_memory_usage()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        end_memory = self._get_memory_usage()

        duration_ms = (end_time - self.start_time) * 1000
        memory_diff_mb = (end_memory - self.start_memory) / 1024 / 1024

        measurement = {
            'name': self.name,
            'duration_ms': duration_ms,
            'memory_diff_mb': memory_diff_mb,
            'timestamp': datetime.now()
        }

        self.measurements.append(measurement)

        # 记录性能指标
        record_timer(f"profile_{self.name}_duration", duration_ms)
        if memory_diff_mb != 0:
            set_gauge(f"profile_{self.name}_memory_mb", memory_diff_mb)

        logger.info(
            f"性能分析: {self.name}",
            details=measurement
        )

    def _get_memory_usage(self):
        """获取内存使用量"""
        try:
            import psutil
            return psutil.Process().memory_info().rss
        except ImportError:
            return 0

    def get_stats(self):
        """获取统计信息"""
        if not self.measurements:
            return {}

        durations = [m['duration_ms'] for m in self.measurements]
        memory_diffs = [m['memory_diff_mb'] for m in self.measurements]

        return {
            'name': self.name,
            'count': len(self.measurements),
            'duration': {
                'avg': sum(durations) / len(durations),
                'min': min(durations),
                'max': max(durations)
            },
            'memory_diff': {
                'avg': sum(memory_diffs) / len(memory_diffs),
                'min': min(memory_diffs),
                'max': max(memory_diffs)
            }
        }