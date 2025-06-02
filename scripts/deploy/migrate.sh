#!/bin/bash
set -euo pipefail

# GraphMemory-IDE CI/CD Migration Automation Script
# This script automates database migrations for CI/CD pipelines

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/deploy/logs/migration_$(date +%Y%m%d_%H%M%S).log"
DATE=$(date +%Y%m%d_%H%M%S)

# Deployment environment
ENVIRONMENT="${ENVIRONMENT:-production}"
DRY_RUN="${DRY_RUN:-false}"
FORCE_MIGRATION="${FORCE_MIGRATION:-false}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"

# Database configuration
DATABASE_URL="${DATABASE_URL}"
POSTGRES_HOST="${POSTGRES_HOST:-postgresql}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-graphmemory}"
POSTGRES_DB="${POSTGRES_DB:-graphmemory}"

# Migration settings
MIGRATION_TIMEOUT="${MIGRATION_TIMEOUT:-300}"  # 5 minutes
MAX_RETRIES="${MAX_RETRIES:-3}"
BACKUP_BEFORE_MIGRATION="${BACKUP_BEFORE_MIGRATION:-true}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$ENVIRONMENT] $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    send_notification "❌ Migration Failed" "$1" "error"
    exit 1
}

# Success notification
success() {
    log "SUCCESS: $1"
    send_notification "✅ Migration Success" "$1" "success"
}

# Warning function
warn() {
    log "WARNING: $1"
}

# Send notifications (webhook, Slack, etc.)
send_notification() {
    local title="$1"
    local message="$2"
    local level="${3:-info}"
    
    # Add your notification logic here
    # Examples: Slack webhook, Discord, email, etc.
    
    if [ -n "${WEBHOOK_URL:-}" ]; then
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"[$ENVIRONMENT] $title\",
                \"attachments\": [{
                    \"color\": \"$([ "$level" = "error" ] && echo "danger" || echo "good")\",
                    \"text\": \"$message\",
                    \"fields\": [{
                        \"title\": \"Environment\",
                        \"value\": \"$ENVIRONMENT\",
                        \"short\": true
                    }, {
                        \"title\": \"Timestamp\",
                        \"value\": \"$(date)\",
                        \"short\": true
                    }]
                }]
            }" > /dev/null 2>&1 || warn "Failed to send notification"
    fi
    
    log "Notification sent: $title - $message"
}

# Check prerequisites
check_prerequisites() {
    log "Checking migration prerequisites..."
    
    # Check required tools
    for tool in python3 alembic psql pg_dump; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            error_exit "Required tool not found: $tool"
        fi
    done
    
    # Check database connectivity
    if ! timeout 30 psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        error_exit "Cannot connect to database: $DATABASE_URL"
    fi
    
    # Check alembic configuration
    if [ ! -f "$PROJECT_ROOT/server/alembic.ini" ]; then
        error_exit "Alembic configuration not found"
    fi
    
    # Check migration directory
    if [ ! -d "$PROJECT_ROOT/server/alembic/versions" ]; then
        error_exit "Alembic versions directory not found"
    fi
    
    log "✓ Prerequisites check passed"
}

# Create pre-migration backup
create_backup() {
    if [ "$SKIP_BACKUP" = "true" ]; then
        log "Skipping backup (SKIP_BACKUP=true)"
        return 0
    fi
    
    log "Creating pre-migration backup..."
    
    local backup_dir="${PROJECT_ROOT}/deploy/backups/pre_migration_${DATE}"
    mkdir -p "$backup_dir"
    
    # Create database backup
    if pg_dump "$DATABASE_URL" \
        --format=custom \
        --file="${backup_dir}/database_backup.sql" \
        --verbose; then
        
        # Compress backup
        gzip "${backup_dir}/database_backup.sql"
        
        # Create checksum
        sha256sum "${backup_dir}/database_backup.sql.gz" > "${backup_dir}/database_backup.sql.gz.sha256"
        
        log "✓ Pre-migration backup created: $backup_dir"
        echo "$backup_dir" > "${PROJECT_ROOT}/deploy/logs/last_backup_location.txt"
    else
        error_exit "Failed to create pre-migration backup"
    fi
}

# Get current migration state
get_migration_state() {
    log "Getting current migration state..."
    
    cd "$PROJECT_ROOT/server"
    
    # Get current database revision
    local current_revision
    if current_revision=$(alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1); then
        log "Current database revision: ${current_revision:-none}"
    else
        log "No current revision found (new database)"
        current_revision="none"
    fi
    
    # Get available migrations
    local pending_migrations
    if pending_migrations=$(alembic history --rev-range="${current_revision}:head" 2>/dev/null | grep -c "^Rev:"); then
        log "Pending migrations: $pending_migrations"
    else
        pending_migrations=0
    fi
    
    echo "$current_revision|$pending_migrations"
}

# Validate migrations
validate_migrations() {
    log "Validating migrations..."
    
    cd "$PROJECT_ROOT/server"
    
    # Check for migration conflicts
    if ! alembic check 2>/dev/null; then
        error_exit "Migration validation failed - conflicts detected"
    fi
    
    # Verify migration files integrity
    local migration_files
    migration_files=$(find alembic/versions -name "*.py" | wc -l)
    
    if [ "$migration_files" -eq 0 ]; then
        warn "No migration files found"
    else
        log "✓ Found $migration_files migration files"
    fi
    
    # Syntax check on migration files
    for migration_file in alembic/versions/*.py; do
        if [ -f "$migration_file" ]; then
            if ! python3 -m py_compile "$migration_file" 2>/dev/null; then
                error_exit "Syntax error in migration file: $(basename "$migration_file")"
            fi
        fi
    done
    
    log "✓ Migration validation passed"
}

# Run migrations with retry logic
run_migrations() {
    local attempt=1
    local max_attempts=$MAX_RETRIES
    
    while [ $attempt -le $max_attempts ]; do
        log "Migration attempt $attempt/$max_attempts..."
        
        cd "$PROJECT_ROOT/server"
        
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would execute migrations"
            alembic history --verbose
            return 0
        fi
        
        # Set migration timeout
        if timeout "$MIGRATION_TIMEOUT" alembic upgrade head; then
            log "✓ Migrations completed successfully"
            return 0
        else
            local exit_code=$?
            
            if [ $attempt -eq $max_attempts ]; then
                error_exit "Migration failed after $max_attempts attempts (exit code: $exit_code)"
            else
                warn "Migration attempt $attempt failed, retrying in 10 seconds..."
                sleep 10
                ((attempt++))
            fi
        fi
    done
}

# Verify migration success
verify_migrations() {
    log "Verifying migration success..."
    
    cd "$PROJECT_ROOT/server"
    
    # Check if we're at head revision
    local current_revision
    local head_revision
    
    current_revision=$(alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
    head_revision=$(alembic heads 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
    
    if [ "$current_revision" = "$head_revision" ]; then
        log "✓ Database is at head revision: $current_revision"
    else
        error_exit "Migration verification failed. Current: $current_revision, Expected: $head_revision"
    fi
    
    # Test database connectivity and basic queries
    if psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM information_schema.tables;" >/dev/null 2>&1; then
        log "✓ Database connectivity verified"
    else
        error_exit "Database connectivity check failed after migration"
    fi
    
    # Run any custom verification scripts
    if [ -f "$PROJECT_ROOT/scripts/deploy/verify_migration.py" ]; then
        log "Running custom verification script..."
        if python3 "$PROJECT_ROOT/scripts/deploy/verify_migration.py"; then
            log "✓ Custom verification passed"
        else
            error_exit "Custom verification failed"
        fi
    fi
}

# Rollback migration (if needed)
rollback_migration() {
    local target_revision="$1"
    
    log "Rolling back to revision: $target_revision"
    
    cd "$PROJECT_ROOT/server"
    
    if [ "$DRY_RUN" = "true" ]; then
        log "DRY RUN: Would rollback to revision $target_revision"
        return 0
    fi
    
    if timeout "$MIGRATION_TIMEOUT" alembic downgrade "$target_revision"; then
        log "✓ Rollback completed successfully"
    else
        error_exit "Rollback failed"
    fi
}

# Data seeding (if needed)
run_data_seeding() {
    if [ -f "$PROJECT_ROOT/server/data_seeding.py" ]; then
        log "Running data seeding..."
        
        cd "$PROJECT_ROOT/server"
        
        if [ "$DRY_RUN" = "true" ]; then
            log "DRY RUN: Would run data seeding"
            return 0
        fi
        
        if python3 data_seeding.py; then
            log "✓ Data seeding completed"
        else
            warn "Data seeding failed (non-critical)"
        fi
    else
        log "No data seeding script found, skipping"
    fi
}

# Generate migration report
generate_report() {
    local report_file="${PROJECT_ROOT}/deploy/logs/migration_report_${DATE}.json"
    
    cd "$PROJECT_ROOT/server"
    
    local current_revision
    current_revision=$(alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)
    
    # Generate JSON report
    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "status": "success",
    "current_revision": "$current_revision",
    "migration_duration": "$SECONDS",
    "dry_run": $DRY_RUN,
    "backup_created": $([ "$SKIP_BACKUP" = "true" ] && echo "false" || echo "true"),
    "log_file": "$LOG_FILE"
}
EOF
    
    log "Migration report generated: $report_file"
}

# Health check after migration
health_check() {
    log "Running post-migration health check..."
    
    # Check database connections
    if ! psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        error_exit "Health check failed: Database connectivity"
    fi
    
    # Check application health (if applicable)
    if [ -n "${HEALTH_CHECK_URL:-}" ]; then
        if curl -f -s "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
            log "✓ Application health check passed"
        else
            warn "Application health check failed"
        fi
    fi
    
    log "✓ Health check completed"
}

# Main migration function
main() {
    local command="${1:-migrate}"
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "Starting migration process..."
    log "Environment: $ENVIRONMENT"
    log "Dry run: $DRY_RUN"
    log "Command: $command"
    
    case "$command" in
        migrate)
            check_prerequisites
            
            # Get initial state
            local state
            state=$(get_migration_state)
            local current_rev=$(echo "$state" | cut -d'|' -f1)
            local pending_count=$(echo "$state" | cut -d'|' -f2)
            
            log "Initial state - Current: $current_rev, Pending: $pending_count"
            
            if [ "$pending_count" -eq 0 ]; then
                log "No pending migrations, database is up to date"
                success "Database is already up to date"
                exit 0
            fi
            
            # Create backup
            if [ "$BACKUP_BEFORE_MIGRATION" = "true" ]; then
                create_backup
            fi
            
            # Validate and run migrations
            validate_migrations
            run_migrations
            verify_migrations
            
            # Optional data seeding
            run_data_seeding
            
            # Health check
            health_check
            
            # Generate report
            generate_report
            
            success "Migration completed successfully ($pending_count migrations applied)"
            ;;
            
        rollback)
            local target_revision="${2:-HEAD~1}"
            check_prerequisites
            create_backup
            rollback_migration "$target_revision"
            verify_migrations
            success "Rollback completed successfully"
            ;;
            
        status)
            check_prerequisites
            get_migration_state
            ;;
            
        validate)
            check_prerequisites
            validate_migrations
            log "Migration validation completed"
            ;;
            
        *)
            echo "Usage: $0 {migrate|rollback [revision]|status|validate}"
            echo ""
            echo "Commands:"
            echo "  migrate          - Run pending migrations"
            echo "  rollback [rev]   - Rollback to specific revision"
            echo "  status          - Show current migration status"
            echo "  validate        - Validate migration files"
            echo ""
            echo "Environment Variables:"
            echo "  ENVIRONMENT      - Deployment environment (default: production)"
            echo "  DRY_RUN         - Preview migrations without executing (default: false)"
            echo "  FORCE_MIGRATION - Force migration even with warnings (default: false)"
            echo "  SKIP_BACKUP     - Skip pre-migration backup (default: false)"
            echo "  DATABASE_URL    - Database connection string (required)"
            echo ""
            echo "Examples:"
            echo "  $0 migrate"
            echo "  DRY_RUN=true $0 migrate"
            echo "  $0 rollback HEAD~1"
            echo "  $0 status"
            exit 1
            ;;
    esac
}

# Trap for cleanup
cleanup() {
    if [ $? -ne 0 ]; then
        error_exit "Migration process interrupted"
    fi
}
trap cleanup EXIT

# Run main function
main "$@" 