"""
缓存策略模块
提供多级缓存支持和智能缓存管理
"""
import asyncio
import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from pathlib import Path
import threading
from collections import OrderedDict
import weakref

import redis.asyncio as redis
from cachetools import TTLCache, LRUCache, cached

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheConfig:
    """缓存配置"""
    # 内存缓存配置
    memory_max_size: int = 1000
    memory_ttl: int = 300  # 5分钟

    # LRU缓存配置
    lru_max_size: int = 500
    lru_ttl: int = 600  # 10分钟

    # Redis缓存配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ttl: int = 3600  # 1小时

    # 文件缓存配置
    file_cache_dir: str = ".cache"
    file_cache_ttl: int = 86400  # 24小时

    # 缓存策略
    cache_strategy: str = "memory"  # memory, lru, redis, file, multi
    compression_enabled: bool = True
    serialization_method: str = "pickle"  # pickle, json


class CacheKey:
    """缓存键生成器"""

    @staticmethod
    def generate_key(
        prefix: str,
        *args,
        **kwargs
    ) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        args_str = str(args) if args else ""
        kwargs_str = str(sorted(kwargs.items())) if kwargs else ""

        # 生成MD5哈希
        content = f"{prefix}:{args_str}:{kwargs_str}"
        hash_obj = hashlib.md5(content.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"

    @staticmethod
    def generate_from_func(func_name: str, args: tuple, kwargs: dict) -> str:
        """从函数参数生成缓存键"""
        return CacheKey.generate_key(func_name, *args, **kwargs)


class BaseCacheBackend(ABC):
    """缓存后端基类"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        pass


class MemoryCacheBackend(BaseCacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'clears': 0
        }

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            try:
                value = self.cache[key]
                self._stats['hits'] += 1
                return value
            except KeyError:
                self._stats['misses'] += 1
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            self.cache[key] = value
            self._stats['sets'] += 1
            return True

    async def delete(self, key: str) -> bool:
        with self._lock:
            try:
                del self.cache[key]
                self._stats['deletes'] += 1
                return True
            except KeyError:
                return False

    async def clear(self) -> bool:
        with self._lock:
            self.cache.clear()
            self._stats['clears'] += 1
            return True

    async def exists(self, key: str) -> bool:
        with self._lock:
            return key in self.cache

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            **self._stats,
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'hit_rate': hit_rate
        }


class LRUCacheBackend(BaseCacheBackend):
    """LRU缓存后端"""

    def __init__(self, max_size: int = 500, ttl: int = 600):
        self.cache = LRUCache(maxsize=max_size)
        self.ttl = ttl
        self._timestamps = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'clears': 0,
            'expired': 0
        }

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            # 检查是否过期
            if self._is_expired(key):
                await self.delete(key)
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None

            try:
                value = self.cache[key]
                self._stats['hits'] += 1
                return value
            except KeyError:
                self._stats['misses'] += 1
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            self.cache[key] = value
            self._timestamps[key] = time.time() + (ttl or self.ttl)
            self._stats['sets'] += 1
            return True

    async def delete(self, key: str) -> bool:
        with self._lock:
            deleted = False
            try:
                del self.cache[key]
                deleted = True
            except KeyError:
                pass

            try:
                del self._timestamps[key]
            except KeyError:
                pass

            if deleted:
                self._stats['deletes'] += 1
            return deleted

    async def clear(self) -> bool:
        with self._lock:
            self.cache.clear()
            self._timestamps.clear()
            self._stats['clears'] += 1
            return True

    async def exists(self, key: str) -> bool:
        with self._lock:
            return key in self.cache and not self._is_expired(key)

    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        if key not in self._timestamps:
            return True
        return time.time() > self._timestamps[key]

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            **self._stats,
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'hit_rate': hit_rate
        }


class RedisCacheBackend(BaseCacheBackend):
    """Redis缓存后端"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'clears': 0,
            'errors': 0
        }

    async def _get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=False
            )
        return self.redis_client

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = await self._get_client()
            value = await client.get(key)

            if value is None:
                self._stats['misses'] += 1
                return None

            self._stats['hits'] += 1
            return pickle.loads(value)
        except Exception as e:
            logger.error(f"Redis获取缓存失败: {e}")
            self._stats['errors'] += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            client = await self._get_client()
            serialized_value = pickle.dumps(value)
            ttl = ttl or self.config.redis_ttl

            await client.setex(key, ttl, serialized_value)
            self._stats['sets'] += 1
            return True
        except Exception as e:
            logger.error(f"Redis设置缓存失败: {e}")
            self._stats['errors'] += 1
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await client.delete(key)
            if result > 0:
                self._stats['deletes'] += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Redis删除缓存失败: {e}")
            self._stats['errors'] += 1
            return False

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            await client.flushdb()
            self._stats['clears'] += 1
            return True
        except Exception as e:
            logger.error(f"Redis清空缓存失败: {e}")
            self._stats['errors'] += 1
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return bool(await client.exists(key))
        except Exception as e:
            logger.error(f"Redis检查缓存存在性失败: {e}")
            self._stats['errors'] += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        return self._stats

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()


class FileCacheBackend(BaseCacheBackend):
    """文件缓存后端"""

    def __init__(self, cache_dir: str = ".cache", ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'clears': 0,
            'expired': 0
        }
        self._lock = threading.RLock()

    def _get_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用安全的文件名
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self.cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                self._stats['misses'] += 1
                return None

            # 检查是否过期
            if time.time() - file_path.stat().st_mtime > self.ttl:
                await self.delete(key)
                self._stats['expired'] += 1
                self._stats['misses'] += 1
                return None

            try:
                with open(file_path, 'rb') as f:
                    value = pickle.load(f)
                self._stats['hits'] += 1
                return value
            except Exception as e:
                logger.error(f"文件缓存读取失败: {e}")
                await self.delete(key)
                self._stats['misses'] += 1
                return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)

            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(value, f)
                self._stats['sets'] += 1
                return True
            except Exception as e:
                logger.error(f"文件缓存写入失败: {e}")
                return False

    async def delete(self, key: str) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)

            if file_path.exists():
                try:
                    file_path.unlink()
                    self._stats['deletes'] += 1
                    return True
                except Exception as e:
                    logger.error(f"文件缓存删除失败: {e}")
                    return False
            return False

    async def clear(self) -> bool:
        with self._lock:
            try:
                for file_path in self.cache_dir.glob("*.cache"):
                    file_path.unlink()
                self._stats['clears'] += 1
                return True
            except Exception as e:
                logger.error(f"文件缓存清空失败: {e}")
                return False

    async def exists(self, key: str) -> bool:
        with self._lock:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                return False

            # 检查是否过期
            if time.time() - file_path.stat().st_mtime > self.ttl:
                return False

            return True

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            'cache_dir': str(self.cache_dir),
            'file_count': len(list(self.cache_dir.glob("*.cache")))
        }


class MultiLevelCache:
    """多级缓存"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.backends: List[BaseCacheBackend] = []
        self._setup_backends()

    def _setup_backends(self):
        """设置缓存后端"""
        if self.config.cache_strategy == "memory":
            self.backends.append(MemoryCacheBackend(
                self.config.memory_max_size,
                self.config.memory_ttl
            ))
        elif self.config.cache_strategy == "lru":
            self.backends.append(LRUCacheBackend(
                self.config.lru_max_size,
                self.config.lru_ttl
            ))
        elif self.config.cache_strategy == "redis":
            self.backends.append(RedisCacheBackend(self.config))
        elif self.config.cache_strategy == "file":
            self.backends.append(FileCacheBackend(
                self.config.file_cache_dir,
                self.config.file_cache_ttl
            ))
        elif self.config.cache_strategy == "multi":
            # 多级缓存：内存 -> Redis -> 文件
            self.backends.append(MemoryCacheBackend(
                self.config.memory_max_size,
                self.config.memory_ttl
            ))
            self.backends.append(RedisCacheBackend(self.config))
            self.backends.append(FileCacheBackend(
                self.config.file_cache_dir,
                self.config.file_cache_ttl
            ))

    async def get(self, key: str) -> Optional[Any]:
        """从缓存获取值（多级查找）"""
        for i, backend in enumerate(self.backends):
            value = await backend.get(key)
            if value is not None:
                # 将值回填到更高级的缓存
                for j in range(i):
                    await self.backends[j].set(key, value)
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值（所有级别）"""
        success = True
        for backend in self.backends:
            result = await backend.set(key, value, ttl)
            success = success and result
        return success

    async def delete(self, key: str) -> bool:
        """删除缓存值（所有级别）"""
        success = True
        for backend in self.backends:
            result = await backend.delete(key)
            success = success and result
        return success

    async def clear(self) -> bool:
        """清空缓存（所有级别）"""
        success = True
        for backend in self.backends:
            result = await backend.clear()
            success = success and result
        return success

    async def exists(self, key: str) -> bool:
        """检查键是否存在（任一级别）"""
        for backend in self.backends:
            if await backend.exists(key):
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存级别的统计信息"""
        stats = {
            'strategy': self.config.cache_strategy,
            'backends': []
        }

        for i, backend in enumerate(self.backends):
            backend_name = backend.__class__.__name__
            stats['backends'].append({
                'level': i + 1,
                'name': backend_name,
                'stats': backend.get_stats()
            })

        return stats

    async def close(self):
        """关闭缓存后端"""
        for backend in self.backends:
            if hasattr(backend, 'close'):
                await backend.close()


# 全局缓存实例
_cache_manager: Optional[MultiLevelCache] = None


def get_cache_manager(config: Optional[CacheConfig] = None) -> MultiLevelCache:
    """获取全局缓存管理器"""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = MultiLevelCache(
            config or CacheConfig()
        )

    return _cache_manager


async def close_cache_manager():
    """关闭全局缓存管理器"""
    global _cache_manager

    if _cache_manager:
        await _cache_manager.close()
        _cache_manager = None


# 缓存装饰器
def cached(
    ttl: int = 300,
    key_prefix: str = "",
    cache_key_func: Optional[Callable] = None
):
    """缓存装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = CacheKey.generate_from_func(
                    f"{key_prefix}:{func.__name__}",
                    args,
                    kwargs
                )

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# 弱引用缓存（用于对象）
class WeakRefCache:
    """弱引用缓存，自动清理不再被引用的对象"""

    def __init__(self):
        self._cache: Dict[str, weakref.ref] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None

            ref = self._cache[key]
            obj = ref()
            if obj is None:
                del self._cache[key]
                return None

            return obj

    def set(self, key: str, obj: Any):
        with self._lock:
            self._cache[key] = weakref.ref(obj)

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def cleanup(self):
        """清理失效的弱引用"""
        with self._lock:
            keys_to_delete = []
            for key, ref in self._cache.items():
                if ref() is None:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]

    def size(self) -> int:
        with self._lock:
            self.cleanup()
            return len(self._cache)