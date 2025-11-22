"""
计时中间件
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """计时中间件"""

    def __init__(self, app, slow_request_threshold: float = 5.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录开始时间
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录慢请求
        if process_time > self.slow_request_threshold:
            logger.warning(
                f"慢请求检测: {request.method} {request.url.path} "
                f"- 处理时间: {process_time:.3f}s "
                f"- 阈值: {self.slow_request_threshold}s"
            )

        # 添加性能指标头
        response.headers["X-Response-Time"] = f"{process_time:.3f}s"

        return response


def setup_timing_middleware(app, slow_request_threshold: float = 5.0):
    """设置计时中间件"""
    app.add_middleware(TimingMiddleware, slow_request_threshold=slow_request_threshold)