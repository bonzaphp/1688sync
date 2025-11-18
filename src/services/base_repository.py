"""
基础数据访问层
"""
import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.base import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    """基础仓储类"""

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    async def create(self, **kwargs) -> T:
        """创建新记录"""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            logger.debug(f"创建记录成功: {self.model_class.__name__}(id={instance.id})")
            return instance
        except Exception as e:
            logger.error(f"创建记录失败: {e}")
            await self.session.rollback()
            raise

    async def create_batch(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """批量创建记录"""
        try:
            instances = [self.model_class(**data) for data in data_list]
            self.session.add_all(instances)
            await self.session.flush()

            # 刷新所有实例以获取ID
            for instance in instances:
                await self.session.refresh(instance)

            logger.debug(f"批量创建记录成功: {len(instances)} 条 {self.model_class.__name__}")
            return instances
        except Exception as e:
            logger.error(f"批量创建记录失败: {e}")
            await self.session.rollback()
            raise

    async def get_by_id(self, record_id: Union[int, str]) -> Optional[T]:
        """根据ID获取记录"""
        try:
            stmt = select(self.model_class).where(
                and_(
                    self.model_class.id == record_id,
                    self.model_class.is_deleted == 'N'
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"根据ID获取记录失败: {e}")
            raise

    async def get_by_field(self, field_name: str, value: Any) -> Optional[T]:
        """根据字段获取记录"""
        try:
            field = getattr(self.model_class, field_name)
            stmt = select(self.model_class).where(
                and_(
                    field == value,
                    self.model_class.is_deleted == 'N'
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"根据字段获取记录失败: {e}")
            raise

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = None,
        include_deleted: bool = False
    ) -> List[T]:
        """获取所有记录"""
        try:
            stmt = select(self.model_class)

            if not include_deleted:
                stmt = stmt.where(self.model_class.is_deleted == 'N')

            if order_by:
                order_field = getattr(self.model_class, order_by)
                stmt = stmt.order_by(order_field.desc())

            stmt = stmt.offset(skip).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取所有记录失败: {e}")
            raise

    async def update(self, record_id: Union[int, str], **kwargs) -> Optional[T]:
        """更新记录"""
        try:
            stmt = (
                update(self.model_class)
                .where(
                    and_(
                        self.model_class.id == record_id,
                        self.model_class.is_deleted == 'N'
                    )
                )
                .values(**kwargs)
                .returning(self.model_class)
            )
            result = await self.session.execute(stmt)
            instance = result.scalar_one_or_none()

            if instance:
                await self.session.refresh(instance)
                logger.debug(f"更新记录成功: {self.model_class.__name__}(id={record_id})")

            return instance
        except Exception as e:
            logger.error(f"更新记录失败: {e}")
            await self.session.rollback()
            raise

    async def update_batch(self, filters: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """批量更新记录"""
        try:
            conditions = [self.model_class.is_deleted == 'N']

            for field, value in filters.items():
                field_obj = getattr(self.model_class, field)
                conditions.append(field_obj == value)

            stmt = (
                update(self.model_class)
                .where(and_(*conditions))
                .values(**update_data)
            )

            result = await self.session.execute(stmt)
            affected_rows = result.rowcount

            logger.debug(f"批量更新记录成功: {affected_rows} 条 {self.model_class.__name__}")
            return affected_rows
        except Exception as e:
            logger.error(f"批量更新记录失败: {e}")
            await self.session.rollback()
            raise

    async def delete(self, record_id: Union[int, str], soft: bool = True) -> bool:
        """删除记录"""
        try:
            if soft:
                # 软删除
                stmt = (
                    update(self.model_class)
                    .where(self.model_class.id == record_id)
                    .values(is_deleted='Y')
                )
            else:
                # 硬删除
                stmt = delete(self.model_class).where(self.model_class.id == record_id)

            result = await self.session.execute(stmt)
            success = result.rowcount > 0

            if success:
                delete_type = "软删除" if soft else "硬删除"
                logger.debug(f"{delete_type}记录成功: {self.model_class.__name__}(id={record_id})")

            return success
        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            await self.session.rollback()
            raise

    async def count(self, filters: Dict[str, Any] = None, include_deleted: bool = False) -> int:
        """统计记录数量"""
        try:
            stmt = select(func.count(self.model_class.id))

            if not include_deleted:
                stmt = stmt.where(self.model_class.is_deleted == 'N')

            if filters:
                conditions = []
                for field, value in filters.items():
                    field_obj = getattr(self.model_class, field)
                    if isinstance(value, (list, tuple)):
                        conditions.append(field_obj.in_(value))
                    else:
                        conditions.append(field_obj == value)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

            result = await self.session.execute(stmt)
            return result.scalar()
        except Exception as e:
            logger.error(f"统计记录数量失败: {e}")
            raise

    async def exists(self, **kwargs) -> bool:
        """检查记录是否存在"""
        try:
            conditions = [self.model_class.is_deleted == 'N']

            for field, value in kwargs.items():
                field_obj = getattr(self.model_class, field)
                conditions.append(field_obj == value)

            stmt = select(func.count(self.model_class.id)).where(and_(*conditions))
            result = await self.session.execute(stmt)
            count = result.scalar()
            return count > 0
        except Exception as e:
            logger.error(f"检查记录存在性失败: {e}")
            raise

    async def find_by_conditions(
        self,
        conditions: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        order_by: str = None
    ) -> List[T]:
        """根据条件查找记录"""
        try:
            stmt = select(self.model_class).where(self.model_class.is_deleted == 'N')

            for field, value in conditions.items():
                field_obj = getattr(self.model_class, field)
                if isinstance(value, dict):
                    # 处理特殊操作符
                    if 'in' in value:
                        stmt = stmt.where(field_obj.in_(value['in']))
                    elif 'like' in value:
                        stmt = stmt.where(field_obj.like(value['like']))
                    elif 'gt' in value:
                        stmt = stmt.where(field_obj > value['gt'])
                    elif 'gte' in value:
                        stmt = stmt.where(field_obj >= value['gte'])
                    elif 'lt' in value:
                        stmt = stmt.where(field_obj < value['lt'])
                    elif 'lte' in value:
                        stmt = stmt.where(field_obj <= value['lte'])
                    elif 'ne' in value:
                        stmt = stmt.where(field_obj != value['ne'])
                else:
                    stmt = stmt.where(field_obj == value)

            if order_by:
                order_field = getattr(self.model_class, order_by)
                stmt = stmt.order_by(order_field.desc())

            stmt = stmt.offset(skip).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"根据条件查找记录失败: {e}")
            raise

    async def upsert(self, unique_fields: List[str], data: Dict[str, Any]) -> T:
        """插入或更新记录"""
        try:
            # 构建冲突条件
            conflict_condition = and_(*[
                getattr(self.model_class, field) == data[field]
                for field in unique_fields
                if field in data
            ])

            # 检查记录是否存在
            check_stmt = select(self.model_class).where(
                and_(conflict_condition, self.model_class.is_deleted == 'N')
            )
            result = await self.session.execute(check_stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # 更新现有记录
                for key, value in data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                await self.session.flush()
                await self.session.refresh(existing)
                logger.debug(f"更新记录成功: {self.model_class.__name__}(id={existing.id})")
                return existing
            else:
                # 创建新记录
                return await self.create(**data)

        except Exception as e:
            logger.error(f"插入或更新记录失败: {e}")
            await self.session.rollback()
            raise

    async def bulk_upsert(self, data_list: List[Dict[str, Any]], unique_fields: List[str]) -> List[T]:
        """批量插入或更新记录 (PostgreSQL ON CONFLICT)"""
        try:
            if not data_list:
                return []

            # 构建 insert 语句
            stmt = insert(self.model_class).values(data_list)

            # 构建更新字段（排除唯一字段和系统字段）
            update_fields = {
                name: getattr(stmt.excluded, name)
                for name in data_list[0].keys()
                if name not in unique_fields + ['id', 'created_at']
            }
            update_fields['updated_at'] = func.now()

            # 添加 ON CONFLICT 子句
            conflict_condition = and_(*[
                getattr(self.model_class, field) == getattr(stmt.excluded, field)
                for field in unique_fields
                if field in data_list[0]
            ])

            stmt = stmt.on_conflict_do_update(
                constraint_elements=conflict_condition,
                set_=update_fields
            ).returning(self.model_class)

            result = await self.session.execute(stmt)
            instances = result.scalars().all()

            logger.debug(f"批量插入或更新成功: {len(instances)} 条 {self.model_class.__name__}")
            return instances

        except Exception as e:
            logger.error(f"批量插入或更新记录失败: {e}")
            await self.session.rollback()
            raise