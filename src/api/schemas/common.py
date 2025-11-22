"""
通用数据模式
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """通用响应模型"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[T] = None
    code: int = 200


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    message: str
    code: int = 400
    details: Optional[dict[str, Any]] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: list[T]
    total: int
    page: int = 1
    size: int = 20
    pages: int

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: float
    version: str
    database: Optional[str] = None
    redis: Optional[str] = None


class StatsResponse(BaseModel):
    """统计信息响应"""
    name: str
    value: Any
    unit: Optional[str] = None
    description: Optional[str] = None


class BulkOperationRequest(BaseModel):
    """批量操作请求"""
    ids: list[int] = Field(..., min_items=1, max_items=100)
    operation: str
    params: Optional[dict[str, Any]] = None


class BulkOperationResponse(BaseModel):
    """批量操作响应"""
    total: int
    success: int
    failed: int
    errors: Optional[list[dict[str, Any]]] = None