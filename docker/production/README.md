# GraphMemory-IDE Production Database Deployment

This directory contains the production deployment configuration for GraphMemory-IDE's database infrastructure, including PostgreSQL, Redis, and Kuzu databases with automated backup and migration systems.

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- OpenSSL (for certificate generation)
- AWS CLI (optional, for S3 backups)

### 1. Environment Setup

```bash
# Copy environment template
cp env.production.template .env

# Edit configuration with your production values
nano .env
```

**Required Environment Variables:**
```bash
# Database credentials
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here

# Security keys
SECRET_KEY=your_jwt_secret_key_here
CSRF_SECRET_KEY=your_csrf_secret_here

# Optional: S3 backup configuration
S3_BACKUP_ENABLED=true
S3_BUCKET=your-backup-bucket
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
```

### 2. SSL Certificate Setup

```bash
# Generate self-signed certificates (development)
mkdir -p postgresql/ssl
openssl req -new -x509 -days 365 -nodes \
  -out postgresql/ssl/server.crt \
  -keyout postgresql/ssl/server.key

# Set proper permissions
chmod 600 postgresql/ssl/server.key
chmod 644 postgresql/ssl/server.crt
```

### 3. Deploy Database Infrastructure

```bash
# Start all database services
docker-compose up -d

# Check service health
docker-compose ps
docker-compose logs postgresql
```

### 4. Initialize Database Schema

```bash
# Run initial migrations
../scripts/deploy/migrate.sh migrate

# Seed production data
python3 ../server/data_seeding.py
```

## 📦 Services Overview

### PostgreSQL Database
- **Image**: `postgres:16-alpine`
- **Port**: `5432`
- **Features**: 
  - Performance-tuned configuration
  - SSL encryption
  - Comprehensive logging
  - Health checks
  - Resource limits

### Redis Cache
- **Image**: `redis:7-alpine`
- **Port**: `6379`
- **Features**:
  - Password authentication
  - Memory optimization
  - Persistence configuration
  - LRU eviction policy

### Kuzu Graph Database
- **Image**: `kuzu/kuzu:latest`
- **Features**:
  - High-performance graph queries
  - Data persistence
  - Resource optimization

### Backup Service
- **Purpose**: Automated database backups
- **Features**:
  - Full and incremental backups
  - S3 upload support
  - Integrity verification
  - Retention management

## 🔧 Database Management

### Migration Management

```bash
# Check migration status
../scripts/deploy/migrate.sh status

# Run migrations (with backup)
../scripts/deploy/migrate.sh migrate

# Dry run (preview changes)
DRY_RUN=true ../scripts/deploy/migrate.sh migrate

# Rollback to previous version
../scripts/deploy/migrate.sh rollback HEAD~1
```

### Backup Operations

```bash
# Full backup
./scripts/backup/backup.sh full

# Incremental backup
./scripts/backup/backup.sh incremental

# Schema-only backup
./scripts/backup/backup.sh schema

# Verify backup integrity
./scripts/backup/backup.sh verify
```

### Restore Operations

```bash
# List available backups
./scripts/backup/restore.sh list

# Interactive PostgreSQL restore
./scripts/backup/restore.sh postgresql-full

# Automated restore (skip confirmations)
./scripts/backup/restore.sh postgresql-full /path/to/backup.sql.gz --yes

# Kuzu database restore
./scripts/backup/restore.sh kuzu
```

### Performance Optimization

```bash
# Generate performance report
python3 ../server/performance_tuning.py

# Run VACUUM ANALYZE
docker-compose exec postgresql psql -U graphmemory -d graphmemory -c "VACUUM ANALYZE;"

# Check database statistics
docker-compose exec postgresql psql -U graphmemory -d graphmemory -c "\l+"
```

## 📊 Monitoring and Maintenance

### Health Checks

```bash
# Database connectivity
docker-compose exec postgresql pg_isready -U graphmemory

# Redis connectivity
docker-compose exec redis redis-cli ping

# Service status
docker-compose ps
```

### Log Management

```bash
# View PostgreSQL logs
docker-compose logs -f postgresql

# View Redis logs
docker-compose logs -f redis

# View backup logs
docker-compose logs backup
```

### Performance Monitoring

```bash
# Database metrics
docker-compose exec postgresql psql -U graphmemory -d graphmemory -c "
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
ORDER BY seq_tup_read DESC;
"

# Connection statistics
docker-compose exec postgresql psql -U graphmemory -d graphmemory -c "
SELECT state, count(*) 
FROM pg_stat_activity 
GROUP BY state;
"
```

## 🔐 Security Configuration

### Database Security
- Password authentication with strong passwords
- SSL/TLS encryption for all connections
- Network isolation with Docker networks
- Read-only database users for applications
- Connection limits and timeouts

### Access Control
```bash
# Create read-only user
docker-compose exec postgresql psql -U graphmemory -d graphmemory -c "
CREATE USER graphmemory_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE graphmemory TO graphmemory_readonly;
GRANT USAGE ON SCHEMA public TO graphmemory_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO graphmemory_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO graphmemory_readonly;
"
```

### Firewall Configuration
```bash
# Allow only necessary ports
ufw allow 5432/tcp comment "PostgreSQL"
ufw allow 6379/tcp comment "Redis"
ufw deny 5432/tcp from any to any comment "Block external PostgreSQL"
```

## 🚨 Disaster Recovery

### Backup Strategy
1. **Daily Full Backups**: Complete database dump with compression
2. **Hourly Incremental**: WAL archiving for point-in-time recovery
3. **Weekly Schema Backups**: Structure-only backups for development
4. **Monthly S3 Sync**: Off-site backup storage

### Recovery Procedures

#### Complete Database Loss
```bash
# 1. Stop all services
docker-compose down

# 2. Restore from latest backup
./scripts/backup/restore.sh postgresql-full --yes

# 3. Verify data integrity
./scripts/backup/restore.sh verify

# 4. Restart services
docker-compose up -d
```

#### Point-in-Time Recovery
```bash
# 1. Identify recovery point
./scripts/backup/backup.sh list

# 2. Restore base backup
./scripts/backup/restore.sh postgresql-full /path/to/base_backup.sql.gz

# 3. Apply WAL files to recovery point
# (Advanced operation - see PostgreSQL documentation)
```

## ⚙️ Configuration Tuning

### PostgreSQL Configuration
The deployment includes optimized PostgreSQL settings:

```ini
# Memory settings (adjust based on available RAM)
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 32MB
maintenance_work_mem = 512MB

# Connection settings
max_connections = 200

# Performance settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Redis Configuration
```ini
# Memory settings
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
appendonly yes
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Database Migrations
  run: |
    ./scripts/deploy/migrate.sh migrate
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    ENVIRONMENT: production

- name: Backup Before Deployment
  run: |
    ./docker/production/scripts/backup/backup.sh full
  env:
    BACKUP_BEFORE_MIGRATION: true
```

### Environment Variables for CI/CD
```bash
# Required for automated deployments
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
ENVIRONMENT=production
DRY_RUN=false
SKIP_BACKUP=false
WEBHOOK_URL=https://hooks.slack.com/your-webhook
```

## 📚 Troubleshooting

### Common Issues

#### Connection Refused
```bash
# Check if PostgreSQL is running
docker-compose ps postgresql

# Check PostgreSQL logs
docker-compose logs postgresql

# Verify network connectivity
docker-compose exec postgresql pg_isready
```

#### Out of Memory
```bash
# Check container resource usage
docker stats

# Adjust memory limits in docker-compose.yml
# Optimize PostgreSQL memory settings
```

#### Slow Queries
```bash
# Enable slow query logging
echo "log_min_duration_statement = 1000" >> postgresql.conf

# Analyze slow queries
python3 ../server/performance_tuning.py

# Create missing indexes
# (Follow recommendations from performance report)
```

#### Backup Failures
```bash
# Check backup directory permissions
ls -la /backups

# Verify database connectivity
./scripts/backup/backup.sh verify

# Check disk space
df -h
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Docker Compose logs: `docker-compose logs`
3. Verify environment configuration
4. Consult PostgreSQL, Redis, and Kuzu documentation

## 🔗 Related Documentation

- [Database Schema Documentation](../../server/database_models.py)
- [Migration System Documentation](../../server/alembic/)
- [Performance Tuning Guide](../../server/performance_tuning.py)
- [Data Seeding Documentation](../../server/data_seeding.py) 