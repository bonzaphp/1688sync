"""
同步记录数据访问层
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select

from src.models.sync_record import SyncRecord
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SyncRepository(BaseRepository[SyncRecord]):
    """同步记录仓储类"""

    def __init__(self, session):
        super().__init__(session, SyncRecord)

    async def get_by_task_id(self, task_id: str) -> Optional[SyncRecord]:
        """根据任务ID获取同步记录"""
        return await self.get_by_field('task_id', task_id)

    async def get_running_syncs(self) -> List[SyncRecord]:
        """获取正在运行的同步任务"""
        return await self.find_by_conditions({'status': 'running'})

    async def get_recent_syncs(self, limit: int = 10, sync_type: str = None) -> List[SyncRecord]:
        """获取最近的同步记录"""
        conditions = {}
        if sync_type:
            conditions['sync_type'] = sync_type
        return await self.find_by_conditions(
            conditions, limit=limit, order_by='start_time'
        )

    async def get_syncs_by_status(self, status: str, limit: int = 50) -> List[SyncRecord]:
        """根据状态获取同步记录"""
        return await self.find_by_conditions({'status': status}, limit=limit)

    async def get_failed_syncs(self, limit: int = 50) -> List[SyncRecord]:
        """获取失败的同步记录"""
        return await self.get_syncs_by_status('failed', limit)

    async def get_completed_syncs(self, limit: int = 50) -> List[SyncRecord]:
        """获取已完成的同步记录"""
        return await self.get_syncs_by_status('completed', limit)

    async def create_sync_record(
        self,
        task_id: str,
        operation_type: str,
        sync_type: str = 'product',
        task_name: str = None,
        **kwargs
    ) -> SyncRecord:
        """创建同步记录"""
        return await self.create(
            task_id=task_id,
            operation_type=operation_type,
            sync_type=sync_type,
            task_name=task_name,
            **kwargs
        )

    async def start_sync(self, task_id: str, total_count: int = 0) -> SyncRecord:
        """开始同步"""
        import time
        sync_record = await self.create(
            task_id=task_id,
            status='running',
            start_time=int(time.time()),
            total_count=total_count,
            processed_count=0,
            success_count=0,
            failed_count=0
        )
        return sync_record

    async def update_sync_progress(self, task_id: str, processed: int, success: int, failed: int) -> bool:
        """更新同步进度"""
        try:
            sync_record = await self.get_by_task_id(task_id)
            if not sync_record:
                return False

            sync_record.update_progress(processed, success, failed)
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"更新同步进度失败: {e}")
            return False

    async def complete_sync(self, task_id: str, status: str = 'completed', error_message: str = None) -> bool:
        """完成同步"""
        try:
            sync_record = await self.get_by_task_id(task_id)
            if not sync_record:
                return False

            sync_record.complete_execution(status)
            if error_message:
                sync_record.error_message = error_message

            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"完成同步失败: {e}")
            return False

    async def cancel_sync(self, task_id: str, reason: str = None) -> bool:
        """取消同步"""
        try:
            sync_record = await self.get_by_task_id(task_id)
            if not sync_record:
                return False

            sync_record.complete_execution('cancelled')
            if reason:
                sync_record.error_message = f"Cancelled: {reason}"

            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"取消同步失败: {e}")
            return False

    async def add_sync_error(self, task_id: str, error_message: str, error_details: dict = None) -> bool:
        """添加同步错误"""
        try:
            sync_record = await self.get_by_task_id(task_id)
            if not sync_record:
                return False

            sync_record.add_error(error_message, error_details)
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"添加同步错误失败: {e}")
            return False

    async def get_sync_statistics(self, days: int = 30) -> Dict:
        """获取同步统计信息"""
        try:
            import time
            cutoff_time = int(time.time()) - (days * 24 * 3600)

            # 总同步次数
            total_stmt = select(func.count(SyncRecord.id)).where(
                SyncRecord.start_time >= cutoff_time
            )
            total_result = await self.session.execute(total_stmt)
            total_count = total_result.scalar()

            # 按状态统计
            status_stmt = select(
                SyncRecord.status,
                func.count(SyncRecord.id).label('count')
            ).where(SyncRecord.start_time >= cutoff_time).group_by(SyncRecord.status)

            status_result = await self.session.execute(status_stmt)
            status_stats = [
                {'status': row.status, 'count': row.count}
                for row in status_result
            ]

            # 按同步类型统计
            type_stmt = select(
                SyncRecord.sync_type,
                func.count(SyncRecord.id).label('count')
            ).where(SyncRecord.start_time >= cutoff_time).group_by(SyncRecord.sync_type)

            type_result = await self.session.execute(type_stmt)
            type_stats = [
                {'sync_type': row.sync_type, 'count': row.count}
                for row in type_result
            ]

            # 按操作类型统计
            operation_stmt = select(
                SyncRecord.operation_type,
                func.count(SyncRecord.id).label('count')
            ).where(SyncRecord.start_time >= cutoff_time).group_by(SyncRecord.operation_type)

            operation_result = await self.session.execute(operation_stmt)
            operation_stats = [
                {'operation_type': row.operation_type, 'count': row.count}
                for row in operation_result
            ]

            # 性能统计
            perf_stmt = select(
                func.avg(SyncRecord.duration).label('avg_duration'),
                func.max(SyncRecord.duration).label('max_duration'),
                func.min(SyncRecord.duration).label('min_duration'),
                func.sum(SyncRecord.total_count).label('total_records'),
                func.sum(SyncRecord.success_count).label('total_success'),
                func.sum(SyncRecord.failed_count).label('total_failed')
            ).where(
                and_(
                    SyncRecord.start_time >= cutoff_time,
                    SyncRecord.status.in_(['completed', 'failed']),
                    SyncRecord.duration.isnot(None)
                )
            )

            perf_result = await self.session.execute(perf_stmt)
            perf_stats = perf_result.first()

            # 计算成功率
            total_processed = (perf_stats.total_success or 0) + (perf_stats.total_failed or 0)
            success_rate = (
                (perf_stats.total_success / total_processed * 100) if total_processed > 0 else 0
            )

            return {
                'period_days': days,
                'total_syncs': total_count,
                'status_distribution': status_stats,
                'sync_type_distribution': type_stats,
                'operation_type_distribution': operation_stats,
                'performance_statistics': {
                    'avg_duration_seconds': float(perf_stats.avg_duration) if perf_stats.avg_duration else 0,
                    'max_duration_seconds': int(perf_stats.max_duration) if perf_stats.max_duration else 0,
                    'min_duration_seconds': int(perf_stats.min_duration) if perf_stats.min_duration else 0,
                    'total_records_processed': int(perf_stats.total_records) if perf_stats.total_records else 0,
                    'total_successful_records': int(perf_stats.total_success) if perf_stats.total_success else 0,
                    'total_failed_records': int(perf_stats.total_failed) if perf_stats.total_failed else 0,
                    'overall_success_rate': round(success_rate, 2),
                }
            }

        except Exception as e:
            logger.error(f"获取同步统计失败: {e}")
            raise

    async def get_daily_sync_summary(self, days: int = 7) -> List[Dict]:
        """获取每日同步汇总"""
        try:
            import time
            summaries = []

            for i in range(days):
                day_start = int(time.time()) - ((i + 1) * 24 * 3600)
                day_end = day_start + 24 * 3600

                # 当日统计
                day_stmt = select(
                    func.count(SyncRecord.id).label('total'),
                    func.sum(SyncRecord.total_count).label('records'),
                    func.sum(SyncRecord.success_count).label('success'),
                    func.sum(SyncRecord.failed_count).label('failed')
                ).where(
                    and_(
                        SyncRecord.start_time >= day_start,
                        SyncRecord.start_time < day_end
                    )
                )

                day_result = await self.session.execute(day_stmt)
                day_stats = day_result.first()

                # 计算成功率
                total_processed = (day_stats.success or 0) + (day_stats.failed or 0)
                success_rate = (
                    (day_stats.success / total_processed * 100) if total_processed > 0 else 0
                )

                summaries.append({
                    'date': time.strftime('%Y-%m-%d', time.localtime(day_start)),
                    'total_syncs': int(day_stats.total) if day_stats.total else 0,
                    'total_records': int(day_stats.records) if day_stats.records else 0,
                    'successful_records': int(day_stats.success) if day_stats.success else 0,
                    'failed_records': int(day_stats.failed) if day_stats.failed else 0,
                    'success_rate': round(success_rate, 2),
                })

            return list(reversed(summaries))  # 按时间正序排列

        except Exception as e:
            logger.error(f"获取每日同步汇总失败: {e}")
            raise

    async def get_long_running_syncs(self, hours: int = 2) -> List[SyncRecord]:
        """获取长时间运行的同步任务"""
        try:
            import time
            cutoff_time = int(time.time()) - (hours * 3600)

            return await self.find_by_conditions({
                'status': 'running',
                'start_time': {'lt': cutoff_time}
            })

        except Exception as e:
            logger.error(f"获取长时间运行同步任务失败: {e}")
            raise

    async def cleanup_old_records(self, days: int = 90) -> int:
        """清理旧的同步记录"""
        try:
            import time
            cutoff_time = int(time.time()) - (days * 24 * 3600)

            from sqlalchemy import delete
            stmt = delete(SyncRecord).where(SyncRecord.start_time < cutoff_time)

            result = await self.session.execute(stmt)
            deleted_count = result.rowcount

            logger.info(f"清理旧同步记录完成: {deleted_count} 条记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理旧同步记录失败: {e}")
            raise

    async def get_sync_performance_metrics(self, task_id: str) -> Optional[Dict]:
        """获取同步性能指标"""
        try:
            sync_record = await self.get_by_task_id(task_id)
            if not sync_record:
                return None

            return {
                'task_id': sync_record.task_id,
                'status': sync_record.status,
                'start_time': sync_record.start_time,
                'end_time': sync_record.end_time,
                'duration_seconds': sync_record.duration,
                'total_records': sync_record.total_count,
                'processed_records': sync_record.processed_count,
                'successful_records': sync_record.success_count,
                'failed_records': sync_record.failed_count,
                'success_rate': sync_record.success_rate,
                'failure_rate': sync_record.failure_rate,
                'records_per_second': sync_record.records_per_second,
                'progress_percentage': sync_record.progress,
                'estimated_remaining_time': sync_record.estimated_remaining_time if sync_record.is_running else 0,
            }

        except Exception as e:
            logger.error(f"获取同步性能指标失败: {e}")
            raise