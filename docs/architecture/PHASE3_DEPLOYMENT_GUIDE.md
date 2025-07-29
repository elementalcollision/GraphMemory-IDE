# Phase 3 Deployment Guide: Multi-Database Integration

## Overview

Phase 3 introduces comprehensive multi-database integration with PostgreSQL and Kuzu graph database, including real-time synchronization, health monitoring, and production-ready infrastructure.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Database Setup](#database-setup)
3. [Graph Database Integration](#graph-database-integration)
4. [Synchronization Configuration](#synchronization-configuration)
5. [Health Monitoring Setup](#health-monitoring-setup)
6. [Production Deployment](#production-deployment)
7. [Testing and Validation](#testing-and-validation)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / macOS 10.15+
- **Memory**: Minimum 8GB RAM (16GB+ recommended for production)
- **Storage**: 50GB+ available disk space
- **CPU**: 4+ cores recommended
- **Network**: Stable internet connection for dependencies

### Software Dependencies

```bash
# Python 3.11+
python --version  # Should be 3.11 or higher

# PostgreSQL 14+
psql --version    # Should be 14 or higher

# Redis 6+
redis-cli --version  # Should be 6 or higher

# Docker & Docker Compose
docker --version
docker-compose --version
```

### Environment Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install additional Phase 3 dependencies
pip install kuzu psutil aiohttp

# Verify installations
python -c "import kuzu; print('Kuzu available')"
python -c "import psutil; print('psutil available')"
```

## Database Setup

### PostgreSQL Configuration

1. **Install and Configure PostgreSQL**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
```

2. **Create Database and User**

```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database
CREATE DATABASE graphmemory_ide;

-- Create user with appropriate permissions
CREATE USER graphmemory_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE graphmemory_ide TO graphmemory_user;

-- Enable required extensions
\c graphmemory_ide
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
```

3. **Configure PostgreSQL Settings**

Edit `/etc/postgresql/14/main/postgresql.conf`:

```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 4MB

# Connection settings
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'

# WAL settings for replication
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
```

Edit `/etc/postgresql/14/main/pg_hba.conf`:

```
# Allow connections from application
host    graphmemory_ide    graphmemory_user    127.0.0.1/32    md5
host    graphmemory_ide    graphmemory_user    ::1/128         md5
```

4. **Restart PostgreSQL**

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### Database Migration Setup

1. **Initialize Alembic**

```bash
# Navigate to server directory
cd server

# Initialize database schema
python -c "
from migrations import MigrationManager
import asyncio
async def init():
    manager = MigrationManager()
    await manager.create_database()
    await manager.create_all_tables()
    print('Database initialized successfully')
asyncio.run(init())
"
```

2. **Verify Database Setup**

```bash
# Test database connection
python -c "
from core.database import get_async_session
from sqlalchemy import text
import asyncio
async def test():
    async with get_async_session() as session:
        result = await session.execute(text('SELECT version()'))
        print('PostgreSQL version:', result.scalar())
asyncio.run(test())
"
```

## Graph Database Integration

### Kuzu Installation and Setup

1. **Install Kuzu Database**

```bash
# Install via pip
pip install kuzu

# Or install from source (advanced)
git clone https://github.com/kuzudb/kuzu.git
cd kuzu
make release
```

2. **Create Data Directory**

```bash
# Create directory for graph database
mkdir -p data/kuzu_graph
chmod 755 data/kuzu_graph
```

3. **Test Kuzu Installation**

```python
# Test script: test_kuzu.py
import kuzu

# Create test database
db = kuzu.Database("./test_kuzu")
conn = kuzu.Connection(db)

# Create test table
conn.execute("CREATE NODE TABLE Person(name STRING, age INT64, PRIMARY KEY(name))")

# Insert test data
conn.execute("CREATE (p:Person {name: 'Alice', age: 30})")

# Query test data
result = conn.execute("MATCH (p:Person) RETURN p.name, p.age")
while result.has_next():
    print(result.get_next())

print("Kuzu installation successful!")
```

4. **Initialize Graph Schema**

```bash
# Initialize graph database schema
python -c "
from graph_database import get_graph_database
import asyncio
async def init():
    graph_db = await get_graph_database()
    if graph_db.schema_manager.initialize_schema():
        print('Graph schema initialized successfully')
    else:
        print('Failed to initialize graph schema')
asyncio.run(init())
"
```

### Graph Database Configuration

Update your environment configuration:

```bash
# .env file
GRAPH_DATABASE_PATH=./data/kuzu_graph
GRAPH_BUFFER_POOL_SIZE=1073741824  # 1GB
GRAPH_MAX_THREADS=8
GRAPH_CONNECTION_POOL_SIZE=10
GRAPH_ENABLE_MONITORING=true
```

## Synchronization Configuration

### Enable Database Synchronization

1. **Configuration Setup**

```python
# config/sync_config.py
SYNC_CONFIG = {
    "enabled": True,
    "batch_size": 100,
    "sync_interval": 30,  # seconds
    "max_retries": 3,
    "retry_delay": 5,
    "conflict_resolution": "latest_wins",
    "enable_monitoring": True,
    "tables_to_sync": {
        "users", "user_sessions", "telemetry_events",
        "analytics_queries", "kuzu_queries", "collaboration_sessions",
        "collaboration_participants", "system_metrics", "api_request_logs"
    }
}
```

2. **Start Synchronization Service**

```python
# sync_service.py
from database_sync import start_database_sync
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("Starting database synchronization...")
    await start_database_sync()
    
    # Keep service running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down synchronization...")
        from database_sync import stop_database_sync
        await stop_database_sync()

if __name__ == "__main__":
    asyncio.run(main())
```

3. **Test Synchronization**

```bash
# Test sync functionality
python -c "
from database_sync import get_database_synchronizer
from database_models import User
from core.database import get_async_session
import asyncio
import uuid
from datetime import datetime, timezone

async def test_sync():
    # Create test user
    async with get_async_session() as session:
        user = User(
            id=uuid.uuid4(),
            username='sync_test',
            email='sync_test@example.com',
            role='user',
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        await session.commit()
        print(f'Created test user: {user.id}')
    
    # Start synchronizer
    sync = await get_database_synchronizer()
    await sync.start()
    
    # Wait for sync
    await asyncio.sleep(5)
    
    # Check if synced to graph
    from graph_database import get_graph_database
    graph_db = await get_graph_database()
    result = graph_db.query_engine.execute_query(
        'MATCH (u:User {id: \$id}) RETURN u',
        {'id': str(user.id)}
    )
    
    if result.success and result.row_count > 0:
        print('Synchronization test passed!')
    else:
        print('Synchronization test failed!')
    
    await sync.stop()

asyncio.run(test_sync())
"
```

## Health Monitoring Setup

### Configure Health Monitoring

1. **Environment Variables**

```bash
# Health monitoring configuration
HEALTH_CHECK_INTERVAL=30
METRICS_COLLECTION_INTERVAL=30
ALERT_THRESHOLDS_CPU_WARNING=80.0
ALERT_THRESHOLDS_CPU_CRITICAL=95.0
ALERT_THRESHOLDS_MEMORY_WARNING=85.0
ALERT_THRESHOLDS_MEMORY_CRITICAL=95.0
```

2. **Start Health Monitor**

```python
# health_service.py
from health_monitoring import get_health_monitor
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("Starting health monitoring system...")
    monitor = await get_health_monitor()
    await monitor.start_monitoring()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down health monitoring...")
        await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

3. **Configure Notifications**

```python
# notification_config.py
import aiohttp
import logging

async def slack_notification(alert):
    """Send alert to Slack"""
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    
    payload = {
        "text": f"🚨 {alert.title}",
        "attachments": [{
            "color": "danger" if alert.severity.value == "critical" else "warning",
            "fields": [
                {"title": "Message", "value": alert.message, "short": False},
                {"title": "Source", "value": alert.source, "short": True},
                {"title": "Severity", "value": alert.severity.value.upper(), "short": True}
            ],
            "ts": alert.timestamp.timestamp()
        }]
    }
    
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)

async def email_notification(alert):
    """Send alert via email"""
    # Implement email notification logic
    logging.info(f"Email alert: {alert.title} - {alert.message}")

# Register notification channels
async def setup_notifications():
    from health_monitoring import get_health_monitor
    monitor = await get_health_monitor()
    monitor.alert_manager.add_notification_channel(slack_notification)
    monitor.alert_manager.add_notification_channel(email_notification)
```

### Health Check Endpoints

Access health information via API:

```bash
# Overall system health
curl http://localhost:8000/health/

# Specific health check
curl http://localhost:8000/health/checks/postgresql

# System metrics
curl http://localhost:8000/health/metrics/system

# Database metrics
curl http://localhost:8000/health/metrics/database/postgresql

# Active alerts
curl http://localhost:8000/health/alerts
```

## Production Deployment

### Docker Compose Setup

1. **Create Production Docker Compose**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/graphmemory_ide
      - REDIS_URL=redis://redis:6379
      - GRAPH_DATABASE_PATH=/app/data/kuzu_graph
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=graphmemory_ide
      - POSTGRES_USER=graphmemory_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

2. **Nginx Configuration**

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://app/health;
            access_log off;
        }
    }
}
```

3. **Deploy to Production**

```bash
# Pull latest code
git pull origin main

# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### Environment Configuration

```bash
# .env.production
DATABASE_URL=postgresql://graphmemory_user:secure_password@postgres:5432/graphmemory_ide
REDIS_URL=redis://redis:6379
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Graph database settings
GRAPH_DATABASE_PATH=/app/data/kuzu_graph
GRAPH_BUFFER_POOL_SIZE=2147483648  # 2GB
GRAPH_MAX_THREADS=16
GRAPH_CONNECTION_POOL_SIZE=20

# Monitoring settings
HEALTH_CHECK_INTERVAL=30
METRICS_COLLECTION_INTERVAL=15
ENABLE_HEALTH_MONITORING=true

# Security settings
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-here
CORS_ORIGINS=https://your-domain.com
```

## Testing and Validation

### Integration Tests

```bash
# Run database integration tests
python -m pytest tests/integration/test_database_integration.py -v

# Run health monitoring tests
python -m pytest tests/integration/test_health_monitoring.py -v

# Run synchronization tests
python -m pytest tests/integration/test_database_sync.py -v
```

### Performance Testing

```bash
# Test database performance
python scripts/performance_test.py

# Load test with multiple concurrent users
python scripts/load_test.py --users 100 --duration 300

# Memory leak detection
python scripts/memory_test.py --duration 3600
```

### Validation Checklist

- [ ] PostgreSQL connection successful
- [ ] Kuzu graph database initialized
- [ ] Database schemas created
- [ ] Synchronization working
- [ ] Health monitoring active
- [ ] All health checks passing
- [ ] Alerts configured and working
- [ ] Performance within acceptable limits
- [ ] Backup systems functional
- [ ] SSL certificates valid
- [ ] Monitoring dashboards accessible

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log

# Test connection manually
psql -h localhost -U graphmemory_user -d graphmemory_ide
```

#### Graph Database Issues

```bash
# Check Kuzu data directory permissions
ls -la data/kuzu_graph

# Test Kuzu installation
python -c "import kuzu; print('Kuzu OK')"

# Check graph database logs
tail -f logs/graph_database.log
```

#### Synchronization Issues

```bash
# Check sync service status
curl http://localhost:8000/sync/status

# View synchronization logs
tail -f logs/database_sync.log

# Manual sync trigger
curl -X POST http://localhost:8000/sync/trigger
```

#### Health Monitoring Issues

```bash
# Check health endpoints
curl http://localhost:8000/health/

# View health monitoring logs
tail -f logs/health_monitoring.log

# Check system resources
htop
df -h
```

### Log Analysis

```bash
# Search for errors in logs
grep -r "ERROR" logs/

# Check memory usage patterns
grep -r "memory" logs/health_monitoring.log

# Monitor database performance
grep -r "slow query" logs/database.log
```

### Performance Issues

#### Database Optimization

```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;

-- Analyze table statistics
ANALYZE VERBOSE;
```

#### Memory Optimization

```bash
# Check memory usage
free -h
cat /proc/meminfo

# Monitor Python memory usage
python -m memory_profiler script.py

# Check for memory leaks
valgrind --tool=memcheck python app.py
```

#### CPU Optimization

```bash
# Check CPU usage
top -p $(pgrep python)

# Profile Python code
python -m cProfile -o profile.stats app.py

# Analyze profile
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

## Performance Optimization

### Database Tuning

1. **PostgreSQL Optimization**

```sql
-- Create additional indexes
CREATE INDEX CONCURRENTLY idx_users_email_active ON users(email) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_telemetry_timestamp ON telemetry_events(timestamp);
CREATE INDEX CONCURRENTLY idx_telemetry_user_type ON telemetry_events(user_id, event_type);

-- Enable query optimization
SET enable_seqscan = off;  -- For testing only
SET work_mem = '16MB';
SET random_page_cost = 1.1;  -- For SSD storage
```

2. **Connection Pooling**

```python
# Database connection pool configuration
DATABASE_POOL_CONFIG = {
    "pool_size": 20,
    "max_overflow": 40,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}
```

3. **Query Optimization**

```python
# Optimized queries with proper indexing
async def get_user_telemetry_optimized(user_id: uuid.UUID, limit: int = 100):
    query = """
    SELECT * FROM telemetry_events 
    WHERE user_id = $1 
    ORDER BY timestamp DESC 
    LIMIT $2
    """
    # Uses idx_telemetry_user_type index
    return await session.execute(text(query), [user_id, limit])
```

### Graph Database Optimization

1. **Kuzu Performance Tuning**

```python
# Optimized Kuzu configuration
KUZU_CONFIG = {
    "buffer_pool_size": 4 * 1024 * 1024 * 1024,  # 4GB
    "max_num_threads": 16,
    "compression": True,
    "auto_checkpoint": True,
    "checkpoint_threshold": 128 * 1024 * 1024  # 128MB
}
```

2. **Query Optimization**

```cypher
-- Optimized graph queries
MATCH (u:User {id: $user_id})
OPTIONAL MATCH (u)-[:OWNS]->(p:Project)
OPTIONAL MATCH (p)-[:CONTAINS]->(m:Memory)
RETURN u, collect(p) as projects, collect(m) as memories
```

### Caching Strategy

1. **Redis Caching**

```python
# Cache frequently accessed data
async def get_user_cached(user_id: str):
    cache_key = f"user:{user_id}"
    cached = await redis.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    user = await get_user_from_db(user_id)
    await redis.setex(cache_key, 3600, json.dumps(user))
    return user
```

2. **Application-Level Caching**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_system_config():
    return load_config_from_db()
```

### Monitoring and Alerts

1. **Performance Metrics**

```python
# Track key performance indicators
PERFORMANCE_METRICS = {
    "database_response_time": {"warning": 100, "critical": 500},  # ms
    "graph_query_time": {"warning": 200, "critical": 1000},      # ms
    "sync_lag": {"warning": 60, "critical": 300},                # seconds
    "memory_usage": {"warning": 85, "critical": 95},             # percent
    "cpu_usage": {"warning": 80, "critical": 95}                 # percent
}
```

2. **Automated Scaling**

```python
# Auto-scaling based on metrics
async def auto_scale_check():
    metrics = await get_current_metrics()
    
    if metrics['cpu_usage'] > 80:
        await scale_up_workers()
    elif metrics['cpu_usage'] < 30:
        await scale_down_workers()
```

## Security Considerations

### Database Security

1. **Access Controls**

```sql
-- Create read-only user for reporting
CREATE USER readonly_user WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE graphmemory_ide TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

2. **SSL Configuration**

```bash
# Enable SSL in PostgreSQL
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_ca_file = 'ca.crt'
```

### Network Security

1. **Firewall Rules**

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 5432/tcp  # PostgreSQL (from app servers only)
sudo ufw enable
```

2. **VPN Access**

```bash
# Configure VPN for administrative access
# Use tools like OpenVPN or WireGuard
```

## Backup and Recovery

### Automated Backups

1. **Database Backups**

```bash
# PostgreSQL backup script
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="graphmemory_backup_${DATE}.sql"

pg_dump -h localhost -U graphmemory_user graphmemory_ide > "${BACKUP_DIR}/${FILENAME}"
gzip "${BACKUP_DIR}/${FILENAME}"

# Keep only last 7 days of backups
find ${BACKUP_DIR} -name "*.gz" -mtime +7 -delete
```

2. **Graph Database Backups**

```bash
# Kuzu backup script
#!/bin/bash
BACKUP_DIR="/backups/kuzu"
DATE=$(date +%Y%m%d_%H%M%S)
SOURCE_DIR="data/kuzu_graph"

tar -czf "${BACKUP_DIR}/kuzu_backup_${DATE}.tar.gz" "${SOURCE_DIR}"

# Keep only last 7 days of backups
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete
```

### Recovery Procedures

1. **Database Recovery**

```bash
# Stop application
docker-compose stop app

# Restore PostgreSQL
gunzip -c /backups/postgresql/graphmemory_backup_YYYYMMDD_HHMMSS.sql.gz | \
psql -h localhost -U graphmemory_user graphmemory_ide

# Restore Kuzu
tar -xzf /backups/kuzu/kuzu_backup_YYYYMMDD_HHMMSS.tar.gz -C /

# Start application
docker-compose start app
```

2. **Point-in-Time Recovery**

```bash
# PostgreSQL PITR setup
wal_level = replica
archive_mode = on
archive_command = 'cp %p /archive/%f'
```

## Conclusion

Phase 3 provides a robust, production-ready multi-database infrastructure with:

- ✅ PostgreSQL and Kuzu graph database integration
- ✅ Real-time data synchronization
- ✅ Comprehensive health monitoring
- ✅ Performance optimization
- ✅ Security best practices
- ✅ Automated backup and recovery
- ✅ Production deployment automation

For additional support or questions, refer to the troubleshooting section or contact the development team.

---

**Last Updated**: June 1, 2025  
**Version**: 3.0.0  
**Author**: GraphMemory-IDE Development Team 