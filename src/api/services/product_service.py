"""
商品服务层
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from fastapi import BackgroundTasks
import uuid
import logging

from ...database.models import Product, ProductImage
from ..schemas.product import ProductCreate, ProductUpdate, ProductSearchQuery

logger = logging.getLogger(__name__)


class ProductService:
    """商品服务类"""

    def __init__(self, db: Session):
        self.db = db

    async def get_products(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Product], int]:
        """获取商品列表"""
        query = self.db.query(Product)

        # 应用过滤条件
        if filters:
            if "status" in filters:
                query = query.filter(Product.status == filters["status"])
            if "sync_status" in filters:
                query = query.filter(Product.sync_status == filters["sync_status"])
            if "category" in filters:
                query = query.filter(Product.category == filters["category"])
            if "seller" in filters:
                query = query.filter(Product.seller == filters["seller"])
            if "search" in filters and filters["search"]:
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Product.title.ilike(search_term),
                        Product.description.ilike(search_term),
                        Product.brand.ilike(search_term),
                        Product.seller.ilike(search_term)
                    )
                )

        # 获取总数
        total = query.count()

        # 应用分页和排序
        products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()

        return products, total

    async def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """根据ID获取商品"""
        return self.db.query(Product).filter(Product.id == product_id).first()

    async def get_product_by_product_id(self, product_id: str) -> Optional[Product]:
        """根据商品ID获取商品"""
        return self.db.query(Product).filter(Product.product_id == product_id).first()

    async def create_product(self, product_data: ProductCreate) -> Product:
        """创建商品"""
        # 检查商品ID是否已存在
        existing_product = await self.get_product_by_product_id(product_data.product_id)
        if existing_product:
            raise ValueError(f"商品ID {product_data.product_id} 已存在")

        # 创建商品记录
        db_product = Product(
            product_id=product_data.product_id,
            title=product_data.title,
            price=product_data.price,
            original_price=product_data.original_price,
            description=product_data.description,
            category=product_data.category,
            brand=product_data.brand,
            seller=product_data.seller,
            seller_id=product_data.seller_id,
            location=product_data.location,
            source_url=product_data.source_url,
            image_urls=product_data.image_urls,
            specifications=product_data.specifications,
            tags=product_data.tags,
            status="active",
            sync_status="pending"
        )

        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)

        logger.info(f"创建商品成功: {db_product.product_id}")
        return db_product

    async def update_product(
        self,
        product_id: int,
        product_data: ProductUpdate
    ) -> Optional[Product]:
        """更新商品"""
        db_product = await self.get_product_by_id(product_id)
        if not db_product:
            return None

        # 更新字段
        update_data = product_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_product, field, value)

        self.db.commit()
        self.db.refresh(db_product)

        logger.info(f"更新商品成功: {db_product.product_id}")
        return db_product

    async def delete_product(self, product_id: int) -> bool:
        """删除商品"""
        db_product = await self.get_product_by_id(product_id)
        if not db_product:
            return False

        # 软删除：更新状态
        db_product.status = "deleted"
        self.db.commit()

        logger.info(f"删除商品成功: {db_product.product_id}")
        return True

    async def get_product_images(self, product_id: int) -> List[ProductImage]:
        """获取商品图片"""
        return self.db.query(ProductImage).filter(
            ProductImage.product_id == product_id
        ).order_by(ProductImage.created_at).all()

    async def sync_product(
        self,
        product_id: int,
        background_tasks: BackgroundTasks
    ) -> str:
        """同步单个商品"""
        db_product = await self.get_product_by_id(product_id)
        if not db_product:
            raise ValueError("商品不存在")

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 更新同步状态
        db_product.sync_status = "syncing"
        self.db.commit()

        # 添加后台任务
        background_tasks.add_task(
            self._perform_product_sync,
            product_id,
            task_id
        )

        logger.info(f"启动商品同步任务: {task_id}")
        return task_id

    async def batch_sync_products(
        self,
        product_ids: List[int],
        background_tasks: BackgroundTasks
    ) -> str:
        """批量同步商品"""
        # 生成批量任务ID
        batch_task_id = str(uuid.uuid4())

        # 验证商品存在
        products = self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        if len(products) != len(product_ids):
            raise ValueError("部分商品不存在")

        # 更新同步状态
        for product in products:
            product.sync_status = "syncing"
        self.db.commit()

        # 添加批量同步任务
        background_tasks.add_task(
            self._perform_batch_sync,
            product_ids,
            batch_task_id
        )

        logger.info(f"启动批量同步任务: {batch_task_id}")
        return batch_task_id

    async def _perform_product_sync(self, product_id: int, task_id: str):
        """执行商品同步（后台任务）"""
        try:
            # 这里应该调用具体的爬虫逻辑
            # 暂时模拟同步过程
            import time
            time.sleep(2)  # 模拟处理时间

            # 更新同步状态
            db_product = await self.get_product_by_id(product_id)
            if db_product:
                db_product.sync_status = "completed"
                db_product.last_sync_at = datetime.utcnow()
                self.db.commit()

            logger.info(f"商品同步完成: {product_id}, 任务ID: {task_id}")

        except Exception as e:
            logger.error(f"商品同步失败: {product_id}, 任务ID: {task_id}, 错误: {e}")

            # 更新同步状态为失败
            db_product = await self.get_product_by_id(product_id)
            if db_product:
                db_product.sync_status = "failed"
                self.db.commit()

    async def _perform_batch_sync(self, product_ids: List[int], batch_task_id: str):
        """执行批量同步（后台任务）"""
        try:
            # 这里应该调用具体的批量同步逻辑
            # 暂时模拟同步过程
            import time
            time.sleep(len(product_ids) * 0.5)  # 模拟处理时间

            # 更新所有商品状态为完成
            products = self.db.query(Product).filter(Product.id.in_(product_ids)).all()
            for product in products:
                product.sync_status = "completed"
                product.last_sync_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"批量同步完成: {len(product_ids)}个商品, 任务ID: {batch_task_id}")

        except Exception as e:
            logger.error(f"批量同步失败: 任务ID: {batch_task_id}, 错误: {e}")

            # 更新所有商品状态为失败
            products = self.db.query(Product).filter(Product.id.in_(product_ids)).all()
            for product in products:
                product.sync_status = "failed"

            self.db.commit()

    async def get_product_stats(self) -> Dict[str, Any]:
        """获取商品统计信息"""
        total_count = self.db.query(Product).filter(Product.status != "deleted").count()
        active_count = self.db.query(Product).filter(
            and_(Product.status == "active", Product.status != "deleted")
        ).count()
        inactive_count = self.db.query(Product).filter(Product.status == "inactive").count()

        pending_sync_count = self.db.query(Product).filter(Product.sync_status == "pending").count()
        completed_sync_count = self.db.query(Product).filter(Product.sync_status == "completed").count()
        failed_sync_count = self.db.query(Product).filter(Product.sync_status == "failed").count()

        # 最近24小时同步数量
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_sync_count = self.db.query(Product).filter(
            Product.last_sync_at >= yesterday
        ).count()

        return {
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
            "pending_sync_count": pending_sync_count,
            "completed_sync_count": completed_sync_count,
            "failed_sync_count": failed_sync_count,
            "recent_sync_count": recent_sync_count
        }