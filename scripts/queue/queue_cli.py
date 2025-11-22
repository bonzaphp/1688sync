#!/usr/bin/env python3
# Queue CLI
# 队列管理命令行工具

import os
import sys
import click
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.queue.manager import queue_manager
from src.queue.scheduler import ScheduleConfig, ScheduleType
from src.queue.task_manager import TaskPriority


@click.group()
@click.option('--config', '-c', help='配置文件路径')
@click.pass_context
def cli(ctx, config):
    """1688sync 队列管理命令行工具"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = config

    # 初始化队列管理器
    try:
        queue_manager.initialize()
        click.echo("✅ 队列管理器已初始化")
    except Exception as e:
        click.echo(f"❌ 初始化失败: {e}")
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', default='table', type=click.Choice(['table', 'json']), help='输出格式')
def status(format):
    """显示系统状态"""
    try:
        health = queue_manager.health_check()

        if format == 'json':
            click.echo(json.dumps(health, indent=2, default=str))
        else:
            click.echo(f"\n🏥 系统健康状态: {health['overall'].upper()}")
            click.echo(f"📅 检查时间: {health['timestamp']}")
            click.echo("\n📊 组件状态:")

            for component, status in health['components'].items():
                status_icon = "✅" if status['status'] == 'healthy' else "⚠️" if status['status'] == 'warning' else "❌"
                click.echo(f"  {status_icon} {component}: {status['status']} - {status['message']}")

            click.echo()
    except Exception as e:
        click.echo(f"❌ 获取状态失败: {e}")


@cli.group()
def task():
    """任务管理"""
    pass


@task.command()
@click.argument('task_name')
@click.option('--args', '-a', help='位置参数 (JSON格式)')
@click.option('--kwargs', '-k', help='关键字参数 (JSON格式)')
@click.option('--priority', '-p', default='normal', type=click.Choice(['low', 'normal', 'high', 'urgent']))
@click.option('--queue', '-q', default='default', help='队列名称')
def create(task_name, args, kwargs, priority, queue):
    """创建任务"""
    try:
        # 解析参数
        args_list = json.loads(args) if args else ()
        kwargs_dict = json.loads(kwargs) if kwargs else {}
        priority_enum = TaskPriority[priority.upper()]

        task_id = queue_manager.create_task(
            task_name=task_name,
            args=args_list,
            kwargs=kwargs_dict,
            priority=priority_enum,
            queue=queue
        )

        click.echo(f"✅ 任务已创建: {task_id}")

    except Exception as e:
        click.echo(f"❌ 创建任务失败: {e}")


@task.command()
@click.argument('task_id')
def info(task_id):
    """查看任务信息"""
    try:
        task_info = queue_manager.get_task_status(task_id)

        if not task_info:
            click.echo(f"❌ 任务不存在: {task_id}")
            return

        click.echo(f"\n📋 任务信息:")
        click.echo(f"  ID: {task_info.task_id}")
        click.echo(f"  名称: {task_info.task_name}")
        click.echo(f"  状态: {task_info.status.value}")
        click.echo(f"  优先级: {task_info.priority.name}")
        click.echo(f"  创建时间: {task_info.created_at}")
        if task_info.started_at:
            click.echo(f"  开始时间: {task_info.started_at}")
        if task_info.completed_at:
            click.echo(f"  完成时间: {task_info.completed_at}")
        if task_info.error:
            click.echo(f"  错误信息: {task_info.error}")
        if task_info.progress:
            click.echo(f"  进度: {task_info.progress}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取任务信息失败: {e}")


@task.command()
@click.option('--format', '-f', default='table', type=click.Choice(['table', 'json']))
def list(format):
    """列出活跃任务"""
    try:
        active_tasks = queue_manager.get_active_tasks()

        if format == 'json':
            tasks_data = []
            for task in active_tasks:
                tasks_data.append({
                    'id': task.task_id,
                    'name': task.task_name,
                    'status': task.status.value,
                    'priority': task.priority.name,
                    'created_at': task.created_at.isoformat()
                })
            click.echo(json.dumps(tasks_data, indent=2))
        else:
            if not active_tasks:
                click.echo("📝 没有活跃任务")
                return

            click.echo(f"\n📝 活跃任务 ({len(active_tasks)}):")
            click.echo("-" * 80)
            click.echo(f"{'ID':<20} {'名称':<25} {'状态':<12} {'优先级':<10} {'创建时间'}")
            click.echo("-" * 80)

            for task in active_tasks:
                created_time = task.created_at.strftime("%H:%M:%S")
                click.echo(f"{task.task_id[:18]:<20} {task.task_name[:23]:<25} {task.status.value:<12} {task.priority.name:<10} {created_time}")

            click.echo()

    except Exception as e:
        click.echo(f"❌ 获取任务列表失败: {e}")


@task.command()
@click.argument('task_id')
@click.option('--terminate', '-t', is_flag=True, help='强制终止')
def cancel(task_id, terminate):
    """取消任务"""
    try:
        success = queue_manager.cancel_task(task_id, terminate)

        if success:
            action = "强制终止" if terminate else "取消"
            click.echo(f"✅ 任务已{action}: {task_id}")
        else:
            click.echo(f"❌ {action}任务失败: {task_id}")

    except Exception as e:
        click.echo(f"❌ 取消任务失败: {e}")


@cli.group()
def schedule():
    """调度管理"""
    pass


@schedule.command()
@click.option('--format', '-f', default='table', type=click.Choice(['table', 'json']))
def list(format):
    """列出调度任务"""
    try:
        schedules = queue_manager.list_schedules()

        if format == 'json':
            click.echo(json.dumps(schedules, indent=2, default=str))
        else:
            if not schedules:
                click.echo("⏰ 没有调度任务")
                return

            click.echo(f"\n⏰ 调度任务 ({len(schedules)}):")
            click.echo("-" * 80)
            click.echo(f"{'名称':<20} {'任务':<25} {'类型':<12} {'状态':<8} {'运行中'}")
            click.echo("-" * 80)

            for sch in schedules:
                running = "是" if sch.get('running', False) else "否"
                click.echo(f"{sch['name'][:18]:<20} {sch['task'][:23]:<25} {sch['schedule_type']:<12} {sch['enabled']:<8} {running}")

            click.echo()

    except Exception as e:
        click.echo(f"❌ 获取调度列表失败: {e}")


@schedule.command()
@click.argument('name')
@click.argument('task_name')
@click.option('--type', '-t', default='interval', type=click.Choice(['interval', 'cron', 'once', 'delayed']))
@click.option('--interval', '-i', type=int, help='间隔秒数 (interval类型)')
@click.option('--cron', '-c', help='Cron表达式 (cron类型)')
@click.option('--start-time', help='开始时间 (ISO格式, delayed类型)')
@click.option('--priority', '-p', default='normal', type=click.Choice(['low', 'normal', 'high', 'urgent']))
@click.option('--queue', '-q', default='default', help='队列名称')
def add(name, task_name, type, interval, cron, start_time, priority, queue):
    """添加调度任务"""
    try:
        # 解析调度类型
        schedule_type = ScheduleType(type.upper())

        # 构建配置
        config = ScheduleConfig(
            name=name,
            task=task_name,
            schedule_type=schedule_type,
            priority=TaskPriority[priority.upper()],
            queue=queue
        )

        # 设置调度特定参数
        if schedule_type == ScheduleType.INTERVAL and interval:
            config.interval_seconds = interval
        elif schedule_type == ScheduleType.CRON and cron:
            config.cron_expression = cron
        elif schedule_type == ScheduleType.DELAYED and start_time:
            config.start_time = datetime.fromisoformat(start_time)

        success = queue_manager.add_schedule(config)

        if success:
            click.echo(f"✅ 调度任务已添加: {name}")
        else:
            click.echo(f"❌ 添加调度任务失败: {name}")

    except Exception as e:
        click.echo(f"❌ 添加调度任务失败: {e}")


@schedule.command()
@click.argument('name')
def remove(name):
    """移除调度任务"""
    try:
        success = queue_manager.remove_schedule(name)

        if success:
            click.echo(f"✅ 调度任务已移除: {name}")
        else:
            click.echo(f"❌ 移除调度任务失败: {name}")

    except Exception as e:
        click.echo(f"❌ 移除调度任务失败: {e}")


@cli.group()
def monitor():
    """监控相关"""
    pass


@monitor.command()
def health():
    """系统健康检查"""
    try:
        health_summary = queue_manager.get_health_summary()

        click.echo(f"\n🏥 系统健康摘要:")
        click.echo(f"  总体状态: {health_summary['overall_status']}")
        click.echo(f"  检查时间: {health_summary['timestamp']}")

        click.echo(f"\n👥 Worker状态:")
        workers = health_summary['workers']
        click.echo(f"  总数: {workers['total']}")
        click.echo(f"  运行中: {workers['running']}")
        click.echo(f"  停止: {workers['stopped']}")
        click.echo(f"  错误: {workers['error']}")

        click.echo(f"\n📊 队列状态:")
        queues = health_summary['queues']
        click.echo(f"  总数: {queues['total']}")
        click.echo(f"  待处理: {queues['pending_tasks']}")
        click.echo(f"  活跃: {queues['active_tasks']}")
        click.echo(f"  失败: {queues['failed_tasks']}")

        click.echo(f"\n📈 性能指标:")
        metrics = health_summary['metrics']
        click.echo(f"  成功率: {metrics['success_rate']}")
        click.echo(f"  错误率: {metrics['error_rate']}")
        click.echo(f"  平均响应时间: {metrics['avg_response_time']}")

        if health_summary['alerts']:
            click.echo(f"\n⚠️ 告警:")
            for alert in health_summary['alerts']:
                click.echo(f"  - {alert}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取健康摘要失败: {e}")


@monitor.command()
def progress():
    """进度监控"""
    try:
        progress_summary = queue_manager.get_progress_summary()
        running_tasks = queue_manager.get_running_tasks_progress()

        click.echo(f"\n📈 进度摘要:")
        click.echo(f"  总任务数: {progress_summary['total_tasks']}")
        click.echo(f"  监控状态: {'活跃' if progress_summary['monitoring_active'] else '停止'}")

        if progress_summary['status_distribution']:
            click.echo(f"\n📊 状态分布:")
            for status, count in progress_summary['status_distribution'].items():
                click.echo(f"  {status}: {count}")

        if progress_summary['avg_progress'] > 0:
            click.echo(f"  平均进度: {progress_summary['avg_progress']:.1f}%")

        if running_tasks:
            click.echo(f"\n🏃 正在运行的任务 ({len(running_tasks)}):")
            click.echo("-" * 80)
            click.echo(f"{'任务ID':<20} {'名称':<25} {'进度':<15} {'描述':<20}")
            click.echo("-" * 80)

            for task in running_tasks:
                task_id = task['task_id'][:18]
                task_name = task['task_name'][:23]
                progress = f"{task['current']}/{task['total']} ({task['percent']}%)"
                description = task['description'][:18]
                click.echo(f"{task_id:<20} {task_name:<25} {progress:<15} {description:<20}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取进度信息失败: {e}")


@cli.group()
def recovery():
    """恢复和检查点"""
    pass


@recovery.command()
@click.argument('task_id')
def checkpoints(task_id):
    """查看任务的检查点"""
    try:
        checkpoints = queue_manager.checkpoint_manager.list_checkpoints(task_id)

        if not checkpoints:
            click.echo(f"📝 任务 {task_id} 没有检查点")
            return

        click.echo(f"\n📝 任务 {task_id} 的检查点 ({len(checkpoints)}):")
        click.echo("-" * 80)
        click.echo(f"{'检查点ID':<30} {'时间':<20} {'进度':<15} {'校验和'}")
        click.echo("-" * 80)

        for cp in checkpoints:
            time_str = cp.timestamp.strftime("%m-%d %H:%M:%S")
            progress = f"{cp.progress_data.get('percent', 0)}%"
            checksum_short = cp.checksum[:8]

            click.echo(f"{cp.checkpoint_id[:28]:<30} {time_str:<20} {progress:<15} {checksum_short}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取检查点失败: {e}")


@recovery.command()
@click.argument('task_id')
@click.option('--checkpoint-id', help='指定检查点ID')
@click.option('--strategy', default='auto', type=click.Choice(['auto', 'checkpoint', 'restart']))
@click.option('--force-restart', is_flag=True, help='强制重新开始')
def resume(task_id, checkpoint_id, strategy, force_restart):
    """恢复任务"""
    try:
        result = queue_manager.resume_manager.resume_task(
            task_id=task_id,
            checkpoint_id=checkpoint_id,
            strategy=strategy,
            force_restart=force_restart
        )

        if result.success:
            click.echo(f"✅ 任务恢复成功:")
            click.echo(f"  新任务ID: {result.new_task_id}")
            click.echo(f"  从检查点恢复: {'是' if result.resumed_from_checkpoint else '否'}")
        else:
            click.echo(f"❌ 任务恢复失败: {result.error_message}")

    except Exception as e:
        click.echo(f"❌ 恢复任务失败: {e}")


@recovery.command()
@click.argument('task_id')
def options(task_id):
    """查看恢复选项"""
    try:
        options = queue_manager.resume_manager.get_resume_options(task_id)

        if not options:
            click.echo(f"❌ 任务 {task_id} 无法恢复")
            return

        click.echo(f"\n🔄 任务 {task_id} 的恢复选项:")
        click.echo("-" * 80)
        click.echo(f"{'检查点ID':<30} {'时间':<20} {'进度':<10} {'推荐策略':<15} {'预计恢复时间'}")
        click.echo("-" * 80)

        for opt in options:
            time_str = datetime.fromisoformat(opt['timestamp']).strftime("%m-%d %H:%M:%S")
            progress = f"{opt['progress'].get('percent', 0)}%"
            strategy = opt['strategy']
            recovery_time = f"{opt['estimated_recovery_time']}s"

            click.echo(f"{opt['checkpoint_id'][:28]:<30} {time_str:<20} {progress:<10} {strategy:<15} {recovery_time}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取恢复选项失败: {e}")


@cli.command()
@click.option('--days', '-d', default=7, help='清理多少天前的数据')
def cleanup(days):
    """清理旧数据"""
    try:
        click.echo(f"🧹 开始清理 {days} 天前的旧数据...")
        queue_manager.cleanup_old_data(days)
        click.echo(f"✅ 清理完成")

    except Exception as e:
        click.echo(f"❌ 清理失败: {e}")


@cli.command()
@click.option('--output', '-o', help='输出文件路径')
def report(output):
    """生成系统报告"""
    try:
        report_data = queue_manager.generate_system_report()

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
            click.echo(f"✅ 报告已保存到: {output}")
        else:
            click.echo(json.dumps(report_data, indent=2, default=str, ensure_ascii=False))

    except Exception as e:
        click.echo(f"❌ 生成报告失败: {e}")


@cli.command()
def config():
    """显示当前配置"""
    try:
        config = queue_manager.get_configuration()

        click.echo("\n⚙️ 当前配置:")
        click.echo(f"  Celery Broker URL: {config['celery_broker_url']}")
        click.echo(f"  Celery Result Backend: {config['celery_result_backend']}")
        click.echo(f"  Task Time Limit: {config['task_time_limit']}s")
        click.echo(f"  Task Soft Time Limit: {config['task_soft_time_limit']}s")
        click.echo(f"  Worker Prefetch Multiplier: {config['worker_prefetch_multiplier']}")

        click.echo(f"\n📊 监控配置:")
        monitoring = config['monitoring']
        click.echo(f"  进度监控: {'活跃' if monitoring['progress_monitor_active'] else '停止'}")
        click.echo(f"  状态监控: {'活跃' if monitoring['status_monitor_active'] else '停止'}")
        click.echo(f"  更新间隔: {monitoring['update_interval']}s")

        click.echo(f"\n⚠️ 监控阈值:")
        thresholds = config['thresholds']
        for key, value in thresholds.items():
            click.echo(f"  {key}: {value}")

        click.echo(f"\n💾 检查点配置:")
        checkpoint = config['checkpoint']
        click.echo(f"  每任务最大检查点数: {checkpoint['max_checkpoints']}")
        click.echo(f"  检查点目录: {checkpoint['checkpoint_dir']}")

        click.echo()

    except Exception as e:
        click.echo(f"❌ 获取配置失败: {e}")


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n👋 再见!")
        sys.exit(0)
    except Exception as e:
        click.echo(f"❌ 程序异常: {e}")
        sys.exit(1)