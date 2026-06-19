#!/bin/bash
# ============================================================
# Docker 一键部署脚本
# 在安装了宝塔面板的 VPS 上执行
# ============================================================

set -e

PROJECT_DIR="/www/bid-review-system"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}── $1 ──${NC}"; }

# 生成随机密码
gen_pass() { openssl rand -base64 18 | tr -d '=/+' | head -c 20; }

# ===== 检查环境 =====
log_step "检查环境"

# Docker
if ! command -v docker &>/dev/null; then
    log_error "Docker 未安装"
    echo "  请先安装 Docker："
    echo "  宝塔面板 → 软件商店 → Docker管理器 → 安装"
    echo "  或手动安装：curl -fsSL https://get.docker.com | sh"
    exit 1
fi
log_info "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# Docker Compose
if ! docker compose version &>/dev/null && ! docker-compose --version &>/dev/null; then
    log_error "Docker Compose 未安装"
    exit 1
fi
log_info "Docker Compose 已就绪"

# 内存
MEM=$(free -m | awk '/^Mem:/{print $2}')
log_info "服务器内存: ${MEM}MB"

# ===== 准备项目 =====
log_step "准备项目文件"

if [ ! -d "${PROJECT_DIR}" ]; then
    log_warn "项目目录不存在，尝试克隆..."
    mkdir -p /www
    cd /www

    # 如果有 GitHub 仓库地址，在这里填入
    REPO_URL="${1:-}"
    if [ -z "$REPO_URL" ]; then
        log_error "请提供 GitHub 仓库地址"
        echo "  用法: bash $0 https://github.com/用户名/仓库名.git"
        exit 1
    fi

    git clone "$REPO_URL" bid-review-system
    cd bid-review-system
else
    cd "${PROJECT_DIR}"
    # 如果是 git 仓库，拉取最新
    if [ -d ".git" ]; then
        log_info "拉取最新代码..."
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true
    fi
fi

# ===== 配置环境变量 =====
log_step "配置环境变量"

if [ ! -f ".env" ]; then
    cp .env.example .env

    # 自动生成安全配置
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASS=$(gen_pass)

    sed -i "s|please-change-me-to-random-string|${SECRET_KEY}|" .env
    sed -i "s|please-change-me-to-strong-password|${DB_PASS}|" .env

    # 获取公网 IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")
    sed -i "s|http://your-server-ip|http://${PUBLIC_IP}|" .env

    log_info ".env 已生成（已自动填充密钥和数据库密码）"
    log_warn "请手动编辑 .env 填入 LLM_API_KEY"
    echo ""
    echo -e "  编辑命令: ${YELLOW}vi ${PROJECT_DIR}/.env${NC}"
    echo ""
    read -p "是否现在编辑 .env？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        vi .env
    fi
else
    log_info ".env 已存在，跳过生成"
fi

# ===== 构建前端 =====
log_step "构建前端"

if [ -d "frontend" ]; then
    log_info "构建前端..."
    cd frontend

    if ! command -v node &>/dev/null; then
        log_info "安装 Node.js..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - 2>/dev/null || true
        yum install -y nodejs 2>/dev/null || apt-get install -y nodejs 2>/dev/null || true
    fi

    npm install --registry=https://registry.npmmirror.com
    npm run build
    cd ..
    log_info "前端构建完成"
else
    log_warn "未找到前端目录，跳过"
fi

# ===== 启动 Docker 容器 =====
log_step "启动 Docker 容器"

# 停止旧容器
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

# 构建并启动
log_info "构建后端镜像..."
docker compose build --no-cache backend 2>/dev/null || docker-compose build --no-cache backend

log_info "启动所有服务..."
docker compose up -d 2>/dev/null || docker-compose up -d

# 等待启动
log_info "等待服务启动..."
sleep 10

# ===== 验证 =====
log_step "验证部署"

FRONTEND_HTTP_PORT=$(grep -E '^FRONTEND_HTTP_PORT=' .env | tail -n1 | cut -d= -f2 || true)
FRONTEND_BIND=$(grep -E '^FRONTEND_BIND=' .env | tail -n1 | cut -d= -f2 || true)
FRONTEND_HTTP_PORT=${FRONTEND_HTTP_PORT:-8080}
FRONTEND_BIND=${FRONTEND_BIND:-127.0.0.1}

# 检查容器状态
echo ""
docker compose ps 2>/dev/null || docker-compose ps

# 检查 API
if curl -s http://127.0.0.1:8000/api/health | grep -q "ok"; then
    log_info "API 接口: 正常"
else
    log_warn "API 接口: 可能还在启动中，稍等几秒再试"
fi

# 检查 Nginx
if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${FRONTEND_HTTP_PORT}" | grep -q "200"; then
    log_info "Nginx: 正常"
else
    log_warn "Nginx: 可能还在启动中"
fi

# ===== 输出结果 =====
log_step "🎉 部署完成"

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_IP")
DB_PASS=$(grep DB_PASSWORD .env | cut -d= -f2)

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     招投标文件智能审核系统 - Docker 部署完成      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
if [ "${FRONTEND_BIND}" = "127.0.0.1" ]; then
    echo -e "  宝塔反代目标: ${CYAN}http://127.0.0.1:${FRONTEND_HTTP_PORT}${NC}"
    echo -e "  公开访问地址: ${YELLOW}请在宝塔站点中绑定域名并反向代理到上方地址${NC}"
else
    echo -e "  访问地址:    ${CYAN}http://${PUBLIC_IP}:${FRONTEND_HTTP_PORT}${NC}"
fi
echo ""
echo -e "  管理员账号:  ${YELLOW}admin${NC}（首次登录时注册）"
echo -e "  数据库密码:  ${YELLOW}${DB_PASS}${NC}"
echo ""
echo -e "  项目目录:    ${PROJECT_DIR}"
echo ""
echo -e "  常用命令:"
echo -e "    查看状态:  ${YELLOW}docker compose ps${NC}"
echo -e "    查看日志:  ${YELLOW}docker compose logs -f backend${NC}"
echo -e "    重启服务:  ${YELLOW}docker compose restart${NC}"
echo -e "    停止服务:  ${YELLOW}docker compose down${NC}"
echo -e "    更新部署:  ${YELLOW}bash $0${NC}"
echo ""
echo -e "  ${RED}⚠️  请确保 .env 中的 LLM_API_KEY 已正确填写！${NC}"
echo ""

# 保存部署信息
cat > "${PROJECT_DIR}/deploy-info.txt" << EOF
部署时间: $(date '+%Y-%m-%d %H:%M:%S')
宝塔反代目标: http://127.0.0.1:${FRONTEND_HTTP_PORT}
数据库密码: ${DB_PASS}
部署方式: Docker Compose
项目目录: ${PROJECT_DIR}
EOF
chmod 600 "${PROJECT_DIR}/deploy-info.txt"
