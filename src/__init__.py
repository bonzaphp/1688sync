"""
1688sync 存储系统
"""
from .database import init_database, close_database
from .models import Base, Supplier, Product, ProductImage, SyncRecord
from .services import (
    SupplierRepository,
    ProductRepository,
    ImageRepository,
    SyncRepository,
    DataConsistencyManager
)
from .storage import image_storage
from .services.backup_restore import backup_restore_manager

__version__ = "1.0.0"
__author__ = "1688sync Team"

__all__ = [
    # 核心模块
    "init_database",
    "close_database",

    # 数据模型
    "Base",
    "Supplier",
    "Product",
    "ProductImage",
    "SyncRecord",

    # 仓储类
    "SupplierRepository",
    "ProductRepository",
    "ImageRepository",
    "SyncRepository",
    "DataConsistencyManager",

    # 存储
    "image_storage",

    # 备份恢复
    "backup_restore_manager",
]