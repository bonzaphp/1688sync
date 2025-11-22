"""
异常处理器
"""
import logging
from typing import Union
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as PydanticValidationError
import traceback

from .custom import BaseAPIException

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""

    @app.exception_handler(BaseAPIException)
    async def api_exception_handler(request: Request, exc: BaseAPIException):
        """处理自定义API异常"""
        logger.error(f"API异常: {exc.code} - {exc.message}")
        if exc.details:
            logger.error(f"异常详情: {exc.details}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理HTTP异常"""
        logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "details": {}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理Starlette HTTP异常"""
        logger.warning(f"Starlette HTTP异常: {exc.status_code} - {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": exc.detail,
                    "details": {}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证异常"""
        logger.warning(f"请求验证异常: {exc.errors()}")

        # 格式化验证错误
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数验证失败",
                    "details": {"errors": errors}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
        """处理Pydantic验证异常"""
        logger.warning(f"Pydantic验证异常: {exc.errors()}")

        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "数据验证失败",
                    "details": {"errors": errors}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """处理值错误"""
        logger.warning(f"值错误: {str(exc)}")

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "VALUE_ERROR",
                    "message": str(exc),
                    "details": {}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        """处理权限错误"""
        logger.warning(f"权限错误: {str(exc)}")

        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "code": "PERMISSION_ERROR",
                    "message": str(exc),
                    "details": {}
                },
                "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        # 记录详细的错误信息
        logger.error(f"未处理的异常: {type(exc).__name__} - {str(exc)}")
        logger.error(f"异常堆栈: {traceback.format_exc()}")

        # 在调试模式下返回详细错误信息
        from ..config import settings
        if settings.api_debug:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": str(exc),
                        "type": type(exc).__name__,
                        "details": {
                            "traceback": traceback.format_exc()
                        }
                    },
                    "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
                }
            )
        else:
            # 生产模式下隐藏敏感信息
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "服务器内部错误",
                        "details": {}
                    },
                    "timestamp": request.state.timestamp if hasattr(request.state, 'timestamp') else None
                }
            )