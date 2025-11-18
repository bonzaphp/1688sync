"""
供应商数据访问层
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_, select

from src.models.supplier import Supplier
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SupplierRepository(BaseRepository[Supplier]):
    """供应商仓储类"""

    def __init__(self, session):
        super().__init__(session, Supplier)

    async def get_by_source_id(self, source_id: str) -> Optional[Supplier]:
        """根据1688原始ID获取供应商"""
        return await self.get_by_field('source_id', source_id)

    async def find_by_name(self, name: str, exact_match: bool = False) -> List[Supplier]:
        """根据名称查找供应商"""
        if exact_match:
            return await self.find_by_conditions({'name': name})
        else:
            return await self.find_by_conditions({
                'name': {'like': f'%{name}%'}
            })

    async def find_by_location(self, province: str = None, city: str = None) -> List[Supplier]:
        """根据地址查找供应商"""
        conditions = {}
        if province:
            conditions['province'] = province
        if city:
            conditions['city'] = city
        return await self.find_by_conditions(conditions)

    async def get_top_suppliers(self, limit: int = 10, sort_by: str = 'product_count') -> List[Supplier]:
        """获取顶级供应商"""
        return await self.get_all(limit=limit, order_by=sort_by)

    async def get_suppliers_by_rating_range(self, min_rating: float, max_rating: float) -> List[Supplier]:
        """根据评分范围获取供应商"""
        return await self.find_by_conditions({
            'rating': {'gte': min_rating, 'lte': max_rating}
        })

    async def get_verified_suppliers(self, verification_level: str = None) -> List[Supplier]:
        """获取已认证供应商"""
        conditions = {'is_verified': 'Y'}
        if verification_level:
            conditions['verification_level'] = verification_level
        return await self.find_by_conditions(conditions)

    async def search_suppliers(
        self,
        keyword: str = None,
        province: str = None,
        business_type: str = None,
        is_verified: bool = None,
        min_rating: float = None,
        max_rating: float = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Supplier]:
        """综合搜索供应商"""
        conditions = {}

        if keyword:
            # 搜索名称或公司名
            # 这里使用 or_ 条件需要特殊处理
            pass  # 暂时简化，后续可以扩展

        if province:
            conditions['province'] = province

        if business_type:
            conditions['business_type'] = business_type

        if is_verified is not None:
            conditions['is_verified'] = 'Y' if is_verified else 'N'

        if min_rating is not None and max_rating is not None:
            conditions['rating'] = {'gte': min_rating, 'lte': max_rating}
        elif min_rating is not None:
            conditions['rating'] = {'gte': min_rating}
        elif max_rating is not None:
            conditions['rating'] = {'lte': max_rating}

        return await self.find_by_conditions(conditions, skip, limit)

    async def get_supplier_statistics(self) -> Dict:
        """获取供应商统计信息"""
        try:
            # 总供应商数
            total_stmt = select(func.count(Supplier.id)).where(Supplier.is_deleted == 'N')
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar()

            # 已认证供应商数
            verified_stmt = select(func.count(Supplier.id)).where(
                and_(Supplier.is_deleted == 'N', Supplier.is_verified == 'Y')
            )
            verified_result = await self.session.execute(verified_stmt)
            verified_count = verified_result.scalar()

            # 按省份统计
            province_stmt = select(
                Supplier.province,
                func.count(Supplier.id).label('count')
            ).where(
                and_(
                    Supplier.is_deleted == 'N',
                    Supplier.province.isnot(None)
                )
            ).group_by(Supplier.province).order_by(func.count(Supplier.id).desc())

            province_result = await self.session.execute(province_stmt)
            province_stats = [
                {'province': row.province, 'count': row.count}
                for row in province_result
            ]

            # 按经营类型统计
            business_type_stmt = select(
                Supplier.business_type,
                func.count(Supplier.id).label('count')
            ).where(
                and_(
                    Supplier.is_deleted == 'N',
                    Supplier.business_type.isnot(None)
                )
            ).group_by(Supplier.business_type)

            business_type_result = await self.session.execute(business_type_stmt)
            business_type_stats = [
                {'business_type': row.business_type, 'count': row.count}
                for row in business_type_result
            ]

            return {
                'total_count': total_count,
                'verified_count': verified_count,
                'verification_rate': round(verified_count / total_count * 100, 2) if total_count > 0 else 0,
                'province_distribution': province_stats,
                'business_type_distribution': business_type_stats,
            }

        except Exception as e:
            logger.error(f"获取供应商统计失败: {e}")
            raise

    async def update_product_count(self, supplier_id: int, count: int):
        """更新供应商商品数量"""
        return await self.update(supplier_id, product_count=count)

    async def batch_update_product_counts(self, updates: Dict[int, int]):
        """批量更新供应商商品数量"""
        try:
            for supplier_id, count in updates.items():
                await self.update_product_count(supplier_id, count)
            logger.debug(f"批量更新供应商商品数量成功: {len(updates)} 条记录")
        except Exception as e:
            logger.error(f"批量更新供应商商品数量失败: {e}")
            raise

    async def get_suppliers_with_low_products(self, threshold: int = 10) -> List[Supplier]:
        """获取商品数量较少的供应商"""
        return await self.find_by_conditions({
            'product_count': {'lt': threshold}
        })

    async def get_active_suppliers(self, min_products: int = 1, min_rating: float = 3.0) -> List[Supplier]:
        """获取活跃供应商"""
        try:
            stmt = select(Supplier).where(
                and_(
                    Supplier.is_deleted == 'N',
                    Supplier.product_count >= min_products,
                    Supplier.rating >= min_rating
                )
            ).order_by(Supplier.product_count.desc())

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取活跃供应商失败: {e}")
            raise

    async def create_or_update_supplier(self, source_id: str, **kwargs) -> Supplier:
        """创建或更新供应商"""
        return await self.upsert(['source_id'], {'source_id': source_id, **kwargs})

    async def bulk_import_suppliers(self, suppliers_data: List[Dict]) -> List[Supplier]:
        """批量导入供应商"""
        return await self.bulk_upsert(suppliers_data, ['source_id'])