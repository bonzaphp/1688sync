"""
数据库模型基类
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import BigInteger, Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr


class BaseModel:
    """数据库模型基类"""

    @declared_attr
    def __tablename__(cls):
        """自动生成表名"""
        return cls.__name__.lower()

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 时间戳字段
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # 软删除字段
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="删除时间")
    is_deleted = Column(
        String(1),
        server_default='N',
        nullable=False,
        comment="是否删除: Y/N"
    )

    def to_dict(self, exclude_fields: list = None) -> Dict[str, Any]:
        """转换为字典"""
        exclude_fields = exclude_fields or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result

    def update_from_dict(self, data: Dict[str, Any], exclude_fields: list = None):
        """从字典更新模型"""
        exclude_fields = exclude_fields or ['id', 'created_at']
        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()

    def soft_delete(self):
        """软删除"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = 'Y'

    def restore(self):
        """恢复软删除"""
        self.deleted_at = None
        self.is_deleted = 'N'

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


# 创建基础模型类
Base = declarative_base(cls=BaseModel)