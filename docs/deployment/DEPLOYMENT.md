# 1688sync 部署运维文档

## 目录

- [快速开始](#快速开始)
- [系统要求](#系统要求)
- [环境配置](#环境配置)
- [部署方式](#部署方式)
- [服务管理](#服务管理)
- [监控和日志](#监控和日志)
- [备份和恢复](#备份和恢复)
- [故障排除](#故障排除)
- [性能优化](#性能优化)
- [安全配置](#安全配置)

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd epic-1688sync
```

### 2. 环境配置
```bash
# 复制环境配置文件
cp .env.example .env.dev

# 编辑配置文件，设置数据库密码等
vim .env.dev
```

### 3. 一键部署
```bash
# 开发环境部署
./scripts/deploy/deploy.sh dev --build --migrate

# 生产环境部署
./scripts/deploy/deploy.sh prod --backup --migrate
```

## 系统要求

### 硬件要求

#### 最小配置（开发/测试）
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 网络: 100Mbps

#### 推荐配置（生产）
- CPU: 4核心以上
- 内存: 8GB RAM 以上
- 存储: 100GB SSD
- 网络: 1Gbps

### 软件要求

- 操作系统: Linux (Ubuntu 20.04+, CentOS 8+) / macOS / Windows 10+
- Docker: 20.10+
- Docker Compose: 2.0+
- Git: 2.30+

## 环境配置

### 环境变量说明

| 变量名 | 说明 | 开发环境示例 | 生产环境要求 |
|--------|------|-------------|-------------|
| `MYSQL_ROOT_PASSWORD` | MySQL root密码 | `dev_password_1688sync` | 强密码，包含大小写、数字、特殊字符 |
| `SECRET_KEY` | JWT签名密钥 | `dev-secret-key` | 32位以上随机字符串 |
| `SENTRY_DSN` | Sentry错误监控URL | 空 | 生产环境必须配置 |
| `DEBUG` | 调试模式 | `true` | `false` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` | `WARNING` 或 `ERROR` |

### 配置文件结构
```
config/
├── mysql/
│   ├── my.cnf          # MySQL开发环境配置
│   └── my.cnf.prod     # MySQL生产环境配置
├── redis/
│   ├── redis.conf      # Redis开发环境配置
│   └── redis.conf.prod # Redis生产环境配置
└── nginx/
    ├── nginx.conf      # Nginx主配置
    └── conf.d/
        └── 1688sync.conf # 站点配置
```

## 部署方式

### 1. 开发环境部署

```bash
# 完整部署（包含构建、迁移）
./scripts/deploy/deploy.sh dev --build --migrate --seed

# 仅重启服务
./scripts/deploy/service.sh restart

# 查看服务状态
./scripts/deploy/service.sh status
```

### 2. 生产环境部署

```bash
# 生产环境部署（包含备份）
./scripts/deploy/deploy.sh prod --backup --migrate

# 滚动更新（零停机）
./scripts/deploy/deploy.sh prod --build

# 扩展服务实例
./scripts/deploy/service.sh scale app 3
```

### 3. 部署选项说明

| 选项 | 说明 |
|------|------|
| `--build` | 强制重新构建Docker镜像 |
| `--no-cache` | 构建时不使用缓存 |
| `--pull` | 部署前拉取最新代码 |
| `--backup` | 部署前备份数据 |
| `--migrate` | 部署后运行数据库迁移 |
| `--seed` | 初始化种子数据 |

## 服务管理

### 服务列表

| 服务名 | 说明 | 端口 | 依赖 |
|--------|------|------|------|
| `app` | 主应用服务 | 8000 | mysql, redis |
| `celery-worker` | 任务队列工作进程 | - | mysql, redis |
| `celery-beat` | 任务调度器 | - | mysql, redis |
| `celery-flower` | 任务监控面板 | 5555 | redis |
| `mysql` | MySQL数据库 | 3306 | - |
| `redis` | Redis缓存 | 6379 | - |
| `web-dashboard` | Web前端 | 3000 | app |
| `nginx` | 反向代理 | 80/443 | app, web-dashboard |

### 常用操作

```bash
# 查看所有服务状态
./scripts/deploy/service.sh status

# 查看特定服务日志
./scripts/deploy/service.sh logs app

# 实时跟踪日志
./scripts/deploy/service.sh logs app -f

# 重启特定服务
./scripts/deploy/service.sh restart celery-worker

# 进入容器执行命令
./scripts/deploy/service.sh exec mysql bash

# 扩展服务实例
./scripts/deploy/service.sh scale celery-worker 3

# 健康检查
./scripts/deploy/service.sh health
```

### 服务依赖关系

```
nginx
├── app
│   ├── mysql
│   └── redis
├── web-dashboard
│   └── app
└── celery-flower
    └── redis

celery-worker
├── mysql
└── redis

celery-beat
├── mysql
└── redis
```

## 监控和日志

### 日志管理

#### 日志位置
- 应用日志: `logs/1688sync.log`
- Nginx日志: `logs/nginx/`
- MySQL日志: Docker容器内 `/var/log/mysql/`
- Redis日志: Docker容器内 `/var/log/redis/`

#### 日志级别
- `DEBUG`: 详细调试信息（仅开发环境）
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

#### 日志轮转配置
```bash
# 日志轮转配置在 config/logrotate/1688sync
# 自动按日期和大小轮转，保留30天
```

### 监控指标

#### 应用监控
- HTTP响应时间
- 请求成功率
- 数据库连接数
- 任务队列长度

#### 系统监控
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络流量

#### 监控工具
- **Flower**: Celery任务监控 (http://localhost:5555)
- **Grafana**: 系统监控面板 (生产环境)
- **Prometheus**: 指标收集 (生产环境)

### 告警配置

#### 告警规则
- 服务不可用超过1分钟
- CPU使用率超过80%持续5分钟
- 内存使用率超过90%
- 磁盘空间不足10%
- 任务队列积压超过1000个

## 备份和恢复

### 自动备份

#### 备份策略
- **数据库**: 每天凌晨2点全量备份
- **Redis**: 每小时增量备份
- **文件**: 每天增量备份，每周全量备份
- **配置**: 版本控制管理

#### 备份保留策略
- 数据库备份: 保留30天
- Redis备份: 保留7天
- 文件备份: 保留90天
- 日志文件: 保留30天

### 手动备份

```bash
# 完整备份
./scripts/deploy/deploy.sh prod --backup

# 仅备份数据库
docker-compose exec mysql mysqldump -u root -p 1688sync > backup_$(date +%Y%m%d).sql

# 仅备份Redis
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### 数据恢复

```bash
# 恢复数据库
docker-compose exec -T mysql mysql -u root -p 1688sync < backup_20231201.sql

# 恢复Redis
docker cp redis_backup_20231201.rdb $(docker-compose ps -q redis):/data/dump.rdb
docker-compose restart redis
```

## 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 查看服务状态
docker-compose ps

# 查看详细日志
./scripts/deploy/service.sh logs <service-name>

# 检查端口占用
netstat -tlnp | grep <port>
```

#### 2. 数据库连接失败
```bash
# 检查数据库服务
./scripts/deploy/service.sh health

# 进入数据库容器
./scripts/deploy/service.sh exec mysql bash

# 测试数据库连接
docker-compose exec mysql mysql -u root -p -e "SHOW DATABASES;"
```

#### 3. 任务队列异常
```bash
# 检查Celery状态
docker-compose exec celery-worker celery -A src.task_queue.celery_app inspect active

# 重启工作进程
./scripts/deploy/service.sh restart celery-worker

# 查看任务队列
docker-compose exec celery-worker celery -A src.task_queue.celery_app inspect reserved
```

#### 4. 内存不足
```bash
# 查看内存使用
docker stats

# 清理未使用的镜像
docker system prune -a

# 重启服务释放内存
./scripts/deploy/service.sh restart
```

#### 5. 磁盘空间不足
```bash
# 查看磁盘使用
df -h

# 清理日志文件
sudo find logs/ -name "*.log" -mtime +30 -delete

# 清理Docker数据
docker system prune -a --volumes
```

### 性能问题诊断

#### 1. 响应时间过长
```bash
# 查看应用日志
./scripts/deploy/service.sh logs app -f

# 检查数据库慢查询
docker-compose exec mysql mysql -u root -p -e "SHOW PROCESSLIST;"

# 查看系统资源
docker stats
```

#### 2. 数据库性能
```bash
# 查看数据库状态
docker-compose exec mysql mysql -u root -p -e "SHOW STATUS;"

# 优化表结构
docker-compose exec mysql mysql -u root -p -e "OPTIMIZE TABLE table_name;"

# 分析查询性能
docker-compose exec mysql mysql -u root -p -e "EXPLAIN SELECT * FROM table_name;"
```

## 性能优化

### 数据库优化

#### MySQL配置优化
```ini
# 生产环境配置
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 1
max_connections = 500
query_cache_type = 0
```

#### 索引优化
```sql
-- 创建复合索引
CREATE INDEX idx_product_category ON products(category_id, created_at);

-- 分析表结构
ANALYZE TABLE products;

-- 检查索引使用情况
SHOW INDEX FROM products;
```

### 应用优化

#### 连接池配置
```python
# 数据库连接池
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 20,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

# Redis连接池
REDIS_CONNECTION_POOL = {
    "max_connections": 50,
    "retry_on_timeout": True
}
```

#### 缓存策略
```python
# Redis缓存配置
CACHE_TTL = {
    "product_info": 3600,      # 1小时
    "category_list": 86400,    # 24小时
    "user_session": 1800       # 30分钟
}
```

### 系统优化

#### 文件描述符限制
```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
```

#### 网络优化
```bash
# TCP优化
echo 'net.core.somaxconn = 65536' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65536' >> /etc/sysctl.conf
sysctl -p
```

## 安全配置

### 网络安全

#### 防火墙配置
```bash
# 仅开放必要端口
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

#### SSL/TLS配置
```nginx
# Nginx SSL配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
```

### 应用安全

#### 密码策略
- 最小长度12位
- 包含大小写字母、数字、特殊字符
- 定期更换（每90天）

#### 访问控制
```nginx
# IP白名单
allow 192.168.1.0/24;
deny all;

# 基础认证
auth_basic "Restricted Area";
auth_basic_user_file /etc/nginx/.htpasswd;
```

#### 数据加密
- 数据库连接加密
- 敏感字段加密存储
- API接口HTTPS

### 安全监控

#### 日志审计
```bash
# 监控失败登录
tail -f /var/log/auth.log | grep "Failed password"

# 监控异常访问
tail -f /var/log/nginx/access.log | grep "HTTP/1.1\" 4[0-9][0-9]"
```

#### 入侵检测
- 文件完整性监控
- 异常登录检测
- 恶意请求识别

## 应急响应

### 服务中断处理

#### 1. 快速诊断（5分钟内）
```bash
# 检查服务状态
./scripts/deploy/service.sh status

# 检查系统资源
docker stats
df -h

# 查看错误日志
./scripts/deploy/service.sh logs app -f
```

#### 2. 紧急恢复（15分钟内）
```bash
# 重启服务
./scripts/deploy/service.sh restart

# 回滚到上一版本
git checkout HEAD~1
./scripts/deploy/deploy.sh prod --build

# 恢复备份
./scripts/backup/restore.sh latest
```

#### 3. 根因分析（1小时内）
- 收集日志文件
- 分析错误原因
- 制定修复方案
- 更新监控告警

### 数据损坏处理

#### 1. 立即停止写入
```bash
# 停止应用服务
./scripts/deploy/service.sh stop app

# 停止任务队列
./scripts/deploy/service.sh stop celery-worker
```

#### 2. 评估损坏程度
```bash
# 检查数据库完整性
docker-compose exec mysql mysqlcheck -u root -p --check 1688sync

# 检查备份数据
ls -la backups/
```

#### 3. 执行恢复
```bash
# 从最近备份恢复
./scripts/backup/restore.sh $(ls -t backups/ | head -1)

# 验证恢复结果
./scripts/deploy/service.sh health
```

## 联系方式

- 技术支持: support@1688sync.com
- 紧急联系: +86-xxx-xxxx-xxxx
- 文档更新: https://docs.1688sync.com

---

*最后更新: 2024年12月*