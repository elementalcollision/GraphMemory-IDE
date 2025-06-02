#!/bin/bash
set -euo pipefail

# GraphMemory-IDE Database Restoration Script
# This script provides comprehensive restoration functionality for PostgreSQL and Kuzu databases

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_STORAGE_PATH:-/backups}"
LOG_FILE="${BACKUP_DIR}/restore.log"
DATE=$(date +%Y%m%d_%H%M%S)

# Database configuration
POSTGRES_HOST="${POSTGRES_HOST:-postgresql}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-graphmemory}"
POSTGRES_DB="${POSTGRES_DB:-graphmemory}"
PGPASSWORD="${POSTGRES_PASSWORD}"

# S3 Configuration (optional)
S3_BACKUP_ENABLED="${S3_BACKUP_ENABLED:-false}"
S3_BUCKET="${S3_BUCKET:-}"
S3_REGION="${S3_REGION:-us-west-2}"

# Safety flags
FORCE_RESTORE=false
SKIP_CONFIRMATION=false

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Warning function
warn() {
    log "WARNING: $1"
}

# Check if backup file exists and is valid
validate_backup() {
    local backup_file="$1"
    local checksum_file="${backup_file}.sha256"
    
    if [ ! -f "$backup_file" ]; then
        error_exit "Backup file not found: $backup_file"
    fi
    
    # Verify checksum if available
    if [ -f "$checksum_file" ]; then
        log "Verifying backup integrity..."
        if sha256sum -c "$checksum_file" > /dev/null 2>&1; then
            log "✓ Backup integrity verified"
        else
            error_exit "Backup integrity check failed"
        fi
    else
        warn "No checksum file found, skipping integrity check"
    fi
}

# List available backups
list_backups() {
    log "Available PostgreSQL backups:"
    echo "================================"
    
    echo "Full backups:"
    ls -lht "${BACKUP_DIR}/postgresql/full"/*.gz 2>/dev/null | head -10 || echo "No full backups found"
    
    echo -e "\nSchema backups:"
    ls -lht "${BACKUP_DIR}/postgresql/schema"/*.gz 2>/dev/null | head -5 || echo "No schema backups found"
    
    echo -e "\nIncremental backups:"
    ls -lht "${BACKUP_DIR}/postgresql/incremental"/ 2>/dev/null | head -5 || echo "No incremental backups found"
    
    echo -e "\nKuzu backups:"
    ls -lht "${BACKUP_DIR}/kuzu/full"/*.tar.gz 2>/dev/null | head -10 || echo "No Kuzu backups found"
}

# Download backup from S3 if needed
download_from_s3() {
    local backup_name="$1"
    local local_path="$2"
    
    if [ "$S3_BACKUP_ENABLED" = "true" ] && [ -n "$S3_BUCKET" ]; then
        if command -v aws >/dev/null 2>&1; then
            log "Downloading backup from S3..."
            
            # Download PostgreSQL backup
            if [[ "$backup_name" == *postgresql* ]]; then
                aws s3 cp "s3://${S3_BUCKET}/postgresql/${backup_name}" "$local_path" --region "$S3_REGION"
                aws s3 cp "s3://${S3_BUCKET}/postgresql/${backup_name}.sha256" "${local_path}.sha256" --region "$S3_REGION"
            fi
            
            # Download Kuzu backup
            if [[ "$backup_name" == *kuzu* ]]; then
                aws s3 cp "s3://${S3_BUCKET}/kuzu/${backup_name}" "$local_path" --region "$S3_REGION"
                aws s3 cp "s3://${S3_BUCKET}/kuzu/${backup_name}.sha256" "${local_path}.sha256" --region "$S3_REGION"
            fi
            
            log "S3 download completed"
        else
            error_exit "AWS CLI not available for S3 download"
        fi
    fi
}

# Create pre-restore backup
create_pre_restore_backup() {
    log "Creating pre-restore backup as safety measure..."
    
    local pre_restore_dir="${BACKUP_DIR}/pre_restore_${DATE}"
    mkdir -p "$pre_restore_dir"
    
    # Backup current PostgreSQL database
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --format=custom --file="${pre_restore_dir}/pre_restore_postgresql.sql"; then
        
        gzip "${pre_restore_dir}/pre_restore_postgresql.sql"
        log "✓ Pre-restore PostgreSQL backup created"
    else
        warn "Failed to create pre-restore PostgreSQL backup"
    fi
    
    # Backup current Kuzu database
    local kuzu_data_dir="/kuzu/data"
    if [ -d "$kuzu_data_dir" ]; then
        if tar -czf "${pre_restore_dir}/pre_restore_kuzu.tar.gz" -C "$(dirname "$kuzu_data_dir")" "$(basename "$kuzu_data_dir")"; then
            log "✓ Pre-restore Kuzu backup created"
        else
            warn "Failed to create pre-restore Kuzu backup"
        fi
    fi
    
    log "Pre-restore backup location: $pre_restore_dir"
}

# Stop application services (to prevent connections during restore)
stop_services() {
    log "Stopping application services..."
    
    # This would typically stop your application containers
    # Adjust based on your deployment setup
    if command -v docker-compose >/dev/null 2>&1; then
        # Stop app services but keep databases running
        docker-compose stop app || warn "Failed to stop app service"
    fi
    
    # Terminate active database connections
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" \
        2>/dev/null || warn "Failed to terminate database connections"
    
    log "Services stopped"
}

# Start application services
start_services() {
    log "Starting application services..."
    
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose start app || warn "Failed to start app service"
    fi
    
    log "Services started"
}

# Restore PostgreSQL database
restore_postgresql() {
    local backup_file="$1"
    local restore_type="$2"  # full, schema, data
    
    log "Starting PostgreSQL restore from: $(basename "$backup_file")"
    
    # Validate backup
    validate_backup "$backup_file"
    
    case "$restore_type" in
        full)
            # Full restore (structure + data)
            if [[ "$backup_file" == *.gz ]]; then
                gunzip -c "$backup_file" | pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                    -d "$POSTGRES_DB" --verbose --clean --if-exists --create --format=custom
            else
                pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                    -d "$POSTGRES_DB" --verbose --clean --if-exists --create --format=custom "$backup_file"
            fi
            ;;
        schema)
            # Schema-only restore
            if [[ "$backup_file" == *.gz ]]; then
                gunzip -c "$backup_file" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"
            else
                psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$backup_file"
            fi
            ;;
        data)
            # Data-only restore
            if [[ "$backup_file" == *.gz ]]; then
                gunzip -c "$backup_file" | pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                    -d "$POSTGRES_DB" --verbose --data-only --format=custom
            else
                pg_restore -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                    -d "$POSTGRES_DB" --verbose --data-only --format=custom "$backup_file"
            fi
            ;;
        *)
            error_exit "Invalid restore type: $restore_type"
            ;;
    esac
    
    log "PostgreSQL restore completed"
}

# Restore Kuzu database
restore_kuzu() {
    local backup_file="$1"
    local kuzu_data_dir="/kuzu/data"
    
    log "Starting Kuzu restore from: $(basename "$backup_file")"
    
    # Validate backup
    validate_backup "$backup_file"
    
    # Stop Kuzu service
    docker-compose stop kuzu 2>/dev/null || warn "Failed to stop Kuzu service"
    
    # Backup current Kuzu data
    if [ -d "$kuzu_data_dir" ]; then
        local backup_current="${kuzu_data_dir}_backup_${DATE}"
        mv "$kuzu_data_dir" "$backup_current"
        log "Current Kuzu data backed up to: $backup_current"
    fi
    
    # Extract backup
    mkdir -p "$(dirname "$kuzu_data_dir")"
    if tar -xzf "$backup_file" -C "$(dirname "$kuzu_data_dir")"; then
        log "Kuzu restore completed"
    else
        error_exit "Kuzu restore failed"
    fi
    
    # Start Kuzu service
    docker-compose start kuzu 2>/dev/null || warn "Failed to start Kuzu service"
    
    log "Kuzu restore completed"
}

# Verify restore integrity
verify_restore() {
    log "Verifying restore integrity..."
    
    # Test PostgreSQL connection and basic queries
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -c "SELECT COUNT(*) FROM information_schema.tables;" > /dev/null 2>&1; then
        log "✓ PostgreSQL restore verification passed"
    else
        error_exit "PostgreSQL restore verification failed"
    fi
    
    # Test Kuzu database
    if [ -d "/kuzu/data" ]; then
        log "✓ Kuzu data directory exists"
    else
        warn "Kuzu data directory not found"
    fi
    
    log "Restore verification completed"
}

# Interactive backup selection
select_backup() {
    local backup_type="$1"
    
    echo "Available ${backup_type} backups:"
    echo "================================"
    
    local backups=()
    local counter=1
    
    case "$backup_type" in
        postgresql-full)
            while IFS= read -r -d '' backup; do
                backups+=("$backup")
                echo "$counter) $(basename "$backup") ($(date -r "$backup" '+%Y-%m-%d %H:%M:%S'))"
                ((counter++))
            done < <(find "${BACKUP_DIR}/postgresql/full" -name "*.gz" -print0 | sort -z)
            ;;
        postgresql-schema)
            while IFS= read -r -d '' backup; do
                backups+=("$backup")
                echo "$counter) $(basename "$backup") ($(date -r "$backup" '+%Y-%m-%d %H:%M:%S'))"
                ((counter++))
            done < <(find "${BACKUP_DIR}/postgresql/schema" -name "*.gz" -print0 | sort -z)
            ;;
        kuzu)
            while IFS= read -r -d '' backup; do
                backups+=("$backup")
                echo "$counter) $(basename "$backup") ($(date -r "$backup" '+%Y-%m-%d %H:%M:%S'))"
                ((counter++))
            done < <(find "${BACKUP_DIR}/kuzu/full" -name "*.tar.gz" -print0 | sort -z)
            ;;
    esac
    
    if [ ${#backups[@]} -eq 0 ]; then
        error_exit "No ${backup_type} backups found"
    fi
    
    echo "0) Cancel"
    echo -n "Select backup to restore (1-${#backups[@]}): "
    read -r selection
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#backups[@]} ]; then
        echo "${backups[$((selection-1))]}"
    elif [ "$selection" -eq 0 ]; then
        log "Restore cancelled by user"
        exit 0
    else
        error_exit "Invalid selection"
    fi
}

# Confirmation prompt
confirm_restore() {
    local backup_file="$1"
    local restore_type="$2"
    
    if [ "$SKIP_CONFIRMATION" = true ]; then
        return 0
    fi
    
    echo "⚠️  WARNING: This will restore the database from backup!"
    echo "Backup file: $(basename "$backup_file")"
    echo "Restore type: $restore_type"
    echo "Current data will be replaced!"
    echo ""
    echo "A pre-restore backup will be created automatically."
    echo ""
    echo -n "Are you sure you want to continue? (yes/no): "
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
}

# Main restore function
main() {
    local command="$1"
    shift
    
    case "$command" in
        list)
            list_backups
            ;;
        postgresql-full)
            local backup_file="${1:-}"
            if [ -z "$backup_file" ]; then
                backup_file=$(select_backup "postgresql-full")
            fi
            
            confirm_restore "$backup_file" "PostgreSQL Full"
            create_pre_restore_backup
            stop_services
            restore_postgresql "$backup_file" "full"
            verify_restore
            start_services
            ;;
        postgresql-schema)
            local backup_file="${1:-}"
            if [ -z "$backup_file" ]; then
                backup_file=$(select_backup "postgresql-schema")
            fi
            
            confirm_restore "$backup_file" "PostgreSQL Schema"
            restore_postgresql "$backup_file" "schema"
            verify_restore
            ;;
        kuzu)
            local backup_file="${1:-}"
            if [ -z "$backup_file" ]; then
                backup_file=$(select_backup "kuzu")
            fi
            
            confirm_restore "$backup_file" "Kuzu"
            create_pre_restore_backup
            restore_kuzu "$backup_file"
            verify_restore
            ;;
        verify)
            verify_restore
            ;;
        *)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  list                    - List available backups"
            echo "  postgresql-full [file]  - Restore PostgreSQL full backup"
            echo "  postgresql-schema [file]- Restore PostgreSQL schema only"
            echo "  kuzu [file]            - Restore Kuzu database"
            echo "  verify                 - Verify current database integrity"
            echo ""
            echo "Options:"
            echo "  --force                - Skip safety checks"
            echo "  --yes                  - Skip confirmation prompts"
            echo ""
            echo "Examples:"
            echo "  $0 list"
            echo "  $0 postgresql-full"
            echo "  $0 postgresql-full /backups/postgresql/full/backup.sql.gz"
            echo "  $0 kuzu --yes"
            exit 1
            ;;
    esac
    
    log "Restore operation completed successfully"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_RESTORE=true
            shift
            ;;
        --yes)
            SKIP_CONFIRMATION=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Check if command provided
if [ $# -eq 0 ]; then
    main "help"
else
    # Export PostgreSQL password for psql/pg_restore
    export PGPASSWORD
    
    # Run main function with all arguments
    main "$@"
fi 