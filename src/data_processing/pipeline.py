"""
数据处理管道集成模块
"""
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .cleaner import DataCleaner
from .validator import DataValidator, ValidationResult, ValidationLevel
from .deduplicator import DataDeduplicator, DuplicateGroup
from .version_manager import VersionManager, ChangeType
from .quality_monitor import DataQualityMonitor, QualityReport

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """管道状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class PipelineResult:
    """管道处理结果"""
    status: PipelineStatus
    entity_type: str
    total_records: int
    processed_records: int
    failed_records: int
    cleaning_results: List[Dict[str, Any]]
    validation_results: List[List[ValidationResult]]
    duplicate_groups: List[DuplicateGroup]
    quality_report: Optional[QualityReport]
    versions_created: int
    errors: List[str]
    warnings: List[str]
    processing_time: float
    started_at: str
    completed_at: str


class DataPipeline:
    """数据处理管道"""

    def __init__(self):
        """初始化数据处理管道"""
        self.cleaner = DataCleaner()
        self.validator = DataValidator()
        self.deduplicator = DataDeduplicator()
        self.version_manager = VersionManager()
        self.quality_monitor = DataQualityMonitor()

    def process_products(self, raw_products: List[Dict[str, Any]],
                        options: Dict[str, Any] = None) -> PipelineResult:
        """处理商品数据"""
        return self._process_data('product', raw_products, options or {})

    def process_suppliers(self, raw_suppliers: List[Dict[str, Any]],
                          options: Dict[str, Any] = None) -> PipelineResult:
        """处理供应商数据"""
        return self._process_data('supplier', raw_suppliers, options or {})

    def _process_data(self, entity_type: str, raw_data: List[Dict[str, Any]],
                      options: Dict[str, Any]) -> PipelineResult:
        """处理数据的通用方法"""
        start_time = datetime.now()
        started_at = start_time.isoformat()

        logger.info(f"开始处理 {entity_type} 数据，共 {len(raw_data)} 条记录")

        # 初始化结果
        result = PipelineResult(
            status=PipelineStatus.RUNNING,
            entity_type=entity_type,
            total_records=len(raw_data),
            processed_records=0,
            failed_records=0,
            cleaning_results=[],
            validation_results=[],
            duplicate_groups=[],
            quality_report=None,
            versions_created=0,
            errors=[],
            warnings=[],
            processing_time=0.0,
            started_at=started_at,
            completed_at=""
        )

        try:
            # 步骤1: 数据清洗
            if not options.get('skip_cleaning', False):
                cleaned_data, cleaning_results = self._clean_data(raw_data, entity_type)
                result.cleaning_results = cleaning_results
            else:
                cleaned_data = raw_data

            # 步骤2: 数据验证
            if not options.get('skip_validation', False):
                validated_data, validation_results = self._validate_data(cleaned_data, entity_type)
                result.validation_results = validation_results

                # 过滤出验证通过的数据
                valid_indices = [
                    i for i, results in enumerate(validation_results)
                    if not any(r.level == ValidationLevel.ERROR for r in results)
                ]
                validated_data = [cleaned_data[i] for i in valid_indices]

                # 记录验证失败的记录
                result.failed_records += len(cleaned_data) - len(valid_indices)
            else:
                validated_data = cleaned_data

            # 步骤3: 去重处理
            if not options.get('skip_deduplication', False):
                deduplicated_data, duplicate_groups = self._deduplicate_data(validated_data, entity_type)
                result.duplicate_groups = duplicate_groups
            else:
                deduplicated_data = validated_data

            # 步骤4: 版本管理
            if not options.get('skip_versioning', False):
                versions_created = self._create_versions(deduplicated_data, entity_type)
                result.versions_created = versions_created

            # 步骤5: 质量监控
            if not options.get('skip_quality_monitoring', False):
                quality_report = self._assess_quality(deduplicated_data, entity_type)
                result.quality_report = quality_report

                # 根据质量报告添加警告
                if quality_report.quality_level.value in ['poor', 'critical']:
                    result.warnings.append(
                        f"数据质量{quality_report.quality_level.value}，评分: {quality_report.overall_score:.2f}"
                    )

            # 更新处理结果
            result.processed_records = len(deduplicated_data)
            result.status = PipelineStatus.COMPLETED if result.failed_records == 0 else PipelineStatus.PARTIAL

            logger.info(f"{entity_type} 数据处理完成: 成功 {result.processed_records}，失败 {result.failed_records}")

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.errors.append(f"管道处理异常: {str(e)}")
            logger.error(f"{entity_type} 数据处理失败: {e}")

        finally:
            # 计算处理时间
            end_time = datetime.now()
            result.processing_time = (end_time - start_time).total_seconds()
            result.completed_at = end_time.isoformat()

        return result

    def _clean_data(self, raw_data: List[Dict[str, Any]], entity_type: str) -> tuple:
        """清洗数据"""
        logger.info(f"开始清洗 {entity_type} 数据")
        cleaned_data = []
        cleaning_results = []

        for i, record in enumerate(raw_data):
            try:
                if entity_type == 'product':
                    cleaned_record = self.cleaner.clean_product_data(record)
                else:  # supplier
                    cleaned_record = self.cleaner.clean_supplier_data(record)

                cleaned_data.append(cleaned_record)
                cleaning_results.append({
                    'index': i,
                    'status': 'success',
                    'source_id': record.get('source_id'),
                    'message': '清洗成功'
                })

            except Exception as e:
                logger.error(f"清洗记录 {i} 失败: {e}")
                cleaning_results.append({
                    'index': i,
                    'status': 'failed',
                    'source_id': record.get('source_id'),
                    'error': str(e)
                })

        success_count = sum(1 for r in cleaning_results if r['status'] == 'success')
        logger.info(f"数据清洗完成: 成功 {success_count}/{len(raw_data)}")

        return cleaned_data, cleaning_results

    def _validate_data(self, data: List[Dict[str, Any]], entity_type: str) -> tuple:
        """验证数据"""
        logger.info(f"开始验证 {entity_type} 数据")
        validation_results = []

        for record in data:
            if entity_type == 'product':
                results = self.validator.validate_product_data(record)
            else:  # supplier
                results = self.validator.validate_supplier_data(record)

            validation_results.append(results)

        # 统计验证结果
        total_errors = sum(
            sum(1 for r in results if r.level == ValidationLevel.ERROR)
            for results in validation_results
        )
        total_warnings = sum(
            sum(1 for r in results if r.level == ValidationLevel.WARNING)
            for results in validation_results
        )

        logger.info(f"数据验证完成: 错误 {total_errors}，警告 {total_warnings}")

        return data, validation_results

    def _deduplicate_data(self, data: List[Dict[str, Any]], entity_type: str) -> tuple:
        """去重处理"""
        logger.info(f"开始去重 {entity_type} 数据")

        if entity_type == 'product':
            duplicate_groups = self.deduplicator.find_duplicate_products(data)
        else:  # supplier
            duplicate_groups = self.deduplicator.find_duplicate_suppliers(data)

        # 根据选项决定是否自动移除重复项
        deduplicated_data = data.copy()
        if duplicate_groups:
            # 标记重复项（实际项目中可能需要移动到单独表中）
            for group in duplicate_groups:
                master_record = group.master_record
                if master_record:
                    logger.debug(f"重复组 {group.group_id}，主记录ID: {master_record.get('id')}")

        logger.info(f"去重完成: 发现 {len(duplicate_groups)} 组重复数据")

        return deduplicated_data, duplicate_groups

    def _create_versions(self, data: List[Dict[str, Any]], entity_type: str) -> int:
        """创建版本记录"""
        logger.info(f"开始创建 {entity_type} 版本记录")
        versions_created = 0

        for record in data:
            try:
                # 检查是否已存在版本
                existing_version = self.version_manager.get_current_version(
                    entity_type, record.get('source_id', '')
                )

                if existing_version:
                    # 更新版本
                    change_type = ChangeType.UPDATE
                    previous_data = existing_version.data
                else:
                    # 新建版本
                    change_type = ChangeType.CREATE
                    previous_data = None

                # 创建新版本
                version = self.version_manager.create_version(
                    entity_type=entity_type,
                    entity_id=record.get('source_id', ''),
                    data=record,
                    change_type=change_type,
                    previous_data=previous_data,
                    created_by='data_pipeline'
                )

                versions_created += 1

            except Exception as e:
                logger.error(f"创建版本失败: {e}")

        logger.info(f"版本创建完成: {versions_created} 个版本")

        return versions_created

    def _assess_quality(self, data: List[Dict[str, Any]], entity_type: str) -> QualityReport:
        """评估数据质量"""
        logger.info(f"开始评估 {entity_type} 数据质量")

        if entity_type == 'product':
            quality_report = self.quality_monitor.assess_product_quality(data)
        else:  # supplier
            quality_report = self.quality_monitor.assess_supplier_quality(data)

        logger.info(f"质量评估完成: {quality_report.quality_level.value} ({quality_report.overall_score:.2f})")

        return quality_report

    def get_pipeline_summary(self, result: PipelineResult) -> Dict[str, Any]:
        """获取管道处理摘要"""
        summary = {
            'entity_type': result.entity_type,
            'status': result.status.value,
            'processing_time': result.processing_time,
            'record_summary': {
                'total': result.total_records,
                'processed': result.processed_records,
                'failed': result.failed_records,
                'success_rate': result.processed_records / result.total_records if result.total_records > 0 else 0
            },
            'quality_summary': None,
            'duplicate_summary': None,
            'issues': {
                'errors': result.errors,
                'warnings': result.warnings
            }
        }

        # 质量摘要
        if result.quality_report:
            summary['quality_summary'] = {
                'overall_score': result.quality_report.overall_score,
                'quality_level': result.quality_report.quality_level.value,
                'metrics_count': len(result.quality_report.metrics),
                'issues_count': len(result.quality_report.issues)
            }

        # 去重摘要
        if result.duplicate_groups:
            duplicate_stats = self.deduplicator.get_deduplication_statistics(result.duplicate_groups)
            summary['duplicate_summary'] = {
                'groups_found': len(result.duplicate_groups),
                'duplicate_records': duplicate_stats['duplicate_records'],
                'duplicate_ratio': duplicate_stats['duplicate_ratio']
            }

        return summary

    def export_pipeline_report(self, result: PipelineResult, output_file: str = None) -> str:
        """导出管道处理报告"""
        try:
            import json

            report = {
                'pipeline_info': {
                    'entity_type': result.entity_type,
                    'status': result.status.value,
                    'started_at': result.started_at,
                    'completed_at': result.completed_at,
                    'processing_time': result.processing_time
                },
                'processing_summary': self.get_pipeline_summary(result),
                'detailed_results': {
                    'cleaning_results': result.cleaning_results,
                    'validation_summary': self._summarize_validation_results(result.validation_results),
                    'duplicate_groups_summary': [
                        {
                            'group_id': group.group_id,
                            'similarity_score': group.similarity_score,
                            'record_count': len(group.records)
                        }
                        for group in result.duplicate_groups
                    ],
                    'versions_created': result.versions_created
                },
                'quality_report': None,
                'errors': result.errors,
                'warnings': result.warnings
            }

            # 添加质量报告
            if result.quality_report:
                from .quality_monitor import QualityMetric
                quality_data = {
                    'entity_type': result.quality_report.entity_type,
                    'overall_score': result.quality_report.overall_score,
                    'quality_level': result.quality_report.quality_level.value,
                    'metrics': [
                        {
                            'name': metric.name,
                            'value': metric.value,
                            'status': metric.status.value,
                            'description': metric.description
                        }
                        for metric in result.quality_report.metrics
                    ],
                    'issues': result.quality_report.issues,
                    'recommendations': result.quality_report.recommendations
                }
                report['quality_report'] = quality_data

            report_content = json.dumps(report, ensure_ascii=False, indent=2)

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                logger.info(f"管道处理报告已导出到: {output_file}")

            return report_content

        except Exception as e:
            logger.error(f"导出管道处理报告失败: {e}")
            raise

    def _summarize_validation_results(self, validation_results: List[List[ValidationResult]]) -> Dict[str, Any]:
        """汇总验证结果"""
        if not validation_results:
            return {'total_records': 0, 'validation_summary': {}}

        total_errors = 0
        total_warnings = 0
        total_info = 0
        field_issues = {}

        for results in validation_results:
            for result in results:
                if result.level == ValidationLevel.ERROR:
                    total_errors += 1
                elif result.level == ValidationLevel.WARNING:
                    total_warnings += 1
                elif result.level == ValidationLevel.INFO:
                    total_info += 1

                # 统计字段问题
                field = result.field
                if field not in field_issues:
                    field_issues[field] = {'errors': 0, 'warnings': 0, 'info': 0}

                if result.level == ValidationLevel.ERROR:
                    field_issues[field]['errors'] += 1
                elif result.level == ValidationLevel.WARNING:
                    field_issues[field]['warnings'] += 1
                else:
                    field_issues[field]['info'] += 1

        return {
            'total_records': len(validation_results),
            'validation_summary': {
                'total_errors': total_errors,
                'total_warnings': total_warnings,
                'total_info': total_info,
                'valid_records': len([
                    results for results in validation_results
                    if not any(r.level == ValidationLevel.ERROR for r in results)
                ]),
                'field_issues': field_issues
            }
        }

    def cleanup_resources(self, days_old: int = 30) -> Dict[str, int]:
        """清理资源"""
        try:
            logger.info("开始清理数据处理资源")

            # 清理旧版本
            versions_cleaned = self.version_manager.cleanup_old_versions(days_old=days_old)

            logger.info(f"资源清理完成: 版本 {versions_cleaned}")

            return {
                'versions_cleaned': versions_cleaned
            }

        except Exception as e:
            logger.error(f"清理资源失败: {e}")
            raise

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 版本管理统计
            version_stats = self.version_manager.get_version_statistics()

            status = {
                'components': {
                    'data_cleaner': 'active',
                    'data_validator': 'active',
                    'data_deduplicator': 'active',
                    'version_manager': 'active',
                    'quality_monitor': 'active'
                },
                'version_statistics': version_stats,
                'last_updated': datetime.now().isoformat()
            }

            return status

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            raise