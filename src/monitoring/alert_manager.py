"""
告警管理器 - 监控指标和错误，根据规则触发告警
"""

import json
import smtplib
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional, Any, Callable, Union
from urllib.parse import urljoin

from .error_tracker import ErrorEvent, ErrorSeverity
from .logger import get_logger
from .monitor import MetricValue

logger = get_logger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    level: AlertLevel
    condition_type: str  # metric, error, log
    condition_config: Dict[str, Any]
    threshold: float
    time_window: int  # seconds
    evaluation_interval: int  # seconds
    enabled: bool = True
    notification_channels: List[str] = None
    cooldown_period: int = 300  # seconds
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = []
        if self.tags is None:
            self.tags = {}


@dataclass
class Alert:
    """告警事件"""
    id: str
    rule_id: str
    rule_name: str
    level: AlertLevel
    status: AlertStatus
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    last_sent: Optional[datetime] = None
    send_count: int = 0
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    def test(self) -> bool:
        """测试连接"""
        pass


class EmailNotificationChannel(NotificationChannel):
    """邮件通知渠道"""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_email: str, to_emails: List[str], use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

    def send(self, alert: Alert) -> bool:
        """发送邮件通知"""
        try:
            # 创建邮件
            msg = MimeMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{alert.level.value.upper()}] {alert.rule_name}"

            # 邮件正文
            body = self._create_email_body(alert)
            msg.attach(MimeText(body, 'html', 'utf-8'))

            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"邮件通知已发送: {alert.id}")
            return True

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}", exc_info=True)
            return False

    def _create_email_body(self, alert: Alert) -> str:
        """创建邮件正文"""
        return f"""
        <html>
        <body>
            <h2>告警通知</h2>
            <table border="1" style="border-collapse: collapse;">
                <tr><td><strong>告警ID</strong></td><td>{alert.id}</td></tr>
                <tr><td><strong>规则名称</strong></td><td>{alert.rule_name}</td></tr>
                <tr><td><strong>级别</strong></td><td>{alert.level.value}</td></tr>
                <tr><td><strong>状态</strong></td><td>{alert.status.value}</td></tr>
                <tr><td><strong>消息</strong></td><td>{alert.message}</td></tr>
                <tr><td><strong>触发时间</strong></td><td>{alert.triggered_at}</td></tr>
                <tr><td><strong>发送次数</strong></td><td>{alert.send_count}</td></tr>
            </table>

            <h3>详细信息</h3>
            <pre>{json.dumps(alert.details, indent=2, ensure_ascii=False)}</pre>
        </body>
        </html>
        """

    def test(self) -> bool:
        """测试邮件连接"""
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
            return True
        except Exception as e:
            logger.error(f"邮件连接测试失败: {e}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Webhook通知渠道"""

    def __init__(self, webhook_url: str, headers: Dict[str, str] = None,
                 timeout: int = 30):
        self.webhook_url = webhook_url
        self.headers = headers or {}
        self.timeout = timeout

    def send(self, alert: Alert) -> bool:
        """发送Webhook通知"""
        try:
            import requests

            payload = {
                'alert_id': alert.id,
                'rule_name': alert.rule_name,
                'level': alert.level.value,
                'status': alert.status.value,
                'message': alert.message,
                'details': alert.details,
                'triggered_at': alert.triggered_at.isoformat(),
                'tags': alert.tags
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            logger.info(f"Webhook通知已发送: {alert.id}")
            return True

        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}", exc_info=True)
            return False

    def test(self) -> bool:
        """测试Webhook连接"""
        try:
            import requests

            test_payload = {'test': True, 'timestamp': datetime.now().isoformat()}
            response = requests.post(
                self.webhook_url,
                json=test_payload,
                headers=self.headers,
                timeout=self.timeout
            )
            return response.status_code < 400

        except Exception as e:
            logger.error(f"Webhook连接测试失败: {e}")
            return False


class LogNotificationChannel(NotificationChannel):
    """日志通知渠道"""

    def send(self, alert: Alert) -> bool:
        """记录告警到日志"""
        try:
            logger.warning(
                f"告警触发: {alert.rule_name} - {alert.message}",
                details={
                    'alert_id': alert.id,
                    'level': alert.level.value,
                    'status': alert.status.value,
                    'details': alert.details,
                    'triggered_at': alert.triggered_at.isoformat()
                }
            )
            return True

        except Exception as e:
            logger.error(f"记录告警日志失败: {e}")
            return False

    def test(self) -> bool:
        """测试日志记录"""
        try:
            logger.info("告警日志渠道测试")
            return True
        except Exception:
            return False


class AlertManager:
    """告警管理器"""

    def __init__(self, max_alerts: int = 10000):
        self.max_alerts = max_alerts
        self.evaluation_active = False
        self.evaluation_thread: Optional[threading.Thread] = None

        # 存储数据
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=max_alerts)

        # 通知渠道
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self._setup_default_channels()

        # 统计信息
        self.alert_counts: Dict[AlertLevel, int] = defaultdict(int)
        self.rule_evaluations: Dict[str, int] = defaultdict(int)

        # 回调函数
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        self._lock = threading.Lock()

    def _setup_default_channels(self):
        """设置默认通知渠道"""
        self.notification_channels['log'] = LogNotificationChannel()

    def start_evaluation(self):
        """启动规则评估"""
        if self.evaluation_active:
            return

        self.evaluation_active = True
        self.evaluation_thread = threading.Thread(target=self._evaluation_loop, daemon=True)
        self.evaluation_thread.start()
        logger.info("告警评估器已启动")

    def stop_evaluation(self):
        """停止规则评估"""
        self.evaluation_active = False
        if self.evaluation_thread:
            self.evaluation_thread.join(timeout=10)
        logger.info("告警评估器已停止")

    def _evaluation_loop(self):
        """评估循环"""
        while self.evaluation_active:
            try:
                self._evaluate_all_rules()
                time.sleep(30)  # 每30秒评估一次
            except Exception as e:
                logger.error("告警评估循环异常", exc_info=True)
                time.sleep(30)

    def _evaluate_all_rules(self):
        """评估所有规则"""
        with self._lock:
            enabled_rules = [rule for rule in self.alert_rules.values() if rule.enabled]

        for rule in enabled_rules:
            try:
                if self._should_evaluate_rule(rule):
                    self._evaluate_rule(rule)
                    self.rule_evaluations[rule.id] += 1

            except Exception as e:
                logger.error(f"评估规则失败 {rule.name}: {e}")

    def _should_evaluate_rule(self, rule: AlertRule) -> bool:
        """检查是否应该评估规则"""
        # 检查评估间隔
        last_evaluation = self.rule_evaluations.get(rule.id, 0)
        if time.time() - last_evaluation < rule.evaluation_interval:
            return False

        return True

    def _evaluate_rule(self, rule: AlertRule):
        """评估单个规则"""
        try:
            if rule.condition_type == 'metric':
                triggered = self._evaluate_metric_rule(rule)
            elif rule.condition_type == 'error':
                triggered = self._evaluate_error_rule(rule)
            elif rule.condition_type == 'log':
                triggered = self._evaluate_log_rule(rule)
            else:
                logger.warning(f"未知的规则条件类型: {rule.condition_type}")
                return

            if triggered:
                self._trigger_alert(rule)

        except Exception as e:
            logger.error(f"评估规则失败 {rule.name}: {e}")

    def _evaluate_metric_rule(self, rule: AlertRule) -> bool:
        """评估指标规则"""
        try:
            from .monitor import performance_monitor

            metric_name = rule.condition_config.get('metric_name')
            if not metric_name:
                return False

            # 获取指标数据
            since = datetime.now() - timedelta(seconds=rule.time_window)
            metrics = performance_monitor.get_metric(metric_name, since)

            if not metrics:
                return False

            # 计算聚合值
            aggregation = rule.condition_config.get('aggregation', 'avg')
            if aggregation == 'avg':
                value = sum(m.value for m in metrics) / len(metrics)
            elif aggregation == 'max':
                value = max(m.value for m in metrics)
            elif aggregation == 'min':
                value = min(m.value for m in metrics)
            elif aggregation == 'count':
                value = len(metrics)
            else:
                value = metrics[-1].value if metrics else 0

            # 检查阈值
            operator = rule.condition_config.get('operator', 'gt')
            if operator == 'gt':
                return value > rule.threshold
            elif operator == 'gte':
                return value >= rule.threshold
            elif operator == 'lt':
                return value < rule.threshold
            elif operator == 'lte':
                return value <= rule.threshold
            elif operator == 'eq':
                return abs(value - rule.threshold) < 0.001

            return False

        except Exception as e:
            logger.error(f"评估指标规则失败: {e}")
            return False

    def _evaluate_error_rule(self, rule: AlertRule) -> bool:
        """评估错误规则"""
        try:
            from .error_tracker import error_tracker

            error_type = rule.condition_config.get('error_type')
            severity = rule.condition_config.get('severity')

            # 获取错误统计
            stats = error_tracker.get_error_statistics(
                hours=rule.time_window // 3600
            )

            if error_type:
                error_count = stats['by_type'].get(error_type, 0)
            elif severity:
                error_count = stats['by_severity'].get(severity, 0)
            else:
                error_count = stats['total_errors']

            return error_count >= rule.threshold

        except Exception as e:
            logger.error(f"评估错误规则失败: {e}")
            return False

    def _evaluate_log_rule(self, rule: AlertRule) -> bool:
        """评估日志规则"""
        try:
            from .logger import structured_logger

            level = rule.condition_config.get('level', 'ERROR')
            pattern = rule.condition_config.get('pattern')

            # 获取日志文件
            log_files = structured_logger.get_log_files()
            if not log_files:
                return False

            # 读取最近的日志
            cutoff_time = datetime.now() - timedelta(seconds=rule.time_window)
            matching_count = 0

            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                log_entry = json.loads(line)
                                log_time = datetime.fromisoformat(log_entry.get('timestamp', ''))

                                if log_time >= cutoff_time:
                                    if log_entry.get('level') == level:
                                        if pattern is None or pattern in log_entry.get('message', ''):
                                            matching_count += 1
                            except (json.JSONDecodeError, ValueError):
                                continue

                except Exception:
                    continue

            return matching_count >= rule.threshold

        except Exception as e:
            logger.error(f"评估日志规则失败: {e}")
            return False

    def _trigger_alert(self, rule: AlertRule):
        """触发告警"""
        try:
            alert_id = f"alert_{int(time.time() * 1000)}_{hash(rule.id) % 10000}"

            # 检查是否已有活跃告警
            if rule.id in self.active_alerts:
                existing_alert = self.active_alerts[rule.id]

                # 检查冷却期
                if (existing_alert.last_sent and
                    time.time() - existing_alert.last_sent.timestamp() < rule.cooldown_period):
                    return

                # 更新现有告警
                existing_alert.send_count += 1
                existing_alert.last_sent = datetime.now()
                alert = existing_alert
            else:
                # 创建新告警
                alert = Alert(
                    id=alert_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    level=rule.level,
                    status=AlertStatus.ACTIVE,
                    message=self._generate_alert_message(rule),
                    details=self._generate_alert_details(rule),
                    triggered_at=datetime.now(),
                    tags=rule.tags
                )

                with self._lock:
                    self.active_alerts[rule.id] = alert
                    self.alert_history.append(alert)
                    self.alert_counts[rule.level] += 1

            # 发送通知
            self._send_notifications(alert, rule)

            # 调用回调
            self._trigger_alert_callbacks(alert)

            logger.warning(f"告警已触发: {alert.id}", details={
                'rule_name': rule.name,
                'level': rule.level.value,
                'message': alert.message
            })

        except Exception as e:
            logger.error(f"触发告警失败: {e}")

    def _generate_alert_message(self, rule: AlertRule) -> str:
        """生成告警消息"""
        if rule.condition_type == 'metric':
            metric_name = rule.condition_config.get('metric_name', 'unknown')
            operator = rule.condition_config.get('operator', 'gt')
            return f"指标 {metric_name} {operator} {rule.threshold}"
        elif rule.condition_type == 'error':
            error_type = rule.condition_config.get('error_type', 'any')
            return f"错误 {error_type} 超过阈值 {rule.threshold}"
        elif rule.condition_type == 'log':
            level = rule.condition_config.get('level', 'ERROR')
            pattern = rule.condition_config.get('pattern', '')
            return f"日志级别 {level} 匹配模式 '{pattern}' 超过阈值"
        else:
            return rule.description

    def _generate_alert_details(self, rule: AlertRule) -> Dict[str, Any]:
        """生成告警详情"""
        return {
            'rule_id': rule.id,
            'rule_description': rule.description,
            'condition_type': rule.condition_type,
            'condition_config': rule.condition_config,
            'threshold': rule.threshold,
            'time_window': rule.time_window,
            'evaluation_time': datetime.now().isoformat()
        }

    def _send_notifications(self, alert: Alert, rule: AlertRule):
        """发送通知"""
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                channel = self.notification_channels[channel_name]
                try:
                    success = channel.send(alert)
                    if success:
                        logger.debug(f"通知已发送: {channel_name}")
                    else:
                        logger.error(f"通知发送失败: {channel_name}")
                except Exception as e:
                    logger.error(f"通知发送异常 {channel_name}: {e}")

    def _trigger_alert_callbacks(self, alert: Alert):
        """触发告警回调"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调函数执行失败: {e}")

    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self._lock:
            self.alert_rules[rule.id] = rule
        logger.info(f"告警规则已添加: {rule.name}")

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        with self._lock:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"告警规则已移除: {rule_id}")

    def add_notification_channel(self, name: str, channel: NotificationChannel):
        """添加通知渠道"""
        self.notification_channels[name] = channel
        logger.info(f"通知渠道已添加: {name}")

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        try:
            with self._lock:
                for alert in self.active_alerts.values():
                    if alert.id == alert_id:
                        alert.status = AlertStatus.ACKNOWLEDGED
                        alert.acknowledged_at = datetime.now()
                        alert.acknowledged_by = acknowledged_by
                        logger.info(f"告警已确认: {alert_id} by {acknowledged_by}")
                        return True

            # 检查历史告警
            for alert in self.alert_history:
                if alert.id == alert_id and alert.status == AlertStatus.ACTIVE:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = datetime.now()
                    alert.acknowledged_by = acknowledged_by
                    return True

            return False

        except Exception as e:
            logger.error(f"确认告警失败: {e}")
            return False

    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """解决告警"""
        try:
            with self._lock:
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    alert.resolved_by = resolved_by
                    del self.active_alerts[alert_id]
                    logger.info(f"告警已解决: {alert_id} by {resolved_by}")
                    return True

            return False

        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            return list(self.active_alerts.values())

    def get_alert_history(self, hours: int = 24, level: AlertLevel = None) -> List[Alert]:
        """获取告警历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            alerts = [
                alert for alert in self.alert_history
                if alert.triggered_at >= cutoff_time
            ]

        if level:
            alerts = [alert for alert in alerts if alert.level == level]

        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)

    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取告警统计"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_alerts = [
                alert for alert in self.alert_history
                if alert.triggered_at >= cutoff_time
            ]

        # 按级别统计
        level_counts = defaultdict(int)
        status_counts = defaultdict(int)
        rule_counts = defaultdict(int)

        for alert in recent_alerts:
            level_counts[alert.level.value] += 1
            status_counts[alert.status.value] += 1
            rule_counts[alert.rule_name] += 1

        return {
            'time_range_hours': hours,
            'total_alerts': len(recent_alerts),
            'by_level': dict(level_counts),
            'by_status': dict(status_counts),
            'by_rule': dict(rule_counts),
            'active_alerts': len(self.active_alerts),
            'total_rules': len(self.alert_rules),
            'enabled_rules': len([r for r in self.alert_rules.values() if r.enabled])
        }

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def test_notification_channel(self, channel_name: str) -> bool:
        """测试通知渠道"""
        if channel_name not in self.notification_channels:
            return False

        return self.notification_channels[channel_name].test()


# 全局告警管理器实例
alert_manager = AlertManager()

# 便捷函数
def create_metric_rule(name: str, metric_name: str, threshold: float,
                      level: AlertLevel = AlertLevel.WARNING,
                      operator: str = 'gt', aggregation: str = 'avg',
                      time_window: int = 300) -> AlertRule:
    """创建指标告警规则"""
    rule_id = f"metric_{int(time.time())}_{hash(name) % 10000}"

    return AlertRule(
        id=rule_id,
        name=name,
        description=f"指标 {metric_name} {operator} {threshold}",
        level=level,
        condition_type='metric',
        condition_config={
            'metric_name': metric_name,
            'operator': operator,
            'aggregation': aggregation
        },
        threshold=threshold,
        time_window=time_window,
        evaluation_interval=60,
        notification_channels=['log']
    )

def create_error_rule(name: str, error_type: str = None, threshold: int = 5,
                     level: AlertLevel = AlertLevel.ERROR,
                     time_window: int = 3600) -> AlertRule:
    """创建错误告警规则"""
    rule_id = f"error_{int(time.time())}_{hash(name) % 10000}"

    condition_config = {'time_window': time_window}
    if error_type:
        condition_config['error_type'] = error_type

    return AlertRule(
        id=rule_id,
        name=name,
        description=f"错误 {error_type or 'any'} 超过 {threshold} 次",
        level=level,
        condition_type='error',
        condition_config=condition_config,
        threshold=threshold,
        time_window=time_window,
        evaluation_interval=300,
        notification_channels=['log']
    )