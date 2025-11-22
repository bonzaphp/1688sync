"""
API异常处理模块
"""
from .handlers import setup_exception_handlers
from .custom import (
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ExternalServiceError
)

__all__ = [
    "setup_exception_handlers",
    "ValidationError",
    "NotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ExternalServiceError"
]