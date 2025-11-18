"""
数据模型模块
"""
from .base import Base, BaseModel
from .supplier import Supplier
from .product import Product
from .image import ProductImage
from .sync_record import SyncRecord

# 导出所有模型
__all__ = [
    'Base',
    'BaseModel',
    'Supplier',
    'Product',
    'ProductImage',
    'SyncRecord',
]