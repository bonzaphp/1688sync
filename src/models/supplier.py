"""
供应商数据模型
"""
from sqlalchemy import BigInteger, Column, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .base import Base


class Supplier(Base):
    """供应商模型"""

    __tablename__ = "suppliers"

    # 供应商基本信息
    source_id = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="1688原始供应商ID"
    )
    name = Column(
        String(200),
        nullable=False,
        comment="供应商名称"
    )
    company_name = Column(
        String(200),
        nullable=True,
        comment="公司名称"
    )

    # 联系信息（JSON格式存储）
    contact_info = Column(
        JSON,
        nullable=True,
        comment="联系信息: {phone, email, qq, wechat}"
    )

    # 地址信息
    location = Column(
        String(100),
        nullable=True,
        comment="地址信息"
    )
    province = Column(
        String(50),
        nullable=True,
        comment="省份"
    )
    city = Column(
        String(50),
        nullable=True,
        comment="城市"
    )

    # 供应商评级和统计
    rating = Column(
        Numeric(3, 2),
        nullable=True,
        comment="供应商评分 (0.00-5.00)"
    )
    response_rate = Column(
        Numeric(5, 2),
        nullable=True,
        comment="响应率 (%)"
    )
    product_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="商品数量"
    )

    # 经营信息
    business_type = Column(
        String(50),
        nullable=True,
        comment="经营类型: manufacturer/trader/individual"
    )
    main_products = Column(
        JSON,
        nullable=True,
        comment="主营产品列表"
    )
    established_year = Column(
        String(4),
        nullable=True,
        comment="成立年份"
    )

    # 认证信息
    is_verified = Column(
        String(1),
        default='N',
        nullable=False,
        comment="是否已认证: Y/N"
    )
    verification_level = Column(
        String(20),
        nullable=True,
        comment="认证级别"
    )

    # 关联关系
    products = relationship(
        "Product",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_supplier_source_id', 'source_id'),
        Index('idx_supplier_location', 'province', 'city'),
        Index('idx_supplier_rating', 'rating'),
        Index('idx_supplier_business_type', 'business_type'),
        Index('idx_supplier_verified', 'is_verified'),
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', source_id='{self.source_id}')>"

    @property
    def is_active_supplier(self) -> bool:
        """判断是否为活跃供应商"""
        return (
            self.is_deleted == 'N' and
            self.product_count > 0 and
            self.rating is not None and float(self.rating) >= 3.0
        )

    def update_product_count(self, count: int):
        """更新商品数量"""
        self.product_count = max(0, count)

    def add_contact_info(self, contact_type: str, contact_value: str):
        """添加联系信息"""
        if self.contact_info is None:
            self.contact_info = {}
        self.contact_info[contact_type] = contact_value

    def get_contact_info(self, contact_type: str = None):
        """获取联系信息"""
        if self.contact_info is None:
            return None
        if contact_type:
            return self.contact_info.get(contact_type)
        return self.contact_info