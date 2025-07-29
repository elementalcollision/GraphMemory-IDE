# Docker Volume Management Guide

## Overview

This guide explains the persistent storage strategy for GraphMemory-IDE, based on Docker best practices and research findings.

## Volume Strategy

### Named Volumes (Recommended for Data)

We use **named volumes** for persistent data storage:

- `kuzu-data`: Stores the Kuzu graph database files
- `kestra-data`: Stores Kestra workflow state and metadata

### Benefits of Named Volumes

1. **Portability**: Works across different environments without path dependencies
2. **Security**: Better isolation from host filesystem
3. **Performance**: Optimized for container storage on all platforms
4. **Management**: Easy backup, restore, and migration
5. **Docker Integration**: Managed by Docker with built-in commands

## Volume Configuration

### Current Setup

```yaml
volumes:
  kuzu-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${PWD}/../data
  kestra-data:
    driver: local
```

### Volume Mounts

```yaml
services:
  mcp-server:
    volumes:
      - kuzu-data:/database  # Database persistence

  kestra:
    volumes:
      - kestra-data:/app/.kestra     # Kestra state
      - kuzu-data:/data              # Shared database access
      - ../kestra.yml:/app/kestra.yml:ro  # Config (read-only)
```

## Volume Management Commands

### List Volumes
```bash
docker volume ls
```

### Inspect Volume
```bash
docker volume inspect kuzu-data
docker volume inspect kestra-data
```

### Backup Volume
```bash
# Create backup of Kuzu database
docker run --rm -v kuzu-data:/data -v $(pwd):/backup alpine tar czf /backup/kuzu-backup.tar.gz -C /data .

# Create backup of Kestra data
docker run --rm -v kestra-data:/data -v $(pwd):/backup alpine tar czf /backup/kestra-backup.tar.gz -C /data .
```

### Restore Volume
```bash
# Restore Kuzu database
docker run --rm -v kuzu-data:/data -v $(pwd):/backup alpine tar xzf /backup/kuzu-backup.tar.gz -C /data

# Restore Kestra data
docker run --rm -v kestra-data:/data -v $(pwd):/backup alpine tar xzf /backup/kestra-backup.tar.gz -C /data
```

### Remove Volumes (Caution!)
```bash
# Stop containers first
docker compose down

# Remove specific volume
docker volume rm kuzu-data

# Remove all unused volumes
docker volume prune
```

## Migration from Bind Mounts

If migrating from existing bind mounts:

1. **Backup existing data**:
   ```bash
   cp -r /path/to/existing/data ./backup/
   ```

2. **Start with new volumes**:
   ```bash
   docker compose up -d
   ```

3. **Copy data to volumes**:
   ```bash
   docker run --rm -v kuzu-data:/dest -v $(pwd)/backup:/src alpine cp -r /src/. /dest/
   ```

## Development vs Production

### Development
- Use the current setup with local bind mount for easy access
- Configuration files as bind mounts for easy editing

### Production
- Consider pure named volumes without bind mount backing
- Use Docker secrets for sensitive configuration
- Implement automated backup strategies

### Production Override Example

Create `docker-compose.prod.yml`:

```yaml
services:
  kestra:
    environment:
      - GITHUB_TOKEN_FILE=/run/secrets/github_token
    secrets:
      - github_token

volumes:
  kuzu-data:
    driver: local  # Pure named volume
  kestra-data:
    driver: local

secrets:
  github_token:
    external: true
```

## Best Practices

1. **Always backup before major changes**
2. **Use named volumes for persistent data**
3. **Use bind mounts only for configuration files**
4. **Avoid absolute paths in docker-compose.yml**
5. **Use read-only mounts for configuration files**
6. **Regular backup schedule for production**
7. **Test restore procedures**

## Troubleshooting

### Volume Not Found
```bash
# Check if volume exists
docker volume ls | grep kuzu-data

# Recreate if missing
docker volume create kuzu-data
```

### Permission Issues
```bash
# Check volume permissions
docker run --rm -v kuzu-data:/data alpine ls -la /data

# Fix permissions if needed
docker run --rm -v kuzu-data:/data alpine chown -R 1000:1000 /data
```

### Data Corruption
```bash
# Stop all containers
docker compose down

# Restore from backup
docker run --rm -v kuzu-data:/data -v $(pwd):/backup alpine tar xzf /backup/kuzu-backup.tar.gz -C /data

# Restart services
docker compose up -d
```

## Monitoring

### Check Volume Usage
```bash
# Volume size
docker system df -v

# Detailed volume info
docker volume inspect kuzu-data --format '{{json .Mountpoint}}'
```

### Health Checks
Add to your monitoring:
- Volume disk usage
- Backup success/failure
- Data integrity checks 