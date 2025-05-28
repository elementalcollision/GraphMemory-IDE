# Analytics Engine - Production Deployment Guide

## Overview

This guide covers the production deployment of the GraphMemory-IDE Analytics Engine Phase 3, including GPU acceleration, performance monitoring, and enterprise-grade configuration.

## 🏗️ Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Load Balancer<br/>nginx/traefik]
        SSL[SSL Termination]
    end
    
    subgraph "Application Layer"
        API[Analytics API<br/>FastAPI]
        Worker[Background Workers<br/>Celery]
        Cache[Redis Cache<br/>Analytics Cache]
    end
    
    subgraph "Analytics Engine"
        Engine[Analytics Engine Core]
        GPU[GPU Acceleration<br/>NVIDIA cuGraph]
        Monitor[Performance Monitor<br/>Prometheus Metrics]
        Concurrent[Concurrent Processing<br/>Thread/Process Pools]
    end
    
    subgraph "Data Layer"
        KuzuDB[(Kuzu GraphDB<br/>Embedded)]
        Redis[(Redis<br/>Cache & Sessions)]
        Prometheus[(Prometheus<br/>Metrics Storage)]
    end
    
    subgraph "Monitoring Stack"
        Grafana[Grafana<br/>Dashboards]
        AlertManager[Alert Manager<br/>Notifications]
        Logs[Log Aggregation<br/>ELK/Loki]
    end
    
    LB --> SSL
    SSL --> API
    API --> Worker
    API --> Cache
    
    API --> Engine
    Engine --> GPU
    Engine --> Monitor
    Engine --> Concurrent
    
    Engine --> KuzuDB
    Cache --> Redis
    Monitor --> Prometheus
    
    Prometheus --> Grafana
    Prometheus --> AlertManager
    API --> Logs
    
    style "Analytics Engine" fill:#e8f5e8
    style "Monitoring Stack" fill:#fce4ec
    style "Data Layer" fill:#fff3e0
```

## 🚀 Quick Deployment

### Docker Compose (Recommended)

```yaml
version: '3.8'

services:
  analytics-engine:
    build: 
      context: ../server
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      # Core Configuration
      - KUZU_DB_PATH=/database
      - REDIS_URL=redis://redis:6379
      
      # Phase 3 Configuration
      - GPU_ACCELERATION_ENABLED=true
      - CUGRAPH_BACKEND_ENABLED=true
      - PROMETHEUS_ENABLED=true
      - PERFORMANCE_MONITORING_ENABLED=true
      
      # Concurrent Processing
      - MAX_THREAD_WORKERS=32
      - MAX_PROCESS_WORKERS=8
      
      # Performance Tuning
      - ALGORITHM_CACHE_TTL=3600
      - GPU_MEMORY_LIMIT=8GB
      - BENCHMARK_MODE=false
    volumes:
      - kuzu-data:/database
      - ./logs:/app/logs
    depends_on:
      - redis
      - prometheus
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  kuzu-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

### Start Deployment

```bash
# Clone repository
git clone <repository>
cd GraphMemory-IDE

# Create monitoring configuration
mkdir -p docker/monitoring/grafana/{dashboards,datasources}

# Start services with GPU support
docker compose -f docker/docker-compose-analytics.yml up -d

# Verify services
docker compose ps
curl http://localhost:8080/analytics/phase3/status
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `GPU_ACCELERATION_ENABLED` | `true` | Enable GPU acceleration | No |
| `CUGRAPH_BACKEND_ENABLED` | `true` | Enable cuGraph backend | No |
| `MAX_THREAD_WORKERS` | `auto` | Thread pool size | No |
| `MAX_PROCESS_WORKERS` | `auto` | Process pool size | No |
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics | No |
| `PERFORMANCE_MONITORING_ENABLED` | `true` | Enable performance monitoring | No |
| `ALGORITHM_CACHE_TTL` | `3600` | Cache TTL in seconds | No |
| `GPU_MEMORY_LIMIT` | `8GB` | GPU memory limit | No |
| `BENCHMARK_MODE` | `false` | Enable benchmark mode | No |

### GPU Configuration

#### Prerequisites

```bash
# Install NVIDIA Docker runtime
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

#### GPU Configuration File

```yaml
# gpu-config.yml
gpu:
  enabled: true
  memory_limit: "8GB"
  algorithms:
    - "pagerank"
    - "betweenness"
    - "louvain"
    - "connected_components"
  fallback_threshold: 1000  # nodes
  memory_monitoring: true
```

#### Verification

```bash
# Test GPU availability
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Test cuGraph installation
docker exec analytics-engine python -c "import cugraph; print('cuGraph available')"
```

### Performance Monitoring Configuration

#### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "analytics_rules.yml"

scrape_configs:
  - job_name: 'analytics-engine'
    static_configs:
      - targets: ['analytics-engine:8080']
    metrics_path: '/analytics/monitoring/prometheus'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "Analytics Engine Performance",
    "panels": [
      {
        "title": "Algorithm Execution Time",
        "type": "graph",
        "targets": [
          {
            "expr": "analytics_operation_duration_seconds",
            "legendFormat": "{{algorithm}} - {{backend}}"
          }
        ]
      },
      {
        "title": "GPU Memory Usage",
        "type": "singlestat",
        "targets": [
          {
            "expr": "analytics_gpu_memory_percent",
            "legendFormat": "GPU Memory %"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(analytics_cache_hits_total[5m]) / (rate(analytics_cache_hits_total[5m]) + rate(analytics_cache_misses_total[5m]))",
            "legendFormat": "Hit Rate"
          }
        ]
      }
    ]
  }
}
```

## 🔍 Monitoring & Alerting

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `analytics_operation_duration_seconds` | Algorithm execution time | > 30s |
| `analytics_gpu_memory_percent` | GPU memory usage | > 90% |
| `analytics_system_cpu_percent` | CPU usage | > 80% |
| `analytics_system_memory_percent` | Memory usage | > 85% |
| `analytics_cache_hit_rate` | Cache efficiency | < 70% |
| `analytics_component_health` | Component status | != 1 |

### Alert Rules

```yaml
# monitoring/analytics_rules.yml
groups:
  - name: analytics_engine
    rules:
      - alert: HighGPUMemoryUsage
        expr: analytics_gpu_memory_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High GPU memory usage detected"
          description: "GPU memory usage is {{ $value }}%"

      - alert: SlowAlgorithmExecution
        expr: analytics_operation_duration_seconds > 30
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Algorithm execution is slow"
          description: "{{ $labels.algorithm }} took {{ $value }}s to execute"

      - alert: LowCacheHitRate
        expr: rate(analytics_cache_hits_total[5m]) / (rate(analytics_cache_hits_total[5m]) + rate(analytics_cache_misses_total[5m])) < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

## 🚀 Production Deployment

### Kubernetes Deployment

```yaml
# k8s/analytics-engine-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-engine
  labels:
    app: analytics-engine
spec:
  replicas: 3
  selector:
    matchLabels:
      app: analytics-engine
  template:
    metadata:
      labels:
        app: analytics-engine
    spec:
      containers:
      - name: analytics-engine
        image: graphmemory/analytics-engine:latest
        ports:
        - containerPort: 8080
        env:
        - name: GPU_ACCELERATION_ENABLED
          value: "true"
        - name: PROMETHEUS_ENABLED
          value: "true"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
            nvidia.com/gpu: 1
          limits:
            memory: "8Gi"
            cpu: "4000m"
            nvidia.com/gpu: 1
        livenessProbe:
          httpGet:
            path: /analytics/monitoring/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /analytics/phase3/status
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      nodeSelector:
        accelerator: nvidia-tesla-k80
```

### Service Configuration

```yaml
# k8s/analytics-engine-service.yml
apiVersion: v1
kind: Service
metadata:
  name: analytics-engine-service
spec:
  selector:
    app: analytics-engine
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

### Ingress Configuration

```yaml
# k8s/analytics-engine-ingress.yml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: analytics-engine-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - analytics.yourdomain.com
    secretName: analytics-tls
  rules:
  - host: analytics.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: analytics-engine-service
            port:
              number: 80
```

## 🔧 Performance Tuning

### GPU Optimization

```python
# config/gpu_config.py
GPU_CONFIG = {
    "memory_limit": "8GB",
    "algorithms": {
        "pagerank": {
            "min_nodes": 100,
            "max_nodes": 100000,
            "memory_factor": 1.5
        },
        "betweenness": {
            "min_nodes": 50,
            "max_nodes": 10000,
            "memory_factor": 2.0
        }
    },
    "fallback_threshold": 1000,
    "monitoring": {
        "memory_check_interval": 30,
        "performance_logging": True
    }
}
```

### Concurrent Processing Tuning

```python
# config/concurrent_config.py
CONCURRENT_CONFIG = {
    "thread_workers": {
        "min": 4,
        "max": 64,
        "auto_scale": True,
        "scale_factor": 2
    },
    "process_workers": {
        "min": 2,
        "max": 16,
        "auto_scale": True,
        "scale_factor": 1
    },
    "task_timeout": 300,
    "health_check_interval": 60
}
```

### Cache Configuration

```python
# config/cache_config.py
CACHE_CONFIG = {
    "redis": {
        "url": "redis://redis:6379",
        "max_connections": 100,
        "retry_on_timeout": True
    },
    "ttl": {
        "centrality": 3600,
        "community": 1800,
        "clustering": 2400,
        "anomalies": 900
    },
    "compression": True,
    "serialization": "pickle"
}
```

## 🔍 Health Checks & Monitoring

### Health Check Endpoints

```bash
# Component health
curl http://localhost:8080/analytics/monitoring/health

# GPU status
curl http://localhost:8080/analytics/gpu/status

# Performance metrics
curl http://localhost:8080/analytics/performance/metrics

# Prometheus metrics
curl http://localhost:8080/analytics/monitoring/prometheus
```

### Monitoring Dashboard URLs

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Analytics API**: http://localhost:8080/docs

## 🚨 Troubleshooting

### Common Issues

#### GPU Not Detected

```bash
# Check NVIDIA drivers
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Check cuGraph installation
docker exec analytics-engine python -c "import cugraph; print('OK')"
```

#### High Memory Usage

```bash
# Check memory usage
docker stats analytics-engine

# Check GPU memory
nvidia-smi

# Restart with memory limits
docker compose restart analytics-engine
```

#### Performance Issues

```bash
# Check concurrent processing status
curl http://localhost:8080/analytics/performance/metrics

# Run benchmarks
curl -X POST http://localhost:8080/analytics/benchmarks/run

# Check cache hit rate
curl http://localhost:8080/analytics/monitoring/prometheus | grep cache_hit
```

### Log Analysis

```bash
# View application logs
docker compose logs -f analytics-engine

# View performance logs
docker exec analytics-engine tail -f /app/logs/performance.log

# View error logs
docker exec analytics-engine tail -f /app/logs/error.log
```

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] NVIDIA drivers installed (if using GPU)
- [ ] Docker with GPU support configured
- [ ] Redis server available
- [ ] Prometheus/Grafana configured
- [ ] SSL certificates ready (production)
- [ ] Environment variables configured
- [ ] Resource limits set appropriately

### Post-Deployment

- [ ] Health checks passing
- [ ] GPU acceleration working (if enabled)
- [ ] Prometheus metrics collecting
- [ ] Grafana dashboards displaying data
- [ ] Cache hit rate > 70%
- [ ] All API endpoints responding
- [ ] Performance benchmarks within targets
- [ ] Alerts configured and tested

### Production Readiness

- [ ] Load balancer configured
- [ ] SSL/TLS enabled
- [ ] Monitoring and alerting active
- [ ] Backup procedures in place
- [ ] Disaster recovery plan tested
- [ ] Security scanning completed
- [ ] Performance testing completed
- [ ] Documentation updated

---

*This deployment guide ensures production-ready deployment of the Analytics Engine Phase 3 with GPU acceleration, comprehensive monitoring, and enterprise-grade configuration.* 