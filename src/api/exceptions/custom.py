"""
自定义异常类
"""
from typing import Any, Dict, Optional


class BaseAPIException(Exception):
    """API基础异常类"""
    def __init__(
        self,
        message: str,
        code: str = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAPIException):
    """验证错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class NotFoundError(BaseAPIException):
    """资源不存在错误"""
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource}不存在"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


class AuthenticationError(BaseAPIException):
    """认证错误"""
    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(BaseAPIException):
    """授权错误"""
    def __init__(self, message: str = "权限不足", permission: str = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details={"permission": permission}
        )


class BusinessLogicError(BaseAPIException):
    """业务逻辑错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            status_code=422,
            details=details
        )


class ExternalServiceError(BaseAPIException):
    """外部服务错误"""
    def __init__(
        self,
        service: str,
        message: str = "外部服务调用失败",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, **(details or {})}
        )


class DatabaseError(BaseAPIException):
    """数据库错误"""
    def __init__(self, message: str = "数据库操作失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class RateLimitError(BaseAPIException):
    """频率限制错误"""
    def __init__(self, limit: int, window: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"请求过于频繁，限制为{limit}次/{window}秒",
            code="RATE_LIMIT_ERROR",
            status_code=429,
            details={"limit": limit, "window": window, **(details or {})}
        )


class ConfigurationError(BaseAPIException):
    """配置错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"配置错误: {message}",
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )