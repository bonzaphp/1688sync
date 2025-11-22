"""
日志中间件
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.time()

        # 添加时间戳到请求状态
        request.state.timestamp = start_time

        # 获取客户端IP
        client_ip = self._get_client_ip(request)

        # 记录请求信息
        logger.info(
            f"请求开始: {request.method} {request.url.path} "
            f"- 客户端: {client_ip} "
            f"- User-Agent: {request.headers.get('user-agent', 'Unknown')}"
        )

        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录处理异常
            logger.error(
                f"请求处理异常: {request.method} {request.url.path} "
                f"- 客户端: {client_ip} "
                f"- 错误: {str(e)}"
            )
            raise

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录响应信息
        logger.info(
            f"请求完成: {request.method} {request.url.path} "
            f"- 状态码: {response.status_code} "
            f"- 处理时间: {process_time:.3f}s "
            f"- 客户端: {client_ip}"
        )

        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For可能包含多个IP，取第一个
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 回退到直接连接的IP
        return request.client.host if request.client else "unknown"


def setup_logging_middleware(app):
    """设置日志中间件"""
    app.add_middleware(LoggingMiddleware)