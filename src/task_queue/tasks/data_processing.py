"""
数据处理任务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseTask, TaskResult, register_task
from ...data_processing.pipeline import DataPipeline
from ...data_processing.cleaner import DataCleaner
from ...data_processing.validator import DataValidator
from ...data_processing.deduplicator import DataDeduplicator
from ...data_processing.quality_monitor import DataQualityMonitor
from ..database.connection import get_db_session
from ..services.product_repository import ProductRepository
from ..services.supplier_repository import SupplierRepository

logger = logging.getLogger(__name__)


@register_task('src.queue.tasks.data_processing.process_raw_products')
class ProcessRawProductsTask(BaseTask):
    """处理原始商品数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True  # 原始数据可以是任意格式

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行商品数据处理"""
        try:
            # 获取参数
            batch_size = kwargs.get('batch_size', 100)
            source_system = kwargs.get('source_system', '1688')
            processing_options = kwargs.get('options', {})
            export_report = kwargs.get('export_report', True)

            self.update_progress(0, 100, "开始处理商品数据")

            # 初始化管道
            pipeline = DataPipeline()

            # 获取待处理的原始商品数据
            raw_products = self._get_raw_products(batch_size, source_system)

            if not raw_products:
                self.update_progress(100, 100, "没有待处理的商品数据")
                return TaskResult(
                    success=True,
                    data={'message': '没有待处理的商品数据', 'processed_count': 0}
                )

            self.update_progress(10, 100, f"找到 {len(raw_products)} 条原始商品数据")

            # 处理数据
            result = pipeline.process_products(raw_products, processing_options)

            self.update_progress(70, 100, "数据处理完成，开始保存结果")

            # 保存处理结果
            saved_count = self._save_processed_products(result)

            # 保存处理报告
            if export_report:
                report_file = self._export_processing_report(result, 'products')
                logger.info(f"商品处理报告已导出: {report_file}")

            self.update_progress(100, 100, "商品数据处理完成")

            # 构建返回结果
            result_data = {
                'total_records': result.total_records,
                'processed_records': result.processed_records,
                'failed_records': result.failed_records,
                'saved_records': saved_count,
                'processing_time': result.processing_time,
                'quality_score': result.quality_report.overall_score if result.quality_report else None,
                'duplicate_groups': len(result.duplicate_groups),
                'versions_created': result.versions_created,
                'status': result.status.value
            }

            return TaskResult(
                success=result.status.value in ['completed', 'partial'],
                data=result_data
            )

        except Exception as e:
            logger.error(f"商品数据处理任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _get_raw_products(self, batch_size: int, source_system: str) -> List[Dict[str, Any]]:
        """获取待处理的原始商品数据"""
        try:
            with get_db_session() as session:
                product_repo = ProductRepository(session)

                # 获取待处理的商品（sync_status为pending或failed的商品）
                products = product_repo.get_pending_sync_products(limit=batch_size)

                # 转换为字典格式
                raw_products = []
                for product in products:
                    product_dict = product.to_dict()
                    # 添加原始数据标记
                    product_dict['_processing_source'] = source_system
                    raw_products.append(product_dict)

                return raw_products

        except Exception as e:
            logger.error(f"获取原始商品数据失败: {e}")
            raise

    def _save_processed_products(self, pipeline_result) -> int:
        """保存处理后的商品数据"""
        try:
            saved_count = 0

            with get_db_session() as session:
                product_repo = ProductRepository(session)

                # 这里应该根据管道结果更新数据库
                # 实际实现中，需要处理清洗后的数据、验证结果、去重结果等

                # 示例：更新处理状态
                for cleaning_result in pipeline_result.cleaning_results:
                    if cleaning_result['status'] == 'success':
                        source_id = cleaning_result.get('source_id')
                        if source_id:
                            # 更新商品状态
                            updated = product_repo.update_sync_status_by_source_id(
                                source_id, 'processed'
                            )
                            if updated:
                                saved_count += 1

                session.commit()

            logger.info(f"保存了 {saved_count} 条处理后的商品数据")
            return saved_count

        except Exception as e:
            logger.error(f"保存处理后的商品数据失败: {e}")
            raise

    def _export_processing_report(self, pipeline_result, entity_type: str) -> str:
        """导出处理报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"processing_report_{entity_type}_{timestamp}.json"
            filepath = f"/tmp/{filename}"

            pipeline_result.export_pipeline_report(filepath)
            return filepath

        except Exception as e:
            logger.error(f"导出处理报告失败: {e}")
            raise


@register_task('src.queue.tasks.data_processing.process_raw_suppliers')
class ProcessRawSuppliersTask(BaseTask):
    """处理原始供应商数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行供应商数据处理"""
        try:
            # 获取参数
            batch_size = kwargs.get('batch_size', 50)
            source_system = kwargs.get('source_system', '1688')
            processing_options = kwargs.get('options', {})
            export_report = kwargs.get('export_report', True)

            self.update_progress(0, 100, "开始处理供应商数据")

            # 初始化管道
            pipeline = DataPipeline()

            # 获取待处理的原始供应商数据
            raw_suppliers = self._get_raw_suppliers(batch_size, source_system)

            if not raw_suppliers:
                self.update_progress(100, 100, "没有待处理的供应商数据")
                return TaskResult(
                    success=True,
                    data={'message': '没有待处理的供应商数据', 'processed_count': 0}
                )

            self.update_progress(10, 100, f"找到 {len(raw_suppliers)} 条原始供应商数据")

            # 处理数据
            result = pipeline.process_suppliers(raw_suppliers, processing_options)

            self.update_progress(70, 100, "数据处理完成，开始保存结果")

            # 保存处理结果
            saved_count = self._save_processed_suppliers(result)

            # 保存处理报告
            if export_report:
                report_file = self._export_processing_report(result, 'suppliers')
                logger.info(f"供应商处理报告已导出: {report_file}")

            self.update_progress(100, 100, "供应商数据处理完成")

            # 构建返回结果
            result_data = {
                'total_records': result.total_records,
                'processed_records': result.processed_records,
                'failed_records': result.failed_records,
                'saved_records': saved_count,
                'processing_time': result.processing_time,
                'quality_score': result.quality_report.overall_score if result.quality_report else None,
                'duplicate_groups': len(result.duplicate_groups),
                'versions_created': result.versions_created,
                'status': result.status.value
            }

            return TaskResult(
                success=result.status.value in ['completed', 'partial'],
                data=result_data
            )

        except Exception as e:
            logger.error(f"供应商数据处理任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _get_raw_suppliers(self, batch_size: int, source_system: str) -> List[Dict[str, Any]]:
        """获取待处理的原始供应商数据"""
        try:
            with get_db_session() as session:
                supplier_repo = SupplierRepository(session)

                # 获取待处理的供应商
                suppliers = supplier_repo.get_pending_sync_suppliers(limit=batch_size)

                # 转换为字典格式
                raw_suppliers = []
                for supplier in suppliers:
                    supplier_dict = supplier.to_dict()
                    supplier_dict['_processing_source'] = source_system
                    raw_suppliers.append(supplier_dict)

                return raw_suppliers

        except Exception as e:
            logger.error(f"获取原始供应商数据失败: {e}")
            raise

    def _save_processed_suppliers(self, pipeline_result) -> int:
        """保存处理后的供应商数据"""
        try:
            saved_count = 0

            with get_db_session() as session:
                supplier_repo = SupplierRepository(session)

                # 更新供应商处理状态
                for cleaning_result in pipeline_result.cleaning_results:
                    if cleaning_result['status'] == 'success':
                        source_id = cleaning_result.get('source_id')
                        if source_id:
                            updated = supplier_repo.update_sync_status_by_source_id(
                                source_id, 'processed'
                            )
                            if updated:
                                saved_count += 1

                session.commit()

            logger.info(f"保存了 {saved_count} 条处理后的供应商数据")
            return saved_count

        except Exception as e:
            logger.error(f"保存处理后的供应商数据失败: {e}")
            raise

    def _export_processing_report(self, pipeline_result, entity_type: str) -> str:
        """导出处理报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"processing_report_{entity_type}_{timestamp}.json"
            filepath = f"/tmp/{filename}"

            pipeline_result.export_pipeline_report(filepath)
            return filepath

        except Exception as e:
            logger.error(f"导出处理报告失败: {e}")
            raise


@register_task('src.queue.tasks.data_processing.batch_clean_data')
class BatchCleanDataTask(BaseTask):
    """批量清洗数据任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行批量数据清洗"""
        try:
            entity_type = kwargs.get('entity_type', 'product')  # product or supplier
            batch_size = kwargs.get('batch_size', 200)
            dry_run = kwargs.get('dry_run', True)

            self.update_progress(0, 100, f"开始批量清洗{entity_type}数据")

            cleaner = DataCleaner()

            if entity_type == 'product':
                raw_data = self._get_products_for_cleaning(batch_size)
                clean_func = cleaner.clean_product_data
            else:
                raw_data = self._get_suppliers_for_cleaning(batch_size)
                clean_func = cleaner.clean_supplier_data

            if not raw_data:
                self.update_progress(100, 100, f"没有需要清洗的{entity_type}数据")
                return TaskResult(
                    success=True,
                    data={'message': f'没有需要清洗的{entity_type}数据', 'cleaned_count': 0}
                )

            self.update_progress(20, 100, f"找到 {len(raw_data)} 条待清洗数据")

            # 执行清洗
            cleaned_data = []
            failed_count = 0

            for i, record in enumerate(raw_data):
                try:
                    cleaned_record = clean_func(record)
                    cleaned_data.append(cleaned_record)

                    # 更新进度
                    progress = 20 + int((i + 1) / len(raw_data) * 60)
                    self.update_progress(progress, 100, f"已清洗 {i + 1}/{len(raw_data)} 条数据")

                except Exception as e:
                    logger.error(f"清洗记录失败 {record.get('source_id', 'unknown')}: {e}")
                    failed_count += 1

            self.update_progress(80, 100, "数据清洗完成")

            # 保存清洗结果（如果不是dry_run）
            saved_count = 0
            if not dry_run and cleaned_data:
                saved_count = self._save_cleaned_data(cleaned_data, entity_type)

            self.update_progress(100, 100, f"{entity_type}数据清洗完成")

            result_data = {
                'entity_type': entity_type,
                'total_records': len(raw_data),
                'cleaned_records': len(cleaned_data),
                'failed_records': failed_count,
                'saved_records': saved_count,
                'dry_run': dry_run
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"批量数据清洗任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _get_products_for_cleaning(self, batch_size: int) -> List[Dict[str, Any]]:
        """获取需要清洗的商品数据"""
        try:
            with get_db_session() as session:
                product_repo = ProductRepository(session)
                products = product_repo.get_products_needing_cleaning(limit=batch_size)
                return [product.to_dict() for product in products]
        except Exception as e:
            logger.error(f"获取待清洗商品数据失败: {e}")
            return []

    def _get_suppliers_for_cleaning(self, batch_size: int) -> List[Dict[str, Any]]:
        """获取需要清洗的供应商数据"""
        try:
            with get_db_session() as session:
                supplier_repo = SupplierRepository(session)
                suppliers = supplier_repo.get_suppliers_needing_cleaning(limit=batch_size)
                return [supplier.to_dict() for supplier in suppliers]
        except Exception as e:
            logger.error(f"获取待清洗供应商数据失败: {e}")
            return []

    def _save_cleaned_data(self, cleaned_data: List[Dict[str, Any]], entity_type: str) -> int:
        """保存清洗后的数据"""
        # 实际实现中需要根据具体的仓储层方法来实现
        # 这里只是示例
        logger.info(f"保存了 {len(cleaned_data)} 条清洗后的{entity_type}数据")
        return len(cleaned_data)


@register_task('src.queue.tasks.data_processing.quality_assessment')
class QualityAssessmentTask(BaseTask):
    """数据质量评估任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行数据质量评估"""
        try:
            entity_type = kwargs.get('entity_type', 'product')  # product or supplier
            sample_size = kwargs.get('sample_size', 1000)
            export_report = kwargs.get('export_report', True)

            self.update_progress(0, 100, f"开始评估{entity_type}数据质量")

            monitor = DataQualityMonitor()

            # 获取样本数据
            if entity_type == 'product':
                sample_data = self._get_product_sample(sample_size)
                assess_func = monitor.assess_product_quality
            else:
                sample_data = self._get_supplier_sample(sample_size)
                assess_func = monitor.assess_supplier_quality

            if not sample_data:
                self.update_progress(100, 100, f"没有{entity_type}数据可供评估")
                return TaskResult(
                    success=True,
                    data={'message': f'没有{entity_type}数据可供评估', 'sample_size': 0}
                )

            self.update_progress(20, 100, f"获取了 {len(sample_data)} 条样本数据")

            # 执行质量评估
            quality_report = assess_func(sample_data)

            self.update_progress(70, 100, "质量评估完成")

            # 导出报告
            report_file = None
            if export_report:
                report_file = self._export_quality_report(quality_report)

            # 更新质量指标到数据库
            self._update_quality_metrics(quality_report)

            self.update_progress(100, 100, f"{entity_type}数据质量评估完成")

            result_data = {
                'entity_type': entity_type,
                'sample_size': quality_report.sample_size,
                'overall_score': quality_report.overall_score,
                'quality_level': quality_report.quality_level.value,
                'metrics_count': len(quality_report.metrics),
                'issues_count': len(quality_report.issues),
                'recommendations_count': len(quality_report.recommendations),
                'report_file': report_file,
                'measured_at': quality_report.measured_at
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"数据质量评估任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _get_product_sample(self, sample_size: int) -> List[Dict[str, Any]]:
        """获取商品样本数据"""
        try:
            with get_db_session() as session:
                product_repo = ProductRepository(session)
                products = product_repo.get_sample_for_quality_assessment(limit=sample_size)
                return [product.to_dict() for product in products]
        except Exception as e:
            logger.error(f"获取商品样本数据失败: {e}")
            return []

    def _get_supplier_sample(self, sample_size: int) -> List[Dict[str, Any]]:
        """获取供应商样本数据"""
        try:
            with get_db_session() as session:
                supplier_repo = SupplierRepository(session)
                suppliers = supplier_repo.get_sample_for_quality_assessment(limit=sample_size)
                return [supplier.to_dict() for supplier in suppliers]
        except Exception as e:
            logger.error(f"获取供应商样本数据失败: {e}")
            return []

    def _export_quality_report(self, quality_report) -> str:
        """导出质量报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"quality_report_{quality_report.entity_type}_{timestamp}.json"
            filepath = f"/tmp/{filename}"

            quality_report.export_quality_report(filepath)
            logger.info(f"质量报告已导出: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出质量报告失败: {e}")
            return None

    def _update_quality_metrics(self, quality_report):
        """更新质量指标到数据库"""
        try:
            # 实际实现中需要将质量指标保存到数据库
            logger.info(f"更新{quality_report.entity_type}质量指标: {quality_report.overall_score:.2f}")
        except Exception as e:
            logger.error(f"更新质量指标失败: {e}")