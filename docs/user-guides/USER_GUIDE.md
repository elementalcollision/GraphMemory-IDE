# GraphMemory-IDE User Guide

## 🎯 Welcome to GraphMemory-IDE

GraphMemory-IDE is an AI-powered memory system that captures, stores, and retrieves your development context to enhance your coding experience. This guide will help you get started and make the most of GraphMemory-IDE's capabilities.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
- [Common Workflows](#common-workflows)
- [IDE Integration](#ide-integration)
- [API Usage](#api-usage)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## 🚀 Getting Started

### Quick Installation

The fastest way to get started with GraphMemory-IDE:

```bash
# Install and start GraphMemory-IDE
npx @graphmemory/cli install

# Verify installation
npx @graphmemory/cli health
```

### System Requirements

- **Operating System**: macOS, Linux, or Windows
- **Docker**: Docker Desktop or OrbStack
- **Node.js**: Version 18 or higher (for CLI)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB free space for data and containers

### First-Time Setup

1. **Install GraphMemory-IDE**:
   ```bash
   npx @graphmemory/cli install
   ```

2. **Verify Services**:
   ```bash
   npx @graphmemory/cli status
   ```

3. **Access Web Interface**:
   - **API Documentation**: http://localhost:8080/docs
   - **Kestra CI/CD**: http://localhost:8081

4. **Test API Connection**:
   ```bash
   curl http://localhost:8080/docs
   ```

## 🧠 Core Concepts

### What is GraphMemory-IDE?

GraphMemory-IDE captures and stores your development context in a graph database, enabling:

- **Contextual Code Search**: Find code based on meaning, not just keywords
- **Development History**: Track your coding patterns and decisions
- **AI-Enhanced Retrieval**: Get relevant context for your current work
- **Cross-Project Insights**: Connect related concepts across projects

### Key Components

#### 1. Telemetry Collection
Captures development events like:
- File opens, edits, and saves
- Function calls and definitions
- Error occurrences and resolutions
- Testing and debugging sessions

#### 2. Graph Database (Kuzu)
Stores relationships between:
- Code files and functions
- Developers and their work
- Projects and dependencies
- Concepts and implementations

#### 3. Vector Search
Enables semantic search using:
- Natural language queries
- Code similarity matching
- Contextual recommendations
- Intelligent code completion

#### 4. REST API
Provides programmatic access for:
- IDE integrations
- Custom tooling
- Automation scripts
- Third-party applications

## 🔄 Common Workflows

### Workflow 1: Daily Development

#### Morning Startup
```bash
# Check system health
npx @graphmemory/cli health

# View recent activity
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8080/telemetry/recent?limit=10"
```

#### During Development
1. **IDE automatically captures telemetry** as you work
2. **Search for relevant code** using natural language
3. **Get contextual suggestions** based on current work
4. **Track progress** through captured events

#### End of Day
```bash
# Create backup of your work
npx @graphmemory/cli backup --reason "end-of-day-$(date +%Y%m%d)"

# View daily summary
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8080/telemetry/summary?date=$(date +%Y-%m-%d)"
```

### Workflow 2: Code Search and Discovery

#### Semantic Code Search
```bash
# Search for authentication-related code
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "user authentication and JWT token validation",
    "k": 5
  }'
```

#### Finding Similar Code Patterns
```bash
# Find code similar to a specific function
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "async function that handles database connections",
    "k": 10,
    "filters": {
      "file_type": "javascript",
      "project": "current"
    }
  }'
```

### Workflow 3: Project Onboarding

#### Understanding a New Codebase
1. **Ingest existing code**:
   ```bash
   # Scan project files
   find . -name "*.py" -o -name "*.js" -o -name "*.ts" | \
   while read file; do
     curl -X POST "http://localhost:8080/telemetry/ingest" \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer YOUR_TOKEN" \
       -d "{
         \"event_type\": \"file_scan\",
         \"file_path\": \"$file\",
         \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
         \"metadata\": {
           \"project\": \"$(basename $(pwd))\",
           \"language\": \"$(echo $file | sed 's/.*\.//')\",
           \"size\": $(wc -c < \"$file\")
         }
       }"
   done
   ```

2. **Explore architecture**:
   ```bash
   # Find main entry points
   curl -X POST "http://localhost:8080/tools/topk" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "query": "main function application entry point",
       "k": 5
     }'
   ```

3. **Understand data flow**:
   ```bash
   # Find database-related code
   curl -X POST "http://localhost:8080/tools/topk" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
       "query": "database models schemas tables",
       "k": 10
     }'
   ```

### Workflow 4: Debugging and Problem Solving

#### Finding Related Issues
```bash
# Search for error handling patterns
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "error handling exception try catch",
    "k": 8,
    "filters": {
      "event_type": "error_resolution"
    }
  }'
```

#### Tracking Bug Fixes
```bash
# Log bug fix event
curl -X POST "http://localhost:8080/telemetry/ingest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "event_type": "bug_fix",
    "file_path": "/src/auth.py",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "metadata": {
      "bug_id": "AUTH-123",
      "description": "Fixed JWT token expiration handling",
      "solution": "Added proper token refresh logic"
    }
  }'
```

## 🔌 IDE Integration

### VS Code Integration

#### Manual Setup
1. **Install REST Client extension**
2. **Create `.vscode/graphmemory.http`**:
   ```http
   ### GraphMemory-IDE Configuration
   @baseUrl = http://localhost:8080
   @token = YOUR_JWT_TOKEN
   
   ### Health Check
   GET {{baseUrl}}/docs
   
   ### Search Code
   POST {{baseUrl}}/tools/topk
   Content-Type: application/json
   Authorization: Bearer {{token}}
   
   {
     "query": "authentication middleware",
     "k": 5
   }
   
   ### Ingest Telemetry
   POST {{baseUrl}}/telemetry/ingest
   Content-Type: application/json
   Authorization: Bearer {{token}}
   
   {
     "event_type": "file_open",
     "file_path": "{{$dotenv %CURRENT_FILE}}",
     "timestamp": "{{$datetime iso8601}}",
     "metadata": {
       "editor": "vscode",
       "language": "{{$dotenv %CURRENT_LANGUAGE}}"
     }
   }
   ```

#### Automated Integration Script
Create `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "GraphMemory: Search Current Context",
      "type": "shell",
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://localhost:8080/tools/topk",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer ${env:GRAPHMEMORY_TOKEN}",
        "-d", "{\"query\": \"${input:searchQuery}\", \"k\": 5}"
      ],
      "group": "build",
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    },
    {
      "label": "GraphMemory: Log Current File",
      "type": "shell",
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://localhost:8080/telemetry/ingest",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer ${env:GRAPHMEMORY_TOKEN}",
        "-d", "{\"event_type\": \"file_open\", \"file_path\": \"${file}\", \"timestamp\": \"${env:CURRENT_TIMESTAMP}\", \"metadata\": {\"editor\": \"vscode\"}}"
      ]
    }
  ],
  "inputs": [
    {
      "id": "searchQuery",
      "description": "Enter search query",
      "default": "current function context",
      "type": "promptString"
    }
  ]
}
```

### IntelliJ IDEA Integration

#### HTTP Client Setup
Create `graphmemory-requests.http`:
```http
### GraphMemory-IDE Requests

### Search for code patterns
POST http://localhost:8080/tools/topk
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "query": "Spring Boot controller REST API",
  "k": 5,
  "filters": {
    "language": "java"
  }
}

### Log development event
POST http://localhost:8080/telemetry/ingest
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "event_type": "refactor",
  "file_path": "{{$projectRoot}}/src/main/java/Controller.java",
  "timestamp": "{{$timestamp}}",
  "metadata": {
    "ide": "intellij",
    "action": "extract_method"
  }
}
```

### Vim/Neovim Integration

#### Lua Configuration
```lua
-- ~/.config/nvim/lua/graphmemory.lua
local M = {}

M.config = {
  base_url = "http://localhost:8080",
  token = os.getenv("GRAPHMEMORY_TOKEN")
}

function M.search_code(query)
  local curl_cmd = string.format(
    'curl -s -X POST "%s/tools/topk" -H "Content-Type: application/json" -H "Authorization: Bearer %s" -d \'{"query": "%s", "k": 5}\'',
    M.config.base_url,
    M.config.token,
    query
  )
  
  local handle = io.popen(curl_cmd)
  local result = handle:read("*a")
  handle:close()
  
  print(result)
end

function M.log_file_open()
  local file_path = vim.fn.expand("%:p")
  local timestamp = os.date("!%Y-%m-%dT%H:%M:%SZ")
  
  local data = {
    event_type = "file_open",
    file_path = file_path,
    timestamp = timestamp,
    metadata = {
      editor = "neovim",
      language = vim.bo.filetype
    }
  }
  
  local json_data = vim.fn.json_encode(data)
  local curl_cmd = string.format(
    'curl -s -X POST "%s/telemetry/ingest" -H "Content-Type: application/json" -H "Authorization: Bearer %s" -d \'%s\'',
    M.config.base_url,
    M.config.token,
    json_data
  )
  
  os.execute(curl_cmd)
end

-- Auto-log file opens
vim.api.nvim_create_autocmd("BufReadPost", {
  callback = M.log_file_open
})

-- Search command
vim.api.nvim_create_user_command("GraphMemorySearch", function(opts)
  M.search_code(opts.args)
end, { nargs = 1 })

return M
```

## 🔧 API Usage

### Authentication

#### Getting a JWT Token
```bash
# Get authentication token
curl -X POST "http://localhost:8080/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

#### Using the Token
```bash
# Store token for reuse
export GRAPHMEMORY_TOKEN="your_jwt_token_here"

# Use token in requests
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/telemetry/events"
```

### Telemetry Ingestion

#### Basic Event Logging
```bash
# Log a file open event
curl -X POST "http://localhost:8080/telemetry/ingest" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "event_type": "file_open",
    "file_path": "/src/main.py",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "metadata": {
      "language": "python",
      "size": 1024,
      "project": "my-project"
    }
  }'
```

#### Batch Event Logging
```bash
# Log multiple events
curl -X POST "http://localhost:8080/telemetry/batch" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "events": [
      {
        "event_type": "file_open",
        "file_path": "/src/auth.py",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "metadata": {"language": "python"}
      },
      {
        "event_type": "function_call",
        "file_path": "/src/auth.py",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "metadata": {"function": "authenticate_user"}
      }
    ]
  }'
```

### Vector Search

#### Semantic Code Search
```bash
# Search for authentication-related code
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "query": "user authentication JWT token validation",
    "k": 10,
    "filters": {
      "language": "python",
      "project": "current"
    }
  }'
```

#### Advanced Search with Filters
```bash
# Search with multiple filters
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "query": "database connection pooling",
    "k": 5,
    "filters": {
      "event_type": "function_definition",
      "language": ["python", "javascript"],
      "date_range": {
        "start": "2025-01-01T00:00:00Z",
        "end": "2025-01-28T23:59:59Z"
      }
    },
    "include_metadata": true
  }'
```

### Data Retrieval

#### Query Recent Events
```bash
# Get recent telemetry events
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/telemetry/events?limit=20&offset=0"
```

#### Get Project Statistics
```bash
# Get project-level statistics
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/telemetry/stats?project=my-project&timeframe=week"
```

## ⚡ Performance Optimization

### Database Optimization

#### Regular Maintenance
```bash
# Create regular backups
npx @graphmemory/cli backup --reason "weekly-maintenance"

# Check database size and health
npx @graphmemory/cli status --verbose
```

#### Query Optimization
```bash
# Use specific filters to improve search performance
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "query": "error handling",
    "k": 5,
    "filters": {
      "language": "python",
      "project": "specific-project",
      "date_range": {
        "start": "2025-01-20T00:00:00Z",
        "end": "2025-01-28T23:59:59Z"
      }
    }
  }'
```

### Memory Management

#### Monitor Resource Usage
```bash
# Check container resource usage
docker stats

# Monitor GraphMemory-IDE specific resources
npx @graphmemory/cli status --verbose
```

#### Optimize Container Resources
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  mcp-server:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Network Optimization

#### Local Development
```bash
# Use local Docker network for better performance
docker network create graphmemory-local

# Configure services to use local network
# (Update docker-compose.yml accordingly)
```

#### Production Deployment
```bash
# Use production-optimized configuration
npx @graphmemory/cli upgrade --strategy blue-green --verify-signatures
```

### Search Performance

#### Optimize Query Patterns
```javascript
// Good: Specific, filtered queries
const searchQuery = {
  query: "JWT authentication middleware",
  k: 5,
  filters: {
    language: "javascript",
    project: "auth-service",
    event_type: "function_definition"
  }
};

// Avoid: Broad, unfiltered queries
const broadQuery = {
  query: "code",
  k: 100  // Too many results
};
```

#### Batch Operations
```javascript
// Batch telemetry ingestion for better performance
const events = [];
for (let i = 0; i < fileList.length; i++) {
  events.push({
    event_type: "file_scan",
    file_path: fileList[i],
    timestamp: new Date().toISOString(),
    metadata: { batch_id: "scan-001" }
  });
}

// Send in batches of 50
const batchSize = 50;
for (let i = 0; i < events.length; i += batchSize) {
  const batch = events.slice(i, i + batchSize);
  await fetch('/telemetry/batch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ events: batch })
  });
}
```

## 🔍 Troubleshooting

### Common Issues

#### API Connection Problems
```bash
# Check if services are running
npx @graphmemory/cli health

# Verify network connectivity
curl -I http://localhost:8080/docs

# Check Docker containers
docker ps
```

#### Authentication Issues
```bash
# Verify JWT token
echo $GRAPHMEMORY_TOKEN

# Test authentication
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/telemetry/events?limit=1"

# Get new token if expired
curl -X POST "http://localhost:8080/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

#### Search Not Returning Results
```bash
# Check if data exists
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/telemetry/events?limit=5"

# Try broader search query
curl -X POST "http://localhost:8080/tools/topk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  -d '{
    "query": "function",
    "k": 10
  }'
```

#### Performance Issues
```bash
# Check system resources
npx @graphmemory/cli status --verbose

# Monitor container performance
docker stats

# Check database size
du -sh ./data/
```

### Debug Mode

#### Enable Verbose Logging
```bash
# Enable debug mode for CLI
DEBUG=graphmemory:* npx @graphmemory/cli status

# Check container logs
docker logs docker-mcp-server-1

# Monitor real-time logs
docker logs -f docker-mcp-server-1
```

#### API Debug Information
```bash
# Get detailed API information
curl -H "Authorization: Bearer $GRAPHMEMORY_TOKEN" \
  "http://localhost:8080/debug/info"

# Check API health with details
curl "http://localhost:8080/health?detailed=true"
```

## 🎯 Best Practices

### Data Collection

#### Meaningful Event Types
```javascript
// Good: Specific, actionable event types
const eventTypes = [
  'file_open',
  'file_save',
  'function_definition',
  'function_call',
  'error_occurrence',
  'bug_fix',
  'refactor',
  'test_run'
];

// Avoid: Generic or unclear event types
const badEventTypes = [
  'action',
  'event',
  'thing'
];
```

#### Rich Metadata
```javascript
// Good: Rich, structured metadata
const goodEvent = {
  event_type: "function_definition",
  file_path: "/src/auth/middleware.js",
  timestamp: "2025-01-28T12:41:19Z",
  metadata: {
    function_name: "authenticateUser",
    parameters: ["req", "res", "next"],
    return_type: "Promise<boolean>",
    language: "javascript",
    project: "auth-service",
    complexity: "medium",
    dependencies: ["jwt", "bcrypt"],
    test_coverage: 85
  }
};

// Avoid: Minimal or unstructured metadata
const badEvent = {
  event_type: "function_definition",
  file_path: "/src/file.js",
  timestamp: "2025-01-28T12:41:19Z",
  metadata: {
    info: "some function"
  }
};
```

### Search Optimization

#### Effective Query Patterns
```javascript
// Good: Specific, context-rich queries
const goodQueries = [
  "JWT authentication middleware Express.js",
  "database connection pooling PostgreSQL",
  "error handling async functions Node.js",
  "React component state management hooks"
];

// Avoid: Vague or overly broad queries
const badQueries = [
  "code",
  "function",
  "error",
  "data"
];
```

#### Smart Filtering
```javascript
// Use filters to narrow down results
const searchWithFilters = {
  query: "authentication",
  k: 5,
  filters: {
    language: "javascript",
    project: "current",
    event_type: ["function_definition", "function_call"],
    date_range: {
      start: "2025-01-20T00:00:00Z",
      end: "2025-01-28T23:59:59Z"
    }
  }
};
```

### Security

#### Token Management
```bash
# Store tokens securely
echo "export GRAPHMEMORY_TOKEN='your_token'" >> ~/.bashrc

# Use environment files for projects
echo "GRAPHMEMORY_TOKEN=your_token" > .env
echo ".env" >> .gitignore
```

#### Data Privacy
```javascript
// Sanitize sensitive data before logging
const sanitizeMetadata = (metadata) => {
  const sanitized = { ...metadata };
  
  // Remove sensitive fields
  delete sanitized.password;
  delete sanitized.api_key;
  delete sanitized.secret;
  
  // Mask email addresses
  if (sanitized.email) {
    sanitized.email = sanitized.email.replace(/(.{2}).*@/, '$1***@');
  }
  
  return sanitized;
};
```

### Maintenance

#### Regular Backups
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
npx @graphmemory/cli backup --reason "daily-backup-$DATE"

# Weekly cleanup of old backups
find ~/.graphmemory/backups -name "*.tar.gz" -mtime +30 -delete
```

#### Health Monitoring
```bash
# Health check script for monitoring
#!/bin/bash
HEALTH_STATUS=$(npx @graphmemory/cli health --json | jq -r '.status')

if [ "$HEALTH_STATUS" != "healthy" ]; then
  echo "GraphMemory-IDE health check failed: $HEALTH_STATUS"
  # Send alert or restart services
  npx @graphmemory/cli upgrade --force
fi
```

---

## 🎉 Conclusion

GraphMemory-IDE provides powerful capabilities for capturing and leveraging your development context. By following this guide and implementing the suggested workflows, you'll be able to:

- **Enhance Code Discovery**: Find relevant code faster using semantic search
- **Improve Development Efficiency**: Leverage captured context for better decision-making
- **Build Better Software**: Learn from past patterns and avoid repeated mistakes
- **Collaborate Effectively**: Share context and insights with your team

### Next Steps

1. **Start Small**: Begin with basic telemetry collection and search
2. **Integrate Gradually**: Add IDE integration and automation over time
3. **Optimize Continuously**: Monitor performance and adjust configurations
4. **Share Knowledge**: Contribute to the community with your experiences

### Getting Help

- **Documentation**: Refer to other guides in the `/docs` directory
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share best practices
- **Support**: Contact the development team for assistance

Happy coding with GraphMemory-IDE! 🚀 