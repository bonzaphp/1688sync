"""
商品图片数据模型
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from .base import Base


class ProductImage(Base):
    """商品图片模型"""

    __tablename__ = "product_images"

    # 关联商品
    product_id = Column(
        BigInteger,
        ForeignKey('products.id'),
        nullable=False,
        comment="商品ID"
    )

    # 图片信息
    url = Column(
        String(1000),
        nullable=False,
        comment="原始图片URL"
    )
    local_path = Column(
        String(1000),
        nullable=True,
        comment="本地存储路径"
    )
    filename = Column(
        String(255),
        nullable=True,
        comment="本地文件名"
    )

    # 图片分类
    image_type = Column(
        String(20),
        nullable=False,
        default='detail',
        comment="图片类型: main/detail/thumb/video"
    )
    sort_order = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="排序顺序"
    )

    # 图片属性
    width = Column(
        BigInteger,
        nullable=True,
        comment="图片宽度"
    )
    height = Column(
        BigInteger,
        nullable=True,
        comment="图片高度"
    )
    size = Column(
        BigInteger,
        nullable=True,
        comment="文件大小(字节)"
    )
    format = Column(
        String(10),
        nullable=True,
        comment="图片格式: jpg/png/webp"
    )
    mime_type = Column(
        String(50),
        nullable=True,
        comment="MIME类型"
    )

    # 图片处理状态
    download_status = Column(
        String(20),
        default='pending',
        nullable=False,
        comment="下载状态: pending/downloading/completed/failed"
    )
    process_status = Column(
        String(20),
        default='pending',
        nullable=False,
        comment="处理状态: pending/processing/completed/failed"
    )

    # CDN相关信息
    cdn_url = Column(
        String(1000),
        nullable=True,
        comment="CDN访问URL"
    )
    thumbnail_path = Column(
        String(1000),
        nullable=True,
        comment="缩略图路径"
    )
    compressed_path = Column(
        String(1000),
        nullable=True,
        comment="压缩图片路径"
    )

    # 处理参数
    compression_ratio = Column(
        String(10),
        nullable=True,
        comment="压缩比率"
    )
    quality_score = Column(
        String(10),
        nullable=True,
        comment="图片质量评分"
    )

    # 错误信息
    error_message = Column(
        String(500),
        nullable=True,
        comment="错误信息"
    )
    retry_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="重试次数"
    )

    # 扩展属性
    image_metadata = Column(
        JSON,
        nullable=True,
        comment="图片元数据: {exif, color_profile, ...}"
    )

    # 关联关系
    product = relationship(
        "Product",
        back_populates="images"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_image_product_id', 'product_id'),
        Index('idx_image_type', 'image_type'),
        Index('idx_image_download_status', 'download_status'),
        Index('idx_image_process_status', 'process_status'),
        Index('idx_image_sort_order', 'sort_order'),
        Index('idx_image_url_hash', 'url'),  # 用于去重
    )

    def __repr__(self) -> str:
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, type='{self.image_type}')>"

    @property
    def is_main_image(self) -> bool:
        """判断是否为主图"""
        return self.image_type == 'main'

    @property
    def is_downloaded(self) -> bool:
        """判断是否已下载"""
        return self.download_status == 'completed'

    @property
    def is_processed(self) -> bool:
        """判断是否已处理"""
        return self.process_status == 'completed'

    @property
    def has_local_file(self) -> bool:
        """判断是否有本地文件"""
        return self.local_path is not None and len(self.local_path) > 0

    @property
    def file_size_mb(self) -> float:
        """获取文件大小(MB)"""
        if self.size is None:
            return 0
        return round(self.size / (1024 * 1024), 2)

    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        if self.width and self.height and self.height > 0:
            return round(self.width / self.height, 2)
        return 0

    def update_download_status(self, status: str, local_path: str = None, error_message: str = None):
        """更新下载状态"""
        self.download_status = status
        if local_path:
            self.local_path = local_path
        if error_message:
            self.error_message = error_message
        if status == 'failed':
            self.retry_count += 1

    def update_process_status(self, status: str, error_message: str = None):
        """更新处理状态"""
        self.process_status = status
        if error_message:
            self.error_message = error_message

    def get_display_url(self) -> str:
        """获取显示URL（优先CDN）"""
        return self.cdn_url or self.local_path or self.url

    def get_thumbnail_url(self) -> str:
        """获取缩略图URL"""
        return self.thumbnail_path or self.get_display_url()

    def add_metadata(self, key: str, value):
        """添加元数据"""
        if self.image_metadata is None:
            self.image_metadata = {}
        self.image_metadata[key] = value

    def get_metadata(self, key: str, default=None):
        """获取元数据"""
        if self.image_metadata is None:
            return default
        return self.image_metadata.get(key, default)