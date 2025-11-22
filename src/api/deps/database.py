"""
数据库依赖注入
"""
from typing import Generator
from sqlalchemy.orm import Session

from ...database.connection import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()