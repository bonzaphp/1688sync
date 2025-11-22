"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Optional

try:
    from pydantic import BaseSettings, Field
except ImportError:
    from pydantic_settings import BaseSettings
    from pydantic import Field


class Settings(BaseSettings):
    """应用配置"""

    # 项目基础配置
    name: str = "1688sync"
    version: str = "0.1.0"
    debug: bool = False

    # 数据库配置
    database_url: str = Field(
        default="mysql+pymysql://user:password@localhost:3306/1688sync",
        env="DATABASE_URL"
    )

    # Redis配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )

    # API配置
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=False, env="API_DEBUG")

    # Scrapy配置
    scrapy_user_agent: str = Field(
        default="1688sync-bot/1.0",
        env="SCRAPY_USER_AGENT"
    )
    scrapy_concurrent_requests: int = Field(
        default=16,
        env="SCRAPY_CONCURRENT_REQUESTS"
    )
    scrapy_download_delay: float = Field(
        default=1.0,
        env="SCRAPY_DOWNLOAD_DELAY"
    )
    scrapy_randomize_download_delay: bool = Field(
        default=True,
        env="SCRAPY_RANDOMIZE_DOWNLOAD_DELAY"
    )

    # Celery配置
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default="logs/1688sync.log", env="LOG_FILE")

    # 文件存储配置
    data_dir: Path = Field(default=Path("./data"), env="DATA_DIR")
    image_dir: Path = Field(default=Path("./data/images"), env="IMAGE_DIR")

    # 1688平台配置
    base_url: str = "https://www.1688.com"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.image_dir.mkdir(parents=True, exist_ok=True)

# 确保日志目录存在
if settings.log_file:
    Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)