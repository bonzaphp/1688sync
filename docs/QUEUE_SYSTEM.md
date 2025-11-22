# 1688sync 队列调度系统

## 概述

1688sync队列调度系统是基于Celery + Redis构建的分布式任务队列系统，提供了完整的任务调度、监控、恢复和断点续传功能。

## 核心功能

### 1. 任务管理
- **任务创建与调度**: 支持创建不同优先级和队列的任务
- **任务状态监控**: 实时监控任务执行状态和进度
- **批量任务处理**: 支持大规模批量任务的创建和管理

### 2. 任务调度
- **定时调度**: 支持间隔调度和Cron表达式调度
- **延迟调度**: 支持指定时间点的延迟执行
- **批量调度**: 支持大批量任务的分批次调度

### 3. 监控系统
- **进度监控**: 实时监控任务执行进度和速度
- **状态监控**: 监控系统整体健康状态和性能指标
- **告警系统**: 基于阈值的自动告警机制

### 4. 恢复机制
- **断点续传**: 支持任务检查点保存和恢复
- **智能重试**: 基于异常类型的智能重试策略
- **任务恢复**: 支持从检查点或重新开始恢复任务

## 架构设计

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   任务创建器     │    │   调度器        │    │   Worker节点     │
│                │    │                │    │                │
│ • 任务管理      │───▶│ • 定时调度      │───▶│ • 任务执行      │
│ • 优先级管理    │    │ • 批量调度      │    │ • 进度报告      │
│ • 队列分配      │    │ • 负载均衡      │    │ • 检查点保存    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis消息代理  │    │   监控系统      │    │   恢复系统      │
│                │    │                │    │                │
│ • 任务队列      │    │ • 进度监控      │    │ • 检查点管理    │
│ • 结果存储      │    │ • 状态监控      │    │ • 任务恢复      │
│ • 消息路由      │    │ • 性能分析      │    │ • 智能重试      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. Redis配置

确保Redis服务正在运行：

```bash
# 启动Redis
redis-server

# 检查Redis状态
redis-cli ping
```

### 3. 环境配置

复制环境配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置Redis连接：

```bash
# Redis配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Celery配置
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIME_LIMIT=1800
CELERY_TASK_SOFT_TIME_LIMIT=1500
```

## 使用指南

### 1. 启动服务

#### 启动Worker

```bash
python scripts/queue/start_worker.py
```

或使用Celery命令：

```bash
celery -A src.queue.celery_app worker --loglevel=info --concurrency=4
```

#### 启动调度器

```bash
python scripts/queue/start_beat.py
```

或使用Celery命令：

```bash
celery -A src.queue.celery_app beat --loglevel=info
```

### 2. 命令行工具

#### 系统状态检查

```bash
python scripts/queue/queue_cli.py status
```

#### 任务管理

```bash
# 创建任务
python scripts/queue/queue_cli.py task create src.queue.tasks.crawler.fetch_products -k '{"category_id": "123", "page_size": 50}'

# 查看任务信息
python scripts/queue/queue_cli.py task info <task_id>

# 列出活跃任务
python scripts/queue/queue_cli.py task list

# 取消任务
python scripts/queue/queue_cli.py task cancel <task_id>
```

#### 调度管理

```bash
# 添加定时调度
python scripts/queue/queue_cli.py schedule add daily_sync src.queue.tasks.data_sync.sync_products -t cron -c "0 2 * * *"

# 列出调度任务
python scripts/queue/queue_cli.py schedule list

# 移除调度任务
python scripts/queue/queue_cli.py schedule remove daily_sync
```

#### 监控和恢复

```bash
# 系统健康检查
python scripts/queue/queue_cli.py monitor health

# 进度监控
python scripts/queue/queue_cli.py monitor progress

# 查看检查点
python scripts/queue/queue_cli.py recovery checkpoints <task_id>

# 恢复任务
python scripts/queue/queue_cli.py recovery resume <task_id>
```

### 3. 编程接口

#### 创建任务

```python
from src.queue.manager import queue_manager

# 创建简单任务
task_id = queue_manager.create_task(
    task_name='src.queue.tasks.crawler.fetch_products',
    kwargs={'category_id': '123', 'page_size': 50},
    priority=TaskPriority.NORMAL,
    queue='crawler'
)

# 创建批量任务
task_ids = queue_manager.create_batch_task(
    task_name='src.queue.tasks.image_processing.download_images',
    items=image_urls,
    batch_size=100
)
```

#### 任务调度

```python
from src.queue.scheduler import ScheduleConfig, ScheduleType

# 添加定时调度
config = ScheduleConfig(
    name='daily_sync',
    task='src.queue.tasks.data_sync.sync_products',
    schedule_type=ScheduleType.CRON,
    cron_expression='0 2 * * *',  # 每天凌晨2点
    kwargs={'sync_type': 'incremental'}
)

queue_manager.add_schedule(config)
```

#### 监控和恢复

```python
# 获取系统健康状态
health = queue_manager.get_system_health()

# 获取任务进度
progress = queue_manager.get_running_tasks_progress()

# 恢复任务
result = queue_manager.resume_task(task_id, strategy='auto')
```

## 任务类型

### 1. 爬虫任务

- `src.queue.tasks.crawler.fetch_products`: 获取产品列表
- `src.queue.tasks.crawler.fetch_product_details`: 获取产品详情
- `src.queue.tasks.crawler.fetch_suppliers`: 获取供应商信息
- `src.queue.tasks.crawler.sync_category`: 同步整个分类

### 2. 图片处理任务

- `src.queue.tasks.image_processing.download_images`: 下载图片
- `src.queue.tasks.image_processing.resize_images`: 调整图片大小
- `src.queue.tasks.image_processing.optimize_images`: 优化图片
- `src.queue.tasks.image_processing.generate_thumbnails`: 生成缩略图

### 3. 数据同步任务

- `src.queue.tasks.data_sync.sync_products`: 同步产品数据
- `src.queue.tasks.data_sync.sync_suppliers`: 同步供应商数据
- `src.queue.tasks.data_sync.validate_data`: 数据验证
- `src.queue.tasks.data_sync.cleanup_duplicates`: 清理重复数据

### 4. 批量处理任务

- `src.queue.tasks.batch_processing.batch_import`: 批量导入
- `src.queue.tasks.batch_processing.batch_export`: 批量导出
- `src.queue.tasks.batch_processing.batch_update`: 批量更新
- `src.queue.tasks.batch_processing.batch_delete`: 批量删除

## 队列配置

### 队列类型

- `default`: 默认队列，用于一般任务
- `crawler`: 爬虫任务队列
- `image_processing`: 图片处理队列
- `data_sync`: 数据同步队列
- `batch_processing`: 批量处理队列

### 优先级

- `LOW` (0): 低优先级
- `NORMAL` (5): 普通优先级
- `HIGH` (8): 高优先级
- `URGENT` (10): 紧急优先级

## 监控指标

### 系统指标

- **错误率**: 任务失败比例
- **成功率**: 任务成功比例
- **平均响应时间**: 任务平均执行时间
- **吞吐量**: 单位时间处理的任务数

### Worker指标

- **活跃Worker数**: 正在运行的Worker数量
- **任务负载**: 每个Worker的当前任务数
- **内存使用**: Worker进程内存占用
- **CPU使用**: Worker进程CPU占用

### 队列指标

- **队列深度**: 待处理任务数量
- **处理速度**: 任务处理速度
- **等待时间**: 任务平均等待时间

## 恢复策略

### 恢复类型

1. **RETRY**: 简单重试任务
2. **RESUME**: 从检查点恢复
3. **RESTART**: 重新开始任务
4. **SKIP**: 跳过任务
5. **MANUAL**: 手动处理

### 检查点机制

- 自动保存任务进度和状态
- 支持手动创建检查点
- 校验和验证数据完整性
- 自动清理过期检查点

### 智能重试

- 基于异常类型的重试策略
- 指数退避算法
- 最大重试次数限制
- 可配置的重试延迟

## 最佳实践

### 1. 任务设计

- 保持任务原子性和幂等性
- 合理设置任务超时时间
- 实现适当的进度报告
- 添加必要的错误处理

### 2. 队列管理

- 根据任务类型使用不同队列
- 合理设置Worker并发数
- 监控队列深度，及时扩容
- 定期清理过期数据

### 3. 监控和告警

- 设置合理的监控阈值
- 配置关键指标告警
- 定期检查系统健康状态
- 建立运维响应流程

### 4. 恢复策略

- 为关键任务启用检查点
- 配置合适的重试策略
- 定期测试任务恢复功能
- 建立手动恢复流程

## 故障排除

### 常见问题

1. **Worker无响应**
   - 检查Redis连接
   - 查看Worker日志
   - 重启Worker进程

2. **任务堆积**
   - 增加Worker数量
   - 检查任务执行时间
   - 优化任务逻辑

3. **内存泄漏**
   - 监控Worker内存使用
   - 设置任务执行次数限制
   - 定期重启Worker

4. **检查点失败**
   - 检查存储空间
   - 验证数据完整性
   - 查看错误日志

### 日志分析

```bash
# 查看Worker日志
tail -f logs/celery_worker.log

# 查看Beat日志
tail -f logs/celery_beat.log

# 查看错误日志
grep ERROR logs/celery_*.log
```

## 性能优化

### 1. Worker优化

- 调整并发数量
- 优化任务预取设置
- 使用进程池而非线程池
- 启用任务结果压缩

### 2. Redis优化

- 配置适当的内存策略
- 使用持久化机制
- 优化网络连接
- 监控Redis性能

### 3. 任务优化

- 减少任务间依赖
- 使用批量处理
- 实现任务合并
- 优化数据传输

## 扩展开发

### 自定义任务

```python
from src.queue.tasks.base import BaseTask, TaskResult, register_task

@register_task('custom.my_task')
class MyCustomTask(BaseTask):
    def execute(self, *args, **kwargs) -> TaskResult:
        # 实现任务逻辑
        return TaskResult(success=True, data=result)
```

### 自定义监控

```python
from src.queue.monitors.progress_monitor import progress_monitor

def my_progress_callback(progress_update):
    # 处理进度更新
    print(f"Task {progress_update.task_id}: {progress_update.percent}%")

progress_monitor.add_progress_callback(my_progress_callback)
```

## 部署建议

### 1. 生产环境

- 使用多个Worker节点
- 配置Redis集群
- 启用监控和告警
- 设置日志轮转

### 2. 容器化部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "scripts/queue/start_worker.py"]
```

### 3. 监控集成

- 集成Prometheus监控
- 配置Grafana仪表盘
- 设置Sentry错误追踪
- 使用ELK日志分析

## 许可证

本项目采用MIT许可证，详见LICENSE文件。