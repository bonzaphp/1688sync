# 1688sync 快速部署指南

本指南帮助您在10分钟内完成1688sync的部署。

## 前置要求

- 已安装 Docker 和 Docker Compose
- 4GB 以上可用内存
- 20GB 以上可用磁盘空间

## 一键部署

### 开发环境

```bash
# 1. 克隆项目
git clone <repository-url>
cd epic-1688sync

# 2. 环境配置
cp .env.example .env.dev
# 编辑 .env.dev，设置 MYSQL_ROOT_PASSWORD

# 3. 一键部署
./scripts/deploy/deploy.sh dev --build --migrate --seed

# 4. 验证部署
curl http://localhost:8000/health
```

### 生产环境

```bash
# 1. 克隆项目
git clone <repository-url>
cd epic-1688sync

# 2. 环境配置
cp .env.prod.example .env.prod
# 编辑 .env.prod，设置强密码和 Sentry DSN

# 3. 生产部署
./scripts/deploy/deploy.sh prod --backup --migrate

# 4. 配置域名和SSL（可选）
# 编辑 config/nginx/conf.d/1688sync.conf
# 配置证书文件到 ssl/ 目录
```

## 访问地址

部署完成后，可通过以下地址访问服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| API服务 | http://localhost:8000 | 主API接口 |
| Web界面 | http://localhost:3000 | Web管理界面 |
| 任务监控 | http://localhost:5555 | Celery监控面板 |
| 数据库 | localhost:3306 | MySQL数据库 |
| 缓存 | localhost:6379 | Redis缓存 |

生产环境额外服务：
| 服务 | 地址 | 说明 |
|------|------|------|
| 监控面板 | http://localhost:3001 | Grafana监控 |
| 指标收集 | http://localhost:9090 | Prometheus |

## 常用命令

```bash
# 查看服务状态
./scripts/deploy/service.sh status

# 查看日志
./scripts/deploy/service.sh logs app

# 重启服务
./scripts/deploy/service.sh restart

# 停止所有服务
./scripts/deploy/stop.sh

# 扩展服务
./scripts/deploy/service.sh scale celery-worker 3
```

## 故障排除

### 服务启动失败
```bash
# 检查容器状态
docker-compose ps

# 查看错误日志
./scripts/deploy/service.sh logs
```

### 端口占用
```bash
# 查看端口占用
netstat -tlnp | grep :8000

# 停止冲突服务
sudo systemctl stop nginx  # 如果系统中已有nginx
```

### 权限问题
```bash
# 设置脚本执行权限
chmod +x scripts/deploy/*.sh

# 创建必要目录
mkdir -p data logs backups checkpoints
```

## 下一步

- 阅读 [完整部署文档](DEPLOYMENT.md)
- 配置监控和告警
- 设置定期备份
- 优化性能参数

## 技术支持

如遇到问题，请：
1. 查看日志文件
2. 检查系统资源
3. 联系技术支持

---

*部署时间约5-10分钟，视网络状况而定*