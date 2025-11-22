"""
图片数据访问层
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select

from src.models.image import ProductImage
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ImageRepository(BaseRepository[ProductImage]):
    """图片仓储类"""

    def __init__(self, session):
        super().__init__(session, ProductImage)

    async def get_by_product_id(self, product_id: int, image_type: str = None) -> List[ProductImage]:
        """根据商品ID获取图片"""
        conditions = {'product_id': product_id}
        if image_type:
            conditions['image_type'] = image_type
        return await self.find_by_conditions(conditions)

    async def get_main_image(self, product_id: int) -> Optional[ProductImage]:
        """获取商品主图"""
        try:
            stmt = select(ProductImage).where(
                and_(
                    ProductImage.product_id == product_id,
                    ProductImage.image_type == 'main',
                    ProductImage.is_deleted == 'N'
                )
            ).order_by(ProductImage.sort_order.asc()).limit(1)

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取商品主图失败: {e}")
            raise

    async def get_detail_images(self, product_id: int) -> List[ProductImage]:
        """获取商品详情图"""
        return await self.get_by_product_id(product_id, 'detail')

    async def get_images_by_status(self, download_status: str = None, process_status: str = None) -> List[ProductImage]:
        """根据状态获取图片"""
        conditions = {}
        if download_status:
            conditions['download_status'] = download_status
        if process_status:
            conditions['process_status'] = process_status
        return await self.find_by_conditions(conditions)

    async def get_pending_download_images(self, limit: int = 100) -> List[ProductImage]:
        """获取待下载图片"""
        return await self.get_images_by_status(download_status='pending', process_status='pending')

    async def get_failed_download_images(self, limit: int = 100) -> List[ProductImage]:
        """获取下载失败图片"""
        return await self.get_images_by_status(download_status='failed')

    async def get_unprocessed_images(self, limit: int = 100) -> List[ProductImage]:
        """获取未处理图片"""
        return await self.find_by_conditions({
            'download_status': 'completed',
            'process_status': {'in': ['pending', 'failed']}
        }, limit=limit)

    async def update_download_status(self, image_id: int, status: str, local_path: str = None, error_message: str = None) -> bool:
        """更新图片下载状态"""
        update_data = {'download_status': status}
        if local_path:
            update_data['local_path'] = local_path
        if error_message:
            update_data['error_message'] = error_message

        if status == 'failed':
            # 增加重试次数
            image = await self.get_by_id(image_id)
            if image:
                update_data['retry_count'] = image.retry_count + 1

        result = await self.update(image_id, **update_data)
        return result is not None

    async def update_process_status(self, image_id: int, status: str, error_message: str = None) -> bool:
        """更新图片处理状态"""
        update_data = {'process_status': status}
        if error_message:
            update_data['error_message'] = error_message

        result = await self.update(image_id, **update_data)
        return result is not None

    async def batch_update_download_status(self, image_ids: List[int], status: str) -> int:
        """批量更新下载状态"""
        return await self.update_batch(
            {'id': {'in': image_ids}},
            {'download_status': status}
        )

    async def batch_update_process_status(self, image_ids: List[int], status: str) -> int:
        """批量更新处理状态"""
        return await self.update_batch(
            {'id': {'in': image_ids}},
            {'process_status': status}
        )

    async def create_product_image(self, product_id: int, url: str, image_type: str = 'detail', sort_order: int = 0) -> ProductImage:
        """创建商品图片记录"""
        return await self.create(
            product_id=product_id,
            url=url,
            image_type=image_type,
            sort_order=sort_order
        )

    async def create_or_update_image(self, product_id: int, url: str, **kwargs) -> ProductImage:
        """创建或更新图片记录"""
        # 检查是否已存在相同URL的图片
        existing = await self.find_by_conditions({'url': url})
        if existing:
            return existing[0]

        return await self.create(
            product_id=product_id,
            url=url,
            **kwargs
        )

    async def bulk_create_product_images(self, images_data: List[Dict]) -> List[ProductImage]:
        """批量创建商品图片"""
        return await self.create_batch(images_data)

    async def get_image_statistics(self) -> Dict:
        """获取图片统计信息"""
        try:
            # 总图片数
            total_stmt = select(func.count(ProductImage.id)).where(ProductImage.is_deleted == 'N')
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar()

            # 按下载状态统计
            download_status_stmt = select(
                ProductImage.download_status,
                func.count(ProductImage.id).label('count')
            ).where(ProductImage.is_deleted == 'N').group_by(ProductImage.download_status)

            download_status_result = await self.session.execute(download_status_stmt)
            download_status_stats = [
                {'status': row.download_status, 'count': row.count}
                for row in download_status_result
            ]

            # 按处理状态统计
            process_status_stmt = select(
                ProductImage.process_status,
                func.count(ProductImage.id).label('count')
            ).where(ProductImage.is_deleted == 'N').group_by(ProductImage.process_status)

            process_status_result = await self.session.execute(process_status_stmt)
            process_status_stats = [
                {'status': row.process_status, 'count': row.count}
                for row in process_status_result
            ]

            # 按图片类型统计
            image_type_stmt = select(
                ProductImage.image_type,
                func.count(ProductImage.id).label('count')
            ).where(ProductImage.is_deleted == 'N').group_by(ProductImage.image_type)

            image_type_result = await self.session.execute(image_type_stmt)
            image_type_stats = [
                {'image_type': row.image_type, 'count': row.count}
                for row in image_type_result
            ]

            # 存储大小统计
            size_stmt = select(
                func.sum(ProductImage.size).label('total_size'),
                func.avg(ProductImage.size).label('avg_size')
            ).where(
                and_(
                    ProductImage.is_deleted == 'N',
                    ProductImage.size.isnot(None)
                )
            )

            size_result = await self.session.execute(size_stmt)
            size_stats = size_result.first()

            return {
                'total_count': total_count,
                'download_status_distribution': download_status_stats,
                'process_status_distribution': process_status_stats,
                'image_type_distribution': image_type_stats,
                'size_statistics': {
                    'total_size_mb': round((size_stats.total_size or 0) / (1024 * 1024), 2),
                    'avg_size_mb': round((size_stats.avg_size or 0) / (1024 * 1024), 2),
                }
            }

        except Exception as e:
            logger.error(f"获取图片统计失败: {e}")
            raise

    async def get_product_images_summary(self, product_id: int) -> Dict:
        """获取商品图片汇总信息"""
        try:
            # 图片总数
            count_stmt = select(func.count(ProductImage.id)).where(
                and_(ProductImage.product_id == product_id, ProductImage.is_deleted == 'N')
            )
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar()

            # 按类型统计
            type_stmt = select(
                ProductImage.image_type,
                func.count(ProductImage.id).label('count')
            ).where(
                and_(
                    ProductImage.product_id == product_id,
                    ProductImage.is_deleted == 'N'
                )
            ).group_by(ProductImage.image_type)

            type_result = await self.session.execute(type_stmt)
            type_stats = {
                row.image_type: row.count
                for row in type_result
            }

            # 下载状态统计
            download_stmt = select(
                ProductImage.download_status,
                func.count(ProductImage.id).label('count')
            ).where(
                and_(
                    ProductImage.product_id == product_id,
                    ProductImage.is_deleted == 'N'
                )
            ).group_by(ProductImage.download_status)

            download_result = await self.session.execute(download_stmt)
            download_stats = {
                row.download_status: row.count
                for row in download_result
            }

            return {
                'total_count': total_count,
                'type_distribution': type_stats,
                'download_status_distribution': download_stats,
                'has_main_image': type_stats.get('main', 0) > 0,
                'has_detail_images': type_stats.get('detail', 0) > 0,
                'download_completed': download_stats.get('completed', 0),
                'download_pending': download_stats.get('pending', 0),
                'download_failed': download_stats.get('failed', 0),
            }

        except Exception as e:
            logger.error(f"获取商品图片汇总失败: {e}")
            raise

    async def find_duplicate_images(self, product_id: int = None) -> List[List[ProductImage]]:
        """查找重复图片"""
        try:
            # 按URL分组查找重复
            stmt = select(
                ProductImage.url,
                func.count(ProductImage.id).label('count'),
                func.array_agg(ProductImage.id).label('image_ids')
            ).where(ProductImage.is_deleted == 'N')

            if product_id:
                stmt = stmt.where(ProductImage.product_id == product_id)

            stmt = stmt.group_by(ProductImage.url).having(func.count(ProductImage.id) > 1)

            result = await self.session.execute(stmt)
            duplicates = []
            for row in result:
                # 获取重复的图片记录
                images = await self.find_by_conditions({'id': {'in': list(row.image_ids)}})
                if len(images) > 1:
                    duplicates.append(images)

            return duplicates

        except Exception as e:
            logger.error(f"查找重复图片失败: {e}")
            raise

    async def cleanup_orphaned_images(self) -> int:
        """清理孤儿图片（不存在对应商品的图片）"""
        try:
            from sqlalchemy import delete
            from src.models.product import Product

            # 删除不存在对应商品的图片记录
            stmt = delete(ProductImage).where(
                and_(
                    ProductImage.is_deleted == 'N',
                    ~ProductImage.product_id.in_(
                        select(Product.id).where(Product.is_deleted == 'N')
                    )
                )
            )

            result = await self.session.execute(stmt)
            deleted_count = result.rowcount

            logger.info(f"清理孤儿图片完成: {deleted_count} 条记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理孤儿图片失败: {e}")
            raise

    async def retry_failed_downloads(self, max_retry_count: int = 3) -> List[ProductImage]:
        """重试失败的下载"""
        try:
            stmt = select(ProductImage).where(
                and_(
                    ProductImage.is_deleted == 'N',
                    ProductImage.download_status == 'failed',
                    ProductImage.retry_count < max_retry_count
                )
            ).order_by(ProductImage.retry_count.asc())

            result = await self.session.execute(stmt)
            images = result.scalars().all()

            # 重置状态为待下载
            for image in images:
                await self.update_download_status(image.id, 'pending')

            logger.info(f"重置失败下载状态: {len(images)} 张图片")
            return images

        except Exception as e:
            logger.error(f"重试失败下载失败: {e}")
            raise