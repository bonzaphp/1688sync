"""
监控集成示例 - 展示如何在现有模块中使用监控系统
"""

import time
import random
from datetime import datetime

from .integration import (
    monitor_execution, monitor_api_request, monitor_database_operation,
    monitor_task_execution, monitor_queue_operation, MonitoringContext,
    track_business_metric, track_user_action, PerformanceProfiler
)
from .logger import get_logger
from .monitor import increment_counter, set_gauge

logger = get_logger(__name__)


# 示例1: 监控普通函数
@monitor_execution(metric_name="data_processing", log_args=True)
def process_data(data_size: int) -> int:
    """处理数据示例"""
    logger.info(f"开始处理 {data_size} 条数据")

    # 模拟数据处理
    for i in range(data_size):
        time.sleep(0.001)  # 模拟处理时间
        if random.random() < 0.01:  # 1%的错误率
            raise ValueError(f"处理第 {i} 条数据时出错")

    return data_size


# 示例2: 监控API端点
@monitor_api_request(endpoint="/api/products", method="GET")
def get_products(page: int = 1, limit: int = 10) -> dict:
    """获取商品列表API示例"""
    logger.info(f"获取商品列表: page={page}, limit={limit}")

    # 模拟API延迟
    time.sleep(random.uniform(0.1, 0.5))

    # 模拟偶尔的错误
    if random.random() < 0.05:
        raise Exception("数据库连接失败")

    return {
        "page": page,
        "limit": limit,
        "total": 100,
        "items": [f"product_{i}" for i in range(limit)]
    }


# 示例3: 监控数据库操作
@monitor_database_operation(operation="select", table="products")
def fetch_products_from_db(category: str = None) -> list:
    """从数据库获取商品示例"""
    logger.info(f"从数据库查询商品: category={category}")

    # 模拟数据库查询
    time.sleep(random.uniform(0.05, 0.2))

    # 模拟查询结果
    products = [f"product_{i}" for i in range(random.randint(10, 50))]

    if random.random() < 0.02:
        raise Exception("SQL执行超时")

    return products


# 示例4: 监控任务执行
@monitor_task_execution(task_name="image_sync")
def sync_images(product_id: int) -> bool:
    """同步图片任务示例"""
    logger.info(f"同步商品图片: product_id={product_id}")

    # 模拟图片同步过程
    image_count = random.randint(1, 10)
    for i in range(image_count):
        time.sleep(random.uniform(0.5, 2.0))
        logger.info(f"同步第 {i+1}/{image_count} 张图片")

        # 模拟偶尔的失败
        if random.random() < 0.1:
            raise Exception(f"图片 {i} 下载失败")

    return True


# 示例5: 监控队列操作
@monitor_queue_operation(operation="enqueue", queue_name="image_processing")
def add_to_image_queue(product_id: int, image_urls: list) -> int:
    """添加到图片处理队列示例"""
    logger.info(f"添加商品到图片处理队列: product_id={product_id}")

    # 模拟队列操作
    time.sleep(random.uniform(0.01, 0.05))

    task_count = len(image_urls)
    if random.random() < 0.01:
        raise Exception("队列已满")

    return task_count


# 示例6: 使用监控上下文管理器
def batch_process_orders():
    """批量处理订单示例"""
    with MonitoringContext("batch_order_processing", batch_size=100):
        logger.info("开始批量处理订单")

        orders = [f"order_{i}" for i in range(100)]
        processed = 0

        for order in orders:
            try:
                # 模拟订单处理
                time.sleep(random.uniform(0.01, 0.1))
                processed += 1

                # 追踪业务指标
                track_business_metric("order_processing_rate", processed / len(orders))

                # 模拟偶尔的失败订单
                if random.random() < 0.05:
                    raise Exception(f"订单 {order} 处理失败")

            except Exception as e:
                logger.error(f"处理订单失败: {order}")

        logger.info(f"批量处理完成: {processed}/{len(orders)}")
        return processed


# 示例7: 追踪用户行为
def simulate_user_actions():
    """模拟用户行为示例"""
    users = ["user_1", "user_2", "user_3"]
    actions = ["login", "view_product", "add_to_cart", "checkout", "logout"]

    for _ in range(20):
        user = random.choice(users)
        action = random.choice(actions)

        track_user_action(user, action, {
            "timestamp": datetime.now().isoformat(),
            "session_id": f"session_{random.randint(1000, 9999)}"
        })

        time.sleep(random.uniform(0.1, 0.5))


# 示例8: 性能分析器
def performance_intensive_task():
    """性能密集型任务示例"""
    with PerformanceProfiler("complex_calculation") as profiler:
        logger.info("开始复杂计算任务")

        # 模拟CPU密集型操作
        result = 0
        for i in range(1000000):
            result += i * i

        # 模拟内存操作
        data = []
        for i in range(10000):
            data.append([random.random() for _ in range(100)])

        logger.info(f"计算完成，结果: {result}")
        return result


# 示例9: 自定义监控逻辑
def custom_monitoring_example():
    """自定义监控示例"""
    logger.info("自定义监控示例")

    # 设置自定义仪表盘指标
    set_gauge("custom.active_sessions", random.randint(50, 200))
    set_gauge("custom.queue_depth", random.randint(10, 100))

    # 增加自定义计数器
    increment_counter("custom.api_calls", 1, {"endpoint": "/custom", "method": "POST"})

    # 记录自定义业务事件
    logger.log_business_event("custom_event", details={
        "event_type": "user_interaction",
        "feature": "custom_monitoring",
        "value": random.randint(1, 100)
    })


# 示例10: 错误处理和恢复
def error_handling_example():
    """错误处理示例"""
    from .error_tracker import track_errors, ErrorSeverity

    @track_errors(severity=ErrorSeverity.MEDIUM)
    def risky_operation():
        """有风险的操作"""
        if random.random() < 0.3:
            raise ValueError("随机错误发生")
        return "操作成功"

    try:
        result = risky_operation()
        logger.info(f"操作结果: {result}")
    except Exception as e:
        logger.error(f"操作失败，但错误已被追踪: {e}")


def run_all_examples():
    """运行所有示例"""
    print("=" * 60)
    print("1688sync 监控系统集成示例")
    print("=" * 60)

    examples = [
        ("函数执行监控", process_data, [100]),
        ("API请求监控", get_products, [1, 20]),
        ("数据库操作监控", fetch_products_from_db, ["electronics"]),
        ("任务执行监控", sync_images, [12345]),
        ("队列操作监控", add_to_image_queue, [12345, ["url1", "url2", "url3"]]),
        ("批量处理监控", batch_process_orders, []),
        ("用户行为追踪", simulate_user_actions, []),
        ("性能分析", performance_intensive_task, []),
        ("自定义监控", custom_monitoring_example, []),
        ("错误处理", error_handling_example, []),
    ]

    for i, (name, func, args) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
        print("-" * 40)

        try:
            start_time = time.time()
            result = func(*args) if args else func()
            duration = time.time() - start_time

            print(f"✓ 执行成功，耗时: {duration:.3f}秒")
            if result is not None:
                print(f"  结果: {result}")

        except Exception as e:
            print(f"✗ 执行失败: {e}")

        time.sleep(1)  # 间隔

    print("\n" + "=" * 60)
    print("所有示例执行完成")
    print("=" * 60)


if __name__ == "__main__":
    # 确保监控系统已启动
    try:
        from .initializer import initialize_monitoring, get_monitoring_components

        # 使用默认配置初始化监控
        if initialize_monitoring():
            print("监控系统已启动，开始运行示例...")
            run_all_examples()
        else:
            print("监控系统启动失败，请检查配置")

    except Exception as e:
        print(f"运行示例失败: {e}")
        print("请确保监控系统已正确安装和配置")