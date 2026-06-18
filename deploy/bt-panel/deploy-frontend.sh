#!/bin/bash
# ============================================================
# 前端单独构建/部署脚本
# ============================================================

set -e

PROJECT_DIR="/www/bid-review-system"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
SITE_NAME="bid-review"
BT_HTML="/www/wwwroot/${SITE_NAME}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }

build_frontend() {
    log_info "构建前端..."
    cd "${FRONTEND_DIR}"

    # 检查 node
    if ! command -v node &>/dev/null; then
        log_warn "Node.js 未安装，尝试安装..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
        yum install -y nodejs
    fi

    log_info "Node.js $(node --version)"

    # 安装依赖（使用镜像加速）
    if [ ! -d "node_modules" ]; then
        log_info "安装依赖..."
        npm install --registry=https://registry.npmmirror.com
    fi

    # 构建
    log_info "构建生产版本..."
    npm run build

    log_info "构建完成"
}

deploy_frontend() {
    log_info "部署前端静态文件..."

    # 创建站点目录
    mkdir -p "${BT_HTML}"

    # 清理旧文件
    rm -rf "${BT_HTML:?}"/*

    # 复制新文件
    cp -r "${FRONTEND_DIR}/dist/"* "${BT_HTML}/"

    # 设置权限
    chown -R www:www "${BT_HTML}" 2>/dev/null || true
    chmod -R 755 "${BT_HTML}"

    # 重载 Nginx
    nginx -s reload 2>/dev/null || systemctl reload nginx 2>/dev/null || true

    log_info "前端部署完成: ${BT_HTML}"
}

case "${1:-all}" in
    build)
        build_frontend
        ;;
    deploy)
        deploy_frontend
        ;;
    all)
        build_frontend
        deploy_frontend
        ;;
    *)
        echo "用法: $0 {build|deploy|all}"
        exit 1
        ;;
esac
