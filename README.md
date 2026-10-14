# GraphMemory-IDE

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/elementalcollision/GraphMemory-IDE/actions/workflows/ci.yml/badge.svg)](https://github.com/elementalcollision/GraphMemory-IDE/actions/workflows/ci.yml)

An AI-assisted, long-term memory system for IDEs, powered by [LadybugDB](https://ladybugdb.com/) — an embedded, columnar, MIT-licensed graph database. GraphMemory-IDE is an MCP (Model Context Protocol) server that provides semantic vector search, graph-based knowledge storage, and real-time analytics. It integrates with VSCode, Cursor, and Windsurf through dedicated IDE plugins.

> **Graph database:** the backend runs on **LadybugDB 0.21.2**, the actively developed successor to KuzuDB (whose open-source development halted after its acquisition by Apple). The full migration record — verified API differences, phase-by-phase execution, and the operational migration guide — lives in [`MIGRATION_PLAN_LADYBUG.md`](MIGRATION_PLAN_LADYBUG.md) and [`docs/migration/KUZU_TO_LADYBUG.md`](docs/migration/KUZU_TO_LADYBUG.md).

## Features

- **Graph-based memory storage** — LadybugDB embedded graph database (Cypher / openCypher dialect) with automatic primary-key hash indexes and zone-map pruning on all columns
- **Semantic vector search** — sentence-transformers embeddings with `array_cosine_similarity` Top-K queries over node embedding columns
- **Codon-accelerated graph algorithms** — Optional native compilation via [Codon](https://github.com/exaloop/codon) for 10-100x speedups on centrality, community detection, path analysis, and similarity computations, with automatic Python/NetworkX fallback
- **FastAPI backend** — Async API with JWT authentication (EdDSA/Ed25519), optional read-only mode, rate limiting, and security middleware
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
# 1. Install dependencies (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Initialise the graph database schema (REQUIRED before first start —
#    the app opens the database but does not create the schema itself)
LADYBUG_DB_PATH=./data/ladybug.lbdb python server/init_db.py

# 3. Start the FastAPI server
uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload

# 4. (optional) Start the Streamlit dashboard (separate terminal)
cd dashboard && streamlit run streamlit_app.py
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_LADYBUG_DB_PATH` | `./data/ladybug.lbdb` | Path to the LadybugDB graph database file (a single `.lbdb` file; the parent directory must exist — the app creates it) |
| `DB_LADYBUG_READ_ONLY` | `false` | Open the graph database read-only (writes rejected at the DB layer; schema init skipped) |
| `JWT_SECRET_KEY` | (auto-generated) | Secret key for JWT token signing; set explicitly in production |
| `DB_DATABASE_URL` | `postgresql://user:password@localhost:5432/graphmemory_dev` | PostgreSQL connection string (relational + telemetry storage) |
| `DB_REDIS_URL` | `redis://localhost:6379/0` | Redis connection for caching (falls back to in-memory cache when unreachable) |
| `CODON_ENABLED` | `true` | Enable Codon acceleration |
| `CODON_LIB_PATH` | `./codon/lib/` | Path to compiled Codon libraries |
| `CODON_MIN_GRAPH_SIZE` | `100` | Minimum graph size for Codon routing |

> **Note on env prefixes:** database-related settings are read by pydantic with the `DB_` prefix — e.g. the setting `LADYBUG_DB_PATH` is set via the `DB_LADYBUG_DB_PATH` environment variable. The plain `LADYBUG_DB_PATH` form is honoured by `server/init_db.py` (and `KUZU_DB_PATH` remains as a deprecated fallback there, for one release cycle).

## Architecture

GraphMemory-IDE uses a hybrid architecture where I/O-bound code (FastAPI, database clients, WebSocket) runs in CPython, while compute-heavy graph algorithms can optionally run as native-compiled Codon modules.

```
IDE Plugins (VSCode/Cursor/Windsurf)
        |
        v
  FastAPI Server (CPython)
   ├── JWT Auth (EdDSA) + Security Middleware (TrustedHost / rate limit)
   ├── MCP Protocol Handler
   ├── Telemetry Ingestion + Query (/telemetry/*)
   ├── Top-K Vector Search (/tools/topk)
   ├── Analytics Engine (/api/v1/analytics/*)
   └── Dashboard Routes + SSE (/dashboard/*)
        |
   ┌────┴─────────┐
   v              v
LadybugDB      PostgreSQL + Redis
(embedded      (relational store,
 graph DB,      sessions, cache)
 sync engine)
   |
   v
Codon Bridge (optional)
 ├── Graph Kernels (.so/.dylib)
 └── Python/NetworkX fallback
```

**Graph database layer** (`server/graph_database.py`): an embedded LadybugDB instance opened in-process — no separate DB server. It provides a thread-safe connection pool (Condition-variable based), LadybugDB's native `AsyncConnection` for async handlers (`GraphDatabaseManager.get_async_connection()`), schema management (User / Project / Memory node tables and OWNS / COLLABORATES / CONTAINS / RELATES_TO / ACCESSED_BY relationship tables), a query engine with parameterised Cypher execution and Prometheus instrumentation, and health checks (`CALL show_tables()` schema-integrity validation). A `read_only` mode opens the database for read-only workloads (e.g. analytics replicas).

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

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health (CPU/memory/disk checks) |
| `/api/v1/status` | GET | Application status incl. `database.ladybug_path` and `read_only` |
| `/auth/token` | POST | JWT access token (OAuth2 password flow) |
| `/telemetry/ingest` | POST | Ingest an IDE telemetry event (validated `EventType` enum, ISO-8601 timestamp, JSON-serialised data) |
| `/telemetry/list` | GET | List telemetry events (paginated) |
| `/telemetry/query` | GET | Query events by `event_type` / `user_id` / `session_id` filters |
| `/tools/topk` | POST | Top-K semantic search: sentence-transformers embedding + `array_cosine_similarity` over the requested node table |
| `/api/v1/analytics/*` | GET | Analytics engine (centrality, community, clustering, streaming, GPU status) |
| `/dashboard/*` | GET | Dashboard API + SSE real-time streams (`/dashboard/stream/analytics`) |
| `/metrics` | GET | Prometheus metrics |

Full reference: [API Guide](docs/api/API_GUIDE.md). Interactive docs at `http://localhost:8080/docs` (disabled in production).

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
│   ├── backup/            # LadybugDB/PostgreSQL/Redis backup orchestration
│   ├── graph_database.py  # LadybugDB integration (pool, schema, query engine, health)
│   └── init_db.py         # Graph schema initialisation (run before first start)
├── dashboard/             # Streamlit UI
├── frontend/              # TypeScript/React frontend
├── codon/                 # Codon acceleration layer
│   ├── bridge/            # Python-Codon interop with fallback
│   ├── graph_kernels/     # Native graph algorithms (.codon)
│   └── data_processing/   # Native data operations (.codon)
├── docker/                # Docker Compose configs
│   ├── docker-compose.yml # Development environment
│   ├── docker-compose.test.yml # Test services (PostgreSQL + Redis, ephemeral)
│   └── production/        # Production multi-service setup
├── tests/                 # Test suites
│   ├── integration/       # Integration tests
│   ├── production/        # Production validation
│   ├── load_testing/      # Locust load tests
│   └── smoke/             # Smoke tests
├── docs/                  # Documentation (incl. docs/migration/)
├── ide-plugins/           # VSCode, Cursor, Windsurf extensions
├── monitoring/            # Prometheus & Grafana configs
├── scripts/               # Build, deployment, and test-DB scripts
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

Registered test markers: `asyncio`, `unit`, `integration`, `slow`, `real_time`, `real_services`, `performance`, `mock_data`, `load`, `external`, `database`, `authentication` (`--strict-markers` is enforced).

### Integration tests against real services

Database integration tests expect PostgreSQL and Redis backing services. The
ephemeral test profile brings them up (Docker / OrbStack), matching the fixture
defaults:

```bash
docker compose -f docker/docker-compose.test.yml up -d
python scripts/init_test_db.py          # create the app schema in the test DB
PYTHONPATH=. pytest tests/integration/test_database_integration.py -v
docker compose -f docker/docker-compose.test.yml down -v
```

Without the services, PG-dependent fixtures skip cleanly; LadybugDB-backed tests run in-process against a temporary database and need no external services.

Coverage target: 85% minimum.

## Production Deployment

For production, use the multi-service Docker Compose configuration:

```bash
cd docker/production
cp env.production.template .env  # Configure environment variables
docker compose -f docker-compose.prod.yml up -d
```

This starts 7+ services: Nginx (reverse proxy), FastAPI, Streamlit, Analytics, PostgreSQL, Redis, Prometheus, and Grafana — with isolated network subnets and resource limits. A LadybugDB `api-server` sidecar (`ghcr.io/ladybugdb/api-server`) is available for external/admin graph access; pin a version tag in production.

See the [Docker Deployment Guide](docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md) for complete production setup instructions.

## Migration: Kuzu → LadybugDB

This codebase was migrated from Kuzu 0.10.0 to LadybugDB 0.21.2 (2026-10). Key facts for anyone extending the integration:

- **Python API**: `import ladybug as lb`; `Connection(db)` + `init_connection()`; snake_case result iteration (`has_next()` / `get_next()`, rows are **lists**)
- **Indexes**: PK-only hash indexes (automatic); secondary-property and FULLTEXT indexes are not supported in 0.21.2 — zone maps serve filter workloads instead
- **Vector search**: `array_cosine_similarity` (Kuzu's `list_cosine_similarity` does not exist)
- **Storage**: a single `.lbdb` file; the parent directory must exist (unlike Kuzu, LadybugDB does not create it)
- **CLI**: `lbug` (`brew install ladybug`); `EXPORT DATABASE` / `IMPORT DATABASE` supported for data migration

Full verified difference catalogue: [`MIGRATION_PLAN_LADYBUG.md`](MIGRATION_PLAN_LADYBUG.md) §3. Operational runbook for deployed instances: [`docs/migration/KUZU_TO_LADYBUG.md`](docs/migration/KUZU_TO_LADYBUG.md).

## Documentation

| Directory | Description |
|-----------|-------------|
| [MIGRATION_PLAN_LADYBUG.md](MIGRATION_PLAN_LADYBUG.md) | Kuzu → LadybugDB migration: phases, verified API differences, defect ledger |
| [docs/migration/](docs/migration/) | Operational migration guide + phase verification scripts |
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
