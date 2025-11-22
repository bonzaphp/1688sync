#!/bin/bash

# 1688sync定时备份脚本
# 用于crontab定时任务

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# 切换到项目目录
cd "$PROJECT_DIR"

# 日志文件
LOG_FILE="logs/cron-backup.log"

# 创建日志目录
mkdir -p logs

# 日志函数
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_info() {
    log_with_timestamp "[INFO] $1"
}

log_success() {
    log_with_timestamp "[SUCCESS] $1"
}

log_warning() {
    log_with_timestamp "[WARNING] $1"
}

log_error() {
    log_with_timestamp "[ERROR] $1"
}

# 检查是否已有备份任务在运行
check_running_backup() {
    if pgrep -f "backup.sh.*all" > /dev/null; then
        log_warning "已有备份任务在运行，跳过本次执行"
        exit 0
    fi
}

# 执行备份
perform_backup() {
    local backup_type="$1"
    local extra_args="$2"

    log_info "开始定时备份 - 类型: $backup_type"

    # 执行备份脚本
    if ./scripts/backup/backup.sh "$backup_type" $extra_args --compress --clean 2>&1 | tee -a "$LOG_FILE"; then
        log_success "定时备份完成"

        # 发送成功通知（可选）
        # send_notification "1688sync备份成功" "备份类型: $backup_type\n时间: $(date)"
    else
        log_error "定时备份失败"

        # 发送失败通知（可选）
        # send_notification "1688sync备份失败" "备份类型: $backup_type\n时间: $(date)\n请检查日志: $LOG_FILE"
        exit 1
    fi
}

# 发送通知函数（示例）
send_notification() {
    local title="$1"
    local message="$2"

    # 邮件通知示例（需要配置邮件服务）
    # echo "$message" | mail -s "$title" admin@example.com

    # Slack通知示例
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"$title\n$message\"}" \
    #     https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

    # 企业微信通知示例
    # curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
    #     -H "Content-Type: application/json" \
    #     -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"$title\n$message\"}}"
}

# 清理旧日志
cleanup_logs() {
    # 保留最近30天的日志
    find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true

    # 压缩7天前的日志
    find logs/ -name "*.log" -mtime +7 -exec gzip {} \; 2>/dev/null || true
}

# 磁盘空间检查
check_disk_space() {
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local required_space=1048576  # 1GB in KB

    if [[ $available_space -lt $required_space ]]; then
        log_error "磁盘空间不足，可用空间: ${available_space}KB，需要至少1GB"
        # send_notification "1688sync备份失败" "磁盘空间不足"
        exit 1
    fi
}

# 主函数
main() {
    local backup_type="all"

    # 解析参数
    case "${1:-all}" in
        "database"|"redis"|"files"|"logs"|"config"|"all")
            backup_type="$1"
            ;;
        *)
            log_error "无效的备份类型: $1"
            exit 1
            ;;
    esac

    # 检查运行状态
    check_running_backup

    # 检查磁盘空间
    check_disk_space

    # 执行备份
    perform_backup "$backup_type"

    # 清理日志
    cleanup_logs

    log_success "定时备份任务完成"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi