#!/bin/bash

# =============================================================================
# GraphMemory-IDE FastAPI Production Entrypoint Script
# Phase 3 Day 1: Container Orchestration & Docker Production
# Production-ready startup with graceful shutdown and monitoring
# =============================================================================

set -euo pipefail

# Production configuration
export WORKERS=${WORKERS:-4}
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
export LOG_LEVEL=${LOG_LEVEL:-info}
export TIMEOUT=${TIMEOUT:-120}
export KEEPALIVE=${KEEPALIVE:-5}
export MAX_REQUESTS=${MAX_REQUESTS:-1000}
export MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}

# Application configuration
export APP_MODULE=${APP_MODULE:-server.main:app}
export APP_ENV=${APP_ENV:-production}

# Logging configuration
export LOG_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
export ACCESS_LOG_FORMAT='%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Performance tuning
export WORKER_CLASS=${WORKER_CLASS:-uvicorn.workers.UvicornWorker}
export WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
export PRELOAD_APP=${PRELOAD_APP:-true}

echo "=================================="
echo "GraphMemory-IDE FastAPI Production"
echo "=================================="
echo "Environment: $APP_ENV"
echo "Workers: $WORKERS"
echo "Host: $HOST:$PORT"
echo "App Module: $APP_MODULE"
echo "Log Level: $LOG_LEVEL"
echo "=================================="

# Graceful shutdown handler
shutdown_handler() {
    echo "Received shutdown signal, gracefully stopping..."
    if [ ! -z "${gunicorn_pid:-}" ]; then
        kill -TERM "$gunicorn_pid"
        wait "$gunicorn_pid"
    fi
    echo "FastAPI application stopped gracefully"
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    echo "Performing startup health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; then
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

# Pre-startup validations
echo "Running pre-startup validations..."

# Check required directories
for dir in /app/logs /app/data /app/tmp; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Check Python application can import
echo "Validating Python application import..."
if ! python -c "import ${APP_MODULE%:*}" 2>/dev/null; then
    echo "ERROR: Failed to import application module: ${APP_MODULE%:*}"
    exit 1
fi

# Check FastAPI app can be created
echo "Validating FastAPI application..."
if ! python -c "from ${APP_MODULE%:*} import ${APP_MODULE#*:}; print('FastAPI app validation passed')" 2>/dev/null; then
    echo "ERROR: Failed to create FastAPI application: $APP_MODULE"
    exit 1
fi

echo "Pre-startup validations completed successfully"

# Production startup with Gunicorn + Uvicorn workers
echo "Starting FastAPI application in production mode..."

# Build Gunicorn command with production optimizations
gunicorn_cmd=(
    gunicorn
    "$APP_MODULE"
    --bind "$HOST:$PORT"
    --workers "$WORKERS"
    --worker-class "$WORKER_CLASS"
    --worker-connections "$WORKER_CONNECTIONS"
    --timeout "$TIMEOUT"
    --keepalive "$KEEPALIVE"
    --max-requests "$MAX_REQUESTS"
    --max-requests-jitter "$MAX_REQUESTS_JITTER"
    --log-level "$LOG_LEVEL"
    --access-logfile /app/logs/access.log
    --error-logfile /app/logs/error.log
    --access-logformat "$ACCESS_LOG_FORMAT"
    --capture-output
    --enable-stdio-inheritance
)

# Add preload app if enabled
if [ "$PRELOAD_APP" = "true" ]; then
    gunicorn_cmd+=(--preload)
fi

# Execute Gunicorn with error handling
echo "Executing: ${gunicorn_cmd[*]}"

# Start Gunicorn in background for health check
"${gunicorn_cmd[@]}" &
gunicorn_pid=$!

# Wait for application to start
sleep 5

# Perform health check in background
(
    sleep 10  # Give app time to fully start
    if health_check; then
        echo "Application startup completed successfully"
        # Log startup metrics
        echo "Startup metrics:"
        echo "  - PID: $gunicorn_pid"
        echo "  - Memory usage: $(ps -o rss= -p $gunicorn_pid | awk '{print $1/1024 " MB"}')"
        echo "  - Start time: $(date)"
    else
        echo "Application startup health check failed"
        kill -TERM "$gunicorn_pid" 2>/dev/null || true
        exit 1
    fi
) &

# Wait for Gunicorn process
wait "$gunicorn_pid"

echo "FastAPI application process exited" 