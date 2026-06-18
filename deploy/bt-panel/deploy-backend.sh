#!/bin/bash
# ============================================================
# 后端单独部署/更新脚本
# 在已初始化的环境中使用
# ============================================================

set -e

PROJECT_DIR="/www/bid-review-system"
BACKEND_DIR="${PROJECT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
LOG_FILE="/www/logs/bid-review-backend.log"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 停止现有服务
stop_service() {
    log_info "停止现有服务..."
    PID_FILE="${PROJECT_DIR}/backend.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 2
            log_info "服务已停止 (PID: $PID)"
        fi
        rm -f "$PID_FILE"
    fi

    # 也尝试通过端口查找
    PID=$(lsof -ti:8000 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
        sleep 2
    fi
}

# 更新代码
update_code() {
    log_info "更新后端代码..."

    cd "${BACKEND_DIR}"

    # 如果是 git 仓库，拉取最新代码
    if [ -d ".git" ]; then
        git pull origin main
        log_info "代码已更新"
    else
        log_warn "非 git 仓库，跳过代码更新"
    fi
}

# 更新依赖
update_deps() {
    log_info "更新 Python 依赖..."
    cd "${BACKEND_DIR}"

    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate

    log_info "依赖更新完成"
}

# 数据库迁移
migrate_db() {
    log_info "执行数据库迁移..."
    cd "${BACKEND_DIR}"

    source venv/bin/activate
    python -c "
import asyncio
from app.core.database import engine, Base
from app.models import *
async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print('Database migration completed')
asyncio.run(migrate())
"
    deactivate
}

# 启动服务
start_service() {
    log_info "启动后端服务..."
    cd "${BACKEND_DIR}"

    source venv/bin/activate

    # 创建日志目录
    mkdir -p /www/logs

    nohup gunicorn -c gunicorn_config.py main:app \
        >> "${LOG_FILE}" 2>&1 &

    echo $! > "${PROJECT_DIR}/backend.pid"
    deactivate

    # 等待启动
    sleep 3

    if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
        log_info "✅ 后端服务启动成功 (PID: $(cat ${PROJECT_DIR}/backend.pid))"
    else
        log_error "❌ 后端服务启动失败，请检查日志: ${LOG_FILE}"
        tail -20 "${LOG_FILE}"
    fi
}

# 查看日志
show_logs() {
    log_info "最近日志:"
    tail -50 "${LOG_FILE}"
}

# 主菜单
case "${1:-deploy}" in
    deploy)
        stop_service
        update_code
        update_deps
        migrate_db
        start_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 1
        start_service
        ;;
    logs)
        show_logs
        ;;
    migrate)
        migrate_db
        ;;
    *)
        echo "用法: $0 {deploy|start|stop|restart|logs|migrate}"
        exit 1
        ;;
esac
