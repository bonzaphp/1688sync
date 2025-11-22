"""
监控初始化器 - 初始化和配置所有监控组件
"""

import logging
from typing import Optional, Dict, Any

from .logger import StructuredLogger, get_logger
from .monitor import PerformanceMonitor, performance_monitor
from .error_tracker import ErrorTracker, error_tracker
from .alert_manager import AlertManager, alert_manager
from .log_analyzer import LogAnalyzer, log_analyzer


class MonitoringInitializer:
    """监控初始化器"""

    def __init__(self):
        self.logger: Optional[StructuredLogger] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.error_tracker: Optional[ErrorTracker] = None
        self.alert_manager: Optional[AlertManager] = None
        self.log_analyzer: Optional[LogAnalyzer] = None
        self.initialized = False

    def initialize_monitoring(self, config: Dict[str, Any] = None) -> bool:
        """初始化监控系统"""
        try:
            if self.initialized:
                return True

            config = config or {}

            # 1. 初始化结构化日志
            self._initialize_logger(config.get('logging', {}))

            # 2. 初始化性能监控
            self._initialize_performance_monitor(config.get('performance', {}))

            # 3. 初始化错误追踪
            self._initialize_error_tracker(config.get('error_tracking', {}))

            # 4. 初始化告警管理
            self._initialize_alert_manager(config.get('alerting', {}))

            # 5. 初始化日志分析
            self._initialize_log_analyzer(config.get('log_analysis', {}))

            # 6. 设置组件间的集成
            self._setup_integrations()

            # 7. 创建默认告警规则
            self._create_default_alert_rules()

            self.initialized = True
            self.logger.info("监控系统初始化完成")

            return True

        except Exception as e:
            print(f"监控系统初始化失败: {e}")
            return False

    def _initialize_logger(self, config: Dict[str, Any]):
        """初始化日志记录器"""
        try:
            self.logger = StructuredLogger()

            # 设置日志级别
            if 'level' in config:
                from .logger import LogLevel
                self.logger.set_level(LogLevel(config['level']))

        except Exception as e:
            raise Exception(f"日志初始化失败: {e}")

    def _initialize_performance_monitor(self, config: Dict[str, Any]):
        """初始化性能监控"""
        try:
            collection_interval = config.get('collection_interval', 30)
            history_size = config.get('history_size', 1000)

            self.performance_monitor = PerformanceMonitor(
                collection_interval=collection_interval,
                history_size=history_size
            )

            # 启动监控
            if config.get('auto_start', True):
                self.performance_monitor.start_monitoring()

        except Exception as e:
            raise Exception(f"性能监控初始化失败: {e}")

    def _initialize_error_tracker(self, config: Dict[str, Any]):
        """初始化错误追踪"""
        try:
            max_events = config.get('max_events', 10000)
            cleanup_interval = config.get('cleanup_interval', 3600)

            self.error_tracker = ErrorTracker(
                max_events=max_events,
                cleanup_interval=cleanup_interval
            )

        except Exception as e:
            raise Exception(f"错误追踪初始化失败: {e}")

    def _initialize_alert_manager(self, config: Dict[str, Any]):
        """初始化告警管理"""
        try:
            max_alerts = config.get('max_alerts', 10000)
            self.alert_manager = AlertManager(max_alerts=max_alerts)

            # 启动评估
            if config.get('auto_start', True):
                self.alert_manager.start_evaluation()

            # 配置通知渠道
            self._setup_notification_channels(config.get('notifications', {}))

        except Exception as e:
            raise Exception(f"告警管理初始化失败: {e}")

    def _setup_notification_channels(self, notifications_config: Dict[str, Any]):
        """设置通知渠道"""
        try:
            # 邮件通知
            email_config = notifications_config.get('email')
            if email_config and email_config.get('enabled'):
                from .alert_manager import EmailNotificationChannel
                email_channel = EmailNotificationChannel(
                    smtp_host=email_config['smtp_host'],
                    smtp_port=email_config['smtp_port'],
                    username=email_config['username'],
                    password=email_config['password'],
                    from_email=email_config['from_email'],
                    to_emails=email_config['to_emails'],
                    use_tls=email_config.get('use_tls', True)
                )
                self.alert_manager.add_notification_channel('email', email_channel)

            # Webhook通知
            webhook_config = notifications_config.get('webhook')
            if webhook_config and webhook_config.get('enabled'):
                from .alert_manager import WebhookNotificationChannel
                webhook_channel = WebhookNotificationChannel(
                    webhook_url=webhook_config['url'],
                    headers=webhook_config.get('headers', {}),
                    timeout=webhook_config.get('timeout', 30)
                )
                self.alert_manager.add_notification_channel('webhook', webhook_channel)

        except Exception as e:
            self.logger.warning(f"设置通知渠道失败: {e}")

    def _initialize_log_analyzer(self, config: Dict[str, Any]):
        """初始化日志分析"""
        try:
            analysis_interval = config.get('analysis_interval', 300)
            max_patterns = config.get('max_patterns', 1000)

            self.log_analyzer = LogAnalyzer(
                analysis_interval=analysis_interval,
                max_patterns=max_patterns
            )

            # 启动分析
            if config.get('auto_start', True):
                self.log_analyzer.start_analysis()

        except Exception as e:
            raise Exception(f"日志分析初始化失败: {e}")

    def _setup_integrations(self):
        """设置组件间的集成"""
        try:
            # 错误事件触发告警
            def on_error_event(error_event):
                from .alert_manager import create_error_rule
                from .error_tracker import ErrorSeverity
                from .alert_manager import AlertLevel

                # 根据错误严重程度触发不同级别的告警
                severity_mapping = {
                    ErrorSeverity.LOW: AlertLevel.INFO,
                    ErrorSeverity.MEDIUM: AlertLevel.WARNING,
                    ErrorSeverity.HIGH: AlertLevel.ERROR,
                    ErrorSeverity.CRITICAL: AlertLevel.CRITICAL
                }

                alert_level = severity_mapping.get(error_event.severity, AlertLevel.WARNING)

                # 创建临时告警规则（简化处理）
                # 实际应该有预定义的规则
                pass

            self.error_tracker.add_error_callback(on_error_event)

            # 性能指标异常触发告警
            def on_metric_value(metric_value):
                from .monitor import MetricType

                if metric_value.metric_type == MetricType.GAUGE:
                    # 检查仪表盘指标的异常情况
                    if 'cpu_percent' in metric_value.name and metric_value.value > 90:
                        self._trigger_performance_alert(
                            'high_cpu', f"CPU使用率过高: {metric_value.value:.1f}%"
                        )
                    elif 'memory_percent' in metric_value.name and metric_value.value > 85:
                        self._trigger_performance_alert(
                            'high_memory', f"内存使用率过高: {metric_value.value:.1f}%"
                        )

            self.performance_monitor.add_metric_callback(on_metric_value)

        except Exception as e:
            self.logger.error(f"设置组件集成失败: {e}")

    def _trigger_performance_alert(self, alert_type: str, message: str):
        """触发性能告警"""
        try:
            from .alert_manager import Alert, AlertLevel, AlertStatus

            alert = Alert(
                id=f"perf_{alert_type}_{int(time.time())}",
                rule_id=f"auto_{alert_type}",
                rule_name=f"自动性能告警 - {alert_type}",
                level=AlertLevel.WARNING,
                status=AlertStatus.ACTIVE,
                message=message,
                details={'alert_type': alert_type, 'auto_generated': True},
                triggered_at=datetime.now()
            )

            # 这里应该通过alert_manager处理，简化处理
            self.logger.warning(f"性能告警: {message}")

        except Exception as e:
            self.logger.error(f"触发性能告警失败: {e}")

    def _create_default_alert_rules(self):
        """创建默认告警规则"""
        try:
            from .alert_manager import create_metric_rule, create_error_rule, AlertLevel

            # CPU使用率告警
            cpu_rule = create_metric_rule(
                name="CPU使用率过高",
                metric_name="system.cpu_percent",
                threshold=80.0,
                level=AlertLevel.WARNING,
                operator='gt',
                aggregation='avg',
                time_window=300
            )
            self.alert_manager.add_rule(cpu_rule)

            # 内存使用率告警
            memory_rule = create_metric_rule(
                name="内存使用率过高",
                metric_name="system.memory_percent",
                threshold=85.0,
                level=AlertLevel.WARNING,
                operator='gt',
                aggregation='avg',
                time_window=300
            )
            self.alert_manager.add_rule(memory_rule)

            # 错误率告警
            error_rule = create_error_rule(
                name="错误数量异常",
                threshold=10,
                level=AlertLevel.ERROR,
                time_window=3600
            )
            self.alert_manager.add_rule(error_rule)

            self.logger.info("默认告警规则已创建")

        except Exception as e:
            self.logger.error(f"创建默认告警规则失败: {e}")

    def shutdown(self):
        """关闭监控系统"""
        try:
            if self.performance_monitor:
                self.performance_monitor.stop_monitoring()

            if self.alert_manager:
                self.alert_manager.stop_evaluation()

            if self.log_analyzer:
                self.log_analyzer.stop_analysis()

            if self.error_tracker:
                self.error_tracker.cleanup()

            self.initialized = False
            print("监控系统已关闭")

        except Exception as e:
            print(f"关闭监控系统失败: {e}")


# 全局初始化器实例
monitoring_initializer = MonitoringInitializer()


def initialize_monitoring(config: Dict[str, Any] = None) -> bool:
    """初始化监控系统"""
    return monitoring_initializer.initialize_monitoring(config)


def get_monitoring_components():
    """获取监控组件"""
    return {
        'logger': monitoring_initializer.logger,
        'performance_monitor': monitoring_initializer.performance_monitor,
        'error_tracker': monitoring_initializer.error_tracker,
        'alert_manager': monitoring_initializer.alert_manager,
        'log_analyzer': monitoring_initializer.log_analyzer
    }


def shutdown_monitoring():
    """关闭监控系统"""
    monitoring_initializer.shutdown()