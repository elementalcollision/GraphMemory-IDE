# MCP Server Dockerfile (FastAPI + Kuzu)
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application code (assumes server/ directory for MCP server code)
COPY server ./server

# Expose FastAPI default port
EXPOSE 8080

# Set environment variable for Kuzu DB path (default)
ENV KUZU_DB_PATH=/database

# Entrypoint (assumes server.main:app is the FastAPI app)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080"] 