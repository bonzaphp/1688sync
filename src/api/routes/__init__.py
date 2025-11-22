"""
API路由模块
"""
from fastapi import APIRouter

# 导入各子路由
from .products import router as products_router
from .tasks import router as tasks_router
from .logs import router as logs_router

# 创建主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(
    products_router,
    prefix="/products",
    tags=["商品管理"]
)

api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["任务管理"]
)

api_router.include_router(
    logs_router,
    prefix="/logs",
    tags=["日志管理"]
)

__all__ = ["api_router"]