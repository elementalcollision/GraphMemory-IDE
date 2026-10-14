# GraphMemory-IDE Code Paths & Component Interactions

## 🎯 Overview

This document provides a comprehensive map of code paths, component interactions, and data flow throughout the GraphMemory-IDE system. It serves as a technical reference for developers to understand how different parts of the system communicate and process data.

## 🏗️ System Architecture Code Paths

### High-Level Data Flow

```mermaid
graph TB
    subgraph "Client Layer"
        IDE[IDE Plugins<br/>Cursor, VSCode, Windsurf]
        CLI[CLI Tool<br/>graphmemory-cli]
        WEB[Web Dashboard<br/>Streamlit]
        API_CLIENT[API Clients<br/>Custom Apps]
    end
    
    subgraph "API Gateway"
        AUTH[Authentication Layer<br/>auth.py]
        RATE[Rate Limiting<br/>Redis]
        VALIDATE[Input Validation<br/>FastAPI]
    end
    
    subgraph "Core Services"
        MCP[MCP Server<br/>main.py]
        ROUTES[API Routes<br/>Various route files]
        BUSINESS[Business Logic<br/>Service layers]
    end
    
    subgraph "Data Processing"
        EMBED[Embedding Service<br/>Sentence Transformers]
        SEARCH[Search Engine<br/>Vector + Graph]
        ANALYTICS[Analytics Engine<br/>NetworkX + cuGraph]
        ALERTS[Alert System<br/>Real-time Processing]
    end
    
    subgraph "Storage Layer"
        LADYBUG[(LadybugDB<br/>Relationships)]
        VECTOR[(Vector Store<br/>Embeddings)]
        CACHE[(Redis Cache<br/>Performance)]
        SQLITE[(SQLite<br/>Alert/Incident Data)]
    end
    
    IDE --> AUTH
    CLI --> AUTH
    WEB --> AUTH
    API_CLIENT --> AUTH
    
    AUTH --> RATE
    RATE --> VALIDATE
    VALIDATE --> MCP
    
    MCP --> ROUTES
    ROUTES --> BUSINESS
    
    BUSINESS --> EMBED
    BUSINESS --> SEARCH
    BUSINESS --> ANALYTICS
    BUSINESS --> ALERTS
    
    EMBED --> VECTOR
    SEARCH --> LADYBUG
    SEARCH --> VECTOR
    ANALYTICS --> LADYBUG
    ALERTS --> SQLITE
    
    BUSINESS --> CACHE
    CACHE --> LADYBUG
    
    style MCP fill:#0073e6,color:#ffffff
    style ALERTS fill:#2546f0,color:#ffffff
    style ANALYTICS fill:#00bf7d,color:#000000
    style LADYBUG fill:#5928ed,color:#ffffff
```

## 📁 Directory Structure & Code Organization

### Core Application Structure

```
GraphMemory-IDE/
├── server/                          # Backend FastAPI server
│   ├── main.py                      # Main application entry point
│   ├── auth.py                      # Authentication & authorization
│   ├── database.py                  # Database connections & setup
│   ├── models.py                    # Pydantic data models
│   ├── routes/                      # API route definitions
│   │   ├── memory.py               # Memory management endpoints
│   │   ├── graph.py                # Graph query endpoints
│   │   ├── search.py               # Search & discovery endpoints
│   │   └── health.py               # Health check endpoints
│   ├── analytics/                   # Analytics engine (2,500+ lines)
│   │   ├── engine.py               # Core analytics orchestration
│   │   ├── algorithms.py           # Graph algorithms & ML
│   │   ├── gpu_acceleration.py     # NVIDIA cuGraph integration
│   │   ├── performance_monitor.py  # Performance tracking
│   │   ├── alert_engine.py         # Alert rule evaluation
│   │   ├── alert_manager.py        # Alert lifecycle management
│   │   ├── notification_dispatcher.py # Multi-channel notifications
│   │   ├── alert_correlator.py     # ML-based correlation
│   │   └── incident_manager.py     # Incident management
│   └── dashboard/                   # Dashboard backend (1,000+ lines)
│       ├── main.py                 # Dashboard FastAPI server
│       ├── sse_server.py           # Server-sent events
│       ├── sse_alert_server.py     # Enhanced SSE for alerts
│       └── data_collection.py      # Real-time data collection
├── dashboard/                       # Streamlit frontend (3,000+ lines)
│   ├── streamlit_app.py            # Main dashboard application
│   ├── components/                 # UI components
│   │   ├── alerts.py               # Alert management UI
│   │   ├── incidents.py            # Incident management UI
│   │   ├── alert_metrics.py        # Analytics dashboard
│   │   └── alert_actions.py        # Action components
│   ├── pages/                      # Dashboard pages
│   │   └── alerts_dashboard.py     # Main alerts page
│   └── utils/                      # Dashboard utilities
├── ide-plugins/                     # IDE integration (2,000+ lines)
│   ├── shared/                     # Common plugin code
│   ├── cursor/                     # Cursor IDE plugin
│   ├── vscode/                     # VSCode extension
│   └── windsurf/                   # Windsurf plugin
└── cli/                            # Command-line interface
    ├── commands.mjs                # CLI command implementations
    └── update/                     # Update management
```

## 🔄 Core Code Paths

### 1. Memory Creation & Storage Flow

```mermaid
sequenceDiagram
    participant Client
    participant Auth as auth.py
    participant Routes as routes/memory.py
    participant Models as models.py
    participant Embed as Embedding Service
    participant DB as database.py
    participant LadybugDB as LadybugDB
    participant Vector as Vector Store
    participant Cache as Redis Cache
    
    Client->>Auth: POST /memory/create + JWT
    Auth->>Auth: validate_token()
    Auth->>Routes: Authenticated request
    
    Routes->>Models: MemoryCreateRequest validation
    Models->>Routes: Validated data
    
    Routes->>Embed: generate_embedding(content)
    Embed->>Embed: SentenceTransformer.encode()
    Embed->>Routes: embedding_vector
    
    Routes->>DB: get_ladybug_connection()
    DB->>Routes: ladybug_connection
    
    Routes->>LadybugDB: CREATE (m:Memory {properties})
    LadybugDB->>Routes: memory_node_id
    
    Routes->>Vector: store_embedding(id, vector)
    Vector->>Routes: success
    
    Routes->>Cache: cache_memory(id, data)
    Cache->>Routes: cached
    
    Routes->>Client: MemoryResponse
```

### 2. Search & Retrieval Flow

```mermaid
sequenceDiagram
    participant Client
    participant Routes as routes/search.py
    participant Embed as Embedding Service
    participant Vector as Vector Store
    participant LadybugDB as LadybugDB
    participant Cache as Redis Cache
    participant Rank as Ranking Engine
    
    Client->>Routes: POST /search/semantic
    
    Routes->>Cache: check_cache(query_hash)
    alt Cache Hit
        Cache->>Routes: cached_results
        Routes->>Client: SearchResponse
    else Cache Miss
        Routes->>Embed: generate_embedding(query)
        Embed->>Routes: query_vector
        
        Routes->>Vector: similarity_search(query_vector, k=10)
        Vector->>Routes: candidate_ids
        
        Routes->>LadybugDB: MATCH (m:Memory) WHERE m.id IN candidates
        LadybugDB->>Routes: memory_data
        
        Routes->>Rank: rank_results(query, memories)
        Rank->>Routes: ranked_results
        
        Routes->>Cache: cache_results(query_hash, results)
        Routes->>Client: SearchResponse
    end
```

### 3. Alert System Flow (Step 8)

```mermaid
sequenceDiagram
    participant Trigger as Data Source
    participant Engine as alert_engine.py
    participant Manager as alert_manager.py
    participant Correlator as alert_correlator.py
    participant Incident as incident_manager.py
    participant Dispatcher as notification_dispatcher.py
    participant SSE as sse_alert_server.py
    participant Dashboard as Dashboard UI
    
    Trigger->>Engine: metric_data
    Engine->>Engine: evaluate_rules()
    Engine->>Engine: check_thresholds()
    
    alt Threshold Exceeded
        Engine->>Manager: create_alert()
        Manager->>Manager: store_alert()
        
        Manager->>Correlator: correlate_alert()
        Correlator->>Correlator: ml_analysis()
        
        alt High Correlation
            Correlator->>Incident: create_incident()
            Incident->>Incident: group_alerts()
            Incident->>Manager: update_alert_status()
        end
        
        Manager->>Dispatcher: dispatch_notification()
        
        par Multi-channel Delivery
            Dispatcher->>Dispatcher: send_websocket()
            Dispatcher->>Dispatcher: send_email()
            Dispatcher->>Dispatcher: send_webhook()
        end
        
        Dispatcher->>SSE: stream_alert_event()
        SSE->>Dashboard: Real-time update
    end
```

### 4. Analytics Engine Flow

```mermaid
sequenceDiagram
    participant Client
    participant Routes as analytics_routes.py
    participant Engine as analytics/engine.py
    participant GPU as gpu_acceleration.py
    participant Algorithms as algorithms.py
    participant Monitor as performance_monitor.py
    participant Cache as Redis Cache
    
    Client->>Routes: POST /analytics/centrality
    Routes->>Engine: execute_analysis()
    
    Engine->>Monitor: start_performance_tracking()
    Engine->>Cache: check_cache(analysis_key)
    
    alt Cache Miss
        Engine->>GPU: check_gpu_available()
        
        alt GPU Available
            GPU->>GPU: cuGraph_pagerank()
            GPU->>Engine: gpu_results
        else CPU Fallback
            Engine->>Algorithms: networkx_pagerank()
            Algorithms->>Engine: cpu_results
        end
        
        Engine->>Cache: store_results()
    end
    
    Engine->>Monitor: end_performance_tracking()
    Monitor->>Monitor: log_metrics()
    
    Engine->>Routes: analysis_results
    Routes->>Client: AnalyticsResponse
```

## 🔌 Plugin Integration Paths

### IDE Plugin Communication Flow

```mermaid
sequenceDiagram
    participant IDE as IDE Environment
    participant Plugin as Plugin MCP Client
    participant Server as GraphMemory Server
    participant Auth as Authentication
    participant Memory as Memory Service
    
    IDE->>Plugin: User action (create memory)
    Plugin->>Plugin: validate_input()
    Plugin->>Plugin: prepare_mcp_request()
    
    Plugin->>Auth: authenticate(api_key/jwt)
    Auth->>Plugin: auth_token
    
    Plugin->>Server: MCP request + auth
    Server->>Memory: process_memory_operation()
    Memory->>Server: operation_result
    Server->>Plugin: MCP response
    
    Plugin->>Plugin: format_response()
    Plugin->>IDE: Display result to user
```

## 📊 Dashboard Real-time Data Flow

```mermaid
sequenceDiagram
    participant Dashboard as Streamlit Dashboard
    participant SSE as SSE Server
    participant Collectors as Data Collectors
    participant Analytics as Analytics Engine
    participant Alerts as Alert System
    participant Cache as Redis Cache
    
    Dashboard->>SSE: Connect to /stream/analytics
    SSE->>SSE: establish_connection()
    
    loop Every 2 seconds
        SSE->>Collectors: collect_system_metrics()
        Collectors->>Analytics: get_performance_data()
        Collectors->>Alerts: get_alert_summary()
        Collectors->>Cache: get_cached_data()
        
        SSE->>SSE: format_sse_event()
        SSE->>Dashboard: Send SSE update
        Dashboard->>Dashboard: update_ui_components()
    end
```

## 🔐 Security Code Paths

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Auth as auth.py
    participant JWT as JWT Service
    participant DB as User Database
    participant Routes as Protected Routes
    
    Client->>Auth: POST /auth/token
    Auth->>Auth: validate_credentials()
    Auth->>DB: verify_user()
    
    alt Valid User
        DB->>Auth: user_data
        Auth->>JWT: create_access_token()
        JWT->>Auth: jwt_token
        Auth->>Client: {"access_token": token}
    else Invalid User
        Auth->>Client: 401 Unauthorized
    end
    
    Note over Client: Subsequent requests
    Client->>Routes: GET /protected + Bearer token
    Routes->>Auth: verify_token()
    Auth->>JWT: decode_token()
    
    alt Valid Token
        JWT->>Auth: user_payload
        Auth->>Routes: authenticated_user
        Routes->>Client: Protected data
    else Invalid Token
        Auth->>Client: 401 Unauthorized
    end
```

## 🚀 Performance Optimization Paths

### Caching Strategy

```mermaid
graph TB
    subgraph "Cache Layers"
        L1[L1: Memory Cache<br/>Local Variables]
        L2[L2: Redis Cache<br/>Shared Memory]
        L3[L3: Database Cache<br/>LadybugDB Internal]
    end
    
    subgraph "Cache Invalidation"
        TTL[TTL Expiration<br/>Time-based]
        EVENT[Event-based<br/>Data Updates]
        MANUAL[Manual Refresh<br/>Admin Actions]
    end
    
    REQUEST[Request] --> L1
    L1 --> L2
    L2 --> L3
    L3 --> DATABASE[(Database)]
    
    TTL --> L1
    TTL --> L2
    EVENT --> L1
    EVENT --> L2
    MANUAL --> L1
    MANUAL --> L2
    MANUAL --> L3
    
    style L1 fill:#28a745
    style L2 fill:#ffc107
    style L3 fill:#17a2b8
```

## 🔍 Error Handling Paths

### Error Propagation Flow

```mermaid
flowchart TD
    START[Request Start] --> VALIDATE{Input Validation}
    VALIDATE -->|Valid| AUTH{Authentication}
    VALIDATE -->|Invalid| ERROR_400[400 Bad Request]
    
    AUTH -->|Authenticated| BUSINESS[Business Logic]
    AUTH -->|Unauthenticated| ERROR_401[401 Unauthorized]
    
    BUSINESS --> DB{Database Operation}
    DB -->|Success| CACHE[Update Cache]
    DB -->|Error| RETRY{Retry Logic}
    
    RETRY -->|Retry Success| CACHE
    RETRY -->|Max Retries| ERROR_500[500 Internal Error]
    
    CACHE --> LOG[Log Success]
    LOG --> RESPONSE[Success Response]
    
    ERROR_400 --> LOG_ERROR[Log Error]
    ERROR_401 --> LOG_ERROR
    ERROR_500 --> LOG_ERROR
    
    LOG_ERROR --> MONITOR[Update Metrics]
    MONITOR --> ERROR_RESPONSE[Error Response]
    
    style ERROR_400 fill:#dc3545
    style ERROR_401 fill:#fd7e14
    style ERROR_500 fill:#dc3545
    style RESPONSE fill:#28a745
```

## 📈 Monitoring & Observability Paths

### Metrics Collection Flow

```mermaid
graph LR
    subgraph "Application Code"
        ROUTES[API Routes]
        BUSINESS[Business Logic]
        DATABASE[Database Operations]
        ALERTS[Alert System]
    end
    
    subgraph "Metrics Collection"
        PROMETHEUS[Prometheus Metrics]
        LOGS[Structured Logging]
        TRACES[Request Tracing]
        PERF[Performance Monitoring]
    end
    
    subgraph "Observability Stack"
        GRAFANA[Grafana Dashboards]
        ALERT_MANAGER[Alert Manager]
        LOG_AGGREGATOR[Log Aggregation]
    end
    
    ROUTES --> PROMETHEUS
    BUSINESS --> LOGS
    DATABASE --> TRACES
    ALERTS --> PERF
    
    PROMETHEUS --> GRAFANA
    LOGS --> LOG_AGGREGATOR
    TRACES --> GRAFANA
    PERF --> ALERT_MANAGER
    
    style PROMETHEUS fill:#e6522c
    style GRAFANA fill:#f46800
    style ALERT_MANAGER fill:#dc3545
```

## 🧪 Testing Code Paths

### Test Execution Flow

```mermaid
flowchart TD
    START[Test Suite Start] --> UNIT[Unit Tests]
    UNIT --> INTEGRATION[Integration Tests]
    INTEGRATION --> E2E[End-to-End Tests]
    E2E --> PERFORMANCE[Performance Tests]
    
    UNIT --> MOCK{Mock Dependencies}
    MOCK --> ISOLATE[Isolated Testing]
    
    INTEGRATION --> TESTDB[Test Database]
    TESTDB --> SETUP[Test Data Setup]
    
    E2E --> CONTAINERS[Test Containers]
    CONTAINERS --> FULLSTACK[Full Stack Testing]
    
    PERFORMANCE --> BENCHMARK[Benchmark Tests]
    BENCHMARK --> METRICS[Performance Metrics]
    
    ISOLATE --> REPORT[Test Report]
    SETUP --> REPORT
    FULLSTACK --> REPORT
    METRICS --> REPORT
    
    REPORT --> COVERAGE[Coverage Analysis]
    COVERAGE --> QUALITY[Quality Gates]
    
    style UNIT fill:#28a745
    style INTEGRATION fill:#ffc107
    style E2E fill:#17a2b8
    style PERFORMANCE fill:#6f42c1
```

## 📚 Code Organization Best Practices

### Module Dependencies

```mermaid
graph TB
    subgraph "Presentation Layer"
        ROUTES[API Routes]
        DASHBOARD[Dashboard]
        PLUGINS[IDE Plugins]
    end
    
    subgraph "Business Logic Layer"
        SERVICES[Service Classes]
        MANAGERS[Manager Classes]
        PROCESSORS[Processors]
    end
    
    subgraph "Data Access Layer"
        REPOSITORIES[Repository Pattern]
        MODELS[Data Models]
        ADAPTERS[Database Adapters]
    end
    
    subgraph "Infrastructure Layer"
        DATABASE[Database Connections]
        CACHE[Cache Management]
        EXTERNAL[External APIs]
    end
    
    ROUTES --> SERVICES
    DASHBOARD --> SERVICES
    PLUGINS --> SERVICES
    
    SERVICES --> REPOSITORIES
    MANAGERS --> REPOSITORIES
    PROCESSORS --> REPOSITORIES
    
    REPOSITORIES --> DATABASE
    MODELS --> DATABASE
    ADAPTERS --> CACHE
    ADAPTERS --> EXTERNAL
    
    style SERVICES fill:#0073e6
    style REPOSITORIES fill:#28a745
    style DATABASE fill:#2546f0
```

---

**Code Paths Documentation**: Comprehensive technical reference for GraphMemory-IDE  
**Version**: 1.0.0  
**Last Updated**: May 29, 2025  
**Maintainer**: Development Team 