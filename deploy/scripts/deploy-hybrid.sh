#!/bin/bash

# Hybrid CPython/Codon Deployment Script
# This script deploys the hybrid architecture with proper error handling and rollback

set -euo pipefail

# Configuration
NAMESPACE="graphmemory"
DEPLOYMENT_FILE="hybrid-deployment-strategy.yaml"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_warn "Namespace $NAMESPACE does not exist, creating..."
        kubectl create namespace $NAMESPACE
    fi
    
    # Check if Istio is installed
    if ! kubectl get namespace istio-system &> /dev/null; then
        log_error "Istio is not installed. Please install Istio first."
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Create backup of current deployment
create_backup() {
    log_info "Creating backup of current deployment..."
    
    mkdir -p $BACKUP_DIR
    
    # Backup current deployments
    kubectl get deployments -n $NAMESPACE -o yaml > $BACKUP_DIR/deployments_$TIMESTAMP.yaml
    kubectl get services -n $NAMESPACE -o yaml > $BACKUP_DIR/services_$TIMESTAMP.yaml
    kubectl get virtualservices -n $NAMESPACE -o yaml > $BACKUP_DIR/virtualservices_$TIMESTAMP.yaml
    
    log_info "Backup created: $BACKUP_DIR/"
}

# Deploy CPython services
deploy_cpython_services() {
    log_info "Deploying CPython services..."
    
    # Deploy auth service
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=auth-service
    
    # Wait for auth service to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/auth-service -n $NAMESPACE
    
    log_info "CPython services deployed successfully"
}

# Deploy Codon services
deploy_codon_services() {
    log_info "Deploying Codon services..."
    
    # Deploy analytics service
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=analytics-service
    
    # Deploy AI detection service
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=ai-detection-service
    
    # Wait for Codon services to be ready
    kubectl wait --for=condition=available --timeout=600s deployment/analytics-service -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=600s deployment/ai-detection-service -n $NAMESPACE
    
    log_info "Codon services deployed successfully"
}

# Deploy infrastructure components
deploy_infrastructure() {
    log_info "Deploying infrastructure components..."
    
    # Deploy OpenTelemetry Collector
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=otel-collector
    
    # Deploy network policies
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=hybrid-app-network-policy
    
    # Deploy autoscalers
    kubectl apply -f $DEPLOYMENT_FILE -n $NAMESPACE --selector=app=HorizontalPodAutoscaler
    
    log_info "Infrastructure components deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if all pods are running
    local failed_pods=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running -o name)
    if [ -n "$failed_pods" ]; then
        log_error "Some pods are not running:"
        echo "$failed_pods"
        return 1
    fi
    
    # Check service endpoints
    local services=("auth-service" "analytics-service" "ai-detection-service")
    for service in "${services[@]}"; do
        local endpoints=$(kubectl get endpoints $service -n $NAMESPACE -o jsonpath='{.subsets[*].addresses[*].ip}')
        if [ -z "$endpoints" ]; then
            log_error "Service $service has no endpoints"
            return 1
        fi
    done
    
    # Check Istio Virtual Service
    kubectl get virtualservice hybrid-app -n $NAMESPACE
    
    log_info "Deployment verification passed"
}

# Health check
health_check() {
    log_info "Performing health checks..."
    
    # Get service URLs
    local auth_url=$(kubectl get service auth-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    local analytics_url=$(kubectl get service analytics-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    local ai_detection_url=$(kubectl get service ai-detection-service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    # Check health endpoints
    local services=(
        "auth-service:http://$auth_url:8000/health"
        "analytics-service:http://$analytics_url:8000/health"
        "ai-detection-service:http://$ai_detection_url:8000/health"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r service_name service_url <<< "$service_info"
        
        if curl -f -s "$service_url" > /dev/null; then
            log_info "$service_name is healthy"
        else
            log_error "$service_name health check failed"
            return 1
        fi
    done
    
    log_info "All health checks passed"
}

# Rollback function
rollback() {
    log_warn "Rolling back deployment..."
    
    # Find the most recent backup
    local latest_backup=$(ls -t $BACKUP_DIR/deployments_*.yaml | head -1)
    
    if [ -n "$latest_backup" ]; then
        log_info "Rolling back to: $latest_backup"
        kubectl apply -f "$latest_backup" -n $NAMESPACE
        
        # Wait for rollback to complete
        kubectl rollout status deployment/auth-service -n $NAMESPACE --timeout=300s
        kubectl rollout status deployment/analytics-service -n $NAMESPACE --timeout=300s
        kubectl rollout status deployment/ai-detection-service -n $NAMESPACE --timeout=300s
        
        log_info "Rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# Main deployment function
main() {
    log_info "Starting hybrid deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup
    create_backup
    
    # Deploy infrastructure first
    deploy_infrastructure
    
    # Deploy CPython services
    if ! deploy_cpython_services; then
        log_error "CPython services deployment failed"
        rollback
        exit 1
    fi
    
    # Deploy Codon services
    if ! deploy_codon_services; then
        log_error "Codon services deployment failed"
        rollback
        exit 1
    fi
    
    # Verify deployment
    if ! verify_deployment; then
        log_error "Deployment verification failed"
        rollback
        exit 1
    fi
    
    # Health check
    if ! health_check; then
        log_error "Health check failed"
        rollback
        exit 1
    fi
    
    log_info "Hybrid deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback
        ;;
    "verify")
        verify_deployment
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|verify|health}"
        exit 1
        ;;
esac 