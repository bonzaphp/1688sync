"""
数据库事务管理模块
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from .connection import db_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionManager:
    """事务管理器"""

    @staticmethod
    @asynccontextmanager
    async def transaction(
        session: AsyncSession,
        isolation_level: Optional[str] = None,
        readonly: bool = False,
        deferrable: bool = False
    ):
        """事务上下文管理器"""
        # 设置事务隔离级别
        transaction_options = {}
        if isolation_level:
            transaction_options['isolation_level'] = isolation_level
        if readonly:
            transaction_options['readonly'] = readonly
        if deferrable:
            transaction_options['deferrable'] = deferrable

        # 开始事务
        transaction = await session.begin(**transaction_options)
        try:
            yield session
            await transaction.commit()
            logger.debug("事务提交成功")
        except Exception as e:
            await transaction.rollback()
            logger.error(f"事务回滚: {e}")
            raise

    @staticmethod
    async def execute_in_transaction(
        func: Callable,
        *args,
        session: Optional[AsyncSession] = None,
        isolation_level: Optional[str] = None,
        readonly: bool = False,
        **kwargs
    ) -> Any:
        """在事务中执行函数"""
        if session is None:
            async with db_manager.get_session() as new_session:
                async with TransactionManager.transaction(
                    new_session, isolation_level, readonly
                ):
                    return await func(new_session, *args, **kwargs)
        else:
            async with TransactionManager.transaction(
                session, isolation_level, readonly
            ):
                return await func(session, *args, **kwargs)


def transactional(
    isolation_level: Optional[str] = None,
    readonly: bool = False,
    deferrable: bool = False,
    retries: int = 3,
    retry_delay: float = 1.0
):
    """事务装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    async with db_manager.get_session() as session:
                        async with TransactionManager.transaction(
                            session, isolation_level, readonly, deferrable
                        ):
                            # 将session注入到函数参数中
                            if 'session' in func.__code__.co_varnames:
                                kwargs['session'] = session
                            return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(
                            f"事务执行失败，正在重试 ({attempt + 1}/{retries}): {e}"
                        )
                        await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
                    else:
                        logger.error(f"事务执行最终失败: {e}")
                        raise

            # 这里不应该到达，但为了类型检查
            raise last_exception

        return wrapper
    return decorator


class BatchOperation:
    """批量操作管理器"""

    def __init__(self, session: AsyncSession, batch_size: int = 1000):
        self.session = session
        self.batch_size = batch_size
        self.pending_operations: List[Callable] = []
        self.total_processed = 0

    async def add_operation(self, operation: Callable):
        """添加操作到批次"""
        self.pending_operations.append(operation)

        if len(self.pending_operations) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """执行当前批次的所有操作"""
        if not self.pending_operations:
            return

        try:
            # 执行所有待处理操作
            for operation in self.pending_operations:
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    operation()

            await self.session.flush()
            self.total_processed += len(self.pending_operations)
            self.pending_operations.clear()

            logger.debug(f"批次执行完成，已处理 {self.total_processed} 条记录")

        except Exception as e:
            logger.error(f"批次执行失败: {e}")
            await self.session.rollback()
            raise

    async def commit(self):
        """提交所有剩余操作"""
        await self.flush()
        await self.session.commit()
        logger.info(f"批量操作完成，总计处理 {self.total_processed} 条记录")


class LockManager:
    """数据库锁管理器"""

    @staticmethod
    async def acquire_advisory_lock(
        session: AsyncSession,
        lock_key: int,
        timeout: int = 30
    ) -> bool:
        """获取咨询锁"""
        try:
            result = await session.execute(
                text("SELECT pg_advisory_lock(:key)"),
                {"key": lock_key}
            )
            logger.debug(f"获取咨询锁成功: {lock_key}")
            return True
        except Exception as e:
            logger.error(f"获取咨询锁失败: {e}")
            return False

    @staticmethod
    async def release_advisory_lock(
        session: AsyncSession,
        lock_key: int
    ) -> bool:
        """释放咨询锁"""
        try:
            result = await session.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": lock_key}
            )
            logger.debug(f"释放咨询锁成功: {lock_key}")
            return True
        except Exception as e:
            logger.error(f"释放咨询锁失败: {e}")
            return False

    @staticmethod
    @asynccontextmanager
    async def advisory_lock(
        session: AsyncSession,
        lock_key: int,
        timeout: int = 30
    ):
        """咨询锁上下文管理器"""
        if await LockManager.acquire_advisory_lock(session, lock_key, timeout):
            try:
                yield
            finally:
                await LockManager.release_advisory_lock(session, lock_key)
        else:
            raise TimeoutError(f"无法获取咨询锁: {lock_key}")


class RetryManager:
    """重试管理器"""

    @staticmethod
    async def execute_with_retry(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """带重试的执行函数"""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func()
                else:
                    return func()
            except exceptions as e:
                last_exception = e

                if attempt < max_retries:
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    logger.warning(
                        f"执行失败，正在重试 ({attempt + 1}/{max_retries}): {e}, "
                        f"等待 {delay:.2f} 秒"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"执行最终失败: {e}")
                    raise

        raise last_exception


# 便捷函数
@asynccontextmanager
async def db_transaction(
    isolation_level: Optional[str] = None,
    readonly: bool = False
):
    """数据库事务便捷上下文管理器"""
    async with db_manager.get_session() as session:
        async with TransactionManager.transaction(session, isolation_level, readonly):
            yield session