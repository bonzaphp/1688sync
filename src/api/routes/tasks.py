"""
任务管理路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from ...database.connection import get_db
from ...database.models import SyncTask, SyncLog
from ..schemas.task import (
    TaskCreate, TaskResponse, TaskListResponse, TaskUpdate,
    TaskStatus, TaskType, LogResponse, LogListResponse
)
from ..services.task_service import TaskService
from ..deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    status: Optional[TaskStatus] = Query(None, description="任务状态"),
    task_type: Optional[TaskType] = Query(None, description="任务类型"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取任务列表"""
    try:
        task_service = TaskService(db)

        # 构建查询参数
        filters = {}
        if status:
            filters["status"] = status
        if task_type:
            filters["task_type"] = task_type

        tasks, total = await task_service.get_tasks(
            skip=skip,
            limit=limit,
            filters=filters
        )

        return TaskListResponse(
            tasks=[TaskResponse.from_orm(task) for task in tasks],
            total=total,
            skip=skip,
            limit=limit
        )

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取单个任务详情"""
    try:
        task_service = TaskService(db)
        task = await task_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return TaskResponse.from_orm(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务详情失败")


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建新任务"""
    try:
        task_service = TaskService(db)
        task = await task_service.create_task(task_data, background_tasks)

        return TaskResponse.from_orm(task)

    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.put("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: TaskStatus,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新任务状态"""
    try:
        task_service = TaskService(db)
        task = await task_service.update_task_status(task_id, status)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        return {"message": "任务状态更新成功", "task_id": task_id, "status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")
        raise HTTPException(status_code=500, detail="更新任务状态失败")


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """取消任务"""
    try:
        task_service = TaskService(db)
        success = await task_service.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法取消")

        return {"message": "任务已取消", "task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除任务"""
    try:
        task_service = TaskService(db)
        success = await task_service.delete_task(task_id)

        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")

        return {"message": "任务删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail="删除任务失败")


@router.get("/{task_id}/logs", response_model=LogListResponse)
async def get_task_logs(
    task_id: str,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    level: Optional[str] = Query(None, description="日志级别"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取任务日志"""
    try:
        task_service = TaskService(db)

        # 检查任务是否存在
        task = await task_service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取日志
        filters = {"task_id": task_id}
        if level:
            filters["level"] = level

        logs, total = await task_service.get_logs(
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务日志失败")


@router.get("/stats/summary")
async def get_task_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取任务统计信息"""
    try:
        task_service = TaskService(db)
        stats = await task_service.get_task_stats()

        return stats

    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务统计失败")


@router.post("/retry-failed")
async def retry_failed_tasks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """重试失败的任务"""
    try:
        task_service = TaskService(db)
        task_ids = await task_service.retry_failed_tasks(background_tasks)

        return {
            "message": "失败任务重试已启动",
            "retry_count": len(task_ids),
            "task_ids": task_ids
        }

    except Exception as e:
        logger.error(f"重试失败任务失败: {e}")
        raise HTTPException(status_code=500, detail="重试失败任务失败")