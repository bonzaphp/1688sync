# 1688sync 存储系统

1688sync 项目的存储系统，提供统一的数据存储、图片管理和备份恢复功能。

## 功能特性

### 🗄️ 数据库管理
- **PostgreSQL** 作为主数据库，支持 JSON 字段和高级查询
- **SQLAlchemy 2.0** ORM 框架，支持异步操作
- **连接池管理**，支持高并发访问
- **事务管理**，确保数据一致性
- **自动迁移**，使用 Alembic 管理数据库版本

### 📦 数据模型
- **供应商模型 (Supplier)**: 1688 供应商信息
- **商品模型 (Product)**: 商品详细信息
- **图片模型 (ProductImage)**: 商品图片管理
- **同步记录模型 (SyncRecord)**: 数据同步追踪

### 🖼️ 图片存储系统
- **本地文件存储**，支持图片自动分类
- **图片处理**：缩略图、压缩图生成
- **多格式支持**：JPEG、PNG、WebP
- **CDN 集成**（预留接口）
- **异步下载**，支持批量处理

### 🔍 数据访问层
- **仓储模式**，清晰的业务逻辑分离
- **CRUD 操作**，支持单条和批量操作
- **复杂查询**，支持条件搜索和分页
- **统计查询**，提供数据分析接口

### 🛡️ 数据一致性
- **外键约束**，保证关联数据完整性
- **软删除机制**，支持数据恢复
- **一致性检查**，自动发现数据问题
- **孤儿数据清理**，维护数据库整洁

### ⚡ 性能优化
- **数据库索引**，优化查询性能
- **连接池配置**，支持高并发
- **批量操作**，减少数据库 I/O
- **查询优化**，使用高级 SQL 特性

### 💾 备份恢复
- **数据库备份**：完整/增量备份
- **文件备份**：图片文件归档
- **配置备份**：系统配置保存
- **自动清理**：过期备份管理

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

### 2. 数据库设置

```bash
# 创建数据库
createdb -h localhost -U postgres 1688sync

# 运行迁移
alembic upgrade head
```

### 3. 基础使用

```python
import asyncio
from src import init_database, SupplierRepository, ProductRepository

async def main():
    # 初始化数据库
    await init_database()

    # 使用仓储类
    async with db_manager.get_session() as session:
        supplier_repo = SupplierRepository(session)
        product_repo = ProductRepository(session)

        # 创建供应商
        supplier = await supplier_repo.create_or_update_supplier(
            source_id="supplier_001",
            name="示例供应商"
        )

        # 创建商品
        product = await product_repo.create_or_update_product(
            source_id="product_001",
            title="示例商品",
            supplier_id=supplier.id
        )

        print(f"创建成功: 供应商 {supplier.name}, 商品 {product.title}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 项目结构

```
epic-1688sync/
├── src/
│   ├── models/           # 数据模型
│   │   ├── base.py      # 基础模型
│   │   ├── supplier.py  # 供应商模型
│   │   ├── product.py   # 商品模型
│   │   ├── image.py     # 图片模型
│   │   └── sync_record.py # 同步记录模型
│   ├── database/         # 数据库管理
│   │   ├── connection.py  # 连接管理
│   │   ├── transaction.py # 事务管理
│   │   ├── performance.py # 性能优化
│   │   └── migration_manager.py # 迁移管理
│   ├── services/         # 业务服务
│   │   ├── base_repository.py # 基础仓储
│   │   ├── supplier_repository.py # 供应商服务
│   │   ├── product_repository.py  # 商品服务
│   │   ├── image_repository.py    # 图片服务
│   │   ├── sync_repository.py     # 同步服务
│   │   ├── data_consistency.py     # 数据一致性
│   │   └── backup_restore.py      # 备份恢复
│   └── storage/          # 存储管理
│       └── image_storage.py # 图片存储
├── config/               # 配置文件
│   ├── database.py   # 数据库配置
│   └── settings.py  # 应用配置
├── migrations/           # 数据库迁移
│   ├── versions/     # 迁移脚本
│   ├── alembic.ini  # Alembic 配置
│   └── env.py       # 迁移环境
├── examples/            # 使用示例
│   └── storage_usage.py
├── images/             # 图片存储目录
├── backups/            # 备份目录
└── tests/              # 测试文件
```

## 核心组件

### 数据库连接管理

```python
from src.database import db_manager, get_db_session

# 使用上下文管理器
async with db_manager.get_session() as session:
    # 数据库操作
    pass

# 依赖注入方式
async with get_db_session() as session:
    # 数据库操作
    pass
```

### 事务管理

```python
from src.database import db_transaction, transactional

# 装饰器方式
@transactional()
async def update_product_data(product_id: int, data: dict, session):
    # 事务内的操作
    product = await product_repo.get_by_id(product_id)
    product.update_from_dict(data)
    return product

# 上下文管理器方式
async with db_transaction() as session:
    # 事务内的操作
    supplier = await supplier_repo.create(...)
    product = await product_repo.create(supplier_id=supplier.id)
    # 自动提交或回滚
```

### 图片存储

```python
from src.storage import image_storage

# 下载并处理图片
success, local_path, image_info = await image_storage.download_image(
    url="https://example.com/image.jpg",
    product_id=123
)

if success:
    print(f"图片保存到: {local_path}")
    print(f"图片信息: {image_info}")

# 获取访问URL
image_url = image_storage.get_image_url(local_path)
thumbnail_url = image_storage.get_thumbnail_url(local_path)
```

### 数据一致性

```python
from src.services import DataConsistencyManager

async with db_manager.get_session() as session:
    manager = DataConsistencyManager(session)

    # 完整性检查
    report = await manager.validate_data_integrity()
    print(f"发现问题: {report['total_issues']}")

    # 修复问题
    if not report['total_issues'] == 0:
        await manager.fix_supplier_product_consistency(dry_run=False)
```

### 备份恢复

```python
from src.services import backup_restore_manager

# 创建完整备份
backup_result = backup_restore_manager.create_full_backup(
    backup_name="production_backup",
    include_images=True,
    include_config=True
)

# 恢复备份
restore_result = backup_restore_manager.restore_database_backup(
    backup_name="production_backup",
    force=True
)
```

## 性能优化

### 数据库索引

系统自动创建以下索引：

- **主键索引**：所有表的 id 字段
- **唯一索引**：source_id 字段防止重复
- **外键索引**：提高关联查询性能
- **查询索引**：常用查询字段组合
- **全文索引**：商品标题搜索（GIN）

### 连接池配置

```python
# 推荐配置（生产环境）
pool_size=50          # 基础连接数
max_overflow=100      # 最大溢出连接
pool_timeout=30       # 获取连接超时
pool_recycle=3600     # 连接回收时间
pool_pre_ping=True     # 连接预检
```

### 批量操作

```python
# 批量插入
products_data = [{"title": f"商品{i}", ...} for i in range(1000)]
products = await product_repo.bulk_import_products(products_data)

# 批量更新
await product_repo.batch_update_sync_status(
    product_ids=[1, 2, 3],
    status="completed"
)
```

## 监控和维护

### 健康检查

```python
# 数据库健康检查
health = await db_manager.health_check()

# 存储统计
stats = await image_storage.get_storage_stats()

# 性能指标
metrics = await performance_manager.monitor_performance_metrics()
```

### 定期维护

```python
# 清理旧备份
cleanup_result = backup_restore_manager.cleanup_old_backups(days_to_keep=30)

# 优化数据库
optimize_result = await performance_manager.optimize_database()

# 数据一致性检查
consistency_result = await consistency_manager.validate_data_integrity()
```

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|---------|---------|------|
| `DB_HOST` | localhost | 数据库主机 |
| `DB_PORT` | 5432 | 数据库端口 |
| `DB_NAME` | 1688sync | 数据库名称 |
| `DB_USER` | postgres | 数据库用户 |
| `DB_PASSWORD` | - | 数据库密码 |
| `STORAGE_PATH` | ./images | 图片存储路径 |
| `MAX_FILE_SIZE` | 10485760 | 最大文件大小(字节) |
| `BATCH_SIZE` | 1000 | 批处理大小 |
| `CACHE_TTL` | 3600 | 缓存过期时间(秒) |

### 数据库配置

详细的数据库配置请参考 `config/database.py`，包括：
- 连接池参数
- SSL 配置
- 连接选项
- 超时设置

## 开发指南

### 添加新模型

1. 在 `src/models/` 下创建模型文件
2. 继承 `BaseModel` 基类
3. 定义字段和索引
4. 创建对应的仓储类
5. 生成迁移脚本

```bash
# 生成迁移
alembic revision --autogenerate -m "添加新模型"

# 应用迁移
alembic upgrade head
```

### 扩展存储功能

1. 在 `src/storage/` 下扩展存储类
2. 实现新的存储后端
3. 更新配置文件
4. 添加相应的测试

### 性能调优

1. 分析慢查询
2. 优化索引策略
3. 调整连接池参数
4. 使用缓存减少数据库访问

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_product_repository.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 部署

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY migrations/ ./migrations/

CMD ["python", "-m", "examples.storage_usage"]
```

### 生产环境配置

1. 设置合适的环境变量
2. 配置数据库 SSL
3. 设置连接池大小
4. 配置监控和日志
5. 设置定期备份

## 故障排除

### 常见问题

**Q: 数据库连接失败**
A: 检查数据库服务状态、网络连接、认证信息

**Q: 图片下载失败**
A: 检查 URL 有效性、网络连接、存储空间

**Q: 迁移失败**
A: 检查数据库权限、SQL 语法、依赖关系

**Q: 性能问题**
A: 检查索引使用情况、连接池配置、查询优化

### 日志分析

```bash
# 查看数据库日志
tail -f logs/database.log

# 查看应用日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/*.log
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request
5. 代码审查和合并

## 许可证

本项目采用 MIT 许可证，详情请参阅 LICENSE 文件。

## 支持

如有问题或建议，请：
1. 查看文档和示例
2. 搜索已有的 Issues
3. 创建新的 Issue
4. 联系开发团队

---

**注意**: 本系统是为 1688 数据同步项目专门设计的存储系统，请根据实际需求进行调整和扩展。