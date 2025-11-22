# 1688sync 部署指南

## 🚀 快速开始

### 一键部署（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd epic-1688sync

# 开发环境部署
./scripts/deploy/deploy.sh dev --build --migrate --seed

# 生产环境部署
./scripts/deploy/deploy.sh prod --backup --migrate
```

## 📋 目录结构

```
epic-1688sync/
├── scripts/deploy/          # 部署脚本
│   ├── deploy.sh           # 主部署脚本
│   ├── service.sh          # 服务管理脚本
│   └── stop.sh             # 停止清理脚本
├── scripts/backup/          # 备份脚本
│   ├── backup.sh           # 备份脚本
│   ├── restore.sh          # 恢复脚本
│   ├── cron-backup.sh      # 定时备份
│   └── crontab.example     # 定时任务示例
├── config/                  # 配置文件
│   ├── mysql/              # MySQL配置
│   ├── redis/              # Redis配置
│   ├── nginx/              # Nginx配置
│   └── logrotate/          # 日志轮转配置
├── monitoring/              # 监控配置
│   ├── prometheus.yml      # Prometheus配置
│   ├── alert_rules.yml     # 告警规则
│   └── grafana/            # Grafana配置
├── docs/deployment/         # 部署文档
│   ├── DEPLOYMENT.md       # 完整部署文档
│   ├── QUICK_START.md      # 快速开始指南
│   └── CHECKLIST.md        # 部署检查清单
├── Dockerfile              # Docker镜像配置
├── Dockerfile.prod         # 生产环境镜像
├── docker-compose.yml      # 开发环境编排
├── docker-compose.prod.yml # 生产环境编排
├── .env.dev                # 开发环境变量
└── .env.prod               # 生产环境变量
```

## 🛠️ 部署脚本使用

### 主部署脚本 (deploy.sh)

```bash
# 基本用法
./scripts/deploy/deploy.sh <环境> [选项]

# 示例
./scripts/deploy/deploy.sh dev --build --migrate
./scripts/deploy/deploy.sh prod --backup --pull

# 选项说明
--build      强制重新构建镜像
--no-cache   构建时不使用缓存
--pull       部署前拉取最新代码
--backup     部署前备份数据
--migrate    部署后运行数据库迁移
--seed       初始化种子数据
```

### 服务管理脚本 (service.sh)

```bash
# 查看服务状态
./scripts/deploy/service.sh status

# 查看日志
./scripts/deploy/service.sh logs app
./scripts/deploy/service.sh logs app -f  # 实时跟踪

# 重启服务
./scripts/deploy/service.sh restart
./scripts/deploy/service.sh restart celery-worker

# 扩展服务
./scripts/deploy/service.sh scale app 3

# 健康检查
./scripts/deploy/service.sh health

# 进入容器
./scripts/deploy/service.sh exec mysql bash
```

### 停止清理脚本 (stop.sh)

```bash
# 停止所有服务
./scripts/deploy/stop.sh

# 停止并备份数据
./scripts/deploy/stop.sh --backup

# 完全清理（包括数据）
./scripts/deploy/stop.sh --remove-volumes --remove-images
```

## 💾 备份和恢复

### 备份数据

```bash
# 完整备份
./scripts/backup/backup.sh all --compress --clean

# 分类备份
./scripts/backup/backup.sh database
./scripts/backup/backup.sh redis
./scripts/backup/backup.sh files
```

### 恢复数据

```bash
# 恢复完整备份
./scripts/backup/restore.sh backups/20231201_120000

# 恢复特定数据
./scripts/backup/restore.sh backups/20231201_120000 --database
./scripts/backup/restore.sh backups/20231201_120000 --redis

# 预演模式（不实际执行）
./scripts/backup/restore.sh backups/20231201_120000 --dry-run
```

### 定时备份

```bash
# 设置定时任务
crontab scripts/backup/crontab.example

# 手动执行定时备份
./scripts/backup/cron-backup.sh all
```

## 📊 监控和日志

### 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| API服务 | http://localhost:8000 | 主API接口 |
| Web界面 | http://localhost:3000 | Web管理界面 |
| 任务监控 | http://localhost:5555 | Celery监控面板 |
| Grafana | http://localhost:3001 | 系统监控面板 |
| Prometheus | http://localhost:9090 | 指标收集 |

### 日志查看

```bash
# 应用日志
./scripts/deploy/service.sh logs app

# 数据库日志
./scripts/deploy/service.sh logs mysql

# 所有服务日志
docker-compose logs

# 实时跟踪
docker-compose logs -f
```

### 监控指标

- **应用指标**: 响应时间、错误率、吞吐量
- **系统指标**: CPU、内存、磁盘、网络
- **数据库指标**: 连接数、查询性能、慢查询
- **缓存指标**: 命中率、内存使用、连接数

## 🔧 环境配置

### 开发环境 (.env.dev)

```bash
# 基础配置
DEBUG=true
LOG_LEVEL=DEBUG
MYSQL_ROOT_PASSWORD=dev_password_1688sync

# 服务地址
API_HOST=0.0.0.0
API_PORT=8000
```

### 生产环境 (.env.prod)

```bash
# 基础配置
DEBUG=false
LOG_LEVEL=WARNING
MYSQL_ROOT_PASSWORD=CHANGE_THIS_STRONG_PASSWORD

# 安全配置
SECRET_KEY=CHANGE_THIS_SUPER_SECRET_KEY
SENTRY_DSN=https://your-sentry-dsn
```

## 🚨 故障排除

### 常见问题

1. **服务无法启动**
   ```bash
   # 检查服务状态
   docker-compose ps

   # 查看错误日志
   ./scripts/deploy/service.sh logs
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库服务
   ./scripts/deploy/service.sh health

   # 测试连接
   ./scripts/deploy/service.sh exec mysql mysql -u root -p
   ```

3. **内存不足**
   ```bash
   # 查看资源使用
   docker stats

   # 清理系统
   docker system prune -a
   ```

4. **磁盘空间不足**
   ```bash
   # 检查磁盘使用
   df -h

   # 清理日志
   find logs/ -name "*.log" -mtime +30 -delete
   ```

### 性能优化

- **数据库**: 优化MySQL配置，添加索引
- **缓存**: 调整Redis内存配置
- **应用**: 调整连接池大小
- **系统**: 优化内核参数

## 📚 文档导航

- [完整部署文档](docs/deployment/DEPLOYMENT.md) - 详细的部署和运维指南
- [快速开始指南](docs/deployment/QUICK_START.md) - 10分钟快速部署
- [部署检查清单](docs/deployment/CHECKLIST.md) - 部署前后检查项目

## 🆘 技术支持

### 获取帮助

```bash
# 查看脚本帮助
./scripts/deploy/deploy.sh --help
./scripts/deploy/service.sh --help
./scripts/backup/backup.sh --help
```

### 联系方式

- 技术支持: support@1688sync.com
- 紧急联系: +86-xxx-xxxx-xxxx
- 文档网站: https://docs.1688sync.com

---

**部署完成后，请运行检查清单确保系统正常运行！**