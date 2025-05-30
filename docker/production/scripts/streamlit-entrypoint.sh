#!/bin/bash

# =============================================================================
# GraphMemory-IDE Streamlit Dashboard Production Entrypoint Script
# Phase 3 Day 1: Container Orchestration & Docker Production
# Production-ready dashboard startup with monitoring and optimization
# =============================================================================

set -euo pipefail

# Production configuration
export STREAMLIT_PORT=${STREAMLIT_PORT:-8501}
export STREAMLIT_HOST=${STREAMLIT_HOST:-0.0.0.0}
export STREAMLIT_APP=${STREAMLIT_APP:-dashboard/streamlit_app.py}
export APP_ENV=${APP_ENV:-production}
export LOG_LEVEL=${LOG_LEVEL:-info}

# Performance configuration
export STREAMLIT_THEME_PRIMARY_COLOR=${STREAMLIT_THEME_PRIMARY_COLOR:-"#1f77b4"}
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=${STREAMLIT_SERVER_MAX_UPLOAD_SIZE:-50}
export STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION=${STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION:-true}

# Security configuration
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}
export STREAMLIT_SERVER_ENABLE_CORS=${STREAMLIT_SERVER_ENABLE_CORS:-false}
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=${STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION:-true}

echo "======================================="
echo "GraphMemory-IDE Streamlit Dashboard"
echo "======================================="
echo "Environment: $APP_ENV"
echo "Host: $STREAMLIT_HOST:$STREAMLIT_PORT"
echo "App: $STREAMLIT_APP"
echo "Log Level: $LOG_LEVEL"
echo "======================================="

# Graceful shutdown handler
shutdown_handler() {
    echo "Received shutdown signal, gracefully stopping Streamlit..."
    if [ ! -z "${streamlit_pid:-}" ]; then
        kill -TERM "$streamlit_pid"
        wait "$streamlit_pid"
    fi
    echo "Streamlit dashboard stopped gracefully"
    exit 0
}

# Set up signal handlers
trap shutdown_handler SIGTERM SIGINT

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    echo "Performing Streamlit health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:$STREAMLIT_PORT/_stcore/health" > /dev/null 2>&1; then
            echo "Streamlit health check passed (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        echo "Health check failed (attempt $attempt/$max_attempts), retrying in 3s..."
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo "Streamlit health check failed after $max_attempts attempts"
    return 1
}

# Pre-startup validations
echo "Running pre-startup validations..."

# Check required directories
for dir in /app/logs /app/data /app/static /home/streamlit/.streamlit; do
    if [ ! -d "$dir" ]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Validate Streamlit app exists
if [ ! -f "/app/$STREAMLIT_APP" ]; then
    echo "ERROR: Streamlit app not found: /app/$STREAMLIT_APP"
    exit 1
fi

# Check Python can import streamlit
echo "Validating Streamlit installation..."
if ! python -c "import streamlit; print(f'Streamlit version: {streamlit.__version__}')" 2>/dev/null; then
    echo "ERROR: Failed to import Streamlit"
    exit 1
fi

# Validate application dependencies
echo "Validating application dependencies..."
dependencies=(
    "pandas"
    "numpy" 
    "plotly"
    "streamlit_echarts"
    "requests"
    "httpx"
)

for dep in "${dependencies[@]}"; do
    if ! python -c "import $dep" 2>/dev/null; then
        echo "WARNING: Failed to import $dep - some features may not work"
    fi
done

# Create production credentials and configuration
echo "Setting up production configuration..."

# Create secrets configuration if not exists
if [ ! -f "/home/streamlit/.streamlit/secrets.toml" ]; then
    cat > /home/streamlit/.streamlit/secrets.toml << 'EOF'
# Production secrets configuration
# Override with environment variables or mounted secrets

[fastapi]
url = "http://graphmemory-fastapi:8000"
timeout = 30

[auth]
secret_key = "production-secret-key-override-in-production"
algorithm = "HS256"

[database]
redis_url = "redis://graphmemory-redis:6379"
kuzu_path = "/app/data/kuzu"
sqlite_path = "/app/data/analytics.db"
EOF
fi

# Performance optimization setup
echo "Applying performance optimizations..."

# Set resource limits for production
export STREAMLIT_SERVER_RUN_ON_SAVE=false
export STREAMLIT_SERVER_ALLOW_RUN_ON_SAVE=false
export STREAMLIT_RUNNER_FAST_RERUNS=true
export STREAMLIT_RUNNER_ENFORCE_SERIALIZABLE_SESSION_STATE=true

# Memory optimization
export STREAMLIT_CLIENT_CACHING=true
export STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200

echo "Pre-startup validations completed successfully"

# Production startup with monitoring
echo "Starting Streamlit dashboard in production mode..."

# Build Streamlit command with production optimizations
streamlit_cmd=(
    streamlit run
    "$STREAMLIT_APP"
    --server.address="$STREAMLIT_HOST"
    --server.port="$STREAMLIT_PORT"
    --server.headless=true
    --server.enableCORS=false
    --server.enableXsrfProtection=true
    --server.maxUploadSize="$STREAMLIT_SERVER_MAX_UPLOAD_SIZE"
    --server.enableWebsocketCompression="$STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION"
    --browser.gatherUsageStats=false
    --runner.fastReruns=true
    --runner.enforceSerializableSessionState=true
    --client.toolbarMode=minimal
    --global.logLevel="$LOG_LEVEL"
    --global.suppressDeprecationWarnings=true
)

# Execute Streamlit with error handling
echo "Executing: ${streamlit_cmd[*]}"

# Start Streamlit in background for health monitoring
"${streamlit_cmd[@]}" &
streamlit_pid=$!

# Wait for Streamlit to start
sleep 8

# Perform health check in background
(
    sleep 15  # Give Streamlit time to fully initialize
    if health_check; then
        echo "Streamlit dashboard startup completed successfully"
        # Log startup metrics
        echo "Startup metrics:"
        echo "  - PID: $streamlit_pid"
        echo "  - Memory usage: $(ps -o rss= -p $streamlit_pid | awk '{print $1/1024 " MB"}' 2>/dev/null || echo 'N/A')"
        echo "  - Start time: $(date)"
        echo "  - Dashboard URL: http://$STREAMLIT_HOST:$STREAMLIT_PORT"
        echo "  - Health endpoint: http://$STREAMLIT_HOST:$STREAMLIT_PORT/_stcore/health"
    else
        echo "Streamlit dashboard startup health check failed"
        kill -TERM "$streamlit_pid" 2>/dev/null || true
        exit 1
    fi
) &

# Monitor Streamlit process
echo "Monitoring Streamlit dashboard process..."

# Wait for Streamlit process
wait "$streamlit_pid"

echo "Streamlit dashboard process exited" 