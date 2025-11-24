# 1688sync - Quick Start Guide

## 🚀 5分钟快速启动

### 前置要求
- Python 3.10+
- Redis (可选，用于任务队列)
- MySQL/SQLite (可选，可使用默认SQLite)

---

## ⚡ 快速启动

### 1. 克隆并安装
```bash
# 克隆项目
git clone https://github.com/bonzaphp/1688sync.git
cd 1688sync

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### 2. 环境配置
```bash
# 复制配置文件
cp .env.example .env

# 使用默认配置即可开始
# 数据库默认使用SQLite，无需额外配置
```

### 3. 初始化项目
```bash
# 创建数据目录
mkdir -p data logs images

# 安装SQLite依赖（如果需要）
pip install "aiosqlite>=0.19.0"

# 初始化数据库（Python）
python -c "
from src.database.connection import create_tables_sync
create_tables_sync()
print('数据库初始化完成！')
"
```

### 4. 启动服务
```bash
# 方式一：使用CLI爬虫
python cli.py crawl products --max-products 10

# 方式二：启动Web API
python run_api.py
# 访问: http://localhost:8000/docs

# 方式三：启动Web界面
cd web-dashboard && npm install && npm start
# 访问: http://localhost:3000
```

---

## 🎯 核心功能演示

### CLI快速命令
```bash
# 查看系统状态
python cli.py status

# 爬取10个商品
python cli.py crawl products --max-products 10

# 同步数据
python cli.py sync products --batch-size 50

# 查看队列状态
python cli.py queue status
```

### API快速测试
```bash
# 启动API服务
python run_api.py

# 测试API（新开终端）
curl http://localhost:8000/api/v1/products/
curl http://localhost:8000/api/v1/tasks/status
```

### Web界面操作
1. 启动前端: `cd web-dashboard && npm start`
2. 访问: http://localhost:3000
3. 查看仪表板、商品管理、任务监控

---

## 📊 验证安装

### 运行测试套件
```bash
# 基础功能测试
python test_simple.py

# 数据处理测试
python tests/test_data_processing.py

# API服务测试
python test_api.py

# 性能测试
python test_performance.py
```

### 预期结果
```
✅ 数据库连接成功
✅ 爬虫系统正常
✅ API服务响应正常
✅ 任务队列运行正常
```

---

## 🛠️ 常用配置

### 修改配置文件 (.env)
```bash
# 数据库配置
DATABASE_URL=sqlite:///data/1688sync.db    # 默认SQLite
# DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/1688sync  # MySQL

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# API服务
API_HOST=0.0.0.0
API_PORT=8000
```

### 爬虫配置
```bash
# 并发控制
SCRAPY_CONCURRENT_REQUESTS=16
SCRAPY_DOWNLOAD_DELAY=1

# 数据存储
DATA_DIR=./data
IMAGE_DIR=./data/images
```

---

## 🐳 Docker快速启动

```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose ps
```

---

## 📱 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| CLI工具 | 命令行 | 直接运行 `python cli.py` |
| API服务 | http://localhost:8000 | RESTful API接口 |
| API文档 | http://localhost:8000/docs | Swagger文档 |
| Web界面 | http://localhost:3000 | React管理控制台 |
| 任务监控 | http://localhost:5555 | Celery Flower (需启动) |

---

## 🔧 故障排除

### 常见问题

#### 1. Python依赖问题
```bash
# 升级pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

#### 2. 数据库连接失败
```bash
# 检查数据库文件权限
ls -la data/

# 重新初始化数据库
python cli.py reset
python cli.py init
```

#### 3. 端口占用
```bash
# 修改端口（编辑.env文件）
API_PORT=8001

# 或停止占用进程
lsof -ti:8000 | xargs kill -9
```

#### 4. Redis连接失败
```bash
# 启动Redis服务
redis-server

# 或使用docker启动Redis
docker run -d -p 6379:6379 redis:alpine
```

### 重置系统
```bash
# 删除数据库文件
rm -f data/1688sync.db

# 重新初始化数据库
python -c "
from src.database.connection import create_tables_sync
create_tables_sync()
print('数据库重新初始化完成！')
"
```

---

## 📈 下一步

### 学习资源
- [完整文档](README.md)
- [API文档](docs/API.md)
- [部署指南](docs/deployment/DEPLOYMENT.md)

### 生产环境部署
```bash
# 使用Docker部署（推荐）
docker-compose -f docker-compose.prod.yml up -d

# 或手动部署
bash scripts/deploy/deploy.sh prod
```

### 高级功能
- 配置Redis任务队列
- 设置定时任务
- 启用监控系统
- 配置反向代理

---

## 🎉 成功标志

当你看到以下输出时，说明启动成功：

```
✅ 1688sync项目初始化完成！
✅ 数据库连接正常
✅ 爬虫系统就绪
✅ API服务启动成功
✅ 任务队列运行正常
```

现在你可以开始使用1688sync进行商品数据同步了！

---

## 💡 提示

- **首次使用建议**: 先用小批量数据测试 (`--max-products 10`)
- **生产环境**: 建议使用MySQL + Redis + Docker部署
- **性能优化**: 根据服务器配置调整并发参数
- **监控**: 启用监控系统以跟踪运行状态

**遇到问题？** 查看 [完整文档](README.md) 或提交Issue。