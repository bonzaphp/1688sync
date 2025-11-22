"""
FastAPI应用主入口
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from config import settings
from api.routes import api_router
from api.exceptions import setup_exception_handlers
from api.middleware import (
    setup_logging_middleware,
    setup_security_middleware,
    setup_rate_limit_middleware,
    setup_timing_middleware
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("1688sync API服务启动中...")

    # 这里可以添加启动时的初始化逻辑
    # 例如：数据库连接检查、缓存预热等

    logger.info("1688sync API服务启动完成")

    yield

    # 关闭时执行
    logger.info("1688sync API服务关闭中...")

    # 这里可以添加关闭时的清理逻辑
    # 例如：关闭数据库连接、清理缓存等

    logger.info("1688sync API服务已关闭")


# 创建FastAPI应用实例
app = FastAPI(
    title="1688sync API",
    description="1688商品数据同步服务 RESTful API",
    version=settings.version,
    docs_url="/docs" if settings.api_debug else None,
    redoc_url="/redoc" if settings.api_debug else None,
    openapi_url="/openapi.json" if settings.api_debug else None,
    lifespan=lifespan
)

# 设置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置可信主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境应该限制具体主机
)

# 设置异常处理器
setup_exception_handlers(app)

# 设置安全中间件
setup_security_middleware(app, https_required=settings.api_debug is False)

# 设置频率限制中间件
rate_limits = {
    "/api/v1/products/sync": {"limit": 10, "window": 60},  # 商品同步限制
    "/api/v1/tasks": {"limit": 50, "window": 60},         # 任务操作限制
    "/api/v1/logs": {"limit": 100, "window": 60},         # 日志查询限制
}
setup_rate_limit_middleware(
    app,
    default_limit=100,
    default_window=60,
    limits=rate_limits
)

# 设置计时中间件
setup_timing_middleware(app, slow_request_threshold=5.0)

# 设置日志中间件
setup_logging_middleware(app)

# 注册主路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "name": settings.name,
        "version": settings.version,
        "status": "running",
        "timestamp": time.time()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.version
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower()
    )