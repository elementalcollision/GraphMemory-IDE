# Docker Deployment Documentation

## Overview

This directory contains Docker configuration for GraphMemory-IDE, providing containerized deployment of the MCP server, Kuzu database, and Kestra CI/CD orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│   MCP Server    │     Kestra      │      Named Volumes      │
│   (FastAPI)     │   (CI/CD)       │                         │
│   Port: 8080    │   Port: 8081    │  ┌─────────────────┐    │
│   Port: 50051   │                 │  │   kuzu-data     │    │
│                 │                 │  │   kestra-data   │    │
└─────────────────┴─────────────────┴──┴─────────────────┴────┘
                           │
                    ┌─────────────┐
                    │ memory-net  │
                    │  (bridge)   │
                    └─────────────┘
```

## Quick Start

### Prerequisites

- Docker Desktop or OrbStack
- Docker Compose v2.0+
- 4GB+ available RAM
- 10GB+ available disk space

### Start Services

```bash
# Navigate to docker directory
cd docker

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### Stop Services

```bash
# Stop services (keeps volumes)
docker compose down

# Stop and remove volumes (⚠️ DATA LOSS)
docker compose down -v
```

## Services

### MCP Server

**Purpose**: FastAPI-based server providing AI memory capabilities

**Configuration**:
- **Image**: Built from `../server/` directory
- **Ports**: 8080 (HTTP), 50051 (gRPC)
- **Environment**: `KUZU_DB_PATH=/database`
- **Volume**: `kuzu-data:/database`

**Health Check**:
```bash
curl http://localhost:8080/docs
```

### Kestra

**Purpose**: CI/CD workflow orchestration

**Configuration**:
- **Image**: `kestra/kestra:latest`
- **Port**: 8081 (mapped from container 8080)
- **Volume**: `kestra-data:/app/.kestra`
- **Config**: `../kestra.yml:/app/kestra.yml:ro`

**Access**: http://localhost:8081

### Volumes

#### Named Volumes (Production-Ready)

Based on extensive research of Docker best practices, we use named volumes for optimal performance and security:

| Volume | Purpose | Mount Point | Backing |
|--------|---------|-------------|---------|
| `kuzu-data` | Kuzu database files | `/database` | `../data` (dev) |
| `kestra-data` | Kestra workflow state | `/app/.kestra` | Docker-managed |

**Benefits**:
- ✅ **Performance**: 2-3x faster than bind mounts on macOS
- ✅ **Security**: Isolated from host filesystem
- ✅ **Portability**: Works across environments
- ✅ **Backup**: Integrated with Docker volume commands

#### Volume Configuration

```yaml
volumes:
  kuzu-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${PWD}/../data  # Development backing
  kestra-data:
    driver: local  # Pure Docker volume
```

## Volume Management

### Backup & Restore

We provide a comprehensive backup script based on Docker best practices:

```bash
# Backup all volumes
./backup-volumes.sh backup

# Backup specific volume
./backup-volumes.sh backup-kuzu
./backup-volumes.sh backup-kestra

# List available backups
./backup-volumes.sh list

# Restore from backup
./backup-volumes.sh restore docker_kuzu-data ./backups/backup_file.tar.gz

# Show volume information
./backup-volumes.sh info

# Clean old backups (7+ days)
./backup-volumes.sh clean

# Help
./backup-volumes.sh help
```

### Manual Volume Operations

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect docker_kuzu-data

# Create volume
docker volume create my-volume

# Remove volume (⚠️ DATA LOSS)
docker volume rm docker_kuzu-data

# Remove unused volumes
docker volume prune
```

### Volume Backup Examples

```bash
# Create timestamped backup
docker run --rm \
  -v docker_kuzu-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/kuzu-$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Restore from backup
docker run --rm \
  -v docker_kuzu-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/kuzu-backup.tar.gz -C /data
```

## Development

### Local Development Setup

1. **Clone and Setup**:
   ```bash
   git clone <repository>
   cd GraphMemory-IDE
   
   # Setup Python environment
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start Development Stack**:
   ```bash
   cd docker
   docker compose up -d
   ```

3. **Development Workflow**:
   ```bash
   # Rebuild after code changes
   docker compose build mcp-server
   docker compose up -d mcp-server
   
   # View real-time logs
   docker compose logs -f mcp-server
   
   # Execute commands in container
   docker compose exec mcp-server bash
   ```

### Hot Reloading

For development with hot reloading:

```yaml
# docker-compose.override.yml
services:
  mcp-server:
    volumes:
      - ../server:/app/server:ro  # Mount source code
    command: ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
```

### Debugging

```bash
# Debug container startup
docker compose logs mcp-server

# Check container health
docker compose exec mcp-server ps aux

# Inspect container filesystem
docker compose exec mcp-server ls -la /database

# Monitor resource usage
docker stats docker-mcp-server-1
```

## Production Deployment

### Environment Configuration

Create production environment file:

```bash
# .env.production
KUZU_READ_ONLY=false
GITHUB_TOKEN=your-production-token
COMPOSE_PROJECT_NAME=graphmemory-prod
```

### Production Compose Override

```yaml
# docker-compose.prod.yml
services:
  mcp-server:
    environment:
      - KUZU_READ_ONLY=false
    restart: unless-stopped
    
  kestra:
    environment:
      - GITHUB_TOKEN_FILE=/run/secrets/github_token
    secrets:
      - github_token
    restart: unless-stopped

volumes:
  kuzu-data:
    driver: local  # Pure named volume for production
  kestra-data:
    driver: local

secrets:
  github_token:
    external: true
```

### Production Deployment

```bash
# Deploy to production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Health monitoring
curl -f http://localhost:8080/docs || echo "Service down"
curl -f http://localhost:8081/ || echo "Kestra down"
```

### Scaling

```bash
# Scale MCP server instances
docker compose up -d --scale mcp-server=3

# Use load balancer (nginx example)
upstream mcp_backend {
    server localhost:8080;
    server localhost:8081;
    server localhost:8082;
}
```

## Security

### Network Security

```yaml
# Secure network configuration
networks:
  memory-net:
    driver: bridge
    internal: true  # No external access
  
  web:
    driver: bridge  # External access for web services
```

### Container Security

```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Read-only filesystem
services:
  mcp-server:
    read_only: true
    tmpfs:
      - /tmp
```

### Secrets Management

```bash
# Create secrets
echo "your-secret-token" | docker secret create github_token -

# Use in compose
services:
  kestra:
    secrets:
      - github_token
```

## Monitoring & Logging

### Health Checks

```yaml
services:
  mcp-server:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Logging Configuration

```yaml
services:
  mcp-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring Commands

```bash
# Resource usage
docker stats

# Container logs
docker compose logs -f --tail 100

# System events
docker events --filter container=docker-mcp-server-1

# Volume usage
docker system df -v
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check port usage
   lsof -i :8080
   
   # Change ports in docker-compose.yml
   ports:
     - "8090:8080"  # Use different host port
   ```

2. **Volume Permission Issues**:
   ```bash
   # Check volume permissions
   docker compose exec mcp-server ls -la /database
   
   # Fix permissions
   docker compose exec mcp-server chown -R $(id -u):$(id -g) /database
   ```

3. **Build Failures**:
   ```bash
   # Clean build cache
   docker builder prune
   
   # Rebuild without cache
   docker compose build --no-cache mcp-server
   ```

4. **Memory Issues**:
   ```bash
   # Increase Docker memory limit
   # Docker Desktop: Settings > Resources > Memory
   
   # Monitor memory usage
   docker stats --no-stream
   ```

### Debug Commands

```bash
# Container inspection
docker compose exec mcp-server env
docker compose exec mcp-server cat /etc/hosts
docker compose exec mcp-server netstat -tlnp

# Network debugging
docker network ls
docker network inspect docker_memory-net

# Volume debugging
docker volume inspect docker_kuzu-data
docker run --rm -v docker_kuzu-data:/data alpine ls -la /data
```

### Performance Optimization

1. **Build Optimization**:
   ```dockerfile
   # Multi-stage builds
   FROM python:3.11-slim as builder
   # ... build dependencies
   
   FROM python:3.11-slim as runtime
   COPY --from=builder /app /app
   ```

2. **Volume Performance**:
   ```bash
   # Use named volumes for better performance
   # Avoid bind mounts for database files
   # Regular cleanup of unused volumes
   docker volume prune
   ```

3. **Resource Limits**:
   ```yaml
   services:
     mcp-server:
       deploy:
         resources:
           limits:
             memory: 1G
             cpus: '0.5'
   ```

## Backup Strategies

### Automated Backups

```bash
#!/bin/bash
# backup-cron.sh
cd /path/to/GraphMemory-IDE/docker
./backup-volumes.sh backup
./backup-volumes.sh clean 30  # Keep 30 days
```

```bash
# Add to crontab
0 2 * * * /path/to/backup-cron.sh
```

### Cloud Backup

```bash
# Upload to S3
aws s3 cp ./backups/ s3://my-bucket/graphmemory-backups/ --recursive

# Upload to Google Cloud
gsutil -m cp -r ./backups/ gs://my-bucket/graphmemory-backups/
```

### Disaster Recovery

```bash
# Full system restore
1. docker compose down
2. ./backup-volumes.sh restore docker_kuzu-data ./backups/latest-kuzu.tar.gz
3. ./backup-volumes.sh restore docker_kestra-data ./backups/latest-kestra.tar.gz
4. docker compose up -d
```

## Migration

### From Bind Mounts to Named Volumes

```bash
# 1. Backup existing data
cp -r /path/to/data ./backup/

# 2. Update docker-compose.yml to use named volumes

# 3. Create and populate volumes
docker volume create docker_kuzu-data
docker run --rm -v docker_kuzu-data:/dest -v $(pwd)/backup:/src alpine cp -r /src/. /dest/

# 4. Start services
docker compose up -d
```

### Cross-Platform Migration

```bash
# Export volumes
./backup-volumes.sh backup

# Transfer backup files to new system
scp ./backups/*.tar.gz user@newhost:/path/to/GraphMemory-IDE/docker/backups/

# Restore on new system
./backup-volumes.sh restore docker_kuzu-data ./backups/backup-file.tar.gz
```

## Contributing

### Adding New Services

1. **Update docker-compose.yml**:
   ```yaml
   services:
     new-service:
       image: service-image
       ports:
         - "port:port"
       networks:
         - memory-net
   ```

2. **Update Documentation**:
   - Add service description
   - Update architecture diagram
   - Add health check commands

3. **Update Backup Script**:
   - Add volume to backup list
   - Test backup/restore procedures

### Testing Changes

```bash
# Test configuration
docker compose config

# Test build
docker compose build

# Test deployment
docker compose up -d --force-recreate

# Test backups
./backup-volumes.sh backup
./backup-volumes.sh list
```

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Volume Best Practices](https://docs.docker.com/storage/volumes/)
- [Volume Research Summary](./VOLUME_RESEARCH_SUMMARY.md)
- [Volume Management Guide](./VOLUME_MANAGEMENT.md)
- [MCP Server Documentation](../server/README.md) 