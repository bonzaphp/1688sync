#!/bin/bash

# 1688sync备份脚本
# 用法: ./backup.sh [类型] [选项]

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
1688sync备份脚本

用法: $0 [类型] [选项]

类型:
    all             备份所有数据（默认）
    database        仅备份数据库
    redis           仅备份Redis
    files           仅备份应用文件
    logs            仅备份日志文件
    config          仅备份配置文件

选项:
    --compress      压缩备份文件
    --upload        上传到远程存储
    --clean         备份后清理旧文件
    --quiet         静默模式
    --help          显示此帮助信息

示例:
    $0 all --compress --upload
    $0 database --clean
    $0 files --compress

EOF
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

# 创建备份目录
create_backup_dir() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

# 备份数据库
backup_database() {
    local backup_dir=$1
    local compress=$2

    log_info "备份MySQL数据库..."

    # 检查MySQL服务状态
    if ! docker-compose ps mysql | grep -q "Up"; then
        log_warning "MySQL服务未运行，跳过数据库备份"
        return 0
    fi

    # 备份所有数据库
    local db_backup_file="$backup_dir/database_all.sql"
    if docker-compose exec -T mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" --all-databases --routines --triggers --events > "$db_backup_file"; then
        log_success "数据库备份完成: $db_backup_file"

        # 备份特定数据库
        local app_db_backup_file="$backup_dir/database_1688sync.sql"
        if docker-compose exec -T mysql mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" 1688sync > "$app_db_backup_file"; then
            log_success "应用数据库备份完成: $app_db_backup_file"
        fi
    else
        log_error "数据库备份失败"
        return 1
    fi

    # 压缩备份文件
    if [[ "$compress" == "true" ]]; then
        log_info "压缩数据库备份..."
        gzip "$backup_dir"/database_*.sql
        log_success "数据库备份压缩完成"
    fi
}

# 备份Redis
backup_redis() {
    local backup_dir=$1
    local compress=$2

    log_info "备份Redis数据..."

    # 检查Redis服务状态
    if ! docker-compose ps redis | grep -q "Up"; then
        log_warning "Redis服务未运行，跳过Redis备份"
        return 0
    fi

    # 触发Redis保存
    docker-compose exec redis redis-cli BGSAVE > /dev/null 2>&1 || true
    sleep 2

    # 复制RDB文件
    local redis_container=$(docker-compose ps -q redis)
    if docker cp "$redis_container:/data/dump.rdb" "$backup_dir/redis_dump.rdb"; then
        log_success "Redis备份完成: $backup_dir/redis_dump.rdb"

        # 备份AOF文件（如果存在）
        if docker cp "$redis_container:/data/appendonly.aof" "$backup_dir/redis_appendonly.aof" 2>/dev/null; then
            log_success "Redis AOF备份完成: $backup_dir/redis_appendonly.aof"
        fi
    else
        log_error "Redis备份失败"
        return 1
    fi

    # 压缩备份文件
    if [[ "$compress" == "true" ]]; then
        log_info "压缩Redis备份..."
        gzip "$backup_dir"/redis_*
        log_success "Redis备份压缩完成"
    fi
}

# 备份应用文件
backup_files() {
    local backup_dir=$1
    local compress=$2

    log_info "备份应用文件..."

    # 备份数据目录
    if [[ -d "data" ]]; then
        log_info "备份数据目录..."
        cp -r data "$backup_dir/"
        log_success "数据目录备份完成"
    fi

    # 备份图片目录
    if [[ -d "images" ]]; then
        log_info "备份图片目录..."
        cp -r images "$backup_dir/"
        log_success "图片目录备份完成"
    fi

    # 备份检查点目录
    if [[ -d "checkpoints" ]]; then
        log_info "备份检查点目录..."
        cp -r checkpoints "$backup_dir/"
        log_success "检查点目录备份完成"
    fi

    # 压缩备份文件
    if [[ "$compress" == "true" ]]; then
        log_info "压缩文件备份..."
        tar -czf "$backup_dir/files.tar.gz" -C "$backup_dir" data images checkpoints 2>/dev/null || true
        rm -rf "$backup_dir"/data "$backup_dir"/images "$backup_dir"/checkpoints 2>/dev/null || true
        log_success "文件备份压缩完成"
    fi
}

# 备份日志文件
backup_logs() {
    local backup_dir=$1
    local compress=$2

    log_info "备份日志文件..."

    if [[ -d "logs" ]]; then
        log_info "备份日志目录..."
        cp -r logs "$backup_dir/"
        log_success "日志目录备份完成"
    fi

    # 压缩备份文件
    if [[ "$compress" == "true" ]]; then
        log_info "压缩日志备份..."
        tar -czf "$backup_dir/logs.tar.gz" -C "$backup_dir" logs 2>/dev/null || true
        rm -rf "$backup_dir/logs" 2>/dev/null || true
        log_success "日志备份压缩完成"
    fi
}

# 备份配置文件
backup_config() {
    local backup_dir=$1
    local compress=$2

    log_info "备份配置文件..."

    # 创建配置目录
    mkdir -p "$backup_dir/config"

    # 备份环境配置文件
    if ls .env* 1> /dev/null 2>&1; then
        log_info "备份环境配置文件..."
        cp .env* "$backup_dir/config/"
    fi

    # 备份Docker配置
    if [[ -f "docker-compose.yml" ]]; then
        log_info "备份Docker配置..."
        cp docker-compose*.yml "$backup_dir/config/"
    fi

    # 备份配置目录
    if [[ -d "config" ]]; then
        log_info "备份配置目录..."
        cp -r config "$backup_dir/"
    fi

    # 备份脚本文件
    if [[ -d "scripts" ]]; then
        log_info "备份脚本文件..."
        cp -r scripts "$backup_dir/"
    fi

    # 压缩备份文件
    if [[ "$compress" == "true" ]]; then
        log_info "压缩配置备份..."
        tar -czf "$backup_dir/config.tar.gz" -C "$backup_dir" config scripts 2>/dev/null || true
        rm -rf "$backup_dir/config" "$backup_dir/scripts" 2>/dev/null || true
        log_success "配置备份压缩完成"
    fi
}

# 上传到远程存储
upload_backup() {
    local backup_dir=$1

    log_info "上传备份到远程存储..."

    # 这里可以添加上传到云存储的逻辑
    # 例如：AWS S3, 阿里云OSS, 腾讯云COS等

    # 示例：使用AWS S3
    # if command -v aws &> /dev/null; then
    #     aws s3 sync "$backup_dir" "s3://your-backup-bucket/1688sync/$(basename $backup_dir)/"
    #     log_success "备份上传到S3完成"
    # fi

    log_warning "远程上传功能未配置，跳过上传"
}

# 清理旧备份
clean_old_backups() {
    local retention_days=${1:-30}

    log_info "清理 $retention_days 天前的备份文件..."

    # 删除旧备份目录
    find backups/ -type d -name "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]" -mtime +$retention_days -exec rm -rf {} + 2>/dev/null || true

    # 删除空目录
    find backups/ -type d -empty -delete 2>/dev/null || true

    log_success "旧备份清理完成"
}

# 生成备份报告
generate_backup_report() {
    local backup_dir=$1
    local backup_type=$2
    local start_time=$3
    local end_time=$4

    local report_file="$backup_dir/backup_report.txt"

    cat > "$report_file" << EOF
1688sync 备份报告
==================

备份类型: $backup_type
备份时间: $(date)
开始时间: $start_time
结束时间: $end_time
耗时: $((end_time - start_time)) 秒

备份目录: $(basename "$backup_dir")

备份内容:
$(ls -la "$backup_dir")

磁盘使用:
$(du -sh "$backup_dir")

系统信息:
- 操作系统: $(uname -s)
- 内核版本: $(uname -r)
- Docker版本: $(docker --version 2>/dev/null || echo "未安装")
- Docker Compose版本: $(docker-compose --version 2>/dev/null || echo "未安装")

服务状态:
$(docker-compose ps)

EOF

    log_success "备份报告生成完成: $report_file"
}

# 主函数
main() {
    local backup_type="all"
    local compress=false
    local upload=false
    local clean=false
    local quiet=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            all|database|redis|files|logs|config)
                backup_type="$1"
                shift
                ;;
            --compress)
                compress=true
                shift
                ;;
            --upload)
                upload=true
                shift
                ;;
            --clean)
                clean=true
                shift
                ;;
            --quiet)
                quiet=true
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

    # 静默模式设置
    if [[ "$quiet" == "true" ]]; then
        exec 1>/dev/null
    fi

    # 开始备份
    local start_time=$(date +%s)
    log_info "开始1688sync备份 - 类型: $backup_type"

    # 检查依赖
    check_dependencies

    # 创建备份目录
    local backup_dir=$(create_backup_dir)
    log_info "备份目录: $backup_dir"

    # 执行备份
    case "$backup_type" in
        "all")
            backup_database "$backup_dir" "$compress"
            backup_redis "$backup_dir" "$compress"
            backup_files "$backup_dir" "$compress"
            backup_logs "$backup_dir" "$compress"
            backup_config "$backup_dir" "$compress"
            ;;
        "database")
            backup_database "$backup_dir" "$compress"
            ;;
        "redis")
            backup_redis "$backup_dir" "$compress"
            ;;
        "files")
            backup_files "$backup_dir" "$compress"
            ;;
        "logs")
            backup_logs "$backup_dir" "$compress"
            ;;
        "config")
            backup_config "$backup_dir" "$compress"
            ;;
    esac

    # 上传备份
    if [[ "$upload" == "true" ]]; then
        upload_backup "$backup_dir"
    fi

    # 清理旧备份
    if [[ "$clean" == "true" ]]; then
        clean_old_backups 30
    fi

    # 生成报告
    local end_time=$(date +%s)
    generate_backup_report "$backup_dir" "$backup_type" "$start_time" "$end_time"

    log_success "1688sync备份完成！"
    log_info "备份位置: $backup_dir"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi