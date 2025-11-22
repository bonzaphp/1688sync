"""
性能优化配置
"""
from src.core import (
    ConcurrencyConfig,
    CacheConfig,
    MemoryThresholds,
    PerformanceConfig
)

# 并发控制配置
CONCURRENCY_CONFIG = ConcurrencyConfig(
    max_workers=32,                    # 最大工作线程数
    max_concurrent_requests=100,       # 最大并发请求数
    rate_limit=10.0,                   # 每秒请求数限制
    queue_size=1000,                   # 任务队列大小
    timeout=30.0,                      # 超时时间
    retry_times=3,                     # 重试次数
    backoff_factor=1.0                 # 退避因子
)

# 缓存配置
CACHE_CONFIG = CacheConfig(
    memory_max_size=1000,              # 内存缓存最大条目数
    memory_ttl=300,                    # 内存缓存TTL(秒)
    lru_max_size=500,                  # LRU缓存最大条目数
    lru_ttl=600,                       # LRU缓存TTL(秒)
    redis_host="localhost",            # Redis主机
    redis_port=6379,                   # Redis端口
    redis_db=0,                        # Redis数据库
    redis_password=None,               # Redis密码
    redis_ttl=3600,                    # Redis缓存TTL(秒)
    file_cache_dir=".cache",           # 文件缓存目录
    file_cache_ttl=86400,              # 文件缓存TTL(秒)
    cache_strategy="multi",            # 缓存策略: memory, lru, redis, file, multi
    compression_enabled=True,          # 启用压缩
    serialization_method="pickle"      # 序列化方法
)

# 内存管理配置
MEMORY_THRESHOLDS = MemoryThresholds(
    warning_percent=70.0,              # 内存警告阈值(%)
    critical_percent=85.0,             # 内存严重阈值(%)
    max_objects=1000000,               # 最大对象数
    gc_frequency=100,                  # 垃圾回收频率
    cleanup_interval=60                # 清理间隔(秒)
)

# 性能监控配置
PERFORMANCE_CONFIG = PerformanceConfig(
    concurrency_config=CONCURRENCY_CONFIG,
    cache_config=CACHE_CONFIG,
    memory_thresholds=MEMORY_THRESHOLDS,
    monitoring_enabled=True,           # 启用监控
    monitoring_interval=30,            # 监控间隔(秒)
    auto_optimization=True,            # 自动优化
    optimization_interval=300,         # 优化间隔(秒)
    alert_enabled=True,                # 启用告警
    slow_request_threshold=2.0,        # 慢请求阈值(秒)
    high_memory_threshold=80.0,        # 高内存阈值(%)
    high_cpu_threshold=80.0            # 高CPU阈值(%)
)

# 环境特定配置
import os

# 开发环境配置
if os.getenv("ENVIRONMENT") == "development":
    CONCURRENCY_CONFIG.max_workers = 8
    CONCURRENCY_CONFIG.max_concurrent_requests = 20
    CACHE_CONFIG.memory_max_size = 100
    MEMORY_THRESHOLDS.warning_percent = 80.0
    PERFORMANCE_CONFIG.monitoring_interval = 60

# 生产环境配置
elif os.getenv("ENVIRONMENT") == "production":
    CONCURRENCY_CONFIG.max_workers = 64
    CONCURRENCY_CONFIG.max_concurrent_requests = 200
    CACHE_CONFIG.memory_max_size = 5000
    MEMORY_THRESHOLDS.warning_percent = 60.0
    PERFORMANCE_CONFIG.monitoring_interval = 15

# 测试环境配置
elif os.getenv("ENVIRONMENT") == "test":
    CONCURRENCY_CONFIG.max_workers = 4
    CONCURRENCY_CONFIG.max_concurrent_requests = 10
    CACHE_CONFIG.memory_max_size = 50
    PERFORMANCE_CONFIG.monitoring_enabled = False
    PERFORMANCE_CONFIG.auto_optimization = False