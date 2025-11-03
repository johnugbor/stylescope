#!/bin/bash

# Backup script for PostgreSQL to S3
# Usage: ./backup.sh

BACKUP_DIR="/tmp/db_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="stylescope_backup_${TIMESTAMP}.sql.gz"
S3_BUCKET="stylescope-bucket"

# Get the directory where this script is located (same as docker-compose.yml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database using docker-compose
echo "Starting backup at $(date)"
cd $COMPOSE_DIR
docker-compose exec -T db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}"

# Keep only last 7 days locally
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}"

# Optional: Keep only last 30 backups in S3
# aws s3 ls s3://${S3_BUCKET}/backups/ | sort | head -n -30 | awk '{print $4}' | xargs -I {} aws s3 rm s3://${S3_BUCKET}/backups/{}