"""
商品数据模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator


class ProductImageBase(BaseModel):
    """商品图片基础模式"""
    url: str = Field(..., description="图片URL")
    image_type: str = Field(default="main", description="图片类型")
    file_size: Optional[int] = Field(None, description="文件大小")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")

    class Config:
        from_attributes = True


class ProductImageResponse(ProductImageBase):
    """商品图片响应模式"""
    id: int
    product_id: int
    local_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ProductBase(BaseModel):
    """商品基础模式"""
    title: str = Field(..., min_length=1, max_length=500, description="商品标题")
    price: Optional[float] = Field(None, ge=0, description="商品价格")
    original_price: Optional[float] = Field(None, ge=0, description="原价")
    description: Optional[str] = Field(None, max_length=10000, description="商品描述")
    category: Optional[str] = Field(None, max_length=200, description="商品分类")
    brand: Optional[str] = Field(None, max_length=200, description="品牌")
    seller: Optional[str] = Field(None, max_length=200, description="卖家")
    seller_id: Optional[str] = Field(None, max_length=100, description="卖家ID")
    location: Optional[str] = Field(None, max_length=200, description="发货地")
    source_url: str = Field(..., description="原始URL")
    tags: Optional[List[str]] = Field(default_factory=list, description="商品标签")

    @validator('price', 'original_price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('价格不能为负数')
        return v

    class Config:
        from_attributes = True


class ProductCreate(ProductBase):
    """创建商品模式"""
    product_id: str = Field(..., min_length=1, max_length=100, description="商品ID")
    image_urls: Optional[List[str]] = Field(default_factory=list, description="图片URL列表")
    specifications: Optional[Dict[str, Any]] = Field(default_factory=dict, description="商品规格")


class ProductUpdate(BaseModel):
    """更新商品模式"""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="商品标题")
    price: Optional[float] = Field(None, ge=0, description="商品价格")
    original_price: Optional[float] = Field(None, ge=0, description="原价")
    description: Optional[str] = Field(None, max_length=10000, description="商品描述")
    category: Optional[str] = Field(None, max_length=200, description="商品分类")
    brand: Optional[str] = Field(None, max_length=200, description="品牌")
    seller: Optional[str] = Field(None, max_length=200, description="卖家")
    seller_id: Optional[str] = Field(None, max_length=100, description="卖家ID")
    location: Optional[str] = Field(None, max_length=200, description="发货地")
    image_urls: Optional[List[str]] = Field(None, description="图片URL列表")
    specifications: Optional[Dict[str, Any]] = Field(None, description="商品规格")
    tags: Optional[List[str]] = Field(None, description="商品标签")
    status: Optional[str] = Field(None, description="商品状态")

    @validator('price', 'original_price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('价格不能为负数')
        return v


class ProductResponse(ProductBase):
    """商品响应模式"""
    id: int
    product_id: str
    image_urls: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: str
    sync_status: str
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    view_count: int = 0
    favorite_count: int = 0

    # 可选的关联数据
    images: Optional[List[ProductImageResponse]] = None


class ProductListResponse(BaseModel):
    """商品列表响应模式"""
    products: List[ProductResponse]
    total: int
    skip: int
    limit: int

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.skip + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.skip > 0


class ProductSearchQuery(BaseModel):
    """商品搜索查询模式"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    category: Optional[str] = Field(None, description="商品分类")
    brand: Optional[str] = Field(None, description="品牌")
    seller: Optional[str] = Field(None, description="卖家")
    min_price: Optional[float] = Field(None, ge=0, description="最低价格")
    max_price: Optional[float] = Field(None, ge=0, description="最高价格")
    status: Optional[str] = Field(None, description="商品状态")
    sync_status: Optional[str] = Field(None, description="同步状态")
    location: Optional[str] = Field(None, description="发货地")
    tags: Optional[List[str]] = Field(None, description="商品标签")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="排序顺序")

    @validator('max_price')
    def validate_price_range(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('最高价格不能低于最低价格')
        return v


class ProductSyncRequest(BaseModel):
    """商品同步请求模式"""
    product_ids: List[int] = Field(..., min_items=1, max_items=50, description="商品ID列表")
    force_update: bool = Field(default=False, description="是否强制更新")
    sync_images: bool = Field(default=True, description="是否同步图片")


class ProductBatchImportRequest(BaseModel):
    """商品批量导入请求模式"""
    products: List[ProductCreate] = Field(..., min_items=1, max_items=100, description="商品列表")
    skip_duplicates: bool = Field(default=True, description="是否跳过重复商品")
    update_existing: bool = Field(default=False, description="是否更新已存在的商品")


class ProductStatsResponse(BaseModel):
    """商品统计响应模式"""
    total_count: int
    active_count: int
    inactive_count: int
    pending_sync_count: int
    completed_sync_count: int
    failed_sync_count: int
    category_counts: Dict[str, int]
    brand_counts: Dict[str, int]
    recent_sync_count: int  # 最近24小时同步数量