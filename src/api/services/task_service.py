"""
任务服务层
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from fastapi import BackgroundTasks
import uuid
import logging
from datetime import datetime

from ...database.models import SyncTask, SyncLog
from ..schemas.task import TaskCreate, TaskUpdate, TaskStatus, TaskType

logger = logging.getLogger(__name__)


class TaskService:
    """任务服务类"""

    def __init__(self, db: Session):
        self.db = db

    async def get_tasks(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[SyncTask], int]:
        """获取任务列表"""
        query = self.db.query(SyncTask)

        # 应用过滤条件
        if filters:
            if "status" in filters:
                query = query.filter(SyncTask.status == filters["status"])
            if "task_type" in filters:
                query = query.filter(SyncTask.task_type == filters["task_type"])

        # 获取总数
        total = query.count()

        # 应用分页和排序
        tasks = query.order_by(desc(SyncTask.created_at)).offset(skip).limit(limit).all()

        return tasks, total

    async def get_task_by_id(self, task_id: str) -> Optional[SyncTask]:
        """根据ID获取任务"""
        return self.db.query(SyncTask).filter(SyncTask.task_id == task_id).first()

    async def create_task(
        self,
        task_data: TaskCreate,
        background_tasks: BackgroundTasks
    ) -> SyncTask:
        """创建任务"""
        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 创建任务记录
        db_task = SyncTask(
            task_id=task_id,
            task_type=task_data.task_type,
            source_url=task_data.source_url,
            target_count=task_data.target_count,
            config=task_data.config,
            status="pending",
            progress=0.0
        )

        self.db.add(db_task)
        self.db.commit()
        self.db.refresh(db_task)

        # 添加后台执行任务
        background_tasks.add_task(
            self._execute_task,
            task_id
        )

        logger.info(f"创建任务成功: {task_id}")
        return db_task

    async def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[SyncTask]:
        """更新任务状态"""
        db_task = await self.get_task_by_id(task_id)
        if not db_task:
            return None

        db_task.status = status

        # 更新时间戳
        if status == "running" and not db_task.started_at:
            db_task.started_at = datetime.utcnow()
        elif status in ["completed", "failed", "cancelled"] and not db_task.completed_at:
            db_task.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_task)

        logger.info(f"更新任务状态: {task_id} -> {status}")
        return db_task

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        db_task = await self.get_task_by_id(task_id)
        if not db_task:
            return False

        if db_task.status in ["completed", "failed", "cancelled"]:
            return False  # 已完成的任务无法取消

        db_task.status = "cancelled"
        db_task.completed_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"取消任务: {task_id}")
        return True

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        db_task = await self.get_task_by_id(task_id)
        if not db_task:
            return False

        # 只能删除已完成、失败或取消的任务
        if db_task.status not in ["completed", "failed", "cancelled"]:
            return False

        self.db.delete(db_task)
        self.db.commit()

        logger.info(f"删除任务: {task_id}")
        return True

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
            if "task_id" in filters:
                query = query.filter(SyncLog.task_id == filters["task_id"])
            if "product_id" in filters:
                query = query.filter(SyncLog.product_id == filters["product_id"])
            if "level" in filters:
                query = query.filter(SyncLog.level == filters["level"])
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

    async def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        # 基础统计
        total_tasks = self.db.query(SyncTask).count()
        pending_tasks = self.db.query(SyncTask).filter(SyncTask.status == "pending").count()
        running_tasks = self.db.query(SyncTask).filter(SyncTask.status == "running").count()
        completed_tasks = self.db.query(SyncTask).filter(SyncTask.status == "completed").count()
        failed_tasks = self.db.query(SyncTask).filter(SyncTask.status == "failed").count()
        cancelled_tasks = self.db.query(SyncTask).filter(SyncTask.status == "cancelled").count()

        # 按类型统计
        task_type_counts = {}
        for task_type in TaskType.__args__:
            count = self.db.query(SyncTask).filter(SyncTask.task_type == task_type).count()
            task_type_counts[task_type] = count

        # 平均执行时长
        avg_duration = self.db.query(func.avg(SyncTask.completed_at - SyncTask.started_at)).filter(
            and_(
                SyncTask.started_at.isnot(None),
                SyncTask.completed_at.isnot(None)
            )
        ).scalar()

        if avg_duration:
            avg_duration = avg_duration.total_seconds()

        # 成功率
        if completed_tasks + failed_tasks > 0:
            success_rate = (completed_tasks / (completed_tasks + failed_tasks)) * 100
        else:
            success_rate = 0.0

        # 最近任务
        recent_tasks = self.db.query(SyncTask).order_by(desc(SyncTask.created_at)).limit(10).all()

        # 按天统计
        from datetime import datetime, timedelta
        daily_stats = {}
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            date_str = date.isoformat()

            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())

            day_total = self.db.query(SyncTask).filter(
                SyncTask.created_at.between(day_start, day_end)
            ).count()

            daily_stats[date_str] = {
                "total": day_total,
                "completed": self.db.query(SyncTask).filter(
                    and_(
                        SyncTask.created_at.between(day_start, day_end),
                        SyncTask.status == "completed"
                    )
                ).count(),
                "failed": self.db.query(SyncTask).filter(
                    and_(
                        SyncTask.created_at.between(day_start, day_end),
                        SyncTask.status == "failed"
                    )
                ).count()
            }

        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "cancelled_tasks": cancelled_tasks,
            "task_type_counts": task_type_counts,
            "avg_duration": avg_duration,
            "success_rate": success_rate,
            "recent_tasks": recent_tasks,
            "daily_stats": daily_stats
        }

    async def retry_failed_tasks(self, background_tasks: BackgroundTasks) -> List[str]:
        """重试失败的任务"""
        failed_tasks = self.db.query(SyncTask).filter(SyncTask.status == "failed").all()

        retried_task_ids = []
        for task in failed_tasks:
            # 重置任务状态
            task.status = "pending"
            task.progress = 0.0
            task.started_at = None
            task.completed_at = None
            task.processed_count = 0
            task.success_count = 0
            task.failed_count = 0

            retried_task_ids.append(task.task_id)

            # 添加重试任务
            background_tasks.add_task(
                self._execute_task,
                task.task_id
            )

        self.db.commit()
        logger.info(f"重试失败任务: {len(retried_task_ids)}个")

        return retried_task_ids

    async def _execute_task(self, task_id: str):
        """执行任务（后台任务）"""
        try:
            # 获取任务
            task = await self.get_task_by_id(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            # 更新状态为运行中
            await self.update_task_status(task_id, "running")

            # 记录开始日志
            await self._create_log(task_id, "INFO", f"任务开始执行: {task.task_type}")

            # 根据任务类型执行不同逻辑
            if task.task_type == "single":
                await self._execute_single_task(task)
            elif task.task_type == "batch":
                await self._execute_batch_task(task)
            elif task.task_type == "category":
                await self._execute_category_task(task)
            elif task.task_type == "full":
                await self._execute_full_task(task)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")

            # 更新状态为完成
            await self.update_task_status(task_id, "completed")
            await self._create_log(task_id, "INFO", "任务执行完成")

        except Exception as e:
            logger.error(f"任务执行失败: {task_id}, 错误: {e}")

            # 更新状态为失败
            await self.update_task_status(task_id, "failed")
            await self._create_log(
                task_id,
                "ERROR",
                f"任务执行失败: {str(e)}",
                error_type=type(e).__name__
            )

    async def _execute_single_task(self, task: SyncTask):
        """执行单个任务"""
        # 模拟任务执行
        import time
        time.sleep(2)

        task.processed_count = 1
        task.success_count = 1
        task.progress = 100.0
        self.db.commit()

    async def _execute_batch_task(self, task: SyncTask):
        """执行批量任务"""
        # 模拟批量任务执行
        import time
        total_items = task.target_count or 10

        for i in range(total_items):
            time.sleep(0.5)  # 模拟处理时间

            task.processed_count = i + 1
            task.success_count = i + 1
            task.progress = ((i + 1) / total_items) * 100
            self.db.commit()

    async def _execute_category_task(self, task: SyncTask):
        """执行分类任务"""
        # 模拟分类任务执行
        await self._execute_batch_task(task)

    async def _execute_full_task(self, task: SyncTask):
        """执行全量任务"""
        # 模拟全量任务执行
        import time
        time.sleep(10)  # 模拟长时间任务

        task.processed_count = 100
        task.success_count = 95
        task.failed_count = 5
        task.progress = 100.0
        self.db.commit()

    async def _create_log(
        self,
        task_id: str,
        level: str,
        message: str,
        product_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None
    ):
        """创建日志记录"""
        log = SyncLog(
            task_id=task_id,
            product_id=product_id,
            level=level,
            message=message,
            details=details or {},
            error_type=error_type,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration=0.0,
            success=(level != "ERROR")
        )

        self.db.add(log)
        self.db.commit()