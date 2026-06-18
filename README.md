# 招投标文件智能审核系统

基于 AI 评分标准驱动的招投标文件智能审核 Web 平台。

## 功能特性

- **评分标准解析**：上传评分标准 PDF，AI 自动提取评分维度、分值和细则
- **投标文件分析**：AI 逐项提取投标文件中与评分标准对应的内容
- **智能评分比对**：AI 对每个评分项进行预估评分和风险判定
- **人工复核**：支持确认、调整、忽略每项 AI 评审结果
- **多 LLM 渠道**：支持 DeepSeek、通义千问、OpenAI 等多种 LLM API
- **项目管理**：完整的项目生命周期管理

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Ant Design Vue |
| 后端 | Python FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL 15 |
| AI | LLM API（DeepSeek / 通义千问 / OpenAI 兼容接口） |
| 部署 | Docker Compose + Nginx |

## 🚀 快速开始（Docker 部署）

### 方式一：VPS 一键部署（推荐）

```bash
# 1. SSH 登录 VPS
ssh root@你的服务器IP

# 2. 克隆项目
cd /www
git clone https://github.com/你的用户名/bid-review-system.git
cd bid-review-system

# 3. 一键部署
chmod +x deploy/docker-deploy.sh
bash deploy/docker-deploy.sh
```

脚本会自动：配置环境变量 → 构建前端 → 构建 Docker 镜像 → 启动所有服务。

### 方式二：手动 Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env
vi .env   # 填入 LLM_API_KEY 等配置

# 2. 构建前端
cd frontend && npm install && npm run build && cd ..

# 3. 启动服务
docker compose up -d

# 4. 查看状态
docker compose ps
docker compose logs -f backend
```

### 方式三：本地开发

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py

# 前端（另一个终端）
cd frontend
npm install
npm run dev
```

## 📁 项目结构

```
bid-review-system/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由（auth, projects, review, settings）
│   │   ├── core/              # 配置、数据库、安全认证
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应 Schema
│   │   ├── services/          # 核心业务（PDF解析、LLM、评分比对）
│   │   └── tasks/             # 异步任务（文档解析、投标分析）
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── api/               # Axios API 客户端
│   │   ├── components/        # 通用组件
│   │   ├── router/            # Vue Router 路由
│   │   ├── stores/            # Pinia 状态管理
│   │   └── views/             # 页面视图
│   └── package.json
├── deploy/                     # 部署配置
│   ├── bt-panel/              # 宝塔面板原生部署脚本
│   ├── docker-deploy.sh       # Docker 一键部署脚本
│   └── nginx-docker.conf      # Nginx 容器配置
├── docker-compose.yml          # Docker Compose 编排
├── .env.example                # 环境变量模板
└── README.md
```

## 🔧 使用流程

1. **创建项目** → 填写项目名称和招标编号
2. **上传评分标准** → AI 自动解析出所有评分项和分值
3. **上传投标文件** → 系统自动解析文本内容
4. **发起审核** → AI 逐项对比评分标准和投标内容
5. **查看结果** → 预估得分、风险分级、逐项分析
6. **人工复核** → 确认/调整/忽略每项结果
7. **完成审核** → 汇总最终得分

## 🐳 Docker 命令速查

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f backend     # 后端日志
docker compose logs -f db          # 数据库日志
docker compose logs -f frontend    # Nginx 日志

# 重启服务
docker compose restart

# 停止所有服务
docker compose down

# 重建并重启（代码更新后）
docker compose up -d --build

# 进入容器调试
docker compose exec backend bash
docker compose exec db psql -U bid_review -d bid_review

# 数据库备份
docker compose exec db pg_dump -U bid_review bid_review > backup.sql

# 数据库恢复
cat backup.sql | docker compose exec -T db psql -U bid_review -d bid_review
```

## 📋 环境变量说明

| 变量 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `SECRET_KEY` | ✅ | JWT 密钥，随机生成 | `openssl rand -hex 32` |
| `DB_PASSWORD` | ✅ | 数据库密码 | 随机强密码 |
| `LLM_API_KEY` | ✅ | LLM API 密钥 | `sk-xxx...` |
| `LLM_BASE_URL` | ✅ | LLM API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | ✅ | 模型名称 | `deepseek-chat` |
| `CORS_ORIGINS` | 可选 | 允许的前端地址 | `["http://IP"]` |

## 📄 License

MIT
