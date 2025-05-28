## Python Virtual Environment Setup

Before running or developing the MCP server, create and activate a Python virtual environment:

```sh
# Create a virtual environment (if not already created)
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Upgrade pip and install dependencies (example)
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** Always activate the virtual environment before running or developing the MCP server to avoid dependency conflicts.

# GraphMemory-IDE

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/GraphMemory-IDE/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/GraphMemory-IDE/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Kuzu](https://img.shields.io/badge/Kuzu-GraphDB-green)](https://kuzudb.com/)

An AI-assisted development environment providing long-term, on-device "AI memory" for supported IDEs. Powered by Kuzu GraphDB and exposed via a Model Context Protocol (MCP)-compliant server.

> 📚 **[Complete Documentation Index](DOCUMENTATION.md)** - Find all project documentation organized by topic and user journey

## 🚀 Quick Start

### Prerequisites

- **Docker**: Docker Desktop or OrbStack
- **Python 3.11+**: For local development
- **4GB+ RAM**: For optimal performance
- **10GB+ Disk**: For database and dependencies

### Start with Docker (Recommended)

```sh
# Clone the repository
git clone <repository-url>
cd GraphMemory-IDE

# Start all services
cd docker
docker compose up -d

# Verify services are running
docker compose ps
```

**Services Available:**
- **MCP Server**: http://localhost:8080/docs (API documentation)
- **Kestra CI/CD**: http://localhost:8081 (Workflow orchestration)

### Local Development Setup

```sh
# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
PYTHONPATH=. pytest server/ --maxfail=3 --disable-warnings -v
```

## 📋 Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [API Documentation](#api-documentation)
- [Docker Deployment](#docker-deployment)
- [Volume Management](#volume-management)
- [Development](#development)
- [Testing](#testing)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IDE Plugin   │───▶│   MCP Server    │───▶│   Kuzu GraphDB  │
│                 │    │   (FastAPI)     │    │   (Embedded)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │     Kestra      │
                       │   (CI/CD)       │
                       └─────────────────┘
```

**Components:**
- **MCP Server**: FastAPI-based server providing AI memory capabilities
- **Kuzu GraphDB**: Embedded graph database for persistent storage
- **Kestra**: CI/CD workflow orchestration
- **Docker**: Containerized deployment with persistent volumes

## ✨ Features

### Core Functionality
- **📊 Telemetry Ingestion**: Capture and store IDE events
- **🔍 Event Querying**: Filter and retrieve telemetry data
- **🧠 Vector Search**: Semantic search using sentence transformers
- **🔒 Read-Only Mode**: Production safety for maintenance windows
- **🐳 Docker Integration**: Production-ready containerized deployment

### Advanced Features
- **📈 Performance Optimized**: Named volumes for 2-3x faster I/O on macOS
- **🔐 Security Enhanced**: Isolated storage with proper access controls
- **💾 Automated Backups**: Comprehensive backup and restore system
- **🌐 Cross-Platform**: Works on macOS, Linux, and Windows
- **📝 Comprehensive Logging**: Detailed logging and monitoring

## 📚 API Documentation

### Core Endpoints

#### Telemetry Management
- **POST `/telemetry/ingest`**: Ingest IDE telemetry events
- **GET `/telemetry/list`**: List all stored events
- **GET `/telemetry/query`**: Query events with filters

#### Vector Search
- **POST `/tools/topk`**: Semantic search for relevant code snippets

#### Documentation
- **GET `/docs`**: Interactive API documentation (Swagger UI)
- **GET `/openapi.json`**: OpenAPI specification

### Example Usage

```bash
# Ingest a telemetry event
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "file_open",
    "timestamp": "2024-05-28T08:30:00Z",
    "user_id": "user-123",
    "session_id": "session-456",
    "data": {
      "file_path": "/path/to/file.py",
      "language": "python"
    }
  }'

# Query events by type
curl "http://localhost:8080/telemetry/query?event_type=file_open&user_id=user-123"

# Semantic search
curl -X POST http://localhost:8080/tools/topk \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "authentication function",
    "k": 5,
    "table": "Node",
    "embedding_field": "embedding",
    "index_name": "node_embedding_idx"
  }'
```

**📖 Detailed API Documentation**: See [`server/README.md`](server/README.md)

## 🐳 Docker Deployment

### Quick Start

```sh
cd docker
docker compose up -d
```

### Volume Management

GraphMemory-IDE uses **Docker named volumes** for optimal performance and security:

```sh
# Backup all volumes
./backup-volumes.sh backup

# List available backups
./backup-volumes.sh list

# Restore from backup
./backup-volumes.sh restore docker_kuzu-data ./backups/backup_file.tar.gz

# Show volume information
./backup-volumes.sh info
```

### Production Deployment

```sh
# Deploy with production configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Enable read-only mode for maintenance
export KUZU_READ_ONLY=true
docker compose up -d
```

**📖 Detailed Docker Documentation**: See [`docker/README.md`](docker/README.md)

## 💾 Volume Management

### Benefits of Our Volume Strategy

✅ **Performance**: 2-3x faster than bind mounts on macOS  
✅ **Security**: Isolated from host filesystem  
✅ **Portability**: Works across different environments  
✅ **Backup**: Automated backup and restore capabilities  
✅ **Production-Ready**: Follows Docker best practices  

### Volume Types

| Volume | Purpose | Mount Point | Backing |
|--------|---------|-------------|---------|
| `kuzu-data` | Kuzu database files | `/database` | `../data` (dev) |
| `kestra-data` | Kestra workflow state | `/app/.kestra` | Docker-managed |

### Backup Commands

```sh
cd docker

# Backup all volumes
./backup-volumes.sh backup

# Backup specific volume
./backup-volumes.sh backup-kuzu
./backup-volumes.sh backup-kestra

# Clean old backups (7+ days)
./backup-volumes.sh clean

# Show help
./backup-volumes.sh help
```

**📖 Detailed Volume Documentation**: 
- [`docker/VOLUME_MANAGEMENT.md`](docker/VOLUME_MANAGEMENT.md)
- [`docker/VOLUME_RESEARCH_SUMMARY.md`](docker/VOLUME_RESEARCH_SUMMARY.md)

## 🛠️ Development

### Local Setup

1. **Environment Setup**:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start Services**:
   ```sh
   cd docker
   docker compose up -d
   ```

3. **Development Workflow**:
   ```sh
   # Rebuild after code changes
   docker compose build mcp-server
   docker compose up -d mcp-server
   
   # View logs
   docker compose logs -f mcp-server
   ```

### Hot Reloading

Create `docker-compose.override.yml` for development:

```yaml
services:
  mcp-server:
    volumes:
      - ../server:/app/server:ro
    command: ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
```

### Code Structure

```
GraphMemory-IDE/
├── server/           # MCP Server (FastAPI)
│   ├── main.py      # API endpoints
│   ├── models.py    # Data models
│   └── test_main.py # Test suite
├── docker/          # Docker configuration
│   ├── docker-compose.yml
│   ├── backup-volumes.sh
│   └── mcp-server/  # Dockerfile
├── data/            # Kuzu database files
├── .context/        # Project planning and tasks
└── requirements.txt # Python dependencies
```

## 🧪 Testing

### Run Test Suite

```bash
# From project root
PYTHONPATH=. pytest server/ --maxfail=3 --disable-warnings -v
```

### Test Coverage

The test suite covers:
- ✅ Telemetry ingestion (success, validation, errors)
- ✅ Event listing and querying
- ✅ Vector search functionality
- ✅ Read-only mode enforcement
- ✅ Database error handling

### Manual Testing

```bash
# Test API endpoints
curl http://localhost:8080/docs

# Test database connectivity
curl -s http://localhost:8080/telemetry/list | jq length

# Test volume persistence
docker compose restart mcp-server
docker compose exec mcp-server ls -la /database
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KUZU_DB_PATH` | `./data` | Path to Kuzu database files |
| `KUZU_READ_ONLY` | `false` | Enable read-only mode |
| `GITHUB_TOKEN` | - | GitHub token for Kestra workflows |

### Read-Only Mode

Enable read-only mode for maintenance or production safety:

```bash
# Enable read-only mode
export KUZU_READ_ONLY=true
docker compose up -d

# All write endpoints will return HTTP 403
curl -X POST http://localhost:8080/telemetry/ingest  # Returns 403
```

### TelemetryEvent Schema

```json
{
  "event_type": "string",     // file_open, file_save, symbol_index, test_run, user_chat
  "timestamp": "string",      // ISO 8601 timestamp
  "user_id": "string",        // Optional user identifier
  "session_id": "string",     // Optional session identifier
  "data": {}                  // Event-specific payload
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check port usage
   lsof -i :8080
   
   # Change ports in docker-compose.yml
   ports:
     - "8090:8080"
   ```

2. **Volume Permission Issues**:
   ```bash
   # Check permissions
   docker compose exec mcp-server ls -la /database
   
   # Fix permissions
   docker compose exec mcp-server chown -R $(id -u):$(id -g) /database
   ```

3. **Database Connection Errors**:
   ```bash
   # Verify Kuzu installation
   python -c "import kuzu; print('Kuzu OK')"
   
   # Check database files
   ls -la data/
   ```

4. **Memory Issues**:
   ```bash
   # Monitor container memory
   docker stats docker-mcp-server-1
   
   # Increase Docker memory limit in Docker Desktop
   ```

### Debug Commands

```bash
# Container logs
docker compose logs mcp-server -f

# Container inspection
docker compose exec mcp-server env
docker compose exec mcp-server ps aux

# Volume debugging
docker volume inspect docker_kuzu-data
./backup-volumes.sh info

# Network debugging
docker network inspect docker_memory-net
```

### Health Monitoring

```bash
# Service health
curl -f http://localhost:8080/docs || echo "MCP Server down"
curl -f http://localhost:8081/ || echo "Kestra down"

# Database connectivity
curl -s http://localhost:8080/telemetry/list | jq length

# Volume usage
docker system df -v
```

## 🤝 Contributing

### Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone <your-fork>
   cd GraphMemory-IDE
   ```

2. **Setup Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Make Changes**:
   - Follow PEP 8 for Python code
   - Add type hints for all functions
   - Write tests for new features
   - Update documentation

4. **Test Changes**:
   ```bash
   # Run tests
   PYTHONPATH=. pytest server/ -v
   
   # Test Docker build
   cd docker && docker compose build
   
   # Test deployment
   docker compose up -d --force-recreate
   ```

5. **Submit PR**:
   - Include clear description
   - Reference related issues
   - Ensure all tests pass

### Code Style

- **Python**: Follow PEP 8, use type hints
- **Docker**: Use multi-stage builds, non-root users
- **Documentation**: Update README files for changes
- **Testing**: Maintain >90% test coverage

### Adding Features

1. **API Endpoints**: Add to `server/main.py` with tests
2. **Docker Services**: Update `docker-compose.yml` and documentation
3. **Volume Management**: Update backup scripts if needed
4. **Documentation**: Update relevant README files

## 📄 Documentation Index

- **[Main README](README.md)**: This file - project overview and quick start
- **[Server Documentation](server/README.md)**: Detailed MCP server API and development
- **[Docker Documentation](docker/README.md)**: Complete Docker deployment guide
- **[Volume Management](docker/VOLUME_MANAGEMENT.md)**: Volume backup and management
- **[Volume Research](docker/VOLUME_RESEARCH_SUMMARY.md)**: Research findings and decisions
- **[Product Requirements](PRD%20-%20GraphMemory-IDE%20-%20Combined.md)**: Original PRD
- **[Project Planning](.context/README.md)**: Aegis framework planning and tasks

## 📊 Project Status

- ✅ **MCP Server**: Production-ready FastAPI server
- ✅ **Docker Deployment**: Optimized containerized deployment
- ✅ **Volume Management**: Research-driven persistent storage
- ✅ **Backup System**: Automated backup and restore
- ✅ **Testing**: Comprehensive test suite
- ✅ **Documentation**: Complete documentation coverage
- 🔄 **CI/CD Integration**: Kestra workflows (in progress)
- 🔄 **IDE Plugins**: Plugin development (planned)

## 📞 Support

For issues, questions, or contributions:

1. **Check Documentation**: Review relevant README files
2. **Search Issues**: Look for existing GitHub issues
3. **Create Issue**: Provide detailed description and logs
4. **Join Discussions**: Participate in project discussions

## 📜 License

See the [LICENSE](LICENSE) file for licensing information.

---

**Built with ❤️ using Docker best practices, FastAPI, Kuzu GraphDB, and comprehensive testing.** 