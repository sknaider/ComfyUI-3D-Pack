#!/bin/bash
# Log rotation script for ComfyUI-3D-Pack
# Usage: ./scripts/rotate-logs.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${LOG_DIR:-$PROJECT_ROOT/logs}"
MAX_AGE_DAYS="${LOG_RETENTION_DAYS:-7}"
MAX_SIZE_MB="${LOG_MAX_SIZE_MB:-100}"
ARCHIVE_DIR="$LOG_DIR/archive"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}ComfyUI-3D-Pack Log Rotation${NC}"
echo "Log directory: $LOG_DIR"
echo "Max age: $MAX_AGE_DAYS days"
echo "Max size: $MAX_SIZE_MB MB"
echo ""

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Function to rotate log file
rotate_log() {
    local log_file="$1"
    local basename=$(basename "$log_file")
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local archived_file="$ARCHIVE_DIR/${basename}.${timestamp}.gz"

    echo -e "${YELLOW}Rotating: $basename${NC}"

    # Compress and archive
    gzip -c "$log_file" > "$archived_file"

    # Truncate original file
    > "$log_file"

    echo -e "${GREEN}✓ Archived to: $archived_file${NC}"
}

# Function to check file size
check_size() {
    local file="$1"
    local size_mb=$(du -m "$file" | cut -f1)

    if [ "$size_mb" -gt "$MAX_SIZE_MB" ]; then
        return 0  # File is too large
    else
        return 1  # File size is okay
    fi
}

# Rotate logs by size
if [ -d "$LOG_DIR" ]; then
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            if check_size "$log_file"; then
                rotate_log "$log_file"
            fi
        fi
    done
fi

# Delete old archived logs
echo ""
echo -e "${YELLOW}Cleaning up old logs...${NC}"
find "$ARCHIVE_DIR" -name "*.gz" -mtime +$MAX_AGE_DAYS -delete

# Show summary
echo ""
echo -e "${GREEN}Log rotation complete!${NC}"
echo ""
echo "Current logs:"
ls -lh "$LOG_DIR"/*.log 2>/dev/null || echo "No active logs"
echo ""
echo "Archived logs:"
ls -lh "$ARCHIVE_DIR"/*.gz 2>/dev/null | tail -10 || echo "No archived logs"

exit 0
