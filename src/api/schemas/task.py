"""
任务数据模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator

# 任务状态枚举
TaskStatus = Literal[
    "pending",    # 等待中
    "running",    # 运行中
    "completed",  # 已完成
    "failed",     # 失败
    "cancelled"   # 已取消
]

# 任务类型枚举
TaskType = Literal[
    "single",     # 单个商品同步
    "batch",      # 批量商品同步
    "category",   # 分类商品同步
    "full"        # 全量同步
]


class TaskBase(BaseModel):
    """任务基础模式"""
    task_type: TaskType = Field(..., description="任务类型")
    source_url: Optional[str] = Field(None, description="源URL")
    target_count: int = Field(default=0, ge=0, description="目标处理数量")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务配置")

    class Config:
        from_attributes = True


class TaskCreate(TaskBase):
    """创建任务模式"""
    pass


class TaskUpdate(BaseModel):
    """更新任务模式"""
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    progress: Optional[float] = Field(None, ge=0, le=100, description="进度百分比")
    processed_count: Optional[int] = Field(None, ge=0, description="已处理数量")
    success_count: Optional[int] = Field(None, ge=0, description="成功数量")
    failed_count: Optional[int] = Field(None, ge=0, description="失败数量")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")

    @validator('progress')
    def validate_progress(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('进度必须在0-100之间')
        return v


class TaskResponse(TaskBase):
    """任务响应模式"""
    id: int
    task_id: str
    processed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    status: TaskStatus
    progress: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    # 计算属性
    @property
    def duration(self) -> Optional[float]:
        """任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.processed_count == 0:
            return 0.0
        return (self.success_count / self.processed_count) * 100


class TaskListResponse(BaseModel):
    """任务列表响应模式"""
    tasks: List[TaskResponse]
    total: int
    skip: int
    limit: int

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.skip + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.skip > 0


class LogBase(BaseModel):
    """日志基础模式"""
    level: str = Field(..., description="日志级别")
    message: Optional[str] = Field(None, description="日志消息")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="详细信息")
    error_type: Optional[str] = Field(None, description="错误类型")

    class Config:
        from_attributes = True


class LogResponse(LogBase):
    """日志响应模式"""
    id: int
    task_id: str
    product_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    created_at: datetime


class LogListResponse(BaseModel):
    """日志列表响应模式"""
    logs: List[LogResponse]
    total: int
    skip: int
    limit: int

    @property
    def has_next(self) -> bool:
        """是否有下一页"""
        return self.skip + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        """是否有上一页"""
        return self.skip > 0


class TaskStatsResponse(BaseModel):
    """任务统计响应模式"""
    total_tasks: int
    pending_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    avg_duration: Optional[float] = None  # 平均执行时长
    success_rate: float = 0.0  # 总体成功率
    recent_tasks: List[TaskResponse]  # 最近任务
    task_type_counts: Dict[TaskType, int]  # 按类型统计
    daily_stats: Dict[str, Dict[str, int]]  # 按天统计


class TaskCreateRequest(BaseModel):
    """任务创建请求模式"""
    task_type: TaskType
    source_url: Optional[str] = None
    target_count: int = Field(default=0, ge=0, le=10000)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10, description="任务优先级")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")


class BatchTaskRequest(BaseModel):
    """批量任务请求模式"""
    task_type: TaskType
    items: List[str] = Field(..., min_items=1, max_items=100, description="任务项目列表")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    parallel: bool = Field(default=True, description="是否并行执行")
    delay_between_tasks: float = Field(default=1.0, ge=0, description="任务间隔时间")


class TaskControlRequest(BaseModel):
    """任务控制请求模式"""
    action: Literal["pause", "resume", "cancel", "retry"] = Field(..., description="控制动作")
    reason: Optional[str] = Field(None, description="操作原因")
    force: bool = Field(default=False, description="是否强制执行")


class TaskMonitoringResponse(BaseModel):
    """任务监控响应模式"""
    active_tasks: List[TaskResponse]
    queue_length: int
    system_load: Dict[str, float]
    recent_errors: List[LogResponse]
    performance_metrics: Dict[str, Any]