# 1688sync - 1688商品数据同步系统

基于Scrapy构建的1688平台商品数据同步系统，支持大规模并发爬取、数据处理和API服务。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境
```bash
cp .env.example .env
# 编辑 .env 配置你的数据库和Redis连接
```

### 3. 初始化项目
```bash
python -m src.cli.main init
```

### 4. 运行爬虫
```bash
python -m src.cli.main run --category 服装 --limit 100
```

### 5. 查看状态
```bash
python -m src.cli.main status
```

## 📋 项目结构

```
1688sync/
├── src/                      # 源代码目录
│   ├── cli/                  # CLI工具
│   ├── config/               # 配置管理
│   ├── database/             # 数据库模型和连接
│   ├── scrapy_project/       # Scrapy爬虫项目
│   │   ├── spiders/         # 爬虫定义
│   │   ├── items.py          # 数据项
│   │   ├── pipelines.py      # 数据处理管道
│   │   └── settings.py      # Scrapy设置
│   └── api/                  # API服务（待开发）
├── tests/                     # 测试用例
├── data/                      # 数据目录
├── logs/                      # 日志目录
├── requirements.txt           # Python依赖
├── pyproject.toml            # 项目配置
└── README.md                  # 项目文档
```

## 🛠️ 技术栈

- **Python 3.10+**: 主要开发语言
- **Scrapy**: 爬虫框架
- **FastAPI**: API服务框架
- **SQLAlchemy**: ORM框架
- **MySQL/SQLite**: 数据库
- **Redis**: 缓存和任务队列
- **Celery**: 分布式任务队列
- **Click**: CLI框架

## 🎯 功能特性

### ✅ 已实现
- [x] 项目基础架构
- [x] 数据库模型设计
- [x] Scrapy爬虫框架
- [x] 数据验证和存储管道
- [x] CLI工具
- [x] 基础测试用例

### 🚧 开发中
- [ ] FastAPI服务
- [ ] Web管理界面
- [ ] 监控和日志系统
- [ ] 性能优化
- [ ] Docker部署

## 📊 使用说明

### CLI命令

```bash
# 初始化项目
python -m src.cli.main init

# 运行爬虫
python -m src.cli.main run

# 指定分类和数量
python -m src.cli.main run --category 服装 --limit 50

# 查看系统状态
python -m src.cli.main status

# 运行测试
python -m src.cli.main test

# 重置数据
python -m src.cli.main reset
```

### 数据库操作

```python
# 创建表
from src.database.connection import create_tables
create_tables()

# 查询商品
from src.database.connection import SessionLocal
from src.database.models import Product

db = SessionLocal()
products = db.query(Product).all()
db.close()
```

## 🔧 配置说明

### 环境变量
```bash
# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/1688sync
REDIS_URL=redis://localhost:6379/0

# API配置
API_HOST=0.0.0.0
API_PORT=8000

# 文件存储
DATA_DIR=./data
IMAGE_DIR=./data/images

# Scrapy配置
SCRAPY_CONCURRENT_REQUESTS=16
SCRAPY_DOWNLOAD_DELAY=1
```

## 🔍 监控和日志

### 日志配置
- 日志文件: `logs/1688sync.log`
- 日志级别: 可通过环境变量 `LOG_LEVEL` 配置
- 支持结构化日志输出

### 监控指标
- 爬取成功率
- 数据库连接状态
- 任务队列状态
- 系统资源使用情况

## 🚀 部署指南

### Docker部署（开发中）
```bash
# 构建Docker镜像
docker build -t 1688sync .

# 运行容器
docker run -d --name 1688sync \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  1688sync
```

### 传统部署
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DATABASE_URL=your_database_url

# 运行服务
python -m src.api.main  # API服务
python -m src.cli.main run  # 爬虫任务
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_database.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 📈 性能目标

- **爬取速度**: 单商品≤3秒
- **并发处理**: ≥16个并发请求
- **日处理量**: 10,000+商品
- **成功率**: ≥95%
- **系统稳定性**: 连续运行≥72小时

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 运行测试
5. 创建Pull Request

## 📄 许可证

MIT License

## 📞 联系方式

- 项目主页: https://github.com/bonzaphp/1688sync
- 问题反馈: https://github.com/bonzaphp/1688sync/issues

---

**注意**: 本项目仅用于学习和研究目的，请遵守1688平台的robots.txt和使用条款。