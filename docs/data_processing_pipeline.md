# 1688sync 数据处理管道

## 概述

1688sync数据处理管道是一个完整的数据质量保证系统，专为1688商品和供应商数据处理而设计。该管道提供了从数据清洗、验证、去重、版本管理到质量监控的全流程解决方案。

## 核心功能

### 1. 数据清洗和标准化 (DataCleaner)
- 文本内容清洗和标准化
- 价格信息提取和标准化
- 单位转换和标准化
- URL验证和格式化
- 联系方式标准化
- 日期格式标准化

### 2. 数据验证机制 (DataValidator)
- 必填字段验证
- 数据格式验证
- 数值范围验证
- 业务逻辑验证
- 多级验证结果（错误、警告、信息）

### 3. 去重算法 (DataDeduplicator)
- 精确匹配去重
- 模糊匹配去重
- 相似度计算
- 智能主记录选择
- 去重统计分析

### 4. 版本控制系统 (VersionManager)
- 数据变更追踪
- 版本比较和回滚
- 变更历史记录
- 批量版本管理
- 版本数据导入导出

### 5. 数据质量监控 (DataQualityMonitor)
- 完整性评估
- 准确性评估
- 一致性评估
- 有效性评估
- 唯一性评估
- 质量报告生成

### 6. 数据处理管道 (DataPipeline)
- 全流程自动化处理
- 可配置处理选项
- 处理结果统计
- 报告导出功能
- 错误处理和恢复

## 架构设计

```
src/data_processing/
├── __init__.py              # 模块导出
├── cleaner.py               # 数据清洗器
├── validator.py             # 数据验证器
├── deduplicator.py          # 数据去重器
├── version_manager.py       # 版本管理器
├── quality_monitor.py       # 质量监控器
└── pipeline.py              # 数据处理管道
```

## 快速开始

### 1. 基本使用

```python
from src.data_processing import DataPipeline

# 创建数据处理管道
pipeline = DataPipeline()

# 处理商品数据
raw_products = [
    {
        'source_id': 'product001',
        'title': 'iPhone 13',
        'price_text': '¥5000 - ¥6000',
        'main_image_url': 'https://example.com/iphone.jpg'
    }
]

# 执行处理
result = pipeline.process_products(raw_products)

# 查看结果
print(f"处理状态: {result.status}")
print(f"成功处理: {result.processed_records}")
print(f"质量评分: {result.quality_report.overall_score}")
```

### 2. 单独使用各组件

#### 数据清洗
```python
from src.data_processing import DataCleaner

cleaner = DataCleaner()
cleaned_data = cleaner.clean_product_data(raw_data)
```

#### 数据验证
```python
from src.data_processing import DataValidator

validator = DataValidator()
validation_results = validator.validate_product_data(data)
```

#### 数据去重
```python
from src.data_processing import DataDeduplicator

deduplicator = DataDeduplicator()
duplicate_groups = deduplicator.find_duplicate_products(products)
```

#### 版本管理
```python
from src.data_processing import VersionManager, ChangeType

version_manager = VersionManager()
version = version_manager.create_version(
    entity_type='product',
    entity_id='p001',
    data=product_data,
    change_type=ChangeType.CREATE
)
```

#### 质量监控
```python
from src.data_processing import DataQualityMonitor

monitor = DataQualityMonitor()
quality_report = monitor.assess_product_quality(products)
```

## 配置选项

### 管道处理选项
```python
options = {
    'skip_cleaning': False,          # 跳过数据清洗
    'skip_validation': False,        # 跳过数据验证
    'skip_deduplication': False,     # 跳过去重处理
    'skip_versioning': False,        # 跳过版本管理
    'skip_quality_monitoring': False # 跳过质量监控
}

result = pipeline.process_products(data, options)
```

### 验证规则配置
商品验证规则可在 `DataValidator.product_rules` 中配置：
```python
product_rules = {
    'required_fields': ['source_id', 'title'],
    'max_lengths': {
        'title': 500,
        'description': 2000
    },
    'price_ranges': {
        'min': 0.01,
        'max': 1000000
    }
}
```

### 去重配置
去重配置可在 `DataDeduplicator.product_config` 中调整：
```python
product_config = {
    'similarity_threshold': 0.85,  # 相似度阈值
    'key_fields': ['title', 'price_min'],
    'weight_config': {
        'title': 0.4,
        'price_min': 0.3
    }
}
```

## 队列集成

数据处理管道已集成到Celery队列系统中，提供了以下任务：

### 处理任务
- `process_raw_products` - 处理原始商品数据
- `process_raw_suppliers` - 处理原始供应商数据
- `batch_clean_data` - 批量数据清洗
- `quality_assessment` - 数据质量评估

### 使用队列任务
```python
from src.queue.tasks.data_processing import ProcessRawProductsTask

# 创建任务
task = ProcessRawProductsTask()

# 执行任务
result = task.execute(
    batch_size=100,
    source_system='1688',
    options={'skip_validation': False},
    export_report=True
)
```

## 测试

运行测试套件：
```bash
python -m pytest tests/test_data_processing.py -v
```

运行示例：
```bash
python examples/data_processing_example.py
```

## 性能优化

### 1. 批量处理
- 使用适当的批量大小（建议100-1000）
- 避免单条记录处理

### 2. 内存管理
- 大数据集分批处理
- 及时释放不需要的对象

### 3. 数据库优化
- 使用连接池
- 批量数据库操作
- 适当的索引

### 4. 并发处理
- 利用多进程处理独立数据
- 使用异步I/O操作

## 监控和日志

### 日志级别
- `DEBUG`: 详细调试信息
- `INFO`: 一般处理信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

### 关键指标
- 处理成功率
- 数据质量评分
- 处理时间
- 错误率

## 扩展开发

### 添加新的清洗规则
```python
def _clean_custom_field(self, value: str) -> str:
    """自定义字段清洗"""
    # 实现清洗逻辑
    return cleaned_value
```

### 添加新的验证规则
```python
def _validate_custom_rule(self, data: Dict[str, Any]) -> List[ValidationResult]:
    """自定义验证规则"""
    # 实现验证逻辑
    return validation_results
```

### 添加新的质量指标
```python
def _assess_custom_metric(self, data: List[Dict[str, Any]]) -> QualityMetric:
    """自定义质量指标"""
    # 实现评估逻辑
    return quality_metric
```

## 故障排除

### 常见问题

1. **内存不足**
   - 减少批量大小
   - 分批处理大数据集
   - 优化数据结构

2. **处理速度慢**
   - 检查数据库连接
   - 优化算法复杂度
   - 增加并发处理

3. **数据质量问题**
   - 调整验证规则
   - 修改清洗逻辑
   - 更新质量阈值

4. **版本冲突**
   - 检查版本一致性
   - 清理冲突版本
   - 重新同步数据

### 调试技巧
```python
# 启用详细日志
import logging
logging.getLogger('src.data_processing').setLevel(logging.DEBUG)

# 单步调试
cleaner = DataCleaner()
cleaned = cleaner.clean_product_data(test_data)
print(json.dumps(cleaned, indent=2))

# 验证结果
validator = DataValidator()
results = validator.validate_product_data(cleaned)
for result in results:
    print(f"{result.field}: {result.message}")
```

## 最佳实践

1. **数据预处理**
   - 在进入管道前进行基本格式检查
   - 移除明显无效的记录

2. **渐进式处理**
   - 先处理小批量测试
   - 逐步增加处理量
   - 监控性能指标

3. **错误处理**
   - 记录详细错误信息
   - 提供错误恢复机制
   - 定期清理失败记录

4. **质量保证**
   - 定期评估数据质量
   - 根据质量报告调整规则
   - 建立质量监控告警

5. **版本管理**
   - 定期清理旧版本
   - 重要变更前创建备份
   - 保持版本历史完整

## 更新日志

### v1.0.0 (2024-01-20)
- 初始版本发布
- 实现核心数据处理功能
- 集成队列系统
- 完善测试覆盖

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交代码变更
4. 运行测试验证
5. 提交Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。