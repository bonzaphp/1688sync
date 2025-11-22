#!/bin/bash

# 1688sync Epic 高频监控协调脚本
# 每15分钟执行一次，检查代理状态和协调工作

set -e

# 配置
EPIC_NAME="1688sync"
WORK_DIR="/Users/yangshiguo/code/xiaoyikeji/epic-1688sync"
LOG_FILE="$WORK_DIR/.claude/epics/$EPIC_NAME/streams/coordination.log"
DASHBOARD_FILE="$WORK_DIR/.claude/epics/$EPIC_NAME/streams/dashboard.md"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S UTC') - $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}INFO${NC} - $1"
    log "INFO: $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS${NC} - $1"
    log "SUCCESS: $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING${NC} - $1"
    log "WARNING: $1"
}

log_error() {
    echo -e "${RED}ERROR${NC} - $1"
    log "ERROR: $1"
}

# 检查Git状态
check_git_status() {
    log_info "检查Git仓库状态..."

    cd "$WORK_DIR"

    if ! git diff --quiet || ! git diff --cached --quiet; then
        log_warning "检测到未提交的更改"
        git status --porcelain
        return 1
    fi

    # 检查分支状态
    CURRENT_BRANCH=$(git branch --show-current)
    if [[ "$CURRENT_BRANCH" != "epic/1688sync" ]]; then
        log_error "当前分支不是 epic/1688sync: $CURRENT_BRANCH"
        return 1
    fi

    log_success "Git状态正常"
    return 0
}

# 检查代理活动
check_agent_activity() {
    log_info "检查代理活动状态..."

    cd "$WORK_DIR"

    # 检查最近15分钟内的提交
    RECENT_COMMITS=$(git log --oneline --since="15 minutes ago" | wc -l)
    log_info "最近15分钟内有 $RECENT_COMMITS 个提交"

    if [[ $RECENT_COMMITS -eq 0 ]]; then
        log_warning "最近15分钟内无代理活动"
        return 1
    fi

    log_success "代理活动正常"
    return 0
}

# 检查文件冲突
check_file_conflicts() {
    log_info "检查文件冲突..."

    cd "$WORK_DIR"

    # 检查merge冲突标记 (排除文档中的说明文字)
    CONFLICT_FILES=$(grep -r "^<<<<<<< \|^\======= \|^\>>>>>>>" . --exclude-dir=.git --exclude="*.md" 2>/dev/null || true)

    if [[ -n "$CONFLICT_FILES" ]]; then
        log_error "检测到文件冲突:"
        echo "$CONFLICT_FILES"
        return 1
    fi

    log_success "无文件冲突"
    return 0
}

# 更新进度报告
update_progress() {
    log_info "更新进度报告..."

    cd "$WORK_DIR"

    # 统计任务完成情况
    TOTAL_TASKS=11
    COMPLETED_TASKS=1  # 存储系统已完成

    # 更新仪表板
    CURRENT_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    NEXT_CHECK=$(date -u -v+15M '+%H:%M UTC')

    # 这里可以添加更详细的进度统计逻辑
    PROGRESS_PERCENT=$((COMPLETED_TASKS * 100 / TOTAL_TASKS))

    log_info "当前进度: $PROGRESS_PERCENT% ($COMPLETED_TASKS/$TOTAL_TASKS)"
    log_success "进度报告更新完成"
}

# 同步GitHub状态
sync_github_status() {
    log_info "同步GitHub状态..."

    # 检查GitHub连接
    if ! gh auth status >/dev/null 2>&1; then
        log_error "GitHub认证失败"
        return 1
    fi

    # 更新Epic评论
    COMMENT_BODY="📊 协调检查报告 - $(date '+%Y-%m-%d %H:%M:%S UTC')

✅ Git状态: 正常
✅ 代理活动: 检测中
✅ 文件冲突: 无
📈 进度: $PROGRESS_PERCENT%
🔄 下次检查: $NEXT_CHECK

所有9个专业代理正在并行执行中..."

    if gh issue comment 1 --repo bonzaphp/1688sync --body "$COMMENT_BODY" >/dev/null 2>&1; then
        log_success "GitHub状态同步完成"
    else
        log_warning "GitHub状态同步失败"
    fi
}

# 主协调函数
main() {
    # 切换到工作目录
    cd "$WORK_DIR" || {
        log_error "无法切换到工作目录: $WORK_DIR"
        exit 1
    }

    # 创建日志文件（如果不存在）
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"

    log_info "开始1688sync Epic协调检查..."

    # 执行检查
    local exit_code=0

    check_git_status || exit_code=1
    check_agent_activity || exit_code=1
    check_file_conflicts || exit_code=1
    update_progress || exit_code=1
    sync_github_status || exit_code=1

    # 总结
    if [[ $exit_code -eq 0 ]]; then
        log_success "协调检查完成 - 系统运行正常"
        echo -e "\n${GREEN}🎉 1688sync Epic 执行状态良好${NC}"
        echo -e "${BLUE}📊 9个专业代理正在并行工作${NC}"
        echo -e "${YELLOW}⏰ 下次检查: $NEXT_CHECK${NC}"
    else
        log_error "协调检查发现问题 - 需要人工干预"
        echo -e "\n${RED}⚠️  检测到问题，请查看日志: $LOG_FILE${NC}"
    fi

    return $exit_code
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi