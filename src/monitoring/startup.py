"""
监控启动脚本 - 启动和配置监控系统
"""

import argparse
import sys
import time
from pathlib import Path

from .config import load_monitoring_config, create_sample_config, validate_config, apply_env_overrides
from .initializer import initialize_monitoring, get_monitoring_components, shutdown_monitoring


def start_monitoring(config_file: str = None, daemon: bool = False):
    """启动监控系统"""
    try:
        print("=" * 60)
        print("1688sync 监控系统启动中...")
        print("=" * 60)

        # 加载配置
        config = load_monitoring_config(config_file)
        config = apply_env_overrides(config)

        # 验证配置
        if not validate_config(config):
            print("配置验证失败，请检查配置文件")
            return False

        print(f"配置加载完成，使用 {len(config)} 个配置节")

        # 初始化监控系统
        if not initialize_monitoring(config):
            print("监控系统初始化失败")
            return False

        print("监控系统启动成功！")

        # 获取组件状态
        components = get_monitoring_components()
        print("\n组件状态:")
        print(f"- 日志记录器: {'✓' if components['logger'] else '✗'}")
        print(f"- 性能监控: {'✓' if components['performance_monitor'] else '✗'}")
        print(f"- 错误追踪: {'✓' if components['error_tracker'] else '✗'}")
        print(f"- 告警管理: {'✓' if components['alert_manager'] else '✗'}")
        print(f"- 日志分析: {'✓' if components['log_analyzer'] else '✗'}")

        if daemon:
            print("\n监控系统以守护进程模式运行，按 Ctrl+C 停止...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n正在停止监控系统...")
                shutdown_monitoring()
                print("监控系统已停止")
        else:
            print("\n监控系统启动完成，返回主程序")

        return True

    except Exception as e:
        print(f"启动监控系统失败: {e}")
        return False


def create_config(config_file: str):
    """创建配置文件"""
    try:
        create_sample_config(config_file)
        return True
    except Exception as e:
        print(f"创建配置文件失败: {e}")
        return False


def validate_config_file(config_file: str):
    """验证配置文件"""
    try:
        from .config import load_monitoring_config
        config = load_monitoring_config(config_file)
        config = apply_env_overrides(config)

        if validate_config(config):
            print("配置文件验证通过")
            return True
        else:
            print("配置文件验证失败")
            return False

    except Exception as e:
        print(f"验证配置文件失败: {e}")
        return False


def show_status():
    """显示监控状态"""
    try:
        components = get_monitoring_components()

        if not components['logger']:
            print("监控系统未启动")
            return False

        print("=" * 60)
        print("1688sync 监控系统状态")
        print("=" * 60)

        # 性能监控状态
        if components['performance_monitor']:
            health = components['performance_monitor'].get_system_health()
            print(f"\n系统健康状态: {health.get('status', 'unknown')}")
            print(f"- CPU使用率: {health.get('cpu_percent', 0):.1f}%")
            print(f"- 内存使用率: {health.get('memory_percent', 0):.1f}%")
            print(f"- 磁盘使用率: {health.get('disk_percent', 0):.1f}%")

            if health.get('alerts'):
                print("- 告警信息:")
                for alert in health['alerts']:
                    print(f"  • {alert}")

        # 错误追踪状态
        if components['error_tracker']:
            stats = components['error_tracker'].get_error_statistics(24)
            print(f"\n错误统计 (24小时):")
            print(f"- 总错误数: {stats.get('total_errors', 0)}")
            print(f"- 错误率: {stats.get('error_rate_per_hour', 0):.1f}/小时")

            by_severity = stats.get('by_severity', {})
            for severity, count in by_severity.items():
                print(f"- {severity}: {count}")

        # 告警管理状态
        if components['alert_manager']:
            active_alerts = components['alert_manager'].get_active_alerts()
            alert_stats = components['alert_manager'].get_alert_statistics(24)

            print(f"\n告警状态 (24小时):")
            print(f"- 活跃告警: {len(active_alerts)}")
            print(f"- 总告警数: {alert_stats.get('total_alerts', 0)}")
            print(f"- 启用规则: {alert_stats.get('enabled_rules', 0)}")

            by_level = alert_stats.get('by_level', {})
            for level, count in by_level.items():
                print(f"- {level}: {count}")

        # 日志分析状态
        if components['log_analyzer']:
            top_patterns = components['log_analyzer'].get_top_patterns(5)
            recent_anomalies = components['log_analyzer'].get_recent_anomalies(24)

            print(f"\n日志分析状态:")
            print(f"- 发现模式: {len(top_patterns)}")
            print(f"- 最近异常: {len(recent_anomalies)}")

            if top_patterns:
                print("- Top 模式:")
                for i, pattern in enumerate(top_patterns[:3], 1):
                    print(f"  {i}. {pattern.pattern[:50]}... ({pattern.count}次)")

        print("\n" + "=" * 60)
        return True

    except Exception as e:
        print(f"获取监控状态失败: {e}")
        return False


def test_notifications():
    """测试通知渠道"""
    try:
        components = get_monitoring_components()

        if not components['alert_manager']:
            print("告警管理器未启动")
            return False

        print("测试通知渠道...")

        # 测试日志通知
        if components['alert_manager'].test_notification_channel('log'):
            print("✓ 日志通知渠道测试成功")
        else:
            print("✗ 日志通知渠道测试失败")

        # 测试邮件通知
        if 'email' in components['alert_manager'].notification_channels:
            if components['alert_manager'].test_notification_channel('email'):
                print("✓ 邮件通知渠道测试成功")
            else:
                print("✗ 邮件通知渠道测试失败")
        else:
            print("- 邮件通知渠道未配置")

        # 测试Webhook通知
        if 'webhook' in components['alert_manager'].notification_channels:
            if components['alert_manager'].test_notification_channel('webhook'):
                print("✓ Webhook通知渠道测试成功")
            else:
                print("✗ Webhook通知渠道测试失败")
        else:
            print("- Webhook通知渠道未配置")

        return True

    except Exception as e:
        print(f"测试通知渠道失败: {e}")
        return False


def export_data(format_type: str = "json", output_file: str = None):
    """导出监控数据"""
    try:
        components = get_monitoring_components()

        if not components['logger']:
            print("监控系统未启动")
            return False

        print(f"导出监控数据 (格式: {format_type})...")

        # 导出性能指标
        if components['performance_monitor']:
            metrics_data = components['performance_monitor'].export_metrics(format_type)
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(metrics_data)
                print(f"性能指标已导出到: {output_file}")
            else:
                print("性能指标数据:")
                print(metrics_data[:1000] + "..." if len(metrics_data) > 1000 else metrics_data)

        # 导出错误数据
        if components['error_tracker']:
            errors_data = components['error_tracker'].export_errors(format_type)
            errors_file = output_file.replace('.json', '_errors.json') if output_file else None
            if errors_file:
                with open(errors_file, 'w', encoding='utf-8') as f:
                    f.write(errors_data)
                print(f"错误数据已导出到: {errors_file}")

        print("数据导出完成")
        return True

    except Exception as e:
        print(f"导出数据失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='1688sync 监控系统管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 启动命令
    start_parser = subparsers.add_parser('start', help='启动监控系统')
    start_parser.add_argument('--config', '-c', help='配置文件路径')
    start_parser.add_argument('--daemon', '-d', action='store_true', help='守护进程模式')

    # 创建配置命令
    config_parser = subparsers.add_parser('create-config', help='创建示例配置文件')
    config_parser.add_argument('file', nargs='?', default='monitoring_config.json', help='配置文件路径')

    # 验证配置命令
    validate_parser = subparsers.add_parser('validate', help='验证配置文件')
    validate_parser.add_argument('config', help='配置文件路径')

    # 状态命令
    subparsers.add_parser('status', help='显示监控状态')

    # 测试命令
    subparsers.add_parser('test', help='测试通知渠道')

    # 导出命令
    export_parser = subparsers.add_parser('export', help='导出监控数据')
    export_parser.add_argument('--format', '-f', choices=['json'], default='json', help='导出格式')
    export_parser.add_argument('--output', '-o', help='输出文件路径')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行命令
    success = True

    if args.command == 'start':
        success = start_monitoring(args.config, args.daemon)

    elif args.command == 'create-config':
        success = create_config(args.file)

    elif args.command == 'validate':
        success = validate_config_file(args.config)

    elif args.command == 'status':
        success = show_status()

    elif args.command == 'test':
        success = test_notifications()

    elif args.command == 'export':
        success = export_data(args.format, args.output)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()