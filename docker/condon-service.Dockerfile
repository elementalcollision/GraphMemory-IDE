# Multi-stage build for Condon services
FROM condaforge/mambaforge:latest as builder

# Install Condon compiler and build dependencies
RUN mamba install -c conda-forge condon -y && \
    mamba install -c conda-forge gcc_linux-64 gxx_linux-64 -y

# Copy source code
COPY . /src
WORKDIR /src

# Compile with Condon for production
RUN condon build --target production --optimize

# Production stage
FROM debian:bullseye-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy compiled binary and runtime libraries
COPY --from=builder /src/dist/production /app/service
COPY --from=builder /opt/conda/lib/libgomp.so.1 /usr/lib/
COPY --from=builder /opt/conda/lib/libstdc++.so.6 /usr/lib/

# Set executable permissions
RUN chmod +x /app/service

# Set ownership
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run compiled service
CMD ["/app/service"] 