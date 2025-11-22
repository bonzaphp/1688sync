# 1688sync Docker配置
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt requirements-api.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-api.txt

# 复制应用程序代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data/images \
    /app/logs \
    /app/checkpoints \
    /app/backups \
    && chmod 755 /app/data /app/logs /app/checkpoints /app/backups

# 设置权限
RUN chmod +x /app/cli.py \
    && chmod +x /app/run_api.py \
    && chmod +x /app/cli.py

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 默认启动命令
CMD ["python", "run_api.py"]