#!/usr/bin/env python3
# Queue Example
# 队列系统使用示例

import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.queue.manager import queue_manager
from src.queue.scheduler import ScheduleConfig, ScheduleType
from src.queue.task_manager import TaskPriority


def example_basic_task():
    """基础任务示例"""
    print("🚀 创建基础任务...")

    # 创建健康检查任务
    task_id = queue_manager.create_task(
        task_name='src.queue.tasks.health_check',
        priority=TaskPriority.NORMAL,
        queue='default'
    )

    print(f"✅ 任务已创建: {task_id}")

    # 监控任务状态
    for i in range(10):
        task_info = queue_manager.get_task_status(task_id)
        if task_info:
            print(f"📊 任务状态: {task_info.status.value}")
            if task_info.status.value in ['SUCCESS', 'FAILURE']:
                break
        time.sleep(1)


def example_batch_task():
    """批量任务示例"""
    print("\n📦 创建批量任务...")

    # 模拟图片URL列表
    image_urls = [
        f"https://example.com/image{i}.jpg" for i in range(20)
    ]

    # 创建批量下载任务
    task_ids = queue_manager.create_batch_task(
        task_name='src.queue.tasks.image_processing.download_images',
        items=image_urls,
        batch_size=5,
        kwargs={'product_id': 'example_product'}
    )

    print(f"✅ 批量任务已创建: {len(task_ids)} 个任务")
    return task_ids


def example_schedule():
    """调度任务示例"""
    print("\n⏰ 创建调度任务...")

    # 创建延迟调度（10秒后执行）
    from datetime import datetime, timedelta

    config = ScheduleConfig(
        name='example_delayed_task',
        task='src.queue.tasks.health_check',
        schedule_type=ScheduleType.DELAYED,
        start_time=datetime.utcnow() + timedelta(seconds=10),
        priority=TaskPriority.NORMAL
    )

    success = queue_manager.add_schedule(config)
    if success:
        print("✅ 延迟调度任务已创建")

    # 创建间隔调度（每30秒执行一次）
    interval_config = ScheduleConfig(
        name='example_interval_task',
        task='src.queue.tasks.health_check',
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=30,
        priority=TaskPriority.LOW
    )

    success = queue_manager.add_schedule(interval_config)
    if success:
        print("✅ 间隔调度任务已创建")


def example_monitoring():
    """监控示例"""
    print("\n📊 系统监控...")

    # 健康检查
    health = queue_manager.health_check()
    print(f"🏥 系统健康状态: {health['overall']}")

    # 任务统计
    stats = queue_manager.get_task_statistics()
    print(f"📈 活跃任务数: {stats.get('total_tasks', 0)}")

    # 进度监控
    progress = queue_manager.get_running_tasks_progress()
    print(f"🏃 正在运行的任务: {len(progress)}")


def example_recovery():
    """恢复示例"""
    print("\n🔄 恢复功能演示...")

    # 创建一个会失败的任务（模拟）
    task_id = queue_manager.create_task(
        task_name='src.queue.tasks.health_check',
        priority=TaskPriority.NORMAL
    )

    print(f"📝 创建测试任务: {task_id}")

    # 检查恢复选项
    if queue_manager.resume_manager.can_resume_task(task_id):
        options = queue_manager.resume_manager.get_resume_options(task_id)
        print(f"🔄 可用恢复选项: {len(options)}")

        if options:
            print("💡 恢复选项详情:")
            for i, option in enumerate(options[:3]):  # 只显示前3个
                print(f"  {i+1}. {option['checkpoint_id'][:16]}... "
                      f"({option['progress'].get('percent', 0)}%) - {option['strategy']}")


def main():
    """主函数"""
    print("🎯 1688sync 队列系统演示")
    print("=" * 50)

    try:
        # 初始化队列管理器
        queue_manager.initialize()

        # 运行示例
        example_basic_task()
        example_batch_task()
        example_schedule()
        example_monitoring()
        example_recovery()

        print("\n✨ 演示完成！")
        print("\n🛠️ 更多功能请使用命令行工具:")
        print("   python scripts/queue/queue_cli.py --help")

    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()