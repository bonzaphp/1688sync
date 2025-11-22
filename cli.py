#!/usr/bin/env python3
# 1688sync CLI Tool
# 基于 Click 框架的命令行工具

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import click
from click import echo, style, secho

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.queue.manager import QueueManager
from src.queue.tasks.data_sync import SyncProductsTask, SyncSuppliersTask, ValidateDataTask, CleanupDuplicatesTask
from src.queue.tasks.crawler import FetchProductsTask, FetchProductDetailsTask, FetchSuppliersTask, SyncCategoryTask
from src.queue.tasks.base import TaskResult
from config.settings import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局队列管理器实例
queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """获取队列管理器实例"""
    global queue_manager
    if queue_manager is None:
        queue_manager = QueueManager()
        queue_manager.initialize()
    return queue_manager


def print_success(message: str):
    """打印成功消息"""
    secho(f"✓ {message}", fg='green', bold=True)


def print_error(message: str):
    """打印错误消息"""
    secho(f"✗ {message}", fg='red', bold=True)


def print_warning(message: str):
    """打印警告消息"""
    secho(f"⚠ {message}", fg='yellow', bold=True)


def print_info(message: str):
    """打印信息消息"""
    secho(f"ℹ {message}", fg='blue')


def format_task_result(result: TaskResult) -> str:
    """格式化任务结果"""
    if result.success:
        status = style("成功", fg='green')
        if result.data:
            data_summary = ", ".join([f"{k}: {v}" for k, v in result.data.items() if isinstance(v, (int, float, str))])
            return f"状态: {status} | {data_summary}"
        return f"状态: {status}"
    else:
        status = style("失败", fg='red')
        error_msg = result.error or "未知错误"
        return f"状态: {status} | 错误: {error_msg}"


@click.group()
@click.option('--config', '-c', help='配置文件路径')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.option('--quiet', '-q', is_flag=True, help='静默模式')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """
    1688sync 命令行工具

    用于管理1688数据同步、爬虫和队列操作。
    """
    # 确保上下文对象存在
    ctx.ensure_object(dict)

    # 设置日志级别
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)

    # 存储配置
    ctx.obj['config'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet

    # 初始化队列管理器
    try:
        get_queue_manager()
        if not quiet:
            print_success("队列管理器初始化成功")
    except Exception as e:
        print_error(f"队列管理器初始化失败: {e}")
        sys.exit(1)


@cli.group()
def sync():
    """数据同步相关命令"""
    pass


@sync.command()
@click.option('--batch-size', '-b', default=100, help='批处理大小')
@click.option('--source', '-s', default='1688', help='数据源系统')
@click.option('--type', '-t', type=click.Choice(['full', 'incremental']), default='incremental', help='同步类型')
@click.option('--filters', '-f', help='过滤条件 (JSON格式)')
@click.option('--watch', '-w', is_flag=True, help='监控任务进度')
def products(batch_size, source, type, filters, watch):
    """同步产品数据"""
    try:
        # 解析过滤条件
        filter_dict = {}
        if filters:
            import json
            filter_dict = json.loads(filters)

        print_info(f"开始同步产品数据 (批大小: {batch_size}, 类型: {type})")

        # 创建同步任务
        task = SyncProductsTask()

        if watch:
            # 监控模式
            print_info("启动任务监控...")

            # 注册进度回调
            def progress_callback(current, total, message):
                progress = (current / total * 100) if total > 0 else 0
                echo(f"进度: {progress:.1f}% | {message}")

            task.add_progress_callback(progress_callback)

        # 执行任务
        result = task.run(
            batch_size=batch_size,
            source_system=source,
            sync_type=type,
            filters=filter_dict
        )

        # 显示结果
        echo("\n" + "="*50)
        echo("任务执行结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            for key, value in result.data.items():
                if key != 'consistency_issues':  # 跳过详细的问题列表
                    echo(f"  {key}: {value}")

    except json.JSONDecodeError:
        print_error("过滤条件格式错误，请使用有效的JSON格式")
    except Exception as e:
        print_error(f"同步产品数据失败: {e}")


@sync.command()
@click.option('--batch-size', '-b', default=50, help='批处理大小')
@click.option('--source', '-s', default='1688', help='数据源系统')
@click.option('--type', '-t', type=click.Choice(['full', 'incremental']), default='incremental', help='同步类型')
@click.option('--watch', '-w', is_flag=True, help='监控任务进度')
def suppliers(batch_size, source, type, watch):
    """同步供应商数据"""
    try:
        print_info(f"开始同步供应商数据 (批大小: {batch_size}, 类型: {type})")

        task = SyncSuppliersTask()

        if watch:
            def progress_callback(current, total, message):
                progress = (current / total * 100) if total > 0 else 0
                echo(f"进度: {progress:.1f}% | {message}")

            task.add_progress_callback(progress_callback)

        result = task.run(
            batch_size=batch_size,
            source_system=source,
            sync_type=type
        )

        echo("\n" + "="*50)
        echo("任务执行结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            for key, value in result.data.items():
                if key != 'consistency_issues':
                    echo(f"  {key}: {value}")

    except Exception as e:
        print_error(f"同步供应商数据失败: {e}")


@sync.command()
@click.option('--type', '-t', type=click.Choice(['products', 'suppliers', 'all']), default='all', help='验证类型')
@click.option('--sample-size', '-s', default=1000, help='样本大小')
@click.option('--fix', is_flag=True, help='自动修复问题')
def validate(type, sample_size, fix):
    """验证数据一致性"""
    try:
        print_info(f"开始验证数据 (类型: {type}, 样本: {sample_size})")

        task = ValidateDataTask()
        result = task.run(
            type=type,
            sample_size=sample_size,
            fix_issues=fix
        )

        echo("\n" + "="*50)
        echo("验证结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            data = result.data
            echo(f"  验证类型: {data.get('validation_type')}")
            echo(f"  样本大小: {data.get('sample_size')}")
            echo(f"  发现问题: {data.get('total_issues')}")
            echo(f"  修复问题: {data.get('total_fixed')}")

            # 显示各类型的问题
            results = data.get('results', {})
            for entity_type, entity_result in results.items():
                echo(f"\n  {entity_type.capitalize()}:")
                echo(f"    问题数量: {entity_result.get('issues_found', 0)}")
                if entity_result.get('fixed_count'):
                    echo(f"    修复数量: {entity_result.get('fixed_count')}")

    except Exception as e:
        print_error(f"数据验证失败: {e}")


@sync.command()
@click.option('--type', '-t', type=click.Choice(['products', 'suppliers', 'all']), default='all', help='清理类型')
@click.option('--dry-run', is_flag=True, default=True, help='只检查不删除')
@click.option('--batch-size', '-b', default=100, help='批处理大小')
@click.confirmation_option(prompt='确定要删除重复数据吗？')
def cleanup(type, dry_run, batch_size):
    """清理重复数据"""
    try:
        action = "检查" if dry_run else "清理"
        print_info(f"开始{action}重复数据 (类型: {type})")

        task = CleanupDuplicatesTask()
        result = task.run(
            entity_type=type,
            dry_run=dry_run,
            batch_size=batch_size
        )

        echo("\n" + "="*50)
        echo(f"{action}结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            data = result.data
            echo(f"  处理类型: {data.get('entity_type')}")
            echo(f"  检查模式: {'是' if data.get('dry_run') else '否'}")
            echo(f"  发现重复: {data.get('total_duplicates')}")
            echo(f"  删除数量: {data.get('total_removed')}")

            # 显示各类型的重复情况
            results = data.get('results', {})
            for entity_type, entity_result in results.items():
                echo(f"\n  {entity_type.capitalize()}:")
                echo(f"    重复组数: {entity_result.get('duplicate_groups', 0)}")
                echo(f"    重复数量: {entity_result.get('total_duplicates', 0)}")
                if not dry_run and entity_result.get('removed_count'):
                    echo(f"    删除数量: {entity_result.get('removed_count')}")

    except Exception as e:
        print_error(f"清理重复数据失败: {e}")


@cli.group()
def crawl():
    """爬虫相关命令"""
    pass


@crawl.command()
@click.argument('category_id')
@click.option('--max-products', '-m', default=1000, help='最大产品数量')
@click.option('--page-size', '-p', default=50, help='每页大小')
@click.option('--filters', '-f', help='过滤条件 (JSON格式)')
@click.option('--watch', '-w', is_flag=True, help='监控任务进度')
def products(category_id, max_products, page_size, filters, watch):
    """爬取产品数据"""
    try:
        filter_dict = {}
        if filters:
            import json
            filter_dict = json.loads(filters)

        print_info(f"开始爬取产品数据 (分类: {category_id}, 最大: {max_products})")

        task = FetchProductsTask()

        if watch:
            def progress_callback(current, total, message):
                progress = (current / total * 100) if total > 0 else 0
                echo(f"进度: {progress:.1f}% | {message}")

            task.add_progress_callback(progress_callback)

        result = task.run(
            category_id=category_id,
            max_products=max_products,
            page_size=page_size,
            filters=filter_dict
        )

        echo("\n" + "="*50)
        echo("爬取结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            data = result.data
            echo(f"  获取数量: {data.get('fetched_count')}")
            echo(f"  分类ID: {data.get('category_id')}")
            echo(f"  页数: {data.get('page_num')}")

    except json.JSONDecodeError:
        print_error("过滤条件格式错误，请使用有效的JSON格式")
    except Exception as e:
        print_error(f"爬取产品数据失败: {e}")


@crawl.command()
@click.argument('category_id')
@click.option('--max-products', '-m', default=1000, help='最大产品数量')
@click.option('--sync-products', is_flag=True, default=True, help='同步产品')
@click.option('--sync-suppliers', is_flag=True, default=True, help='同步供应商')
@click.option('--watch', '-w', is_flag=True, help='监控任务进度')
def category(category_id, max_products, sync_products, sync_suppliers, watch):
    """同步整个分类"""
    try:
        print_info(f"开始同步分类 (分类: {category_id})")

        task = SyncCategoryTask()

        if watch:
            def progress_callback(current, total, message):
                progress = (current / total * 100) if total > 0 else 0
                echo(f"进度: {progress:.1f}% | {message}")

            task.add_progress_callback(progress_callback)

        result = task.run(
            category_id=category_id,
            max_products=max_products,
            sync_products=sync_products,
            sync_suppliers=sync_suppliers
        )

        echo("\n" + "="*50)
        echo("分类同步结果:")
        echo(format_task_result(result))

        if result.success and result.data:
            echo(f"\n详细结果:")
            data = result.data
            echo(f"  分类ID: {data.get('category_id')}")
            echo(f"  产品数量: {data.get('products_count')}")
            echo(f"  同步产品: {'是' if data.get('sync_products') else '否'}")
            echo(f"  同步供应商: {'是' if data.get('sync_suppliers') else '否'}")

    except Exception as e:
        print_error(f"同步分类失败: {e}")


@cli.group()
def queue():
    """队列管理相关命令"""
    pass


@queue.command()
def status():
    """查看队列状态"""
    try:
        manager = get_queue_manager()

        echo("队列状态信息:")
        echo("="*50)

        # 获取活跃任务
        active_tasks = manager.task_manager.get_active_tasks()
        echo(f"活跃任务数: {len(active_tasks)}")

        # 获取队列统计
        queue_stats = manager.status_monitor.get_queue_stats()
        echo(f"等待任务: {queue_stats.get('pending', 0)}")
        echo(f"运行中任务: {queue_stats.get('running', 0)}")
        echo(f"失败任务: {queue_stats.get('failed', 0)}")

        # 获取工作进程状态
        worker_stats = manager.status_monitor.get_worker_stats()
        echo(f"活跃工作进程: {worker_stats.get('active', 0)}")

        if active_tasks:
            echo(f"\n活跃任务列表:")
            for task in active_tasks[:5]:  # 只显示前5个
                echo(f"  - {task.get('task_id')}: {task.get('status')}")

    except Exception as e:
        print_error(f"获取队列状态失败: {e}")


@queue.command()
@click.argument('task_id')
def info(task_id):
    """查看任务详细信息"""
    try:
        manager = get_queue_manager()
        task_info = manager.task_manager.get_task_info(task_id)

        if not task_info:
            print_error(f"任务 {task_id} 不存在")
            return

        echo(f"任务详细信息:")
        echo("="*50)
        echo(f"任务ID: {task_info.get('task_id')}")
        echo(f"任务名称: {task_info.get('task_name')}")
        echo(f"状态: {task_info.get('status')}")
        echo(f"创建时间: {task_info.get('created_at')}")
        echo(f"开始时间: {task_info.get('started_at')}")
        echo(f"完成时间: {task_info.get('completed_at')}")

        if task_info.get('progress'):
            progress = task_info['progress']
            echo(f"进度: {progress.get('current', 0)}/{progress.get('total', 0)}")
            echo(f"进度消息: {progress.get('message', '')}")

        if task_info.get('result'):
            echo(f"结果: {task_info['result']}")

        if task_info.get('error'):
            echo(f"错误: {task_info['error']}")

    except Exception as e:
        print_error(f"获取任务信息失败: {e}")


@queue.command()
@click.argument('task_id')
@click.confirmation_option(prompt='确定要取消这个任务吗？')
def cancel(task_id):
    """取消任务"""
    try:
        manager = get_queue_manager()
        success = manager.task_manager.cancel_task(task_id)

        if success:
            print_success(f"任务 {task_id} 已取消")
        else:
            print_error(f"无法取消任务 {task_id}")

    except Exception as e:
        print_error(f"取消任务失败: {e}")


@queue.command()
@click.option('--force', is_flag=True, help='强制清理')
def purge():
    """清理队列"""
    try:
        manager = get_queue_manager()

        if not force:
            if not click.confirm('确定要清理所有等待中的任务吗？'):
                return

        purged_count = manager.task_manager.purge_queue()
        print_success(f"已清理 {purged_count} 个任务")

    except Exception as e:
        print_error(f"清理队列失败: {e}")


@cli.command()
def version():
    """显示版本信息"""
    try:
        settings = get_settings()
        echo("1688sync CLI 工具")
        echo("="*30)
        echo(f"版本: {settings.app_version}")
        echo(f"应用名: {settings.app_name}")
        echo(f"调试模式: {'开启' if settings.debug else '关闭'}")
        echo(f"日志级别: {settings.log_level}")
        echo(f"存储路径: {settings.storage_path}")

    except Exception as e:
        print_error(f"获取版本信息失败: {e}")


if __name__ == '__main__':
    cli()