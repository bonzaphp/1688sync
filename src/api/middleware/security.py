"""
安全中间件
"""
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app, https_required: bool = False):
        super().__init__(app)
        self.https_required = https_required

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # HTTPS重定向检查
        if self.https_required and self._is_insecure(request):
            logger.warning(f"不安全的连接被拒绝: {request.url}")
            raise HTTPException(
                status_code=400,
                detail="HTTPS连接是必需的"
            )

        # 添加安全头
        response = await call_next(request)
        self._add_security_headers(response)

        return response

    def _is_insecure(self, request: Request) -> bool:
        """检查是否为不安全连接"""
        # 检查URL协议
        if request.url.scheme != "https":
            return True

        # 检查代理头
        forwarded_proto = request.headers.get("X-Forwarded-Proto")
        if forwarded_proto and forwarded_proto.lower() != "https":
            return True

        return False

    def _add_security_headers(self, response: Response):
        """添加安全头"""
        # 防止点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 防止MIME类型嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS保护
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 强制HTTPS（仅在HTTPS连接下）
        if response.scope.get("scheme") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 内容安全策略（简化版）
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # 引用策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略（替代Feature-Policy）
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"


def setup_security_middleware(app, https_required: bool = False):
    """设置安全中间件"""
    app.add_middleware(SecurityMiddleware, https_required=https_required)