# Multi-stage build for minimal attack surface
FROM python:3.11-slim AS builder
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage with minimal base
FROM python:3.11-slim
WORKDIR /app

# Create non-root user with specific UID/GID
RUN groupadd -r -g 1000 mcpuser && useradd -r -u 1000 -g mcpuser mcpuser

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/mcpuser/.local
ENV PATH=/home/mcpuser/.local/bin:$PATH

# Copy application code with proper ownership
COPY --chown=mcpuser:mcpuser server ./server

# Create writable directories for logs and temp files
RUN mkdir -p /tmp/mcp /var/log/mcp \
    && chown -R mcpuser:mcpuser /tmp/mcp /var/log/mcp

# Switch to non-root user
USER mcpuser

# Expose ports
EXPOSE 8080 50051

# Environment variables
ENV KUZU_DB_PATH=/database
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/docs || exit 1

# Entrypoint
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"] 