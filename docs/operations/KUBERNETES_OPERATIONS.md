# GraphMemory-IDE Kubernetes Operations Guide

## 🎯 Overview

This guide covers the operational aspects of managing GraphMemory-IDE in a production Kubernetes environment. It includes the complete Phase 3 Day 2 implementation with StatefulSets, Gateway API, auto-scaling, and advanced operational procedures.

## 📋 Table of Contents

- [Kubernetes Architecture Overview](#kubernetes-architecture-overview)
- [Resource Management](#resource-management)
- [Scaling Operations](#scaling-operations)
- [Network Management](#network-management)
- [Storage Operations](#storage-operations)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Security Operations](#security-operations)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## 🏗️ Kubernetes Architecture Overview

### Complete System Architecture

```mermaid
architecture-beta
    group cloud_provider(cloud)[Cloud Provider Infrastructure]
    group k8s_control(server)[Kubernetes Control Plane] in cloud_provider
    group worker_nodes(server)[Worker Nodes] in cloud_provider
    group data_tier(database)[Data Tier] in cloud_provider
    group networking(internet)[Networking Layer] in cloud_provider
    group monitoring(server)[Monitoring Stack] in cloud_provider

    service api_server(server)[kube-apiserver] in k8s_control
    service scheduler(server)[kube-scheduler] in k8s_control
    service controller(server)[kube-controller-manager] in k8s_control
    service etcd(database)[etcd cluster] in k8s_control

    service fastapi(server)[FastAPI Backend] in worker_nodes
    service streamlit(server)[Streamlit Dashboard] in worker_nodes
    service analytics(server)[Analytics Engine] in worker_nodes
    service gateway(internet)[NGINX Gateway] in worker_nodes

    service postgresql(database)[PostgreSQL StatefulSet] in data_tier
    service redis(database)[Redis StatefulSet] in data_tier
    service volumes(disk)[Persistent Volumes] in data_tier

    service gateway_api(internet)[Gateway API] in networking
    service ingress(internet)[Ingress Controller] in networking
    service network_policies(server)[Network Policies] in networking

    service prometheus(server)[Prometheus] in monitoring
    service grafana(server)[Grafana] in monitoring
    service alertmanager(server)[Alertmanager] in monitoring

    api_server:L -- R:fastapi
    scheduler:L -- R:fastapi
    controller:L -- R:postgresql
    etcd:L -- R:volumes

    gateway:T -- B:fastapi
    gateway:T -- B:streamlit
    analytics:B -- T:postgresql
    analytics:B -- T:redis

    gateway_api:L -- R:gateway
    ingress:L -- R:gateway_api
    
    prometheus:T -- B:fastapi
    prometheus:T -- B:postgresql
    grafana:L -- R:prometheus
```

### Namespace Organization

```mermaid
flowchart TB
    subgraph "Production Namespace"
        subgraph "Application Pods"
            FASTAPI[FastAPI Backend<br/>3 replicas]
            STREAMLIT[Streamlit Dashboard<br/>2 replicas]
            ANALYTICS[Analytics Engine<br/>2 replicas]
        end
        
        subgraph "Data StatefulSets"
            POSTGRES[PostgreSQL<br/>Primary + Replicas]
            REDIS[Redis<br/>Cluster Mode]
        end
        
        subgraph "Network Components"
            GATEWAY[Gateway API<br/>NGINX Fabric]
            INGRESS[Ingress Resources<br/>HTTP/HTTPS Routes]
            SERVICES[Services<br/>ClusterIP/LoadBalancer]
        end
    end
    
    subgraph "System Namespace"
        RBAC[RBAC<br/>Service Accounts]
        SECRETS[Secrets<br/>Configuration]
        CONFIGMAPS[ConfigMaps<br/>Application Config]
    end
    
    subgraph "Monitoring Namespace"
        PROMETHEUS[Prometheus<br/>Metrics Collection]
        GRAFANA[Grafana<br/>Dashboards]
        SERVICEMONITOR[ServiceMonitors<br/>Metric Discovery]
    end
    
    FASTAPI --> POSTGRES
    FASTAPI --> REDIS
    ANALYTICS --> POSTGRES
    STREAMLIT --> FASTAPI
    
    GATEWAY --> FASTAPI
    GATEWAY --> STREAMLIT
    INGRESS --> GATEWAY
    
    PROMETHEUS --> SERVICEMONITOR
    GRAFANA --> PROMETHEUS
    
    style FASTAPI fill:#326ce5,color:#fff
    style POSTGRES fill:#336791,color:#fff
    style REDIS fill:#dc382d,color:#fff
    style PROMETHEUS fill:#e6522c,color:#fff
```

## ⚙️ Resource Management

### Resource Quotas and Limits

```mermaid
flowchart TD
    subgraph "Namespace Quotas"
        QUOTA[Resource Quota<br/>graphmemory-prod]
        CPU_QUOTA[CPU: 4-8 cores]
        MEM_QUOTA[Memory: 8-16GB]
        STORAGE_QUOTA[Storage: 100GB]
        POD_QUOTA[Pods: 50 max]
    end
    
    subgraph "Application Limits"
        FASTAPI_LIMITS[FastAPI<br/>200m-1000m CPU<br/>512Mi-2Gi Memory]
        STREAMLIT_LIMITS[Streamlit<br/>100m-500m CPU<br/>256Mi-1Gi Memory]
        ANALYTICS_LIMITS[Analytics<br/>300m-2000m CPU<br/>1Gi-4Gi Memory]
    end
    
    subgraph "StatefulSet Limits"
        POSTGRES_LIMITS[PostgreSQL<br/>500m-2000m CPU<br/>1Gi-4Gi Memory<br/>20GB Storage]
        REDIS_LIMITS[Redis<br/>100m-500m CPU<br/>256Mi-1Gi Memory<br/>10GB Storage]
    end
    
    QUOTA --> CPU_QUOTA
    QUOTA --> MEM_QUOTA
    QUOTA --> STORAGE_QUOTA
    QUOTA --> POD_QUOTA
    
    CPU_QUOTA --> FASTAPI_LIMITS
    CPU_QUOTA --> STREAMLIT_LIMITS
    CPU_QUOTA --> ANALYTICS_LIMITS
    
    MEM_QUOTA --> POSTGRES_LIMITS
    MEM_QUOTA --> REDIS_LIMITS
    
    style QUOTA fill:#ff9800,color:#000
    style FASTAPI_LIMITS fill:#326ce5,color:#fff
    style POSTGRES_LIMITS fill:#336791,color:#fff
```

### Pod Affinity and Anti-Affinity

```mermaid
flowchart TB
    subgraph "Node 1"
        FASTAPI1[FastAPI Pod 1]
        POSTGRES_PRIMARY[PostgreSQL Primary]
    end
    
    subgraph "Node 2"
        FASTAPI2[FastAPI Pod 2]
        ANALYTICS1[Analytics Pod 1]
        REDIS1[Redis Pod 1]
    end
    
    subgraph "Node 3"
        FASTAPI3[FastAPI Pod 3]
        ANALYTICS2[Analytics Pod 2]
        POSTGRES_REPLICA[PostgreSQL Replica]
    end
    
    subgraph "Affinity Rules"
        DATABASE_AFFINITY[Database Affinity<br/>Analytics → PostgreSQL]
        ANTI_AFFINITY[Pod Anti-Affinity<br/>FastAPI spread across nodes]
        NODE_SELECTOR[Node Selector<br/>SSD nodes for databases]
    end
    
    DATABASE_AFFINITY -.-> ANALYTICS1
    DATABASE_AFFINITY -.-> POSTGRES_PRIMARY
    DATABASE_AFFINITY -.-> ANALYTICS2
    DATABASE_AFFINITY -.-> POSTGRES_REPLICA
    
    ANTI_AFFINITY -.-> FASTAPI1
    ANTI_AFFINITY -.-> FASTAPI2
    ANTI_AFFINITY -.-> FASTAPI3
    
    NODE_SELECTOR -.-> POSTGRES_PRIMARY
    NODE_SELECTOR -.-> POSTGRES_REPLICA
    NODE_SELECTOR -.-> REDIS1
    
    style DATABASE_AFFINITY fill:#4caf50,color:#000
    style ANTI_AFFINITY fill:#ff5722,color:#fff
    style NODE_SELECTOR fill:#2196f3,color:#fff
```

## 📊 Scaling Operations

### Horizontal Pod Autoscaler (HPA) Workflow

```mermaid
sequenceDiagram
    participant Metrics as Metrics Server
    participant HPA as HPA Controller
    participant Deployment as Deployment
    participant Pods as Application Pods
    participant Monitor as Monitoring

    Note over Metrics, Monitor: Auto-scaling Workflow

    Metrics->>HPA: CPU/Memory metrics (30s interval)
    HPA->>HPA: Calculate target replicas
    
    alt CPU > 70% (scale up)
        HPA->>Deployment: Increase replica count
        Deployment->>Pods: Create new pods
        Pods->>Monitor: Health check endpoints
        Monitor->>HPA: Confirm pods ready
    else CPU < 30% (scale down)
        HPA->>Deployment: Decrease replica count
        Deployment->>Pods: Terminate pods gracefully
        Pods->>Pods: 30s termination grace period
    end
    
    Note over HPA: Wait 3 min stabilization
    HPA->>Metrics: Next evaluation cycle
```

### Vertical Pod Autoscaler (VPA) Workflow

```mermaid
flowchart TD
    subgraph "VPA Components"
        VPA_CONTROLLER[VPA Controller<br/>Recommendations]
        VPA_RECOMMENDER[VPA Recommender<br/>Resource Analysis]
        VPA_UPDATER[VPA Updater<br/>Pod Restart]
        VPA_ADMISSION[VPA Admission Controller<br/>Resource Injection]
    end
    
    subgraph "Application Workloads"
        FASTAPI_VPA[FastAPI VPA<br/>Off mode - recommendations only]
        ANALYTICS_VPA[Analytics VPA<br/>Auto mode - apply changes]
        POSTGRES_VPA[PostgreSQL VPA<br/>Initial mode - set once]
    end
    
    subgraph "Resource Monitoring"
        METRICS[Metrics Server<br/>CPU/Memory Usage]
        HISTORY[Historical Data<br/>8 days retention]
        RECOMMENDATIONS[Resource Recommendations<br/>Request/Limit suggestions]
    end
    
    METRICS --> VPA_RECOMMENDER
    VPA_RECOMMENDER --> HISTORY
    HISTORY --> RECOMMENDATIONS
    RECOMMENDATIONS --> VPA_CONTROLLER
    
    VPA_CONTROLLER --> FASTAPI_VPA
    VPA_CONTROLLER --> ANALYTICS_VPA
    VPA_CONTROLLER --> POSTGRES_VPA
    
    VPA_UPDATER -.-> ANALYTICS_VPA
    VPA_ADMISSION -.-> POSTGRES_VPA
    
    style VPA_CONTROLLER fill:#4caf50,color:#000
    style ANALYTICS_VPA fill:#ff9800,color:#000
    style RECOMMENDATIONS fill:#2196f3,color:#fff
```

### Combined HPA + VPA Strategy

```mermaid
flowchart TB
    subgraph "Scaling Strategy"
        HPA_ZONE[HPA Zone<br/>Scale replicas 1-10<br/>Based on CPU/Memory]
        VPA_ZONE[VPA Zone<br/>Optimize resources<br/>Based on usage patterns]
        MANUAL_ZONE[Manual Zone<br/>Override scaling<br/>Special events]
    end
    
    subgraph "Application Tiers"
        FRONTEND[Frontend Tier<br/>Streamlit Dashboard]
        BACKEND[Backend Tier<br/>FastAPI Services]
        ANALYTICS[Analytics Tier<br/>Processing Engine]
        DATA[Data Tier<br/>StatefulSets]
    end
    
    subgraph "Scaling Triggers"
        CPU_TRIGGER[CPU > 70%<br/>Scale out]
        MEMORY_TRIGGER[Memory > 80%<br/>Scale out]
        REQUEST_TRIGGER[Requests > 1000/min<br/>Scale out]
        CUSTOM_TRIGGER[Custom Metrics<br/>Queue depth, response time]
    end
    
    HPA_ZONE --> FRONTEND
    HPA_ZONE --> BACKEND
    
    VPA_ZONE --> ANALYTICS
    VPA_ZONE --> BACKEND
    
    MANUAL_ZONE --> DATA
    
    CPU_TRIGGER --> HPA_ZONE
    MEMORY_TRIGGER --> HPA_ZONE
    REQUEST_TRIGGER --> HPA_ZONE
    CUSTOM_TRIGGER --> HPA_ZONE
    
    style HPA_ZONE fill:#4caf50,color:#000
    style VPA_ZONE fill:#ff9800,color:#000
    style MANUAL_ZONE fill:#f44336,color:#fff
```

## 🌐 Network Management

### Gateway API Architecture

```mermaid
flowchart TB
    subgraph "External Traffic"
        INTERNET[Internet Traffic]
        DNS[DNS Resolution<br/>graphmemory.example.com]
        CDN[CloudFlare CDN<br/>Static Assets]
    end
    
    subgraph "Gateway Layer"
        GATEWAY_CLASS[GatewayClass<br/>nginx-gateway-fabric]
        GATEWAY[Gateway<br/>graphmemory-gateway]
        HTTP_LISTENER[HTTP Listener<br/>Port 80 → HTTPS redirect]
        HTTPS_LISTENER[HTTPS Listener<br/>Port 443 → TLS termination]
        API_LISTENER[API Listener<br/>Port 8443 → API traffic]
    end
    
    subgraph "Routing Layer"
        DASHBOARD_ROUTE[HTTPRoute<br/>/ → Dashboard]
        API_ROUTE[HTTPRoute<br/>/api → Backend]
        WS_ROUTE[HTTPRoute<br/>/ws → WebSocket]
        HEALTH_ROUTE[HTTPRoute<br/>/health → Health checks]
    end
    
    subgraph "Service Layer"
        STREAMLIT_SVC[Streamlit Service<br/>ClusterIP]
        FASTAPI_SVC[FastAPI Service<br/>ClusterIP]
        ANALYTICS_SVC[Analytics Service<br/>ClusterIP]
    end
    
    subgraph "Security Policies"
        RATE_LIMIT[Rate Limiting<br/>100-300 req/min]
        CORS_POLICY[CORS Policy<br/>API access control]
        TLS_POLICY[TLS Policy<br/>Certificate management]
        NETWORK_POLICY[Network Policies<br/>Pod-to-pod communication]
    end
    
    INTERNET --> DNS
    DNS --> CDN
    CDN --> GATEWAY
    
    GATEWAY --> HTTP_LISTENER
    GATEWAY --> HTTPS_LISTENER
    GATEWAY --> API_LISTENER
    
    HTTP_LISTENER --> DASHBOARD_ROUTE
    HTTPS_LISTENER --> DASHBOARD_ROUTE
    HTTPS_LISTENER --> API_ROUTE
    API_LISTENER --> WS_ROUTE
    
    DASHBOARD_ROUTE --> STREAMLIT_SVC
    API_ROUTE --> FASTAPI_SVC
    WS_ROUTE --> ANALYTICS_SVC
    
    GATEWAY --> RATE_LIMIT
    GATEWAY --> CORS_POLICY
    GATEWAY --> TLS_POLICY
    NETWORK_POLICY --> STREAMLIT_SVC
    NETWORK_POLICY --> FASTAPI_SVC
    
    style GATEWAY fill:#326ce5,color:#fff
    style RATE_LIMIT fill:#ff5722,color:#fff
    style TLS_POLICY fill:#4caf50,color:#000
```

### Network Policies and Security

```mermaid
flowchart TD
    subgraph "Default Deny Policy"
        DENY_ALL[Deny All Ingress<br/>Default namespace policy]
        DENY_EGRESS[Deny All Egress<br/>Strict outbound control]
    end
    
    subgraph "Application Network Policies"
        FRONTEND_POLICY[Frontend Policy<br/>Allow: Gateway → Streamlit]
        BACKEND_POLICY[Backend Policy<br/>Allow: Gateway + Frontend → FastAPI]
        ANALYTICS_POLICY[Analytics Policy<br/>Allow: Backend → Analytics]
        DATABASE_POLICY[Database Policy<br/>Allow: Backend + Analytics → DB]
    end
    
    subgraph "System Network Policies"
        MONITORING_POLICY[Monitoring Policy<br/>Allow: Prometheus scraping]
        DNS_POLICY[DNS Policy<br/>Allow: DNS resolution]
        EGRESS_POLICY[Egress Policy<br/>Allow: External APIs]
    end
    
    subgraph "Allowed Traffic Flows"
        INGRESS_FLOW[Internet → Gateway → Apps]
        INTERNAL_FLOW[App → App communication]
        DATABASE_FLOW[Apps → Databases]
        MONITORING_FLOW[Prometheus → All endpoints]
        EGRESS_FLOW[Apps → External services]
    end
    
    DENY_ALL --> FRONTEND_POLICY
    DENY_ALL --> BACKEND_POLICY
    DENY_ALL --> ANALYTICS_POLICY
    DENY_ALL --> DATABASE_POLICY
    
    FRONTEND_POLICY --> INGRESS_FLOW
    BACKEND_POLICY --> INTERNAL_FLOW
    DATABASE_POLICY --> DATABASE_FLOW
    
    MONITORING_POLICY --> MONITORING_FLOW
    EGRESS_POLICY --> EGRESS_FLOW
    
    style DENY_ALL fill:#f44336,color:#fff
    style FRONTEND_POLICY fill:#4caf50,color:#000
    style MONITORING_POLICY fill:#ff9800,color:#000
```

## 💾 Storage Operations

### Persistent Volume Management

```mermaid
flowchart TB
    subgraph "Storage Classes"
        FAST_SSD[fast-ssd<br/>High IOPS storage<br/>For databases]
        STANDARD[standard<br/>Standard SSD<br/>For application data]
        BACKUP[backup-storage<br/>Slow/cheap storage<br/>For backups]
    end
    
    subgraph "PostgreSQL Storage"
        PG_PVC[PostgreSQL PVC<br/>20GB fast-ssd<br/>VolumeClaimTemplate]
        PG_PV[PostgreSQL PV<br/>Dynamically provisioned<br/>Reclaim policy: Retain]
        PG_BACKUP[PostgreSQL Backup<br/>Daily snapshots<br/>backup-storage class]
    end
    
    subgraph "Redis Storage"
        REDIS_PVC[Redis PVC<br/>10GB fast-ssd<br/>VolumeClaimTemplate]
        REDIS_PV[Redis PV<br/>Dynamically provisioned<br/>Reclaim policy: Retain]
        REDIS_CONFIG[Redis Config<br/>AOF persistence<br/>LRU eviction]
    end
    
    subgraph "Application Storage"
        APP_CONFIG[Config Storage<br/>ConfigMaps + Secrets<br/>Application configuration]
        APP_LOGS[Log Storage<br/>EmptyDir volumes<br/>Temporary log files]
        APP_CACHE[Cache Storage<br/>EmptyDir volumes<br/>Temporary cache files]
    end
    
    subgraph "Backup Strategy"
        VOLUME_SNAPSHOTS[Volume Snapshots<br/>Point-in-time recovery<br/>CSI snapshots]
        AUTOMATED_BACKUP[Automated Backups<br/>CronJob schedules<br/>velero/external tools]
        DISASTER_RECOVERY[Disaster Recovery<br/>Cross-region replication<br/>RTO: 4 hours, RPO: 1 hour]
    end
    
    FAST_SSD --> PG_PVC
    FAST_SSD --> REDIS_PVC
    STANDARD --> APP_CONFIG
    BACKUP --> PG_BACKUP
    
    PG_PVC --> PG_PV
    REDIS_PVC --> REDIS_PV
    
    PG_PV --> VOLUME_SNAPSHOTS
    REDIS_PV --> VOLUME_SNAPSHOTS
    VOLUME_SNAPSHOTS --> AUTOMATED_BACKUP
    AUTOMATED_BACKUP --> DISASTER_RECOVERY
    
    style FAST_SSD fill:#ff5722,color:#fff
    style PG_PV fill:#336791,color:#fff
    style VOLUME_SNAPSHOTS fill:#4caf50,color:#000
```

### StatefulSet Scaling Operations

```mermaid
sequenceDiagram
    participant Operator as Kubernetes Operator
    participant StatefulSet as StatefulSet Controller
    participant Pods as StatefulSet Pods
    participant Storage as Persistent Volumes
    participant Database as Database Cluster

    Note over Operator, Database: StatefulSet Scaling Workflow

    Operator->>StatefulSet: Scale replicas: 1 → 3
    StatefulSet->>Storage: Create PVC for pod-1
    Storage->>Storage: Provision volume
    
    StatefulSet->>Pods: Create pod-1 (replica)
    Pods->>Database: Initialize as replica
    Database->>Database: Start replication from primary
    
    loop Health Check
        StatefulSet->>Pods: Check pod-1 readiness
        Pods->>Database: Verify replication lag
        Database-->>Pods: Replication healthy
    end
    
    StatefulSet->>Storage: Create PVC for pod-2
    Storage->>Storage: Provision volume
    StatefulSet->>Pods: Create pod-2 (replica)
    
    Note over Database: All replicas running
    Database->>Operator: Scaling complete
```

## 📊 Monitoring and Alerting

### Prometheus Monitoring Architecture

```mermaid
flowchart TB
    subgraph "Metrics Collection"
        PROMETHEUS[Prometheus Server<br/>Metrics storage & queries]
        SERVICE_MONITORS[ServiceMonitors<br/>Automatic target discovery]
        POD_MONITORS[PodMonitors<br/>Pod-level metrics]
        PROBES[Probes<br/>Blackbox monitoring]
    end
    
    subgraph "Application Metrics"
        FASTAPI_METRICS[FastAPI Metrics<br/>Request rate, latency, errors<br/>Custom business metrics]
        STREAMLIT_METRICS[Streamlit Metrics<br/>Session metrics, user activity<br/>Component performance]
        ANALYTICS_METRICS[Analytics Metrics<br/>Processing time, queue depth<br/>Algorithm performance]
    end
    
    subgraph "Infrastructure Metrics"
        NODE_METRICS[Node Metrics<br/>CPU, memory, disk, network<br/>Kubernetes resource usage]
        POSTGRES_METRICS[PostgreSQL Metrics<br/>Connection count, query time<br/>Replication lag, cache hit ratio]
        REDIS_METRICS[Redis Metrics<br/>Memory usage, key count<br/>Command statistics]
    end
    
    subgraph "Alerting Pipeline"
        ALERTMANAGER[Alertmanager<br/>Alert routing & notification]
        SLACK_ALERTS[Slack Notifications<br/>Critical alerts]
        EMAIL_ALERTS[Email Notifications<br/>Warning alerts]
        PAGERDUTY[PagerDuty Integration<br/>On-call escalation]
    end
    
    subgraph "Dashboards"
        GRAFANA[Grafana Dashboards<br/>Visualization & analysis]
        BUSINESS_DASH[Business Dashboard<br/>User metrics, revenue impact]
        TECHNICAL_DASH[Technical Dashboard<br/>System health, performance]
        SRE_DASH[SRE Dashboard<br/>SLI/SLO tracking, error budgets]
    end
    
    SERVICE_MONITORS --> FASTAPI_METRICS
    SERVICE_MONITORS --> STREAMLIT_METRICS
    SERVICE_MONITORS --> ANALYTICS_METRICS
    
    POD_MONITORS --> NODE_METRICS
    POD_MONITORS --> POSTGRES_METRICS
    POD_MONITORS --> REDIS_METRICS
    
    PROMETHEUS --> SERVICE_MONITORS
    PROMETHEUS --> POD_MONITORS
    PROMETHEUS --> PROBES
    
    PROMETHEUS --> ALERTMANAGER
    ALERTMANAGER --> SLACK_ALERTS
    ALERTMANAGER --> EMAIL_ALERTS
    ALERTMANAGER --> PAGERDUTY
    
    PROMETHEUS --> GRAFANA
    GRAFANA --> BUSINESS_DASH
    GRAFANA --> TECHNICAL_DASH
    GRAFANA --> SRE_DASH
    
    style PROMETHEUS fill:#e6522c,color:#fff
    style ALERTMANAGER fill:#ff5722,color:#fff
    style GRAFANA fill:#f46800,color:#fff
```

### SLI/SLO Monitoring

```mermaid
flowchart TD
    subgraph "Service Level Indicators (SLIs)"
        AVAILABILITY[Availability SLI<br/>Uptime percentage<br/>Target: 99.9%]
        LATENCY[Latency SLI<br/>Request response time<br/>Target: P95 < 500ms]
        ERROR_RATE[Error Rate SLI<br/>Failed requests<br/>Target: < 0.1%]
        THROUGHPUT[Throughput SLI<br/>Requests per second<br/>Target: > 1000 RPS]
    end
    
    subgraph "Service Level Objectives (SLOs)"
        MONTHLY_SLO[Monthly SLO<br/>99.9% availability<br/>Error budget: 43.2 min/month]
        WEEKLY_SLO[Weekly SLO<br/>P95 latency < 500ms<br/>95% of time windows]
        DAILY_SLO[Daily SLO<br/>Error rate < 0.1%<br/>Rolling 24h window]
    end
    
    subgraph "Error Budget Management"
        BUDGET_TRACKING[Error Budget Tracking<br/>Real-time consumption<br/>Burn rate alerts]
        BUDGET_ALERTS[Budget Alerts<br/>25%, 50%, 75%, 90% consumption<br/>Progressive escalation]
        INCIDENT_RESPONSE[Incident Response<br/>Auto-trigger when budget exhausted<br/>Feature freeze protocols]
    end
    
    subgraph "SLO Alerting"
        FAST_BURN[Fast Burn Alert<br/>Error budget consumed rapidly<br/>Page immediately]
        SLOW_BURN[Slow Burn Alert<br/>Gradual budget consumption<br/>Warning notification]
        BUDGET_EXHAUSTED[Budget Exhausted<br/>SLO violation<br/>Critical incident]
    end
    
    AVAILABILITY --> MONTHLY_SLO
    LATENCY --> WEEKLY_SLO
    ERROR_RATE --> DAILY_SLO
    
    MONTHLY_SLO --> BUDGET_TRACKING
    WEEKLY_SLO --> BUDGET_TRACKING
    DAILY_SLO --> BUDGET_TRACKING
    
    BUDGET_TRACKING --> BUDGET_ALERTS
    BUDGET_ALERTS --> FAST_BURN
    BUDGET_ALERTS --> SLOW_BURN
    BUDGET_ALERTS --> BUDGET_EXHAUSTED
    
    BUDGET_EXHAUSTED --> INCIDENT_RESPONSE
    
    style AVAILABILITY fill:#4caf50,color:#000
    style MONTHLY_SLO fill:#2196f3,color:#fff
    style BUDGET_EXHAUSTED fill:#f44336,color:#fff
```

## 🔒 Security Operations

### RBAC and Access Control

```mermaid
flowchart TB
    subgraph "Service Accounts"
        GRAPHMEMORY_SA[graphmemory-service-account<br/>Application runtime permissions]
        MONITORING_SA[monitoring-service-account<br/>Metrics collection permissions]
        BACKUP_SA[backup-service-account<br/>Backup operation permissions]
    end
    
    subgraph "Roles and ClusterRoles"
        APP_ROLE[graphmemory-app-role<br/>ConfigMaps, Secrets read<br/>Pod management]
        MONITORING_ROLE[monitoring-cluster-role<br/>Metrics endpoints access<br/>Node and pod stats]
        BACKUP_ROLE[backup-role<br/>Volume snapshot creation<br/>PVC management]
    end
    
    subgraph "RoleBindings"
        APP_BINDING[App RoleBinding<br/>Bind service account to role<br/>Namespace scoped]
        MONITORING_BINDING[Monitoring ClusterRoleBinding<br/>Cluster-wide monitoring access<br/>Read-only permissions]
        BACKUP_BINDING[Backup RoleBinding<br/>Backup operations<br/>Scheduled job permissions]
    end
    
    subgraph "Security Policies"
        POD_SECURITY[Pod Security Standards<br/>Restricted profile<br/>No privileged containers]
        NETWORK_SECURITY[Network Security<br/>Default deny all<br/>Explicit allow policies]
        ADMISSION_SECURITY[Admission Controllers<br/>Policy enforcement<br/>Resource validation]
    end
    
    GRAPHMEMORY_SA --> APP_ROLE
    MONITORING_SA --> MONITORING_ROLE
    BACKUP_SA --> BACKUP_ROLE
    
    APP_ROLE --> APP_BINDING
    MONITORING_ROLE --> MONITORING_BINDING
    BACKUP_ROLE --> BACKUP_BINDING
    
    APP_BINDING --> POD_SECURITY
    MONITORING_BINDING --> NETWORK_SECURITY
    BACKUP_BINDING --> ADMISSION_SECURITY
    
    style GRAPHMEMORY_SA fill:#4caf50,color:#000
    style POD_SECURITY fill:#ff5722,color:#fff
    style NETWORK_SECURITY fill:#f44336,color:#fff
```

### Secrets Management

```mermaid
flowchart TD
    subgraph "Secret Sources"
        EXTERNAL_SECRETS[External Secrets Operator<br/>HashiCorp Vault integration<br/>AWS Secrets Manager]
        SEALED_SECRETS[Sealed Secrets<br/>GitOps-friendly<br/>Encrypted in git]
        CERT_MANAGER[Cert Manager<br/>TLS certificate automation<br/>Let's Encrypt integration]
    end
    
    subgraph "Secret Types"
        DATABASE_SECRETS[Database Secrets<br/>PostgreSQL passwords<br/>Redis auth tokens]
        API_SECRETS[API Secrets<br/>JWT signing keys<br/>External API tokens]
        TLS_SECRETS[TLS Secrets<br/>HTTPS certificates<br/>mTLS client certs]
        CONFIG_SECRETS[Config Secrets<br/>Application configuration<br/>Environment variables]
    end
    
    subgraph "Secret Rotation"
        AUTOMATED_ROTATION[Automated Rotation<br/>30-day certificate rotation<br/>90-day password rotation]
        MANUAL_ROTATION[Manual Rotation<br/>Emergency rotation procedures<br/>Incident response]
        ROTATION_MONITORING[Rotation Monitoring<br/>Expiry alerts<br/>Rotation success tracking]
    end
    
    subgraph "Secret Access"
        VOLUME_MOUNTS[Volume Mounts<br/>File-based secret access<br/>Automatic updates]
        ENV_VARIABLES[Environment Variables<br/>Direct injection<br/>Pod restart for updates]
        INIT_CONTAINERS[Init Containers<br/>Secret preparation<br/>Validation before start]
    end
    
    EXTERNAL_SECRETS --> DATABASE_SECRETS
    SEALED_SECRETS --> API_SECRETS
    CERT_MANAGER --> TLS_SECRETS
    EXTERNAL_SECRETS --> CONFIG_SECRETS
    
    DATABASE_SECRETS --> AUTOMATED_ROTATION
    API_SECRETS --> AUTOMATED_ROTATION
    TLS_SECRETS --> AUTOMATED_ROTATION
    
    AUTOMATED_ROTATION --> ROTATION_MONITORING
    MANUAL_ROTATION --> ROTATION_MONITORING
    
    DATABASE_SECRETS --> VOLUME_MOUNTS
    API_SECRETS --> ENV_VARIABLES
    TLS_SECRETS --> VOLUME_MOUNTS
    CONFIG_SECRETS --> INIT_CONTAINERS
    
    style EXTERNAL_SECRETS fill:#4caf50,color:#000
    style AUTOMATED_ROTATION fill:#ff9800,color:#000
    style ROTATION_MONITORING fill:#2196f3,color:#fff
```

## 💾 Backup and Recovery

### Backup Strategy

```mermaid
flowchart TB
    subgraph "Backup Types"
        VOLUME_SNAPSHOTS[Volume Snapshots<br/>CSI driver snapshots<br/>Point-in-time recovery]
        DATABASE_DUMPS[Database Dumps<br/>pg_dump for PostgreSQL<br/>BGSAVE for Redis]
        CONFIG_BACKUP[Configuration Backup<br/>YAML manifests<br/>Secrets and ConfigMaps]
        APPLICATION_BACKUP[Application Backup<br/>Code repositories<br/>Build artifacts]
    end
    
    subgraph "Backup Schedule"
        HOURLY[Hourly Backups<br/>Volume snapshots<br/>Last 24 hours]
        DAILY[Daily Backups<br/>Database dumps<br/>Last 30 days]
        WEEKLY[Weekly Backups<br/>Full system backup<br/>Last 12 weeks]
        MONTHLY[Monthly Backups<br/>Archive backup<br/>Long-term retention]
    end
    
    subgraph "Backup Storage"
        LOCAL_STORAGE[Local Storage<br/>Fast recovery<br/>Same cluster]
        REMOTE_STORAGE[Remote Storage<br/>Disaster recovery<br/>Different region]
        ARCHIVE_STORAGE[Archive Storage<br/>Compliance<br/>Glacier/cold storage]
    end
    
    subgraph "Recovery Procedures"
        POINT_IN_TIME[Point-in-Time Recovery<br/>Restore to specific moment<br/>Volume snapshot + WAL replay]
        FULL_RESTORE[Full System Restore<br/>Complete cluster recreation<br/>Multi-component coordination]
        PARTIAL_RESTORE[Partial Restore<br/>Individual component recovery<br/>Minimal downtime]
        CROSS_REGION[Cross-Region Recovery<br/>Disaster recovery<br/>RTO: 4 hours, RPO: 1 hour]
    end
    
    VOLUME_SNAPSHOTS --> HOURLY
    DATABASE_DUMPS --> DAILY
    CONFIG_BACKUP --> WEEKLY
    APPLICATION_BACKUP --> MONTHLY
    
    HOURLY --> LOCAL_STORAGE
    DAILY --> REMOTE_STORAGE
    WEEKLY --> REMOTE_STORAGE
    MONTHLY --> ARCHIVE_STORAGE
    
    LOCAL_STORAGE --> POINT_IN_TIME
    REMOTE_STORAGE --> FULL_RESTORE
    REMOTE_STORAGE --> PARTIAL_RESTORE
    ARCHIVE_STORAGE --> CROSS_REGION
    
    style VOLUME_SNAPSHOTS fill:#4caf50,color:#000
    style DAILY fill:#ff9800,color:#000
    style POINT_IN_TIME fill:#2196f3,color:#fff
```

### Disaster Recovery Workflow

```mermaid
sequenceDiagram
    participant Incident as Incident Detection
    participant OnCall as On-Call Engineer
    participant Backup as Backup System
    participant K8s as Kubernetes Cluster
    participant Monitor as Monitoring
    participant Stakeholders as Stakeholders

    Note over Incident, Stakeholders: Disaster Recovery Workflow

    Incident->>Monitor: System failure detected
    Monitor->>OnCall: Alert notification (PagerDuty)
    OnCall->>OnCall: Assess incident severity
    
    alt Major Incident (RTO activated)
        OnCall->>Stakeholders: Incident declared
        OnCall->>Backup: Initiate recovery procedure
        Backup->>K8s: Restore from latest backup
        
        loop Recovery Process
            K8s->>Monitor: Recovery status updates
            Monitor->>OnCall: Progress notifications
            OnCall->>Stakeholders: Status updates
        end
        
        K8s->>Monitor: System health check
        Monitor->>OnCall: Recovery validation
        OnCall->>Stakeholders: Service restored
        
    else Minor Incident (standard recovery)
        OnCall->>K8s: Standard troubleshooting
        K8s->>Monitor: Issue resolution
        Monitor->>OnCall: Confirmation
    end
    
    Note over OnCall: Post-incident review
    OnCall->>Stakeholders: Incident report
```

## 🔧 Troubleshooting

### Common Issues and Solutions

```mermaid
flowchart TD
    subgraph "Pod Issues"
        POD_PENDING[Pod Pending<br/>Resource constraints<br/>Node selector mismatch]
        POD_CRASHLOOP[CrashLoopBackOff<br/>Application errors<br/>Health check failures]
        POD_OOM[OutOfMemory<br/>Insufficient memory limits<br/>Memory leaks]
        POD_IMAGEPULL[ImagePullBackOff<br/>Registry access<br/>Image not found]
    end
    
    subgraph "Service Issues"
        SERVICE_UNREACHABLE[Service Unreachable<br/>Endpoint mismatch<br/>Network policies]
        SERVICE_SLOW[Slow Response<br/>Resource limitations<br/>Database performance]
        SERVICE_502[502 Bad Gateway<br/>Upstream failures<br/>Health check issues]
        SERVICE_SSL[SSL/TLS Issues<br/>Certificate problems<br/>Gateway configuration]
    end
    
    subgraph "Storage Issues"
        PVC_PENDING[PVC Pending<br/>Storage class issues<br/>Insufficient capacity]
        VOLUME_MOUNT[Volume Mount Failures<br/>Permission issues<br/>Path conflicts]
        DATA_CORRUPTION[Data Corruption<br/>Backup restoration<br/>Integrity checks]
        PERFORMANCE_SLOW[Slow I/O Performance<br/>Storage class optimization<br/>IOPS limitations]
    end
    
    subgraph "Diagnostic Commands"
        KUBECTL_DESCRIBE[kubectl describe<br/>Event inspection<br/>Resource details]
        KUBECTL_LOGS[kubectl logs<br/>Application logs<br/>Previous container logs]
        KUBECTL_EXEC[kubectl exec<br/>Container debugging<br/>Interactive troubleshooting]
        KUBECTL_TOP[kubectl top<br/>Resource usage<br/>Performance metrics]
    end
    
    POD_PENDING --> KUBECTL_DESCRIBE
    POD_CRASHLOOP --> KUBECTL_LOGS
    POD_OOM --> KUBECTL_TOP
    POD_IMAGEPULL --> KUBECTL_DESCRIBE
    
    SERVICE_UNREACHABLE --> KUBECTL_DESCRIBE
    SERVICE_SLOW --> KUBECTL_TOP
    SERVICE_502 --> KUBECTL_LOGS
    SERVICE_SSL --> KUBECTL_DESCRIBE
    
    PVC_PENDING --> KUBECTL_DESCRIBE
    VOLUME_MOUNT --> KUBECTL_LOGS
    DATA_CORRUPTION --> KUBECTL_EXEC
    PERFORMANCE_SLOW --> KUBECTL_TOP
    
    style POD_CRASHLOOP fill:#f44336,color:#fff
    style SERVICE_502 fill:#ff5722,color:#fff
    style DATA_CORRUPTION fill:#f44336,color:#fff
```

### Performance Troubleshooting

```mermaid
flowchart TB
    subgraph "Performance Metrics"
        CPU_METRICS[CPU Metrics<br/>Utilization, throttling<br/>Scheduler latency]
        MEMORY_METRICS[Memory Metrics<br/>Usage, pressure<br/>OOM events]
        NETWORK_METRICS[Network Metrics<br/>Throughput, errors<br/>Connection limits]
        DISK_METRICS[Disk Metrics<br/>IOPS, latency<br/>Queue depth]
    end
    
    subgraph "Application Metrics"
        REQUEST_LATENCY[Request Latency<br/>P50, P95, P99<br/>Slow queries]
        ERROR_RATES[Error Rates<br/>HTTP 4xx, 5xx<br/>Application exceptions]
        THROUGHPUT[Throughput<br/>Requests per second<br/>Concurrent users]
        RESOURCE_USAGE[Resource Usage<br/>Per-component analysis<br/>Hotspot identification]
    end
    
    subgraph "Optimization Actions"
        VERTICAL_SCALING[Vertical Scaling<br/>Increase resource limits<br/>VPA recommendations]
        HORIZONTAL_SCALING[Horizontal Scaling<br/>Add more replicas<br/>HPA triggers]
        CODE_OPTIMIZATION[Code Optimization<br/>Algorithm improvements<br/>Database query tuning]
        INFRASTRUCTURE_TUNING[Infrastructure Tuning<br/>Storage class changes<br/>Network optimization]
    end
    
    subgraph "Monitoring Tools"
        GRAFANA_DASH[Grafana Dashboards<br/>Real-time visualization<br/>Historical trends]
        KUBECTL_TOP[kubectl top<br/>Resource usage<br/>Node and pod metrics]
        PROMETHEUS_QUERIES[Prometheus Queries<br/>Custom metrics<br/>Alert investigation]
        JAEGER_TRACING[Distributed Tracing<br/>Request flow analysis<br/>Bottleneck identification]
    end
    
    CPU_METRICS --> VERTICAL_SCALING
    MEMORY_METRICS --> VERTICAL_SCALING
    NETWORK_METRICS --> INFRASTRUCTURE_TUNING
    DISK_METRICS --> INFRASTRUCTURE_TUNING
    
    REQUEST_LATENCY --> CODE_OPTIMIZATION
    ERROR_RATES --> CODE_OPTIMIZATION
    THROUGHPUT --> HORIZONTAL_SCALING
    RESOURCE_USAGE --> VERTICAL_SCALING
    
    GRAFANA_DASH --> CPU_METRICS
    KUBECTL_TOP --> MEMORY_METRICS
    PROMETHEUS_QUERIES --> APPLICATION_METRICS
    JAEGER_TRACING --> REQUEST_LATENCY
    
    style CPU_METRICS fill:#ff9800,color:#000
    style CODE_OPTIMIZATION fill:#4caf50,color:#000
    style JAEGER_TRACING fill:#2196f3,color:#fff
```

## 📚 Operational Runbooks

### Daily Operations Checklist

```mermaid
flowchart TD
    subgraph "Morning Checks"
        HEALTH_CHECK[System Health Check<br/>All pods running<br/>Services responding]
        RESOURCE_CHECK[Resource Usage Check<br/>CPU, memory, storage<br/>Within normal ranges]
        ALERT_REVIEW[Alert Review<br/>Overnight alerts<br/>False positive analysis]
        BACKUP_VERIFY[Backup Verification<br/>Last night's backups<br/>Success confirmation]
    end
    
    subgraph "Continuous Monitoring"
        SLO_TRACKING[SLO Tracking<br/>Error budget consumption<br/>Performance trends]
        CAPACITY_PLANNING[Capacity Planning<br/>Growth trends<br/>Resource forecasting]
        SECURITY_MONITORING[Security Monitoring<br/>Access logs<br/>Anomaly detection]
        COST_MONITORING[Cost Monitoring<br/>Resource costs<br/>Optimization opportunities]
    end
    
    subgraph "Evening Tasks"
        PERFORMANCE_REVIEW[Performance Review<br/>Daily metrics summary<br/>Trend analysis]
        INCIDENT_REVIEW[Incident Review<br/>Day's incidents<br/>Action items]
        CHANGE_PLANNING[Change Planning<br/>Tomorrow's deployments<br/>Maintenance windows]
        ON_CALL_HANDOFF[On-Call Handoff<br/>Status briefing<br/>Known issues]
    end
    
    subgraph "Weekly Tasks"
        CAPACITY_REVIEW[Capacity Review<br/>Weekly resource trends<br/>Scaling decisions]
        SECURITY_REVIEW[Security Review<br/>Access audit<br/>Certificate expiry]
        BACKUP_TEST[Backup Testing<br/>Recovery procedures<br/>RTO/RPO validation]
        DOCUMENTATION_UPDATE[Documentation Update<br/>Runbook maintenance<br/>Process improvements]
    end
    
    HEALTH_CHECK --> SLO_TRACKING
    RESOURCE_CHECK --> CAPACITY_PLANNING
    ALERT_REVIEW --> SECURITY_MONITORING
    BACKUP_VERIFY --> COST_MONITORING
    
    SLO_TRACKING --> PERFORMANCE_REVIEW
    CAPACITY_PLANNING --> INCIDENT_REVIEW
    SECURITY_MONITORING --> CHANGE_PLANNING
    COST_MONITORING --> ON_CALL_HANDOFF
    
    PERFORMANCE_REVIEW --> CAPACITY_REVIEW
    INCIDENT_REVIEW --> SECURITY_REVIEW
    CHANGE_PLANNING --> BACKUP_TEST
    ON_CALL_HANDOFF --> DOCUMENTATION_UPDATE
    
    style HEALTH_CHECK fill:#4caf50,color:#000
    style SLO_TRACKING fill:#2196f3,color:#fff
    style BACKUP_TEST fill:#ff9800,color:#000
```

This comprehensive Kubernetes Operations Guide provides detailed operational procedures for managing GraphMemory-IDE in production. The guide includes visual workflows for all major operational tasks, from scaling and monitoring to troubleshooting and disaster recovery.

Key operational principles:
- **Proactive monitoring** with comprehensive SLI/SLO tracking
- **Automated scaling** using HPA and VPA for optimal resource utilization  
- **Security-first approach** with RBAC, network policies, and secrets management
- **Disaster recovery** planning with defined RTO/RPO targets
- **Performance optimization** through continuous monitoring and tuning

For specific operational procedures, refer to the individual sections and use the provided mermaid diagrams to understand the complete workflows. 