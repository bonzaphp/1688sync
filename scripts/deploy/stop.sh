#!/bin/bash

# 1688sync停止和清理脚本
# 用法: ./stop.sh [选项]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

show_help() {
    cat << EOF
1688sync停止和清理脚本

用法: $0 [选项]

选项:
    --remove-volumes  删除数据卷 (危险操作)
    --remove-images   删除相关镜像
    --backup          停止前备份数据
    --force           强制停止，不询问确认
    --help            显示此帮助信息

示例:
    $0                    # 停止服务
    $0 --backup           # 停止前备份数据
    $0 --remove-volumes   # 停止并删除所有数据
    $0 --remove-images    # 停止并删除镜像

EOF
}

# 确认操作
confirm() {
    if [[ "$FORCE" == "true" ]]; then
        return 0
    fi

    echo -n "$1 (y/N): "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 备份数据
backup_data() {
    log_info "停止前备份数据..."

    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)_shutdown"
    mkdir -p "$backup_dir"

    # 备份数据库
    if docker-compose ps mysql 2>/dev/null | grep -q "Up"; then
        log_info "备份MySQL数据库..."
        if docker-compose exec -T mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" 1688sync > "$backup_dir/database.sql" 2>/dev/null; then
            log_success "数据库备份完成"
        else
            log_warning "数据库备份失败"
        fi
    fi

    # 备份Redis
    if docker-compose ps redis 2>/dev/null | grep -q "Up"; then
        log_info "备份Redis数据..."
        docker-compose exec -T redis redis-cli BGSAVE > /dev/null 2>&1 || true
        sleep 2
        docker cp "$(docker-compose ps -q redis 2>/dev/null):/data/dump.rdb" "$backup_dir/" 2>/dev/null || log_warning "Redis备份失败"
    fi

    # 备份应用数据
    if [[ -d "data" ]]; then
        log_info "备份应用数据..."
        cp -r data "$backup_dir/" 2>/dev/null || log_warning "应用数据备份失败"
    fi

    log_success "数据备份完成: $backup_dir"
}

# 停止服务
stop_services() {
    log_info "停止1688sync服务..."

    if docker-compose down; then
        log_success "服务停止完成"
    else
        log_warning "服务停止时出现警告"
    fi
}

# 清理容器和网络
cleanup_containers() {
    log_info "清理停止的容器和网络..."

    # 清理停止的容器
    if docker container prune -f > /dev/null 2>&1; then
        log_success "容器清理完成"
    fi

    # 清理未使用的网络
    if docker network prune -f > /dev/null 2>&1; then
        log_success "网络清理完成"
    fi
}

# 删除数据卷
remove_volumes() {
    if ! confirm "确定要删除所有数据卷吗？这将删除所有数据！"; then
        log_info "取消删除数据卷"
        return 0
    fi

    log_warning "正在删除数据卷..."

    # 删除项目相关的卷
    local volumes=(
        "epic-1688sync_mysql_data"
        "epic-1688sync_redis_data"
        "epic-1688sync_mysql_data_prod"
        "epic-1688sync_redis_data_prod"
        "epic-1688sync_app_data"
        "epic-1688sync_app_logs"
        "epic-1688sync_app_checkpoints"
        "epic-1688sync_app_backups"
        "epic-1688sync_mysql_backup"
        "epic-1688sync_prometheus_data"
        "epic-1688sync_grafana_data"
    )

    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "^${volume}$"; then
            log_info "删除卷: $volume"
            docker volume rm "$volume" 2>/dev/null || log_warning "删除卷 $volume 失败"
        fi
    done

    log_success "数据卷删除完成"
}

# 删除镜像
remove_images() {
    if ! confirm "确定要删除1688sync相关镜像吗？"; then
        log_info "取消删除镜像"
        return 0
    fi

    log_warning "正在删除1688sync相关镜像..."

    # 删除项目镜像
    local images=(
        "epic-1688sync_app"
        "epic-1688sync_app-prod"
        "epic-1688sync_worker"
        "epic-1688sync_beat"
        "epic-1688sync_flower"
        "epic-1688sync_dashboard"
    )

    for image in "${images[@]}"; do
        if docker images -q "$image" | grep -q .; then
            log_info "删除镜像: $image"
            docker rmi "$image" 2>/dev/null || log_warning "删除镜像 $image 失败"
        fi
    done

    # 清理悬空镜像
    if docker image prune -f > /dev/null 2>&1; then
        log_success "悬空镜像清理完成"
    fi

    log_success "镜像删除完成"
}

# 显示状态
show_status() {
    log_info "当前状态:"
    echo
    echo "容器:"
    docker ps -a --filter "name=1688sync" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  无相关容器"
    echo
    echo "数据卷:"
    docker volume ls --filter "name=epic-1688sync" --format "table {{.Name}}\t{{.Driver}}" || echo "  无相关数据卷"
    echo
    echo "镜像:"
    docker images --filter "reference=epic-1688sync*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" || echo "  无相关镜像"
}

# 主函数
main() {
    local remove_volumes_flag=false
    local remove_images_flag=false
    local backup_flag=false
    local force_flag=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --remove-volumes)
                remove_volumes_flag=true
                shift
                ;;
            --remove-images)
                remove_images_flag=true
                shift
                ;;
            --backup)
                backup_flag=true
                shift
                ;;
            --force)
                force_flag=true
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

    export FORCE="$force_flag"

    log_info "开始1688sync停止和清理流程..."

    # 检查Docker
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 备份数据
    if [[ "$backup_flag" == "true" ]]; then
        backup_data
    fi

    # 停止服务
    stop_services

    # 清理容器和网络
    cleanup_containers

    # 删除数据卷
    if [[ "$remove_volumes_flag" == "true" ]]; then
        remove_volumes
    fi

    # 删除镜像
    if [[ "$remove_images_flag" == "true" ]]; then
        remove_images
    fi

    # 显示最终状态
    show_status

    log_success "1688sync停止和清理完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi