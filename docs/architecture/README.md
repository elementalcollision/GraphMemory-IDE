# MCP Server Documentation

## Overview

The MCP (Model Context Protocol) Server is a FastAPI-based service that provides AI memory capabilities for IDEs. It uses Kuzu GraphDB for persistent storage and offers telemetry ingestion, querying, vector-based semantic search, and JWT-based authentication.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IDE Plugin   │───▶│   MCP Server    │───▶│   Kuzu GraphDB  │
│                 │    │   (FastAPI)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Features

- **JWT Authentication**: Secure token-based authentication for API access
- **Telemetry Ingestion**: Capture IDE events and store them in graph database
- **Event Querying**: Filter and retrieve telemetry events by various criteria
- **Vector Search**: Semantic search using sentence transformers and HNSW indexing
- **Read-Only Mode**: Production safety mode for maintenance windows
- **Docker Integration**: Containerized deployment with persistent volumes

## API Endpoints

### Authentication

#### POST `/auth/token`
Generate a JWT access token for authentication.

**Request Body (Form Data):**
```
username=testuser&password=testpassword
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Default Test Credentials:**
- Username: `testuser`, Password: `testpassword`
- Username: `admin`, Password: `adminpassword`

**Usage:**
```bash
# Get token
curl -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"

# Use token in subsequent requests
curl -X POST http://localhost:8080/telemetry/ingest \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "file_open", ...}'
```

### Health & Documentation

- **GET `/docs`**: Interactive API documentation (Swagger UI)
- **GET `/openapi.json`**: OpenAPI specification

### Telemetry Management

#### POST `/telemetry/ingest`
Ingest a telemetry event from an IDE plugin.

**Authentication:** Required (JWT Bearer token)

**Request Body:**
```json
{
  "event_type": "file_open",
  "timestamp": "2024-05-28T08:30:00Z",
  "user_id": "user-123",
  "session_id": "session-456",
  "data": {
    "file_path": "/path/to/file.py",
    "language": "python"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Event ingested"
}
```

**Event Types:**
- `file_open`: File opened in IDE
- `file_save`: File saved
- `symbol_index`: Code symbol indexed
- `test_run`: Test execution
- `user_chat`: AI chat interaction

#### GET `/telemetry/list`
List all telemetry events stored in the database.

**Authentication:** Optional (configurable via JWT_ENABLED)

**Response:**
```json
[
  {
    "event_type": "file_open",
    "timestamp": "2024-05-28T08:30:00Z",
    "user_id": "user-123",
    "session_id": "session-456",
    "data": {
      "file_path": "/path/to/file.py",
      "language": "python"
    }
  }
]
```

#### GET `/telemetry/query`
Query telemetry events with filters.

**Authentication:** Optional (configurable via JWT_ENABLED)

**Query Parameters:**
- `event_type` (optional): Filter by event type
- `user_id` (optional): Filter by user ID
- `session_id` (optional): Filter by session ID

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8080/telemetry/query?event_type=file_open&user_id=user-123"
```

### Vector Search

#### POST `/tools/topk`
Retrieve top-K relevant nodes/snippets using vector search.

**Authentication:** Required (JWT Bearer token)

**Request Body:**
```json
{
  "query_text": "find relevant code for function X",
  "k": 5,
  "table": "Node",
  "embedding_field": "embedding",
  "index_name": "node_embedding_idx",
  "filters": {
    "user_id": "user-123"
  }
}
```

**Response:**
```json
[
  {
    "node": {
      "id": "n1",
      "snippet": "def function_x():",
      "file_path": "/src/module.py"
    },
    "distance": 0.01
  },
  {
    "node": {
      "id": "n2", 
      "snippet": "class FunctionX:",
      "file_path": "/src/classes.py"
    },
    "distance": 0.02
  }
]
```

**Features:**
- Automatic vector index creation
- Filtered search with projected graphs
- Semantic similarity using sentence transformers
- HNSW indexing for performance

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KUZU_DB_PATH` | `./data` | Path to Kuzu database files |
| `KUZU_READ_ONLY` | `false` | Enable read-only mode |
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT token signing key |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration time in minutes |
| `JWT_ENABLED` | `true` | Enable/disable JWT authentication |

### JWT Authentication

The server supports JWT-based authentication with the following features:

- **Token-based Security**: Stateless authentication using JWT tokens
- **Configurable Expiration**: Default 30-minute token lifetime
- **Development Mode**: Optional authentication bypass via `JWT_ENABLED=false`
- **OAuth2 Compatible**: Follows OAuth2 password flow standards

**Production Setup:**
```bash
# Generate secure secret key
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export JWT_ENABLED="true"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"
```

**Development Setup:**
```bash
# Disable authentication for development
export JWT_ENABLED="false"
```

### Read-Only Mode

When `KUZU_READ_ONLY=true`:
- All write endpoints return HTTP 403 Forbidden
- Read endpoints continue to function normally
- Useful for maintenance, backups, or production safety

```bash
# Enable read-only mode
export KUZU_READ_ONLY=true
docker compose up -d
```

## Database Schema

### TelemetryEvent Node
```cypher
CREATE (e:TelemetryEvent {
  event_type: STRING,
  timestamp: STRING,
  user_id: STRING,
  session_id: STRING,
  data: STRING
})
```

### Vector Indexes
The server automatically creates vector indexes for semantic search:
```cypher
CALL CREATE_VECTOR_INDEX('Node', 'node_embedding_idx', 'embedding');
```

## Development

### Local Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Database:**
   ```bash
   # Ensure Kuzu database directory exists
   mkdir -p data
   ```

3. **Run Server:**
   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. **Access Documentation:**
   - Swagger UI: http://localhost:8080/docs
   - ReDoc: http://localhost:8080/redoc

### Testing

Run the comprehensive test suite:

```bash
# From project root
PYTHONPATH=. pytest server/ --maxfail=3 --disable-warnings -v
```

**Test Coverage:**
- Telemetry ingestion (success, validation, errors)
- Event listing and querying
- Vector search functionality
- Read-only mode enforcement
- Database error handling

### Docker Development

```bash
# Build and run with Docker Compose
cd docker
docker compose up -d

# View logs
docker compose logs mcp-server -f

# Execute commands in container
docker compose exec mcp-server bash
```

## Production Deployment

### Docker Compose (Recommended)

```yaml
services:
  mcp-server:
    build:
      context: ..
      dockerfile: docker/mcp-server/Dockerfile
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      - KUZU_DB_PATH=/database
      - KUZU_READ_ONLY=false
    volumes:
      - kuzu-data:/database
    networks:
      - memory-net
```

### Health Monitoring

Monitor the service health:

```bash
# Check service status
curl -f http://localhost:8080/docs || echo "Service down"

# Check database connectivity
curl -s http://localhost:8080/telemetry/list | jq length
```

### Performance Tuning

1. **Database Optimization:**
   - Use named volumes for better I/O performance
   - Regular database maintenance and indexing
   - Monitor disk usage and implement rotation

2. **Memory Management:**
   - Configure appropriate container memory limits
   - Monitor embedding model memory usage
   - Implement connection pooling if needed

3. **Scaling:**
   - Use load balancer for multiple instances
   - Implement database read replicas
   - Consider caching for frequent queries

## Security

### Best Practices

1. **Network Security:**
   - Use internal networks for database communication
   - Implement proper firewall rules
   - Enable HTTPS in production

2. **Data Protection:**
   - Regular backups using volume backup scripts
   - Encrypt sensitive data in transit and at rest
   - Implement proper access controls

3. **Container Security:**
   - Use non-root users in containers
   - Regular security updates
   - Scan images for vulnerabilities

### Authentication

Currently, the server operates without authentication. For production:

1. **API Keys:**
   ```python
   from fastapi import Header, HTTPException
   
   async def verify_api_key(x_api_key: str = Header()):
       if x_api_key != "your-secret-key":
           raise HTTPException(status_code=401)
   ```

2. **JWT Tokens:**
   ```python
   from fastapi import Depends
   from fastapi.security import HTTPBearer
   
   security = HTTPBearer()
   
   async def verify_token(token: str = Depends(security)):
       # Verify JWT token
       pass
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors:**
   ```bash
   # Check database path permissions
   ls -la /database
   
   # Verify Kuzu installation
   python -c "import kuzu; print('Kuzu OK')"
   ```

2. **Vector Search Failures:**
   ```bash
   # Check VECTOR extension
   # In Kuzu console:
   INSTALL VECTOR;
   LOAD VECTOR;
   ```

3. **Memory Issues:**
   ```bash
   # Monitor container memory
   docker stats docker-mcp-server-1
   
   # Check embedding model loading
   docker compose logs mcp-server | grep -i "sentence"
   ```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Monitoring

```bash
# API response times
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8080/telemetry/list

# Database query performance
# Monitor Kuzu query execution times
```

## API Client Examples

### Python Client

```python
import requests
import json

class MCPClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def ingest_event(self, event_data):
        response = requests.post(
            f"{self.base_url}/telemetry/ingest",
            json=event_data
        )
        return response.json()
    
    def query_events(self, **filters):
        response = requests.get(
            f"{self.base_url}/telemetry/query",
            params=filters
        )
        return response.json()
    
    def search_similar(self, query_text, k=5):
        response = requests.post(
            f"{self.base_url}/tools/topk",
            json={
                "query_text": query_text,
                "k": k,
                "table": "Node",
                "embedding_field": "embedding",
                "index_name": "node_embedding_idx"
            }
        )
        return response.json()

# Usage
client = MCPClient()
result = client.search_similar("authentication function")
```

### JavaScript Client

```javascript
class MCPClient {
    constructor(baseUrl = 'http://localhost:8080') {
        this.baseUrl = baseUrl;
    }
    
    async ingestEvent(eventData) {
        const response = await fetch(`${this.baseUrl}/telemetry/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(eventData)
        });
        return response.json();
    }
    
    async queryEvents(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseUrl}/telemetry/query?${params}`);
        return response.json();
    }
    
    async searchSimilar(queryText, k = 5) {
        const response = await fetch(`${this.baseUrl}/tools/topk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query_text: queryText,
                k: k,
                table: 'Node',
                embedding_field: 'embedding',
                index_name: 'node_embedding_idx'
            })
        });
        return response.json();
    }
}

// Usage
const client = new MCPClient();
const results = await client.searchSimilar('database connection');
```

## Contributing

1. **Code Style:**
   - Follow PEP 8 for Python code
   - Use type hints for all functions
   - Add docstrings for all public methods

2. **Testing:**
   - Write tests for all new endpoints
   - Maintain test coverage above 90%
   - Test both success and error cases

3. **Documentation:**
   - Update API documentation for changes
   - Include examples for new features
   - Update this README for significant changes

## License

See the main project LICENSE file for licensing information. 