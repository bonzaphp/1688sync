"""
同步记录数据模型
"""
from sqlalchemy import BigInteger, Column, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON

from .base import Base


class SyncRecord(Base):
    """同步记录模型"""

    __tablename__ = "sync_records"

    # 任务信息
    task_id = Column(
        String(100),
        nullable=False,
        comment="任务ID"
    )
    task_name = Column(
        String(200),
        nullable=True,
        comment="任务名称"
    )

    # 操作类型和范围
    operation_type = Column(
        String(20),
        nullable=False,
        comment="操作类型: full/incremental/manual/scheduled"
    )
    sync_type = Column(
        String(20),
        nullable=False,
        default='product',
        comment="同步类型: product/supplier/image/all"
    )
    source_filter = Column(
        JSON,
        nullable=True,
        comment="源数据过滤条件"
    )

    # 执行状态
    status = Column(
        String(20),
        default='pending',
        nullable=False,
        comment="状态: pending/running/completed/failed/cancelled"
    )
    progress = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="进度百分比 (0-100)"
    )

    # 时间信息
    start_time = Column(
        BigInteger,
        nullable=True,
        comment="开始时间戳"
    )
    end_time = Column(
        BigInteger,
        nullable=True,
        comment="结束时间戳"
    )
    duration = Column(
        BigInteger,
        nullable=True,
        comment="执行时长(秒)"
    )

    # 统计信息
    total_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="总数量"
    )
    processed_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="已处理数量"
    )
    success_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="成功数量"
    )
    failed_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="失败数量"
    )
    skipped_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="跳过数量"
    )

    # 错误信息
    error_message = Column(
        Text,
        nullable=True,
        comment="主要错误信息"
    )
    error_details = Column(
        JSON,
        nullable=True,
        comment="详细错误信息列表"
    )
    error_count = Column(
        BigInteger,
        default=0,
        nullable=False,
        comment="错误次数"
    )

    # 性能指标
    records_per_second = Column(
        BigInteger,
        nullable=True,
        comment="每秒处理记录数"
    )
    memory_usage_mb = Column(
        BigInteger,
        nullable=True,
        comment="内存使用量(MB)"
    )
    cpu_usage_percent = Column(
        BigInteger,
        nullable=True,
        comment="CPU使用率(%)"
    )

    # 配置信息
    config = Column(
        JSON,
        nullable=True,
        comment="同步配置参数"
    )
    batch_size = Column(
        BigInteger,
        default=1000,
        nullable=False,
        comment="批次大小"
    )
    max_retries = Column(
        BigInteger,
        default=3,
        nullable=False,
        comment="最大重试次数"
    )

    # 结果摘要
    summary = Column(
        JSON,
        nullable=True,
        comment="执行摘要信息"
    )
    recommendations = Column(
        JSON,
        nullable=True,
        comment="优化建议"
    )

    # 索引定义
    __table_args__ = (
        Index('idx_sync_task_id', 'task_id'),
        Index('idx_sync_operation_type', 'operation_type'),
        Index('idx_sync_status', 'status'),
        Index('idx_sync_start_time', 'start_time'),
        Index('idx_sync_sync_type', 'sync_type'),
        Index('idx_sync_progress', 'progress'),
    )

    def __repr__(self) -> str:
        return f"<SyncRecord(id={self.id}, task_id='{self.task_id}', status='{self.status}')>"

    @property
    def is_running(self) -> bool:
        """判断是否正在运行"""
        return self.status == 'running'

    @property
    def is_completed(self) -> bool:
        """判断是否已完成"""
        return self.status in ['completed', 'failed', 'cancelled']

    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if self.processed_count == 0:
            return 0.0
        return round((self.success_count / self.processed_count) * 100, 2)

    @property
    def failure_rate(self) -> float:
        """获取失败率"""
        if self.processed_count == 0:
            return 0.0
        return round((self.failed_count / self.processed_count) * 100, 2)

    @property
    def estimated_remaining_time(self) -> int:
        """估算剩余时间(秒)"""
        if not self.is_running or self.processed_count == 0:
            return 0

        elapsed_time = self.duration or 0
        if elapsed_time == 0:
            return 0

        avg_time_per_record = elapsed_time / self.processed_count
        remaining_records = self.total_count - self.processed_count
        return int(remaining_records * avg_time_per_record)

    def start_execution(self):
        """开始执行"""
        import time
        self.status = 'running'
        self.start_time = int(time.time())
        self.progress = 0

    def complete_execution(self, status: str = 'completed'):
        """完成执行"""
        import time
        current_time = int(time.time())
        self.status = status
        self.end_time = current_time
        if self.start_time:
            self.duration = current_time - self.start_time
            if self.duration > 0 and self.processed_count > 0:
                self.records_per_second = int(self.processed_count / self.duration)
        self.progress = 100

    def update_progress(self, processed: int, success: int, failed: int):
        """更新进度"""
        self.processed_count = processed
        self.success_count = success
        self.failed_count = failed

        if self.total_count > 0:
            self.progress = int((processed / self.total_count) * 100)
            self.progress = min(100, max(0, self.progress))

    def add_error(self, error_message: str, error_details: dict = None):
        """添加错误信息"""
        self.error_count += 1
        self.error_message = error_message

        if self.error_details is None:
            self.error_details = []
        if not isinstance(self.error_details, list):
            self.error_details = []

        error_entry = {
            'timestamp': int(__import__('time').time()),
            'message': error_message
        }
        if error_details:
            error_entry.update(error_details)
        self.error_details.append(error_entry)

    def add_summary(self, key: str, value):
        """添加摘要信息"""
        if self.summary is None:
            self.summary = {}
        self.summary[key] = value

    def get_config_value(self, key: str, default=None):
        """获取配置值"""
        if self.config is None:
            return default
        return self.config.get(key, default)