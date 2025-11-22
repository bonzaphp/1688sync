# 1688sync 监控日志系统

## 概述

1688sync监控日志系统提供了完整的监控、日志记录和错误追踪功能，包括：

- **结构化日志记录** - 统一的日志格式和管理
- **性能监控** - 系统和应用性能指标监控
- **错误追踪** - 错误捕获、分析和追踪
- **告警机制** - 基于规则的智能告警
- **日志分析** - 自动化日志模式识别和异常检测

## 快速开始

### 1. 初始化监控系统

```python
from src.monitoring.initializer import initialize_monitoring

# 使用默认配置启动
success = initialize_monitoring()

# 或使用自定义配置文件
success = initialize_monitoring(config_file="monitoring_config.json")
```

### 2. 基本使用

```python
from src.monitoring.integration import monitor_execution, monitor_api_request
from src.monitoring.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 监控函数执行
@monitor_execution(metric_name="data_processing")
def process_data(data):
    logger.info("开始处理数据")
    # 业务逻辑
    return processed_data

# 监控API请求
@monitor_api_request(endpoint="/api/products", method="GET")
def get_products():
    # API逻辑
    return products
```

### 3. 命令行工具

```bash
# 启动监控系统
python -m src.monitoring.startup start --config monitoring_config.json --daemon

# 创建示例配置文件
python -m src.monitoring.startup create-config

# 查看监控状态
python -m src.monitoring.startup status

# 测试通知渠道
python -m src.monitoring.startup test

# 导出监控数据
python -m src.monitoring.startup export --format json --output monitoring_data.json
```

## 核心组件

### 1. 结构化日志记录器 (StructuredLogger)

提供统一的日志记录接口，支持多种输出格式和自动轮转。

```python
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# 基本日志记录
logger.info("用户登录", user_id="12345", session_id="sess_abc")

# 任务日志
logger.log_task_start("task_123", "图片同步")
logger.log_task_complete("task_123", "图片同步", 1500.5)

# API日志
logger.log_api_request("GET", "/api/products", 200, 250.3)

# 数据库日志
logger.log_database_operation("SELECT", "products", 120.5, 25)

# 业务事件
logger.log_business_event("user_registered", user_id="12345")
```

### 2. 性能监控器 (PerformanceMonitor)

监控系统性能指标，包括CPU、内存、磁盘、网络等。

```python
from src.monitoring.monitor import increment_counter, set_gauge, record_timer

# 计数器
increment_counter("api_requests", 1, {"endpoint": "/api/products", "method": "GET"})

# 仪表盘指标
set_gauge("active_connections", 150)

# 计时器
record_timer("response_time", 250.5, {"endpoint": "/api/products"})

# 获取系统健康状态
from src.monitoring.monitor import performance_monitor
health = performance_monitor.get_system_health()
```

### 3. 错误追踪器 (ErrorTracker)

捕获、分析和追踪应用程序错误。

```python
from src.monitoring.error_tracker import capture_exception, track_errors, ErrorSeverity

# 手动捕获异常
try:
    risky_operation()
except Exception as e:
    capture_exception(e, severity=ErrorSeverity.HIGH)

# 使用装饰器自动追踪
@track_errors(severity=ErrorSeverity.MEDIUM)
def risky_function():
    # 函数逻辑
    pass

# 获取错误统计
from src.monitoring.error_tracker import error_tracker
stats = error_tracker.get_error_statistics(hours=24)
```

### 4. 告警管理器 (AlertManager)

基于规则的智能告警系统，支持多种通知渠道。

```python
from src.monitoring.alert_manager import (
    alert_manager, create_metric_rule, create_error_rule, AlertLevel
)

# 创建指标告警规则
cpu_rule = create_metric_rule(
    name="CPU使用率过高",
    metric_name="system.cpu_percent",
    threshold=80.0,
    level=AlertLevel.WARNING
)
alert_manager.add_rule(cpu_rule)

# 创建错误告警规则
error_rule = create_error_rule(
    name="错误数量异常",
    threshold=10,
    level=AlertLevel.ERROR
)
alert_manager.add_rule(error_rule)

# 获取活跃告警
active_alerts = alert_manager.get_active_alerts()
```

### 5. 日志分析器 (LogAnalyzer)

自动化日志分析，识别模式和异常。

```python
from src.monitoring.log_analyzer import log_analyzer

# 获取日志模式
patterns = log_analyzer.get_top_patterns(limit=10)

# 获取最近的异常
anomalies = log_analyzer.get_recent_anomalies(hours=24)

# 搜索日志
results = log_analyzer.search_logs("error", level="ERROR", hours=1)

# 生成分析报告
report = log_analyzer.generate_analysis_report(hours=24)
```

## 集成装饰器

### 函数执行监控

```python
from src.monitoring.integration import monitor_execution

@monitor_execution(metric_name="data_processing", log_args=True)
def process_data(data_size):
    # 业务逻辑
    return result
```

### API请求监控

```python
from src.monitoring.integration import monitor_api_request

@monitor_api_request(endpoint="/api/products", method="GET")
def get_products(page, limit):
    # API逻辑
    return products
```

### 数据库操作监控

```python
from src.monitoring.integration import monitor_database_operation

@monitor_database_operation(operation="SELECT", table="products")
def fetch_products(category):
    # 数据库查询
    return products
```

### 任务执行监控

```python
from src.monitoring.integration import monitor_task_execution

@monitor_task_execution(task_name="image_sync")
def sync_images(product_id):
    # 任务逻辑
    return True
```

## 配置

### 配置文件结构

```json
{
  "logging": {
    "level": "INFO",
    "structured_format": true,
    "include_stack_trace": true,
    "retention_days": 30
  },
  "performance": {
    "collection_interval": 30,
    "history_size": 1000,
    "auto_start": true
  },
  "error_tracking": {
    "max_events": 10000,
    "cleanup_interval": 3600,
    "auto_capture": true
  },
  "alerting": {
    "max_alerts": 10000,
    "evaluation_interval": 60,
    "notifications": {
      "email": {
        "enabled": false,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your-email@gmail.com",
        "password": "your-password",
        "from_email": "monitoring@yourcompany.com",
        "to_emails": ["admin@yourcompany.com"]
      },
      "webhook": {
        "enabled": false,
        "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      }
    }
  },
  "log_analysis": {
    "analysis_interval": 300,
    "max_patterns": 1000,
    "auto_start": true
  }
}
```

### 环境变量配置

```bash
# 日志级别
export MONITORING_LOG_LEVEL=INFO

# 性能监控间隔（秒）
export MONITORING_COLLECTION_INTERVAL=30

# 告警评估间隔（秒）
export MONITORING_EVALUATION_INTERVAL=60

# 邮件配置
export MONITORING_SMTP_HOST=smtp.gmail.com
export MONITORING_SMTP_PORT=587
export MONITORING_SMTP_USERNAME=your-email@gmail.com
export MONITORING_SMTP_PASSWORD=your-password
export MONITORING_FROM_EMAIL=monitoring@yourcompany.com
```

## 监控指标

### 系统指标

- `system.cpu_percent` - CPU使用率
- `system.memory_percent` - 内存使用率
- `system.disk_usage_percent` - 磁盘使用率
- `system.process_count` - 进程数量
- `system.network_io` - 网络IO统计

### 应用指标

- `active_requests` - 活跃请求数
- `total_requests` - 总请求数
- `error_count` - 错误计数
- `process_memory_mb` - 进程内存使用
- `process_cpu_percent` - 进程CPU使用率

### 自定义指标

```python
from src.monitoring.monitor import increment_counter, set_gauge

# 业务指标
increment_counter("user_registrations", 1, {"plan": "premium"})
set_gauge("active_sessions", 150)

# 队列指标
increment_counter("queue_messages_processed", 1, {"queue": "email"})
set_gauge("queue_depth", 25, {"queue": "email"})
```

## 最佳实践

### 1. 日志记录

- 使用结构化日志，包含足够的上下文信息
- 为不同的操作类型使用专门的日志方法
- 避免记录敏感信息
- 合理设置日志级别

### 2. 性能监控

- 监控关键路径的性能指标
- 设置合理的告警阈值
- 定期分析性能趋势
- 监控资源使用情况

### 3. 错误处理

- 使用装饰器自动追踪错误
- 为不同严重程度的错误设置不同的告警级别
- 定期分析错误模式和趋势
- 及时处理和解决告警

### 4. 告警配置

- 避免告警风暴，设置合理的冷却期
- 使用多级告警，区分严重程度
- 定期测试通知渠道
- 根据业务需求调整告警规则

## 故障排除

### 常见问题

1. **监控系统启动失败**
   - 检查配置文件格式和内容
   - 确认依赖包已安装
   - 检查日志文件权限

2. **告警通知不发送**
   - 验证通知渠道配置
   - 测试网络连接
   - 检查告警规则设置

3. **性能数据缺失**
   - 确认性能监控已启动
   - 检查系统权限
   - 验证指标名称正确

4. **日志分析不工作**
   - 检查日志文件格式
   - 确认分析器已启动
   - 验证时间范围设置

### 调试模式

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看组件状态
from src.monitoring.initializer import get_monitoring_components
components = get_monitoring_components()
```

## 扩展开发

### 自定义通知渠道

```python
from src.monitoring.alert_manager import NotificationChannel, Alert

class CustomNotificationChannel(NotificationChannel):
    def send(self, alert: Alert) -> bool:
        # 自定义通知逻辑
        return True

    def test(self) -> bool:
        # 测试逻辑
        return True

# 添加到告警管理器
alert_manager.add_notification_channel('custom', CustomNotificationChannel())
```

### 自定义分析器

```python
from src.monitoring.log_analyzer import LogAnalyzer

class CustomLogAnalyzer(LogAnalyzer):
    def _custom_analysis(self):
        # 自定义分析逻辑
        pass
```

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 支持

如有问题或建议，请通过以下方式联系：

- 创建 Issue
- 发送邮件到 support@1688sync.com
- 查看文档：https://docs.1688sync.com/monitoring