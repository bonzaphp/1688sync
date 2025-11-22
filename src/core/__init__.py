"""
性能优化核心模块
提供并发控制、缓存策略、数据库优化、内存管理和性能监控功能
"""

# 并发控制
from .concurrency import (
    ConcurrencyController,
    ConcurrencyConfig,
    AsyncTaskQueue,
    get_concurrency_controller,
    close_concurrency_controller,
    with_concurrency_control
)

# 缓存策略
from .cache import (
    CacheConfig,
    CacheKey,
    MultiLevelCache,
    MemoryCacheBackend,
    LRUCacheBackend,
    RedisCacheBackend,
    FileCacheBackend,
    WeakRefCache,
    get_cache_manager,
    close_cache_manager,
    cached
)

# 数据库优化
from .database_optimizer import (
    QueryOptimizer,
    IndexAnalyzer,
    ConnectionPoolOptimizer,
    QueryCache,
    DatabaseOptimizer,
    get_database_optimizer,
    execute_query,
    batch_insert_data
)

# 内存管理
from .memory_manager import (
    MemoryStats,
    MemoryThresholds,
    ObjectTracker,
    MemoryManager,
    MemoryProfiler,
    MemoryLeakDetector,
    get_memory_manager,
    initialize_memory_monitoring,
    shutdown_memory_manager,
    memory_monitor,
    memory_limit
)

# 性能监控
from .performance_monitor import (
    PerformanceMetric,
    RequestMetrics,
    SystemMetrics,
    MetricsCollector,
    SystemMonitor,
    RequestMonitor,
    PerformanceMonitor,
    get_performance_monitor,
    initialize_performance_monitoring,
    shutdown_performance_monitor,
    performance_monitor as perf_monitor_decorator
)

# 性能管理器
from .performance_manager import (
    PerformanceConfig,
    PerformanceManager,
    get_performance_manager,
    initialize_performance_system,
    shutdown_performance_system,
    optimized_execution
)

__version__ = "1.0.0"
__author__ = "perf-specialist"

# 便捷导入
__all__ = [
    # 并发控制
    "ConcurrencyController",
    "ConcurrencyConfig",
    "get_concurrency_controller",
    "with_concurrency_control",

    # 缓存策略
    "CacheConfig",
    "MultiLevelCache",
    "get_cache_manager",
    "cached",

    # 数据库优化
    "DatabaseOptimizer",
    "get_database_optimizer",
    "execute_query",
    "batch_insert_data",

    # 内存管理
    "MemoryManager",
    "get_memory_manager",
    "memory_monitor",
    "memory_limit",

    # 性能监控
    "PerformanceMonitor",
    "get_performance_monitor",
    "perf_monitor_decorator",

    # 性能管理器
    "PerformanceManager",
    "PerformanceConfig",
    "get_performance_manager",
    "initialize_performance_system",
    "shutdown_performance_system",
    "optimized_execution"
]