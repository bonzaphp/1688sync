"""
数据库性能优化模块
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PerformanceManager:
    """性能管理器"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_indexes(self) -> Dict[str, bool]:
        """创建数据库索引"""
        index_definitions = [
            # 供应商表索引
            {
                'name': 'idx_suppliers_source_id',
                'table': 'suppliers',
                'columns': ['source_id'],
                'unique': True
            },
            {
                'name': 'idx_suppliers_location',
                'table': 'suppliers',
                'columns': ['province', 'city']
            },
            {
                'name': 'idx_suppliers_rating',
                'table': 'suppliers',
                'columns': ['rating']
            },
            {
                'name': 'idx_suppliers_business_type',
                'table': 'suppliers',
                'columns': ['business_type']
            },
            {
                'name': 'idx_suppliers_verified',
                'table': 'suppliers',
                'columns': ['is_verified']
            },
            {
                'name': 'idx_suppliers_product_count',
                'table': 'suppliers',
                'columns': ['product_count']
            },

            # 商品表索引
            {
                'name': 'idx_products_source_id',
                'table': 'products',
                'columns': ['source_id'],
                'unique': True
            },
            {
                'name': 'idx_products_supplier_id',
                'table': 'products',
                'columns': ['supplier_id']
            },
            {
                'name': 'idx_products_category',
                'table': 'products',
                'columns': ['category_id']
            },
            {
                'name': 'idx_products_price_range',
                'table': 'products',
                'columns': ['price_min', 'price_max']
            },
            {
                'name': 'idx_products_sales',
                'table': 'products',
                'columns': ['sales_count']
            },
            {
                'name': 'idx_products_rating',
                'table': 'products',
                'columns': ['rating']
            },
            {
                'name': 'idx_products_status',
                'table': 'products',
                'columns': ['status']
            },
            {
                'name': 'idx_products_sync_status',
                'table': 'products',
                'columns': ['sync_status']
            },
            {
                'name': 'idx_products_title_gin',
                'table': 'products',
                'columns': ['title'],
                'index_type': 'gin'
            },

            # 商品图片表索引
            {
                'name': 'idx_product_images_product_id',
                'table': 'product_images',
                'columns': ['product_id']
            },
            {
                'name': 'idx_product_images_type',
                'table': 'product_images',
                'columns': ['image_type']
            },
            {
                'name': 'idx_product_images_download_status',
                'table': 'product_images',
                'columns': ['download_status']
            },
            {
                'name': 'idx_product_images_process_status',
                'table': 'product_images',
                'columns': ['process_status']
            },
            {
                'name': 'idx_product_images_sort_order',
                'table': 'product_images',
                'columns': ['sort_order']
            },
            {
                'name': 'idx_product_images_url_hash',
                'table': 'product_images',
                'columns': ['url']
            },

            # 同步记录表索引
            {
                'name': 'idx_sync_records_task_id',
                'table': 'sync_records',
                'columns': ['task_id']
            },
            {
                'name': 'idx_sync_records_operation_type',
                'table': 'sync_records',
                'columns': ['operation_type']
            },
            {
                'name': 'idx_sync_records_status',
                'table': 'sync_records',
                'columns': ['status']
            },
            {
                'name': 'idx_sync_records_start_time',
                'table': 'sync_records',
                'columns': ['start_time']
            },
            {
                'name': 'idx_sync_records_sync_type',
                'table': 'sync_records',
                'columns': ['sync_type']
            },
            {
                'name': 'idx_sync_records_progress',
                'table': 'sync_records',
                'columns': ['progress']
            },

            # 通用软删除索引
            {
                'name': 'idx_suppliers_deleted',
                'table': 'suppliers',
                'columns': ['is_deleted']
            },
            {
                'name': 'idx_products_deleted',
                'table': 'products',
                'columns': ['is_deleted']
            },
            {
                'name': 'idx_product_images_deleted',
                'table': 'product_images',
                'columns': ['is_deleted']
            },

            # 复合索引
            {
                'name': 'idx_products_supplier_status',
                'table': 'products',
                'columns': ['supplier_id', 'status']
            },
            {
                'name': 'idx_products_category_status',
                'table': 'products',
                'columns': ['category_id', 'status']
            },
            {
                'name': 'idx_products_sync_status_updated',
                'table': 'products',
                'columns': ['sync_status', 'updated_at']
            },
            {
                'name': 'idx_images_product_type_status',
                'table': 'product_images',
                'columns': ['product_id', 'image_type', 'download_status']
            },
        ]

        results = {}

        for index_def in index_definitions:
            try:
                success = await self._create_single_index(index_def)
                results[index_def['name']] = success
                if success:
                    logger.info(f"创建索引成功: {index_def['name']}")
                else:
                    logger.warning(f"创建索引失败或已存在: {index_def['name']}")
            except Exception as e:
                logger.error(f"创建索引异常 {index_def['name']}: {e}")
                results[index_def['name']] = False

        return results

    async def _create_single_index(self, index_def: Dict) -> bool:
        """创建单个索引"""
        try:
            # 检查索引是否已存在
            check_stmt = text("""
                SELECT COUNT(*) as count
                FROM pg_indexes
                WHERE indexname = :index_name
            """)
            result = await self.session.execute(check_stmt, {'index_name': index_def['name']})
            if result.scalar() > 0:
                logger.debug(f"索引已存在: {index_def['name']}")
                return True

            # 构建创建索引的SQL
            columns_str = ', '.join(index_def['columns'])
            unique_str = 'UNIQUE ' if index_def.get('unique', False) else ''
            index_type_str = f"USING {index_def['index_type']} " if index_def.get('index_type') else ''

            create_sql = f"""
                CREATE {unique_str}INDEX CONCURRENTLY {index_def['name']}
                {index_type_str}
                ON {index_def['table']} ({columns_str})
            """

            # 对于GIN索引，需要特殊处理
            if index_def.get('index_type') == 'gin':
                create_sql = f"""
                    CREATE INDEX CONCURRENTLY {index_def['name']}
                    ON {index_def['table']} USING gin (to_tsvector('chinese', {index_def['columns'][0]}))
                """

            await self.session.execute(text(create_sql))
            await self.session.commit()
            return True

        except Exception as e:
            logger.error(f"创建索引失败 {index_def['name']}: {e}")
            await self.session.rollback()
            return False

    async def analyze_tables(self) -> Dict[str, bool]:
        """分析表统计信息"""
        tables = ['suppliers', 'products', 'product_images', 'sync_records']
        results = {}

        for table in tables:
            try:
                await self.session.execute(text(f"ANALYZE {table}"))
                results[table] = True
                logger.info(f"分析表统计信息成功: {table}")
            except Exception as e:
                logger.error(f"分析表统计信息失败 {table}: {e}")
                results[table] = False

        return results

    async def vacuum_tables(self) -> Dict[str, bool]:
        """清理表空间"""
        tables = ['suppliers', 'products', 'product_images', 'sync_records']
        results = {}

        for table in tables:
            try:
                await self.session.execute(text(f"VACUUM ANALYZE {table}"))
                results[table] = True
                logger.info(f"清理表空间成功: {table}")
            except Exception as e:
                logger.error(f"清理表空间失败 {table}: {e}")
                results[table] = False

        return results

    async def get_table_statistics(self) -> Dict:
        """获取表统计信息"""
        try:
            stats_query = text("""
                SELECT
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats
                WHERE schemaname = 'public'
                AND tablename IN ('suppliers', 'products', 'product_images', 'sync_records')
                ORDER BY tablename, attname
            """)
            result = await self.session.execute(stats_query)
            rows = result.all()

            # 组织数据
            table_stats = {}
            for row in rows:
                if row.tablename not in table_stats:
                    table_stats[row.tablename] = []
                table_stats[row.tablename].append({
                    'column': row.attname,
                    'distinct_values': row.n_distinct,
                    'correlation': row.correlation
                })

            return table_stats

        except Exception as e:
            logger.error(f"获取表统计信息失败: {e}")
            return {}

    async def get_index_usage(self) -> List[Dict]:
        """获取索引使用情况"""
        try:
            usage_query = text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
            """)
            result = await self.session.execute(usage_query)
            rows = result.all()

            return [
                {
                    'schema': row.schemaname,
                    'table': row.tablename,
                    'index': row.indexname,
                    'scans': row.idx_scan,
                    'tuples_read': row.idx_tup_read,
                    'tuples_fetched': row.idx_tup_fetch
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"获取索引使用情况失败: {e}")
            return []

    async def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """获取慢查询（需要pg_stat_statements扩展）"""
        try:
            # 首先检查扩展是否存在
            check_ext = text("""
                SELECT COUNT(*) as count
                FROM pg_extension
                WHERE extname = 'pg_stat_statements'
            """)
            result = await self.session.execute(check_ext)
            if result.scalar() == 0:
                logger.warning("pg_stat_statements 扩展未安装")
                return []

            slow_query_sql = text("""
                SELECT
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > 1000  -- 超过1秒的查询
                ORDER BY mean_exec_time DESC
                LIMIT :limit
            """)
            result = await self.session.execute(slow_query_sql, {'limit': limit})
            rows = result.all()

            return [
                {
                    'query': row.query[:200] + '...' if len(row.query) > 200 else row.query,
                    'calls': row.calls,
                    'total_time_ms': row.total_exec_time,
                    'avg_time_ms': row.mean_exec_time,
                    'rows_returned': row.rows
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"获取慢查询失败: {e}")
            return []

    async def optimize_database(self) -> Dict:
        """综合数据库优化"""
        try:
            results = {
                'indexes': {},
                'table_analysis': {},
                'vacuum': {},
                'statistics': {},
                'index_usage': [],
                'slow_queries': []
            }

            # 1. 创建索引
            logger.info("开始创建数据库索引...")
            results['indexes'] = await self.create_indexes()

            # 2. 分析表统计信息
            logger.info("开始分析表统计信息...")
            results['table_analysis'] = await self.analyze_tables()

            # 3. 清理表空间（可选，在生产环境中谨慎使用）
            logger.info("开始清理表空间...")
            results['vacuum'] = await self.vacuum_tables()

            # 4. 获取统计信息
            logger.info("收集表和索引统计信息...")
            results['statistics'] = await self.get_table_statistics()
            results['index_usage'] = await self.get_index_usage()
            results['slow_queries'] = await self.get_slow_queries()

            logger.info("数据库优化完成")
            return {
                'status': 'completed',
                'results': results
            }

        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def create_partitioned_tables(self) -> Dict[str, bool]:
        """创建分区表（针对大表）"""
        try:
            # 为同步记录表创建按月分区
            partition_sql = text("""
                -- 创建分区表（如果不存在）
                CREATE TABLE IF NOT EXISTS sync_records_partitioned (
                    LIKE sync_records INCLUDING ALL
                ) PARTITION BY RANGE (start_time);

                -- 创建未来几个月的分区
                DO $$
                DECLARE
                    start_date date;
                    end_date date;
                    partition_name text;
                BEGIN
                    FOR i IN 0..11 LOOP
                        start_date := date_trunc('month', CURRENT_DATE + interval '1 month' * i);
                        end_date := start_date + interval '1 month';
                        partition_name := 'sync_records_' || to_char(start_date, 'YYYY_MM');

                        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF sync_records_partitioned
                                      FOR VALUES FROM (%L) TO (%L)',
                                      partition_name, start_date, end_date);
                    END LOOP;
                END $$;
            """)

            await self.session.execute(partition_sql)
            await self.session.commit()

            logger.info("分区表创建成功")
            return {'sync_records_partitioned': True}

        except Exception as e:
            logger.error(f"创建分区表失败: {e}")
            await self.session.rollback()
            return {'sync_records_partitioned': False}

    async def monitor_performance_metrics(self) -> Dict:
        """监控性能指标"""
        try:
            metrics = {}

            # 连接数统计
            connection_query = text("""
                SELECT count(*) as total_connections
                FROM pg_stat_activity
                WHERE state = 'active'
            """)
            result = await self.session.execute(connection_query)
            metrics['active_connections'] = result.scalar()

            # 数据库大小
            size_query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as database_size
            """)
            result = await self.session.execute(size_query)
            metrics['database_size'] = result.scalar()

            # 表大小统计
            table_size_query = text("""
                SELECT
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('suppliers', 'products', 'product_images', 'sync_records')
                ORDER BY size_bytes DESC
            """)
            result = await self.session.execute(table_size_query)
            metrics['table_sizes'] = [
                {
                    'table': row.tablename,
                    'size': row.size,
                    'size_bytes': row.size_bytes
                }
                for row in result
            ]

            # 缓存命中率
            cache_query = text("""
                SELECT
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100 as ratio
                FROM pg_statio_user_tables
            """)
            result = await self.session.execute(cache_query)
            cache_stats = result.first()
            metrics['cache_hit_ratio'] = round(cache_stats.ratio or 0, 2)

            return metrics

        except Exception as e:
            logger.error(f"获取性能指标失败: {e}")
            return {}