# GraphMemory-IDE Network Flows & Data Movement

## 🎯 Overview

This guide provides detailed network flow diagrams and packet-level analysis for GraphMemory-IDE. It covers the complete data journey from user interactions through the Kubernetes infrastructure to database storage and back.

## 📋 Table of Contents

- [Network Topology Overview](#network-topology-overview)
- [Request Flow Patterns](#request-flow-patterns)
- [Database Communication](#database-communication)
- [Real-time Data Flows](#real-time-data-flows)
- [Security Boundaries](#security-boundaries)
- [Load Balancing & Routing](#load-balancing--routing)
- [Performance Optimization](#performance-optimization)

## 🌐 Network Topology Overview

### Complete Network Architecture

```mermaid
flowchart TB
    subgraph "External Network"
        INTERNET[Internet Users<br/>Global Access]
        CDN[CloudFlare CDN<br/>Static Assets<br/>Edge Locations]
        DNS[DNS Resolution<br/>graphmemory.example.com<br/>Route 53/CloudFlare]
    end
    
    subgraph "Edge & Load Balancing"
        ALB[Application Load Balancer<br/>AWS ALB/GCP GLB<br/>SSL Termination]
        WAF[Web Application Firewall<br/>DDoS Protection<br/>Rate Limiting]
    end
    
    subgraph "Kubernetes Cluster Network"
        subgraph "Ingress Layer"
            NGINX_GW[NGINX Gateway Fabric<br/>10.244.1.0/24<br/>Ports: 80,443,8443]
            GATEWAY_API[Gateway API Resources<br/>HTTPRoutes<br/>TLS Configuration]
        end
        
        subgraph "Service Mesh"
            STREAMLIT_SVC[Streamlit Service<br/>10.244.2.10:8501<br/>ClusterIP]
            FASTAPI_SVC[FastAPI Service<br/>10.244.2.20:8080<br/>ClusterIP]
            ANALYTICS_SVC[Analytics Service<br/>10.244.2.30:8000<br/>ClusterIP]
        end
        
        subgraph "Database Network"
            POSTGRES_SVC[PostgreSQL Service<br/>10.244.3.10:5432<br/>StatefulSet]
            REDIS_SVC[Redis Service<br/>10.244.3.20:6379<br/>StatefulSet]
        end
        
        subgraph "Monitoring Network"
            PROMETHEUS_SVC[Prometheus<br/>10.244.4.10:9090<br/>Metrics Collection]
            GRAFANA_SVC[Grafana<br/>10.244.4.20:3000<br/>Dashboards]
        end
    end
    
    subgraph "Pod Network (CNI)"
        POD_CIDR[Pod CIDR: 10.244.0.0/16<br/>Canal CNI<br/>VXLAN Overlay]
        NODE_CIDR[Node CIDR: 10.240.0.0/16<br/>Physical Network<br/>Cloud Provider VPC]
    end
    
    INTERNET --> CDN
    CDN --> DNS
    DNS --> ALB
    ALB --> WAF
    WAF --> NGINX_GW
    
    NGINX_GW --> GATEWAY_API
    GATEWAY_API --> STREAMLIT_SVC
    GATEWAY_API --> FASTAPI_SVC
    GATEWAY_API --> ANALYTICS_SVC
    
    FASTAPI_SVC --> POSTGRES_SVC
    FASTAPI_SVC --> REDIS_SVC
    ANALYTICS_SVC --> POSTGRES_SVC
    
    PROMETHEUS_SVC -.-> STREAMLIT_SVC
    PROMETHEUS_SVC -.-> FASTAPI_SVC
    PROMETHEUS_SVC -.-> POSTGRES_SVC
    
    POD_CIDR -.-> NODE_CIDR
    
    style INTERNET fill:#4caf50,color:#000
    style NGINX_GW fill:#326ce5,color:#fff
    style POSTGRES_SVC fill:#336791,color:#fff
    style PROMETHEUS_SVC fill:#e6522c,color:#fff
```

### Network Layers & CIDR Allocation

```mermaid
flowchart TD
    subgraph "Network Layer Architecture"
        subgraph "Layer 7 - Application"
            HTTP_HTTPS[HTTP/HTTPS Traffic<br/>Application Layer<br/>API Calls, Web Interface]
            WEBSOCKET[WebSocket Connections<br/>Real-time Updates<br/>Streamlit Communication]
        end
        
        subgraph "Layer 4 - Transport"
            TCP_CONNECTIONS[TCP Connections<br/>Reliable Transport<br/>Database Connections]
            UDP_TRAFFIC[UDP Traffic<br/>DNS Resolution<br/>Service Discovery]
        end
        
        subgraph "Layer 3 - Network"
            POD_ROUTING[Pod-to-Pod Routing<br/>10.244.0.0/16<br/>VXLAN Encapsulation]
            SERVICE_ROUTING[Service Routing<br/>10.96.0.0/12<br/>kube-proxy iptables]
            NODE_ROUTING[Node Routing<br/>10.240.0.0/16<br/>Cloud Provider Network]
        end
        
        subgraph "Layer 2 - Data Link"
            OVERLAY_NETWORK[Overlay Network<br/>Canal CNI<br/>VXLAN Tunnels]
            BRIDGE_NETWORK[Bridge Network<br/>cni0 Bridge<br/>Container veth pairs]
        end
    end
    
    subgraph "CIDR Allocation"
        CLUSTER_CIDR[Cluster CIDR<br/>10.244.0.0/16<br/>Pod Network]
        SERVICE_CIDR[Service CIDR<br/>10.96.0.0/12<br/>Service Discovery]
        NODE_CIDR[Node CIDR<br/>10.240.0.0/16<br/>Node Network]
    end
    
    HTTP_HTTPS --> TCP_CONNECTIONS
    WEBSOCKET --> TCP_CONNECTIONS
    TCP_CONNECTIONS --> POD_ROUTING
    UDP_TRAFFIC --> SERVICE_ROUTING
    
    POD_ROUTING --> OVERLAY_NETWORK
    SERVICE_ROUTING --> BRIDGE_NETWORK
    NODE_ROUTING --> BRIDGE_NETWORK
    
    CLUSTER_CIDR -.-> POD_ROUTING
    SERVICE_CIDR -.-> SERVICE_ROUTING
    NODE_CIDR -.-> NODE_ROUTING
    
    style HTTP_HTTPS fill:#4caf50,color:#000
    style POD_ROUTING fill:#ff9800,color:#000
    style CLUSTER_CIDR fill:#2196f3,color:#fff
```

## 🔄 Request Flow Patterns

### User Request Lifecycle

```mermaid
sequenceDiagram
    participant User as User Browser
    participant CDN as CloudFlare CDN
    participant ALB as Load Balancer
    participant Gateway as NGINX Gateway
    participant Frontend as Streamlit Frontend
    participant Backend as FastAPI Backend
    participant Cache as Redis Cache
    participant DB as PostgreSQL DB

    Note over User, DB: Complete Request Lifecycle

    User->>CDN: GET /dashboard
    CDN->>ALB: Forward request (if not cached)
    ALB->>Gateway: Route to cluster (SSL termination)
    Gateway->>Frontend: HTTPRoute matching (port 8501)
    
    Frontend->>Backend: API call /api/v1/data
    Backend->>Cache: Check cached data (Redis)
    
    alt Cache Hit
        Cache-->>Backend: Return cached data
        Backend-->>Frontend: JSON response
    else Cache Miss
        Backend->>DB: SQL query
        DB-->>Backend: Query results
        Backend->>Cache: Store in cache (TTL: 300s)
        Backend-->>Frontend: JSON response
    end
    
    Frontend-->>Gateway: HTML response
    Gateway-->>ALB: Response with headers
    ALB-->>CDN: Response (cache static assets)
    CDN-->>User: Final response (with CDN headers)
    
    Note over User: Page rendered
```

### API Request Flow Patterns

```mermaid
flowchart TB
    subgraph "API Request Types"
        READ_REQUEST[Read Requests<br/>GET /api/v1/*<br/>Cacheable, High Volume]
        WRITE_REQUEST[Write Requests<br/>POST/PUT/DELETE<br/>Transactional, Lower Volume]
        REALTIME_REQUEST[Real-time Requests<br/>WebSocket /ws<br/>Streaming, Persistent]
        ANALYTICS_REQUEST[Analytics Requests<br/>POST /api/v1/analytics<br/>Compute Intensive]
    end
    
    subgraph "Request Routing"
        GATEWAY_ROUTING[Gateway API Routing<br/>Path-based routing<br/>Rate limiting per route]
        SERVICE_DISCOVERY[Service Discovery<br/>CoreDNS resolution<br/>Service endpoints]
        LOAD_BALANCING[Load Balancing<br/>Round-robin<br/>Session affinity]
    end
    
    subgraph "Processing Flow"
        AUTH_VALIDATION[Authentication<br/>JWT validation<br/>RBAC checks]
        REQUEST_VALIDATION[Request Validation<br/>Schema validation<br/>Input sanitization]
        BUSINESS_LOGIC[Business Logic<br/>Core processing<br/>Data transformation]
        RESPONSE_FORMATTING[Response Formatting<br/>JSON serialization<br/>Error handling]
    end
    
    subgraph "Data Layer Access"
        CACHE_LAYER[Cache Layer<br/>Redis lookup<br/>Write-through/Write-back]
        DATABASE_LAYER[Database Layer<br/>PostgreSQL<br/>Connection pooling]
        STORAGE_LAYER[Storage Layer<br/>File system<br/>Object storage]
    end
    
    READ_REQUEST --> GATEWAY_ROUTING
    WRITE_REQUEST --> GATEWAY_ROUTING
    REALTIME_REQUEST --> GATEWAY_ROUTING
    ANALYTICS_REQUEST --> GATEWAY_ROUTING
    
    GATEWAY_ROUTING --> SERVICE_DISCOVERY
    SERVICE_DISCOVERY --> LOAD_BALANCING
    
    LOAD_BALANCING --> AUTH_VALIDATION
    AUTH_VALIDATION --> REQUEST_VALIDATION
    REQUEST_VALIDATION --> BUSINESS_LOGIC
    BUSINESS_LOGIC --> RESPONSE_FORMATTING
    
    BUSINESS_LOGIC --> CACHE_LAYER
    BUSINESS_LOGIC --> DATABASE_LAYER
    BUSINESS_LOGIC --> STORAGE_LAYER
    
    style READ_REQUEST fill:#4caf50,color:#000
    style REALTIME_REQUEST fill:#ff9800,color:#000
    style GATEWAY_ROUTING fill:#2196f3,color:#fff
    style CACHE_LAYER fill:#f44336,color:#fff
```

## 💾 Database Communication

### Database Connection Patterns

```mermaid
flowchart TB
    subgraph "Application Layer"
        FASTAPI_PODS[FastAPI Pods<br/>3 replicas<br/>Connection Pool: 20/pod]
        ANALYTICS_PODS[Analytics Pods<br/>2 replicas<br/>Connection Pool: 15/pod]
        STREAMLIT_PODS[Streamlit Pods<br/>2 replicas<br/>Connection Pool: 5/pod]
    end
    
    subgraph "Connection Management"
        CONNECTION_POOLER[PgBouncer<br/>Connection Pooling<br/>Pool Mode: Transaction]
        CONN_MONITOR[Connection Monitor<br/>Active connections<br/>Pool statistics]
        CONN_LIMITS[Connection Limits<br/>Max: 200 total<br/>Per-user: 50]
    end
    
    subgraph "Database Cluster"
        PG_PRIMARY[PostgreSQL Primary<br/>Read/Write operations<br/>WAL generation]
        PG_REPLICA1[PostgreSQL Replica 1<br/>Read operations<br/>Streaming replication]
        PG_REPLICA2[PostgreSQL Replica 2<br/>Read operations<br/>Backup target]
    end
    
    subgraph "Connection Routing"
        READ_ROUTER[Read Router<br/>Load balance reads<br/>Health check enabled]
        WRITE_ROUTER[Write Router<br/>Primary only<br/>Failover detection]
        REPLICATION[Replication Stream<br/>WAL streaming<br/>Async replication]
    end
    
    FASTAPI_PODS --> CONNECTION_POOLER
    ANALYTICS_PODS --> CONNECTION_POOLER
    STREAMLIT_PODS --> CONNECTION_POOLER
    
    CONNECTION_POOLER --> CONN_MONITOR
    CONNECTION_POOLER --> READ_ROUTER
    CONNECTION_POOLER --> WRITE_ROUTER
    
    READ_ROUTER --> PG_REPLICA1
    READ_ROUTER --> PG_REPLICA2
    WRITE_ROUTER --> PG_PRIMARY
    
    PG_PRIMARY --> REPLICATION
    REPLICATION --> PG_REPLICA1
    REPLICATION --> PG_REPLICA2
    
    style FASTAPI_PODS fill:#326ce5,color:#fff
    style CONNECTION_POOLER fill:#4caf50,color:#000
    style PG_PRIMARY fill:#336791,color:#fff
    style REPLICATION fill:#ff9800,color:#000
```

### Query Flow & Optimization

```mermaid
sequenceDiagram
    participant App as Application Pod
    participant Pool as Connection Pool
    participant Primary as PostgreSQL Primary
    participant Replica as PostgreSQL Replica
    participant Cache as Redis Cache

    Note over App, Cache: Database Query Optimization Flow

    App->>Pool: Request connection
    Pool->>Pool: Check available connections
    
    alt Write Operation
        Pool->>Primary: Establish connection
        App->>Primary: BEGIN TRANSACTION
        App->>Primary: INSERT/UPDATE/DELETE
        Primary->>Primary: Write to WAL
        App->>Primary: COMMIT
        Primary-->>App: Success response
        Primary->>Replica: Stream WAL (async)
        App->>Cache: Invalidate related cache keys
    else Read Operation
        Pool->>Replica: Establish connection (load balanced)
        App->>Cache: Check cache first
        alt Cache Miss
            App->>Replica: SELECT query
            Replica-->>App: Query results
            App->>Cache: Store results (TTL: 300s)
        else Cache Hit
            Cache-->>App: Cached results
        end
    end
    
    Pool->>Pool: Return connection to pool
    
    Note over App: Query complete
```

## ⚡ Real-time Data Flows

### WebSocket Communication

```mermaid
flowchart TB
    subgraph "Client Connections"
        BROWSER_WS[Browser WebSocket<br/>wss://graphmemory.example.com/ws<br/>Real-time dashboard updates]
        IDE_PLUGIN[IDE Plugin Connection<br/>WebSocket client<br/>Code analysis updates]
        API_CLIENT[API Client<br/>Server-sent events<br/>Notification stream]
    end
    
    subgraph "WebSocket Gateway"
        WS_GATEWAY[WebSocket Gateway<br/>NGINX Gateway Fabric<br/>Sticky sessions]
        WS_ROUTER[WebSocket Router<br/>Connection routing<br/>Load balancing]
        WS_MANAGER[Connection Manager<br/>Session tracking<br/>Heartbeat monitoring]
    end
    
    subgraph "Application Layer"
        STREAMLIT_WS[Streamlit WebSocket<br/>Component updates<br/>State synchronization]
        ANALYTICS_WS[Analytics WebSocket<br/>Real-time metrics<br/>Progress updates]
        NOTIFICATION_SVC[Notification Service<br/>Event broadcasting<br/>Subscription management]
    end
    
    subgraph "Event Processing"
        EVENT_QUEUE[Event Queue<br/>Redis Pub/Sub<br/>Message routing]
        EVENT_PROCESSOR[Event Processor<br/>Data transformation<br/>Filtering rules]
        EVENT_STORE[Event Store<br/>PostgreSQL<br/>Audit trail]
    end
    
    subgraph "Data Sources"
        DB_CHANGES[Database Changes<br/>PostgreSQL triggers<br/>Change data capture]
        ANALYTICS_ENGINE[Analytics Engine<br/>Real-time processing<br/>Stream analytics]
        EXTERNAL_APIs[External APIs<br/>Webhook receivers<br/>Third-party events]
    end
    
    BROWSER_WS --> WS_GATEWAY
    IDE_PLUGIN --> WS_GATEWAY
    API_CLIENT --> WS_GATEWAY
    
    WS_GATEWAY --> WS_ROUTER
    WS_ROUTER --> WS_MANAGER
    
    WS_MANAGER --> STREAMLIT_WS
    WS_MANAGER --> ANALYTICS_WS
    WS_MANAGER --> NOTIFICATION_SVC
    
    STREAMLIT_WS --> EVENT_QUEUE
    ANALYTICS_WS --> EVENT_QUEUE
    NOTIFICATION_SVC --> EVENT_QUEUE
    
    EVENT_QUEUE --> EVENT_PROCESSOR
    EVENT_PROCESSOR --> EVENT_STORE
    
    DB_CHANGES --> EVENT_QUEUE
    ANALYTICS_ENGINE --> EVENT_QUEUE
    EXTERNAL_APIs --> EVENT_QUEUE
    
    style BROWSER_WS fill:#4caf50,color:#000
    style WS_GATEWAY fill:#ff9800,color:#000
    style EVENT_QUEUE fill:#f44336,color:#fff
    style ANALYTICS_ENGINE fill:#2196f3,color:#fff
```

### Event-Driven Architecture

```mermaid
sequenceDiagram
    participant User as User Interface
    participant WS as WebSocket Gateway
    participant App as Application
    participant Queue as Event Queue
    participant Processor as Event Processor
    participant DB as Database
    participant Cache as Cache

    Note over User, Cache: Real-time Event Flow

    User->>WS: Establish WebSocket connection
    WS->>App: Route to application instance
    App->>Queue: Subscribe to user events
    
    DB->>Queue: Database change event
    Queue->>Processor: Process event
    Processor->>Processor: Transform & filter
    
    alt User subscribed to event
        Processor->>Queue: Publish to user channel
        Queue->>App: Route to user's app instance
        App->>WS: Send WebSocket message
        WS->>User: Real-time update
    end
    
    Processor->>Cache: Update cached data
    Processor->>DB: Store processed event
    
    Note over User: Real-time update received
```

## 🔐 Security Boundaries

### Network Security Zones

```mermaid
flowchart TB
    subgraph "DMZ Zone"
        PUBLIC_LB[Public Load Balancer<br/>Internet-facing<br/>DDoS protection]
        WAF_EDGE[WAF Edge<br/>Application firewall<br/>Threat detection]
    end
    
    subgraph "Ingress Zone"
        NGINX_INGRESS[NGINX Ingress<br/>TLS termination<br/>Rate limiting]
        CERT_MANAGER[Certificate Manager<br/>Automatic TLS<br/>Let's Encrypt]
    end
    
    subgraph "Application Zone"
        APP_PODS[Application Pods<br/>Frontend & Backend<br/>Non-privileged containers]
        NETWORK_POLICIES[Network Policies<br/>Pod-to-pod rules<br/>Default deny all]
    end
    
    subgraph "Data Zone"
        DATABASE_PODS[Database Pods<br/>Persistent storage<br/>Encrypted at rest]
        BACKUP_STORAGE[Backup Storage<br/>Encrypted backups<br/>Cross-region replication]
    end
    
    subgraph "Management Zone"
        MONITORING[Monitoring Stack<br/>Prometheus & Grafana<br/>Metrics collection]
        LOGGING[Logging Stack<br/>Centralized logs<br/>Audit trail]
    end
    
    subgraph "Security Controls"
        RBAC[RBAC Controls<br/>Service accounts<br/>Least privilege]
        SECRETS[Secrets Management<br/>Encrypted secrets<br/>Rotation policies]
        POD_SECURITY[Pod Security<br/>Security contexts<br/>No root containers]
    end
    
    PUBLIC_LB --> WAF_EDGE
    WAF_EDGE --> NGINX_INGRESS
    NGINX_INGRESS --> CERT_MANAGER
    
    NGINX_INGRESS --> APP_PODS
    APP_PODS --> NETWORK_POLICIES
    
    APP_PODS --> DATABASE_PODS
    DATABASE_PODS --> BACKUP_STORAGE
    
    APP_PODS -.-> MONITORING
    APP_PODS -.-> LOGGING
    
    RBAC -.-> APP_PODS
    SECRETS -.-> APP_PODS
    POD_SECURITY -.-> APP_PODS
    
    style PUBLIC_LB fill:#f44336,color:#fff
    style NETWORK_POLICIES fill:#ff9800,color:#000
    style DATABASE_PODS fill:#336791,color:#fff
    style RBAC fill:#4caf50,color:#000
```

### Traffic Filtering & Inspection

```mermaid
flowchart TD
    subgraph "Ingress Traffic Flow"
        EXTERNAL_TRAFFIC[External Traffic<br/>Internet requests<br/>Various protocols]
        DPI_INSPECTION[Deep Packet Inspection<br/>Protocol analysis<br/>Threat detection]
        RATE_LIMITING[Rate Limiting<br/>Per-IP limits<br/>Burst control]
        GEO_FILTERING[Geo Filtering<br/>Country blocking<br/>Allowlist regions]
    end
    
    subgraph "Application Security"
        INPUT_VALIDATION[Input Validation<br/>Schema validation<br/>XSS/SQL injection protection]
        AUTH_CHECKS[Authentication<br/>JWT validation<br/>Session management]
        AUTHZ_CHECKS[Authorization<br/>RBAC enforcement<br/>Resource permissions]
        AUDIT_LOGGING[Audit Logging<br/>Access logs<br/>Security events]
    end
    
    subgraph "Network Policies"
        INGRESS_POLICIES[Ingress Policies<br/>Allow from gateway only<br/>Port restrictions]
        EGRESS_POLICIES[Egress Policies<br/>Database access only<br/>External API whitelist]
        INTER_POD[Inter-pod Communication<br/>Service mesh rules<br/>mTLS encryption]
    end
    
    subgraph "Data Protection"
        ENCRYPTION_TRANSIT[Encryption in Transit<br/>TLS 1.3<br/>Perfect forward secrecy]
        ENCRYPTION_REST[Encryption at Rest<br/>Database encryption<br/>Storage encryption]
        DATA_MASKING[Data Masking<br/>PII protection<br/>Log sanitization]
    end
    
    EXTERNAL_TRAFFIC --> DPI_INSPECTION
    DPI_INSPECTION --> RATE_LIMITING
    RATE_LIMITING --> GEO_FILTERING
    
    GEO_FILTERING --> INPUT_VALIDATION
    INPUT_VALIDATION --> AUTH_CHECKS
    AUTH_CHECKS --> AUTHZ_CHECKS
    AUTHZ_CHECKS --> AUDIT_LOGGING
    
    AUDIT_LOGGING --> INGRESS_POLICIES
    INGRESS_POLICIES --> EGRESS_POLICIES
    EGRESS_POLICIES --> INTER_POD
    
    INTER_POD --> ENCRYPTION_TRANSIT
    ENCRYPTION_TRANSIT --> ENCRYPTION_REST
    ENCRYPTION_REST --> DATA_MASKING
    
    style EXTERNAL_TRAFFIC fill:#f44336,color:#fff
    style DPI_INSPECTION fill:#ff5722,color:#fff
    style AUTH_CHECKS fill:#4caf50,color:#000
    style ENCRYPTION_TRANSIT fill:#2196f3,color:#fff
```

## ⚖️ Load Balancing & Routing

### Traffic Distribution Strategy

```mermaid
flowchart TB
    subgraph "Global Load Balancing"
        DNS_LB[DNS Load Balancing<br/>GeoDNS routing<br/>Health-based failover]
        CDN_LB[CDN Load Balancing<br/>Edge cache routing<br/>Origin selection]
        GLOBAL_LB[Global Load Balancer<br/>Cross-region routing<br/>Latency-based]
    end
    
    subgraph "Regional Load Balancing"
        REGIONAL_LB[Regional Load Balancer<br/>Multi-AZ distribution<br/>SSL termination]
        WAF_LB[WAF Load Balancer<br/>Security filtering<br/>DDoS protection]
        INGRESS_LB[Ingress Load Balancer<br/>Kubernetes ingress<br/>Service routing]
    end
    
    subgraph "Service Level Routing"
        GATEWAY_ROUTING[Gateway API Routing<br/>Path-based routing<br/>Header-based routing]
        SERVICE_LB[Service Load Balancer<br/>kube-proxy iptables<br/>Session affinity]
        POD_LB[Pod Load Balancing<br/>Round-robin<br/>Least connections]
    end
    
    subgraph "Application Routing"
        FRONTEND_ROUTING[Frontend Routing<br/>Streamlit instances<br/>Sticky sessions]
        BACKEND_ROUTING[Backend Routing<br/>FastAPI instances<br/>Stateless routing]
        DATABASE_ROUTING[Database Routing<br/>Read/write split<br/>Connection pooling]
    end
    
    DNS_LB --> CDN_LB
    CDN_LB --> GLOBAL_LB
    GLOBAL_LB --> REGIONAL_LB
    
    REGIONAL_LB --> WAF_LB
    WAF_LB --> INGRESS_LB
    INGRESS_LB --> GATEWAY_ROUTING
    
    GATEWAY_ROUTING --> SERVICE_LB
    SERVICE_LB --> POD_LB
    POD_LB --> FRONTEND_ROUTING
    POD_LB --> BACKEND_ROUTING
    
    BACKEND_ROUTING --> DATABASE_ROUTING
    
    style DNS_LB fill:#4caf50,color:#000
    style GATEWAY_ROUTING fill:#ff9800,color:#000
    style DATABASE_ROUTING fill:#336791,color:#fff
```

### Health Check & Failover

```mermaid
sequenceDiagram
    participant LB as Load Balancer
    participant Health as Health Checker
    participant Pod1 as Healthy Pod
    participant Pod2 as Unhealthy Pod
    participant Monitor as Monitoring

    Note over LB, Monitor: Health Check & Failover Process

    Health->>Pod1: HTTP GET /health
    Pod1-->>Health: 200 OK (healthy)
    
    Health->>Pod2: HTTP GET /health
    Pod2-->>Health: 500 Error (unhealthy)
    
    Health->>LB: Update backend status
    LB->>LB: Remove Pod2 from rotation
    
    LB->>Monitor: Alert unhealthy backend
    Monitor->>Monitor: Trigger auto-healing
    
    loop Traffic Routing
        LB->>Pod1: Route all traffic
        Pod1-->>LB: Handle requests
    end
    
    Note over Pod2: Pod restart/recovery
    
    Health->>Pod2: HTTP GET /health
    Pod2-->>Health: 200 OK (recovered)
    
    Health->>LB: Pod2 healthy again
    LB->>LB: Add Pod2 back to rotation
    
    LB->>Monitor: Backend recovered
```

## 🚀 Performance Optimization

### Caching Strategy

```mermaid
flowchart TB
    subgraph "Client-Side Caching"
        BROWSER_CACHE[Browser Cache<br/>Static assets<br/>24h TTL]
        SERVICE_WORKER[Service Worker<br/>Offline support<br/>API response cache]
        LOCAL_STORAGE[Local Storage<br/>User preferences<br/>Session data]
    end
    
    subgraph "CDN Caching"
        EDGE_CACHE[Edge Cache<br/>Global distribution<br/>Static content]
        DYNAMIC_CACHE[Dynamic Cache<br/>API responses<br/>5min TTL]
        CACHE_PURGE[Cache Purge<br/>Automated invalidation<br/>Content updates]
    end
    
    subgraph "Application Caching"
        REDIS_CACHE[Redis Cache<br/>Database query results<br/>Session storage]
        MEMORY_CACHE[In-Memory Cache<br/>Hot data<br/>Application cache]
        COMPUTED_CACHE[Computed Cache<br/>Analytics results<br/>Heavy computations]
    end
    
    subgraph "Database Caching"
        QUERY_CACHE[Query Cache<br/>PostgreSQL<br/>Prepared statements]
        BUFFER_CACHE[Buffer Cache<br/>Shared buffers<br/>Page cache]
        CONNECTION_CACHE[Connection Cache<br/>PgBouncer<br/>Connection pooling]
    end
    
    BROWSER_CACHE --> EDGE_CACHE
    SERVICE_WORKER --> DYNAMIC_CACHE
    LOCAL_STORAGE --> CACHE_PURGE
    
    EDGE_CACHE --> REDIS_CACHE
    DYNAMIC_CACHE --> MEMORY_CACHE
    CACHE_PURGE --> COMPUTED_CACHE
    
    REDIS_CACHE --> QUERY_CACHE
    MEMORY_CACHE --> BUFFER_CACHE
    COMPUTED_CACHE --> CONNECTION_CACHE
    
    style BROWSER_CACHE fill:#4caf50,color:#000
    style REDIS_CACHE fill:#f44336,color:#fff
    style QUERY_CACHE fill:#336791,color:#fff
```

This comprehensive Network Flows documentation provides detailed packet-level analysis and data movement patterns for GraphMemory-IDE. The guide includes visual representations of all network communication paths, security boundaries, and performance optimization strategies. 