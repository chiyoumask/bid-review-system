#!/bin/bash
# ============================================================
# 数据库备份脚本（可配合 crontab 定期执行）
# ============================================================

set -e

BACKUP_DIR="/www/backup/bid-review"
DB_NAME="bid_review"
DB_USER="bid_review"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "${BACKUP_DIR}"

# 备份数据库
echo "备份数据库 ${DB_NAME}..."
pg_dump -h 127.0.0.1 -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"

# 备份上传文件
echo "备份上传文件..."
tar czf "${BACKUP_DIR}/uploads_${TIMESTAMP}.tar.gz" -C /www/bid-review-system/data uploads/ 2>/dev/null || true

# 清理旧备份
echo "清理 ${KEEP_DAYS} 天前的备份..."
find "${BACKUP_DIR}" -name "*.gz" -mtime +${KEEP_DAYS} -delete

echo "备份完成: ${BACKUP_DIR}"
ls -lh "${BACKUP_DIR}"/*.gz 2>/dev/null | tail -5
