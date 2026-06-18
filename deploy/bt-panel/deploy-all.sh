#!/bin/bash
# ============================================================
# 招投标文件智能审核系统 - 宝塔面板一键部署脚本
# 适用环境：2核2G 轻量VPS + 宝塔面板
# 系统要求：CentOS 7+ / Ubuntu 18+ / Debian 10+
# ============================================================

set -e

# ===== 配置区（按需修改） =====
PROJECT_DIR="/www/bid-review-system"
BACKEND_DIR="${PROJECT_DIR}/backend"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
DATA_DIR="${PROJECT_DIR}/data"
VENV_DIR="${BACKEND_DIR}/venv"
SITE_NAME="bid-review"          # 宝塔站点名
DOMAIN=""                        # 域名（留空则用IP访问）
DB_NAME="bid_review"
DB_USER="bid_review"
DB_PASS=""                       # 留空则自动生成
DB_PORT=5432
BACKEND_PORT=8000
FRONTEND_PORT=80
ADMIN_USER="admin"
ADMIN_PASS=""                    # 留空则自动生成
ADMIN_EMAIL="admin@example.com"
LLM_API_KEY=""                   # 你的 LLM API Key
LLM_BASE_URL="https://api.deepseek.com/v1"
LLM_MODEL="deepseek-chat"

# ===== 颜色输出 =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}========== $1 ==========${NC}"; }

# ===== 自动生成密码 =====
generate_password() {
    openssl rand -base64 16 | tr -d '=/+' | head -c 16
}

if [ -z "$DB_PASS" ]; then
    DB_PASS=$(generate_password)
    log_warn "数据库密码已自动生成: ${DB_PASS}"
fi
if [ -z "$ADMIN_PASS" ]; then
    ADMIN_PASS=$(generate_password)
    log_warn "管理员密码已自动生成: ${ADMIN_PASS}"
fi

# ===== 检查运行环境 =====
check_environment() {
    log_step "Step 0: 环境检查"

    # 检查是否 root
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi

    # 检查系统信息
    OS=$(cat /etc/os-release 2>/dev/null | grep -w "ID" | cut -d= -f2 | tr -d '"')
    MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
    CPU_CORES=$(nproc)

    log_info "操作系统: ${OS}"
    log_info "CPU 核心: ${CPU_CORES}"
    log_info "总内存: ${MEM_TOTAL}MB"

    if [ "$MEM_TOTAL" -lt 1800 ]; then
        log_warn "内存不足 2G，部署后可能运行不稳定"
    fi

    # 检查宝塔
    if command -v bt &>/dev/null || [ -f "/www/server/panel/BT-Panel" ]; then
        log_info "宝塔面板: 已安装"
    else
        log_warn "未检测到宝塔面板，部分功能可能需要手动配置"
    fi

    # 检查必要命令
    for cmd in python3 git curl; do
        if ! command -v $cmd &>/dev/null; then
            log_warn "未找到 ${cmd}，将尝试安装"
        fi
    done
}

# ===== 安装系统依赖 =====
install_system_deps() {
    log_step "Step 1: 安装系统依赖"

    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip python3-venv \
            libpq-dev gcc build-essential \
            git curl wget supervisor
    elif command -v yum &>/dev/null; then
        yum install -y -q python3 python3-pip python3-devel \
            postgresql-devel gcc gcc-c++ make \
            git curl wget supervisor
    fi

    # 确保 python3 可用
    python3 --version
    log_info "系统依赖安装完成"
}

# ===== 安装/配置 PostgreSQL =====
setup_postgresql() {
    log_step "Step 2: 配置 PostgreSQL"

    # 检查 PostgreSQL 是否已运行
    if systemctl is-active --quiet postgresql 2>/dev/null; then
        log_info "PostgreSQL 已运行"
    else
        # 尝试启动
        systemctl start postgresql 2>/dev/null || true
    fi

    # 如果宝塔安装了 PostgreSQL，使用宝塔的
    if [ -d "/www/server/pgsql" ]; then
        PG_BIN="/www/server/pgsql/bin"
        PG_DATA="/www/server/pgsql/data"
        export PATH="${PG_BIN}:${PATH}"
        log_info "使用宝塔 PostgreSQL"
    elif command -v psql &>/dev/null; then
        PG_BIN=$(dirname $(which psql))
        log_info "使用系统 PostgreSQL"
    else
        log_warn "PostgreSQL 未安装，请通过宝塔面板安装"
        log_warn "宝塔面板 → 软件商店 → PostgreSQL → 安装"
        log_warn "安装完成后重新运行此脚本"
        return 1
    fi

    # 创建数据库和用户
    su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\"" 2>/dev/null || true
    su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\"" 2>/dev/null || true
    su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\"" 2>/dev/null || true

    # 优化 PostgreSQL 内存配置（适配 2G 内存）
    PG_HBA=$(find / -name "pg_hba.conf" -path "*/data/*" 2>/dev/null | head -1)
    PG_CONF=$(find / -name "postgresql.conf" -path "*/data/*" 2>/dev/null | head -1)

    if [ -n "$PG_CONF" ]; then
        log_info "优化 PostgreSQL 内存配置..."
        # 2G 服务器，分配 256MB 给 PG
        sed -i "s/#shared_buffers =.*/shared_buffers = 256MB/" "$PG_CONF" 2>/dev/null || true
        sed -i "s/shared_buffers =.*/shared_buffers = 256MB/" "$PG_CONF" 2>/dev/null || true
        sed -i "s/#effective_cache_size =.*/effective_cache_size = 512MB/" "$PG_CONF" 2>/dev/null || true
        sed -i "s/effective_cache_size =.*/effective_cache_size = 512MB/" "$PG_CONF" 2>/dev/null || true
        sed -i "s/#work_mem =.*/work_mem = 4MB/" "$PG_CONF" 2>/dev/null || true
        sed -i "s/work_mem =.*/work_mem = 4MB/" "$PG_CONF" 2>/dev/null || true

        # 允许本地密码认证
        if [ -n "$PG_HBA" ]; then
            sed -i 's/local.*all.*all.*peer/local   all             all                                     md5/' "$PG_HBA" 2>/dev/null || true
        fi

        systemctl restart postgresql 2>/dev/null || true
        log_info "PostgreSQL 内存优化完成"
    fi

    log_info "数据库配置完成: ${DB_NAME}"
}

# ===== 部署后端 =====
deploy_backend() {
    log_step "Step 3: 部署后端"

    mkdir -p "${BACKEND_DIR}"

    # 如果是从 git 克隆的项目，假设代码已在 PROJECT_DIR
    if [ ! -f "${BACKEND_DIR}/main.py" ]; then
        log_error "未找到后端代码: ${BACKEND_DIR}/main.py"
        log_warn "请先将项目文件上传到 ${PROJECT_DIR}"
        return 1
    fi

    cd "${BACKEND_DIR}"

    # 创建 Python 虚拟环境（2G 内存要精简）
    log_info "创建 Python 虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate

    # 升级 pip
    pip install --upgrade pip -q

    # 安装依赖
    log_info "安装 Python 依赖（这可能需要几分钟）..."
    pip install -r requirements.txt -q

    # 创建 .env 配置文件
    log_info "生成配置文件..."
    cat > .env << EOF
# ===== 招投标文件智能审核系统 - 生产环境配置 =====

# 安全密钥（已自动生成）
SECRET_KEY=$(openssl rand -hex 32)

# 调试模式（生产环境关闭）
DEBUG=false

# 数据库连接
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@127.0.0.1:${DB_PORT}/${DB_NAME}

# LLM API 配置
LLM_API_KEY=${LLM_API_KEY}
LLM_BASE_URL=${LLM_BASE_URL}
LLM_MODEL=${LLM_MODEL}
LLM_TIMEOUT=120

# CORS（允许前端域名）
CORS_ORIGINS=["http://127.0.0.1","http://localhost:8080"${DOMAIN:+,"https://${DOMAIN}"}]

# 文件上传
MAX_FILE_SIZE_MB=50
EOF

    # 创建数据目录
    mkdir -p "${DATA_DIR}/uploads" "${DATA_DIR}/outputs"

    # 初始化数据库表
    log_info "初始化数据库..."
    python -c "
import asyncio
from app.core.database import engine, Base
from app.models import *
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
asyncio.run(init())
" 2>/dev/null || log_warn "数据库初始化将在首次启动时自动执行"

    # 创建默认管理员账号
    log_info "创建默认管理员账号..."
    python -c "
import asyncio
from app.core.database import async_session
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy import select

async def create_admin():
    async with async_session() as db:
        result = await db.execute(select(User).where(User.username == '${ADMIN_USER}'))
        if not result.scalar_one_or_none():
            admin = User(
                username='${ADMIN_USER}',
                email='${ADMIN_EMAIL}',
                hashed_password=hash_password('${ADMIN_PASS}'),
                display_name='管理员',
                role='admin',
            )
            db.add(admin)
            await db.commit()
            print('Admin created successfully')
        else:
            print('Admin already exists')

asyncio.run(create_admin())
" 2>/dev/null || log_warn "管理员账号将在首次启动时创建"

    deactivate
    log_info "后端部署完成"
}

# ===== 部署前端 =====
deploy_frontend() {
    log_step "Step 4: 构建前端"

    cd "${FRONTEND_DIR}"

    if [ ! -f "package.json" ]; then
        log_error "未找到前端代码: ${FRONTEND_DIR}/package.json"
        return 1
    fi

    # 检查 node
    if ! command -v node &>/dev/null; then
        log_info "安装 Node.js..."
        if command -v apt-get &>/dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y -qq nodejs
        elif command -v yum &>/dev/null; then
            curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
            yum install -y -q nodejs
        fi
    fi

    log_info "Node.js: $(node --version)"
    log_info "npm: $(npm --version)"

    # 安装依赖
    log_info "安装前端依赖..."
    npm install --production=false

    # 构建
    log_info "构建前端..."
    npm run build

    # 将构建产物复制到 Nginx 目录
    log_info "部署前端静态文件..."
    BT_HTML="/www/wwwroot/${SITE_NAME}"
    mkdir -p "${BT_HTML}"
    cp -r dist/* "${BT_HTML}/"

    log_info "前端构建完成: ${BT_HTML}"
}

# ===== 配置 Nginx =====
configure_nginx() {
    log_step "Step 5: 配置 Nginx"

    NGINX_CONF="/www/server/panel/vhost/nginx/${SITE_NAME}.conf"

    # 也写一份到项目目录做备份
    mkdir -p "${PROJECT_DIR}/deploy"
    cat > "${PROJECT_DIR}/deploy/nginx-bt.conf" << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 前端静态文件
    root /www/wwwroot/bid-review;
    index index.html;

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_connect_timeout 10s;

        # 文件上传大小限制
        client_max_body_size 50m;
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1024;
}
NGINX_EOF

    # 如果宝塔 Nginx 配置目录存在，直接写入
    if [ -d "/www/server/panel/vhost/nginx" ]; then
        cp "${PROJECT_DIR}/deploy/nginx-bt.conf" "${NGINX_CONF}"
        # 替换域名
        if [ -n "$DOMAIN" ]; then
            sed -i "s/server_name _;/server_name ${DOMAIN};/" "${NGINX_CONF}"
        fi
        # 重载 Nginx
        nginx -s reload 2>/dev/null || systemctl reload nginx 2>/dev/null || true
        log_info "Nginx 配置已写入: ${NGINX_CONF}"
    else
        log_warn "未找到宝塔 Nginx 配置目录"
        log_info "Nginx 配置已保存到: ${PROJECT_DIR}/deploy/nginx-bt.conf"
        log_warn "请手动将此配置添加到 Nginx"
    fi
}

# ===== 配置 Supervisor 进程守护 =====
configure_supervisor() {
    log_step "Step 6: 配置进程守护"

    SUPERVISOR_CONF="/www/server/panel/vhost/supervisor/${SITE_NAME}.conf"

    cat > "${PROJECT_DIR}/deploy/supervisord.conf" << SUPER_EOF
[program:bid-review-backend]
command=${VENV_DIR}/bin/gunicorn -c ${BACKEND_DIR}/gunicorn_config.py main:app
directory=${BACKEND_DIR}
user=root
autostart=true
autorestart=true
startsecs=10
startretries=3
stopwaitsecs=10
redirect_stderr=true
stdout_logfile=/www/logs/${SITE_NAME}-backend.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
environment=PATH="${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
SUPER_EOF

    # 宝塔 Supervisor 目录
    if [ -d "/www/server/panel/vhost/supervisor" ]; then
        cp "${PROJECT_DIR}/deploy/supervisord.conf" "${SUPERVISOR_CONF}"
        log_info "Supervisor 配置已写入: ${SUPERVISOR_CONF}"
    else
        # 使用系统 supervisor
        if command -v supervisorctl &>/dev/null; then
            cp "${PROJECT_DIR}/deploy/supervisord.conf" "/etc/supervisor/conf.d/${SITE_NAME}.conf" 2>/dev/null || \
            cp "${PROJECT_DIR}/deploy/supervisord.conf" "/etc/supervisord.d/${SITE_NAME}.ini" 2>/dev/null || true
            supervisorctl reread 2>/dev/null || true
            supervisorctl update 2>/dev/null || true
            log_info "Supervisor 配置已写入系统 supervisor"
        else
            log_warn "Supervisor 未安装，请通过宝塔面板安装"
            log_info "配置文件已保存到: ${PROJECT_DIR}/deploy/supervisord.conf"
        fi
    fi

    # 创建日志目录
    mkdir -p /www/logs
}

# ===== 创建启动/停止脚本 =====
create_scripts() {
    log_step "Step 7: 创建管理脚本"

    # 启动脚本
    cat > "${PROJECT_DIR}/start.sh" << 'START_EOF'
#!/bin/bash
# 启动后端服务
cd /www/bid-review-system/backend
source venv/bin/activate
echo "启动招投标审核系统后端..."
gunicorn -c gunicorn_config.py main:app &
echo $! > /www/bid-review-system/backend.pid
deactivate
echo "后端已启动 (PID: $(cat /www/bid-review-system/backend.pid))"
START_EOF

    # 停止脚本
    cat > "${PROJECT_DIR}/stop.sh" << 'STOP_EOF'
#!/bin/bash
# 停止后端服务
PID_FILE="/www/bid-review-system/backend.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "后端服务已停止 (PID: $PID)"
    else
        echo "进程已不存在"
    fi
    rm -f "$PID_FILE"
else
    echo "未找到 PID 文件，尝试通过端口查找..."
    PID=$(lsof -ti:8000 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID"
        echo "已停止进程 $PID"
    fi
fi
STOP_EOF

    # 状态检查脚本
    cat > "${PROJECT_DIR}/status.sh" << 'STATUS_EOF'
#!/bin/bash
echo "===== 招投标审核系统状态 ====="
echo ""

# 检查后端进程
PID_FILE="/www/bid-review-system/backend.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
    echo "✅ 后端服务: 运行中 (PID: $(cat $PID_FILE))"
else
    echo "❌ 后端服务: 未运行"
fi

# 检查端口
if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "✅ API 接口: 正常响应"
else
    echo "❌ API 接口: 无响应"
fi

# 检查数据库
if pg_isready -h 127.0.0.1 > /dev/null 2>&1; then
    echo "✅ 数据库: 连接正常"
else
    echo "❌ 数据库: 连接失败"
fi

# 检查磁盘
DISK_USAGE=$(df -h /www | awk 'NR==2{print $5}' | tr -d '%')
echo "📊 磁盘使用: ${DISK_USAGE}%"

# 检查内存
MEM_USAGE=$(free | awk '/^Mem:/{printf "%.0f", $3/$2*100}')
echo "📊 内存使用: ${MEM_USAGE}%"
STATUS_EOF

    chmod +x "${PROJECT_DIR}/start.sh" "${PROJECT_DIR}/stop.sh" "${PROJECT_DIR}/status.sh"
    log_info "管理脚本已创建"
}

# ===== 输出部署信息 =====
print_summary() {
    log_step "🎉 部署完成！"

    # 获取公网 IP
    PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "YOUR_IP")

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  招投标文件智能审核系统 - 部署信息${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "  访问地址:  ${CYAN}http://${DOMAIN:-$PUBLIC_IP}${NC}"
    echo ""
    echo -e "  管理员账号: ${YELLOW}${ADMIN_USER}${NC}"
    echo -e "  管理员密码: ${YELLOW}${ADMIN_PASS}${NC}"
    echo ""
    echo -e "  数据库名:  ${DB_NAME}"
    echo -e "  数据库用户: ${DB_USER}"
    echo -e "  数据库密码: ${YELLOW}${DB_PASS}${NC}"
    echo ""
    echo -e "  项目目录:  ${PROJECT_DIR}"
    echo -e "  后端端口:  ${BACKEND_PORT}"
    echo -e "  Nginx 站点: ${SITE_NAME}"
    echo ""
    echo -e "${RED}  ⚠️  请妥善保存以上密码信息！${NC}"
    echo ""
    echo -e "  管理命令:"
    echo -e "    启动: ${PROJECT_DIR}/start.sh"
    echo -e "    停止: ${PROJECT_DIR}/stop.sh"
    echo -e "    状态: ${PROJECT_DIR}/status.sh"
    echo ""

    # 保存部署信息
    cat > "${PROJECT_DIR}/deploy-info.txt" << EOF
部署时间: $(date '+%Y-%m-%d %H:%M:%S')
访问地址: http://${DOMAIN:-$PUBLIC_IP}
管理员账号: ${ADMIN_USER}
管理员密码: ${ADMIN_PASS}
数据库名: ${DB_NAME}
数据库用户: ${DB_USER}
数据库密码: ${DB_PASS}
项目目录: ${PROJECT_DIR}
EOF
    chmod 600 "${PROJECT_DIR}/deploy-info.txt"
    log_info "部署信息已保存到: ${PROJECT_DIR}/deploy-info.txt"
}

# ===== 主流程 =====
main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  招投标文件智能审核系统 - 宝塔面板部署脚本       ║"
    echo "║  适用: 2核2G 轻量VPS                            ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_environment
    install_system_deps
    setup_postgresql
    deploy_backend
    deploy_frontend
    configure_nginx
    configure_supervisor
    create_scripts
    print_summary
}

# 运行
main "$@"
