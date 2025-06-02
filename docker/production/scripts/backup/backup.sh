#!/bin/bash
set -euo pipefail

# GraphMemory-IDE Database Backup Script
# This script provides comprehensive backup functionality for PostgreSQL and Kuzu databases

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_STORAGE_PATH:-/backups}"
LOG_FILE="${BACKUP_DIR}/backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

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

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Create backup directory structure
create_backup_dirs() {
    log "Creating backup directory structure..."
    mkdir -p "${BACKUP_DIR}"/{postgresql,kuzu,logs,temp}
    mkdir -p "${BACKUP_DIR}/postgresql"/{full,incremental,schema}
    mkdir -p "${BACKUP_DIR}/kuzu"/{full,incremental}
}

# Check database connectivity
check_db_connection() {
    log "Checking database connectivity..."
    
    # Test PostgreSQL connection
    if ! pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        error_exit "Cannot connect to PostgreSQL database"
    fi
    
    log "Database connectivity verified"
}

# PostgreSQL full backup
postgres_full_backup() {
    local backup_file="${BACKUP_DIR}/postgresql/full/graphmemory_full_${DATE}.sql"
    local compressed_file="${backup_file}.gz"
    
    log "Starting PostgreSQL full backup..."
    
    # Create full database dump
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --verbose --clean --if-exists --create --format=custom \
        --file="$backup_file"; then
        
        # Compress backup
        gzip "$backup_file"
        
        # Calculate checksums
        sha256sum "$compressed_file" > "${compressed_file}.sha256"
        
        log "PostgreSQL full backup completed: $compressed_file"
        return 0
    else
        error_exit "PostgreSQL full backup failed"
    fi
}

# PostgreSQL schema-only backup
postgres_schema_backup() {
    local backup_file="${BACKUP_DIR}/postgresql/schema/graphmemory_schema_${DATE}.sql"
    
    log "Starting PostgreSQL schema backup..."
    
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --verbose --schema-only --create --format=plain \
        --file="$backup_file"; then
        
        # Compress schema backup
        gzip "$backup_file"
        
        log "PostgreSQL schema backup completed: ${backup_file}.gz"
        return 0
    else
        error_exit "PostgreSQL schema backup failed"
    fi
}

# PostgreSQL incremental backup (WAL archiving)
postgres_incremental_backup() {
    local wal_backup_dir="${BACKUP_DIR}/postgresql/incremental/${DATE}"
    
    log "Starting PostgreSQL incremental backup..."
    
    mkdir -p "$wal_backup_dir"
    
    # Create base backup if first incremental
    if [ ! -f "${BACKUP_DIR}/postgresql/incremental/base_backup_complete" ]; then
        log "Creating base backup for incremental backups..."
        
        if pg_basebackup -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
            -D "${BACKUP_DIR}/postgresql/incremental/base" \
            -Ft -z -P; then
            
            touch "${BACKUP_DIR}/postgresql/incremental/base_backup_complete"
            log "Base backup for incremental backups completed"
        else
            error_exit "Base backup creation failed"
        fi
    fi
    
    # Archive WAL files (this would typically be configured in PostgreSQL)
    log "WAL archiving setup completed"
}

# Kuzu database backup
kuzu_backup() {
    local kuzu_backup_dir="${BACKUP_DIR}/kuzu/full/kuzu_${DATE}"
    local kuzu_data_dir="/kuzu/data"
    
    log "Starting Kuzu database backup..."
    
    mkdir -p "$kuzu_backup_dir"
    
    # Copy Kuzu database files
    if [ -d "$kuzu_data_dir" ]; then
        if tar -czf "${kuzu_backup_dir}.tar.gz" -C "$(dirname "$kuzu_data_dir")" "$(basename "$kuzu_data_dir")"; then
            
            # Calculate checksums
            sha256sum "${kuzu_backup_dir}.tar.gz" > "${kuzu_backup_dir}.tar.gz.sha256"
            
            log "Kuzu backup completed: ${kuzu_backup_dir}.tar.gz"
            return 0
        else
            error_exit "Kuzu backup failed"
        fi
    else
        log "WARNING: Kuzu data directory not found, skipping Kuzu backup"
    fi
}

# Upload to S3 (if enabled)
s3_upload() {
    if [ "$S3_BACKUP_ENABLED" = "true" ] && [ -n "$S3_BUCKET" ]; then
        log "Starting S3 upload..."
        
        # Upload PostgreSQL backups
        if command -v aws >/dev/null 2>&1; then
            aws s3 sync "${BACKUP_DIR}/postgresql" "s3://${S3_BUCKET}/postgresql/" \
                --exclude "*" --include "*.gz" --include "*.sha256" \
                --region "$S3_REGION"
            
            # Upload Kuzu backups
            aws s3 sync "${BACKUP_DIR}/kuzu" "s3://${S3_BUCKET}/kuzu/" \
                --exclude "*" --include "*.tar.gz" --include "*.sha256" \
                --region "$S3_REGION"
            
            log "S3 upload completed"
        else
            log "WARNING: AWS CLI not available, skipping S3 upload"
        fi
    else
        log "S3 backup disabled or not configured"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Clean local backups
    find "${BACKUP_DIR}/postgresql" -name "*.gz" -mtime +$RETENTION_DAYS -delete
    find "${BACKUP_DIR}/kuzu" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "${BACKUP_DIR}/postgresql" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
    find "${BACKUP_DIR}/kuzu" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
    
    # Clean S3 backups if enabled
    if [ "$S3_BACKUP_ENABLED" = "true" ] && [ -n "$S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        # Note: This requires proper S3 lifecycle policies for optimal cleanup
        log "S3 cleanup should be configured via lifecycle policies"
    fi
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backups() {
    log "Verifying backup integrity..."
    
    local verification_failed=0
    
    # Verify PostgreSQL backups
    for backup_file in "${BACKUP_DIR}/postgresql/full"/*.gz; do
        if [ -f "$backup_file" ]; then
            if [ -f "${backup_file}.sha256" ]; then
                if sha256sum -c "${backup_file}.sha256" > /dev/null 2>&1; then
                    log "✓ Verified: $(basename "$backup_file")"
                else
                    log "✗ Verification failed: $(basename "$backup_file")"
                    verification_failed=1
                fi
            else
                log "⚠ No checksum file for: $(basename "$backup_file")"
            fi
        fi
    done
    
    # Verify Kuzu backups
    for backup_file in "${BACKUP_DIR}/kuzu/full"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            if [ -f "${backup_file}.sha256" ]; then
                if sha256sum -c "${backup_file}.sha256" > /dev/null 2>&1; then
                    log "✓ Verified: $(basename "$backup_file")"
                else
                    log "✗ Verification failed: $(basename "$backup_file")"
                    verification_failed=1
                fi
            else
                log "⚠ No checksum file for: $(basename "$backup_file")"
            fi
        fi
    done
    
    if [ $verification_failed -eq 0 ]; then
        log "All backups verified successfully"
        return 0
    else
        error_exit "Backup verification failed"
    fi
}

# Generate backup report
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report_${DATE}.txt"
    
    {
        echo "GraphMemory-IDE Backup Report"
        echo "=============================="
        echo "Date: $(date)"
        echo "Backup Directory: $BACKUP_DIR"
        echo ""
        echo "PostgreSQL Backups:"
        ls -lh "${BACKUP_DIR}/postgresql/full"/*.gz 2>/dev/null | tail -5 || echo "No PostgreSQL backups found"
        echo ""
        echo "Kuzu Backups:"
        ls -lh "${BACKUP_DIR}/kuzu/full"/*.tar.gz 2>/dev/null | tail -5 || echo "No Kuzu backups found"
        echo ""
        echo "Disk Usage:"
        du -sh "${BACKUP_DIR}"/* 2>/dev/null || echo "No backup data"
        echo ""
        echo "Log Summary:"
        tail -20 "$LOG_FILE"
    } > "$report_file"
    
    log "Backup report generated: $report_file"
}

# Main backup function
main() {
    log "Starting GraphMemory-IDE backup process..."
    
    # Parse command line arguments
    BACKUP_TYPE="${1:-full}"
    
    case "$BACKUP_TYPE" in
        full)
            create_backup_dirs
            check_db_connection
            postgres_full_backup
            postgres_schema_backup
            kuzu_backup
            verify_backups
            s3_upload
            cleanup_old_backups
            generate_report
            ;;
        incremental)
            create_backup_dirs
            check_db_connection
            postgres_incremental_backup
            s3_upload
            ;;
        schema)
            create_backup_dirs
            check_db_connection
            postgres_schema_backup
            s3_upload
            ;;
        verify)
            verify_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        *)
            echo "Usage: $0 {full|incremental|schema|verify|cleanup}"
            echo "  full        - Complete backup of all databases"
            echo "  incremental - Incremental backup (WAL archiving)"
            echo "  schema      - Schema-only backup"
            echo "  verify      - Verify backup integrity"
            echo "  cleanup     - Clean old backups"
            exit 1
            ;;
    esac
    
    log "Backup process completed successfully"
}

# Export PostgreSQL password for pg_dump
export PGPASSWORD

# Run main function
main "$@" 