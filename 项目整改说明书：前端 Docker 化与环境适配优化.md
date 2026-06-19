项目整改说明书：前端 Docker 化与环境适配优化
一、 项目背景与当前状态

项目架构：前后端分离。后端使用 Python FastAPI，前端使用 Vue3，数据库使用 PostgreSQL。

部署环境：目标是在 2核2G 的 VPS 上，使用宝塔面板的 Docker Compose 容器编排进行一键部署。

当前痛点：

前端未容器化：当前的 docker-compose.yml 中，前端服务 frontend 依赖挂载宿主机的 ./frontend/dist 文件夹运行 Nginx。但由于 .gitignore 排除了 dist，导致 Git 仓库中没有打包后的产物。在全新环境（如 VPS）拉取代码后直接运行 docker-compose up 时，由于找不到 dist，Nginx 会启动失败或报 403 错误。

健康检查隐患：后端 backend 的 Dockerfile 构建出的镜像如果过于精简，可能缺失 curl 命令，导致 docker-compose.yml 中依赖 curl 的后端 healthcheck 永远失败。这会引发级联错误：等待后端的 frontend 容器将永远卡在 Created 状态无法启动。

开发与生产环境配置差异：项目根目录的 .env.example 尚未完全针对 Docker Compose 的服务发现机制进行适配（如 DATABASE_URL 的主机名）。

二、 整改目标

实现前端的多阶段构建（Multi-stage Build）：通过编写 frontend/Dockerfile，实现“Node 环境拉取代码并打包 -> 纯净 Nginx 环境托管静态文件”，使整个部署流程摆脱对宿主机 Node 环境和手动 npm run build 的依赖。

优化 Docker Compose 配置：适配前端的多阶段构建，并使用更稳健的方法替换依赖 curl 的后端健康检查。

完善环境变量文档：规范 .env.example 模板，使其更贴合容器化部署的实际场景。

三、 核心任务拆解与执行标准

任务 1：创建前端 Dockerfile

位置：在 frontend/ 目录下创建 Dockerfile。

要求：使用多阶段构建。

阶段 1 (Builder)：使用 node:20-alpine，配置淘宝镜像源以加速国内下载（npm config set registry https://registry.npmmirror.com），复制 package.json 等执行 npm install，然后复制源码执行 npm run build。

阶段 2 (Production)：使用 nginx:1.25-alpine，清理默认 html 文件，将第一阶段生成的 /app/dist 目录下的内容复制到 Nginx 的网页托管目录（/usr/share/nginx/html）。设置暴露端口 80，并使用非后台模式启动 Nginx。

任务 2：更新 Nginx 配置文件

位置：检查并修改 ./deploy/nginx-docker.conf。

要求：因为 Vue3 是单页面应用（SPA），必须包含针对 Vue Router history 模式的配置支持。确保 location / 块中包含 try_files $uri $uri/ /index.html;。

任务 3：重构 docker-compose.yml

位置：修改项目根目录的 docker-compose.yml。

要求：

前端服务改造：在 frontend 服务块中，移除原有的 image: nginx:1.25-alpine 和 ./frontend/dist 的 volume 挂载。改为使用 build 指令指向 ./frontend 目录下的 Dockerfile。保留 nginx 配置文件的挂载。

后端健康检查优化：修改 backend 服务的 healthcheck，将原来的 curl 命令替换为 Python 内置库的方式，以避免镜像精简导致的命令缺失。参考命令：python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1。

任务 4：规范 .env.example 模板

位置：修改项目根目录的 .env.example。

要求：

将 DATABASE_URL 的示例主机名从 localhost 更改为 db（与 docker-compose 中的服务名一致）。

增加注释，明确说明在 Docker 环境中，FRONTEND_BIND 应设置为 0.0.0.0，以便宿主机的端口映射能够正常工作。

提供 CORS_ORIGINS 的正确 JSON 数组格式示例。

四、 验证与自测标准
完成以上修改后，本地 AI 需协助确认：

无需在宿主机执行任何 npm 命令。

仅使用 docker-compose up --build -d 即可在干净的环境中成功拉起包括数据库、后端、前端在内的所有服务。

前后端容器状态均为 Up 且 healthy，可通过映射的端口正常访问网页且路由跳转（刷新页面）不报 404。