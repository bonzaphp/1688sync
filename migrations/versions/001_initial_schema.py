"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-11-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库结构"""

    # 创建供应商表
    op.create_table('suppliers',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False, comment='1688原始供应商ID'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='供应商名称'),
        sa.Column('company_name', sa.String(length=200), nullable=True, comment='公司名称'),
        sa.Column('contact_info', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='联系信息'),
        sa.Column('location', sa.String(length=100), nullable=True, comment='地址'),
        sa.Column('province', sa.String(length=50), nullable=True, comment='省份'),
        sa.Column('city', sa.String(length=50), nullable=True, comment='城市'),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True, comment='供应商评分'),
        sa.Column('response_rate', sa.Numeric(precision=5, scale=2), nullable=True, comment='响应率'),
        sa.Column('product_count', sa.BigInteger(), nullable=False, server_default='0', comment='商品数量'),
        sa.Column('business_type', sa.String(length=50), nullable=True, comment='经营类型'),
        sa.Column('main_products', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='主营产品'),
        sa.Column('established_year', sa.String(length=4), nullable=True, comment='成立年份'),
        sa.Column('is_verified', sa.String(length=1), nullable=False, server_default='N', comment='是否已认证'),
        sa.Column('verification_level', sa.String(length=20), nullable=True, comment='认证级别'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('is_deleted', sa.String(length=1), nullable=False, server_default='N', comment='是否删除'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id'),
        comment='供应商表'
    )

    # 创建供应商表索引
    op.create_index('idx_suppliers_source_id', 'suppliers', ['source_id'], unique=True)
    op.create_index('idx_suppliers_location', 'suppliers', ['province', 'city'])
    op.create_index('idx_suppliers_rating', 'suppliers', ['rating'])
    op.create_index('idx_suppliers_business_type', 'suppliers', ['business_type'])
    op.create_index('idx_suppliers_verified', 'suppliers', ['is_verified'])
    op.create_index('idx_suppliers_deleted', 'suppliers', ['is_deleted'])

    # 创建商品表
    op.create_table('products',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_id', sa.String(length=50), nullable=False, comment='1688原始商品ID'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='商品标题'),
        sa.Column('subtitle', sa.String(length=500), nullable=True, comment='商品副标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='商品详细描述'),
        sa.Column('price_min', sa.Numeric(precision=10, scale=2), nullable=True, comment='最低价格'),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2), nullable=True, comment='最高价格'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='CNY', comment='货币单位'),
        sa.Column('moq', sa.BigInteger(), nullable=True, comment='最小起订量'),
        sa.Column('price_unit', sa.String(length=20), nullable=True, comment='价格单位'),
        sa.Column('main_image_url', sa.String(length=1000), nullable=True, comment='主图片URL'),
        sa.Column('detail_images', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='详情图片列表'),
        sa.Column('video_url', sa.String(length=1000), nullable=True, comment='商品视频URL'),
        sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='商品规格参数'),
        sa.Column('attributes', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='商品属性'),
        sa.Column('supplier_id', sa.BigInteger(), nullable=False, comment='供应商ID'),
        sa.Column('sales_count', sa.BigInteger(), nullable=False, server_default='0', comment='销量'),
        sa.Column('review_count', sa.BigInteger(), nullable=False, server_default='0', comment='评论数'),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True, comment='商品评分'),
        sa.Column('category_id', sa.String(length=50), nullable=True, comment='分类ID'),
        sa.Column('category_name', sa.String(length=200), nullable=True, comment='分类名称'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active', comment='商品状态'),
        sa.Column('sync_status', sa.String(length=20), nullable=False, server_default='pending', comment='同步状态'),
        sa.Column('last_sync_time', sa.BigInteger(), nullable=True, comment='最后同步时间戳'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('is_deleted', sa.String(length=1), nullable=False, server_default='N', comment='是否删除'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id'),
        comment='商品表'
    )

    # 创建商品表索引
    op.create_index('idx_products_source_id', 'products', ['source_id'], unique=True)
    op.create_index('idx_products_supplier_id', 'products', ['supplier_id'])
    op.create_index('idx_products_category', 'products', ['category_id'])
    op.create_index('idx_products_price_range', 'products', ['price_min', 'price_max'])
    op.create_index('idx_products_sales', 'products', ['sales_count'])
    op.create_index('idx_products_rating', 'products', ['rating'])
    op.create_index('idx_products_status', 'products', ['status'])
    op.create_index('idx_products_sync_status', 'products', ['sync_status'])
    op.create_index('idx_products_supplier_status', 'products', ['supplier_id', 'status'])
    op.create_index('idx_products_category_status', 'products', ['category_id', 'status'])
    op.create_index('idx_products_sync_status_updated', 'products', ['sync_status', 'updated_at'])
    op.create_index('idx_products_deleted', 'products', ['is_deleted'])

    # 创建商品图片表
    op.create_table('product_images',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False, comment='商品ID'),
        sa.Column('url', sa.String(length=1000), nullable=False, comment='原始图片URL'),
        sa.Column('local_path', sa.String(length=1000), nullable=True, comment='本地存储路径'),
        sa.Column('filename', sa.String(length=255), nullable=True, comment='本地文件名'),
        sa.Column('image_type', sa.String(length=20), nullable=False, server_default='detail', comment='图片类型'),
        sa.Column('sort_order', sa.BigInteger(), nullable=False, server_default='0', comment='排序顺序'),
        sa.Column('width', sa.BigInteger(), nullable=True, comment='图片宽度'),
        sa.Column('height', sa.BigInteger(), nullable=True, comment='图片高度'),
        sa.Column('size', sa.BigInteger(), nullable=True, comment='文件大小'),
        sa.Column('format', sa.String(length=10), nullable=True, comment='图片格式'),
        sa.Column('mime_type', sa.String(length=50), nullable=True, comment='MIME类型'),
        sa.Column('download_status', sa.String(length=20), nullable=False, server_default='pending', comment='下载状态'),
        sa.Column('process_status', sa.String(length=20), nullable=False, server_default='pending', comment='处理状态'),
        sa.Column('cdn_url', sa.String(length=1000), nullable=True, comment='CDN访问URL'),
        sa.Column('thumbnail_path', sa.String(length=1000), nullable=True, comment='缩略图路径'),
        sa.Column('compressed_path', sa.String(length=1000), nullable=True, comment='压缩图片路径'),
        sa.Column('compression_ratio', sa.String(length=10), nullable=True, comment='压缩比率'),
        sa.Column('quality_score', sa.String(length=10), nullable=True, comment='图片质量评分'),
        sa.Column('error_message', sa.String(length=500), nullable=True, comment='错误信息'),
        sa.Column('retry_count', sa.BigInteger(), nullable=False, server_default='0', comment='重试次数'),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='图片元数据'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('is_deleted', sa.String(length=1), nullable=False, server_default='N', comment='是否删除'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        comment='商品图片表'
    )

    # 创建商品图片表索引
    op.create_index('idx_product_images_product_id', 'product_images', ['product_id'])
    op.create_index('idx_product_images_type', 'product_images', ['image_type'])
    op.create_index('idx_product_images_download_status', 'product_images', ['download_status'])
    op.create_index('idx_product_images_process_status', 'product_images', ['process_status'])
    op.create_index('idx_product_images_sort_order', 'product_images', ['sort_order'])
    op.create_index('idx_product_images_url_hash', 'product_images', ['url'])
    op.create_index('idx_images_product_type_status', 'product_images', ['product_id', 'image_type', 'download_status'])
    op.create_index('idx_product_images_deleted', 'product_images', ['is_deleted'])

    # 创建同步记录表
    op.create_table('sync_records',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=False, comment='任务ID'),
        sa.Column('task_name', sa.String(length=200), nullable=True, comment='任务名称'),
        sa.Column('operation_type', sa.String(length=20), nullable=False, comment='操作类型'),
        sa.Column('sync_type', sa.String(length=20), nullable=False, server_default='product', comment='同步类型'),
        sa.Column('source_filter', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='源数据过滤条件'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='状态'),
        sa.Column('progress', sa.BigInteger(), nullable=False, server_default='0', comment='进度百分比'),
        sa.Column('start_time', sa.BigInteger(), nullable=True, comment='开始时间戳'),
        sa.Column('end_time', sa.BigInteger(), nullable=True, comment='结束时间戳'),
        sa.Column('duration', sa.BigInteger(), nullable=True, comment='执行时长'),
        sa.Column('total_count', sa.BigInteger(), nullable=False, server_default='0', comment='总数量'),
        sa.Column('processed_count', sa.BigInteger(), nullable=False, server_default='0', comment='已处理数量'),
        sa.Column('success_count', sa.BigInteger(), nullable=False, server_default='0', comment='成功数量'),
        sa.Column('failed_count', sa.BigInteger(), nullable=False, server_default='0', comment='失败数量'),
        sa.Column('skipped_count', sa.BigInteger(), nullable=False, server_default='0', comment='跳过数量'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='主要错误信息'),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='详细错误信息'),
        sa.Column('error_count', sa.BigInteger(), nullable=False, server_default='0', comment='错误次数'),
        sa.Column('records_per_second', sa.BigInteger(), nullable=True, comment='每秒处理记录数'),
        sa.Column('memory_usage_mb', sa.BigInteger(), nullable=True, comment='内存使用量'),
        sa.Column('cpu_usage_percent', sa.BigInteger(), nullable=True, comment='CPU使用率'),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='同步配置参数'),
        sa.Column('batch_size', sa.BigInteger(), nullable=False, server_default='1000', comment='批次大小'),
        sa.Column('max_retries', sa.BigInteger(), nullable=False, server_default='3', comment='最大重试次数'),
        sa.Column('summary', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='执行摘要信息'),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='优化建议'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='删除时间'),
        sa.Column('is_deleted', sa.String(length=1), nullable=False, server_default='N', comment='是否删除'),
        sa.PrimaryKeyConstraint('id'),
        comment='同步记录表'
    )

    # 创建同步记录表索引
    op.create_index('idx_sync_records_task_id', 'sync_records', ['task_id'])
    op.create_index('idx_sync_records_operation_type', 'sync_records', ['operation_type'])
    op.create_index('idx_sync_records_status', 'sync_records', ['status'])
    op.create_index('idx_sync_records_start_time', 'sync_records', ['start_time'])
    op.create_index('idx_sync_records_sync_type', 'sync_records', ['sync_type'])
    op.create_index('idx_sync_records_progress', 'sync_records', ['progress'])


def downgrade() -> None:
    """降级数据库结构"""

    # 删除同步记录表
    op.drop_table('sync_records')

    # 删除商品图片表
    op.drop_table('product_images')

    # 删除商品表
    op.drop_table('products')

    # 删除供应商表
    op.drop_table('suppliers')