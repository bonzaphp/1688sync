"""
日志数据模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

# 日志级别枚举
LogLevel = Literal[
    "DEBUG",   # 调试信息
    "INFO",    # 一般信息
    "WARNING", # 警告
    "ERROR",   # 错误
    "CRITICAL" # 严重错误
]


class LogBase(BaseModel):
    """日志基础模式"""
    level: LogLevel = Field(..., description="日志级别")
    message: Optional[str] = Field(None, description="日志消息")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="详细信息")
    error_type: Optional[str] = Field(None, description="错误类型")

    class Config:
        from_attributes = True


class LogCreate(LogBase):
    """创建日志模式"""
    task_id: str = Field(..., description="任务ID")
    product_id: Optional[int] = Field(None, description="商品ID")


class LogUpdate(BaseModel):
    """更新日志模式"""
    message: Optional[str] = Field(None, description="日志消息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    duration: Optional[float] = Field(None, ge=0, description="执行时长")
    success: Optional[bool] = Field(None, description="是否成功")
    error_type: Optional[str] = Field(None, description="错误类型")


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


class LogStats(BaseModel):
    """日志统计模式"""
    total_logs: int
    level_counts: Dict[LogLevel, int]
    error_rate: float = 0.0
    avg_duration: Optional[float] = None
    recent_errors: int = 0  # 最近24小时错误数
    time_range: Dict[str, datetime]


class LogSearchQuery(BaseModel):
    """日志搜索查询模式"""
    level: Optional[LogLevel] = Field(None, description="日志级别")
    task_id: Optional[str] = Field(None, description="任务ID")
    product_id: Optional[int] = Field(None, description="商品ID")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    search: Optional[str] = Field(None, description="搜索关键词")
    error_type: Optional[str] = Field(None, description="错误类型")
    success: Optional[bool] = Field(None, description="是否成功")
    min_duration: Optional[float] = Field(None, ge=0, description="最小时长")
    max_duration: Optional[float] = Field(None, ge=0, description="最大时长")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="排序顺序")


class LogAggregationResponse(BaseModel):
    """日志聚合响应模式"""
    time_interval: str  # hour, day, week, month
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]


class LogExportRequest(BaseModel):
    """日志导出请求模式"""
    format: Literal["json", "csv", "xlsx"] = Field("json", description="导出格式")
    filters: Optional[LogSearchQuery] = Field(None, description="过滤条件")
    include_details: bool = Field(default=True, description="是否包含详细信息")
    compress: bool = Field(default=False, description="是否压缩")


class LogExportResponse(BaseModel):
    """日志导出响应模式"""
    file_id: str
    filename: str
    format: str
    file_size: int
    record_count: int
    download_url: str
    expires_at: datetime


class LogCleanupRequest(BaseModel):
    """日志清理请求模式"""
    retention_days: int = Field(..., ge=7, le=365, description="保留天数")
    level_filter: Optional[List[LogLevel]] = Field(None, description="级别过滤")
    dry_run: bool = Field(default=True, description="是否试运行")
    backup: bool = Field(default=False, description="是否备份")


class LogCleanupResponse(BaseModel):
    """日志清理响应模式"""
    dry_run: bool
    cutoff_time: datetime
    total_before: int
    total_after: int
    deleted_count: int
    backup_file: Optional[str] = None
    duration: float


class LogAlertRule(BaseModel):
    """日志告警规则模式"""
    name: str = Field(..., description="规则名称")
    level: LogLevel = Field(..., description="触发级别")
    threshold: int = Field(default=10, description="阈值")
    time_window: int = Field(default=300, description="时间窗口（秒）")
    condition: Literal["count", "rate", "pattern"] = Field("count", description="触发条件")
    pattern: Optional[str] = Field(None, description="匹配模式")
    enabled: bool = Field(default=True, description="是否启用")
    notification_channels: List[str] = Field(default_factory=list, description="通知渠道")


class LogAlert(BaseModel):
    """日志告警模式"""
    id: str
    rule_name: str
    level: LogLevel
    message: str
    triggered_at: datetime
    matched_logs: List[LogResponse]
    resolved: bool = False
    resolved_at: Optional[datetime] = None