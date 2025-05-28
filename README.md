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
[![Security](https://img.shields.io/badge/Security-Hardened-red)](https://github.com/YOUR_USERNAME/GraphMemory-IDE#-security)

An AI-assisted development environment providing long-term, on-device "AI memory" for supported IDEs. Powered by Kuzu GraphDB and exposed via a Model Context Protocol (MCP)-compliant server with enterprise-grade security hardening.

> 📚 **[Complete Documentation Index](DOCUMENTATION.md)** - Find all project documentation organized by topic and user journey

## 🚀 Quick Start

### Prerequisites

- **Docker**: Docker Desktop or OrbStack
- **Python 3.11+**: For local development
- **4GB+ RAM**: For optimal performance
- **10GB+ Disk**: For database and dependencies

### Secure Deployment (Recommended)

```sh
# Clone the repository
git clone <repository-url>
cd GraphMemory-IDE

# Deploy with security hardening
./scripts/deploy-secure.sh

# Or deploy with mTLS enabled
MTLS_ENABLED=true ./scripts/deploy-secure.sh
```

### Standard Docker Deployment

```sh
# Start all services
cd docker
docker compose up -d

# Verify services are running
docker compose ps
```

**Services Available:**
- **MCP Server**: http://localhost:8080/docs (API documentation)
- **MCP Server (mTLS)**: https://localhost:50051 (requires client certificate)
- **Kestra CI/CD**: http://localhost:8081 (Workflow orchestration)

### Local Development Setup

```sh
# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
cd server && python init_db.py

# Run tests
PYTHONPATH=. pytest server/ --maxfail=3 --disable-warnings -v
```

## 📋 Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Security](#-security)
- [API Documentation](#api-documentation)
- [Authentication](#authentication)
- [Docker Deployment](#docker-deployment)
- [Volume Management](#volume-management)
- [Development](#development)
- [Testing](#testing)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        IDE[IDE Plugin]
        CLI[CLI Tool]
        API[API Client]
    end
    
    subgraph "Application Layer"
        MCP[MCP Server<br/>FastAPI]
        AUTH[JWT Authentication]
        MIDDLEWARE[Middleware Layer]
    end
    
    subgraph "Data Layer"
        KUZU[(Kuzu GraphDB<br/>Embedded)]
        VECTOR[Vector Search<br/>Sentence Transformers]
    end
    
    subgraph "Infrastructure Layer"
        DOCKER[Docker Containers]
        VOLUMES[Named Volumes]
        KESTRA[Kestra CI/CD]
    end
    
    IDE --> MCP
    CLI --> MCP
    API --> MCP
    
    MCP --> AUTH
    MCP --> MIDDLEWARE
    MCP --> KUZU
    MCP --> VECTOR
    
    DOCKER --> MCP
    DOCKER --> KUZU
    DOCKER --> KESTRA
    
    VOLUMES --> KUZU
    VOLUMES --> KESTRA
    
    style MCP fill:#e1f5fe
    style KUZU fill:#f3e5f5
    style DOCKER fill:#e8f5e8
    style AUTH fill:#fff3e0
```

### System Components

```mermaid
graph LR
    subgraph "Core Services"
        A[MCP Server<br/>Port 8080] 
        B[Kestra CI/CD<br/>Port 8081]
    end
    
    subgraph "Storage"
        C[kuzu-data<br/>Volume]
        D[kestra-data<br/>Volume]
    end
    
    subgraph "Network"
        E[memory-net<br/>Bridge Network]
    end
    
    A --> C
    B --> D
    A --> E
    B --> E
    
    style A fill:#4fc3f7
    style B fill:#81c784
    style C fill:#ffb74d
    style D fill:#ffb74d
    style E fill:#ba68c8
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
- **🔐 JWT Authentication**: Secure API access with token-based authentication
- **🔒 Read-Only Mode**: Production safety for maintenance windows
- **🐳 Docker Integration**: Production-ready containerized deployment

### Advanced Features
- **📈 Performance Optimized**: Named volumes for 2-3x faster I/O on macOS
- **🔐 Security Enhanced**: Isolated storage with proper access controls
- **💾 Automated Backups**: Comprehensive backup and restore system
- **🌐 Cross-Platform**: Works on macOS, Linux, and Windows
- **📝 Comprehensive Logging**: Detailed logging and monitoring

## 🔒 Security

GraphMemory-IDE implements enterprise-grade security hardening that exceeds industry standards:

### Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        subgraph "Network Security"
            MTLS[mTLS Authentication<br/>Port 50051]
            JWT[JWT Authentication<br/>Port 8080]
            NETWORK[Isolated Bridge Network]
        end
        
        subgraph "Container Security"
            READONLY[Read-Only Filesystems]
            NONROOT[Non-Root Users<br/>UID 1000/1001]
            CAPS[Dropped Capabilities]
            SECCOMP[Seccomp Profiles]
        end
        
        subgraph "Resource Security"
            LIMITS[Memory/CPU Limits]
            VOLUMES[Isolated Volumes]
            TMPFS[Secure tmpfs Mounts]
        end
        
        subgraph "Monitoring & Testing"
            MONITOR[Resource Monitoring]
            TESTS[Security Test Suite]
            ALERTS[Security Alerts]
        end
    end
    
    MTLS --> READONLY
    JWT --> NONROOT
    NETWORK --> CAPS
    READONLY --> SECCOMP
    NONROOT --> LIMITS
    CAPS --> VOLUMES
    SECCOMP --> TMPFS
    LIMITS --> MONITOR
    VOLUMES --> TESTS
    TMPFS --> ALERTS
    
    style MTLS fill:#ffcdd2
    style JWT fill:#f8bbd9
    style READONLY fill:#e1bee7
    style NONROOT fill:#c5cae9
    style CAPS fill:#bbdefb
    style SECCOMP fill:#b3e5fc
    style LIMITS fill:#b2dfdb
    style MONITOR fill:#c8e6c9
```

### Container Security Hardening

**🛡️ Multi-Layer Container Protection:**

1. **Read-Only Root Filesystems**
   - All containers run with read-only root filesystems
   - Prevents runtime file system modifications
   - Writable volumes only for logs and temporary files

2. **Non-Root User Execution**
   - MCP Server: UID 1000 (mcpuser)
   - Kestra: UID 1001 (non-root)
   - Eliminates privilege escalation risks

3. **Capability Dropping**
   - All dangerous capabilities dropped (`CAP_DROP: ALL`)
   - Only essential capabilities added (`NET_BIND_SERVICE`)
   - Minimal attack surface

4. **Seccomp Security Profiles**
   - Custom seccomp profiles restrict system calls
   - Only essential syscalls allowed (54 categories)
   - Blocks dangerous operations like `ptrace`, `mount`

5. **Resource Limits**
   - Memory limits: 1GB (MCP), 2GB (Kestra)
   - CPU limits: 0.5 cores (MCP), 1.0 cores (Kestra)
   - Prevents resource exhaustion attacks

6. **Security Options**
   - `no-new-privileges:true` prevents privilege escalation
   - Secure tmpfs mounts with `noexec,nosuid`
   - No privileged mode execution

### mTLS Implementation

**🔐 Mutual TLS Authentication:**

```mermaid
sequenceDiagram
    participant Client
    participant Server as MCP Server
    participant CA as Certificate Authority
    
    Note over Client,CA: Certificate Setup
    CA->>Server: Server Certificate
    CA->>Client: Client Certificate
    
    Note over Client,Server: mTLS Handshake
    Client->>Server: Client Hello + Client Cert
    Server->>Client: Server Hello + Server Cert
    Server->>CA: Verify Client Cert
    Client->>CA: Verify Server Cert
    CA->>Server: Client Valid
    CA->>Client: Server Valid
    
    Note over Client,Server: Secure Communication
    Client->>Server: Encrypted API Requests
    Server->>Client: Encrypted API Responses
```

**Features:**
- **PKI Infrastructure**: Complete CA, server, and client certificates
- **Mutual Authentication**: Both client and server verify certificates
- **TLS 1.2+ Only**: Modern TLS versions with secure cipher suites
- **Certificate Validation**: Automated certificate chain validation
- **Configurable**: Enable/disable via `MTLS_ENABLED` environment variable

**Setup mTLS:**
```bash
# Generate certificates
./scripts/setup-mtls.sh

# Deploy with mTLS
MTLS_ENABLED=true ./scripts/deploy-secure.sh

# Test mTLS connection
openssl s_client -connect localhost:50051 \
  -cert certs/client-cert.pem \
  -key certs/client-key.pem \
  -CAfile certs/ca-cert.pem
```

### Security Monitoring

**📊 Real-Time Security Monitoring:**

```bash
# Run security monitoring
./monitoring/resource-monitor.sh

# Continuous monitoring
watch -n 30 ./monitoring/resource-monitor.sh
```

**Monitoring Features:**
- **Container Resource Usage**: Memory, CPU, network I/O
- **Security Status Validation**: User privileges, filesystem permissions
- **Capability Verification**: Dropped capabilities, security options
- **Network Connectivity**: HTTP and mTLS endpoint health
- **Alert System**: Automated alerts for security violations
- **Log Analysis**: Security event logging and analysis

### Security Testing

**🧪 Comprehensive Security Test Suite:**

```bash
# Run security tests
pytest tests/test_security.py -v

# Run with coverage
pytest tests/test_security.py --cov=server --cov-report=html
```

**Test Coverage:**
- ✅ **Container Security**: Non-root users, read-only filesystems, capabilities
- ✅ **mTLS Implementation**: Certificate validation, mutual authentication
- ✅ **Network Security**: Port accessibility, connection security
- ✅ **Resource Limits**: Memory and CPU constraint validation
- ✅ **Security Monitoring**: Monitoring script functionality
- ✅ **Access Controls**: Permission validation, privilege checks

### Deployment Security

**🚀 Secure Deployment Automation:**

```bash
# Automated secure deployment
./scripts/deploy-secure.sh

# Deployment with validation
./scripts/deploy-secure.sh validate

# Security-only testing
./scripts/deploy-secure.sh test
```

**Deployment Features:**
- **Environment Validation**: Docker, OpenSSL, dependencies
- **Certificate Management**: Automated PKI setup and validation
- **Security Configuration**: Hardened container deployment
- **Health Checks**: Service and security validation
- **Automated Testing**: Security test execution
- **Deployment Summary**: Complete security status report

### Security Configuration

**Environment Variables:**
```bash
# mTLS Configuration
export MTLS_ENABLED=true              # Enable mTLS
export MTLS_PORT=50051                # mTLS port
export MTLS_CERT_DIR=./certs          # Certificate directory

# JWT Security
export JWT_SECRET_KEY=$(openssl rand -hex 32)  # Secure secret
export JWT_ENABLED=true               # Enable authentication
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30     # Token expiration

# Container Security
export KUZU_READ_ONLY=false           # Read-only mode
```

### Security Best Practices

**🔒 Production Security Checklist:**

- ✅ **Use secure deployment script**: `./scripts/deploy-secure.sh`
- ✅ **Enable mTLS**: Set `MTLS_ENABLED=true`
- ✅ **Generate secure JWT secret**: Use `openssl rand -hex 32`
- ✅ **Monitor resources**: Run `./monitoring/resource-monitor.sh`
- ✅ **Run security tests**: Execute `pytest tests/test_security.py`
- ✅ **Validate certificates**: Check certificate expiration dates
- ✅ **Review logs**: Monitor for security events and alerts
- ✅ **Update regularly**: Keep containers and dependencies updated

### Security Compliance

**Standards Compliance:**
- **OWASP Container Security**: Follows OWASP container security guidelines
- **CIS Docker Benchmark**: Implements CIS Docker security recommendations
- **NIST Cybersecurity Framework**: Aligns with NIST security controls
- **Zero Trust Architecture**: Implements zero trust security principles

**Security Certifications:**
- Container hardening exceeds industry standards
- mTLS implementation follows RFC 8446 (TLS 1.3)
- PKI infrastructure follows X.509 standards
- Security monitoring implements SIEM best practices

> **📖 For complete security documentation, implementation details, and best practices, see [SECURITY.md](SECURITY.md)**

## 📚 API Documentation

### Authentication

The MCP Server supports JWT-based authentication for secure API access:

```bash
# Get access token
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# Use token in requests
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"event_type": "file_open", ...}'
```

**Default Test Credentials:**
- Username: `testuser`, Password: `testpassword`
- Username: `admin`, Password: `adminpassword`

### Core Endpoints

#### Authentication
- **POST `/auth/token`**: Generate JWT access token

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
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword" | jq -r .access_token)

# Ingest a telemetry event
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Authorization: Bearer $TOKEN" \
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
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/telemetry/query?event_type=file_open&user_id=user-123"

# Semantic search
curl -X POST http://localhost:8080/tools/topk \
  -H "Authorization: Bearer $TOKEN" \
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

### Docker Architecture

```mermaid
graph TB
    subgraph "Host System"
        DOCKER[Docker Engine]
        COMPOSE[Docker Compose]
    end
    
    subgraph "Container Network: memory-net"
        subgraph "MCP Container"
            MCPAPP[FastAPI App<br/>Port 8080]
            PYTHON[Python 3.11+]
        end
        
        subgraph "Kestra Container"
            KESTAPP[Kestra App<br/>Port 8081]
            JAVA[Java Runtime]
        end
    end
    
    subgraph "Named Volumes"
        KUZUVOL[kuzu-data<br/>Database Files]
        KESTRAVOL[kestra-data<br/>Workflow State]
    end
    
    subgraph "Host Ports"
        PORT8080[localhost:8080]
        PORT8081[localhost:8081]
    end
    
    COMPOSE --> DOCKER
    DOCKER --> MCPAPP
    DOCKER --> KESTAPP
    
    MCPAPP --> KUZUVOL
    KESTAPP --> KESTRAVOL
    
    PORT8080 --> MCPAPP
    PORT8081 --> KESTAPP
    
    style MCPAPP fill:#e3f2fd
    style KESTAPP fill:#e8f5e8
    style KUZUVOL fill:#fff3e0
    style KESTRAVOL fill:#fff3e0
```

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

### Volume Management Workflow

```mermaid
graph TD
    A[Start Backup Process] --> B{Check Volume Exists}
    B -->|Yes| C[Create Backup Container]
    B -->|No| D[Error: Volume Not Found]
    
    C --> E[Mount Volume as Read-Only]
    E --> F[Create Compressed Archive]
    F --> G[Store in ./backups/]
    G --> H[Cleanup Temp Container]
    H --> I[Backup Complete]
    
    J[Start Restore Process] --> K{Backup File Exists}
    K -->|Yes| L[Stop Target Services]
    K -->|No| M[Error: Backup Not Found]
    
    L --> N[Create Restore Container]
    N --> O[Mount Target Volume]
    O --> P[Extract Archive to Volume]
    P --> Q[Cleanup Temp Container]
    Q --> R[Restart Services]
    R --> S[Restore Complete]
    
    style A fill:#e8f5e8
    style I fill:#c8e6c9
    style J fill:#e8f5e8
    style S fill:#c8e6c9
    style D fill:#ffcdd2
    style M fill:#ffcdd2
```

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
| **Database Configuration** | | |
| `KUZU_DB_PATH` | `./data` | Path to Kuzu database files |
| `KUZU_READ_ONLY` | `false` | Enable read-only mode |
| **JWT Authentication** | | |
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT token signing key |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration time in minutes |
| `JWT_ENABLED` | `true` | Enable/disable JWT authentication |
| **mTLS Security** | | |
| `MTLS_ENABLED` | `false` | Enable mutual TLS authentication |
| `MTLS_PORT` | `50051` | Port for mTLS connections |
| `MTLS_CERT_DIR` | `./certs` | Certificate directory path |
| **CI/CD Integration** | | |
| `GITHUB_TOKEN` | - | GitHub token for Kestra workflows |

### Security Configuration

**Production Security Setup:**
```bash
# Generate secure JWT secret
export JWT_SECRET_KEY=$(openssl rand -hex 32)

# Enable security features
export JWT_ENABLED=true
export MTLS_ENABLED=true
export KUZU_READ_ONLY=false

# Configure mTLS
export MTLS_PORT=50051
export MTLS_CERT_DIR=./certs

# Set token expiration
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Development Configuration:**
```bash
# Disable authentication for development
export JWT_ENABLED=false
export MTLS_ENABLED=false

# Use default test credentials
# Username: testuser, Password: testpassword
```

### Container Security Configuration

The following security hardening is automatically applied:

**Container Hardening:**
- Read-only root filesystems
- Non-root user execution (UID 1000/1001)
- Dropped capabilities (`CAP_DROP: ALL`)
- Seccomp security profiles
- Resource limits (1GB/2GB memory, 0.5/1.0 CPU cores)
- No privileged mode execution

**Network Security:**
- Isolated bridge network (`memory-net`)
- Port exposure only for required services
- mTLS encryption for secure communications

**Volume Security:**
- Named volumes with proper isolation
- Secure tmpfs mounts (`noexec,nosuid`)
- Writable volumes only for logs and temporary files

### Deployment Configurations

**Secure Deployment (Recommended):**
```bash
# Full security hardening
./scripts/deploy-secure.sh

# With mTLS enabled
MTLS_ENABLED=true ./scripts/deploy-secure.sh
```

**Standard Deployment:**
```bash
cd docker
docker compose up -d
```

**Development Deployment:**
```bash
# Create development override
cat > docker/docker-compose.override.yml << EOF
services:
  mcp-server:
    volumes:
      - ../server:/app/server:ro
    command: ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
    environment:
      - JWT_ENABLED=false
EOF

# Start with hot reloading
cd docker && docker compose up -d
```

## 🔧 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check port usage
   lsof -i :8080
   lsof -i :50051  # mTLS port
   
   # Change ports in docker-compose.yml
   ports:
     - "8090:8080"
     - "50052:50051"
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

5. **mTLS Certificate Issues**:
   ```bash
   # Regenerate certificates
   ./scripts/setup-mtls.sh
   
   # Verify certificate chain
   openssl verify -CAfile certs/ca-cert.pem certs/server-cert.pem
   openssl verify -CAfile certs/ca-cert.pem certs/client-cert.pem
   
   # Check certificate permissions
   ls -la certs/
   ```

6. **Container Security Issues**:
   ```bash
   # Check container security status
   ./monitoring/resource-monitor.sh
   
   # Verify non-root user
   docker exec docker-mcp-server-1 id
   
   # Check read-only filesystem
   docker exec docker-mcp-server-1 touch /test-file  # Should fail
   ```

7. **Authentication Problems**:
   ```bash
   # Test JWT token generation
   curl -X POST http://localhost:8080/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=testpassword"
   
   # Disable authentication for debugging
   export JWT_ENABLED=false
   docker compose up -d
   ```

### Security Troubleshooting

**mTLS Connection Issues:**
```bash
# Test mTLS connectivity
openssl s_client -connect localhost:50051 \
  -cert certs/client-cert.pem \
  -key certs/client-key.pem \
  -CAfile certs/ca-cert.pem

# Check mTLS configuration
docker compose exec mcp-server env | grep MTLS

# Verify certificate expiration
openssl x509 -in certs/server-cert.pem -text -noout | grep "Not After"
```

**Container Security Validation:**
```bash
# Run security tests
pytest tests/test_security.py -v

# Check security configuration
docker inspect docker-mcp-server-1 | jq '.HostConfig.SecurityOpt'
docker inspect docker-mcp-server-1 | jq '.HostConfig.ReadonlyRootfs'

# Verify capabilities
docker exec docker-mcp-server-1 cat /proc/self/status | grep Cap
```

**Resource Monitoring Issues:**
```bash
# Check monitoring script permissions
ls -la monitoring/resource-monitor.sh

# Make script executable
chmod +x monitoring/resource-monitor.sh

# Run monitoring with debug
bash -x monitoring/resource-monitor.sh
```

### Debug Commands

```bash
# Container logs
docker compose logs mcp-server -f
docker compose logs kestra -f

# Container inspection
docker compose exec mcp-server env
docker compose exec mcp-server ps aux

# Security inspection
docker compose exec mcp-server id
docker compose exec mcp-server cat /proc/self/status | grep Cap

# Volume debugging
docker volume inspect docker_kuzu-data
./backup-volumes.sh info

# Network debugging
docker network inspect docker_memory-net

# Certificate debugging
openssl x509 -in certs/ca-cert.pem -text -noout
openssl x509 -in certs/server-cert.pem -text -noout
```

### Health Monitoring

```bash
# Service health
curl -f http://localhost:8080/docs || echo "MCP Server down"
curl -f http://localhost:8081/ || echo "Kestra down"

# mTLS health (if enabled)
timeout 5 openssl s_client -connect localhost:50051 -verify_return_error || echo "mTLS down"

# Database connectivity
curl -s http://localhost:8080/telemetry/list | jq length

# Volume usage
docker system df -v

# Security monitoring
./monitoring/resource-monitor.sh

# Container resource usage
docker stats --no-stream
```

### Performance Optimization

```bash
# Monitor container performance
docker stats docker-mcp-server-1 docker-kestra-1

# Check volume performance
time docker compose exec mcp-server ls -la /database

# Optimize Docker settings (macOS)
# Increase Docker Desktop memory to 4GB+
# Enable VirtioFS for better volume performance

# Monitor security overhead
./monitoring/resource-monitor.sh | grep -E "(CPU|Memory)"
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
- **[Security Documentation](SECURITY.md)**: Complete security hardening guide and best practices
- **[Security Testing](tests/test_security.py)**: Comprehensive security test suite
- **[Security Monitoring](monitoring/resource-monitor.sh)**: Real-time security monitoring
- **[mTLS Setup](scripts/setup-mtls.sh)**: Certificate generation and mTLS configuration
- **[Secure Deployment](scripts/deploy-secure.sh)**: Automated secure deployment
- **[Product Requirements](PRD%20-%20GraphMemory-IDE%20-%20Combined.md)**: Original PRD
- **[Project Planning](.context/README.md)**: Aegis framework planning and tasks

## 📊 Project Status

- ✅ **MCP Server**: Production-ready FastAPI server
- ✅ **Docker Deployment**: Optimized containerized deployment
- ✅ **Volume Management**: Research-driven persistent storage
- ✅ **Backup System**: Automated backup and restore
- ✅ **Testing**: Comprehensive test suite
- ✅ **Documentation**: Complete documentation coverage
- ✅ **Security Hardening**: Enterprise-grade container security
- ✅ **mTLS Implementation**: Mutual TLS authentication with PKI
- ✅ **Security Monitoring**: Real-time security monitoring and alerting
- ✅ **Security Testing**: Comprehensive security test suite
- ✅ **Secure Deployment**: Automated secure deployment scripts
- 🔄 **CI/CD Integration**: Kestra workflows (in progress)
- 🔄 **IDE Plugins**: Plugin development (planned)

### Security Implementation Status

**✅ Completed Security Features:**
- **Container Hardening**: Read-only filesystems, non-root users, capability dropping
- **Seccomp Profiles**: Custom security profiles restricting system calls
- **Resource Limits**: Memory and CPU constraints with monitoring
- **mTLS Authentication**: Complete PKI infrastructure with mutual authentication
- **Security Monitoring**: Real-time monitoring with automated alerts
- **Security Testing**: Comprehensive test suite covering all security aspects
- **Deployment Security**: Automated secure deployment with validation
- **Network Security**: Isolated networks with secure communication

**🔒 Security Compliance:**
- OWASP Container Security Guidelines
- CIS Docker Benchmark Recommendations
- NIST Cybersecurity Framework Alignment
- Zero Trust Architecture Principles

> **📖 For complete security documentation, implementation details, and best practices, see [SECURITY.md](SECURITY.md)**

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

## 🔐 Authentication

GraphMemory-IDE uses JWT (JSON Web Tokens) for secure API authentication:

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant MCP as MCP Server
    participant JWT as JWT Service
    participant DB as Kuzu GraphDB
    
    Client->>MCP: POST /auth/token<br/>(username, password)
    MCP->>JWT: Validate credentials
    JWT->>MCP: Generate JWT token
    MCP->>Client: Return access_token
    
    Note over Client: Store token for API calls
    
    Client->>MCP: API Request<br/>Authorization: Bearer <token>
    MCP->>JWT: Validate token
    JWT->>MCP: Token valid + user context
    MCP->>DB: Execute operation
    DB->>MCP: Return data
    MCP->>Client: API Response
    
    Note over Client,DB: Optional: JWT_ENABLED=false<br/>bypasses authentication
```

### Features & Usage

- **Token-based Authentication**: Secure, stateless authentication
- **Configurable Expiration**: Default 30-minute token lifetime
- **Development Mode**: Optional authentication bypass for development
- **OAuth2 Compatible**: Follows OAuth2 password flow standards

```bash
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword" | jq -r .access_token)

# Use token in API calls
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "file_open", ...}'
```

**Default Test Credentials:**
- Username: `testuser`, Password: `testpassword`
- Username: `admin`, Password: `adminpassword`