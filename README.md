# GraphMemory-IDE

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/elementalcollision/GraphMemory-IDE/actions/workflows/ci.yml/badge.svg)](https://github.com/elementalcollision/GraphMemory-IDE/actions/workflows/ci.yml)

An AI-assisted, long-term memory system for IDEs, powered by [Kuzu](https://kuzudb.com/) graph database. GraphMemory-IDE is an MCP (Model Context Protocol) server that provides semantic vector search, graph-based knowledge storage, and real-time analytics. It integrates with VSCode, Cursor, and Windsurf through dedicated IDE plugins.

## Features

- **Graph-based memory storage** — Kuzu native graph database with semantic vector search (HNSW indexes, sentence-transformers embeddings)
- **Codon-accelerated graph algorithms** — Optional native compilation via [Codon](https://github.com/exaloop/codon) for 10-100x speedups on centrality, community detection, path analysis, and similarity computations, with automatic Python/NetworkX fallback
- **FastAPI backend** — Async API with JWT authentication (EdDSA/Ed25519), rate limiting, and security middleware
- **Real-time analytics** — WebSocket and SSE streaming for live telemetry dashboards
- **Streamlit dashboard** — Interactive visualization of graph metrics, user activity, and system health
- **Multi-IDE plugin support** — Extensions for VSCode, Cursor, and Windsurf
- **Full observability** — Prometheus metrics, Grafana dashboards, health checks, and alert correlation
- **Production-ready Docker deployment** — Multi-service Docker Compose with Nginx, PostgreSQL, Redis, and monitoring stack

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/elementalcollision/GraphMemory-IDE.git
cd GraphMemory-IDE/docker
docker compose up -d
```

Services will be available at:
- MCP Server: http://localhost:8080/docs
- Kestra (workflow orchestration): http://localhost:8081

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload

# Start the Streamlit dashboard (separate terminal)
cd dashboard
streamlit run streamlit_app.py
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | (required) | Secret key for JWT token signing |
| `DATABASE_URL` | `sqlite:///./graphmemory.db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection for caching |
| `KUZU_DB_PATH` | `./data/kuzu` | Path to Kuzu graph database |
| `CODON_ENABLED` | `true` | Enable Codon acceleration |
| `CODON_LIB_PATH` | `./codon/lib/` | Path to compiled Codon libraries |
| `CODON_MIN_GRAPH_SIZE` | `100` | Minimum graph size for Codon routing |

## Architecture

GraphMemory-IDE uses a hybrid architecture where I/O-bound code (FastAPI, database clients, WebSocket) runs in CPython, while compute-heavy graph algorithms can optionally run as native-compiled Codon modules.

```
IDE Plugins (VSCode/Cursor/Windsurf)
        |
        v
  FastAPI Server (CPython)
   ├── JWT Auth + Security Middleware
   ├── MCP Protocol Handler
   ├── Telemetry Ingestion
   └── Analytics Engine
        |
   ┌────┴────┐
   v         v
Kuzu DB   Redis Cache
(graphs)  (sessions)
   |
   v
Codon Bridge (optional)
 ├── Graph Kernels (.so/.dylib)
 └── Python/NetworkX fallback
```

See [Architecture Overview](docs/architecture/ARCHITECTURE_OVERVIEW.md) for detailed system design.

### Codon Acceleration

The `codon/` directory contains graph algorithm implementations compiled to native machine code via Codon. The bridge layer (`codon/bridge/`) automatically routes computations based on graph size and library availability:

- **Graph kernels**: betweenness/closeness/degree centrality, PageRank, label propagation, Louvain community detection, BFS/Dijkstra shortest paths
- **Data processing**: cosine similarity, batch vector operations, consistent hashing
- **Fallback**: If Codon libraries aren't compiled, all operations fall back to NetworkX/numpy transparently

Compile Codon modules with:

```bash
./scripts/build_codon.sh
```

## Project Structure

```
GraphMemory-IDE/
├── server/                # FastAPI backend
│   ├── main.py            # Application entry point
│   ├── core/              # Configuration and settings
│   ├── auth/              # SSO, MFA, onboarding
│   ├── auth_jwt.py        # JWT authentication
│   ├── analytics/         # Analytics engine
│   ├── collaboration/     # Real-time collaboration
│   ├── dashboard/         # Dashboard API routes
│   ├── monitoring/        # Health checks, metrics, alerting
│   ├── security/          # Security middleware
│   ├── streaming/         # WebSocket/SSE streaming
│   └── graph_database.py  # Kuzu DB integration
├── dashboard/             # Streamlit UI
├── frontend/              # TypeScript/React frontend
├── codon/                 # Codon acceleration layer
│   ├── bridge/            # Python-Codon interop with fallback
│   ├── graph_kernels/     # Native graph algorithms (.codon)
│   └── data_processing/   # Native data operations (.codon)
├── docker/                # Docker Compose configs
│   ├── docker-compose.yml # Development environment
│   └── production/        # Production multi-service setup
├── tests/                 # Test suites
│   ├── integration/       # Integration tests
│   ├── production/        # Production validation
│   ├── load_testing/      # Locust load tests
│   └── smoke/             # Smoke tests
├── docs/                  # Documentation
├── ide-plugins/           # VSCode, Cursor, Windsurf extensions
├── monitoring/            # Prometheus & Grafana configs
├── scripts/               # Build and deployment scripts
└── kubernetes/            # Kubernetes manifests
```

## Testing

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run with coverage
PYTHONPATH=. pytest tests/ --cov=server --cov-report=html

# Run specific test categories
PYTHONPATH=. pytest tests/ -m unit
PYTHONPATH=. pytest tests/ -m integration
PYTHONPATH=. pytest tests/ -m "not slow"
```

Test markers: `unit`, `integration`, `e2e`, `api`, `database`, `authentication`, `analytics`, `performance`, `slow`

Coverage target: 85% minimum.

## Production Deployment

For production, use the multi-service Docker Compose configuration:

```bash
cd docker/production
cp .env.example .env  # Configure environment variables
docker compose -f docker-compose.prod.yml up -d
```

This starts 7+ services: Nginx (reverse proxy), FastAPI, Streamlit, Analytics, PostgreSQL, Redis, Prometheus, and Grafana — with isolated network subnets and resource limits.

See the [Docker Deployment Guide](docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md) for complete production setup instructions.

## Documentation

| Directory | Description |
|-----------|-------------|
| [docs/project/](docs/project/) | Project overview, PRD, contributing guidelines, security policy |
| [docs/architecture/](docs/architecture/) | System architecture, code paths, network flows |
| [docs/api/](docs/api/) | API reference and client examples |
| [docs/deployment/](docs/deployment/) | Docker, Kubernetes, and production deployment guides |
| [docs/development/](docs/development/) | Developer setup, code quality, testing procedures |
| [docs/operations/](docs/operations/) | System operations and performance tuning |
| [docs/monitoring/](docs/monitoring/) | Prometheus, Grafana, and alerting configuration |
| [docs/analytics/](docs/analytics/) | Analytics system and ML components |
| [docs/ide-plugins/](docs/ide-plugins/) | Plugin development for VSCode, Cursor, Windsurf |
| [docs/user-guides/](docs/user-guides/) | Tutorials and end-user documentation |

## Contributing

See [Contributing Guidelines](docs/project/CONTRIBUTING.md) for development workflow, commit conventions, and code review process.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
