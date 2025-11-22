"""
频率限制中间件
"""
import time
import logging
from typing import Callable, Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """频率限制器"""

    def __init__(self, limit: int, window: int):
        self.limit = limit  # 限制次数
        self.window = window  # 时间窗口（秒）
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        requests = self.requests[key]

        # 清理过期的请求记录
        while requests and requests[0] <= now - self.window:
            requests.popleft()

        # 检查是否超过限制
        if len(requests) >= self.limit:
            return False

        # 记录当前请求
        requests.append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """获取剩余请求次数"""
        now = time.time()
        requests = self.requests[key]

        # 清理过期的请求记录
        while requests and requests[0] <= now - self.window:
            requests.popleft()

        return max(0, self.limit - len(requests))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """频率限制中间件"""

    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,
        limits: Optional[Dict[str, Dict[str, int]]] = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.limits = limits or {}

        # 创建不同路径的频率限制器
        self.limiters = {}
        for path, config in self.limits.items():
            self.limiters[path] = RateLimiter(
                limit=config["limit"],
                window=config["window"]
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取客户端标识
        client_key = self._get_client_key(request)

        # 获取路径限制配置
        path = request.url.path
        limiter = self.limiters.get(path, RateLimiter(self.default_limit, self.default_window))

        # 检查频率限制
        if not limiter.is_allowed(client_key):
            remaining = limiter.get_remaining(client_key)
            logger.warning(
                f"频率限制触发: {request.method} {path} "
                f"- 客户端: {client_key} "
                f"- 剩余: {remaining}"
            )
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁，请稍后再试",
                headers={
                    "X-RateLimit-Limit": str(limiter.limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(time.time() + limiter.window))
                }
            )

        # 处理请求
        response = await call_next(request)

        # 添加频率限制头
        remaining = limiter.get_remaining(client_key)
        response.headers["X-RateLimit-Limit"] = str(limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + limiter.window))

        return response

    def _get_client_key(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户ID（如果已认证）
        if hasattr(request.state, 'user') and request.state.user:
            return f"user:{request.state.user.get('id')}"

        # 使用客户端IP
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"


def setup_rate_limit_middleware(
    app,
    default_limit: int = 100,
    default_window: int = 60,
    limits: Optional[Dict[str, Dict[str, int]]] = None
):
    """设置频率限制中间件"""
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=default_limit,
        default_window=default_window,
        limits=limits
    )