#!/usr/bin/env python3
"""
1688sync爬虫演示脚本
提供简单的爬虫功能演示
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def demo_crawl():
    """演示爬虫功能"""
    try:
        print("🚀 1688sync爬虫演示")
        print("=" * 50)

        # 检查数据库是否已初始化
        if not os.path.exists("data/1688sync.db"):
            print("❌ 数据库未初始化，请先运行: python init_db.py")
            return False

        print("✅ 数据库已初始化")

        # 导入必要的模块
        from src.task_queue.manager import QueueManager
        from src.task_queue.tasks.crawler import FetchProductsTask

        print("✅ 爬虫模块加载成功")

        # 初始化队列管理器
        queue_manager = QueueManager()
        print("✅ 队列管理器初始化成功")

        # 创建爬虫任务
        print("\n📝 创建爬虫任务...")

        # 使用通用分类ID进行演示
        task_params = {
            "category_id": "123",  # 1688的通用分类ID
            "max_products": 5,     # 限制数量用于演示
            "page_size": 2,        # 每页大小
        }

        task_id = queue_manager.create_task(
            task_name="src.task_queue.tasks.crawler.fetch_products",
            kwargs=task_params
        )

        print(f"✅ 爬虫任务创建成功: #{task_id}")
        print(f"📊 任务参数: {task_params}")

        # 获取任务状态
        task_info = queue_manager.get_task_info(task_id)
        print(f"📈 任务状态: {task_info.get('status', 'unknown')}")

        print("\n" + "=" * 50)
        print("🎉 爬虫演示完成！")
        print("\n💡 提示:")
        print("- 任务已添加到队列，需要启动Celery Worker来执行")
        print("- 使用 'python cli.py queue status' 查看任务状态")
        print("- 使用 'python cli.py queue info <task_id>' 查看详细信息")

        return True

    except Exception as e:
        print(f"❌ 爬虫演示失败: {e}")
        return False

def show_usage():
    """显示使用说明"""
    print("📚 1688sync爬虫使用说明")
    print("=" * 50)
    print()
    print("1. 基础爬虫命令:")
    print("   python cli.py crawl products 123 --max-products 10")
    print("   # 123是分类ID，--max-products限制数量")
    print()
    print("2. 启动Worker执行任务:")
    print("   python scripts/queue/start_worker.py")
    print()
    print("3. 查看队列状态:")
    print("   python cli.py queue status")
    print()
    print("4. 监控任务进度:")
    print("   python cli.py queue info <task_id>")
    print()
    print("5. 分类ID示例:")
    print("   - 123: 通用商品分类")
    print("   - 124: 电子产品")
    print("   - 125: 服装鞋帽")
    print("   - 更多分类请参考1688网站")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        show_usage()
    else:
        success = demo_crawl()
        if not success:
            print("\n💡 需要帮助? 运行: python demo_crawl.py --help")
            sys.exit(1)