# Operations Guide

## Table of Contents
- [Production Deployment](#production-deployment)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Performance Tuning](#performance-tuning)
- [Security Operations](#security-operations)
- [Maintenance Procedures](#maintenance-procedures)
- [Troubleshooting](#troubleshooting)
- [Scaling and Load Management](#scaling-and-load-management)

## Production Deployment

### Pre-Deployment Checklist

#### Infrastructure Requirements
- [ ] **Compute Resources**
  - Minimum: 4 CPU cores, 8GB RAM, 100GB SSD
  - Recommended: 8 CPU cores, 16GB RAM, 500GB NVMe SSD
  - Network: 1Gbps bandwidth, low latency (<10ms)

- [ ] **Operating System**
  - Ubuntu 22.04 LTS or CentOS 8+ (recommended)
  - Docker 24.0+ and Docker Compose 2.0+
  - OrbStack (for macOS development environments)

- [ ] **Security Requirements**
  - SSL/TLS certificates for HTTPS
  - Firewall configuration (ports 80, 443, 8080, 8081)
  - SSH key-based authentication
  - Regular security updates enabled

#### Environment Configuration

```bash
# Production environment variables
cat > .env.production << EOF
# Application Configuration
NODE_ENV=production
GRAPHMEMORY_ENV=production
LOG_LEVEL=info

# Database Configuration
KUZU_DB_PATH=/data/kuzu
KUZU_BUFFER_POOL_SIZE=4GB
KUZU_MAX_CONNECTIONS=100

# MCP Server Configuration
MCP_PORT=8080
MCP_HOST=0.0.0.0
MCP_MAX_CONNECTIONS=1000
MCP_TIMEOUT=30000

# Kestra Configuration
KESTRA_PORT=8081
KESTRA_DB_URL=jdbc:postgresql://postgres:5432/kestra
KESTRA_STORAGE_TYPE=local
KESTRA_STORAGE_LOCAL_BASE_PATH=/data/kestra

# Security Configuration
MTLS_ENABLED=true
MTLS_CERT_DIR=/etc/ssl/graphmemory
MTLS_PORT=50051

# Monitoring Configuration
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
GRAFANA_ENABLED=true
GRAFANA_PORT=3000

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=graphmemory-backups
EOF
```

### Deployment Steps

#### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directories
sudo mkdir -p /opt/graphmemory/{data,logs,backups,ssl}
sudo chown -R $USER:$USER /opt/graphmemory
```

#### 2. SSL Certificate Setup

```bash
# Generate SSL certificates (Let's Encrypt recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# Or use the provided mTLS setup script
./scripts/setup-mtls.sh --production
```

#### 3. Deploy Application

```bash
# Clone repository
git clone https://github.com/elementalcollision/GraphMemory-IDE.git
cd GraphMemory-IDE

# Copy production configuration
cp .env.production .env

# Deploy with security hardening
./scripts/deploy-secure.sh --production

# Verify deployment
docker-compose ps
docker-compose logs -f
```

#### 4. Post-Deployment Verification

```bash
# Health checks
curl -k https://localhost:8080/health
curl -k https://localhost:8081/health

# Security validation
./monitoring/resource-monitor.sh --security-check

# Performance baseline
./scripts/performance-test.sh --baseline
```

### Production Docker Compose

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  mcp-server:
    build:
      context: .
      dockerfile: docker/mcp-server/Dockerfile
    ports:
      - "8080:8080"
      - "50051:50051"  # mTLS port
    environment:
      - NODE_ENV=production
      - MCP_PORT=8080
      - MTLS_ENABLED=true
    volumes:
      - ./data:/app/data:ro
      - ./logs:/app/logs
      - /etc/ssl/graphmemory:/etc/ssl/graphmemory:ro
    security_opt:
      - seccomp:./docker/security/seccomp-profile.json
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  kestra:
    image: kestra/kestra:latest
    ports:
      - "8081:8081"
    environment:
      - KESTRA_CONFIGURATION_PATH=/app/kestra.yml
    volumes:
      - ./kestra.yml:/app/kestra.yml:ro
      - ./data/kestra:/app/data
      - ./logs/kestra:/app/logs
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=200m
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password_here
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - mcp-server
      - kestra
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Monitoring and Alerting

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'graphmemory-mcp'
    static_configs:
      - targets: ['mcp-server:8080']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'graphmemory-kestra'
    static_configs:
      - targets: ['kestra:8081']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'docker'
    static_configs:
      - targets: ['docker-exporter:9323']
```

### Alert Rules

```yaml
# monitoring/alert_rules.yml
groups:
  - name: graphmemory_alerts
    rules:
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Memory usage is above 85% for more than 5 minutes"

      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 5 minutes"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} service is down"

      - alert: DatabaseConnectionFailure
        expr: kuzu_connection_errors_total > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failures"
          description: "Multiple database connection failures detected"

      - alert: DiskSpaceUsage
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space usage critical"
          description: "Disk usage is above 90%"
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "GraphMemory-IDE Operations Dashboard",
    "panels": [
      {
        "title": "System Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "up",
            "legendFormat": "Services Up"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes",
            "legendFormat": "Used Memory"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU Usage %"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      }
    ]
  }
}
```

### Custom Monitoring Script

```bash
#!/bin/bash
# monitoring/health-monitor.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/graphmemory/health-monitor.log"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local timeout="${3:-10}"
    
    if curl -f -s --max-time "$timeout" "$health_url" > /dev/null; then
        log "✅ $service_name is healthy"
        return 0
    else
        log "❌ $service_name health check failed"
        return 1
    fi
}

check_disk_space() {
    local threshold="${1:-90}"
    local usage
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -gt "$threshold" ]; then
        log "❌ Disk usage critical: ${usage}%"
        return 1
    else
        log "✅ Disk usage normal: ${usage}%"
        return 0
    fi
}

check_memory_usage() {
    local threshold="${1:-85}"
    local usage
    usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$usage" -gt "$threshold" ]; then
        log "❌ Memory usage high: ${usage}%"
        return 1
    else
        log "✅ Memory usage normal: ${usage}%"
        return 0
    fi
}

send_alert() {
    local message="$1"
    
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$ALERT_WEBHOOK"
    fi
    
    # Send email if configured
    if command -v mail > /dev/null; then
        echo "$message" | mail -s "GraphMemory-IDE Alert" admin@example.com
    fi
}

main() {
    log "Starting health monitoring check"
    
    local failed_checks=0
    
    # Check service health
    if ! check_service_health "MCP Server" "http://localhost:8080/health"; then
        ((failed_checks++))
    fi
    
    if ! check_service_health "Kestra" "http://localhost:8081/health"; then
        ((failed_checks++))
    fi
    
    # Check system resources
    if ! check_disk_space 90; then
        ((failed_checks++))
    fi
    
    if ! check_memory_usage 85; then
        ((failed_checks++))
    fi
    
    # Check Docker containers
    local unhealthy_containers
    unhealthy_containers=$(docker ps --filter "health=unhealthy" --format "table {{.Names}}" | tail -n +2)
    
    if [ -n "$unhealthy_containers" ]; then
        log "❌ Unhealthy containers: $unhealthy_containers"
        ((failed_checks++))
    fi
    
    # Send alerts if needed
    if [ "$failed_checks" -gt 0 ]; then
        send_alert "GraphMemory-IDE: $failed_checks health checks failed"
        exit 1
    else
        log "✅ All health checks passed"
        exit 0
    fi
}

main "$@"
```

## Backup and Disaster Recovery

### Automated Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/graphmemory/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="graphmemory_backup_$TIMESTAMP"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

create_backup() {
    local backup_path="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p "$backup_path"
    
    log "Creating backup: $BACKUP_NAME"
    
    # Backup Kuzu database
    log "Backing up Kuzu database..."
    docker-compose exec -T mcp-server kuzu-export \
        --database /app/data/kuzu \
        --output "$backup_path/kuzu_export"
    
    # Backup Kestra data
    log "Backing up Kestra data..."
    cp -r ./data/kestra "$backup_path/kestra_data"
    
    # Backup configuration files
    log "Backing up configuration..."
    tar -czf "$backup_path/config.tar.gz" \
        docker-compose.yml \
        .env \
        kestra.yml \
        nginx/ \
        monitoring/
    
    # Backup SSL certificates
    if [ -d "/etc/ssl/graphmemory" ]; then
        log "Backing up SSL certificates..."
        cp -r /etc/ssl/graphmemory "$backup_path/ssl_certs"
    fi
    
    # Create backup metadata
    cat > "$backup_path/metadata.json" << EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$TIMESTAMP",
    "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "services": [
        "mcp-server",
        "kestra",
        "prometheus",
        "grafana"
    ],
    "size_bytes": $(du -sb "$backup_path" | cut -f1)
}
EOF
    
    # Compress backup
    log "Compressing backup..."
    tar -czf "$backup_path.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
    rm -rf "$backup_path"
    
    log "Backup created: $backup_path.tar.gz"
}

upload_to_s3() {
    if [ -n "$S3_BUCKET" ]; then
        log "Uploading backup to S3..."
        aws s3 cp "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
            "s3://$S3_BUCKET/backups/$BACKUP_NAME.tar.gz"
        log "Backup uploaded to S3"
    fi
}

cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Local cleanup
    find "$BACKUP_DIR" -name "graphmemory_backup_*.tar.gz" \
        -mtime +$RETENTION_DAYS -delete
    
    # S3 cleanup
    if [ -n "$S3_BUCKET" ]; then
        aws s3 ls "s3://$S3_BUCKET/backups/" | \
        awk '{print $4}' | \
        while read -r file; do
            if [ -n "$file" ]; then
                file_date=$(echo "$file" | grep -o '[0-9]\{8\}' | head -1)
                if [ -n "$file_date" ]; then
                    days_old=$(( ($(date +%s) - $(date -d "$file_date" +%s)) / 86400 ))
                    if [ "$days_old" -gt "$RETENTION_DAYS" ]; then
                        aws s3 rm "s3://$S3_BUCKET/backups/$file"
                        log "Deleted old S3 backup: $file"
                    fi
                fi
            fi
        done
    fi
}

main() {
    log "Starting backup process..."
    
    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"
    
    # Create backup
    create_backup
    
    # Upload to S3 if configured
    upload_to_s3
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "Backup process completed successfully"
}

main "$@"
```

### Disaster Recovery Procedures

#### 1. Complete System Recovery

```bash
#!/bin/bash
# scripts/disaster-recovery.sh

set -euo pipefail

BACKUP_FILE="$1"
RECOVERY_DIR="/opt/graphmemory/recovery"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

restore_from_backup() {
    local backup_file="$1"
    
    log "Starting disaster recovery from: $backup_file"
    
    # Stop all services
    log "Stopping services..."
    docker-compose down
    
    # Create recovery directory
    mkdir -p "$RECOVERY_DIR"
    
    # Extract backup
    log "Extracting backup..."
    tar -xzf "$backup_file" -C "$RECOVERY_DIR"
    
    # Restore configuration
    log "Restoring configuration..."
    cp -r "$RECOVERY_DIR"/*/config/* ./
    
    # Restore Kuzu database
    log "Restoring Kuzu database..."
    rm -rf ./data/kuzu
    mkdir -p ./data/kuzu
    kuzu-import --database ./data/kuzu \
        --input "$RECOVERY_DIR"/*/kuzu_export
    
    # Restore Kestra data
    log "Restoring Kestra data..."
    rm -rf ./data/kestra
    cp -r "$RECOVERY_DIR"/*/kestra_data ./data/kestra
    
    # Restore SSL certificates
    if [ -d "$RECOVERY_DIR"/*/ssl_certs ]; then
        log "Restoring SSL certificates..."
        sudo cp -r "$RECOVERY_DIR"/*/ssl_certs /etc/ssl/graphmemory
    fi
    
    # Start services
    log "Starting services..."
    docker-compose up -d
    
    # Verify recovery
    sleep 30
    ./monitoring/health-monitor.sh
    
    log "Disaster recovery completed successfully"
}

main() {
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <backup_file>"
        exit 1
    fi
    
    restore_from_backup "$1"
}

main "$@"
```

#### 2. Database Recovery

```bash
#!/bin/bash
# scripts/recover-database.sh

recover_kuzu_database() {
    local backup_path="$1"
    
    log "Recovering Kuzu database from: $backup_path"
    
    # Stop MCP server
    docker-compose stop mcp-server
    
    # Backup current database
    if [ -d "./data/kuzu" ]; then
        mv ./data/kuzu "./data/kuzu.backup.$(date +%s)"
    fi
    
    # Restore from backup
    mkdir -p ./data/kuzu
    kuzu-import --database ./data/kuzu --input "$backup_path"
    
    # Start MCP server
    docker-compose start mcp-server
    
    # Verify database integrity
    docker-compose exec mcp-server kuzu-verify --database /app/data/kuzu
    
    log "Database recovery completed"
}
```

## Performance Tuning

### System Optimization

```bash
#!/bin/bash
# scripts/optimize-system.sh

optimize_kernel_parameters() {
    log "Optimizing kernel parameters..."
    
    cat >> /etc/sysctl.conf << EOF
# GraphMemory-IDE optimizations
vm.swappiness=10
vm.dirty_ratio=15
vm.dirty_background_ratio=5
net.core.somaxconn=65535
net.core.netdev_max_backlog=5000
net.ipv4.tcp_max_syn_backlog=65535
net.ipv4.tcp_fin_timeout=30
net.ipv4.tcp_keepalive_time=1200
net.ipv4.tcp_max_tw_buckets=400000
EOF
    
    sysctl -p
}

optimize_docker() {
    log "Optimizing Docker configuration..."
    
    cat > /etc/docker/daemon.json << EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ],
    "default-ulimits": {
        "nofile": {
            "Name": "nofile",
            "Hard": 64000,
            "Soft": 64000
        }
    }
}
EOF
    
    systemctl restart docker
}

optimize_database() {
    log "Optimizing database configuration..."
    
    # Kuzu optimization
    cat > ./config/kuzu.conf << EOF
buffer_pool_size=4GB
max_connections=100
checkpoint_frequency=300
wal_flush_threshold=1MB
query_timeout=300
EOF
}
```

### Application Performance Tuning

```yaml
# docker-compose.performance.yml
version: '3.8'

services:
  mcp-server:
    environment:
      - NODE_OPTIONS="--max-old-space-size=4096 --optimize-for-size"
      - UV_THREADPOOL_SIZE=16
    deploy:
      resources:
        limits:
          memory: 6G
          cpus: '2.0'
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  kestra:
    environment:
      - JAVA_OPTS="-Xmx4g -Xms2g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
    deploy:
      resources:
        limits:
          memory: 6G
          cpus: '2.0'
```

### Performance Monitoring

```bash
#!/bin/bash
# monitoring/performance-monitor.sh

monitor_performance() {
    local duration="${1:-60}"
    local output_file="performance_report_$(date +%Y%m%d_%H%M%S).json"
    
    log "Starting performance monitoring for ${duration}s..."
    
    # System metrics
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    
    local memory_usage
    memory_usage=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
    
    local disk_io
    disk_io=$(iostat -x 1 2 | tail -n +4 | awk '{print $4}')
    
    # Application metrics
    local response_time
    response_time=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8080/health)
    
    local active_connections
    active_connections=$(netstat -an | grep :8080 | grep ESTABLISHED | wc -l)
    
    # Database metrics
    local db_connections
    db_connections=$(docker-compose exec -T mcp-server kuzu-stats --connections)
    
    # Generate report
    cat > "$output_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "duration_seconds": $duration,
    "system": {
        "cpu_usage_percent": $cpu_usage,
        "memory_usage_percent": $memory_usage,
        "disk_io_ops": $disk_io
    },
    "application": {
        "response_time_seconds": $response_time,
        "active_connections": $active_connections,
        "database_connections": $db_connections
    }
}
EOF
    
    log "Performance report saved: $output_file"
}
```

## Security Operations

### Security Monitoring

```bash
#!/bin/bash
# monitoring/security-monitor.sh

check_security_status() {
    log "Performing security status check..."
    
    # Check for failed login attempts
    local failed_logins
    failed_logins=$(grep "Failed password" /var/log/auth.log | wc -l)
    
    if [ "$failed_logins" -gt 10 ]; then
        log "⚠️  High number of failed login attempts: $failed_logins"
    fi
    
    # Check SSL certificate expiry
    local cert_expiry
    cert_expiry=$(openssl x509 -in /etc/ssl/graphmemory/server.crt -noout -dates | grep notAfter | cut -d= -f2)
    local days_until_expiry
    days_until_expiry=$(( ($(date -d "$cert_expiry" +%s) - $(date +%s)) / 86400 ))
    
    if [ "$days_until_expiry" -lt 30 ]; then
        log "⚠️  SSL certificate expires in $days_until_expiry days"
    fi
    
    # Check for security updates
    local security_updates
    security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
    
    if [ "$security_updates" -gt 0 ]; then
        log "⚠️  $security_updates security updates available"
    fi
    
    # Check container security
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image --severity HIGH,CRITICAL \
        graphmemory/mcp-server:latest
}

rotate_secrets() {
    log "Rotating secrets..."
    
    # Generate new API keys
    local new_api_key
    new_api_key=$(openssl rand -hex 32)
    
    # Update environment variables
    sed -i "s/API_KEY=.*/API_KEY=$new_api_key/" .env
    
    # Restart services
    docker-compose restart
    
    log "Secrets rotated successfully"
}
```

### Incident Response

```bash
#!/bin/bash
# scripts/incident-response.sh

handle_security_incident() {
    local incident_type="$1"
    local severity="$2"
    
    log "Security incident detected: $incident_type (Severity: $severity)"
    
    case "$incident_type" in
        "unauthorized_access")
            # Block suspicious IPs
            iptables -A INPUT -s "$suspicious_ip" -j DROP
            
            # Force password reset
            ./scripts/force-password-reset.sh
            ;;
            
        "data_breach")
            # Immediate containment
            docker-compose down
            
            # Preserve evidence
            ./scripts/preserve-logs.sh
            
            # Notify stakeholders
            ./scripts/notify-incident.sh "$incident_type" "$severity"
            ;;
            
        "malware_detected")
            # Isolate affected containers
            docker-compose stop mcp-server
            
            # Run security scan
            ./scripts/security-scan.sh
            ;;
    esac
}
```

## Maintenance Procedures

### Regular Maintenance Tasks

```bash
#!/bin/bash
# scripts/maintenance.sh

perform_maintenance() {
    log "Starting maintenance procedures..."
    
    # Update system packages
    log "Updating system packages..."
    apt update && apt upgrade -y
    
    # Update Docker images
    log "Updating Docker images..."
    docker-compose pull
    docker-compose up -d
    
    # Clean up Docker resources
    log "Cleaning up Docker resources..."
    docker system prune -f
    docker volume prune -f
    
    # Rotate logs
    log "Rotating logs..."
    logrotate /etc/logrotate.d/graphmemory
    
    # Database maintenance
    log "Performing database maintenance..."
    docker-compose exec mcp-server kuzu-vacuum --database /app/data/kuzu
    docker-compose exec mcp-server kuzu-analyze --database /app/data/kuzu
    
    # Security updates
    log "Checking security updates..."
    ./monitoring/security-monitor.sh
    
    # Performance optimization
    log "Optimizing performance..."
    ./scripts/optimize-system.sh
    
    log "Maintenance completed successfully"
}

# Schedule maintenance (add to crontab)
# 0 2 * * 0 /opt/graphmemory/scripts/maintenance.sh
```

### Database Maintenance

```bash
#!/bin/bash
# scripts/database-maintenance.sh

maintain_database() {
    log "Starting database maintenance..."
    
    # Vacuum database
    docker-compose exec mcp-server kuzu-vacuum --database /app/data/kuzu
    
    # Update statistics
    docker-compose exec mcp-server kuzu-analyze --database /app/data/kuzu
    
    # Check integrity
    docker-compose exec mcp-server kuzu-verify --database /app/data/kuzu
    
    # Optimize indexes
    docker-compose exec mcp-server kuzu-reindex --database /app/data/kuzu
    
    log "Database maintenance completed"
}
```

## Troubleshooting

### Common Issues and Solutions

#### High Memory Usage

```bash
# Identify memory-consuming processes
docker stats --no-stream
ps aux --sort=-%mem | head -10

# Optimize memory usage
echo 3 > /proc/sys/vm/drop_caches
docker-compose restart mcp-server
```

#### Database Connection Issues

```bash
# Check database status
docker-compose exec mcp-server kuzu-status --database /app/data/kuzu

# Reset connections
docker-compose restart mcp-server

# Check connection limits
docker-compose logs mcp-server | grep "connection"
```

#### SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in /etc/ssl/graphmemory/server.crt -text -noout

# Renew certificate
certbot renew --force-renewal

# Update certificate in containers
docker-compose restart nginx
```

### Log Analysis

```bash
#!/bin/bash
# scripts/analyze-logs.sh

analyze_logs() {
    local service="$1"
    local time_range="${2:-1h}"
    
    log "Analyzing logs for $service (last $time_range)..."
    
    case "$service" in
        "mcp-server")
            docker-compose logs --since="$time_range" mcp-server | \
            grep -E "(ERROR|WARN)" | \
            awk '{print $1, $2, $NF}' | \
            sort | uniq -c | sort -nr
            ;;
            
        "kestra")
            docker-compose logs --since="$time_range" kestra | \
            grep -E "(ERROR|WARN)" | \
            awk '{print $1, $2, $NF}' | \
            sort | uniq -c | sort -nr
            ;;
            
        "system")
            journalctl --since="$time_range" --priority=err | \
            awk '{print $5}' | sort | uniq -c | sort -nr
            ;;
    esac
}
```

## Scaling and Load Management

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  mcp-server:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/load-balancer.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - mcp-server
```

### Load Balancer Configuration

```nginx
# nginx/load-balancer.conf
upstream mcp_backend {
    least_conn;
    server mcp-server_1:8080 max_fails=3 fail_timeout=30s;
    server mcp-server_2:8080 max_fails=3 fail_timeout=30s;
    server mcp-server_3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
    
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### Auto-scaling Script

```bash
#!/bin/bash
# scripts/auto-scale.sh

auto_scale() {
    local cpu_threshold=80
    local memory_threshold=85
    local scale_up_threshold=3
    local scale_down_threshold=1
    
    # Get current metrics
    local cpu_usage
    cpu_usage=$(docker stats --no-stream --format "table {{.CPUPerc}}" | tail -n +2 | sed 's/%//' | awk '{sum+=$1} END {print sum/NR}')
    
    local memory_usage
    memory_usage=$(docker stats --no-stream --format "table {{.MemPerc}}" | tail -n +2 | sed 's/%//' | awk '{sum+=$1} END {print sum/NR}')
    
    local current_replicas
    current_replicas=$(docker-compose ps -q mcp-server | wc -l)
    
    # Scale up if needed
    if (( $(echo "$cpu_usage > $cpu_threshold" | bc -l) )) || (( $(echo "$memory_usage > $memory_threshold" | bc -l) )); then
        if [ "$current_replicas" -lt "$scale_up_threshold" ]; then
            log "Scaling up: CPU=$cpu_usage%, Memory=$memory_usage%"
            docker-compose up -d --scale mcp-server=$((current_replicas + 1))
        fi
    fi
    
    # Scale down if needed
    if (( $(echo "$cpu_usage < 30" | bc -l) )) && (( $(echo "$memory_usage < 40" | bc -l) )); then
        if [ "$current_replicas" -gt "$scale_down_threshold" ]; then
            log "Scaling down: CPU=$cpu_usage%, Memory=$memory_usage%"
            docker-compose up -d --scale mcp-server=$((current_replicas - 1))
        fi
    fi
}

# Run auto-scaling check every 5 minutes
while true; do
    auto_scale
    sleep 300
done
```

---

## Support and Escalation

### Support Contacts
- **Level 1 Support**: support@graphmemory.dev
- **Level 2 Support**: engineering@graphmemory.dev
- **Emergency**: +1-555-GRAPH-MEM

### Escalation Procedures
1. **P1 (Critical)**: Immediate escalation to on-call engineer
2. **P2 (High)**: Escalate within 2 hours
3. **P3 (Medium)**: Escalate within 8 hours
4. **P4 (Low)**: Escalate within 24 hours

For additional operational guidance, refer to the [main documentation](../README.md) and [security guide](../SECURITY.md). 