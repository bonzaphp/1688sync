# 1688sync 爬虫系统使用指南

## 概述

1688sync 是一个基于 Scrapy 框架的 1688.com 商品爬虫系统，具有以下特点：

- **智能反爬虫**: 随机 User-Agent、代理支持、请求限速
- **数据清洗**: 自动清理和标准化商品数据
- **图片下载**: 自动下载商品图片并本地存储
- **去重过滤**: 避免重复爬取同一商品
- **数据库存储**: 完整的商品数据持久化
- **统计分析**: 详细的爬取统计信息

## 系统架构

```
src/scrapy_project/
├── spiders/
│   ├── __init__.py
│   └── 1688_spider.py          # 主爬虫
├── items.py                    # 数据项定义
├── settings.py                 # Scrapy配置
├── pipelines.py                # 数据处理管道
├── middlewares.py              # 中间件
└── crawler.py                  # 爬虫运行器
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/1688sync

# Redis配置（可选）
REDIS_URL=redis://localhost:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/1688sync.log

# Scrapy配置
SCRAPY_CONCURRENT_REQUESTS=16
SCRAPY_DOWNLOAD_DELAY=1.0
SCRAPY_USER_AGENT=1688sync-bot/1.0
```

### 3. 运行爬虫

#### 方式一：使用爬虫运行器（推荐）

```bash
# 搜索关键词爬取
python src/scrapy_project/crawler.py --keyword "手机" --max-requests 100

# 分类爬取
python src/scrapy_project/crawler.py --category "电子产品" --max-requests 100

# 首页爬取
python src/scrapy_project/crawler.py --max-requests 50
```

#### 方式二：使用 Scrapy 命令

```bash
# 搜索爬取
scrapy crawl 1688_products -a keyword="手机" -a max_requests=100

# 分类爬取
scrapy crawl 1688_products -a category="电子产品" -a max_requests=100

# 首页爬取
scrapy crawl 1688_products -a max_requests=50
```

## 功能特性

### 1. 爬虫模式

- **搜索模式**: 根据关键词搜索商品
- **分类模式**: 爬取指定分类的商品
- **首页模式**: 爬取首页推荐商品

### 2. 数据提取

商品信息包括：
- 基本信息：标题、价格、原价、描述
- 卖家信息：卖家名称、ID、地理位置
- 媒体内容：图片URL（自动下载）
- 规格参数：商品详细规格
- 标签分类：商品标签

### 3. 反爬虫策略

- **随机User-Agent**: 多种浏览器标识轮换
- **请求限速**: 智能延迟避免被封
- **代理支持**: 可配置代理池
- **Cookie管理**: 自动处理Cookie
- **反检测**: 模拟真实用户行为

### 4. 数据处理管道

1. **数据清理**: 清理文本、去重、标准化
2. **数据验证**: 验证必要字段完整性
3. **重复过滤**: 避免重复数据
4. **数据库存储**: 持久化到MySQL
5. **图片下载**: 自动下载并存储图片
6. **统计报告**: 生成详细统计信息

## 配置说明

### Scrapy 核心配置

```python
# 并发控制
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True

# 用户代理列表
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    # 更多User-Agent
]

# 中间件配置
DOWNLOADER_MIDDLEWARES = {
    'src.scrapy_project.middlewares.UserAgentMiddleware': 540,
    'src.scrapy_project.middlewares.ProxyMiddleware': 541,
    'src.scrapy_project.middlewares.AntiDetectionMiddleware': 544,
    # ...
}
```

### 管道配置

```python
ITEM_PIPELINES = {
    'src.scrapy_project.pipelines.DataCleaningPipeline': 200,
    'src.scrapy_project.pipelines.DataValidationPipeline': 300,
    'src.scrapy_project.pipelines.DuplicateFilterPipeline': 350,
    'src.scrapy_project.pipelines.DatabasePipeline': 400,
    'src.scrapy_project.pipelines.ImageDownloadPipeline': 500,
    'src.scrapy_project.pipelines.StatsPipeline': 900,
}
```

## 数据库结构

### 商品表 (products)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| product_id | varchar(100) | 商品ID |
| title | varchar(500) | 商品标题 |
| price | float | 当前价格 |
| original_price | float | 原价 |
| description | text | 商品描述 |
| category | varchar(200) | 分类 |
| brand | varchar(200) | 品牌 |
| seller | varchar(200) | 卖家名称 |
| location | varchar(200) | 地理位置 |
| image_urls | json | 图片URL列表 |
| specifications | json | 规格参数 |
| tags | json | 标签列表 |
| source_url | varchar(1000) | 原始URL |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

## 使用示例

### 1. 基础爬取

```python
from src.scrapy_project.crawler import CrawlerRunner

runner = CrawlerRunner()
runner.run_search_spider(keyword="手机", max_requests=100)
```

### 2. 自定义爬虫

```python
from scrapy.crawler import CrawlerProcess
from src.scrapy_project.spiders._1688_spider import Product1688Spider

process = CrawlerProcess()
process.crawl(Product1688Spider, keyword="笔记本电脑", max_requests=200)
process.start()
```

### 3. 数据查询

```python
from src.database.connection import SessionLocal
from src.database.models import Product

db = SessionLocal()
products = db.query(Product).filter(
    Product.category == "电子产品"
).limit(10).all()

for product in products:
    print(f"{product.title} - ¥{product.price}")
```

## 监控和日志

### 日志配置

- 日志级别：DEBUG, INFO, WARNING, ERROR
- 日志文件：`logs/1688sync.log`
- 日志格式：包含时间戳、级别、消息

### 统计信息

爬虫完成后会输出详细统计：
- 运行时间
- 总商品数
- 成功/失败数量
- 图片下载统计
- 成功率

## 常见问题

### 1. 爬虫被限制

**问题**: 请求频繁被封IP
**解决方案**:
- 降低并发数量
- 增加下载延迟
- 使用代理池
- 设置更真实的User-Agent

### 2. 数据提取失败

**问题**: 商品信息提取不完整
**解决方案**:
- 检查网站页面结构是否变化
- 更新CSS选择器
- 查看日志中的错误信息

### 3. 数据库连接失败

**问题**: 无法连接到数据库
**解决方案**:
- 检查数据库服务是否启动
- 验证连接字符串配置
- 确认网络连接正常

### 4. 图片下载失败

**问题**: 图片下载不成功
**解决方案**:
- 检查图片URL是否有效
- 确认存储目录权限
- 查看网络连接状态

## 性能优化

### 1. 并发优化

```python
# 提高并发数量
CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 16
```

### 2. 内存优化

```python
# 启用压缩
COMPRESSION_ENABLED = True

# 限制队列大小
REACTOR_THREADPOOL_MAXSIZE = 20
```

### 3. 存储优化

```python
# 批量插入数据库
DATABASE_PIPELINE_BATCH_SIZE = 100

# 图片缓存
IMAGES_EXPIRES = 30  # 天
```

## 安全注意事项

1. **遵守robots.txt**: 系统默认遵守网站的robots.txt规则
2. **合理频率**: 不要设置过高的请求频率
3. **数据使用**: 仅用于合法用途，遵守相关法律法规
4. **隐私保护**: 不要爬取和存储用户隐私信息

## 扩展开发

### 添加新的数据源

1. 创建新的Spider类
2. 定义专用的Item
3. 实现特定的Pipeline
4. 更新配置文件

### 自定义中间件

```python
class CustomMiddleware:
    def process_request(self, request, spider):
        # 自定义处理逻辑
        return None
```

## 技术支持

如果遇到问题，请：
1. 查看日志文件获取详细错误信息
2. 运行测试脚本检查系统完整性
3. 检查配置文件是否正确
4. 确认依赖包是否完整安装

---

**注意**: 使用本爬虫系统时请遵守目标网站的使用条款和相关法律法规。