"""
商品数据访问层
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_, select

from src.models.product import Product
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ProductRepository(BaseRepository[Product]):
    """商品仓储类"""

    def __init__(self, session):
        super().__init__(session, Product)

    async def get_by_source_id(self, source_id: str) -> Optional[Product]:
        """根据1688原始ID获取商品"""
        return await self.get_by_field('source_id', source_id)

    async def get_by_supplier(self, supplier_id: int, skip: int = 0, limit: int = 50) -> List[Product]:
        """根据供应商ID获取商品"""
        return await self.find_by_conditions({'supplier_id': supplier_id}, skip, limit)

    async def get_by_category(self, category_id: str, skip: int = 0, limit: int = 50) -> List[Product]:
        """根据分类ID获取商品"""
        return await self.find_by_conditions({'category_id': category_id}, skip, limit)

    async def search_products(
        self,
        keyword: str = None,
        supplier_id: int = None,
        category_id: str = None,
        min_price: Decimal = None,
        max_price: Decimal = None,
        min_rating: float = None,
        status: str = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Product]:
        """综合搜索商品"""
        conditions = {}

        if keyword:
            # 搜索标题
            conditions['title'] = {'like': f'%{keyword}%'}

        if supplier_id:
            conditions['supplier_id'] = supplier_id

        if category_id:
            conditions['category_id'] = category_id

        if min_price is not None and max_price is not None:
            conditions['price_min'] = {'gte': min_price, 'lte': max_price}
        elif min_price is not None:
            conditions['price_min'] = {'gte': min_price}
        elif max_price is not None:
            conditions['price_max'] = {'lte': max_price}

        if min_rating is not None:
            conditions['rating'] = {'gte': min_rating}

        if status:
            conditions['status'] = status

        return await self.find_by_conditions(conditions, skip, limit)

    async def get_products_by_price_range(self, min_price: Decimal, max_price: Decimal) -> List[Product]:
        """根据价格范围获取商品"""
        return await self.find_by_conditions({
            'price_min': {'gte': min_price, 'lte': max_price}
        })

    async def get_hot_products(self, limit: int = 10, sort_by: str = 'sales_count') -> List[Product]:
        """获取热门商品"""
        try:
            stmt = select(Product).where(
                and_(
                    Product.is_deleted == 'N',
                    Product.status == 'active'
                )
            ).order_by(getattr(Product, sort_by).desc()).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取热门商品失败: {e}")
            raise

    async def get_high_rated_products(self, min_rating: float = 4.0, limit: int = 10) -> List[Product]:
        """获取高评分商品"""
        return await self.find_by_conditions({
            'rating': {'gte': min_rating},
            'status': 'active'
        }, limit=limit)

    async def get_products_by_sync_status(self, sync_status: str, skip: int = 0, limit: int = 100) -> List[Product]:
        """根据同步状态获取商品"""
        return await self.find_by_conditions({'sync_status': sync_status}, skip, limit)

    async def get_pending_sync_products(self, limit: int = 100) -> List[Product]:
        """获取待同步商品"""
        return await self.get_products_by_sync_status('pending', limit=limit)

    async def get_failed_sync_products(self, limit: int = 100) -> List[Product]:
        """获取同步失败商品"""
        return await self.get_products_by_sync_status('failed', limit=limit)

    async def update_sync_status(self, product_id: int, status: str) -> bool:
        """更新商品同步状态"""
        try:
            product = await self.update(product_id, sync_status=status)
            if product:
                # 更新同步时间戳
                import time
                await self.update(product_id, last_sync_time=int(time.time()))
            return product is not None
        except Exception as e:
            logger.error(f"更新商品同步状态失败: {e}")
            return False

    async def batch_update_sync_status(self, product_ids: List[int], status: str) -> int:
        """批量更新商品同步状态"""
        try:
            import time
            return await self.update_batch(
                {'id': {'in': product_ids}},
                {'sync_status': status, 'last_sync_time': int(time.time())}
            )
        except Exception as e:
            logger.error(f"批量更新商品同步状态失败: {e}")
            raise

    async def get_product_statistics(self) -> Dict:
        """获取商品统计信息"""
        try:
            # 总商品数
            total_stmt = select(func.count(Product.id)).where(Product.is_deleted == 'N')
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar()

            # 按状态统计
            status_stmt = select(
                Product.status,
                func.count(Product.id).label('count')
            ).where(
                and_(Product.is_deleted == 'N', Product.status.isnot(None))
            ).group_by(Product.status)

            status_result = await self.session.execute(status_stmt)
            status_stats = [
                {'status': row.status, 'count': row.count}
                for row in status_result
            ]

            # 按同步状态统计
            sync_status_stmt = select(
                Product.sync_status,
                func.count(Product.id).label('count')
            ).where(Product.is_deleted == 'N').group_by(Product.sync_status)

            sync_status_result = await self.session.execute(sync_status_stmt)
            sync_status_stats = [
                {'sync_status': row.sync_status, 'count': row.count}
                for row in sync_status_result
            ]

            # 按分类统计
            category_stmt = select(
                Product.category_name,
                func.count(Product.id).label('count')
            ).where(
                and_(
                    Product.is_deleted == 'N',
                    Product.category_name.isnot(None)
                )
            ).group_by(Product.category_name).order_by(func.count(Product.id).desc()).limit(10)

            category_result = await self.session.execute(category_stmt)
            category_stats = [
                {'category': row.category_name, 'count': row.count}
                for row in category_result
            ]

            # 价格统计
            price_stmt = select(
                func.min(Product.price_min).label('min_price'),
                func.max(Product.price_max).label('max_price'),
                func.avg(Product.price_min).label('avg_price')
            ).where(
                and_(
                    Product.is_deleted == 'N',
                    Product.price_min.isnot(None)
                )
            )

            price_result = await self.session.execute(price_stmt)
            price_stats = price_result.first()

            return {
                'total_count': total_count,
                'status_distribution': status_stats,
                'sync_status_distribution': sync_status_stats,
                'top_categories': category_stats,
                'price_statistics': {
                    'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
                    'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
                    'avg_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
                }
            }

        except Exception as e:
            logger.error(f"获取商品统计失败: {e}")
            raise

    async def create_or_update_product(self, source_id: str, **kwargs) -> Product:
        """创建或更新商品"""
        return await self.upsert(['source_id'], {'source_id': source_id, **kwargs})

    async def bulk_import_products(self, products_data: List[Dict]) -> List[Product]:
        """批量导入商品"""
        return await self.bulk_upsert(products_data, ['source_id'])

    async def get_available_products(self, skip: int = 0, limit: int = 50) -> List[Product]:
        """获取可用商品"""
        try:
            stmt = select(Product).where(
                and_(
                    Product.is_deleted == 'N',
                    Product.status == 'active',
                    Product.price_min > 0
                )
            ).order_by(Product.updated_at.desc()).offset(skip).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取可用商品失败: {e}")
            raise

    async def count_products_by_supplier(self, supplier_id: int) -> int:
        """统计供应商商品数量"""
        return await self.count({'supplier_id': supplier_id})

    async def get_supplier_products_summary(self, supplier_id: int) -> Dict:
        """获取供应商商品汇总信息"""
        try:
            # 商品数量
            count_stmt = select(func.count(Product.id)).where(
                and_(Product.supplier_id == supplier_id, Product.is_deleted == 'N')
            )
            count_result = await self.session.execute(count_stmt)
            product_count = count_result.scalar()

            # 价格范围
            price_stmt = select(
                func.min(Product.price_min).label('min_price'),
                func.max(Product.price_max).label('max_price'),
                func.avg(Product.price_min).label('avg_price')
            ).where(
                and_(
                    Product.supplier_id == supplier_id,
                    Product.is_deleted == 'N',
                    Product.price_min.isnot(None)
                )
            )
            price_result = await self.session.execute(price_stmt)
            price_stats = price_result.first()

            # 销量和评分
            stats_stmt = select(
                func.sum(Product.sales_count).label('total_sales'),
                func.avg(Product.rating).label('avg_rating')
            ).where(
                and_(Product.supplier_id == supplier_id, Product.is_deleted == 'N')
            )
            stats_result = await self.session.execute(stats_stmt)
            stats = stats_result.first()

            return {
                'product_count': product_count,
                'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
                'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
                'avg_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
                'total_sales': int(stats.total_sales) if stats.total_sales else 0,
                'avg_rating': float(stats.avg_rating) if stats.avg_rating else 0,
            }

        except Exception as e:
            logger.error(f"获取供应商商品汇总失败: {e}")
            raise