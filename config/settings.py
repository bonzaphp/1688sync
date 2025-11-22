"""
应用配置模块
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    app_name: str = Field(default="1688sync", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 存储配置
    storage_path: str = Field(default="./images", env="STORAGE_PATH")
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    allowed_image_types: list = Field(
        default=["image/jpeg", "image/jpg", "image/png", "image/webp"],
        env="ALLOWED_IMAGE_TYPES"
    )

    # CDN配置（预留）
    cdn_base_url: Optional[str] = Field(default=None, env="CDN_BASE_URL")
    cdn_enabled: bool = Field(default=False, env="CDN_ENABLED")

    # 缓存配置
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1小时

    # 并发配置
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")

    # 监控配置
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    metrics_enabled: bool = Field(default=False, env="METRICS_ENABLED")

    # 数据同步配置
    batch_size: int = Field(default=1000, env="BATCH_SIZE")
    sync_interval: int = Field(default=300, env="SYNC_INTERVAL")  # 5分钟
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    retry_delay: int = Field(default=5, env="RETRY_DELAY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
app_settings = AppSettings()


def get_settings() -> AppSettings:
    """获取应用配置实例"""
    return app_settings