#!/bin/bash

# 1688sync部署脚本
# 用法: ./deploy.sh [环境] [选项]
# 环境: dev, staging, prod

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
1688sync部署脚本

用法: $0 [环境] [选项]

环境:
    dev         开发环境部署
    staging     测试环境部署
    prod        生产环境部署

选项:
    --build     强制重新构建镜像
    --no-cache  构建时不使用缓存
    --pull      部署前拉取最新代码
    --backup    部署前备份数据
    --migrate   部署后运行数据库迁移
    --seed      初始化种子数据
    --help      显示此帮助信息

示例:
    $0 dev --build --migrate
    $0 prod --backup --pull
    $0 staging --no-cache

EOF
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行，请启动Docker服务"
        exit 1
    fi

    log_success "系统依赖检查通过"
}

# 设置环境变量
setup_environment() {
    local env=$1
    log_info "设置${env}环境..."

    # 检查环境文件
    if [[ ! -f ".env.${env}" ]]; then
        log_warning ".env.${env}不存在，使用.env.example创建"
        if [[ ! -f ".env.example" ]]; then
            log_error ".env.example不存在"
            exit 1
        fi
        cp .env.example ".env.${env}"
        log_warning "请编辑.env.${env}文件并设置正确的配置"
        exit 1
    fi

    # 复制环境文件
    cp ".env.${env}" .env

    # 设置环境变量
    export COMPOSE_FILE="docker-compose.yml"
    if [[ "$env" == "prod" ]]; then
        export COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"
    fi

    log_success "环境设置完成"
}

# 拉取最新代码
pull_code() {
    log_info "拉取最新代码..."

    if ! git pull origin main; then
        log_error "代码拉取失败"
        exit 1
    fi

    log_success "代码拉取完成"
}

# 备份数据
backup_data() {
    log_info "备份数据..."

    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # 备份数据库
    if docker-compose ps mysql | grep -q "Up"; then
        log_info "备份MySQL数据库..."
        docker-compose exec mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" 1688sync > "$backup_dir/database.sql"
    fi

    # 备份Redis
    if docker-compose ps redis | grep -q "Up"; then
        log_info "备份Redis数据..."
        docker-compose exec redis redis-cli BGSAVE
        sleep 2
        docker cp "$(docker-compose ps -q redis):/data/dump.rdb" "$backup_dir/"
    fi

    # 备份应用数据
    if [[ -d "data" ]]; then
        log_info "备份应用数据..."
        cp -r data "$backup_dir/"
    fi

    log_success "数据备份完成: $backup_dir"
}

# 构建镜像
build_images() {
    local build_args=""

    if [[ "$NO_CACHE" == "true" ]]; then
        build_args="$build_args --no-cache"
    fi

    if [[ "$FORCE_BUILD" != "true" ]]; then
        build_args="$build_args --pull"
    fi

    log_info "构建Docker镜像..."
    log_info "构建参数: $build_args"

    if ! docker-compose build $build_args; then
        log_error "镜像构建失败"
        exit 1
    fi

    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 停止现有服务
    docker-compose down

    # 启动基础服务 (数据库、Redis)
    log_info "启动基础服务..."
    docker-compose up -d mysql redis

    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 30

    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose up -d

    log_success "服务启动完成"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."

    # 等待数据库完全就绪
    sleep 10

    if docker-compose exec app python -m alembic upgrade head; then
        log_success "数据库迁移完成"
    else
        log_error "数据库迁移失败"
        exit 1
    fi
}

# 初始化种子数据
seed_data() {
    log_info "初始化种子数据..."

    if docker-compose exec app python cli.py seed; then
        log_success "种子数据初始化完成"
    else
        log_warning "种子数据初始化失败（可能已经存在）"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "应用健康检查通过"
            return 0
        fi

        log_info "等待应用启动... ($attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    log_error "应用健康检查失败"
    exit 1
}

# 显示部署状态
show_status() {
    log_info "部署状态:"
    echo
    docker-compose ps
    echo
    log_info "服务地址:"
    echo "  API: http://localhost:8000"
    echo "  Web Dashboard: http://localhost:3000"
    echo "  Flower监控: http://localhost:5555"
    echo "  Grafana监控: http://localhost:3001 (生产环境)"
    echo "  Prometheus: http://localhost:9090 (生产环境)"
}

# 主函数
main() {
    local environment=""
    local force_build=false
    local no_cache=false
    local pull_code_flag=false
    local backup_flag=false
    local migrate_flag=false
    local seed_flag=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|staging|prod)
                environment="$1"
                shift
                ;;
            --build)
                force_build=true
                shift
                ;;
            --no-cache)
                no_cache=true
                shift
                ;;
            --pull)
                pull_code_flag=true
                shift
                ;;
            --backup)
                backup_flag=true
                shift
                ;;
            --migrate)
                migrate_flag=true
                shift
                ;;
            --seed)
                seed_flag=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 检查环境参数
    if [[ -z "$environment" ]]; then
        log_error "请指定部署环境 (dev|staging|prod)"
        show_help
        exit 1
    fi

    # 开始部署流程
    log_info "开始1688sync $environment 环境部署..."

    # 导出变量
    export FORCE_BUILD="$force_build"
    export NO_CACHE="$no_cache"

    # 执行部署步骤
    check_dependencies
    setup_environment "$environment"

    if [[ "$pull_code_flag" == "true" ]]; then
        pull_code
    fi

    if [[ "$backup_flag" == "true" ]]; then
        backup_data
    fi

    build_images
    start_services

    if [[ "$migrate_flag" == "true" ]]; then
        run_migrations
    fi

    if [[ "$seed_flag" == "true" ]]; then
        seed_data
    fi

    health_check
    show_status

    log_success "1688sync $environment 环境部署完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi