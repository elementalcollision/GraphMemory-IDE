# GraphMemory-IDE Documentation Index

## 📚 Complete Documentation Guide

This document serves as a comprehensive index to all GraphMemory-IDE documentation, organized by topic and user type.

## 🚀 Getting Started

### For New Users
1. **[Main README](README.md)** - Start here for project overview and quick setup
2. **[Docker Quick Start](docker/README.md#quick-start)** - Get running in 5 minutes
3. **[API Documentation](server/README.md#api-endpoints)** - Understand the API

### For Developers
1. **[Development Setup](README.md#development)** - Local development environment
2. **[Server Documentation](server/README.md)** - MCP server development
3. **[Testing Guide](README.md#testing)** - Running and writing tests

### For DevOps/Production
1. **[Docker Deployment](docker/README.md)** - Production deployment guide
2. **[Volume Management](docker/VOLUME_MANAGEMENT.md)** - Backup and storage
3. **[Troubleshooting](README.md#troubleshooting)** - Common issues and solutions

## 📋 Documentation by Category

### 🏗️ Architecture & Design

| Document | Description | Audience |
|----------|-------------|----------|
| [Main README](README.md) | Project overview, architecture, quick start | All users |
| [Product Requirements](PRD%20-%20GraphMemory-IDE%20-%20Combined.md) | Original PRD with detailed requirements | Product, Engineering |
| [Volume Research Summary](docker/VOLUME_RESEARCH_SUMMARY.md) | Docker volume strategy research and decisions | DevOps, Engineering |

### 🛠️ Development

| Document | Description | Audience |
|----------|-------------|----------|
| [Server README](server/README.md) | Complete MCP server documentation | Backend developers |
| [API Examples](server/README.md#api-client-examples) | Python and JavaScript client examples | Frontend developers |
| [Testing Guide](README.md#testing) | Test suite and coverage information | QA, Developers |

### 🐳 Deployment & Operations

| Document | Description | Audience |
|----------|-------------|----------|
| [Docker README](docker/README.md) | Complete Docker deployment guide | DevOps, SRE |
| [Volume Management](docker/VOLUME_MANAGEMENT.md) | Backup, restore, and volume operations | DevOps, SRE |
| [Backup Script Guide](docker/backup-volumes.sh) | Automated backup system | Operations |

### 🔧 Configuration & Troubleshooting

| Document | Description | Audience |
|----------|-------------|----------|
| [Configuration Guide](README.md#configuration) | Environment variables and settings | All users |
| [Troubleshooting](README.md#troubleshooting) | Common issues and solutions | Support, Users |
| [Debug Commands](docker/README.md#troubleshooting) | Advanced debugging techniques | DevOps, Support |

### 📊 Project Management

| Document | Description | Audience |
|----------|-------------|----------|
| [Project Planning](.context/README.md) | Aegis framework and task management | Project managers |
| [AI Instructions](.context/AI_INSTRUCTIONS.md) | Framework for AI-assisted development | AI developers |

## 🎯 Documentation by User Journey

### 🆕 First-Time Setup

1. **Read Overview**: [Main README](README.md) - Understand what GraphMemory-IDE does
2. **Check Prerequisites**: [Quick Start](README.md#quick-start) - Ensure system requirements
3. **Start Services**: [Docker Quick Start](docker/README.md#quick-start) - Get running
4. **Test API**: [API Examples](README.md#example-usage) - Verify functionality
5. **Explore Features**: [API Documentation](server/README.md#api-endpoints) - Learn capabilities

### 🔧 Development Workflow

1. **Setup Environment**: [Local Development](README.md#development) - Configure dev environment
2. **Understand Architecture**: [Server Documentation](server/README.md#architecture) - Learn system design
3. **Run Tests**: [Testing Guide](README.md#testing) - Verify code quality
4. **Make Changes**: [Contributing Guide](README.md#contributing) - Development best practices
5. **Deploy Changes**: [Docker Development](docker/README.md#development) - Test in containers

### 🚀 Production Deployment

1. **Plan Deployment**: [Production Guide](docker/README.md#production-deployment) - Understand requirements
2. **Configure Environment**: [Configuration](README.md#configuration) - Set environment variables
3. **Setup Volumes**: [Volume Management](docker/VOLUME_MANAGEMENT.md) - Configure persistent storage
4. **Deploy Services**: [Docker Deployment](docker/README.md) - Start production stack
5. **Setup Monitoring**: [Health Monitoring](README.md#health-monitoring) - Monitor system health
6. **Configure Backups**: [Backup System](docker/VOLUME_MANAGEMENT.md#backup--restore) - Ensure data safety

### 🔍 Troubleshooting Journey

1. **Check Status**: [Health Monitoring](README.md#health-monitoring) - Verify service health
2. **Review Logs**: [Debug Commands](docker/README.md#debugging) - Examine system logs
3. **Common Issues**: [Troubleshooting](README.md#troubleshooting) - Known problems and solutions
4. **Advanced Debug**: [Docker Troubleshooting](docker/README.md#troubleshooting) - Deep debugging
5. **Get Support**: [Support](README.md#support) - Contact options

## 📖 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8080/docs (when running)
- **ReDoc**: http://localhost:8080/redoc (when running)
- **OpenAPI Spec**: http://localhost:8080/openapi.json

### Endpoint Categories

| Category | Endpoints | Documentation |
|----------|-----------|---------------|
| **Authentication** | `/auth/token` | [JWT Authentication](server/README.md#authentication) |
| **Telemetry** | `/telemetry/*` | [Telemetry Management](server/README.md#telemetry-management) |
| **Vector Search** | `/tools/topk` | [Vector Search](server/README.md#vector-search) |
| **Health** | `/docs`, `/openapi.json` | [Health & Documentation](server/README.md#health--documentation) |

### Client Libraries
- **Python Client**: [Python Examples](server/README.md#python-client)
- **JavaScript Client**: [JavaScript Examples](server/README.md#javascript-client)
- **Authentication Examples**: [JWT Usage](README.md#authentication)

## 🐳 Docker Documentation

### Core Files
- **[docker-compose.yml](docker/docker-compose.yml)** - Main service configuration
- **[Dockerfile](docker/mcp-server/Dockerfile)** - MCP server container build
- **[backup-volumes.sh](docker/backup-volumes.sh)** - Volume backup script

### Volume Strategy
- **[Volume Management](docker/VOLUME_MANAGEMENT.md)** - Complete volume guide
- **[Research Summary](docker/VOLUME_RESEARCH_SUMMARY.md)** - Why we chose our approach
- **[Backup Guide](docker/README.md#volume-management)** - Backup and restore procedures

## 🧪 Testing Documentation

### Test Categories
- **Unit Tests**: [Server Tests](server/test_main.py) - API endpoint testing
- **Integration Tests**: [Docker Testing](docker/README.md#testing-changes) - Container integration
- **Manual Tests**: [Manual Testing](README.md#manual-testing) - User acceptance testing

### Coverage Areas
- ✅ Telemetry ingestion and querying
- ✅ Vector search functionality
- ✅ JWT authentication and token validation
- ✅ Read-only mode enforcement
- ✅ Database error handling
- ✅ Docker volume persistence

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description | Documentation |
|----------|---------|-------------|---------------|
| `KUZU_DB_PATH` | `./data` | Database file location | [Configuration](README.md#configuration) |
| `KUZU_READ_ONLY` | `false` | Enable read-only mode | [Read-Only Mode](README.md#read-only-mode) |
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT token signing key | [JWT Configuration](README.md#jwt-authentication-configuration) |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm | [JWT Configuration](README.md#jwt-authentication-configuration) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration time | [JWT Configuration](README.md#jwt-authentication-configuration) |
| `JWT_ENABLED` | `true` | Enable/disable authentication | [JWT Configuration](README.md#jwt-authentication-configuration) |
| `GITHUB_TOKEN` | - | GitHub API token | [Docker Config](docker/README.md#environment-configuration) |

### Service Ports

| Service | Port | Purpose | Documentation |
|---------|------|---------|---------------|
| MCP Server | 8080 | HTTP API | [Server Documentation](server/README.md) |
| MCP Server | 50051 | gRPC (future) | [Server Documentation](server/README.md) |
| Kestra | 8081 | CI/CD Web UI | [Docker Documentation](docker/README.md) |

## 📊 Project Status & Roadmap

### Current Status
- ✅ **Core Features**: All basic functionality implemented
- ✅ **Documentation**: Comprehensive documentation complete
- ✅ **Testing**: Full test coverage
- ✅ **Docker**: Production-ready deployment
- ✅ **Volume Management**: Research-driven storage strategy

### In Progress
- 🔄 **CI/CD Integration**: Kestra workflow development
- 🔄 **Performance Optimization**: Query and indexing improvements

### Planned
- 📋 **IDE Plugins**: VS Code, IntelliJ, etc.
- ✅ **Authentication**: JWT token-based authentication (COMPLETED)
- 📋 **Monitoring**: Prometheus and Grafana integration

## 🤝 Contributing to Documentation

### Documentation Standards
- **Clarity**: Write for your audience (beginner, intermediate, expert)
- **Examples**: Include working code examples
- **Cross-References**: Link to related documentation
- **Maintenance**: Keep documentation up-to-date with code changes

### Documentation Types
- **README Files**: Overview and quick start information
- **API Docs**: Detailed endpoint documentation
- **Guides**: Step-by-step instructions
- **Reference**: Configuration and troubleshooting

### Update Process
1. **Make Changes**: Update relevant documentation files
2. **Test Examples**: Verify all code examples work
3. **Update Index**: Add new documentation to this index
4. **Review**: Ensure consistency and clarity

## 📞 Getting Help

### Self-Service Resources
1. **Search Documentation**: Use this index to find relevant docs
2. **Check Examples**: Look for similar use cases in examples
3. **Review Issues**: Search existing GitHub issues

### Support Channels
1. **GitHub Issues**: For bugs and feature requests
2. **Discussions**: For questions and community support
3. **Documentation**: For comprehensive guides and references

### Contributing
1. **Documentation**: Improve existing docs or add new ones
2. **Examples**: Add more client examples and use cases
3. **Testing**: Help improve test coverage and documentation

---

## 📝 Documentation Maintenance

This documentation index is maintained as part of the GraphMemory-IDE project. When adding new documentation:

1. **Add to Index**: Update this file with new documentation
2. **Cross-Reference**: Link from related documents
3. **Test Links**: Verify all links work correctly
4. **Update Status**: Reflect current project status

**Last Updated**: 2024-05-28  
**Maintained By**: GraphMemory-IDE Team 