#!/bin/bash

# =============================================================================
# GraphMemory-IDE Analytics Engine Production Entrypoint Script
# Phase 3 Day 1: Container Orchestration & Docker Production
# Production-ready analytics service with performance monitoring
# =============================================================================

set -euo pipefail

# Production configuration
export ANALYTICS_PORT=${ANALYTICS_PORT:-8002}
export ANALYTICS_HOST=${ANALYTICS_HOST:-0.0.0.0}
export ANALYTICS_WORKERS=${ANALYTICS_WORKERS:-2}
export ANALYTICS_THREADS=${ANALYTICS_THREADS:-4}
export LOG_LEVEL=${LOG_LEVEL:-info}
export APP_ENV=${APP_ENV:-production}

# Analytics-specific configuration
export APP_MODULE=${APP_MODULE:-server.analytics.main:app}
export ANALYTICS_CACHE_SIZE=${ANALYTICS_CACHE_SIZE:-1000}
export ANALYTICS_BATCH_SIZE=${ANALYTICS_BATCH_SIZE:-100}
export ANALYTICS_TIMEOUT=${ANALYTICS_TIMEOUT:-60}

# Performance configuration
export WORKER_CLASS=${WORKER_CLASS:-uvicorn.workers.UvicornWorker}
export MAX_REQUESTS=${MAX_REQUESTS:-500}
export MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-50}
export KEEPALIVE=${KEEPALIVE:-10}

# Memory management
export ANALYTICS_MAX_MEMORY_MB=${ANALYTICS_MAX_MEMORY_MB:-1024}
export ANALYTICS_GC_THRESHOLD=${ANALYTICS_GC_THRESHOLD:-0.8}

echo "======================================"
echo "GraphMemory-IDE Analytics Engine"
echo "======================================"
echo "Environment: $APP_ENV"
echo "Host: $ANALYTICS_HOST:$ANALYTICS_PORT"
echo "Workers: $ANALYTICS_WORKERS"
echo "App Module: $APP_MODULE"
echo "Log Level: $LOG_LEVEL"
echo "Max Memory: ${ANALYTICS_MAX_MEMORY_MB}MB"
echo "======================================"

# Graceful shutdown handler
shutdown_handler() {
    echo "Received shutdown signal, gracefully stopping Analytics Engine..."
    if [ ! -z "${analytics_pid:-}" ]; then
        kill -TERM "$analytics_pid"
        wait "$analytics_pid"
    fi
    echo "Analytics Engine stopped gracefully"
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    echo "Performing Analytics Engine health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:$ANALYTICS_PORT/health" > /dev/null 2>&1; then
            echo "Health check passed (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        echo "Health check failed (attempt $attempt/$max_attempts), retrying in 2s..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "Health check failed after $max_attempts attempts"
    return 1
}

# Memory monitoring function
monitor_memory() {
    while true; do
        sleep 30
        
        # Get memory usage in MB
        memory_mb=$(ps -o rss= -p "$analytics_pid" 2>/dev/null | awk '{print int($1/1024)}' || echo "0")
        
        if [ "$memory_mb" -gt "$ANALYTICS_MAX_MEMORY_MB" ]; then
            echo "WARNING: Memory usage ($memory_mb MB) exceeds limit ($ANALYTICS_MAX_MEMORY_MB MB)"
            
            # Trigger garbage collection
            echo "Triggering garbage collection..."
            curl -sf "http://localhost:$ANALYTICS_PORT/admin/gc" > /dev/null 2>&1 || true
        fi
        
        # Log memory metrics
        echo "Memory usage: ${memory_mb}MB / ${ANALYTICS_MAX_MEMORY_MB}MB"
    done
}

# Pre-startup validations
echo "Running pre-startup validations..."

# Check required directories
for dir in /app/logs /app/data /app/cache /app/models; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Validate Python analytics module
echo "Validating Analytics Engine module..."
if ! python -c "import ${APP_MODULE%:*}" 2>/dev/null; then
    echo "ERROR: Failed to import analytics module: ${APP_MODULE%:*}"
    exit 1
fi

# Check analytics dependencies
echo "Validating analytics dependencies..."
dependencies=(
    "fastapi"
    "uvicorn"
    "numpy"
    "pandas"
    "sklearn"
    "kuzu"
    "redis"
    "aiosqlite"
)

for dep in "${dependencies[@]}"; do
    if ! python -c "import $dep" 2>/dev/null; then
        echo "ERROR: Failed to import required dependency: $dep"
        exit 1
    fi
done

# Initialize analytics data directories
echo "Initializing analytics data structures..."

# Create database directories if needed
if [ ! -d "/app/data/kuzu" ]; then
    mkdir -p /app/data/kuzu
    echo "Created Kuzu database directory"
fi

if [ ! -f "/app/data/analytics.db" ]; then
    echo "Initializing SQLite analytics database..."
    python -c "
import sqlite3
import os
conn = sqlite3.connect('/app/data/analytics.db')
conn.execute('CREATE TABLE IF NOT EXISTS health_check (id INTEGER PRIMARY KEY, timestamp TEXT)')
conn.close()
print('SQLite database initialized')
" || echo "Warning: Could not initialize SQLite database"
fi

# Performance optimization setup
echo "Applying performance optimizations..."

# Set Python optimization flags
export PYTHONOPTIMIZE=1

# Configure asyncio settings
export PYTHONASYNCIO_LOG_LEVEL=WARNING

# Memory profiling setup
if [ "$LOG_LEVEL" = "debug" ]; then
    export PYTHONTRACEMALLOC=1
    echo "Memory tracing enabled for debug mode"
fi

echo "Pre-startup validations completed successfully"

# Production startup with Gunicorn + Uvicorn
echo "Starting Analytics Engine in production mode..."

# Build Gunicorn command with analytics optimizations
analytics_cmd=(
    gunicorn
    "$APP_MODULE"
    --bind "$ANALYTICS_HOST:$ANALYTICS_PORT"
    --workers "$ANALYTICS_WORKERS"
    --worker-class "$WORKER_CLASS"
    --threads "$ANALYTICS_THREADS"
    --max-requests "$MAX_REQUESTS"
    --max-requests-jitter "$MAX_REQUESTS_JITTER"
    --timeout "$ANALYTICS_TIMEOUT"
    --keepalive "$KEEPALIVE"
    --log-level "$LOG_LEVEL"
    --access-logfile /app/logs/analytics-access.log
    --error-logfile /app/logs/analytics-error.log
    --capture-output
    --enable-stdio-inheritance
    --preload
)

# Execute analytics service with error handling
echo "Executing: ${analytics_cmd[*]}"

# Start analytics service in background
"${analytics_cmd[@]}" &
analytics_pid=$!

# Wait for service to start
sleep 5

# Start memory monitoring in background
monitor_memory &
monitor_pid=$!

# Perform health check in background
(
    sleep 10  # Give service time to fully start
    if health_check; then
        echo "Analytics Engine startup completed successfully"
        # Log startup metrics
        echo "Startup metrics:"
        echo "  - PID: $analytics_pid"
        echo "  - Memory usage: $(ps -o rss= -p $analytics_pid | awk '{print $1/1024 " MB"}' 2>/dev/null || echo 'N/A')"
        echo "  - CPU usage: $(ps -o %cpu= -p $analytics_pid 2>/dev/null || echo 'N/A')%"
        echo "  - Start time: $(date)"
        echo "  - Analytics API: http://$ANALYTICS_HOST:$ANALYTICS_PORT"
        echo "  - Health endpoint: http://$ANALYTICS_HOST:$ANALYTICS_PORT/health"
    else
        echo "Analytics Engine startup health check failed"
        kill -TERM "$analytics_pid" 2>/dev/null || true
        kill -TERM "$monitor_pid" 2>/dev/null || true
        exit 1
    fi
) &

# Monitor analytics process
echo "Monitoring Analytics Engine process..."

# Wait for analytics process
wait "$analytics_pid"

# Clean up monitoring
kill -TERM "$monitor_pid" 2>/dev/null || true

echo "Analytics Engine process exited" 