# Data Sync Tasks
# 数据同步相关任务

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .base import BaseTask, TaskResult, register_task
from ...database.connection import get_db_session
from ...models.sync_record import SyncRecord
from ...services.product_repository import ProductRepository
from ...services.supplier_repository import SupplierRepository
from ...services.data_consistency import DataConsistencyManager

logger = logging.getLogger(__name__)


@register_task('src.queue.tasks.data_sync.sync_products')
class SyncProductsTask(BaseTask):
    """同步产品数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        # 可选参数，不需要严格验证
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行产品数据同步任务"""
        try:
            batch_size = kwargs.get('batch_size', 100)
            source_system = kwargs.get('source_system', '1688')
            sync_type = kwargs.get('sync_type', 'incremental')  # full, incremental
            filters = kwargs.get('filters', {})

            self.update_progress(0, 100, "开始同步产品数据")

            # 创建同步记录
            sync_record = self._create_sync_record('products', source_system, sync_type)

            product_repo = ProductRepository()
            consistency_service = DataConsistencyManager(session)

            # 获取需要同步的产品
            if sync_type == 'full':
                products = product_repo.get_all_for_sync(batch_size=batch_size, **filters)
            else:
                # 增量同步 - 获取最近更新的产品
                since = kwargs.get('since', datetime.utcnow() - timedelta(hours=24))
                products = product_repo.get_updated_since(since, batch_size=batch_size, **filters)

            total_products = len(products)
            synced_count = 0
            failed_count = 0

            self.update_progress(10, 100, f"找到 {total_products} 个产品需要同步")

            # 分批同步
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]

                for product in batch:
                    try:
                        # 执行同步逻辑
                        sync_result = self._sync_single_product(product, source_system)

                        if sync_result['success']:
                            synced_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"产品同步失败 {product.id}: {sync_result['error']}")

                        # 更新进度
                        progress = 10 + int((synced_count + failed_count) / total_products * 80)
                        self.update_progress(
                            progress,
                            100,
                            f"已同步 {synced_count} 个产品，失败 {failed_count} 个"
                        )

                    except Exception as e:
                        logger.error(f"同步产品异常 {product.id}: {e}")
                        failed_count += 1

            # 数据一致性检查
            self.update_progress(90, 100, "执行数据一致性检查")
            consistency_issues = consistency_service.check_product_consistency(batch=products[:100])

            # 更新同步记录
            self._update_sync_record(
                sync_record.id,
                'completed',
                {
                    'total_products': total_products,
                    'synced_count': synced_count,
                    'failed_count': failed_count,
                    'consistency_issues': len(consistency_issues)
                }
            )

            self.update_progress(100, 100, "产品数据同步完成")

            result_data = {
                'sync_record_id': sync_record.id,
                'total_products': total_products,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'consistency_issues': consistency_issues
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"产品数据同步任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _create_sync_record(self, entity_type: str, source_system: str, sync_type: str) -> SyncRecord:
        """创建同步记录"""
        with get_db_session() as session:
            sync_record = SyncRecord(
                entity_type=entity_type,
                source_system=source_system,
                sync_type=sync_type,
                status='running',
                started_at=datetime.utcnow()
            )
            session.add(sync_record)
            session.commit()
            session.refresh(sync_record)
            return sync_record

    def _update_sync_record(self, record_id: int, status: str, result_data: Dict[str, Any]):
        """更新同步记录"""
        with get_db_session() as session:
            sync_record = session.query(SyncRecord).filter_by(id=record_id).first()
            if sync_record:
                sync_record.status = status
                sync_record.result_data = json.dumps(result_data)
                sync_record.completed_at = datetime.utcnow()
                sync_record.updated_at = datetime.utcnow()
                session.commit()

    def _sync_single_product(self, product, source_system: str) -> Dict[str, Any]:
        """同步单个产品"""
        try:
            # 这里应该包含实际的同步逻辑
            # 例如：调用外部API、更新远程系统等

            # 模拟同步
            import time
            time.sleep(0.1)  # 模拟网络延迟

            # 更新产品的最后同步时间
            product.last_sync_at = datetime.utcnow()
            product.sync_source = source_system

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}


@register_task('src.queue.tasks.data_sync.sync_suppliers')
class SyncSuppliersTask(BaseTask):
    """同步供应商数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行供应商数据同步任务"""
        try:
            batch_size = kwargs.get('batch_size', 50)
            source_system = kwargs.get('source_system', '1688')
            sync_type = kwargs.get('sync_type', 'incremental')

            self.update_progress(0, 100, "开始同步供应商数据")

            # 创建同步记录
            sync_record = self._create_sync_record('suppliers', source_system, sync_type)

            supplier_repo = SupplierRepository()
            consistency_service = DataConsistencyManager(session)

            # 获取需要同步的供应商
            if sync_type == 'full':
                suppliers = supplier_repo.get_all_for_sync(batch_size=batch_size)
            else:
                since = kwargs.get('since', datetime.utcnow() - timedelta(hours=24))
                suppliers = supplier_repo.get_updated_since(since, batch_size=batch_size)

            total_suppliers = len(suppliers)
            synced_count = 0
            failed_count = 0

            self.update_progress(10, 100, f"找到 {total_suppliers} 个供应商需要同步")

            # 分批同步
            for i in range(0, len(suppliers), batch_size):
                batch = suppliers[i:i + batch_size]

                for supplier in batch:
                    try:
                        # 执行同步逻辑
                        sync_result = self._sync_single_supplier(supplier, source_system)

                        if sync_result['success']:
                            synced_count += 1
                        else:
                            failed_count += 1

                        # 更新进度
                        progress = 10 + int((synced_count + failed_count) / total_suppliers * 80)
                        self.update_progress(
                            progress,
                            100,
                            f"已同步 {synced_count} 个供应商，失败 {failed_count} 个"
                        )

                    except Exception as e:
                        logger.error(f"同步供应商异常 {supplier.id}: {e}")
                        failed_count += 1

            # 数据一致性检查
            self.update_progress(90, 100, "执行数据一致性检查")
            consistency_issues = consistency_service.check_supplier_consistency(batch=suppliers[:50])

            # 更新同步记录
            self._update_sync_record(
                sync_record.id,
                'completed',
                {
                    'total_suppliers': total_suppliers,
                    'synced_count': synced_count,
                    'failed_count': failed_count,
                    'consistency_issues': len(consistency_issues)
                }
            )

            self.update_progress(100, 100, "供应商数据同步完成")

            result_data = {
                'sync_record_id': sync_record.id,
                'total_suppliers': total_suppliers,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'consistency_issues': consistency_issues
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"供应商数据同步任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _sync_single_supplier(self, supplier, source_system: str) -> Dict[str, Any]:
        """同步单个供应商"""
        try:
            # 模拟同步逻辑
            import time
            time.sleep(0.15)

            # 更新供应商的最后同步时间
            supplier.last_sync_at = datetime.utcnow()
            supplier.sync_source = source_system

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}


@register_task('src.queue.tasks.data_sync.validate_data')
class ValidateDataTask(BaseTask):
    """数据验证任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行数据验证任务"""
        try:
            validation_type = kwargs.get('type', 'all')  # products, suppliers, all
            sample_size = kwargs.get('sample_size', 1000)
            fix_issues = kwargs.get('fix_issues', False)

            self.update_progress(0, 100, "开始数据验证")

            consistency_service = DataConsistencyManager(session)
            validation_results = {}

            # 验证产品数据
            if validation_type in ['products', 'all']:
                self.update_progress(20, 100, "验证产品数据")
                product_issues = consistency_service.check_product_consistency(sample_size=sample_size)
                validation_results['products'] = {
                    'issues_found': len(product_issues),
                    'issues': product_issues[:10]  # 只返回前10个问题
                }

                if fix_issues and product_issues:
                    self.update_progress(40, 100, "修复产品数据问题")
                    fixed_products = consistency_service.fix_product_issues(product_issues)
                    validation_results['products']['fixed_count'] = len(fixed_products)

            # 验证供应商数据
            if validation_type in ['suppliers', 'all']:
                self.update_progress(60, 100, "验证供应商数据")
                supplier_issues = consistency_service.check_supplier_consistency(sample_size=sample_size)
                validation_results['suppliers'] = {
                    'issues_found': len(supplier_issues),
                    'issues': supplier_issues[:10]
                }

                if fix_issues and supplier_issues:
                    self.update_progress(80, 100, "修复供应商数据问题")
                    fixed_suppliers = consistency_service.fix_supplier_issues(supplier_issues)
                    validation_results['suppliers']['fixed_count'] = len(fixed_suppliers)

            self.update_progress(100, 100, "数据验证完成")

            # 统计总体结果
            total_issues = sum(result['issues_found'] for result in validation_results.values())
            total_fixed = sum(result.get('fixed_count', 0) for result in validation_results.values())

            result_data = {
                'validation_type': validation_type,
                'sample_size': sample_size,
                'total_issues': total_issues,
                'total_fixed': total_fixed,
                'results': validation_results
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"数据验证任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )


@register_task('src.queue.tasks.data_sync.cleanup_duplicates')
class CleanupDuplicatesTask(BaseTask):
    """清理重复数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行清理重复数据任务"""
        try:
            entity_type = kwargs.get('entity_type', 'all')  # products, suppliers, all
            dry_run = kwargs.get('dry_run', True)  # 是否只检查不删除
            batch_size = kwargs.get('batch_size', 100)

            self.update_progress(0, 100, "开始清理重复数据")

            consistency_service = DataConsistencyManager(session)
            cleanup_results = {}

            # 清理产品重复数据
            if entity_type in ['products', 'all']:
                self.update_progress(20, 100, "检查产品重复数据")
                product_duplicates = consistency_service.find_duplicate_products()

                if product_duplicates:
                    cleanup_results['products'] = {
                        'duplicate_groups': len(product_duplicates),
                        'total_duplicates': sum(len(group) - 1 for group in product_duplicates),
                        'duplicates': product_duplicates[:5]  # 只返回前5组
                    }

                    if not dry_run:
                        self.update_progress(40, 100, "清理产品重复数据")
                        removed_products = consistency_service.remove_duplicate_products(
                            product_duplicates, batch_size=batch_size
                        )
                        cleanup_results['products']['removed_count'] = len(removed_products)

            # 清理供应商重复数据
            if entity_type in ['suppliers', 'all']:
                self.update_progress(60, 100, "检查供应商重复数据")
                supplier_duplicates = consistency_service.find_duplicate_suppliers()

                if supplier_duplicates:
                    cleanup_results['suppliers'] = {
                        'duplicate_groups': len(supplier_duplicates),
                        'total_duplicates': sum(len(group) - 1 for group in supplier_duplicates),
                        'duplicates': supplier_duplicates[:5]
                    }

                    if not dry_run:
                        self.update_progress(80, 100, "清理供应商重复数据")
                        removed_suppliers = consistency_service.remove_duplicate_suppliers(
                            supplier_duplicates, batch_size=batch_size
                        )
                        cleanup_results['suppliers']['removed_count'] = len(removed_suppliers)

            self.update_progress(100, 100, "重复数据清理完成")

            # 统计总体结果
            total_duplicates = sum(
                result.get('total_duplicates', 0) for result in cleanup_results.values()
            )
            total_removed = sum(
                result.get('removed_count', 0) for result in cleanup_results.values()
            )

            result_data = {
                'entity_type': entity_type,
                'dry_run': dry_run,
                'total_duplicates': total_duplicates,
                'total_removed': total_removed,
                'results': cleanup_results
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"清理重复数据任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )