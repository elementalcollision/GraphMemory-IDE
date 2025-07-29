# GraphMemory-IDE Docker Deployment Guide

## Table of Contents
1. [Docker Overview](#docker-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Docker Start](#quick-docker-start)
4. [Docker Architecture](#docker-architecture)
5. [Building Images](#building-images)
6. [Database Containers](#database-containers)
7. [Application Services](#application-services)
8. [Docker Compose Deployment](#docker-compose-deployment)
9. [Production Configuration](#production-configuration)
10. [Networking & Security](#networking-security)
11. [Monitoring & Logging](#monitoring-logging)
12. [Backup & Recovery](#backup-recovery)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance & Updates](#maintenance-updates)

## Docker Overview

This guide provides comprehensive instructions for deploying GraphMemory-IDE using Docker containers. The containerized deployment includes:

- **Multi-Service Architecture**: Separate containers for each service component
- **Database Persistence**: Kuzu graph database, PostgreSQL, and Redis with persistent volumes
- **Scalable Design**: Horizontal scaling support for API and dashboard services
- **Production Ready**: Security, monitoring, and backup configurations
- **Development Support**: Local development environment with hot-reload

### Key Components
- **API Server**: FastAPI-based backend with analytics engine
- **Dashboard**: Streamlit-based interactive dashboard
- **Frontend**: Next.js frontend application
- **PostgreSQL**: Primary relational database
- **Kuzu Database**: Graph database for entity relationships
- **Redis**: Caching and session storage
- **Nginx**: Reverse proxy and load balancer
- **Monitoring**: Prometheus, Grafana, and logging services

## Prerequisites

### Docker Requirements
- **Docker Engine**: Version 24.0+ (recommended)
- **Docker Compose**: Version 2.20+
- **Operating System**: Linux (Ubuntu 20.04+), macOS (12+), Windows (with WSL2)

### Hardware Requirements
- **Minimum**: 8GB RAM, 4 CPU cores, 50GB disk space
- **Recommended**: 16GB+ RAM, 8+ CPU cores, 100GB+ SSD
- **Production**: 32GB+ RAM, 16+ CPU cores, 500GB+ NVMe SSD

### Network Requirements
- Internet connection for image downloads
- Available ports: 80, 443, 8000, 8501, 3000, 5432, 6379, 9090, 3001

### Installation Commands

#### Ubuntu/Debian
```bash
# Update package index
sudo apt update

# Install Docker Engine
sudo apt install docker.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app

# Verify installation
docker --version
docker compose version
```

#### CentOS/RHEL
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

## Quick Docker Start

For immediate deployment with default configuration:

```bash
# Clone repository
git clone https://github.com/your-org/GraphMemory-IDE.git
cd GraphMemory-IDE

# Create environment file
cp .env.example .env.docker

# Build and start all services
docker compose up -d

# Verify deployment
docker compose ps
docker compose logs -f

# Access services
# Dashboard: http://localhost:8501
# API: http://localhost:8000
# Frontend: http://localhost:3000
# Monitoring: http://localhost:9090 (Prometheus), http://localhost:3001 (Grafana)
```

## Docker Architecture

### Service Dependencies
```mermaid
graph TD
    A[Frontend] --> B[API Server]
    C[Dashboard] --> B
    B --> D[PostgreSQL]
    B --> E[Redis]
    B --> F[Kuzu Database]
    G[Nginx] --> A
    G --> B
    G --> C
    H[Prometheus] --> B
    I[Grafana] --> H
```

### Container Network Layout
- **Frontend Network**: `graphmemory-frontend` (bridge)
- **Backend Network**: `graphmemory-backend` (bridge)
- **Database Network**: `graphmemory-db` (internal)
- **Monitoring Network**: `graphmemory-monitoring` (bridge)

### Volume Structure
```
graphmemory-data/
├── postgresql/          # PostgreSQL data
├── kuzu/               # Kuzu graph database
├── redis/              # Redis persistence
├── logs/               # Application logs
├── backups/            # Database backups
├── uploads/            # File uploads
└── ssl/                # SSL certificates
```

## Building Images

### Directory Structure
```
docker/
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── entrypoint.sh
├── dashboard/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── entrypoint.sh
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── nginx.conf
└── nginx/
    ├── Dockerfile
    ├── nginx.conf
    └── ssl/
```

### API Server Image
Create `docker/api/Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY scripts/ ./scripts/
COPY .env.docker .env

# Create directories
RUN mkdir -p /app/data/kuzu /app/logs /app/backups

# Set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dashboard Image
Create `docker/dashboard/Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install dependencies
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard code
COPY dashboard/ .

# Create user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/health || exit 1

# Expose port
EXPOSE 8501

# Start command
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Frontend Image
Create `docker/frontend/Dockerfile`:
```dockerfile
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci --only=production

# Copy source code
COPY frontend/ .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY docker/frontend/nginx.conf /etc/nginx/nginx.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

### Build Commands
```bash
# Build all images
docker compose build

# Build specific image
docker compose build api
docker compose build dashboard
docker compose build frontend

# Build with no cache
docker compose build --no-cache

# Build and push to registry
docker compose build
docker compose push
```

## Database Containers

### PostgreSQL Configuration
```yaml
# docker-compose.yml - PostgreSQL service
postgresql:
  image: postgres:15-alpine
  container_name: graphmemory-postgres
  environment:
    POSTGRES_DB: graphmemory
    POSTGRES_USER: graphmemory
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=C"
  volumes:
    - postgresql_data:/var/lib/postgresql/data
    - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/01_init.sql:ro
    - ./backups:/backups
  ports:
    - "5432:5432"
  networks:
    - graphmemory-db
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=64MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U graphmemory -d graphmemory"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
  restart: unless-stopped
```

### Kuzu Database Configuration
```yaml
# Kuzu as a volume-mounted service
kuzu-init:
  image: alpine:latest
  container_name: graphmemory-kuzu-init
  volumes:
    - kuzu_data:/data/kuzu
    - ./scripts/init_kuzu.sh:/init_kuzu.sh:ro
  command: >
    sh -c "
    if [ ! -f /data/kuzu/.initialized ]; then
      echo 'Initializing Kuzu database...'
      mkdir -p /data/kuzu
      chmod 755 /data/kuzu
      touch /data/kuzu/.initialized
      echo 'Kuzu database initialized'
    else
      echo 'Kuzu database already initialized'
    fi
    "
  networks:
    - graphmemory-db
```

### Redis Configuration
```yaml
# Redis service
redis:
  image: redis:7-alpine
  container_name: graphmemory-redis
  environment:
    REDIS_PASSWORD: ${REDIS_PASSWORD}
  volumes:
    - redis_data:/data
    - ./docker/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
  ports:
    - "6379:6379"
  networks:
    - graphmemory-db
  command: redis-server /usr/local/etc/redis/redis.conf --requirepass ${REDIS_PASSWORD}
  healthcheck:
    test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
  restart: unless-stopped
```

### Database Initialization
Create `scripts/init_db.sql`:
```sql
-- Initialize GraphMemory database schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create initial tables
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

## Application Services

### Complete Docker Compose Configuration
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  # Database Services
  postgresql:
    image: postgres:15-alpine
    container_name: graphmemory-postgres
    environment:
      POSTGRES_DB: graphmemory
      POSTGRES_USER: graphmemory
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
    volumes:
      - postgresql_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - graphmemory-db
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U graphmemory"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: graphmemory-redis
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD:-changeme}
    volumes:
      - redis_data:/data
    networks:
      - graphmemory-db
    command: redis-server --requirepass ${REDIS_PASSWORD:-changeme}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  kuzu-init:
    image: alpine:latest
    container_name: graphmemory-kuzu-init
    volumes:
      - kuzu_data:/data/kuzu
    command: >
      sh -c "
      mkdir -p /data/kuzu
      chmod 755 /data/kuzu
      if [ ! -f /data/kuzu/.initialized ]; then
        touch /data/kuzu/.initialized
        echo 'Kuzu database initialized'
      fi
      "

  # Application Services
  api:
    build:
      context: .
      dockerfile: docker/api/Dockerfile
    container_name: graphmemory-api
    environment:
      - DATABASE_URL=postgresql://graphmemory:${POSTGRES_PASSWORD:-changeme}@postgresql:5432/graphmemory
      - REDIS_URL=redis://:${REDIS_PASSWORD:-changeme}@redis:6379/0
      - KUZU_DATABASE_PATH=/app/data/kuzu
      - SECRET_KEY=${SECRET_KEY:-your-secret-key-change-this}
      - ENVIRONMENT=${ENVIRONMENT:-production}
    volumes:
      - kuzu_data:/app/data/kuzu
      - app_logs:/app/logs
      - app_backups:/app/backups
    networks:
      - graphmemory-backend
      - graphmemory-db
    ports:
      - "8000:8000"
    depends_on:
      postgresql:
        condition: service_healthy
      redis:
        condition: service_healthy
      kuzu-init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  dashboard:
    build:
      context: .
      dockerfile: docker/dashboard/Dockerfile
    container_name: graphmemory-dashboard
    environment:
      - API_URL=http://api:8000
      - REDIS_URL=redis://:${REDIS_PASSWORD:-changeme}@redis:6379/1
    networks:
      - graphmemory-backend
      - graphmemory-db
    ports:
      - "8501:8501"
    depends_on:
      api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: .
      dockerfile: docker/frontend/Dockerfile
    container_name: graphmemory-frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_DASHBOARD_URL=http://localhost:8501
    networks:
      - graphmemory-frontend
    ports:
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped

  # Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: graphmemory-nginx
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - graphmemory-frontend
      - graphmemory-backend
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - dashboard
      - frontend
    restart: unless-stopped

  # Monitoring Services
  prometheus:
    image: prom/prometheus:latest
    container_name: graphmemory-prometheus
    volumes:
      - ./monitoring/prometheus:/etc/prometheus:ro
      - prometheus_data:/prometheus
    networks:
      - graphmemory-monitoring
      - graphmemory-backend
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: graphmemory-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning:ro
    networks:
      - graphmemory-monitoring
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

networks:
  graphmemory-frontend:
    driver: bridge
  graphmemory-backend:
    driver: bridge
  graphmemory-db:
    driver: bridge
    internal: true
  graphmemory-monitoring:
    driver: bridge

volumes:
  postgresql_data:
    driver: local
  redis_data:
    driver: local
  kuzu_data:
    driver: local
  app_logs:
    driver: local
  app_backups:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
```

## Docker Compose Deployment

### Environment Configuration
Create `.env.docker`:
```env
# Environment
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=your-super-secret-key-change-this-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Database Passwords
POSTGRES_PASSWORD=secure_postgres_password_here
REDIS_PASSWORD=secure_redis_password_here

# Database URLs
DATABASE_URL=postgresql://graphmemory:${POSTGRES_PASSWORD}@postgresql:5432/graphmemory
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
KUZU_DATABASE_PATH=/app/data/kuzu

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8501

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501

# Monitoring
GRAFANA_PASSWORD=secure_grafana_password

# Logging
LOG_LEVEL=INFO

# SSL (if using HTTPS)
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

### Deployment Commands
```bash
# Start all services
docker compose up -d

# Start specific services
docker compose up -d postgresql redis
docker compose up -d api dashboard

# Scale services
docker compose up -d --scale api=3 --scale dashboard=2

# View logs
docker compose logs -f
docker compose logs -f api
docker compose logs -f postgresql

# Check service status
docker compose ps
docker compose top

# Stop services
docker compose stop
docker compose down

# Remove everything (including volumes)
docker compose down -v --remove-orphans
```

### Service Health Monitoring
```bash
# Check health of all services
docker compose ps

# Check individual service health
docker inspect graphmemory-api --format='{{.State.Health.Status}}'
docker inspect graphmemory-postgres --format='{{.State.Health.Status}}'

# Monitor resource usage
docker stats

# View container logs
docker logs -f graphmemory-api
docker logs -f graphmemory-postgres --tail=100
```

## Production Configuration

### SSL/TLS Configuration
Create `docker/nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8000;
    }
    
    upstream dashboard_backend {
        server dashboard:8501;
    }
    
    upstream frontend_backend {
        server frontend:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # HTTPS configuration
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Frontend
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        # Dashboard
        location /dashboard/ {
            proxy_pass http://dashboard_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### Resource Limits
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  dashboard:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  postgresql:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=512MB
      -c effective_cache_size=2GB
      -c maintenance_work_mem=128MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=32MB

  redis:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
    command: >
      redis-server
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
```

### Production Deployment
```bash
# Deploy with production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Use specific environment file
docker compose --env-file .env.production up -d

# Deploy with scaling
docker compose up -d --scale api=3 --scale dashboard=2
```

## Networking & Security

### Network Security Configuration
```yaml
# Security-focused network configuration
networks:
  frontend:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  
  backend:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.21.0.0/24
  
  database:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.22.0.0/24
```

### Firewall Configuration
```bash
# UFW firewall rules
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 9090/tcp    # Prometheus (if external access needed)
sudo ufw deny 5432/tcp     # Block direct PostgreSQL access
sudo ufw deny 6379/tcp     # Block direct Redis access
sudo ufw enable
```

### Container Security
```dockerfile
# Security hardening in Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set security options
USER appuser
WORKDIR /app

# Remove unnecessary packages
RUN apt-get autoremove -y && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/*

# Set security labels
LABEL security.scan="enabled"
LABEL security.level="high"
```

## Monitoring & Logging

### Prometheus Configuration
Create `monitoring/prometheus/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'graphmemory-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'graphmemory-dashboard'
    static_configs:
      - targets: ['dashboard:8501']
    metrics_path: '/metrics'

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboard Configuration
Create `monitoring/grafana/provisioning/dashboards/dashboard.json`:
```json
{
  "dashboard": {
    "id": null,
    "title": "GraphMemory-IDE Monitoring",
    "tags": ["graphmemory"],
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends"
          }
        ]
      }
    ]
  }
}
```

### Centralized Logging
```yaml
# Add to docker-compose.yml
services:
  elasticsearch:
    image: elasticsearch:7.17.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - logging

  logstash:
    image: logstash:7.17.0
    volumes:
      - ./monitoring/logstash:/usr/share/logstash/pipeline:ro
    networks:
      - logging
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:7.17.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    networks:
      - logging
    depends_on:
      - elasticsearch
```

## Backup & Recovery

### Database Backup Configuration
Create `scripts/backup.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker compose exec -T postgresql pg_dump -U graphmemory graphmemory > \
    "${BACKUP_DIR}/postgresql_${TIMESTAMP}.sql"

# Kuzu backup (copy entire directory)
docker compose exec -T api tar -czf "/app/backups/kuzu_${TIMESTAMP}.tar.gz" \
    -C /app/data kuzu/

# Redis backup
docker compose exec -T redis redis-cli --rdb "/data/dump_${TIMESTAMP}.rdb"
docker compose cp redis:/data/dump_${TIMESTAMP}.rdb "${BACKUP_DIR}/"

# Cleanup old backups (keep last 7 days)
find "${BACKUP_DIR}" -name "*.sql" -mtime +7 -delete
find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +7 -delete
find "${BACKUP_DIR}" -name "*.rdb" -mtime +7 -delete

echo "Backup completed: ${TIMESTAMP}"
```

### Automated Backup with Cron
```bash
# Add to crontab
0 2 * * * /path/to/GraphMemory-IDE/scripts/backup.sh

# Or use Docker cron container
docker run -d \
  --name graphmemory-backup \
  -v $(pwd):/app \
  -v $(pwd)/scripts:/scripts \
  --network graphmemory_default \
  alpine/cron:latest \
  sh -c "echo '0 2 * * * /scripts/backup.sh' | crontab - && crond -f"
```

### Recovery Procedures
```bash
# Restore PostgreSQL
docker compose exec -T postgresql psql -U graphmemory -d graphmemory < \
    backups/postgresql_20240107_020000.sql

# Restore Kuzu
docker compose down kuzu-init
docker volume rm graphmemory_kuzu_data
docker volume create graphmemory_kuzu_data
docker compose run --rm -v $(pwd)/backups:/backups api \
    tar -xzf /backups/kuzu_20240107_020000.tar.gz -C /app/data/

# Restore Redis
docker compose exec redis redis-cli FLUSHALL
docker compose cp backups/dump_20240107_020000.rdb redis:/data/dump.rdb
docker compose restart redis
```

## Troubleshooting

### Common Docker Issues

#### Container Won't Start
```bash
# Check container logs
docker compose logs api
docker compose logs postgresql

# Check container status
docker compose ps
docker container inspect graphmemory-api

# Check resource usage
docker stats
df -h  # Check disk space
free -h  # Check memory

# Restart specific service
docker compose restart api
docker compose up -d --force-recreate api
```

#### Database Connection Issues
```bash
# Test PostgreSQL connection
docker compose exec postgresql psql -U graphmemory -d graphmemory -c "SELECT 1;"

# Check PostgreSQL logs
docker compose logs postgresql

# Test Redis connection
docker compose exec redis redis-cli ping

# Check network connectivity
docker compose exec api ping postgresql
docker compose exec api ping redis
```

#### Network Issues
```bash
# List Docker networks
docker network ls

# Inspect network configuration
docker network inspect graphmemory_backend

# Check container network settings
docker inspect graphmemory-api | grep -A 10 NetworkSettings

# Test inter-container connectivity
docker compose exec api curl http://postgresql:5432
docker compose exec dashboard curl http://api:8000/health
```

#### Volume and Data Issues
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect graphmemory_postgresql_data

# Check volume usage
docker system df

# Backup and restore volume
docker run --rm -v graphmemory_postgresql_data:/data -v $(pwd):/backup \
    alpine tar czf /backup/postgresql_data.tar.gz /data
```

### Performance Issues

#### Memory Problems
```bash
# Check memory usage
docker stats --no-stream

# Increase memory limits
# Edit docker-compose.yml:
services:
  api:
    mem_limit: 4g
    memswap_limit: 4g

# Clear unused Docker resources
docker system prune -a
docker volume prune
```

#### CPU Issues
```bash
# Monitor CPU usage
docker stats

# Limit CPU usage
services:
  api:
    cpus: '2.0'
    cpu_shares: 1024

# Scale horizontally
docker compose up -d --scale api=3
```

#### Disk Space Issues
```bash
# Check disk usage
docker system df
du -sh /var/lib/docker/

# Clean up Docker resources
docker system prune -a --volumes
docker container prune
docker image prune -a
docker volume prune

# Move Docker data directory
sudo systemctl stop docker
sudo mv /var/lib/docker /new/path/docker
sudo ln -s /new/path/docker /var/lib/docker
sudo systemctl start docker
```

### Debug Mode Deployment
```yaml
# docker-compose.debug.yml
version: '3.8'

services:
  api:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    ports:
      - "5678:5678"  # Debug port
    volumes:
      - ./server:/app/server:ro  # Mount source for hot reload
    command: >
      sh -c "
      pip install debugpy &&
      python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
      "

  dashboard:
    environment:
      - DEBUG=true
    volumes:
      - ./dashboard:/app:ro
    command: streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --logger.level=debug
```

## Maintenance & Updates

### Regular Maintenance Tasks

#### Daily Monitoring
```bash
# Health check script
#!/bin/bash
echo "=== GraphMemory-IDE Health Check ==="
echo "Date: $(date)"
echo

echo "Container Status:"
docker compose ps

echo -e "\nResource Usage:"
docker stats --no-stream

echo -e "\nDisk Usage:"
docker system df

echo -e "\nAPI Health:"
curl -s http://localhost:8000/health | jq .

echo -e "\nDatabase Status:"
docker compose exec -T postgresql pg_isready -U graphmemory
```

#### Weekly Maintenance
```bash
# Weekly maintenance script
#!/bin/bash

echo "Starting weekly maintenance..."

# Update container images
docker compose pull

# Restart services with new images
docker compose up -d

# Clean up unused resources
docker image prune -f
docker container prune -f

# Run database maintenance
docker compose exec postgresql psql -U graphmemory -d graphmemory -c "VACUUM ANALYZE;"

# Check logs for errors
docker compose logs --since=168h | grep -i error

echo "Weekly maintenance completed"
```

#### Update Procedures
```bash
# Update to latest version
git pull origin main

# Backup before update
./scripts/backup.sh

# Build new images
docker compose build --no-cache

# Deploy with downtime
docker compose down
docker compose up -d

# Or rolling update (no downtime)
docker compose up -d --scale api=6  # Scale up
sleep 30
docker compose up -d --scale api=3  # Scale back down
```

### Monitoring Scripts
```bash
# Container health monitoring
#!/bin/bash
CONTAINERS="graphmemory-api graphmemory-dashboard graphmemory-postgres graphmemory-redis"

for container in $CONTAINERS; do
    health=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null)
    if [ "$health" != "healthy" ]; then
        echo "ALERT: Container $container is $health"
        # Send alert (email, Slack, etc.)
    fi
done

# Resource monitoring
memory_usage=$(docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | grep graphmemory)
echo "Memory Usage:"
echo "$memory_usage"

# Check if any container is using > 80% memory
# Add alerting logic here
```

### Scaling Operations
```bash
# Horizontal scaling
docker compose up -d --scale api=5 --scale dashboard=3

# Load balancer health check
for i in {1..5}; do
    curl -s http://localhost:8000/health
    sleep 1
done

# Monitor during scaling
watch -n 2 "docker compose ps && echo && docker stats --no-stream"
```

## Security Best Practices

### Container Security Checklist
- [ ] Use official base images
- [ ] Run containers as non-root users
- [ ] Scan images for vulnerabilities
- [ ] Use read-only root filesystems where possible
- [ ] Limit container capabilities
- [ ] Use secrets management
- [ ] Enable Docker Content Trust
- [ ] Regular security updates

### Implementation Examples
```bash
# Scan images for vulnerabilities
docker scout cves graphmemory-api:latest

# Use Docker secrets
echo "mypassword" | docker secret create postgres_password -
# Reference in compose:
secrets:
  postgres_password:
    external: true

# Enable read-only filesystem
services:
  api:
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache
```

---

This completes the comprehensive Docker deployment guide for GraphMemory-IDE. The guide covers all aspects of containerized deployment from basic setup to production-ready configurations with monitoring, security, and maintenance procedures. 