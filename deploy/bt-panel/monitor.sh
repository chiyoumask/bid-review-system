#!/bin/bash
# ============================================================
# 资源监控脚本 - 2核2G 服务器健康检查
# ============================================================

echo "╔══════════════════════════════════════════╗"
echo "║   招投标审核系统 - 服务器资源监控         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# CPU
echo "=== CPU ==="
LOAD=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
CORES=$(nproc)
echo "负载: ${LOAD} (核心数: ${CORES})"
echo ""

# 内存
echo "=== 内存 ==="
free -m | awk '
/^Mem:/ {
    printf "总计: %sMB  已用: %sMB  可用: %sMB\n", $2, $3, $7
    printf "使用率: %.1f%%\n", $3/$2*100
}'
echo ""

# 磁盘
echo "=== 磁盘 ==="
df -h / /www 2>/dev/null | awk '
NR>1 {
    printf "%s  总计:%s  已用:%s  使用率:%s\n", $6, $2, $3, $5
}'
echo ""

# 后端服务
echo "=== 服务状态 ==="
PID_FILE="/www/bid-review-system/backend.pid"
if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
    PID=$(cat "$PID_FILE")
    MEM=$(ps -o rss= -p "$PID" 2>/dev/null | awk '{printf "%.1f", $1/1024}')
    echo "✅ 后端服务: 运行中 (PID: ${PID}, 内存: ${MEM}MB)"
else
    echo "❌ 后端服务: 未运行"
fi

# API 健康检查
if curl -s --max-time 5 http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "✅ API 接口: 正常"
else
    echo "❌ API 接口: 无响应"
fi

# PostgreSQL
if pg_isready -h 127.0.0.1 -q 2>/dev/null; then
    echo "✅ PostgreSQL: 正常"
else
    echo "❌ PostgreSQL: 异常"
fi

# Nginx
if curl -s --max-time 5 http://127.0.0.1 > /dev/null 2>&1; then
    echo "✅ Nginx: 正常"
else
    echo "❌ Nginx: 异常"
fi

echo ""
echo "=== 活跃连接 ==="
ss -tnp | grep -E ':(8000|80|5432)' 2>/dev/null | wc -l | xargs -I {} echo "Web 相关连接数: {}"
echo ""
echo "=== 时间 ==="
date '+%Y-%m-%d %H:%M:%S'
