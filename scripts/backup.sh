#!/bin/bash
# Automated backup script for ComfyUI-3D-Pack
# Usage: ./scripts/backup.sh [models|output|all] [destination]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_TYPE="${1:-all}"
DESTINATION="${2:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="comfyui-3d-pack-${BACKUP_TYPE}-${TIMESTAMP}"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-backups}"

echo -e "${GREEN}ComfyUI-3D-Pack Backup Script${NC}"
echo "Backup type: $BACKUP_TYPE"
echo "Destination: $DESTINATION"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create destination directory
mkdir -p "$DESTINATION"

# Function to backup directory
backup_directory() {
    local dir="$1"
    local name="$2"

    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}Warning: Directory $dir does not exist, skipping${NC}"
        return 0
    fi

    echo -e "${GREEN}Backing up $name...${NC}"

    local backup_file="$DESTINATION/${BACKUP_NAME}-${name}.tar.gz"

    # Create compressed archive
    tar -czf "$backup_file" -C "$(dirname "$dir")" "$(basename "$dir")" 2>/dev/null || {
        echo -e "${RED}Error: Failed to create backup for $name${NC}"
        return 1
    }

    local size=$(du -h "$backup_file" | cut -f1)
    echo -e "${GREEN}✓ Created backup: $backup_file (Size: $size)${NC}"

    # Upload to S3 if configured
    if [ -n "$S3_BUCKET" ]; then
        upload_to_s3 "$backup_file" "$name"
    fi
}

# Function to upload to S3
upload_to_s3() {
    local file="$1"
    local name="$2"

    echo -e "${YELLOW}Uploading to S3...${NC}"

    if command -v aws &> /dev/null; then
        aws s3 cp "$file" "s3://${S3_BUCKET}/${S3_PREFIX}/$(basename "$file")" || {
            echo -e "${RED}Failed to upload to S3${NC}"
            return 1
        }
        echo -e "${GREEN}✓ Uploaded to S3: s3://${S3_BUCKET}/${S3_PREFIX}/$(basename "$file")${NC}"
    else
        echo -e "${YELLOW}AWS CLI not installed, skipping S3 upload${NC}"
    fi
}

# Function to backup database (if using PostgreSQL)
backup_database() {
    echo -e "${GREEN}Backing up database...${NC}"

    if [ -n "$DATABASE_URL" ]; then
        local backup_file="$DESTINATION/${BACKUP_NAME}-database.sql.gz"

        pg_dump "$DATABASE_URL" | gzip > "$backup_file" || {
            echo -e "${RED}Failed to backup database${NC}"
            return 1
        }

        echo -e "${GREEN}✓ Database backup created: $backup_file${NC}"

        if [ -n "$S3_BUCKET" ]; then
            upload_to_s3 "$backup_file" "database"
        fi
    else
        echo -e "${YELLOW}No database configured, skipping${NC}"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    local keep_days="${BACKUP_RETENTION_DAYS:-7}"

    echo -e "${YELLOW}Cleaning up backups older than $keep_days days...${NC}"

    find "$DESTINATION" -name "comfyui-3d-pack-*.tar.gz" -mtime +$keep_days -delete

    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main backup logic
case "$BACKUP_TYPE" in
    models)
        backup_directory "$PROJECT_ROOT/models" "models"
        ;;
    output)
        backup_directory "$PROJECT_ROOT/output" "output"
        ;;
    config)
        backup_directory "$PROJECT_ROOT/Configs" "config"
        backup_directory "$PROJECT_ROOT/.env" "env" 2>/dev/null || true
        ;;
    database)
        backup_database
        ;;
    all)
        backup_directory "$PROJECT_ROOT/models" "models"
        backup_directory "$PROJECT_ROOT/output" "output"
        backup_directory "$PROJECT_ROOT/Configs" "config"
        backup_database
        ;;
    *)
        echo -e "${RED}Error: Invalid backup type: $BACKUP_TYPE${NC}"
        echo "Usage: $0 [models|output|config|database|all] [destination]"
        exit 1
        ;;
esac

# Cleanup old backups
cleanup_old_backups

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Backup location: $DESTINATION"
echo "Backup name: $BACKUP_NAME"

if [ -n "$S3_BUCKET" ]; then
    echo "S3 location: s3://${S3_BUCKET}/${S3_PREFIX}/"
fi

# List backups
echo ""
echo "Recent backups:"
ls -lh "$DESTINATION" | grep comfyui-3d-pack | tail -5

exit 0
