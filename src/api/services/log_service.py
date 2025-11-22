"""
日志服务层
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from datetime import datetime, timedelta
import logging

from ...database.models import SyncLog
from ..schemas.log import LogLevel, LogStats

logger = logging.getLogger(__name__)


class LogService:
    """日志服务类"""

    def __init__(self, db: Session):
        self.db = db

    async def get_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[SyncLog], int]:
        """获取日志列表"""
        query = self.db.query(SyncLog)

        # 应用过滤条件
        if filters:
            if "level" in filters:
                query = query.filter(SyncLog.level == filters["level"])
            if "task_id" in filters:
                query = query.filter(SyncLog.task_id == filters["task_id"])
            if "product_id" in filters:
                query = query.filter(SyncLog.product_id == filters["product_id"])
            if "start_time" in filters:
                query = query.filter(SyncLog.created_at >= filters["start_time"])
            if "end_time" in filters:
                query = query.filter(SyncLog.created_at <= filters["end_time"])
            if "search" in filters and filters["search"]:
                search_term = f"%{filters['search']}%"
                query = query.filter(SyncLog.message.ilike(search_term))

        # 获取总数
        total = query.count()

        # 应用分页和排序
        logs = query.order_by(desc(SyncLog.created_at)).offset(skip).limit(limit).all()

        return logs, total

    async def get_log_by_id(self, log_id: int) -> Optional[SyncLog]:
        """根据ID获取日志"""
        return self.db.query(SyncLog).filter(SyncLog.id == log_id).first()

    async def get_log_stats(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> LogStats:
        """获取日志统计信息"""
        # 基础统计
        total_logs = self.db.query(SyncLog).filter(
            SyncLog.created_at.between(start_time, end_time)
        ).count()

        # 按级别统计
        level_counts = {}
        for level in LogLevel.__args__:
            count = self.db.query(SyncLog).filter(
                and_(
                    SyncLog.created_at.between(start_time, end_time),
                    SyncLog.level == level
                )
            ).count()
            level_counts[level] = count

        # 错误率
        error_count = level_counts.get("ERROR", 0) + level_counts.get("CRITICAL", 0)
        error_rate = (error_count / total_logs * 100) if total_logs > 0 else 0.0

        # 平均执行时长
        avg_duration = self.db.query(func.avg(SyncLog.duration)).filter(
            and_(
                SyncLog.created_at.between(start_time, end_time),
                SyncLog.duration.isnot(None)
            )
        ).scalar()

        # 最近24小时错误数
        recent_start = datetime.utcnow() - timedelta(hours=24)
        recent_errors = self.db.query(SyncLog).filter(
            and_(
                SyncLog.created_at >= recent_start,
                SyncLog.level.in_(["ERROR", "CRITICAL"])
            )
        ).count()

        return LogStats(
            total_logs=total_logs,
            level_counts=level_counts,
            error_rate=error_rate,
            avg_duration=avg_duration,
            recent_errors=recent_errors,
            time_range={
                "start": start_time,
                "end": end_time
            }
        )

    async def get_log_levels_count(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """获取各级别日志数量统计"""
        level_counts = {}
        for level in LogLevel.__args__:
            count = self.db.query(SyncLog).filter(
                and_(
                    SyncLog.created_at.between(start_time, end_time),
                    SyncLog.level == level
                )
            ).count()
            level_counts[level] = count

        return level_counts

    async def get_recent_errors(
        self,
        start_time: datetime,
        limit: int = 20
    ) -> List[SyncLog]:
        """获取最近的错误日志"""
        return self.db.query(SyncLog).filter(
            and_(
                SyncLog.created_at >= start_time,
                SyncLog.level.in_(["ERROR", "CRITICAL"])
            )
        ).order_by(desc(SyncLog.created_at)).limit(limit).all()

    async def count_old_logs(self, cutoff_time: datetime) -> int:
        """统计旧日志数量"""
        return self.db.query(SyncLog).filter(
            SyncLog.created_at < cutoff_time
        ).count()

    async def delete_old_logs(self, cutoff_time: datetime) -> int:
        """删除旧日志"""
        deleted_count = self.db.query(SyncLog).filter(
            SyncLog.created_at < cutoff_time
        ).delete()

        self.db.commit()
        return deleted_count

    async def export_logs(
        self,
        filters: Dict[str, Any],
        format: str = "json"
    ) -> Dict[str, Any]:
        """导出日志"""
        # 构建查询
        query = self.db.query(SyncLog)

        if filters:
            if "level" in filters:
                query = query.filter(SyncLog.level == filters["level"])
            if "start_time" in filters:
                query = query.filter(SyncLog.created_at >= filters["start_time"])
            if "end_time" in filters:
                query = query.filter(SyncLog.created_at <= filters["end_time"])

        # 限制导出数量
        logs = query.order_by(desc(SyncLog.created_at)).limit(10000).all()

        # 生成文件ID和文件名
        import uuid
        file_id = str(uuid.uuid4())
        filename = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"

        # 这里应该实现实际的文件导出逻辑
        # 暂时返回模拟数据
        return {
            "file_id": file_id,
            "filename": filename,
            "logs": [
                {
                    "id": log.id,
                    "task_id": log.task_id,
                    "level": log.level,
                    "message": log.message,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        }

    async def create_log(
        self,
        task_id: str,
        level: str,
        message: str,
        product_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration: Optional[float] = None,
        success: Optional[bool] = None
    ) -> SyncLog:
        """创建日志记录"""
        log = SyncLog(
            task_id=task_id,
            product_id=product_id,
            level=level,
            message=message,
            details=details or {},
            error_type=error_type,
            started_at=started_at,
            completed_at=completed_at,
            duration=duration,
            success=success
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    async def update_log(
        self,
        log_id: int,
        updates: Dict[str, Any]
    ) -> Optional[SyncLog]:
        """更新日志记录"""
        log = await self.get_log_by_id(log_id)
        if not log:
            return None

        for field, value in updates.items():
            if hasattr(log, field):
                setattr(log, field, value)

        self.db.commit()
        self.db.refresh(log)

        return log

    async def get_task_logs(
        self,
        task_id: str,
        skip: int = 0,
        limit: int = 50,
        level: Optional[str] = None
    ) -> Tuple[List[SyncLog], int]:
        """获取特定任务的日志"""
        query = self.db.query(SyncLog).filter(SyncLog.task_id == task_id)

        if level:
            query = query.filter(SyncLog.level == level)

        total = query.count()
        logs = query.order_by(desc(SyncLog.created_at)).offset(skip).limit(limit).all()

        return logs, total

    async def get_product_logs(
        self,
        product_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[SyncLog], int]:
        """获取特定商品的日志"""
        query = self.db.query(SyncLog).filter(SyncLog.product_id == product_id)

        total = query.count()
        logs = query.order_by(desc(SyncLog.created_at)).offset(skip).limit(limit).all()

        return logs, total

    async def get_error_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取错误摘要"""
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # 按错误类型统计
        error_types = self.db.query(
            SyncLog.error_type,
            func.count(SyncLog.id).label('count')
        ).filter(
            and_(
                SyncLog.created_at >= start_time,
                SyncLog.level.in_(["ERROR", "CRITICAL"]),
                SyncLog.error_type.isnot(None)
            )
        ).group_by(SyncLog.error_type).order_by(desc('count')).limit(10).all()

        # 按任务统计错误数
        task_errors = self.db.query(
            SyncLog.task_id,
            func.count(SyncLog.id).label('error_count')
        ).filter(
            and_(
                SyncLog.created_at >= start_time,
                SyncLog.level.in_(["ERROR", "CRITICAL"])
            )
        ).group_by(SyncLog.task_id).order_by(desc('error_count')).limit(10).all()

        return {
            "time_range_hours": hours,
            "error_types": [
                {"error_type": et.error_type, "count": et.count}
                for et in error_types
            ],
            "top_error_tasks": [
                {"task_id": te.task_id, "error_count": te.error_count}
                for te in task_errors
            ]
        }