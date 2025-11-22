# 1688sync CLI Makefile
# 构建和安装脚本

.PHONY: help install install-dev test lint format clean build upload docs run

# 默认目标
help:
	@echo "1688sync CLI 可用命令:"
	@echo "  install      - 安装包"
	@echo "  install-dev  - 安装开发依赖"
	@echo "  test         - 运行测试"
	@echo "  lint         - 代码检查"
	@echo "  format       - 代码格式化"
	@echo "  clean        - 清理构建文件"
	@echo "  build        - 构建包"
	@echo "  upload       - 上传到PyPI"
	@echo "  docs         - 生成文档"
	@echo "  run          - 运行CLI工具"
	@echo ""
	@echo "示例用法:"
	@echo "  make install"
	@echo "  make run ARGS='--help'"

# 安装包
install:
	pip install -e .

# 安装开发依赖
install-dev:
	pip install -e ".[dev,docs]"
	pre-commit install

# 运行测试
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# 代码检查
lint:
	flake8 src/ tests/ cli.py
	mypy src/ --ignore-missing-imports
	black --check src/ tests/ cli.py
	isort --check-only src/ tests/ cli.py

# 代码格式化
format:
	black src/ tests/ cli.py
	isort src/ tests/ cli.py

# 清理构建文件
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# 构建包
build: clean
	python setup.py sdist bdist_wheel

# 上传到PyPI
upload: build
	twine upload dist/*

# 上传到测试PyPI
upload-test: build
	twine upload --repository testpypi dist/*

# 生成文档
docs:
	cd docs && make html

# 运行CLI工具
run:
	python cli.py $(ARGS)

# 快速测试CLI
test-cli:
	python cli.py --help
	python cli.py version
	python cli.py sync --help

# 创建虚拟环境
venv:
	python -m venv venv
	@echo "虚拟环境已创建。激活方法:"
	@echo "  source venv/bin/activate  # Linux/Mac"
	@echo "  venv\\Scripts\\activate     # Windows"

# 初始化项目
init: venv install-dev
	@echo "项目初始化完成！"
	@echo "现在可以运行: source venv/bin/activate && make test-cli"

# 检查依赖
check-deps:
	pip check
	safety check

# 更新依赖
update-deps:
	pip-review --local --interactive

# 生成依赖文件
freeze:
	pip freeze > requirements-freeze.txt

# 数据库迁移
migrate:
	alembic upgrade head

# 创建新的数据库迁移
migration:
	alembic revision --autogenerate -m "$(MSG)"

# 启动Redis (用于开发)
redis:
	redis-server

# 启动Celery Worker
worker:
	celery -A src.queue.celery_app worker --loglevel=info

# 启动Celery Beat
beat:
	celery -A src.queue.celery_app beat --loglevel=info

# 监控Celery
monitor:
	celery -A src.queue.celery_app flower

# 完整的开发环境启动
dev-setup: install-dev
	@echo "开发环境设置完成！"
	@echo ""
	@echo "下一步:"
	@echo "1. 配置环境变量 (复制 .env.example 到 .env)"
	@echo "2. 运行 'make migrate' 初始化数据库"
	@echo "3. 运行 'make test-cli' 测试CLI工具"
	@echo "4. 运行 'make worker' 启动后台任务处理器"

# 备份数据库
backup:
	@echo "备份数据库到 backups/ 目录"
	mkdir -p backups
	pg_dump $${DATABASE_URL} > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql

# 恢复数据库
restore:
	@echo "从备份恢复数据库"
	@echo "用法: make restore BACKUP_FILE=path/to/backup.sql"
	@if [ -z "$(BACKUP_FILE)" ]; then echo "错误: 请指定 BACKUP_FILE"; exit 1; fi
	psql $${DATABASE_URL} < $(BACKUP_FILE)