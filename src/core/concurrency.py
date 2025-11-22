"""
并发控制模块
提供高性能的并发处理和资源管理功能
"""
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, TypeVar, Union
from queue import Queue
from threading import Semaphore, Lock
import multiprocessing as mp

import psutil

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_workers: int = None
    max_concurrent_requests: int = 100
    rate_limit: float = 10.0  # 每秒请求数
    queue_size: int = 1000
    timeout: float = 30.0
    retry_times: int = 3
    backoff_factor: float = 1.0

    def __post_init__(self):
        if self.max_workers is None:
            self.max_workers = min(32, (mp.cpu_count() or 1) + 4)


class RateLimiter:
    """速率限制器"""

    def __init__(self, rate_limit: float):
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.last_call = 0.0
        self._lock = Lock()

    def acquire(self):
        """获取访问许可"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

            self.last_call = time.time()


class AsyncRateLimiter:
    """异步速率限制器"""

    def __init__(self, rate_limit: float):
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取访问许可"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                await asyncio.sleep(sleep_time)

            self.last_call = time.time()


class ConcurrencyController:
    """并发控制器"""

    def __init__(self, config: ConcurrencyConfig):
        self.config = config
        self.semaphore = Semaphore(config.max_concurrent_requests)
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.executor = ThreadPoolExecutor(max_workers=config.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=config.max_workers // 2)
        self._stats = {
            'total_requests': 0,
            'active_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'peak_concurrent': 0
        }
        self._stats_lock = Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """获取并发许可"""
        self.rate_limiter.acquire()
        self.semaphore.acquire()

        with self._stats_lock:
            self._stats['active_requests'] += 1
            self._stats['total_requests'] += 1
            self._stats['peak_concurrent'] = max(
                self._stats['peak_concurrent'],
                self._stats['active_requests']
            )

        try:
            yield
        finally:
            with self._stats_lock:
                self._stats['active_requests'] -= 1
                self._stats['completed_requests'] += 1
            self.semaphore.release()

    async def submit_task(
        self,
        func: Callable[..., T],
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> T:
        """提交任务到线程池"""
        timeout = timeout or self.config.timeout

        async with self.acquire():
            start_time = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: func(*args, **kwargs)
                )

                # 更新响应时间统计
                response_time = time.time() - start_time
                with self._stats_lock:
                    total = self._stats['completed_requests']
                    current_avg = self._stats['avg_response_time']
                    if total > 0:
                        self._stats['avg_response_time'] = (
                            (current_avg * (total - 1) + response_time) / total
                        )
                    else:
                        self._stats['avg_response_time'] = response_time

                return result

            except Exception as e:
                with self._stats_lock:
                    self._stats['failed_requests'] += 1
                logger.error(f"任务执行失败: {e}")
                raise

    async def submit_cpu_task(
        self,
        func: Callable[..., T],
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> T:
        """提交CPU密集型任务到进程池"""
        timeout = timeout or self.config.timeout

        async with self.acquire():
            start_time = time.time()
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.process_executor,
                    lambda: func(*args, **kwargs)
                )

                response_time = time.time() - start_time
                with self._stats_lock:
                    total = self._stats['completed_requests']
                    current_avg = self._stats['avg_response_time']
                    self._stats['avg_response_time'] = (
                        (current_avg * (total - 1) + response_time) / total
                    )

                return result

            except Exception as e:
                with self._stats_lock:
                    self._stats['failed_requests'] += 1
                logger.error(f"CPU任务执行失败: {e}")
                raise

    async def batch_process(
        self,
        tasks: List[Callable[[], T]],
        max_concurrent: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[T]:
        """批量处理任务"""
        max_concurrent = max_concurrent or self.config.max_concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        results = [None] * len(tasks)
        completed = 0

        async def process_task(index: int, task: Callable[[], T]):
            nonlocal completed
            async with semaphore:
                try:
                    result = await self.submit_task(task)
                    results[index] = result
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, len(tasks))

                except Exception as e:
                    logger.error(f"批量任务 {index} 执行失败: {e}")
                    results[index] = e

        # 创建所有任务
        await asyncio.gather(*[
            process_task(i, task) for i, task in enumerate(tasks)
        ])

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()

        # 添加系统资源信息
        stats.update({
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'active_threads': threading.active_count(),
            'config': {
                'max_workers': self.config.max_workers,
                'max_concurrent_requests': self.config.max_concurrent_requests,
                'rate_limit': self.config.rate_limit
            }
        })

        return stats

    def adjust_rate_limit(self, new_rate: float):
        """动态调整速率限制"""
        self.config.rate_limit = new_rate
        self.rate_limiter = RateLimiter(new_rate)
        logger.info(f"速率限制已调整为: {new_rate} 请求/秒")

    def adjust_concurrency(self, new_max: int):
        """动态调整并发数"""
        old_max = self.config.max_concurrent_requests
        self.config.max_concurrent_requests = new_max

        # 重新创建信号量
        self.semaphore = Semaphore(new_max)
        logger.info(f"并发数已调整为: {old_max} -> {new_max}")

    def close(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        logger.info("并发控制器已关闭")


class AsyncTaskQueue:
    """异步任务队列"""

    def __init__(self, max_size: int = 1000):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.workers = []
        self.running = False
        self._stats = {
            'enqueued': 0,
            'dequeued': 0,
            'processed': 0,
            'failed': 0
        }

    async def put(self, task: Callable[[], Any], priority: int = 0):
        """添加任务到队列"""
        await self.queue.put((priority, task))
        self._stats['enqueued'] += 1

    async def get(self) -> Callable[[], Any]:
        """从队列获取任务"""
        priority, task = await self.queue.get()
        self._stats['dequeued'] += 1
        return task

    async def process_tasks(self, worker_count: int = 4):
        """处理队列中的任务"""
        self.running = True

        async def worker():
            while self.running or not self.queue.empty():
                try:
                    task = await asyncio.wait_for(self.get(), timeout=1.0)
                    try:
                        await task()
                        self._stats['processed'] += 1
                    except Exception as e:
                        logger.error(f"队列任务执行失败: {e}")
                        self._stats['failed'] += 1
                except asyncio.TimeoutError:
                    continue

        # 启动工作线程
        self.workers = [asyncio.create_task(worker()) for _ in range(worker_count)]

        # 等待所有工作线程完成
        await asyncio.gather(*self.workers)

    def stop(self):
        """停止队列处理"""
        self.running = False

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        return {
            **self._stats,
            'queue_size': self.queue.qsize(),
            'running': self.running
        }


# 全局并发控制器实例
_concurrency_controller: Optional[ConcurrencyController] = None


def get_concurrency_controller(config: Optional[ConcurrencyConfig] = None) -> ConcurrencyController:
    """获取全局并发控制器"""
    global _concurrency_controller

    if _concurrency_controller is None:
        _concurrency_controller = ConcurrencyController(
            config or ConcurrencyConfig()
        )

    return _concurrency_controller


def close_concurrency_controller():
    """关闭全局并发控制器"""
    global _concurrency_controller

    if _concurrency_controller:
        _concurrency_controller.close()
        _concurrency_controller = None


# 便捷装饰器
def with_concurrency_control(
    max_concurrent: int = 10,
    rate_limit: float = 5.0
):
    """并发控制装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args, **kwargs):
            controller = get_concurrency_controller()
            async with controller.acquire():
                return await controller.submit_task(func, *args, **kwargs)
        return wrapper
    return decorator


# 导入threading模块
import threading