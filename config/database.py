"""
数据库配置模块
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field


class DatabaseSettings(BaseSettings):
    """数据库配置类"""

    # 数据库连接配置
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    database: str = Field(default="1688sync", env="DB_NAME")
    username: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="password", env="DB_PASSWORD")

    # 连接池配置
    pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=30, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    pool_pre_ping: bool = Field(default=True, env="DB_POOL_PRE_PING")

    # SSL配置
    ssl_mode: Optional[str] = Field(default=None, env="DB_SSL_MODE")
    ssl_cert_file: Optional[str] = Field(default=None, env="DB_SSL_CERT")
    ssl_key_file: Optional[str] = Field(default=None, env="DB_SSL_KEY")

    # 连接选项
    echo: bool = Field(default=False, env="DB_ECHO")
    echo_pool: bool = Field(default=False, env="DB_ECHO_POOL")
    future: bool = Field(default=True, env="DB_FUTURE")

    @property
    def database_url(self) -> str:
        """生成数据库连接URL"""
        if self.ssl_mode:
            return (
                f"postgresql+asyncpg://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
                f"?ssl={self.ssl_mode}"
            )
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    @property
    def sync_database_url(self) -> str:
        """生成同步数据库连接URL（用于Alembic迁移）"""
        return (
            f"postgresql+psycopg2://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
db_settings = DatabaseSettings()