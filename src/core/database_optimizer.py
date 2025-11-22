"""
数据库查询优化模块
提供查询优化、连接池管理、索引建议等功能
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import text, func, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select
from sqlalchemy.pool import QueuePool

from src.database.connection import db_manager

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """查询统计信息"""
    query: str
    execution_time: float
    rows_affected: int
    timestamp: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class IndexRecommendation:
    """索引建议"""
    table_name: str
    column_names: List[str]
    index_type: str  # btree, hash, gin, gist
    estimated_improvement: float
    reason: str


class QueryOptimizer:
    """查询优化器"""

    def __init__(self):
        self.query_history: List[QueryStats] = []
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.max_history_size = 1000
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def optimized_query(
        self,
        session: AsyncSession,
        query: Union[str, Select],
        params: Optional[Dict] = None,
        use_cache: bool = True,
        timeout: Optional[float] = None
    ):
        """优化查询执行上下文管理器"""
        start_time = time.time()
        query_str = str(query) if not isinstance(query, str) else query

        try:
            # 执行查询
            if timeout:
                result = await asyncio.wait_for(
                    session.execute(query, params or {}),
                    timeout=timeout
                )
            else:
                result = await session.execute(query, params or {})

            execution_time = time.time() - start_time
            rows_affected = result.rowcount if hasattr(result, 'rowcount') else 0

            # 记录查询统计
            stats = QueryStats(
                query=query_str,
                execution_time=execution_time,
                rows_affected=rows_affected,
                timestamp=time.time(),
                success=True
            )
            await self._record_query(stats)

            # 检查慢查询
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"检测到慢查询: 执行时间 {execution_time:.3f}s, "
                    f"SQL: {query_str[:200]}..."
                )

            yield result

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)

            # 记录失败查询
            stats = QueryStats(
                query=query_str,
                execution_time=execution_time,
                rows_affected=0,
                timestamp=time.time(),
                success=False,
                error_message=error_message
            )
            await self._record_query(stats)

            logger.error(f"查询执行失败: {error_message}, SQL: {query_str[:200]}...")
            raise

    async def _record_query(self, stats: QueryStats):
        """记录查询统计"""
        async with self._lock:
            self.query_history.append(stats)

            # 限制历史记录大小
            if len(self.query_history) > self.max_history_size:
                self.query_history = self.query_history[-self.max_history_size:]

    def get_slow_queries(self, limit: int = 10) -> List[QueryStats]:
        """获取慢查询列表"""
        slow_queries = [
            stats for stats in self.query_history
            if stats.execution_time > self.slow_query_threshold
        ]
        return sorted(slow_queries, key=lambda x: x.execution_time, reverse=True)[:limit]

    def get_failed_queries(self, limit: int = 10) -> List[QueryStats]:
        """获取失败查询列表"""
        failed_queries = [stats for stats in self.query_history if not stats.success]
        return sorted(failed_queries, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_query_stats_summary(self) -> Dict[str, Any]:
        """获取查询统计摘要"""
        if not self.query_history:
            return {}

        total_queries = len(self.query_history)
        successful_queries = sum(1 for stats in self.query_history if stats.success)
        failed_queries = total_queries - successful_queries

        execution_times = [stats.execution_time for stats in self.query_history if stats.success]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        max_execution_time = max(execution_times) if execution_times else 0

        return {
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'failed_queries': failed_queries,
            'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
            'avg_execution_time': avg_execution_time,
            'max_execution_time': max_execution_time,
            'slow_query_count': len(self.get_slow_queries()),
            'slow_query_threshold': self.slow_query_threshold
        }


class IndexAnalyzer:
    """索引分析器"""

    def __init__(self):
        self.query_optimizer = QueryOptimizer()

    async def analyze_missing_indexes(self, session: AsyncSession) -> List[IndexRecommendation]:
        """分析缺失的索引"""
        recommendations = []

        # 获取慢查询
        slow_queries = self.query_optimizer.get_slow_queries()

        # 分析WHERE子句中的列
        for query_stats in slow_queries:
            try:
                # 简单的SQL解析，提取WHERE子句中的列
                where_columns = self._extract_where_columns(query_stats.query)
                table_name = self._extract_table_name(query_stats.query)

                if table_name and where_columns:
                    recommendation = IndexRecommendation(
                        table_name=table_name,
                        column_names=where_columns,
                        index_type="btree",
                        estimated_improvement=min(query_stats.execution_time * 0.5, 5.0),
                        reason=f"慢查询中频繁使用WHERE条件: {', '.join(where_columns)}"
                    )
                    recommendations.append(recommendation)

            except Exception as e:
                logger.warning(f"分析查询索引失败: {e}")

        # 去重
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        return sorted(unique_recommendations, key=lambda x: x.estimated_improvement, reverse=True)

    def _extract_where_columns(self, query: str) -> List[str]:
        """从SQL查询中提取WHERE子句中的列"""
        # 简单的字符串解析，实际应用中可能需要更复杂的SQL解析器
        columns = []
        query_upper = query.upper()

        if 'WHERE' in query_upper:
            where_part = query_upper.split('WHERE')[1].split('ORDER BY')[0].split('GROUP BY')[0]
            # 简单提取列名（实际应用中需要更精确的解析）
            import re
            matches = re.findall(r'(\w+)\s*=', where_part)
            columns = [col for col in matches if col not in ['AND', 'OR']]

        return columns[:3]  # 最多返回3列

    def _extract_table_name(self, query: str) -> Optional[str]:
        """从SQL查询中提取表名"""
        query_upper = query.upper()
        if 'FROM' in query_upper:
            from_part = query_upper.split('FROM')[1].split()[0]
            return from_part.strip('"').strip("'")
        return None

    def _deduplicate_recommendations(
        self,
        recommendations: List[IndexRecommendation]
    ) -> List[IndexRecommendation]:
        """去重索引建议"""
        seen = set()
        unique_recommendations = []

        for rec in recommendations:
            key = (rec.table_name, tuple(rec.column_names))
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)

        return unique_recommendations


class ConnectionPoolOptimizer:
    """连接池优化器"""

    def __init__(self):
        self.pool_stats = {}

    async def analyze_pool_performance(self) -> Dict[str, Any]:
        """分析连接池性能"""
        try:
            async with db_manager.get_session() as session:
                # 获取连接池状态
                pool = db_manager.engine.pool

                pool_info = {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                }

                # 计算连接池利用率
                utilization = pool_info['checked_out'] / (pool_info['pool_size'] + pool_info['overflow'])
                pool_info['utilization'] = utilization

                # 性能建议
                recommendations = []
                if utilization > 0.8:
                    recommendations.append("连接池利用率过高，建议增加连接池大小")
                elif utilization < 0.2:
                    recommendations.append("连接池利用率过低，可以减少连接池大小")

                if pool_info['overflow'] > 0:
                    recommendations.append("检测到连接池溢出，建议增加max_overflow")

                return {
                    'pool_info': pool_info,
                    'recommendations': recommendations,
                    'engine_info': {
                        'driver': db_manager.engine.driver,
                        'dialect': db_manager.engine.dialect.name,
                        'pool_class': pool.__class__.__name__
                    }
                }

        except Exception as e:
            logger.error(f"分析连接池性能失败: {e}")
            return {'error': str(e)}

    async def optimize_pool_settings(self) -> Dict[str, Any]:
        """优化连接池设置"""
        current_stats = await self.analyze_pool_performance()
        recommendations = []

        if 'error' in current_stats:
            return current_stats

        pool_info = current_stats['pool_info']

        # 基于当前使用情况建议优化
        optimal_pool_size = pool_info['pool_size']
        optimal_max_overflow = db_manager.engine.pool._max_overflow

        if pool_info['utilization'] > 0.9:
            optimal_pool_size = min(pool_info['pool_size'] * 2, 50)
            optimal_max_overflow = min(optimal_max_overflow * 2, 20)
        elif pool_info['utilization'] < 0.3:
            optimal_pool_size = max(pool_info['pool_size'] // 2, 5)

        return {
            'current_settings': {
                'pool_size': pool_info['pool_size'],
                'max_overflow': db_manager.engine.pool._max_overflow,
                'pool_timeout': db_manager.engine.pool._timeout,
                'pool_recycle': db_manager.engine.pool._recycle
            },
            'recommended_settings': {
                'pool_size': optimal_pool_size,
                'max_overflow': optimal_max_overflow
            },
            'reasoning': current_stats['recommendations']
        }


class QueryCache:
    """查询结果缓存"""

    def __init__(self, max_size: int = 100, ttl: int = 300):
        from cachetools import TTLCache
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = asyncio.Lock()

    def _generate_cache_key(self, query: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        import hashlib
        content = f"{query}:{str(sorted(params.items()) if params else '')}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get(self, query: str, params: Optional[Dict] = None) -> Optional[Any]:
        """获取缓存的查询结果"""
        cache_key = self._generate_cache_key(query, params)

        async with self._lock:
            return self.cache.get(cache_key)

    async def set(self, query: str, params: Optional[Dict], result: Any) -> None:
        """缓存查询结果"""
        cache_key = self._generate_cache_key(query, params)

        async with self._lock:
            self.cache[cache_key] = result

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'size': len(self.cache),
            'max_size': self.cache.maxsize,
            'curr_size': self.cache.currsize,
            'ttl': self.cache.ttl
        }


class DatabaseOptimizer:
    """数据库优化器主类"""

    def __init__(self):
        self.query_optimizer = QueryOptimizer()
        self.index_analyzer = IndexAnalyzer()
        self.pool_optimizer = ConnectionPoolOptimizer()
        self.query_cache = QueryCache()

    @asynccontextmanager
    async def optimized_session(self):
        """优化的数据库会话上下文"""
        async with db_manager.get_session() as session:
            yield session

    async def execute_optimized_query(
        self,
        query: Union[str, Select],
        params: Optional[Dict] = None,
        use_cache: bool = True,
        timeout: Optional[float] = None
    ):
        """执行优化的查询"""
        query_str = str(query) if not isinstance(query, str) else query

        # 尝试从缓存获取结果
        if use_cache and isinstance(query, str):
            cached_result = await self.query_cache.get(query_str, params)
            if cached_result is not None:
                logger.debug(f"查询命中缓存: {query_str[:100]}...")
                return cached_result

        # 执行查询
        async with db_manager.get_session() as session:
            async with self.query_optimizer.optimized_query(
                session, query, params, timeout=timeout
            ) as result:
                result_data = result.fetchall() if hasattr(result, 'fetchall') else result

                # 缓存结果
                if use_cache and isinstance(query, str):
                    await self.query_cache.set(query_str, params, result_data)

                return result_data

    async def batch_insert(
        self,
        model_class,
        data: List[Dict],
        batch_size: int = 1000,
        return_results: bool = False
    ):
        """批量插入优化"""
        inserted_results = []

        async with db_manager.get_session() as session:
            # 分批处理
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]

                try:
                    # 使用bulk_insert_mappings进行批量插入
                    await session.execute(
                        model_class.__table__.insert(),
                        batch
                    )
                    await session.commit()

                    logger.info(f"批量插入成功: {len(batch)} 条记录")

                    if return_results:
                        # 获取插入的结果（如果需要）
                        inserted_results.extend(batch)

                except Exception as e:
                    await session.rollback()
                    logger.error(f"批量插入失败: {e}")
                    raise

        return inserted_results

    async def analyze_performance(self) -> Dict[str, Any]:
        """分析数据库性能"""
        performance_report = {
            'query_stats': self.query_optimizer.get_query_stats_summary(),
            'slow_queries': [stats.__dict__ for stats in self.query_optimizer.get_slow_queries(5)],
            'failed_queries': [stats.__dict__ for stats in self.query_optimizer.get_failed_queries(5)],
            'pool_performance': await self.pool_optimizer.analyze_pool_performance(),
            'query_cache_stats': self.query_cache.get_stats()
        }

        # 获取索引建议
        try:
            async with db_manager.get_session() as session:
                index_recommendations = await self.index_analyzer.analyze_missing_indexes(session)
                performance_report['index_recommendations'] = [
                    {
                        'table': rec.table_name,
                        'columns': rec.column_names,
                        'type': rec.index_type,
                        'estimated_improvement': rec.estimated_improvement,
                        'reason': rec.reason
                    }
                    for rec in index_recommendations[:5]
                ]
        except Exception as e:
            logger.warning(f"获取索引建议失败: {e}")

        return performance_report

    async def apply_optimizations(self) -> Dict[str, Any]:
        """应用数据库优化建议"""
        optimization_results = {
            'applied_optimizations': [],
            'errors': []
        }

        try:
            # 优化连接池设置
            pool_recommendations = await self.pool_optimizer.optimize_pool_settings()
            optimization_results['pool_optimization'] = pool_recommendations

            logger.info("数据库优化分析完成")
            logger.info(f"查询统计: {self.query_optimizer.get_query_stats_summary()}")
            logger.info(f"连接池状态: {pool_recommendations['current_settings']}")

        except Exception as e:
            optimization_results['errors'].append(str(e))
            logger.error(f"应用数据库优化失败: {e}")

        return optimization_results

    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")


# 全局数据库优化器实例
_db_optimizer: Optional[DatabaseOptimizer] = None


def get_database_optimizer() -> DatabaseOptimizer:
    """获取全局数据库优化器"""
    global _db_optimizer

    if _db_optimizer is None:
        _db_optimizer = DatabaseOptimizer()

    return _db_optimizer


# 便捷函数
async def execute_query(query: Union[str, Select], params: Optional[Dict] = None):
    """执行优化查询的便捷函数"""
    optimizer = get_database_optimizer()
    return await optimizer.execute_optimized_query(query, params)


async def batch_insert_data(model_class, data: List[Dict], batch_size: int = 1000):
    """批量插入数据的便捷函数"""
    optimizer = get_database_optimizer()
    return await optimizer.batch_insert(model_class, data, batch_size)