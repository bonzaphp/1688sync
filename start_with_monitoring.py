#!/usr/bin/env python3
"""
1688sync 应用启动脚本 - 集成监控系统
"""

import os
import sys
import signal
import time
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from monitoring.initializer import initialize_monitoring, get_monitoring_components, shutdown_monitoring
from monitoring.config import load_monitoring_config, apply_env_overrides
from monitoring.logger import get_logger


class ApplicationWithMonitoring:
    """集成监控的应用程序"""

    def __init__(self):
        self.monitoring_initialized = False
        self.running = False
        self.logger = None

    def initialize(self, config_file: str = None):
        """初始化应用和监控系统"""
        try:
            print("=" * 60)
            print("1688sync 应用启动中...")
            print("=" * 60)

            # 1. 初始化监控系统
            print("正在初始化监控系统...")
            config = load_monitoring_config(config_file)
            config = apply_env_overrides(config)

            if initialize_monitoring(config):
                self.monitoring_initialized = True
                print("✓ 监控系统初始化成功")
            else:
                print("✗ 监控系统初始化失败，继续以基本模式运行")

            # 2. 获取日志记录器
            self.logger = get_logger("main_application")
            self.logger.info("1688sync应用启动", details={
                "monitoring_enabled": self.monitoring_initialized,
                "config_file": config_file
            })

            # 3. 初始化其他应用组件
            self._initialize_application_components()

            print("✓ 应用初始化完成")
            return True

        except Exception as e:
            print(f"✗ 应用初始化失败: {e}")
            return False

    def _initialize_application_components(self):
        """初始化应用组件"""
        try:
            # 这里可以初始化其他应用组件
            # 例如：数据库连接、API服务器、任务队列等

            if self.logger:
                self.logger.info("正在初始化应用组件...")

            # 示例：初始化数据库
            self._initialize_database()

            # 示例：初始化API服务器
            self._initialize_api_server()

            # 示例：初始化任务队列
            self._initialize_task_queue()

            if self.logger:
                self.logger.info("应用组件初始化完成")

        except Exception as e:
            if self.logger:
                self.logger.error(f"应用组件初始化失败: {e}", exc_info=True)
            raise

    def _initialize_database(self):
        """初始化数据库连接"""
        try:
            # 这里应该是实际的数据库初始化代码
            if self.logger:
                self.logger.info("数据库连接初始化")
            print("✓ 数据库连接已建立")
        except Exception as e:
            raise Exception(f"数据库初始化失败: {e}")

    def _initialize_api_server(self):
        """初始化API服务器"""
        try:
            # 这里应该是实际的API服务器初始化代码
            if self.logger:
                self.logger.info("API服务器初始化")
            print("✓ API服务器已启动")
        except Exception as e:
            raise Exception(f"API服务器初始化失败: {e}")

    def _initialize_task_queue(self):
        """初始化任务队列"""
        try:
            # 这里应该是实际的任务队列初始化代码
            if self.logger:
                self.logger.info("任务队列初始化")
            print("✓ 任务队列已启动")
        except Exception as e:
            raise Exception(f"任务队列初始化失败: {e}")

    def run(self):
        """运行应用"""
        try:
            self.running = True

            if self.logger:
                self.logger.info("1688sync应用开始运行")

            print("\n" + "=" * 60)
            print("1688sync 应用正在运行")
            print("按 Ctrl+C 停止应用")
            print("=" * 60)

            # 主循环
            while self.running:
                try:
                    # 这里是应用的主逻辑
                    self._main_loop()
                    time.sleep(1)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"主循环异常: {e}", exc_info=True)
                    time.sleep(5)  # 等待后继续

        except KeyboardInterrupt:
            print("\n收到停止信号")
        finally:
            self.shutdown()

    def _main_loop(self):
        """应用主循环"""
        # 这里可以添加应用的主逻辑
        # 例如：处理任务、响应请求等

        # 示例：定期记录心跳
        static_counter = getattr(self, '_heartbeat_counter', 0)
        if static_counter % 60 == 0:  # 每分钟记录一次
            if self.logger:
                self.logger.info("应用心跳", details={
                    "uptime_seconds": static_counter,
                    "status": "running"
                })

        static_counter += 1
        self._heartbeat_counter = static_counter

    def shutdown(self):
        """关闭应用"""
        try:
            print("\n正在关闭应用...")
            self.running = False

            if self.logger:
                self.logger.info("1688sync应用正在关闭")

            # 关闭应用组件
            self._shutdown_application_components()

            # 关闭监控系统
            if self.monitoring_initialized:
                print("正在关闭监控系统...")
                shutdown_monitoring()
                print("✓ 监控系统已关闭")

            print("✓ 应用已安全关闭")

        except Exception as e:
            print(f"关闭应用时出错: {e}")

    def _shutdown_application_components(self):
        """关闭应用组件"""
        try:
            # 关闭任务队列
            if self.logger:
                self.logger.info("正在关闭任务队列...")
            print("✓ 任务队列已关闭")

            # 关闭API服务器
            if self.logger:
                self.logger.info("正在关闭API服务器...")
            print("✓ API服务器已关闭")

            # 关闭数据库连接
            if self.logger:
                self.logger.info("正在关闭数据库连接...")
            print("✓ 数据库连接已关闭")

        except Exception as e:
            if self.logger:
                self.logger.error(f"关闭应用组件失败: {e}")

    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}")
        self.running = False


def show_monitoring_status():
    """显示监控状态"""
    try:
        components = get_monitoring_components()
        if not components['logger']:
            print("监控系统未启动")
            return

        print("\n" + "=" * 60)
        print("当前监控状态")
        print("=" * 60)

        # 系统健康
        if components['performance_monitor']:
            health = components['performance_monitor'].get_system_health()
            print(f"系统状态: {health.get('status', 'unknown')}")
            print(f"CPU使用率: {health.get('cpu_percent', 0):.1f}%")
            print(f"内存使用率: {health.get('memory_percent', 0):.1f}%")

        # 错误统计
        if components['error_tracker']:
            stats = components['error_tracker'].get_error_statistics(1)
            print(f"最近1小时错误: {stats.get('total_errors', 0)}")

        # 告警状态
        if components['alert_manager']:
            active_alerts = components['alert_manager'].get_active_alerts()
            print(f"活跃告警: {len(active_alerts)}")

        print("=" * 60)

    except Exception as e:
        print(f"获取监控状态失败: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='1688sync 应用启动器')
    parser.add_argument('--config', '-c', help='监控配置文件路径')
    parser.add_argument('--no-monitoring', action='store_true', help='禁用监控系统')
    parser.add_argument('--status', '-s', action='store_true', help='显示监控状态')
    args = parser.parse_args()

    # 如果只是查看状态
    if args.status:
        show_monitoring_status()
        return

    # 创建应用实例
    app = ApplicationWithMonitoring()

    # 设置信号处理器
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)

    try:
        # 初始化应用
        config_file = None if args.no_monitoring else args.config
        if not app.initialize(config_file):
            sys.exit(1)

        # 运行应用
        app.run()

    except Exception as e:
        print(f"应用运行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()