"""
Gunicorn 配置 - 用于生产环境部署
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
# 2核2G服务器，使用 2-3 个 worker
workers = min(2, multiprocessing.cpu_count())
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "bid-review-backend"
