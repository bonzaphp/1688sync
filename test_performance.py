#!/usr/bin/env python3
"""
性能测试脚本
用于验证性能优化模块的功能和效果
"""
import asyncio
import time
import random
import logging
from pathlib import Path

from src.core import (
    initialize_performance_system,
    shutdown_performance_system,
    get_performance_manager,
    optimized_execution
)
from src.core.performance_monitor import performance_monitor
from src.config.performance import PERFORMANCE_CONFIG
from src.core import CacheConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """性能测试套件"""

    def __init__(self):
        self.test_results = {}

    async def setup(self):
        """设置测试环境"""
        logger.info("初始化性能测试环境...")

        # 使用仅内存缓存的配置进行测试
        test_config = PERFORMANCE_CONFIG
        test_config.cache_config = CacheConfig(
            cache_strategy="memory",
            memory_max_size=100,
            memory_ttl=60
        )

        await initialize_performance_system(test_config)
        self.manager = get_performance_manager()

    async def teardown(self):
        """清理测试环境"""
        logger.info("清理性能测试环境...")
        await shutdown_performance_system()

    async def test_concurrency_performance(self):
        """测试并发性能"""
        logger.info("测试并发性能...")

        # 模拟CPU密集型任务
        def cpu_task(n):
            # 计算斐波那契数列
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

        start_time = time.time()
        tasks = []

        # 提交100个并发任务
        for i in range(100):
            task = self.manager.execute_optimized_task(
                cpu_task, 20 + i % 10
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        self.test_results['concurrency'] = {
            'total_tasks': len(tasks),
            'execution_time': end_time - start_time,
            'tasks_per_second': len(tasks) / (end_time - start_time),
            'success_count': len([r for r in results if r is not None])
        }

        logger.info(f"并发测试完成: {len(tasks)} 个任务，耗时 {end_time - start_time:.2f}s")

    async def test_cache_performance(self):
        """测试缓存性能"""
        logger.info("测试缓存性能...")

        # 模拟数据获取函数
        async def get_user_data(user_id):
            # 模拟数据库查询延迟
            await asyncio.sleep(0.1)
            return {"user_id": user_id, "name": f"User {user_id}"}

        # 测试无缓存性能
        start_time = time.time()
        for i in range(50):
            await get_user_data(i % 10)  # 重复请求相同数据
        no_cache_time = time.time() - start_time

        # 测试有缓存性能
        start_time = time.time()
        for i in range(50):
            await self.manager.execute_optimized_task(
                get_user_data, i % 10,
                use_cache=True,
                cache_ttl=60
            )
        with_cache_time = time.time() - start_time

        self.test_results['cache'] = {
            'no_cache_time': no_cache_time,
            'with_cache_time': with_cache_time,
            'improvement_percent': (no_cache_time - with_cache_time) / no_cache_time * 100
        }

        logger.info(f"缓存测试完成: 无缓存 {no_cache_time:.2f}s, 有缓存 {with_cache_time:.2f}s")

    @performance_monitor(endpoint="memory_test")
    async def test_memory_management(self):
        """测试内存管理"""
        logger.info("测试内存管理...")

        # 获取初始内存状态
        initial_stats = self.manager.memory_manager.get_memory_stats()

        # 创建大量对象
        large_data = []
        for i in range(10000):
            large_data.append({
                'id': i,
                'data': 'x' * 1000,  # 1KB数据
                'timestamp': time.time()
            })

        # 获取峰值内存状态
        peak_stats = self.manager.memory_manager.get_memory_stats()

        # 清理数据
        large_data.clear()

        # 强制垃圾回收
        await self.manager.memory_manager.garbage_collect()

        # 获取清理后内存状态
        final_stats = self.manager.memory_manager.get_memory_stats()

        self.test_results['memory'] = {
            'initial_memory_mb': initial_stats.rss_mb,
            'peak_memory_mb': peak_stats.rss_mb,
            'final_memory_mb': final_stats.rss_mb,
            'memory_recovered_mb': peak_stats.rss_mb - final_stats.rss_mb,
            'object_count_change': final_stats.object_count - initial_stats.object_count
        }

        logger.info(f"内存测试完成: 峰值 {peak_stats.rss_mb:.1f}MB, 恢复 {peak_stats.rss_mb - final_stats.rss_mb:.1f}MB")

    @optimized_execution(use_cache=True, cache_ttl=30)
    async def expensive_calculation(self, n):
        """模拟昂贵的计算"""
        await asyncio.sleep(0.05)  # 模拟计算延迟
        return sum(i * i for i in range(n))

    async def test_optimized_execution(self):
        """测试优化执行"""
        logger.info("测试优化执行...")

        # 第一次执行（无缓存）
        start_time = time.time()
        result1 = await self.expensive_calculation(1000)
        first_execution_time = time.time() - start_time

        # 第二次执行（有缓存）
        start_time = time.time()
        result2 = await self.expensive_calculation(1000)
        second_execution_time = time.time() - start_time

        # 验证结果一致性
        results_match = result1 == result2

        self.test_results['optimized_execution'] = {
            'first_execution_time': first_execution_time,
            'second_execution_time': second_execution_time,
            'cache_speedup': first_execution_time / second_execution_time if second_execution_time > 0 else 0,
            'results_match': results_match
        }

        logger.info(f"优化执行测试完成: 首次 {first_execution_time:.3f}s, 缓存 {second_execution_time:.3f}s")

    async def test_performance_monitoring(self):
        """测试性能监控"""
        logger.info("测试性能监控...")

        # 模拟一系列请求
        for i in range(20):
            response_time = random.uniform(0.1, 2.0)
            status_code = 200 if random.random() > 0.1 else 500

            self.manager.performance_monitor.record_request(
                endpoint=f"/api/test/{i % 3}",
                method="GET",
                status_code=status_code,
                response_time=response_time,
                request_size=100,
                response_size=500
            )

        # 获取性能报告
        report = self.manager.performance_monitor.get_performance_report(minutes=1)

        self.test_results['monitoring'] = {
            'total_requests': report.get('requests', {}).get('total_requests', 0),
            'avg_response_time': report.get('response_time', {}).get('mean', 0),
            'success_rate': report.get('requests', {}).get('success_rate', 0),
            'alerts_count': len(report.get('alerts', []))
        }

        logger.info(f"性能监控测试完成: {report.get('requests', {}).get('total_requests', 0)} 个请求")

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始性能测试套件...")

        try:
            await self.setup()

            # 运行各项测试
            await self.test_concurrency_performance()
            await asyncio.sleep(1)  # 间隔

            await self.test_cache_performance()
            await asyncio.sleep(1)

            await self.test_memory_management()
            await asyncio.sleep(1)

            await self.test_optimized_execution()
            await asyncio.sleep(1)

            await self.test_performance_monitoring()

            # 生成测试报告
            await self.generate_test_report()

        finally:
            await self.teardown()

    async def generate_test_report(self):
        """生成测试报告"""
        logger.info("生成性能测试报告...")

        # 获取综合性能统计
        comprehensive_stats = await self.manager.get_comprehensive_stats()

        # 合并测试结果
        full_report = {
            'test_timestamp': time.time(),
            'test_results': self.test_results,
            'comprehensive_stats': comprehensive_stats,
            'performance_config': {
                'concurrency_max_workers': PERFORMANCE_CONFIG.concurrency_config.max_workers,
                'cache_strategy': PERFORMANCE_CONFIG.cache_config.cache_strategy,
                'monitoring_enabled': PERFORMANCE_CONFIG.monitoring_enabled,
                'auto_optimization': PERFORMANCE_CONFIG.auto_optimization
            }
        }

        # 导出报告
        import json
        report_path = Path("performance_test_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"性能测试报告已导出到: {report_path}")

        # 打印摘要
        self.print_test_summary()

    def print_test_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("性能测试摘要")
        print("="*60)

        for test_name, results in self.test_results.items():
            print(f"\n{test_name.upper()}:")
            for key, value in results.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")

        print("\n" + "="*60)


async def main():
    """主函数"""
    test_suite = PerformanceTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())