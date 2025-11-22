#!/bin/bash

# 1688sync恢复脚本
# 用法: ./restore.sh <备份目录> [选项]

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
1688sync恢复脚本

用法: $0 <备份目录> [选项]

参数:
    备份目录        备份文件所在的目录路径

选项:
    --database      仅恢复数据库
    --redis         仅恢复Redis
    --files         仅恢复应用文件
    --logs          仅恢复日志文件
    --config        仅恢复配置文件
    --force         强制覆盖现有数据
    --dry-run       预演模式，不执行实际恢复
    --help          显示此帮助信息

示例:
    $0 backups/20231201_120000
    $0 backups/20231201_120000 --database
    $0 backups/20231201_120000 --force
    $0 backups/20231201_120000 --dry-run

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

# 检查依赖
check_dependencies() {
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml文件不存在"
        exit 1
    fi
}

# 验证备份目录
validate_backup_dir() {
    local backup_dir=$1

    if [[ ! -d "$backup_dir" ]]; then
        log_error "备份目录不存在: $backup_dir"
        exit 1
    fi

    if [[ ! -f "$backup_dir/backup_report.txt" ]]; then
        log_warning "备份报告文件不存在，可能不是完整的备份"
    fi

    log_info "备份目录验证通过: $backup_dir"
}

# 恢复数据库
restore_database() {
    local backup_dir=$1

    log_info "恢复MySQL数据库..."

    # 检查MySQL服务状态
    if ! docker-compose ps mysql | grep -q "Up"; then
        log_error "MySQL服务未运行，请先启动服务"
        return 1
    fi

    # 查找数据库备份文件
    local db_backup_file=""
    if [[ -f "$backup_dir/database_1688sync.sql.gz" ]]; then
        db_backup_file="$backup_dir/database_1688sync.sql.gz"
    elif [[ -f "$backup_dir/database_1688sync.sql" ]]; then
        db_backup_file="$backup_dir/database_1688sync.sql"
    elif [[ -f "$backup_dir/database_all.sql.gz" ]]; then
        db_backup_file="$backup_dir/database_all.sql.gz"
    elif [[ -f "$backup_dir/database_all.sql" ]]; then
        db_backup_file="$backup_dir/database_all.sql"
    else
        log_error "未找到数据库备份文件"
        return 1
    fi

    log_info "使用数据库备份文件: $db_backup_file"

    # 确认恢复操作
    if ! confirm "确定要恢复数据库吗？这将覆盖现有数据！"; then
        log_info "取消数据库恢复"
        return 0
    fi

    # 执行恢复
    if [[ "$db_backup_file" == *.gz ]]; then
        log_info "恢复压缩的数据库备份..."
        gunzip -c "$db_backup_file" | docker-compose exec -T mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD"
    else
        log_info "恢复数据库备份..."
        docker-compose exec -T mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" < "$db_backup_file"
    fi

    log_success "数据库恢复完成"
}

# 恢复Redis
restore_redis() {
    local backup_dir=$1

    log_info "恢复Redis数据..."

    # 检查Redis服务状态
    if ! docker-compose ps redis | grep -q "Up"; then
        log_error "Redis服务未运行，请先启动服务"
        return 1
    fi

    # 查找Redis备份文件
    local redis_backup_file=""
    if [[ -f "$backup_dir/redis_dump.rdb.gz" ]]; then
        redis_backup_file="$backup_dir/redis_dump.rdb.gz"
    elif [[ -f "$backup_dir/redis_dump.rdb" ]]; then
        redis_backup_file="$backup_dir/redis_dump.rdb"
    else
        log_error "未找到Redis备份文件"
        return 1
    fi

    log_info "使用Redis备份文件: $redis_backup_file"

    # 确认恢复操作
    if ! confirm "确定要恢复Redis数据吗？这将覆盖现有数据！"; then
        log_info "取消Redis恢复"
        return 0
    fi

    # 停止Redis服务
    log_info "停止Redis服务..."
    docker-compose stop redis

    # 获取Redis容器数据目录
    local redis_container=$(docker-compose ps -q redis)
    local redis_data_dir=$(docker inspect "$redis_container" --format '{{ range .Mounts }}{{ if .Destination }}{{ .Destination }}{{ end }}{{ end }}' | grep data)

    # 清理现有数据
    log_info "清理现有Redis数据..."
    docker exec "$redis_container" rm -f /data/dump.rdb /data/appendonly.aof 2>/dev/null || true

    # 复制备份文件
    if [[ "$redis_backup_file" == *.gz ]]; then
        log_info "解压并复制Redis备份..."
        gunzip -c "$redis_backup_file" > /tmp/redis_dump.rdb
        docker cp /tmp/redis_dump.rdb "$redis_container:/data/dump.rdb"
        rm -f /tmp/redis_dump.rdb
    else
        log_info "复制Redis备份..."
        docker cp "$redis_backup_file" "$redis_container:/data/dump.rdb"
    fi

    # 设置权限
    docker exec "$redis_container" chown redis:redis /data/dump.rdb

    # 启动Redis服务
    log_info "启动Redis服务..."
    docker-compose start redis

    # 等待Redis就绪
    sleep 5

    # 验证恢复
    if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis恢复完成"
    else
        log_error "Redis恢复验证失败"
        return 1
    fi
}

# 恢复应用文件
restore_files() {
    local backup_dir=$1

    log_info "恢复应用文件..."

    local files_restored=false

    # 恢复数据目录
    if [[ -f "$backup_dir/files.tar.gz" ]]; then
        log_info "从压缩文件恢复应用文件..."
        tar -xzf "$backup_dir/files.tar.gz" -C "$backup_dir"/
        files_restored=true
    fi

    # 恢复data目录
    if [[ -d "$backup_dir/data" ]]; then
        if confirm "恢复data目录？这将覆盖现有数据目录"; then
            log_info "恢复data目录..."
            rm -rf data 2>/dev/null || true
            cp -r "$backup_dir/data" ./
            files_restored=true
        fi
    fi

    # 恢复images目录
    if [[ -d "$backup_dir/images" ]]; then
        if confirm "恢复images目录？这将覆盖现有图片目录"; then
            log_info "恢复images目录..."
            rm -rf images 2>/dev/null || true
            cp -r "$backup_dir/images" ./
            files_restored=true
        fi
    fi

    # 恢复checkpoints目录
    if [[ -d "$backup_dir/checkpoints" ]]; then
        if confirm "恢复checkpoints目录？这将覆盖现有检查点目录"; then
            log_info "恢复checkpoints目录..."
            rm -rf checkpoints 2>/dev/null || true
            cp -r "$backup_dir/checkpoints" ./
            files_restored=true
        fi
    fi

    if [[ "$files_restored" == "true" ]]; then
        log_success "应用文件恢复完成"
    else
        log_info "跳过应用文件恢复"
    fi
}

# 恢复日志文件
restore_logs() {
    local backup_dir=$1

    log_info "恢复日志文件..."

    if [[ -f "$backup_dir/logs.tar.gz" ]]; then
        log_info "从压缩文件恢复日志..."
        tar -xzf "$backup_dir/logs.tar.gz" -C "$backup_dir"/
    fi

    if [[ -d "$backup_dir/logs" ]]; then
        if confirm "恢复logs目录？这将覆盖现有日志目录"; then
            log_info "恢复logs目录..."
            rm -rf logs 2>/dev/null || true
            cp -r "$backup_dir/logs" ./
            log_success "日志文件恢复完成"
        else
            log_info "跳过日志文件恢复"
        fi
    else
        log_warning "未找到日志备份文件"
    fi
}

# 恢复配置文件
restore_config() {
    local backup_dir=$1

    log_info "恢复配置文件..."

    local config_restored=false

    if [[ -f "$backup_dir/config.tar.gz" ]]; then
        log_info "从压缩文件恢复配置..."
        tar -xzf "$backup_dir/config.tar.gz" -C "$backup_dir"/
        config_restored=true
    fi

    # 恢复环境配置文件
    if ls "$backup_dir"/.env* 1> /dev/null 2>&1; then
        if confirm "恢复环境配置文件？这将覆盖现有.env文件"; then
            log_info "恢复环境配置文件..."
            cp "$backup_dir"/.env* ./
            config_restored=true
        fi
    fi

    # 恢复Docker配置
    if ls "$backup_dir"/docker-compose*.yml 1> /dev/null 2>&1; then
        if confirm "恢复Docker配置文件？这将覆盖现有compose文件"; then
            log_info "恢复Docker配置文件..."
            cp "$backup_dir"/docker-compose*.yml ./
            config_restored=true
        fi
    fi

    # 恢复config目录
    if [[ -d "$backup_dir/config" ]]; then
        if confirm "恢复config目录？这将覆盖现有配置目录"; then
            log_info "恢复config目录..."
            rm -rf config 2>/dev/null || true
            cp -r "$backup_dir/config" ./
            config_restored=true
        fi
    fi

    # 恢复scripts目录
    if [[ -d "$backup_dir/scripts" ]]; then
        if confirm "恢复scripts目录？这将覆盖现有脚本目录"; then
            log_info "恢复scripts目录..."
            rm -rf scripts 2>/dev/null || true
            cp -r "$backup_dir/scripts" ./
            config_restored=true
        fi
    fi

    if [[ "$config_restored" == "true" ]]; then
        log_success "配置文件恢复完成"
        log_warning "配置文件已更新，可能需要重启服务"
    else
        log_info "跳过配置文件恢复"
    fi
}

# 验证恢复结果
verify_restore() {
    log_info "验证恢复结果..."

    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose ps

    # 检查数据库连接
    if docker-compose ps mysql | grep -q "Up"; then
        log_info "检查数据库连接..."
        if docker-compose exec mysql mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SHOW DATABASES;" &>/dev/null; then
            log_success "数据库连接正常"
        else
            log_warning "数据库连接异常"
        fi
    fi

    # 检查Redis连接
    if docker-compose ps redis | grep -q "Up"; then
        log_info "检查Redis连接..."
        if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
            log_success "Redis连接正常"
        else
            log_warning "Redis连接异常"
        fi
    fi

    log_success "恢复验证完成"
}

# 主函数
main() {
    local backup_dir=""
    local restore_type="all"
    local force=false
    local dry_run=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --database)
                restore_type="database"
                shift
                ;;
            --redis)
                restore_type="redis"
                shift
                ;;
            --files)
                restore_type="files"
                shift
                ;;
            --logs)
                restore_type="logs"
                shift
                ;;
            --config)
                restore_type="config"
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$backup_dir" ]]; then
                    backup_dir="$1"
                else
                    log_error "多余参数: $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # 检查备份目录参数
    if [[ -z "$backup_dir" ]]; then
        log_error "请指定备份目录"
        show_help
        exit 1
    fi

    # 导出变量
    export FORCE="$force"

    # 开始恢复流程
    log_info "开始1688sync恢复 - 备份目录: $backup_dir"

    # 检查依赖
    check_dependencies

    # 验证备份目录
    validate_backup_dir "$backup_dir"

    # 预演模式
    if [[ "$dry_run" == "true" ]]; then
        log_info "预演模式 - 仅显示将要执行的操作"
        log_info "恢复类型: $restore_type"
        log_info "备份目录: $backup_dir"
        log_info "预演模式完成，未执行实际恢复"
        exit 0
    fi

    # 执行恢复
    case "$restore_type" in
        "all")
            restore_config "$backup_dir"
            restore_files "$backup_dir"
            restore_database "$backup_dir"
            restore_redis "$backup_dir"
            restore_logs "$backup_dir"
            ;;
        "database")
            restore_database "$backup_dir"
            ;;
        "redis")
            restore_redis "$backup_dir"
            ;;
        "files")
            restore_files "$backup_dir"
            ;;
        "logs")
            restore_logs "$backup_dir"
            ;;
        "config")
            restore_config "$backup_dir"
            ;;
    esac

    # 验证恢复结果
    verify_restore

    log_success "1688sync恢复完成！"
    log_warning "建议重启服务以确保所有配置生效"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi