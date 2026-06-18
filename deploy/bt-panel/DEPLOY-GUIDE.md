# 宝塔面板部署指南（2核2G VPS 详细版）

> 本文档提供**逐步手动部署**和**一键脚本部署**两种方式。推荐先了解手动流程，再决定是否使用脚本。

---

## 📋 部署前准备

### 硬件要求
| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 2核 | 2核 |
| 内存 | 2GB | 2GB+ |
| 硬盘 | 20GB SSD | 40GB SSD |
| 带宽 | 1Mbps | 3Mbps |

### 软件要求（通过宝塔安装）
- [x] Nginx（宝塔自带）
- [x] PostgreSQL（软件商店安装）
- [x] Supervisor（软件商店安装，可选）
- [x] Python 项目管理器（软件商店安装，可选）

### 需要准备的信息
1. **LLM API Key** — DeepSeek / 通义千问 / OpenAI 的 API 密钥
2. **域名**（可选）— 如有域名可绑定，否则用 IP 访问
3. **SSH 工具** — 如 Xshell、MobaXterm、PuTTY

---

## 方式一：一键脚本部署（推荐）

### Step 1: 上传项目文件到 VPS

将本地项目目录打包上传：

```bash
# 在本地打包（Windows PowerShell）
cd "E:\02.Work\Temporary files\zhaobiao"
tar -czf bid-review-system.tar.gz bid-review-system/
```

通过宝塔面板的「文件管理」或 SCP 上传到 VPS：

```bash
# 通过 SCP 上传（本地 PowerShell）
scp bid-review-system.tar.gz root@你的VIP:/tmp/
```

### Step 2: 解压项目文件

```bash
# SSH 登录 VPS
ssh root@你的VIP

# 解压到 /www 目录
mkdir -p /www
cd /www
tar -xzf /tmp/bid-review-system.tar.gz
mv bid-review-system bid-review-system  # 确认目录名
```

### Step 3: 编辑配置

```bash
cd /www/bid-review-system/deploy/bt-panel

# 编辑部署脚本，填入你的配置
vi deploy-all.sh
```

**必须修改的配置项：**

```bash
LLM_API_KEY="你的API密钥"       # ← 必填
LLM_BASE_URL="https://api.deepseek.com/v1"  # ← 按你的渠道修改
LLM_MODEL="deepseek-chat"       # ← 按你的渠道修改
DOMAIN=""                        # ← 有域名填域名
ADMIN_USER="admin"               # ← 管理员用户名
ADMIN_EMAIL="your@email.com"    # ← 管理员邮箱
```

### Step 4: 执行部署

```bash
cd /www/bid-review-system/deploy/bt-panel
chmod +x deploy-all.sh
bash deploy-all.sh
```

脚本会自动完成所有步骤，最后输出访问地址和管理员密码。

### Step 5: 访问系统

浏览器打开 `http://你的VIP`，用输出的管理员账号密码登录。

---

## 方式二：手动逐步部署

如果你更想控制每一步，按以下流程操作。

### Step 1: 安装宝塔面板

```bash
# CentOS
yum install -y wget && wget -O install.sh https://download.bt.cn/install/install_6.0.sh && sh install.sh

# Ubuntu
wget -O install.sh https://download.bt.cn/install/install-ubuntu_6.0_en.sh && sudo bash install.sh
```

安装完成后，按终端输出的地址访问宝塔面板。

### Step 2: 通过宝塔安装必要软件

在宝塔面板 → **软件商店** 中安装：

| 软件 | 用途 | 版本建议 |
|------|------|---------|
| Nginx | Web 服务器 + 反向代理 | 1.22+ |
| PostgreSQL | 数据库 | 15.x |
| Python项目管理器 | Python 环境管理 | 最新版 |
| Supervisor | 进程守护 | 最新版 |

### Step 3: 配置 PostgreSQL

```bash
# SSH 登录后执行

# 创建数据库用户和数据库
su - postgres -c "psql -c \"CREATE USER bid_review WITH PASSWORD '你的密码';\""
su - postgres -c "psql -c \"CREATE DATABASE bid_review OWNER bid_review;\""
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE bid_review TO bid_review;\""
```

**优化内存配置**（2G 服务器必须做）：

```bash
# 找到 postgresql.conf
find / -name "postgresql.conf" -path "*/data/*" 2>/dev/null

# 编辑，修改以下参数（约在文件中的位置）:
shared_buffers = 256MB          # 默认可能更大，改小
effective_cache_size = 512MB
work_mem = 4MB
maintenance_work_mem = 64MB     # 默认可能更大
wal_buffers = 8MB
checkpoint_completion_target = 0.9
max_connections = 50            # 默认可能100，改小省内存
```

修改后重启 PostgreSQL。

### Step 4: 部署后端

```bash
cd /www/bid-review-system/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建 .env 配置文件
cp .env.example .env
vi .env  # 按实际情况修改
```

**.env 关键配置：**

```ini
SECRET_KEY=随机生成一个长字符串
DEBUG=false
DATABASE_URL=postgresql+asyncpg://bid_review:你的密码@127.0.0.1:5432/bid_review
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
CORS_ORIGINS=["http://你的IP","http://你的域名"]
```

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# 测试后端能否正常启动
python main.py
# 应该看到: Uvicorn running on http://0.0.0.0:8000
# Ctrl+C 停止测试
```

### Step 5: 配置 Supervisor 进程守护

在宝塔面板 → **软件商店** → 安装 **Supervisor** → 点击 **添加守护进程**：

| 字段 | 值 |
|------|-----|
| 名称 | bid-review-backend |
| 运行目录 | /www/bid-review-system/backend |
| 启动命令 | /www/bid-review-system/backend/venv/bin/gunicorn -c gunicorn_config.py main:app |
| 启动用户 | root |

或者手动创建配置文件：

```bash
# 宝塔 Supervisor 配置
cat > /www/server/panel/vhost/supervisor/bid-review.conf << 'EOF'
[program:bid-review-backend]
command=/www/bid-review-system/backend/venv/bin/gunicorn -c /www/bid-review-system/backend/gunicorn_config.py main:app
directory=/www/bid-review-system/backend
user=root
autostart=true
autorestart=true
startsecs=5
redirect_stderr=true
stdout_logfile=/www/logs/bid-review-backend.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
environment=PATH="/www/bid-review-system/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EOF
```

重启 Supervisor 使配置生效。

### Step 6: 构建前端

```bash
cd /www/bid-review-system/frontend

# 安装 Node.js（如果没有）
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# 安装依赖
npm install --registry=https://registry.npmmirror.com

# 构建
npm run build

# 部署到 Nginx 目录
mkdir -p /www/wwwroot/bid-review
cp -r dist/* /www/wwwroot/bid-review/
chown -R www:www /www/wwwroot/bid-review
```

### Step 7: 配置 Nginx 反向代理

**方式 A：通过宝塔面板配置（推荐）**

1. 宝塔面板 → **网站** → **添加站点**
2. 域名填写：`你的IP` 或 `你的域名`
3. 根目录选择：`/www/wwwroot/bid-review`
4. 创建后，点击站点名 → **反向代理** → 添加反向代理：
   - 代理名称：`api`
   - 目标URL：`http://127.0.0.1:8000`
   - 发送域名：`127.0.0.1`

**方式 B：手动编辑 Nginx 配置**

```bash
# 找到站点配置文件
ls /www/server/panel/vhost/nginx/

# 编辑站点配置，在 server {} 块内添加：
```

```nginx
# 在宝塔生成的站点配置中，找到 server 块，确保包含以下内容：

# SPA 路由
location / {
    root /www/wwwroot/bid-review;
    index index.html;
    try_files $uri $uri/ /index.html;
}

# API 反向代理
location /api/ {
    proxy_pass http://127.0.0.1:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    client_max_body_size 50m;
}
```

修改后重载 Nginx。

### Step 8: 开放防火墙端口

```bash
# 开放 80 端口（HTTP）
# 如果用宝塔，可以在面板 → 安全 → 防火墙 中操作

# 命令行方式
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --reload

# 或者关闭防火墙（不推荐生产环境）
# systemctl stop firewalld
```

同时确保 VPS 服务商的安全组/防火墙已开放 80 端口。

### Step 9: 配置 SSL（推荐）

**方式 A：宝塔面板一键申请**

1. 宝塔面板 → 网站 → 点击站点名 → **SSL**
2. 选择 **Let's Encrypt** → 勾选域名 → 点击申请
3. 开启 **强制 HTTPS**

**方式 B：手动配置**

需要先将域名解析到 VPS IP，然后通过 certbot 申请证书。

### Step 10: 验证部署

```bash
# 检查后端
curl http://127.0.0.1:8000/api/health
# 应返回: {"status":"ok","version":"1.0.0"}

# 检查 Nginx
curl -I http://127.0.0.1
# 应返回 200 OK

# 查看后端日志
tail -f /www/logs/bid-review-backend.log
```

浏览器访问 `http://你的IP`，应该能看到登录页面。

---

## 🔧 日常运维

### 查看服务状态

```bash
bash /www/bid-review-system/deploy/bt-panel/monitor.sh
```

### 重启后端

```bash
# 通过 Supervisor
supervisorctl restart bid-review-backend

# 或通过脚本
bash /www/bid-review-system/stop.sh
bash /www/bid-review-system/start.sh
```

### 查看日志

```bash
# 后端日志
tail -100 /www/logs/bid-review-backend.log

# 实时查看
tail -f /www/logs/bid-review-backend.log
```

### 更新代码

```bash
# 更新后端
bash /www/bid-review-system/deploy/bt-panel/deploy-backend.sh deploy

# 更新前端
bash /www/bid-review-system/deploy/bt-panel/deploy-frontend.sh all
```

### 数据库备份

```bash
# 手动备份
bash /www/bid-review-system/deploy/bt-panel/backup.sh

# 定时备份（每天凌晨3点）
crontab -e
# 添加：
0 3 * * * bash /www/bid-review-system/deploy/bt-panel/backup.sh >> /www/logs/backup.log 2>&1
```

### 卸载/清理

```bash
# 停止服务
bash /www/bid-review-system/stop.sh

# 删除项目
rm -rf /www/bid-review-system

# 删除数据库
su - postgres -c "psql -c 'DROP DATABASE bid_review;'"
su - postgres -c "psql -c 'DROP USER bid_review;'"

# 删除 Nginx 配置
rm -f /www/server/panel/vhost/nginx/bid-review.conf
rm -rf /www/wwwroot/bid-review

# 删除 Supervisor 配置
rm -f /www/server/panel/vhost/supervisor/bid-review.conf
```

---

## ⚠️ 2核2G 资源优化要点

| 优化项 | 默认值 | 建议值 | 原因 |
|--------|--------|--------|------|
| PostgreSQL shared_buffers | 128MB | 256MB | 平衡缓存和可用内存 |
| PostgreSQL max_connections | 100 | 50 | 减少连接开销 |
| Gunicorn workers | 4 | 2 | 匹配 CPU 核心数 |
| Gunicorn timeout | 30s | 120s | LLM 调用耗时长 |
| LLM API timeout | - | 120s | 避免超时 |
| 文件上传限制 | - | 50MB | 标书文件通常较大 |

**不要在 2G 服务器上运行：**
- Docker（额外开销约 200-400MB）
- Elasticsearch（需要 1GB+ 内存）
- Celery + Redis（可以，但 Redis 需要配 maxmemory）

---

## 🐛 常见问题排查

### 后端启动失败
```bash
# 检查 Python 依赖
cd /www/bid-review-system/backend
source venv/bin/activate
python -c "import fastapi; print('FastAPI OK')"

# 检查数据库连接
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def test():
    engine = create_async_engine('postgresql+asyncpg://bid_review:密码@127.0.0.1:5432/bid_review')
    async with engine.connect() as conn:
        print('数据库连接成功')
    await engine.dispose()
asyncio.run(test())
"
```

### 502 Bad Gateway
```bash
# 后端没启动
curl http://127.0.0.1:8000/api/health

# 检查端口
ss -tlnp | grep 8000

# 检查 Nginx 配置
nginx -t
```

### 内存不足 (OOM)
```bash
# 查看内存
free -m

# 查看占用内存最多的进程
ps aux --sort=-%mem | head -10

# 如果 PostgreSQL 占用过多，调小 shared_buffers
```

### 文件上传失败
```bash
# 检查 Nginx 上传限制
grep client_max_body_size /www/server/panel/vhost/nginx/bid-review.conf

# 检查磁盘空间
df -h /www
```

---

*最后更新: 2026-06-18*
