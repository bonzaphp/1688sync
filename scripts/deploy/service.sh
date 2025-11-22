#!/bin/bash

# 1688sync服务管理脚本
# 用法: ./service.sh [操作] [服务名]

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
1688sync服务管理脚本

用法: $0 [操作] [服务名]

操作:
    status          显示所有服务状态
    logs            查看服务日志
    restart         重启服务
    start           启动服务
    stop            停止服务
    exec            在服务容器中执行命令
    update          更新服务镜像并重启
    scale           扩展服务实例数量
    health          检查服务健康状态
    clean           清理服务资源

服务名 (可选):
    app             主应用服务
    celery-worker   Celery工作进程
    celery-beat     Celery调度器
    celery-flower   Celery监控
    mysql           MySQL数据库
    redis           Redis缓存
    web-dashboard   Web前端
    nginx           反向代理
    prometheus      监控服务
    grafana         监控面板

示例:
    $0 status                    # 显示所有服务状态
    $0 logs app                  # 查看应用日志
    $0 restart celery-worker     # 重启Celery工作进程
    $0 exec mysql bash           # 进入MySQL容器
    $0 scale app 3               # 扩展应用到3个实例
    $0 health                    # 检查所有服务健康状态

EOF
}

# 检查Docker Compose
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml文件不存在"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "1688sync服务状态:"
    echo
    docker-compose ps
    echo

    # 显示资源使用情况
    log_info "资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" \
        $(docker-compose ps -q) 2>/dev/null || echo "  无法获取资源信息"
}

# 查看服务日志
show_logs() {
    local service=$1
    local follow=${2:-false}
    local lines=${3:-100}

    if [[ -z "$service" ]]; then
        log_info "查看所有服务日志 (最近 $lines 行)..."
        docker-compose logs --tail="$lines"
    else
        log_info "查看 $service 服务日志..."
        if [[ "$follow" == "true" ]]; then
            docker-compose logs -f --tail="$lines" "$service"
        else
            docker-compose logs --tail="$lines" "$service"
        fi
    fi
}

# 重启服务
restart_service() {
    local service=$1

    if [[ -z "$service" ]]; then
        log_info "重启所有服务..."
        docker-compose restart
    else
        log_info "重启 $service 服务..."
        docker-compose restart "$service"
    fi

    log_success "服务重启完成"
}

# 启动服务
start_service() {
    local service=$1

    if [[ -z "$service" ]]; then
        log_info "启动所有服务..."
        docker-compose up -d
    else
        log_info "启动 $service 服务..."
        docker-compose up -d "$service"
    fi

    log_success "服务启动完成"
}

# 停止服务
stop_service() {
    local service=$1

    if [[ -z "$service" ]]; then
        log_info "停止所有服务..."
        docker-compose stop
    else
        log_info "停止 $service 服务..."
        docker-compose stop "$service"
    fi

    log_success "服务停止完成"
}

# 在服务容器中执行命令
exec_command() {
    local service=$1
    shift

    if [[ -z "$service" ]]; then
        log_error "请指定服务名"
        exit 1
    fi

    log_info "在 $service 容器中执行: $*"
    docker-compose exec "$service" "$@"
}

# 更新服务
update_service() {
    local service=$1

    if [[ -z "$service" ]]; then
        log_info "更新所有服务..."
        docker-compose pull
        docker-compose up -d
    else
        log_info "更新 $service 服务..."
        docker-compose pull "$service"
        docker-compose up -d "$service"
    fi

    log_success "服务更新完成"
}

# 扩展服务
scale_service() {
    local service=$1
    local replicas=$2

    if [[ -z "$service" || -z "$replicas" ]]; then
        log_error "请指定服务名和实例数量"
        exit 1
    fi

    log_info "扩展 $service 服务到 $replicas 个实例..."
    docker-compose up -d --scale "$service=$replicas" "$service"

    log_success "服务扩展完成"
}

# 健康检查
health_check() {
    log_info "执行服务健康检查..."

    local services=(
        "app:8000/health"
        "mysql:3306"
        "redis:6379"
    )

    for service_info in "${services[@]}"; do
        local service=$(echo "$service_info" | cut -d: -f1)
        local check_info=$(echo "$service_info" | cut -d: -f2-)

        case "$service" in
            "app")
                if curl -f "http://localhost:$check_info" &> /dev/null; then
                    log_success "$service: 健康"
                else
                    log_error "$service: 不健康"
                fi
                ;;
            "mysql")
                if docker-compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
                    log_success "$service: 健康"
                else
                    log_error "$service: 不健康"
                fi
                ;;
            "redis")
                if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
                    log_success "$service: 健康"
                else
                    log_error "$service: 不健康"
                fi
                ;;
        esac
    done
}

# 清理服务资源
clean_service() {
    log_info "清理服务资源..."

    # 清理停止的容器
    docker container prune -f > /dev/null 2>&1

    # 清理未使用的网络
    docker network prune -f > /dev/null 2>&1

    # 清理悬空镜像
    docker image prune -f > /dev/null 2>&1

    log_success "服务资源清理完成"
}

# 主函数
main() {
    local operation=$1
    local service=$2
    local extra_args=("${@:3}")

    # 检查Docker Compose
    check_docker_compose

    case "$operation" in
        "status")
            show_status
            ;;
        "logs")
            if [[ "$service" == "-f" || "$service" == "--follow" ]]; then
                show_logs "" true "${extra_args[0]}"
            elif [[ "${extra_args[0]}" == "-f" || "${extra_args[0]}" == "--follow" ]]; then
                show_logs "$service" true "${extra_args[1]}"
            else
                show_logs "$service" false "${extra_args[0]}"
            fi
            ;;
        "restart")
            restart_service "$service"
            ;;
        "start")
            start_service "$service"
            ;;
        "stop")
            stop_service "$service"
            ;;
        "exec")
            exec_command "$service" "${extra_args[@]}"
            ;;
        "update")
            update_service "$service"
            ;;
        "scale")
            scale_service "$service" "${extra_args[0]}"
            ;;
        "health")
            health_check
            ;;
        "clean")
            clean_service
            ;;
        "--help"|"help"|"")
            show_help
            ;;
        *)
            log_error "未知操作: $operation"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi