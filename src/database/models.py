"""
数据库模型定义
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Product(Base):
    """商品模型"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String(200), nullable=True)
    brand = Column(String(200), nullable=True)
    seller = Column(String(200), nullable=True)
    seller_id = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    image_urls = Column(JSON, nullable=True)  # 存储图片URL列表
    specifications = Column(JSON, nullable=True)  # 商品规格参数
    tags = Column(JSON, nullable=True)  # 商品标签
    source_url = Column(String(1000), nullable=False)  # 原始URL

    # 状态字段
    status = Column(String(20), default="active", index=True)  # active, inactive, deleted
    sync_status = Column(String(20), default="pending", index=True)  # pending, syncing, completed, failed

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)

    # 统计字段
    view_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)

    # 关联关系
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_product_status_sync', 'status', 'sync_status'),
        Index('idx_product_created', 'created_at'),
        Index('idx_product_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, product_id='{self.product_id}', title='{self.title[:50]}')>"


class ProductImage(Base):
    """商品图片模型"""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    local_path = Column(String(500), nullable=True)  # 本地存储路径
    image_type = Column(String(50), default="main")  # main, detail, thumbnail
    file_size = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # 状态字段
    status = Column(String(20), default="pending")  # pending, downloading, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联关系
    product = relationship("Product", back_populates="images")

    def __repr__(self):
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, url='{self.url[:50]}')>"


class SyncLog(Base):
    """同步日志模型"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    task_id = Column(String(100), nullable=False, index=True)  # Celery任务ID

    # 日志信息
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)  # 详细信息

    # 执行信息
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # 执行时长(秒)
    success = Column(Boolean, nullable=True)
    error_type = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关联关系
    product = relationship("Product", back_populates="sync_logs")

    def __repr__(self):
        return f"<SyncLog(id={self.id}, task_id='{self.task_id}', level='{self.level}')>"


class SyncTask(Base):
    """同步任务模型"""
    __tablename__ = "sync_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)  # Celery任务ID

    # 任务信息
    task_type = Column(String(50), nullable=False)  # single, batch, category
    source_url = Column(String(1000), nullable=True)
    target_count = Column(Integer, default=0)  # 目标处理数量
    processed_count = Column(Integer, default=0)  # 已处理数量
    success_count = Column(Integer, default=0)  # 成功数量
    failed_count = Column(Integer, default=0)  # 失败数量

    # 状态字段
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)  # 进度百分比

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 配置信息
    config = Column(JSON, nullable=True)  # 任务配置
    result = Column(JSON, nullable=True)  # 执行结果

    __table_args__ = (
        Index('idx_sync_task_status', 'status'),
        Index('idx_sync_task_created', 'created_at'),
    )

    def __repr__(self):
        return f"<SyncTask(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"