"""
日志管理路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from ...database.connection import get_db
from ...database.models import SyncLog
from ..schemas.log import (
    LogResponse, LogListResponse, LogLevel, LogStats, LogSearchQuery
)
from ..services.log_service import LogService
from ..deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=LogListResponse)
async def list_logs(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    task_id: Optional[str] = Query(None, description="任务ID"),
    product_id: Optional[int] = Query(None, description="商品ID"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取日志列表"""
    try:
        log_service = LogService(db)

        # 构建查询参数
        filters = {}
        if level:
            filters["level"] = level
        if task_id:
            filters["task_id"] = task_id
        if product_id:
            filters["product_id"] = product_id
        if start_time:
            filters["start_time"] = start_time
        if end_time:
            filters["end_time"] = end_time
        if search:
            filters["search"] = search

        logs, total = await log_service.get_logs(
            skip=skip,
            limit=limit,
            filters=filters
        )

        return LogListResponse(
            logs=[LogResponse.from_orm(log) for log in logs],
            total=total,
            skip=skip,
            limit=limit
        )

    except Exception as e:
        logger.error(f"获取日志列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志列表失败")


@router.get("/{log_id}", response_model=LogResponse)
async def get_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单条日志详情"""
    try:
        log_service = LogService(db)
        log = await log_service.get_log_by_id(log_id)

        if not log:
            raise HTTPException(status_code=404, detail="日志不存在")

        return LogResponse.from_orm(log)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日志详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志详情失败")


@router.get("/stats/summary")
async def get_log_stats(
    days: int = Query(7, ge=1, le=30, description="统计天数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取日志统计信息"""
    try:
        log_service = LogService(db)

        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        stats = await log_service.get_log_stats(start_time, end_time)

        return stats

    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志统计失败")


@router.get("/levels/count")
async def get_log_levels_count(
    hours: int = Query(24, ge=1, le=168, description="统计小时数"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取各级别日志数量统计"""
    try:
        log_service = LogService(db)

        # 计算时间范围
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        level_counts = await log_service.get_log_levels_count(start_time, end_time)

        return {
            "time_range": f"最近{hours}小时",
            "start_time": start_time,
            "end_time": end_time,
            "level_counts": level_counts
        }

    except Exception as e:
        logger.error(f"获取日志级别统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志级别统计失败")


@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取最近的错误日志"""
    try:
        log_service = LogService(db)

        # 计算时间范围
        start_time = datetime.utcnow() - timedelta(hours=hours)

        errors = await log_service.get_recent_errors(start_time, limit)

        return {
            "time_range": f"最近{hours}小时",
            "count": len(errors),
            "errors": [LogResponse.from_orm(error) for error in errors]
        }

    except Exception as e:
        logger.error(f"获取最近错误失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近错误失败")


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(30, ge=7, le=365, description="保留天数"),
    dry_run: bool = Query(True, description="是否为试运行"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """清理旧日志"""
    try:
        log_service = LogService(db)

        # 计算清理时间点
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        if dry_run:
            # 试运行，只返回将要删除的日志数量
            count = await log_service.count_old_logs(cutoff_time)
            return {
                "dry_run": True,
                "cutoff_time": cutoff_time,
                "delete_count": count,
                "message": f"将删除{count}条{days}天前的日志"
            }
        else:
            # 实际删除
            count = await log_service.delete_old_logs(cutoff_time)
            return {
                "dry_run": False,
                "cutoff_time": cutoff_time,
                "deleted_count": count,
                "message": f"已删除{count}条{days}天前的日志"
            }

    except Exception as e:
        logger.error(f"清理旧日志失败: {e}")
        raise HTTPException(status_code=500, detail="清理旧日志失败")


@router.get("/export")
async def export_logs(
    level: Optional[LogLevel] = Query(None, description="日志级别"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    format: str = Query("json", regex="^(json|csv)$", description="导出格式"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出日志"""
    try:
        log_service = LogService(db)

        # 构建查询参数
        filters = {}
        if level:
            filters["level"] = level
        if start_time:
            filters["start_time"] = start_time
        if end_time:
            filters["end_time"] = end_time

        # 导出日志（这里简化处理，实际应该返回文件流）
        export_data = await log_service.export_logs(filters, format)

        return {
            "format": format,
            "filters": filters,
            "export_count": len(export_data["logs"]),
            "download_url": f"/api/v1/logs/download/{export_data['file_id']}",
            "message": "日志导出成功"
        }

    except Exception as e:
        logger.error(f"导出日志失败: {e}")
        raise HTTPException(status_code=500, detail="导出日志失败")