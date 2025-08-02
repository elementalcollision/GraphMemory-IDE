#!/bin/bash

# Disaster Recovery Script for Hybrid CPython/Codon Architecture
# This script handles disaster recovery procedures with automated recovery

set -euo pipefail

# Configuration
NAMESPACE="graphmemory"
BACKUP_DIR="backups"
RECOVERY_LOG="recovery.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a $RECOVERY_LOG
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a $RECOVERY_LOG
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $RECOVERY_LOG
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1" | tee -a $RECOVERY_LOG
}

# Initialize recovery log
init_recovery_log() {
    echo "=== Disaster Recovery Started: $(date) ===" > $RECOVERY_LOG
    log_info "Recovery log initialized: $RECOVERY_LOG"
}

# Check cluster health
check_cluster_health() {
    log_info "Checking cluster health..."
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        return 1
    fi
    
    # Check node status
    local unhealthy_nodes=$(kubectl get nodes --field-selector=status.conditions[?(@.type=="Ready")].status!=True -o name)
    if [ -n "$unhealthy_nodes" ]; then
        log_warn "Unhealthy nodes detected:"
        echo "$unhealthy_nodes"
    fi
    
    log_info "Cluster health check completed"
}

# Check service health
check_service_health() {
    local service=$1
    local namespace=${2:-$NAMESPACE}
    
    log_debug "Checking health of $service in namespace $namespace"
    
    # Check if service exists
    if ! kubectl get service $service -n $namespace &> /dev/null; then
        log_error "Service $service does not exist"
        return 1
    fi
    
    # Check if pods are running
    local running_pods=$(kubectl get pods -n $namespace -l app=$service --field-selector=status.phase=Running -o name | wc -l)
    local total_pods=$(kubectl get pods -n $namespace -l app=$service -o name | wc -l)
    
    if [ $running_pods -eq 0 ]; then
        log_error "No running pods for service $service"
        return 1
    fi
    
    if [ $running_pods -lt $total_pods ]; then
        log_warn "Some pods for service $service are not running ($running_pods/$total_pods)"
    fi
    
    log_debug "Service $service health check passed"
    return 0
}

# Scale services for recovery
scale_services() {
    log_info "Scaling services for recovery..."
    
    # Scale CPython services
    kubectl scale deployment auth-service --replicas=5 -n $NAMESPACE
    log_info "Scaled auth-service to 5 replicas"
    
    # Scale Codon services
    kubectl scale deployment analytics-service --replicas=3 -n $NAMESPACE
    kubectl scale deployment ai-detection-service --replicas=2 -n $NAMESPACE
    log_info "Scaled Codon services for recovery"
    
    # Wait for scaling to complete
    kubectl rollout status deployment/auth-service -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/analytics-service -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/ai-detection-service -n $NAMESPACE --timeout=300s
    
    log_info "Service scaling completed"
}

# Restart failed services
restart_failed_services() {
    log_info "Restarting failed services..."
    
    local services=("auth-service" "analytics-service" "ai-detection-service")
    
    for service in "${services[@]}"; do
        if ! check_service_health $service; then
            log_warn "Restarting $service..."
            kubectl rollout restart deployment/$service -n $NAMESPACE
            
            # Wait for restart to complete
            kubectl rollout status deployment/$service -n $NAMESPACE --timeout=300s
            
            # Verify service is healthy after restart
            if check_service_health $service; then
                log_info "$service restarted successfully"
            else
                log_error "$service restart failed"
                return 1
            fi
        fi
    done
    
    log_info "Service restart completed"
}

# Restore from backup
restore_from_backup() {
    local backup_name=$1
    
    log_info "Restoring from backup: $backup_name"
    
    if [ ! -f "$BACKUP_DIR/$backup_name" ]; then
        log_error "Backup file $backup_name not found"
        return 1
    fi
    
    # Apply backup
    kubectl apply -f "$BACKUP_DIR/$backup_name" -n $NAMESPACE
    
    # Wait for restoration to complete
    kubectl rollout status deployment/auth-service -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/analytics-service -n $NAMESPACE --timeout=300s
    kubectl rollout status deployment/ai-detection-service -n $NAMESPACE --timeout=300s
    
    log_info "Restoration from backup completed"
}

# Find latest backup
find_latest_backup() {
    local latest_backup=$(ls -t $BACKUP_DIR/deployments_*.yaml 2>/dev/null | head -1)
    
    if [ -z "$latest_backup" ]; then
        log_error "No backup files found in $BACKUP_DIR"
        return 1
    fi
    
    echo "$latest_backup"
}

# Check data integrity
check_data_integrity() {
    log_info "Checking data integrity..."
    
    # Check database connectivity
    local db_pod=$(kubectl get pods -n $NAMESPACE -l app=database -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$db_pod" ]; then
        if kubectl exec $db_pod -n $NAMESPACE -- pg_isready; then
            log_info "Database connectivity verified"
        else
            log_error "Database connectivity failed"
            return 1
        fi
    fi
    
    # Check Redis connectivity
    local redis_pod=$(kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [ -n "$redis_pod" ]; then
        if kubectl exec $redis_pod -n $NAMESPACE -- redis-cli ping; then
            log_info "Redis connectivity verified"
        else
            log_error "Redis connectivity failed"
            return 1
        fi
    fi
    
    log_info "Data integrity check completed"
}

# Monitor recovery progress
monitor_recovery() {
    log_info "Monitoring recovery progress..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_debug "Recovery monitoring attempt $attempt/$max_attempts"
        
        local all_healthy=true
        local services=("auth-service" "analytics-service" "ai-detection-service")
        
        for service in "${services[@]}"; do
            if ! check_service_health $service; then
                all_healthy=false
                break
            fi
        done
        
        if $all_healthy; then
            log_info "All services are healthy"
            return 0
        fi
        
        log_debug "Waiting for services to become healthy... (attempt $attempt)"
        sleep 10
        ((attempt++))
    done
    
    log_error "Recovery monitoring timeout - services did not become healthy"
    return 1
}

# Perform health checks
perform_health_checks() {
    log_info "Performing comprehensive health checks..."
    
    # Check all services
    local services=("auth-service" "analytics-service" "ai-detection-service")
    local failed_services=()
    
    for service in "${services[@]}"; do
        if ! check_service_health $service; then
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        log_error "Failed services: ${failed_services[*]}"
        return 1
    fi
    
    # Check data integrity
    if ! check_data_integrity; then
        log_error "Data integrity check failed"
        return 1
    fi
    
    log_info "All health checks passed"
    return 0
}

# Main recovery procedure
main() {
    log_info "Starting disaster recovery procedure"
    
    # Initialize recovery log
    init_recovery_log
    
    # Check cluster health
    if ! check_cluster_health; then
        log_error "Cluster health check failed - manual intervention required"
        exit 1
    fi
    
    # Perform initial health check
    if perform_health_checks; then
        log_info "All services are healthy - no recovery needed"
        return 0
    fi
    
    # Scale services for recovery
    scale_services
    
    # Restart failed services
    if ! restart_failed_services; then
        log_warn "Service restart failed, attempting backup restoration"
        
        # Find and restore from latest backup
        local latest_backup=$(find_latest_backup)
        if [ -n "$latest_backup" ]; then
            restore_from_backup "$latest_backup"
        else
            log_error "No backup available for restoration"
            exit 1
        fi
    fi
    
    # Monitor recovery progress
    if ! monitor_recovery; then
        log_error "Recovery monitoring failed"
        exit 1
    fi
    
    # Final health check
    if ! perform_health_checks; then
        log_error "Final health check failed"
        exit 1
    fi
    
    log_info "Disaster recovery completed successfully!"
}

# Handle script arguments
case "${1:-recover}" in
    "recover")
        main
        ;;
    "check")
        check_cluster_health
        perform_health_checks
        ;;
    "scale")
        scale_services
        ;;
    "restart")
        restart_failed_services
        ;;
    "restore")
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 restore <backup-file>"
            exit 1
        fi
        restore_from_backup "$2"
        ;;
    "monitor")
        monitor_recovery
        ;;
    *)
        echo "Usage: $0 {recover|check|scale|restart|restore|monitor}"
        exit 1
        ;;
esac 