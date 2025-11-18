"""
数据库连接管理模块
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql import text

from config.database import db_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._is_initialized = False

    @property
    def engine(self):
        """获取数据库引擎"""
        if self._engine is None:
            raise RuntimeError("数据库引擎未初始化，请先调用 initialize() 方法")
        return self._engine

    @property
    def session_factory(self):
        """获取会话工厂"""
        if self._session_factory is None:
            raise RuntimeError("会话工厂未初始化，请先调用 initialize() 方法")
        return self._session_factory

    async def initialize(self, test_mode: bool = False):
        """初始化数据库连接"""
        if self._is_initialized:
            logger.warning("数据库连接已经初始化")
            return

        try:
            # 创建数据库引擎
            self._engine = create_async_engine(
                db_settings.database_url,
                # 连接池配置
                poolclass=QueuePool,
                pool_size=db_settings.pool_size,
                max_overflow=db_settings.max_overflow,
                pool_timeout=db_settings.pool_timeout,
                pool_recycle=db_settings.pool_recycle,
                pool_pre_ping=db_settings.pool_pre_ping,
                # 测试模式配置
                poolclass=NullPool if test_mode else QueuePool,
                # 连接选项
                echo=db_settings.echo,
                echo_pool=db_settings.echo_pool,
                future=db_settings.future,
                # 连接参数
                connect_args={
                    "command_timeout": 60,
                    "timeout": 60,
                    "server_settings": {
                        "application_name": "1688sync",
                        "jit": "off",  # 关闭JIT提升简单查询性能
                    }
                }
            )

            # 创建会话工厂
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )

            # 注册事件监听器
            self._register_event_listeners()

            # 测试连接
            await self._test_connection()

            self._is_initialized = True
            logger.info("数据库连接初始化成功")

        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    def _register_event_listeners(self):
        """注册事件监听器"""

        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """连接建立时的回调"""
            logger.debug("数据库连接已建立")

        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """从连接池获取连接时的回调"""
            logger.debug("从连接池获取连接")

        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接归还到连接池时的回调"""
            logger.debug("连接归还到连接池")

        @event.listens_for(self._engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """连接失效时的回调"""
            logger.warning(f"数据库连接失效: {exception}")

    async def _test_connection(self):
        """测试数据库连接"""
        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
            logger.info("数据库连接测试成功")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器"""
        if not self._is_initialized:
            raise RuntimeError("数据库连接未初始化")

        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_session(self) -> AsyncSession:
        """创建新的数据库会话"""
        if not self._is_initialized:
            raise RuntimeError("数据库连接未初始化")
        return self._session_factory()

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._is_initialized = False
            logger.info("数据库连接已关闭")

    async def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT version()"))
                version = result.scalar()

                # 检查连接池状态
                pool = self._engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }

                return {
                    "status": "healthy",
                    "version": version,
                    "pool": pool_status,
                    "url": str(self._engine.url).replace(self._engine.url.password or "", "***")
                }
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def execute_raw_sql(self, sql: str, params: dict = None):
        """执行原生SQL"""
        async with self.get_session() as session:
            try:
                result = await session.execute(text(sql), params or {})
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"执行SQL失败: {sql}, 错误: {e}")
                raise

    async def get_connection_info(self) -> dict:
        """获取连接信息"""
        if not self._is_initialized:
            return {"status": "not_initialized"}

        return {
            "url": str(self._engine.url).replace(self._engine.url.password or "", "***"),
            "pool_size": db_settings.pool_size,
            "max_overflow": db_settings.max_overflow,
            "pool_timeout": db_settings.pool_timeout,
            "pool_recycle": db_settings.pool_recycle,
            "driver": self._engine.driver,
            "dialect": self._engine.dialect.name,
        }


# 全局数据库管理器实例
db_manager = DatabaseManager()


# 便捷函数
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的便捷函数（用于依赖注入）"""
    async with db_manager.get_session() as session:
        yield session


async def init_database(test_mode: bool = False):
    """初始化数据库的便捷函数"""
    await db_manager.initialize(test_mode)


async def close_database():
    """关闭数据库连接的便捷函数"""
    await db_manager.close()