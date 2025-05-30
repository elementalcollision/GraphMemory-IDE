# GraphMemory-IDE Deployment Guide

## 🎯 Overview

This comprehensive guide covers deploying GraphMemory-IDE in various environments, from local development to production-grade Kubernetes deployments. This guide includes the complete Phase 3 implementation with container orchestration, Kubernetes production deployment, and advanced operational features.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Quick Start Deployment](#quick-start-deployment)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Kubernetes Production Deployment](#kubernetes-production-deployment)
- [Advanced Configuration](#advanced-configuration)
- [Security & Hardening](#security--hardening)
- [Monitoring & Observability](#monitoring--observability)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)

## 🚀 Prerequisites

### System Requirements

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 2 cores | 4 cores | 8+ cores |
| **RAM** | 4GB | 8GB | 16GB+ |
| **Storage** | 20GB | 50GB | 100GB+ |
| **Network** | 1Gbps | 1Gbps | 10Gbps |

### Software Dependencies

```mermaid
flowchart TB
    subgraph "Development Environment"
        DOCKER[Docker 24.0+<br/>Container Runtime]
        COMPOSE[Docker Compose 2.0+<br/>Multi-container Apps]
        PYTHON[Python 3.11+<br/>Development]
    end
    
    subgraph "Production Environment"
        KUBERNETES[Kubernetes 1.28+<br/>Container Orchestration]
        KUBECTL[kubectl CLI<br/>Cluster Management]
        HELM[Helm 3.0+<br/>Package Manager]
    end
    
    subgraph "Monitoring Stack"
        PROMETHEUS[Prometheus<br/>Metrics Collection]
        GRAFANA[Grafana<br/>Dashboards]
        ALERTMANAGER[Alertmanager<br/>Alert Routing]
    end
    
    subgraph "Security Tools"
        TRIVY[Trivy<br/>Security Scanning]
        VAULT[HashiCorp Vault<br/>Secrets Management]
        CERT_MANAGER[Cert Manager<br/>TLS Automation]
    end
    
    DOCKER --> COMPOSE
    KUBERNETES --> KUBECTL
    KUBECTL --> HELM
    
    PROMETHEUS --> GRAFANA
    GRAFANA --> ALERTMANAGER
    
    TRIVY --> VAULT
    VAULT --> CERT_MANAGER
    
    style KUBERNETES fill:#326ce5,color:#fff
    style PROMETHEUS fill:#e6522c,color:#fff
    style VAULT fill:#000000,color:#fff
```

### Environment Preparation

```bash
# Verify required tools
docker --version
docker compose version
kubectl version --client
helm version

# Clone repository
git clone https://github.com/elementalcollision/GraphMemory-IDE.git
cd GraphMemory-IDE

# Verify system resources
df -h  # Check disk space
free -h  # Check memory
lscpu  # Check CPU cores
```

## 🔧 Deployment Options

### Deployment Strategy Matrix

```mermaid
flowchart TB
    subgraph "Development Stage"
        LOCAL_DEV[Local Development<br/>Docker Compose<br/>Single Developer]
        TEAM_DEV[Team Development<br/>Shared Environment<br/>Feature Testing]
    end
    
    subgraph "Testing Stage"
        INTEGRATION[Integration Testing<br/>Docker Compose<br/>CI/CD Pipeline]
        STAGING[Staging Environment<br/>Kubernetes<br/>Production-like]
    end
    
    subgraph "Production Stage"
        SINGLE_NODE[Single Node<br/>Docker Compose<br/>Small Scale]
        KUBERNETES_PROD[Kubernetes Production<br/>Multi-node Cluster<br/>High Availability]
        ENTERPRISE[Enterprise<br/>Multi-cluster<br/>Global Scale]
    end
    
    LOCAL_DEV --> INTEGRATION
    TEAM_DEV --> STAGING
    INTEGRATION --> SINGLE_NODE
    STAGING --> KUBERNETES_PROD
    SINGLE_NODE --> KUBERNETES_PROD
    KUBERNETES_PROD --> ENTERPRISE
    
    style LOCAL_DEV fill:#4caf50,color:#000
    style KUBERNETES_PROD fill:#326ce5,color:#fff
    style ENTERPRISE fill:#ff9800,color:#000
```

## 🚀 Quick Start Deployment

### Option 1: Docker Compose (Recommended for Development)

```bash
# Navigate to docker directory
cd docker

# Start all services with production config
docker compose up -d

# Verify services are running
docker compose ps
docker compose logs -f fastapi-backend
```

**Services Available:**
- FastAPI Backend: http://localhost:8080
- Streamlit Dashboard: http://localhost:8501
- Kestra CI/CD: http://localhost:8081
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Option 2: Kubernetes Quick Deploy

```bash
# Create namespace and apply manifests
kubectl create namespace graphmemory-prod
kubectl apply -f kubernetes/manifests/ -n graphmemory-prod

# Verify deployment
kubectl get pods -n graphmemory-prod
kubectl get services -n graphmemory-prod

# Check application status
kubectl logs -f deployment/fastapi-backend -n graphmemory-prod
```

### Option 3: Local Development

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:5432/graphmemory"
export REDIS_URL="redis://localhost:6379"

# Start services
python server/main.py
```

## 📦 Docker Compose Deployment

### Production Docker Compose

```mermaid
flowchart TB
    subgraph "Docker Compose Stack"
        subgraph "Application Services"
            FASTAPI[FastAPI Backend<br/>Production Image<br/>Health Checks]
            STREAMLIT[Streamlit Dashboard<br/>Real-time Features<br/>WebSocket Support]
            ANALYTICS[Analytics Engine<br/>ML Processing<br/>Graph Analytics]
        end
        
        subgraph "Data Services"
            POSTGRES[PostgreSQL 16<br/>Persistent Storage<br/>Replication Ready]
            REDIS[Redis 7<br/>Caching Layer<br/>Pub/Sub Support]
        end
        
        subgraph "Infrastructure"
            NGINX[NGINX Gateway<br/>Reverse Proxy<br/>SSL Termination]
            PROMETHEUS[Prometheus<br/>Metrics Collection<br/>Alert Rules]
            GRAFANA[Grafana<br/>Dashboards<br/>Visualization]
        end
    end
    
    NGINX --> FASTAPI
    NGINX --> STREAMLIT
    FASTAPI --> POSTGRES
    FASTAPI --> REDIS
    ANALYTICS --> POSTGRES
    PROMETHEUS --> FASTAPI
    PROMETHEUS --> POSTGRES
    GRAFANA --> PROMETHEUS
    
    style FASTAPI fill:#326ce5,color:#fff
    style POSTGRES fill:#336791,color:#fff
    style PROMETHEUS fill:#e6522c,color:#fff
```

### Docker Compose Configuration

```bash
# Production deployment with all features
cd docker
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With security scanning
docker compose -f docker-compose.yml -f docker-compose.security.yml up -d

# Development with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Compose Environment Configuration

```bash
# Create environment file
cat > .env << EOF
# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=info
DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/graphmemory
REDIS_URL=redis://redis:6379

# Security Configuration
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Performance Configuration
WORKERS=4
MAX_CONNECTIONS=100
CACHE_TTL=300

# Monitoring Configuration
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
EOF
```

## ☸️ Kubernetes Production Deployment

### Kubernetes Architecture Overview

```mermaid
flowchart TB
    subgraph "External Access"
        INTERNET[Internet Traffic]
        DNS[DNS Resolution]
        CDN[Content Delivery Network]
    end
    
    subgraph "Kubernetes Cluster"
        subgraph "Ingress Layer"
            GATEWAY_API[Gateway API<br/>NGINX Gateway Fabric<br/>TLS Termination]
            INGRESS_CTRL[Ingress Controller<br/>HTTP/HTTPS Routing<br/>Rate Limiting]
        end
        
        subgraph "Application Layer"
            FASTAPI_PODS[FastAPI Pods<br/>3 Replicas<br/>Auto-scaling]
            STREAMLIT_PODS[Streamlit Pods<br/>2 Replicas<br/>Session Affinity]
            ANALYTICS_PODS[Analytics Pods<br/>2 Replicas<br/>Resource Intensive]
        end
        
        subgraph "Data Layer"
            POSTGRES_SS[PostgreSQL StatefulSet<br/>Primary + Replicas<br/>Persistent Storage]
            REDIS_SS[Redis StatefulSet<br/>Cluster Mode<br/>High Availability]
        end
        
        subgraph "Monitoring"
            PROMETHEUS_STACK[Prometheus Stack<br/>Metrics & Alerts<br/>Service Discovery]
            GRAFANA_DASH[Grafana Dashboards<br/>Visualization<br/>Real-time Monitoring]
        end
    end
    
    INTERNET --> DNS
    DNS --> CDN
    CDN --> GATEWAY_API
    GATEWAY_API --> INGRESS_CTRL
    
    INGRESS_CTRL --> FASTAPI_PODS
    INGRESS_CTRL --> STREAMLIT_PODS
    FASTAPI_PODS --> ANALYTICS_PODS
    
    FASTAPI_PODS --> POSTGRES_SS
    ANALYTICS_PODS --> POSTGRES_SS
    FASTAPI_PODS --> REDIS_SS
    
    PROMETHEUS_STACK -.-> FASTAPI_PODS
    PROMETHEUS_STACK -.-> POSTGRES_SS
    GRAFANA_DASH --> PROMETHEUS_STACK
    
    style GATEWAY_API fill:#326ce5,color:#fff
    style POSTGRES_SS fill:#336791,color:#fff
    style PROMETHEUS_STACK fill:#e6522c,color:#fff
```

### Step-by-Step Kubernetes Deployment

#### 1. Namespace and RBAC Setup

```bash
# Create production namespace
kubectl apply -f kubernetes/manifests/namespace.yaml

# Verify namespace creation
kubectl get namespace graphmemory-prod

# Check RBAC configuration
kubectl get serviceaccounts -n graphmemory-prod
kubectl get roles,rolebindings -n graphmemory-prod
```

#### 2. Storage and StatefulSets

```bash
# Apply storage classes
kubectl apply -f kubernetes/manifests/storage-classes.yaml

# Deploy PostgreSQL StatefulSet
kubectl apply -f kubernetes/manifests/statefulsets.yaml

# Verify StatefulSet deployment
kubectl get statefulsets -n graphmemory-prod
kubectl get pvc -n graphmemory-prod

# Check PostgreSQL pods
kubectl get pods -l app=postgresql -n graphmemory-prod
kubectl logs postgresql-0 -n graphmemory-prod
```

#### 3. Application Deployments

```bash
# Deploy application services
kubectl apply -f kubernetes/manifests/deployments.yaml

# Verify deployments
kubectl get deployments -n graphmemory-prod
kubectl get pods -n graphmemory-prod

# Check application logs
kubectl logs -f deployment/fastapi-backend -n graphmemory-prod
kubectl logs -f deployment/streamlit-dashboard -n graphmemory-prod
```

#### 4. Networking and Ingress

```bash
# Apply Gateway API configuration
kubectl apply -f kubernetes/manifests/gateway-ingress.yaml

# Verify Gateway and HTTPRoutes
kubectl get gateway -n graphmemory-prod
kubectl get httproutes -n graphmemory-prod

# Check ingress status
kubectl describe gateway graphmemory-gateway -n graphmemory-prod
```

#### 5. Configuration and Secrets

```bash
# Apply ConfigMaps and Secrets
kubectl apply -f kubernetes/manifests/configmaps-secrets.yaml

# Verify configuration
kubectl get configmaps -n graphmemory-prod
kubectl get secrets -n graphmemory-prod

# Check configuration values
kubectl describe configmap app-config -n graphmemory-prod
```

#### 6. Auto-scaling Configuration

```bash
# Apply HPA and VPA
kubectl apply -f kubernetes/manifests/autoscaling.yaml

# Verify auto-scaling
kubectl get hpa -n graphmemory-prod
kubectl get vpa -n graphmemory-prod

# Check scaling metrics
kubectl top pods -n graphmemory-prod
kubectl describe hpa fastapi-backend-hpa -n graphmemory-prod
```

### Production Kubernetes Verification

```bash
# Complete deployment verification script
cat > verify-deployment.sh << 'EOF'
#!/bin/bash

NAMESPACE="graphmemory-prod"

echo "🔍 Verifying GraphMemory-IDE Kubernetes Deployment..."

# Check namespace
echo "📁 Checking namespace..."
kubectl get namespace $NAMESPACE

# Check StatefulSets
echo "📊 Checking StatefulSets..."
kubectl get statefulsets -n $NAMESPACE

# Check Deployments
echo "🚀 Checking Deployments..."
kubectl get deployments -n $NAMESPACE

# Check Services
echo "🌐 Checking Services..."
kubectl get services -n $NAMESPACE

# Check Ingress/Gateway
echo "🔗 Checking Gateway API..."
kubectl get gateway,httproutes -n $NAMESPACE

# Check Pods
echo "📦 Checking Pods..."
kubectl get pods -n $NAMESPACE

# Check Auto-scaling
echo "📈 Checking Auto-scaling..."
kubectl get hpa,vpa -n $NAMESPACE

# Check Storage
echo "💾 Checking Storage..."
kubectl get pvc -n $NAMESPACE

# Application Health
echo "🏥 Checking Application Health..."
kubectl get pods -n $NAMESPACE -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

echo "✅ Deployment verification complete!"
EOF

chmod +x verify-deployment.sh
./verify-deployment.sh
```

## ⚙️ Advanced Configuration

### Environment-specific Configurations

```mermaid
flowchart TB
    subgraph "Configuration Management"
        BASE_CONFIG[Base Configuration<br/>Common settings<br/>Default values]
        ENV_OVERLAYS[Environment Overlays<br/>Dev/Staging/Prod<br/>Specific overrides]
        SECRET_MGMT[Secret Management<br/>Encrypted secrets<br/>External vaults]
    end
    
    subgraph "Development"
        DEV_CONFIG[Development Config<br/>Debug enabled<br/>Hot reload]
        DEV_SECRETS[Development Secrets<br/>Local credentials<br/>Test data]
    end
    
    subgraph "Production"
        PROD_CONFIG[Production Config<br/>Optimized settings<br/>Security hardened]
        PROD_SECRETS[Production Secrets<br/>Vault integration<br/>Rotation policies]
    end
    
    BASE_CONFIG --> ENV_OVERLAYS
    ENV_OVERLAYS --> SECRET_MGMT
    
    ENV_OVERLAYS --> DEV_CONFIG
    ENV_OVERLAYS --> PROD_CONFIG
    SECRET_MGMT --> DEV_SECRETS
    SECRET_MGMT --> PROD_SECRETS
    
    style BASE_CONFIG fill:#4caf50,color:#000
    style PROD_CONFIG fill:#ff5722,color:#fff
    style SECRET_MGMT fill:#9c27b0,color:#fff
```

### Resource Configuration

```yaml
# Production resource configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: resource-config
  namespace: graphmemory-prod
data:
  cpu_limits: |
    fastapi: "1000m"
    streamlit: "500m"
    analytics: "2000m"
    postgresql: "2000m"
    redis: "500m"
  
  memory_limits: |
    fastapi: "2Gi"
    streamlit: "1Gi"
    analytics: "4Gi"
    postgresql: "4Gi"
    redis: "1Gi"
  
  scaling_config: |
    min_replicas: 2
    max_replicas: 10
    target_cpu: 70
    target_memory: 80
```

### Custom Resource Definitions

```bash
# Apply custom monitoring configuration
kubectl apply -f - << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: graphmemory-monitoring
  namespace: graphmemory-prod
spec:
  selector:
    matchLabels:
      app: graphmemory
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF
```

## 🔒 Security & Hardening

### Security Configuration

```mermaid
flowchart TB
    subgraph "Network Security"
        NETWORK_POLICIES[Network Policies<br/>Pod-to-pod rules<br/>Default deny]
        TLS_CONFIG[TLS Configuration<br/>End-to-end encryption<br/>Certificate management]
        FIREWALL_RULES[Firewall Rules<br/>Ingress filtering<br/>Egress control]
    end
    
    subgraph "Container Security"
        IMAGE_SCANNING[Image Scanning<br/>Vulnerability assessment<br/>Policy enforcement]
        RUNTIME_SECURITY[Runtime Security<br/>Non-root containers<br/>Read-only filesystems]
        RESOURCE_LIMITS[Resource Limits<br/>CPU/Memory quotas<br/>DoS prevention]
    end
    
    subgraph "Application Security"
        AUTH_CONFIG[Authentication<br/>JWT tokens<br/>RBAC enforcement]
        SECRET_ENCRYPTION[Secret Encryption<br/>At-rest encryption<br/>Transit encryption]
        AUDIT_LOGGING[Audit Logging<br/>Access logs<br/>Security events]
    end
    
    NETWORK_POLICIES --> IMAGE_SCANNING
    TLS_CONFIG --> RUNTIME_SECURITY
    FIREWALL_RULES --> RESOURCE_LIMITS
    
    IMAGE_SCANNING --> AUTH_CONFIG
    RUNTIME_SECURITY --> SECRET_ENCRYPTION
    RESOURCE_LIMITS --> AUDIT_LOGGING
    
    style NETWORK_POLICIES fill:#f44336,color:#fff
    style IMAGE_SCANNING fill:#ff5722,color:#fff
    style AUTH_CONFIG fill:#4caf50,color:#000
```

### Security Deployment Commands

```bash
# Apply security hardening
kubectl apply -f kubernetes/security/

# Enable Pod Security Standards
kubectl label namespace graphmemory-prod \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Apply Network Policies
kubectl apply -f kubernetes/manifests/network-policies.yaml

# Verify security configuration
kubectl get networkpolicies -n graphmemory-prod
kubectl get podsecuritypolicy
kubectl auth can-i --list --as=system:serviceaccount:graphmemory-prod:graphmemory-service-account
```

## 📊 Monitoring & Observability

### Monitoring Stack Deployment

```bash
# Deploy Prometheus and Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values kubernetes/monitoring/prometheus-values.yaml

# Install Grafana dashboards
kubectl apply -f kubernetes/monitoring/grafana-dashboards.yaml

# Verify monitoring stack
kubectl get pods -n monitoring
kubectl get services -n monitoring
```

### Custom Metrics Configuration

```yaml
# Custom ServiceMonitor for GraphMemory-IDE
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: graphmemory-metrics
  namespace: graphmemory-prod
spec:
  selector:
    matchLabels:
      app: graphmemory
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
    honorLabels: true
```

## 🎯 Performance Tuning

### Performance Optimization

```mermaid
flowchart TB
    subgraph "Application Optimization"
        CODE_OPTIMIZATION[Code Optimization<br/>Async operations<br/>Connection pooling]
        CACHING_STRATEGY[Caching Strategy<br/>Redis cache<br/>Query optimization]
        RESOURCE_TUNING[Resource Tuning<br/>CPU/Memory limits<br/>JVM parameters]
    end
    
    subgraph "Infrastructure Optimization"
        AUTO_SCALING[Auto-scaling<br/>HPA + VPA<br/>Cluster scaling]
        STORAGE_OPTIMIZATION[Storage Optimization<br/>SSD storage<br/>IOPS tuning]
        NETWORK_OPTIMIZATION[Network Optimization<br/>CNI optimization<br/>Load balancing]
    end
    
    subgraph "Database Optimization"
        DB_TUNING[Database Tuning<br/>Connection pooling<br/>Query optimization]
        INDEX_OPTIMIZATION[Index Optimization<br/>Query performance<br/>Statistics]
        REPLICATION_SETUP[Replication Setup<br/>Read replicas<br/>Load distribution]
    end
    
    CODE_OPTIMIZATION --> AUTO_SCALING
    CACHING_STRATEGY --> STORAGE_OPTIMIZATION
    RESOURCE_TUNING --> NETWORK_OPTIMIZATION
    
    AUTO_SCALING --> DB_TUNING
    STORAGE_OPTIMIZATION --> INDEX_OPTIMIZATION
    NETWORK_OPTIMIZATION --> REPLICATION_SETUP
    
    style CODE_OPTIMIZATION fill:#4caf50,color:#000
    style AUTO_SCALING fill:#ff9800,color:#000
    style DB_TUNING fill:#336791,color:#fff
```

### Performance Testing

```bash
# Load testing script
cat > load-test.sh << 'EOF'
#!/bin/bash

NAMESPACE="graphmemory-prod"
SERVICE_URL="http://$(kubectl get service fastapi-backend -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"

echo "🚀 Starting load test on $SERVICE_URL"

# Install k6 if not available
if ! command -v k6 &> /dev/null; then
    echo "Installing k6..."
    sudo apt-get update && sudo apt-get install k6
fi

# Run load test
k6 run --vus 50 --duration 5m - << EOT
import http from 'k6/http';
import { check, sleep } from 'k6';

export default function () {
  let response = http.get('${SERVICE_URL}/health');
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
EOT

echo "✅ Load test completed"
EOF

chmod +x load-test.sh
./load-test.sh
```

## 🔧 Troubleshooting

### Common Deployment Issues

```mermaid
flowchart TD
    subgraph "Pod Issues"
        POD_PENDING[Pod Pending<br/>Resource constraints<br/>Node selection]
        POD_CRASHLOOP[CrashLoopBackOff<br/>Application errors<br/>Health checks]
        POD_OOM[Out of Memory<br/>Resource limits<br/>Memory leaks]
    end
    
    subgraph "Service Issues"
        SERVICE_UNREACHABLE[Service Unreachable<br/>Networking<br/>DNS resolution]
        INGRESS_ISSUES[Ingress Issues<br/>Certificate problems<br/>Routing]
        LOAD_BALANCER[Load Balancer<br/>Health checks<br/>Backend registration]
    end
    
    subgraph "Storage Issues"
        PVC_PENDING[PVC Pending<br/>Storage class<br/>Provisioning]
        MOUNT_FAILURES[Mount Failures<br/>Permissions<br/>Path issues]
        DATA_CORRUPTION[Data Corruption<br/>Backup restore<br/>Integrity]
    end
    
    subgraph "Solutions"
        RESOURCE_INCREASE[Increase Resources<br/>CPU/Memory limits<br/>Node capacity]
        CONFIG_FIX[Fix Configuration<br/>Environment variables<br/>Secrets]
        STORAGE_FIX[Storage Fix<br/>Reclaim policy<br/>Backup restore]
    end
    
    POD_PENDING --> RESOURCE_INCREASE
    POD_CRASHLOOP --> CONFIG_FIX
    POD_OOM --> RESOURCE_INCREASE
    
    SERVICE_UNREACHABLE --> CONFIG_FIX
    INGRESS_ISSUES --> CONFIG_FIX
    LOAD_BALANCER --> RESOURCE_INCREASE
    
    PVC_PENDING --> STORAGE_FIX
    MOUNT_FAILURES --> CONFIG_FIX
    DATA_CORRUPTION --> STORAGE_FIX
    
    style POD_CRASHLOOP fill:#f44336,color:#fff
    style SERVICE_UNREACHABLE fill:#ff5722,color:#fff
    style DATA_CORRUPTION fill:#f44336,color:#fff
```

### Troubleshooting Commands

```bash
# Diagnostic script
cat > diagnose.sh << 'EOF'
#!/bin/bash

NAMESPACE="graphmemory-prod"

echo "🔍 GraphMemory-IDE Diagnostic Report"
echo "======================================"

# Cluster information
echo "📊 Cluster Information:"
kubectl cluster-info
kubectl get nodes

# Namespace resources
echo "📁 Namespace Resources:"
kubectl get all -n $NAMESPACE

# Pod details
echo "📦 Pod Details:"
kubectl describe pods -n $NAMESPACE

# Events
echo "📋 Recent Events:"
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'

# Resource usage
echo "📈 Resource Usage:"
kubectl top nodes
kubectl top pods -n $NAMESPACE

# Storage
echo "💾 Storage Status:"
kubectl get pv,pvc -n $NAMESPACE

# Network
echo "🌐 Network Status:"
kubectl get services,ingress,networkpolicies -n $NAMESPACE

echo "✅ Diagnostic complete"
EOF

chmod +x diagnose.sh
./diagnose.sh
```

This comprehensive deployment guide provides complete instructions for deploying GraphMemory-IDE from development to production with Kubernetes, including all Phase 3 Day 2 components like StatefulSets, Gateway API, auto-scaling, and monitoring. 