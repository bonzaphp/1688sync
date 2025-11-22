# 1688sync API 服务

基于FastAPI构建的1688商品数据同步服务RESTful API。

## 功能特性

- 🚀 **高性能异步框架**: 基于FastAPI和Uvicorn
- 📊 **自动API文档**: 支持OpenAPI和ReDoc
- 🔐 **认证和授权**: JWT令牌认证
- 🛡️ **安全中间件**: CORS、安全头、频率限制
- 📝 **完整日志记录**: 结构化日志和错误追踪
- 🗄️ **数据库集成**: SQLAlchemy ORM
- ⚡ **后台任务**: 支持异步任务处理
- 📈 **监控和统计**: 性能指标和健康检查

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements-api.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和其他设置
```

### 3. 初始化数据库

```bash
python -c "from src.database.connection import create_tables; create_tables()"
```

### 4. 启动服务

```bash
python run_api.py
```

服务将在 `http://localhost:8000` 启动。

### 5. 查看API文档

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API 端点

### 商品管理
- `GET /api/v1/products/` - 获取商品列表
- `GET /api/v1/products/{id}` - 获取商品详情
- `POST /api/v1/products/` - 创建商品
- `PUT /api/v1/products/{id}` - 更新商品
- `DELETE /api/v1/products/{id}` - 删除商品
- `POST /api/v1/products/{id}/sync` - 同步商品
- `POST /api/v1/products/batch-sync` - 批量同步商品

### 任务管理
- `GET /api/v1/tasks/` - 获取任务列表
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `POST /api/v1/tasks/` - 创建任务
- `PUT /api/v1/tasks/{id}/status` - 更新任务状态
- `POST /api/v1/tasks/{id}/cancel` - 取消任务
- `DELETE /api/v1/tasks/{id}` - 删除任务
- `GET /api/v1/tasks/{id}/logs` - 获取任务日志

### 日志管理
- `GET /api/v1/logs/` - 获取日志列表
- `GET /api/v1/logs/{id}` - 获取日志详情
- `GET /api/v1/logs/stats/summary` - 获取日志统计
- `GET /api/v1/logs/errors/recent` - 获取最近错误
- `DELETE /api/v1/logs/cleanup` - 清理旧日志

### 系统管理
- `GET /` - 根路径信息
- `GET /health` - 健康检查

## 认证

API使用JWT令牌认证。在请求头中包含：

```
Authorization: Bearer <your-jwt-token>
```

## 错误处理

API返回统一的错误格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 开发

### 代码格式化

```bash
black src/api/
isort src/api/
```

### 运行测试

```bash
pytest tests/
```

### 环境变量

主要环境变量：

- `DATABASE_URL` - 数据库连接字符串
- `REDIS_URL` - Redis连接字符串
- `SECRET_KEY` - JWT密钥
- `API_HOST` - API服务主机
- `API_PORT` - API服务端口
- `DEBUG` - 调试模式

## 部署

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY . .
EXPOSE 8000

CMD ["python", "run_api.py"]
```

### 生产环境配置

1. 设置环境变量 `DEBUG=false`
2. 配置真实的数据库连接
3. 设置强密码的 `SECRET_KEY`
4. 配置HTTPS和反向代理
5. 设置日志轮转和监控

## 许可证

MIT License