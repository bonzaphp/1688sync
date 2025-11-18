"""
数据一致性保障机制
"""
import logging
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.models.supplier import Supplier
from src.models.image import ProductImage
from src.models.sync_record import SyncRecord

logger = logging.getLogger(__name__)


class DataConsistencyManager:
    """数据一致性管理器"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_supplier_product_consistency(self) -> Dict:
        """检查供应商与商品数据一致性"""
        try:
            issues = []

            # 1. 检查商品引用的供应商是否存在
            orphaned_products_stmt = select(Product.id, Product.supplier_id).where(
                and_(
                    Product.is_deleted == 'N',
                    ~Product.supplier_id.in_(
                        select(Supplier.id).where(Supplier.is_deleted == 'N')
                    )
                )
            )
            orphaned_result = await self.session.execute(orphaned_products_stmt)
            orphaned_products = orphaned_result.all()

            if orphaned_products:
                issues.append({
                    'type': 'orphaned_products',
                    'count': len(orphaned_products),
                    'details': [
                        {'product_id': row.id, 'supplier_id': row.supplier_id}
                        for row in orphaned_products
                    ]
                })

            # 2. 检查供应商商品数量是否正确
            supplier_count_stmt = select(
                Supplier.id,
                Supplier.product_count,
                func.count(Product.id).label('actual_count')
            ).outerjoin(
                Product, and_(
                    Product.supplier_id == Supplier.id,
                    Product.is_deleted == 'N'
                )
            ).where(
                Supplier.is_deleted == 'N'
            ).group_by(Supplier.id, Supplier.product_count)

            count_result = await self.session.execute(supplier_count_stmt)
            count_mismatches = []

            for row in count_result:
                if row.product_count != row.actual_count:
                    count_mismatches.append({
                        'supplier_id': row.id,
                        'stored_count': row.product_count,
                        'actual_count': row.actual_count,
                        'difference': row.product_count - row.actual_count
                    })

            if count_mismatches:
                issues.append({
                    'type': 'product_count_mismatch',
                    'count': len(count_mismatches),
                    'details': count_mismatches
                })

            # 3. 检查重复的供应商source_id
            duplicate_supplier_stmt = select(
                Supplier.source_id,
                func.count(Supplier.id).label('count')
            ).where(
                and_(
                    Supplier.is_deleted == 'N',
                    Supplier.source_id.isnot(None)
                )
            ).group_by(Supplier.source_id).having(func.count(Supplier.id) > 1)

            duplicate_result = await self.session.execute(duplicate_supplier_stmt)
            duplicate_suppliers = [
                {'source_id': row.source_id, 'count': row.count}
                for row in duplicate_result
            ]

            if duplicate_suppliers:
                issues.append({
                    'type': 'duplicate_suppliers',
                    'count': len(duplicate_suppliers),
                    'details': duplicate_suppliers
                })

            return {
                'status': 'completed',
                'issues_found': len(issues),
                'issues': issues
            }

        except Exception as e:
            logger.error(f"检查供应商商品一致性失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def check_product_image_consistency(self) -> Dict:
        """检查商品与图片数据一致性"""
        try:
            issues = []

            # 1. 检查图片引用的商品是否存在
            orphaned_images_stmt = select(ProductImage.id, ProductImage.product_id).where(
                and_(
                    ProductImage.is_deleted == 'N',
                    ~ProductImage.product_id.in_(
                        select(Product.id).where(Product.is_deleted == 'N')
                    )
                )
            )
            orphaned_result = await self.session.execute(orphaned_images_stmt)
            orphaned_images = orphaned_result.all()

            if orphaned_images:
                issues.append({
                    'type': 'orphaned_images',
                    'count': len(orphaned_images),
                    'details': [
                        {'image_id': row.id, 'product_id': row.product_id}
                        for row in orphaned_images
                    ]
                })

            # 2. 检查商品的主图配置是否正确
            products_without_main_image_stmt = select(Product.id).where(
                and_(
                    Product.is_deleted == 'N',
                    Product.status == 'active',
                    ~Product.id.in_(
                        select(ProductImage.product_id).where(
                            and_(
                                ProductImage.is_deleted == 'N',
                                ProductImage.image_type == 'main'
                            )
                        )
                    )
                )
            )
            main_image_result = await self.session.execute(products_without_main_image_stmt)
            products_without_main_image = [row.id for row in main_image_result]

            if products_without_main_image:
                issues.append({
                    'type': 'missing_main_images',
                    'count': len(products_without_main_image),
                    'details': [{'product_id': pid} for pid in products_without_main_image]
                })

            # 3. 检查重复的图片URL
            duplicate_image_stmt = select(
                ProductImage.url,
                func.count(ProductImage.id).label('count')
            ).where(
                and_(
                    ProductImage.is_deleted == 'N',
                    ProductImage.url.isnot(None)
                )
            ).group_by(ProductImage.url).having(func.count(ProductImage.id) > 1)

            duplicate_result = await self.session.execute(duplicate_image_stmt)
            duplicate_images = [
                {'url': row.url, 'count': row.count}
                for row in duplicate_result
            ]

            if duplicate_images:
                issues.append({
                    'type': 'duplicate_images',
                    'count': len(duplicate_images),
                    'details': duplicate_images
                })

            return {
                'status': 'completed',
                'issues_found': len(issues),
                'issues': issues
            }

        except Exception as e:
            logger.error(f"检查商品图片一致性失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def check_sync_record_consistency(self) -> Dict:
        """检查同步记录数据一致性"""
        try:
            issues = []

            # 1. 检查长时间运行的同步任务
            import time
            long_running_threshold = 24 * 3600  # 24小时
            cutoff_time = int(time.time()) - long_running_threshold

            long_running_stmt = select(SyncRecord.task_id, SyncRecord.start_time).where(
                and_(
                    SyncRecord.status == 'running',
                    SyncRecord.start_time < cutoff_time
                )
            )
            long_running_result = await self.session.execute(long_running_stmt)
            long_running_tasks = [
                {
                    'task_id': row.task_id,
                    'start_time': row.start_time,
                    'duration_hours': (time.time() - row.start_time) / 3600
                }
                for row in long_running_result
            ]

            if long_running_tasks:
                issues.append({
                    'type': 'long_running_tasks',
                    'count': len(long_running_tasks),
                    'details': long_running_tasks
                })

            # 2. 检查同步记录的数据一致性
            inconsistent_records_stmt = select(SyncRecord.id, SyncRecord.task_id).where(
                and_(
                    SyncRecord.is_deleted == 'N',
                    or_(
                        and_(
                            SyncRecord.total_count < 0,
                            SyncRecord.total_count.isnot(None)
                        ),
                        and_(
                            SyncRecord.processed_count < 0,
                            SyncRecord.processed_count.isnot(None)
                        ),
                        and_(
                            SyncRecord.success_count < 0,
                            SyncRecord.success_count.isnot(None)
                        ),
                        and_(
                            SyncRecord.failed_count < 0,
                            SyncRecord.failed_count.isnot(None)
                        ),
                        and_(
                            SyncRecord.processed_count > SyncRecord.total_count,
                            SyncRecord.total_count.isnot(None)
                        )
                    )
                )
            )
            inconsistent_result = await self.session.execute(inconsistent_records_stmt)
            inconsistent_records = [
                {'record_id': row.id, 'task_id': row.task_id}
                for row in inconsistent_result
            ]

            if inconsistent_records:
                issues.append({
                    'type': 'inconsistent_records',
                    'count': len(inconsistent_records),
                    'details': inconsistent_records
                })

            return {
                'status': 'completed',
                'issues_found': len(issues),
                'issues': issues
            }

        except Exception as e:
            logger.error(f"检查同步记录一致性失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def fix_supplier_product_consistency(self, dry_run: bool = True) -> Dict:
        """修复供应商与商品数据一致性问题"""
        try:
            fixes_applied = []

            if not dry_run:
                # 1. 修复供应商商品数量
                supplier_count_stmt = select(
                    Supplier.id,
                    func.count(Product.id).label('actual_count')
                ).outerjoin(
                    Product, and_(
                        Product.supplier_id == Supplier.id,
                        Product.is_deleted == 'N'
                    )
                ).where(
                    Supplier.is_deleted == 'N'
                ).group_by(Supplier.id)

                count_result = await self.session.execute(supplier_count_stmt)
                updates_count = 0

                for row in count_result:
                    if await self.session.execute(
                        text("UPDATE suppliers SET product_count = :count WHERE id = :id"),
                        {'count': row.actual_count, 'id': row.id}
                    ):
                        updates_count += 1

                if updates_count > 0:
                    fixes_applied.append({
                        'type': 'supplier_product_count_fix',
                        'count': updates_count
                    })

                await self.session.commit()

            return {
                'status': 'completed',
                'dry_run': dry_run,
                'fixes_applied': len(fixes_applied),
                'details': fixes_applied
            }

        except Exception as e:
            logger.error(f"修复供应商商品一致性失败: {e}")
            await self.session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }

    async def cleanup_orphaned_records(self, dry_run: bool = True) -> Dict:
        """清理孤儿记录"""
        try:
            cleanup_stats = {}

            if not dry_run:
                # 1. 清理孤儿商品（供应商不存在）
                orphaned_products_stmt = text("""
                    DELETE FROM products
                    WHERE is_deleted = 'N'
                    AND supplier_id NOT IN (SELECT id FROM suppliers WHERE is_deleted = 'N')
                """)
                result = await self.session.execute(orphaned_products_stmt)
                cleanup_stats['orphaned_products'] = result.rowcount

                # 2. 清理孤儿图片（商品不存在）
                orphaned_images_stmt = text("""
                    DELETE FROM product_images
                    WHERE is_deleted = 'N'
                    AND product_id NOT IN (SELECT id FROM products WHERE is_deleted = 'N')
                """)
                result = await self.session.execute(orphaned_images_stmt)
                cleanup_stats['orphaned_images'] = result.rowcount

                # 3. 清理无效的同步记录（超过90天的已完成记录）
                import time
                cutoff_time = int(time.time()) - (90 * 24 * 3600)

                old_sync_records_stmt = text("""
                    DELETE FROM sync_records
                    WHERE start_time < :cutoff_time
                    AND status IN ('completed', 'failed', 'cancelled')
                """)
                result = await self.session.execute(old_sync_records_stmt, {'cutoff_time': cutoff_time})
                cleanup_stats['old_sync_records'] = result.rowcount

                await self.session.commit()

            return {
                'status': 'completed',
                'dry_run': dry_run,
                'cleanup_stats': cleanup_stats
            }

        except Exception as e:
            logger.error(f"清理孤儿记录失败: {e}")
            await self.session.rollback()
            return {
                'status': 'error',
                'error': str(e)
            }

    async def validate_data_integrity(self) -> Dict:
        """全面的数据完整性验证"""
        try:
            results = {}

            # 供应商商品一致性
            results['supplier_product'] = await self.check_supplier_product_consistency()

            # 商品图片一致性
            results['product_image'] = await self.check_product_image_consistency()

            # 同步记录一致性
            results['sync_record'] = await self.check_sync_record_consistency()

            # 数据库约束验证
            constraint_issues = await self._check_database_constraints()
            results['database_constraints'] = constraint_issues

            # 统计总体问题
            total_issues = sum(
                result.get('issues_found', 0) for result in results.values()
                if isinstance(result, dict) and 'issues_found' in result
            )

            return {
                'status': 'completed',
                'total_issues': total_issues,
                'validation_results': results
            }

        except Exception as e:
            logger.error(f"数据完整性验证失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _check_database_constraints(self) -> Dict:
        """检查数据库约束"""
        try:
            issues = []

            # 检查外键约束
            foreign_key_checks = [
                {
                    'table': 'products',
                    'column': 'supplier_id',
                    'reference': 'suppliers.id'
                },
                {
                    'table': 'product_images',
                    'column': 'product_id',
                    'reference': 'products.id'
                }
            ]

            for check in foreign_key_checks:
                stmt = text(f"""
                    SELECT COUNT(*) as count
                    FROM {check['table']} t1
                    LEFT JOIN {check['reference'].split('.')[0]} t2 ON t1.{check['column']} = t2.{check['reference'].split('.')[1]}
                    WHERE t1.is_deleted = 'N' AND t2.id IS NULL
                """)
                result = await self.session.execute(stmt)
                count = result.scalar()

                if count > 0:
                    issues.append({
                        'type': 'foreign_key_violation',
                        'table': check['table'],
                        'column': check['column'],
                        'reference': check['reference'],
                        'count': count
                    })

            return {
                'status': 'completed',
                'issues_found': len(issues),
                'issues': issues
            }

        except Exception as e:
            logger.error(f"检查数据库约束失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def generate_consistency_report(self) -> Dict:
        """生成一致性报告"""
        try:
            validation_result = await self.validate_data_integrity()

            # 生成修复建议
            recommendations = []

            for category, result in validation_result['validation_results'].items():
                if isinstance(result, dict) and result.get('issues_found', 0) > 0:
                    for issue in result.get('issues', []):
                        if issue['type'] == 'orphaned_products':
                            recommendations.append({
                                'category': category,
                                'issue': issue['type'],
                                'action': 'cleanup_orphaned_records',
                                'priority': 'high',
                                'description': f"清理 {issue['count']} 个孤儿商品记录"
                            })
                        elif issue['type'] == 'product_count_mismatch':
                            recommendations.append({
                                'category': category,
                                'issue': issue['type'],
                                'action': 'fix_supplier_product_consistency',
                                'priority': 'medium',
                                'description': f"修复 {issue['count']} 个供应商的商品数量统计"
                            })
                        elif issue['type'] == 'missing_main_images':
                            recommendations.append({
                                'category': category,
                                'issue': issue['type'],
                                'action': 'download_missing_images',
                                'priority': 'medium',
                                'description': f"为 {issue['count']} 个商品下载主图"
                            })

            return {
                'status': 'completed',
                'validation_summary': validation_result,
                'recommendations': recommendations,
                'generated_at': int(__import__('time').time())
            }

        except Exception as e:
            logger.error(f"生成一致性报告失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }