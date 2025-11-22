# Batch Processing Tasks
# 批量处理相关任务

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BaseTask, TaskResult, register_task
from ..database.connection import get_db_session
from ..models.sync_record import SyncRecord
from ..services.product_repository import ProductRepository
from ..services.supplier_repository import SupplierRepository

logger = logging.getLogger(__name__)


@register_task('src.queue.tasks.batch_processing.batch_import')
class BatchImportTask(BaseTask):
    """批量导入任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'items' not in kwargs:
            raise ValueError("缺少必需参数: items")
        if 'item_type' not in kwargs:
            raise ValueError("缺少必需参数: item_type")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行批量导入任务"""
        try:
            items = kwargs.get('items', [])
            item_type = kwargs.get('item_type')  # products, suppliers
            batch_size = kwargs.get('batch_size', 50)
            parallel_workers = kwargs.get('parallel_workers', 4)
            validate_before_import = kwargs.get('validate', True)
            update_existing = kwargs.get('update_existing', False)

            total_items = len(items)
            imported_count = 0
            failed_count = 0
            validation_errors = []

            self.update_progress(0, total_items, "开始批量导入")

            # 创建导入记录
            import_record = self._create_import_record(item_type, total_items)

            # 验证数据（如果需要）
            if validate_before_import:
                self.update_progress(5, total_items, "验证导入数据")
                validation_result = self._validate_items(items, item_type)
                if not validation_result['valid']:
                    return TaskResult(
                        success=False,
                        error=f"数据验证失败: {validation_result['errors']}"
                    )

            # 分批并行处理
            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                futures = []

                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    future = executor.submit(
                        self._process_import_batch,
                        batch,
                        item_type,
                        update_existing,
                        i // batch_size
                    )
                    futures.append(future)

                # 收集结果
                for future in as_completed(futures):
                    try:
                        batch_result = future.result()
                        imported_count += batch_result['imported']
                        failed_count += batch_result['failed']
                        validation_errors.extend(batch_result['errors'])

                        # 更新进度
                        current_progress = imported_count + failed_count
                        self.update_progress(
                            current_progress,
                            total_items,
                            f"已导入 {imported_count} 项，失败 {failed_count} 项"
                        )

                    except Exception as e:
                        logger.error(f"批次处理失败: {e}")
                        failed_count += batch_size

            # 更新导入记录
            self._update_import_record(
                import_record.id,
                'completed',
                {
                    'total_items': total_items,
                    'imported_count': imported_count,
                    'failed_count': failed_count,
                    'validation_errors': validation_errors[:10]
                }
            )

            result_data = {
                'import_record_id': import_record.id,
                'total_items': total_items,
                'imported_count': imported_count,
                'failed_count': failed_count,
                'success_rate': imported_count / total_items if total_items > 0 else 0,
                'validation_errors': validation_errors
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"批量导入任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _create_import_record(self, item_type: str, total_items: int) -> SyncRecord:
        """创建导入记录"""
        with get_db_session() as session:
            import_record = SyncRecord(
                entity_type=f"{item_type}_import",
                source_system='batch_import',
                sync_type='full',
                status='running',
                started_at=datetime.utcnow(),
                result_data=json.dumps({'total_items': total_items})
            )
            session.add(import_record)
            session.commit()
            session.refresh(import_record)
            return import_record

    def _update_import_record(self, record_id: int, status: str, result_data: Dict[str, Any]):
        """更新导入记录"""
        with get_db_session() as session:
            import_record = session.query(SyncRecord).filter_by(id=record_id).first()
            if import_record:
                import_record.status = status
                import_record.result_data = json.dumps(result_data)
                import_record.completed_at = datetime.utcnow()
                import_record.updated_at = datetime.utcnow()
                session.commit()

    def _validate_items(self, items: List[Dict[str, Any]], item_type: str) -> Dict[str, Any]:
        """验证导入数据"""
        errors = []
        required_fields = {
            'products': ['title', 'price'],
            'suppliers': ['name', 'contact_info']
        }

        for i, item in enumerate(items):
            if item_type in required_fields:
                for field in required_fields[item_type]:
                    if field not in item or not item[field]:
                        errors.append(f"第 {i+1} 项缺少必需字段: {field}")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _process_import_batch(
        self, batch: List[Dict[str, Any]], item_type: str, update_existing: bool, batch_index: int
    ) -> Dict[str, Any]:
        """处理单个批次"""
        imported = 0
        failed = 0
        errors = []

        try:
            if item_type == 'products':
                repo = ProductRepository()
                for item in batch:
                    try:
                        if update_existing:
                            # 检查是否已存在
                            existing = repo.get_by_source_url(item.get('source_url'))
                            if existing:
                                repo.update(existing.id, item)
                            else:
                                repo.create(item)
                        else:
                            repo.create(item)
                        imported += 1
                    except Exception as e:
                        failed += 1
                        errors.append(f"产品导入失败: {str(e)}")

            elif item_type == 'suppliers':
                repo = SupplierRepository()
                for item in batch:
                    try:
                        if update_existing:
                            # 根据名称查找已存在的供应商
                            existing = repo.get_by_name(item.get('name'))
                            if existing:
                                repo.update(existing.id, item)
                            else:
                                repo.create(item)
                        else:
                            repo.create(item)
                        imported += 1
                    except Exception as e:
                        failed += 1
                        errors.append(f"供应商导入失败: {str(e)}")

        except Exception as e:
            logger.error(f"批次 {batch_index} 处理失败: {e}")
            failed += len(batch)

        return {
            'imported': imported,
            'failed': failed,
            'errors': errors
        }


@register_task('src.queue.tasks.batch_processing.batch_export')
class BatchExportTask(BaseTask):
    """批量导出任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'export_type' not in kwargs:
            raise ValueError("缺少必需参数: export_type")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行批量导出任务"""
        try:
            export_type = kwargs.get('export_type')  # products, suppliers
            export_format = kwargs.get('format', 'json')  # json, csv, xlsx
            filters = kwargs.get('filters', {})
            batch_size = kwargs.get('batch_size', 1000)
            output_path = kwargs.get('output_path')

            self.update_progress(0, 100, "开始批量导出")

            # 创建导出记录
            export_record = self._create_export_record(export_type, export_format)

            # 获取数据
            self.update_progress(10, 100, "获取导出数据")
            if export_type == 'products':
                repo = ProductRepository()
                items = repo.get_all_for_export(batch_size=batch_size, **filters)
            elif export_type == 'suppliers':
                repo = SupplierRepository()
                items = repo.get_all_for_export(batch_size=batch_size, **filters)
            else:
                raise ValueError(f"不支持的导出类型: {export_type}")

            total_items = len(items)
            self.update_progress(30, 100, f"找到 {total_items} 项数据")

            # 导出数据
            self.update_progress(50, 100, "导出数据")
            export_file_path = self._export_data(items, export_format, output_path, export_type)

            self.update_progress(100, 100, "批量导出完成")

            # 更新导出记录
            self._update_export_record(
                export_record.id,
                'completed',
                {
                    'total_items': total_items,
                    'export_format': export_format,
                    'file_path': export_file_path
                }
            )

            result_data = {
                'export_record_id': export_record.id,
                'total_items': total_items,
                'export_format': export_format,
                'file_path': export_file_path
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"批量导出任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _create_export_record(self, export_type: str, export_format: str) -> SyncRecord:
        """创建导出记录"""
        with get_db_session() as session:
            export_record = SyncRecord(
                entity_type=f"{export_type}_export",
                source_system='batch_export',
                sync_type='export',
                status='running',
                started_at=datetime.utcnow(),
                result_data=json.dumps({'export_format': export_format})
            )
            session.add(export_record)
            session.commit()
            session.refresh(export_record)
            return export_record

    def _update_export_record(self, record_id: int, status: str, result_data: Dict[str, Any]):
        """更新导出记录"""
        with get_db_session() as session:
            export_record = session.query(SyncRecord).filter_by(id=record_id).first()
            if export_record:
                export_record.status = status
                export_record.result_data = json.dumps(result_data)
                export_record.completed_at = datetime.utcnow()
                export_record.updated_at = datetime.utcnow()
                session.commit()

    def _export_data(
        self, items: List[Any], export_format: str, output_path: Optional[str], export_type: str
    ) -> str:
        """导出数据到文件"""
        import os
        import csv
        import json
        from datetime import datetime

        # 生成文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if output_path:
            filename = output_path
        else:
            filename = f"exports/{export_type}_export_{timestamp}.{export_format}"

        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if export_format == 'json':
            # 转换为字典格式
            data = []
            for item in items:
                if hasattr(item, 'to_dict'):
                    data.append(item.to_dict())
                else:
                    data.append(item.__dict__)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        elif export_format == 'csv':
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if items:
                    # 获取字段名
                    if hasattr(items[0], 'to_dict'):
                        fieldnames = items[0].to_dict().keys()
                    else:
                        fieldnames = items[0].__dict__.keys()

                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in items:
                        if hasattr(item, 'to_dict'):
                            writer.writerow(item.to_dict())
                        else:
                            writer.writerow(item.__dict__)

        elif export_format == 'xlsx':
            try:
                import pandas as pd

                # 转换为DataFrame
                data = []
                for item in items:
                    if hasattr(item, 'to_dict'):
                        data.append(item.to_dict())
                    else:
                        data.append(item.__dict__)

                df = pd.DataFrame(data)
                df.to_excel(filename, index=False)

            except ImportError:
                raise ValueError("导出Excel格式需要安装pandas库")

        else:
            raise ValueError(f"不支持的导出格式: {export_format}")

        return filename


@register_task('src.queue.tasks.batch_processing.batch_update')
class BatchUpdateTask(BaseTask):
    """批量更新任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'updates' not in kwargs:
            raise ValueError("缺少必需参数: updates")
        if 'entity_type' not in kwargs:
            raise ValueError("缺少必需参数: entity_type")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行批量更新任务"""
        try:
            updates = kwargs.get('updates', [])  # [{'id': 1, 'data': {...}}, ...]
            entity_type = kwargs.get('entity_type')  # products, suppliers
            batch_size = kwargs.get('batch_size', 50)
            validate_updates = kwargs.get('validate', True)

            total_updates = len(updates)
            updated_count = 0
            failed_count = 0
            errors = []

            self.update_progress(0, total_updates, "开始批量更新")

            # 验证更新数据
            if validate_updates:
                self.update_progress(5, total_updates, "验证更新数据")
                validation_result = self._validate_updates(updates)
                if not validation_result['valid']:
                    return TaskResult(
                        success=False,
                        error=f"更新数据验证失败: {validation_result['errors']}"
                    )

            # 分批处理更新
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]

                for update in batch:
                    try:
                        entity_id = update['id']
                        data = update['data']

                        if entity_type == 'products':
                            repo = ProductRepository()
                            repo.update(entity_id, data)
                        elif entity_type == 'suppliers':
                            repo = SupplierRepository()
                            repo.update(entity_id, data)
                        else:
                            raise ValueError(f"不支持的实体类型: {entity_type}")

                        updated_count += 1

                    except Exception as e:
                        failed_count += 1
                        errors.append(f"更新失败 ID {update['id']}: {str(e)}")

                    # 更新进度
                    current_progress = updated_count + failed_count
                    self.update_progress(
                        current_progress,
                        total_updates,
                        f"已更新 {updated_count} 项，失败 {failed_count} 项"
                    )

            result_data = {
                'total_updates': total_updates,
                'updated_count': updated_count,
                'failed_count': failed_count,
                'success_rate': updated_count / total_updates if total_updates > 0 else 0,
                'errors': errors[:10]
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"批量更新任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )

    def _validate_updates(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证更新数据"""
        errors = []

        for i, update in enumerate(updates):
            if 'id' not in update:
                errors.append(f"第 {i+1} 项缺少ID")
            if 'data' not in update or not update['data']:
                errors.append(f"第 {i+1} 项缺少更新数据")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


@register_task('src.queue.tasks.batch_processing.batch_delete')
class BatchDeleteTask(BaseTask):
    """批量删除任务"""

    def validate_inputs(self, *args, **kwargs) -> bool:
        """验证输入参数"""
        if 'entity_ids' not in kwargs:
            raise ValueError("缺少必需参数: entity_ids")
        if 'entity_type' not in kwargs:
            raise ValueError("缺少必需参数: entity_type")
        return True

    def execute(self, *args, **kwargs) -> TaskResult:
        """执行批量删除任务"""
        try:
            entity_ids = kwargs.get('entity_ids', [])
            entity_type = kwargs.get('entity_type')  # products, suppliers
            batch_size = kwargs.get('batch_size', 50)
            soft_delete = kwargs.get('soft_delete', True)
            confirm_deletion = kwargs.get('confirm', False)

            if not confirm_deletion:
                return TaskResult(
                    success=False,
                    error="批量删除需要确认参数 confirm=True"
                )

            total_entities = len(entity_ids)
            deleted_count = 0
            failed_count = 0
            errors = []

            self.update_progress(0, total_entities, "开始批量删除")

            # 分批处理删除
            for i in range(0, len(entity_ids), batch_size):
                batch = entity_ids[i:i + batch_size]

                for entity_id in batch:
                    try:
                        if entity_type == 'products':
                            repo = ProductRepository()
                            if soft_delete:
                                repo.soft_delete(entity_id)
                            else:
                                repo.delete(entity_id)
                        elif entity_type == 'suppliers':
                            repo = SupplierRepository()
                            if soft_delete:
                                repo.soft_delete(entity_id)
                            else:
                                repo.delete(entity_id)
                        else:
                            raise ValueError(f"不支持的实体类型: {entity_type}")

                        deleted_count += 1

                    except Exception as e:
                        failed_count += 1
                        errors.append(f"删除失败 ID {entity_id}: {str(e)}")

                    # 更新进度
                    current_progress = deleted_count + failed_count
                    self.update_progress(
                        current_progress,
                        total_entities,
                        f"已删除 {deleted_count} 项，失败 {failed_count} 项"
                    )

            result_data = {
                'total_entities': total_entities,
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'success_rate': deleted_count / total_entities if total_entities > 0 else 0,
                'errors': errors[:10]
            }

            return TaskResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"批量删除任务失败: {e}")
            return TaskResult(
                success=False,
                error=str(e)
            )