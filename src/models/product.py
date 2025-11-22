"""
商品数据模型
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, Index, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .base import Base


class Product(Base):
    """商品模型"""

    __tablename__ = "products"

    # 商品基本信息
    source_id = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="1688原始商品ID"
    )
    title = Column(
        String(500),
        nullable=False,
        comment="商品标题"
    )
    subtitle = Column(
        String(500),
        nullable=True,
        comment="商品副标题"
    )
    description = Column(
        Text,
        nullable=True,
        comment="商品详细描述"
    )

    # 价格信息
    price_min = Column(
        Numeric(10, 2),
        nullable=True,
        comment="最低价格"
    )
    price_max = Column(
        Numeric(10, 2),
        nullable=True,
        comment="最高价格"
    )
    currency = Column(
        String(3),
        default='CNY',
        nullable=False,
        comment="货币单位"
    )

    # 订货信息
    moq = Column(
        BigInteger,
        nullable=True,
        comment="最小起订量"
    )
    price_unit = Column(
        String(20),
        nullable=True,
        comment="价格单位: piece/kg/meter"
    )

    # 商品图片
    main_image_url = Column(
        String(1000),
        nullable=True,
        comment="主图片URL"
    )
    detail_images = Column(
        JSON,
        nullable=True,
        comment="详情图片URL列表"
    )
    video_url = Column(
        String(1000),
        nullable=True,
        comment="商品视频URL"
    )

    # 商品规格参数
    specifications = Column(
        JSON,
        nullable=True,
        comment="商品规格参数: {color, size, material, ...}"
    )
    attributes = Column(
        JSON,
        nullable=True,
        comment="商品属性: {brand, model, warranty, ...}"
    )

    # 供应商关联
    supplier_id = Column(
        BigInteger,
        ForeignKey('suppliers.id'),
        nullable=False,
        comment="供应商ID"
    )

    # 销售统计
    sales_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="销量"
    )
    review_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="评论数"
    )
    rating = Column(
        Numeric(3, 2),
        nullable=True,
        comment="商品评分 (0.00-5.00)"
    )

    # 商品分类和状态
    category_id = Column(
        String(50),
        nullable=True,
        comment="分类ID"
    )
    category_name = Column(
        String(200),
        nullable=True,
        comment="分类名称"
    )
    status = Column(
        String(20),
        default='active',
        nullable=False,
        comment="商品状态: active/inactive/discontinued"
    )

    # 同步状态
    sync_status = Column(
        String(20),
        default='pending',
        nullable=False,
        comment="同步状态: pending/syncing/completed/failed"
    )
    last_sync_time = Column(
        BigInteger,
        nullable=True,
        comment="最后同步时间戳"
    )

    # 关联关系
    supplier = relationship(
        "Supplier",
        back_populates="products"
    )
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_product_source_id', 'source_id'),
        Index('idx_product_supplier_id', 'supplier_id'),
        Index('idx_product_category', 'category_id'),
        Index('idx_product_price', 'price_min', 'price_max'),
        Index('idx_product_sales', 'sales_count'),
        Index('idx_product_rating', 'rating'),
        Index('idx_product_status', 'status'),
        Index('idx_product_sync_status', 'sync_status'),
        Index('idx_product_title', 'title'),  # 全文搜索
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, title='{self.title[:50]}...', source_id='{self.source_id}')>"

    @property
    def price_range(self) -> Optional[str]:
        """获取价格范围字符串"""
        if self.price_min is None and self.price_max is None:
            return None
        if self.price_min == self.price_max:
            return f"¥{self.price_min}"
        return f"¥{self.price_min} - ¥{self.price_max}"

    @property
    def is_available(self) -> bool:
        """判断商品是否可用"""
        return (
            self.is_deleted == 'N' and
            self.status == 'active' and
            self.price_min is not None and
            self.price_min > 0
        )

    @property
    def average_rating(self) -> Optional[float]:
        """获取平均评分"""
        return float(self.rating) if self.rating else None

    def update_sync_status(self, status: str):
        """更新同步状态"""
        self.sync_status = status
        self.last_sync_time = int(self.updated_at.timestamp())

    def add_specification(self, key: str, value: str):
        """添加规格参数"""
        if self.specifications is None:
            self.specifications = {}
        self.specifications[key] = value

    def get_specification(self, key: str, default=None):
        """获取规格参数"""
        if self.specifications is None:
            return default
        return self.specifications.get(key, default)

    def add_attribute(self, key: str, value: str):
        """添加商品属性"""
        if self.attributes is None:
            self.attributes = {}
        self.attributes[key] = value

    def get_attribute(self, key: str, default=None):
        """获取商品属性"""
        if self.attributes is None:
            return default
        return self.attributes.get(key, default)

    def get_main_image_url(self) -> Optional[str]:
        """获取主图URL"""
        return self.main_image_url

    def get_detail_image_urls(self) -> list:
        """获取详情图URL列表"""
        if self.detail_images is None:
            return []
        return self.detail_images if isinstance(self.detail_images, list) else []