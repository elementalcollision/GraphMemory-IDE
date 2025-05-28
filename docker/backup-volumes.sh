#!/bin/bash

# GraphMemory-IDE Volume Backup Script
# Based on Docker best practices for persistent volume management

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}GraphMemory-IDE Volume Backup Tool${NC}"
echo "Backup directory: $BACKUP_DIR"
echo "Timestamp: $TIMESTAMP"
echo

# Function to backup a volume
backup_volume() {
    local volume_name=$1
    local backup_file="$BACKUP_DIR/${volume_name}_${TIMESTAMP}.tar.gz"
    
    echo -e "${YELLOW}Backing up volume: $volume_name${NC}"
    
    # Check if volume exists
    if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
        echo -e "${RED}Error: Volume $volume_name does not exist${NC}"
        return 1
    fi
    
    # Create backup
    docker run --rm \
        -v "$volume_name":/data \
        -v "$(pwd)/$BACKUP_DIR":/backup \
        alpine tar czf "/backup/$(basename "$backup_file")" -C /data .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully backed up $volume_name to $backup_file${NC}"
        
        # Show backup size
        local size=$(du -h "$backup_file" | cut -f1)
        echo "  Backup size: $size"
    else
        echo -e "${RED}✗ Failed to backup $volume_name${NC}"
        return 1
    fi
    echo
}

# Function to restore a volume
restore_volume() {
    local volume_name=$1
    local backup_file=$2
    
    echo -e "${YELLOW}Restoring volume: $volume_name from $backup_file${NC}"
    
    # Check if backup file exists
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file $backup_file does not exist${NC}"
        return 1
    fi
    
    # Warning about data loss
    echo -e "${RED}WARNING: This will overwrite all data in volume $volume_name${NC}"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Restore cancelled"
        return 0
    fi
    
    # Create volume if it doesn't exist
    docker volume create "$volume_name" >/dev/null 2>&1 || true
    
    # Restore backup
    docker run --rm \
        -v "$volume_name":/data \
        -v "$(pwd)/$(dirname "$backup_file")":/backup \
        alpine sh -c "rm -rf /data/* /data/..?* /data/.[!.]* 2>/dev/null || true && tar xzf /backup/$(basename "$backup_file") -C /data"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully restored $volume_name from $backup_file${NC}"
    else
        echo -e "${RED}✗ Failed to restore $volume_name${NC}"
        return 1
    fi
    echo
}

# Function to list backups
list_backups() {
    echo -e "${YELLOW}Available backups:${NC}"
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A "$BACKUP_DIR"/*.tar.gz 2>/dev/null)" ]; then
        ls -lh "$BACKUP_DIR"/*.tar.gz | awk '{print $9, "(" $5 ")", $6, $7, $8}'
    else
        echo "No backups found in $BACKUP_DIR"
    fi
    echo
}

# Function to clean old backups
clean_backups() {
    local days=${1:-7}
    echo -e "${YELLOW}Cleaning backups older than $days days...${NC}"
    
    find "$BACKUP_DIR" -name "*.tar.gz" -type f -mtime +$days -delete
    
    echo -e "${GREEN}✓ Cleanup completed${NC}"
    echo
}

# Function to show volume info
show_volume_info() {
    echo -e "${YELLOW}Volume Information:${NC}"
    
    for volume in docker_kuzu-data docker_kestra-data; do
        if docker volume inspect "$volume" >/dev/null 2>&1; then
            echo "Volume: $volume"
            docker volume inspect "$volume" --format "  Mountpoint: {{.Mountpoint}}"
            docker volume inspect "$volume" --format "  Driver: {{.Driver}}"
            
            # Get size if possible
            local mountpoint=$(docker volume inspect "$volume" --format "{{.Mountpoint}}")
            if [ -d "$mountpoint" ]; then
                local size=$(du -sh "$mountpoint" 2>/dev/null | cut -f1 || echo "Unknown")
                echo "  Size: $size"
            fi
            echo
        else
            echo -e "${RED}Volume $volume does not exist${NC}"
        fi
    done
}

# Main script logic
case "${1:-help}" in
    backup)
        echo "Starting backup of all volumes..."
        backup_volume "docker_kuzu-data"
        backup_volume "docker_kestra-data"
        echo -e "${GREEN}All backups completed!${NC}"
        ;;
    
    backup-kuzu)
        backup_volume "docker_kuzu-data"
        ;;
    
    backup-kestra)
        backup_volume "docker_kestra-data"
        ;;
    
    restore)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 restore <volume-name> <backup-file>"
            echo "Example: $0 restore kuzu-data ./backups/kuzu-data_20240527_120000.tar.gz"
            exit 1
        fi
        restore_volume "$2" "$3"
        ;;
    
    list)
        list_backups
        ;;
    
    clean)
        clean_backups "${2:-7}"
        ;;
    
    info)
        show_volume_info
        ;;
    
    help|*)
        echo "GraphMemory-IDE Volume Management Script"
        echo
        echo "Usage: $0 <command> [options]"
        echo
        echo "Commands:"
        echo "  backup           - Backup all volumes (kuzu-data and kestra-data)"
        echo "  backup-kuzu      - Backup only kuzu-data volume"
        echo "  backup-kestra    - Backup only kestra-data volume"
        echo "  restore <vol> <file> - Restore volume from backup file"
        echo "  list             - List all available backups"
        echo "  clean [days]     - Clean backups older than N days (default: 7)"
        echo "  info             - Show volume information"
        echo "  help             - Show this help message"
        echo
        echo "Examples:"
        echo "  $0 backup                    # Backup all volumes"
        echo "  $0 restore kuzu-data ./backups/kuzu-data_20240527_120000.tar.gz"
        echo "  $0 clean 30                  # Clean backups older than 30 days"
        echo
        ;;
esac 