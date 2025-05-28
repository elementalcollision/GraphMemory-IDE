## **Product Requirements Document: GraphMemory-IDE**

Version: 1.0 (Combined)  
Date: 27 May 2025  
Author:  Dave Graham  
Project Code-Name: “GraphMemory-IDE”

### ---

**0\. Document Control**

| Item | Value |
| :---- | :---- |
| **Author** | Dave Graham (@dave.graham) |
| **Reviewers** | "Core Engineering, Dev Infra, Security, DX UX" |
| **Status** | Draft |
| **Target release** | v1.0 MVP (± 12 weeks from kickoff) |

### ---

**1\. Executive Summary & Purpose**

**Objective:** To create an AI-assisted development environment by providing every supported IDE (Cursor, Windsurf, Qodo, Zed) with an on-device, long-term “AI memory” layer. This system will be powered by Kuzu GraphDB and exposed through a Model Context Protocol (MCP)-compliant server. The core purpose is to enable AI agents, code-completion engines, and chat copilots to query rich, cross-file context with high performance.

### ---

**2\. Background**

The foundation for this project includes an existing Kuzu MCP server, available via Docker or Node, providing a starting point for the storage and query layer. We will leverage **OrbStack** as a lightweight, Docker-compatible engine for development and CI/headless operations. **Kestra** will serve as our declarative workflow engine for CI/CD. The **Model Context Protocol (MCP)** provides official Python and TypeScript SDKs, facilitating client and server implementation.

### ---

**3\. Goals & Success Metrics**

| Goal | Metric | Target |
| :---- | :---- | :---- |
| Low-latency retrieval | p95 time for mcp/tools/query | ≤ 50 ms on M2 laptop, 1 M nodes |
| Developer productivity | Task-completion time delta vs control | ≥ 15 % faster |
| One-command updates | npx @graphmemory/cli@latest upgrade success rate | 100 % |
| CI reliability | Kestra pipeline pass rate on main | ≥ 95 % |
| Repository Ingestion | 1GB Repository | \< 2 minutes |
| Cold Start Time |  | \< 5s |
| Memory Usage | DB Container | \< 512MB |

### ---

**4\. Scope**

| In-scope | Out-of-scope / Future |
| :---- | :---- |
| Local Kuzu DB container & MCP server | Cloud-sync of memory graphs |
| IDE plugins (Cursor, Windsurf, Qodo, Zed) | Non-desktop IDEs (e.g., Codespaces) |
| Kestra-based build / test / publish | Large-scale analytics on memory data |
| npx-driven installer & updater | Alternative graph engines |
| GitHub repository analysis & pattern ingestion |  |
| Local Docker-based Kuzu instance management |  |

### ---

**5\. System Architecture**

The system enables IDE plugins to communicate with a local MCP server via gRPC or HTTP/SSE, which in turn interacts with a Kuzu GraphDB instance. CI/CD and updates are handled by Kestra/OrbStack and NPX, respectively.

Code snippet

graph TD  
    A\[IDE Plugin (TS/Rust)\] \--\>|gRPC / MCP (HTTP/SSE)| B\[MCP Server (Python 3.11+)\]  
    B \--\>|libkuzu / Cypher/Tools| C\[(Kuzu DB)\]  
    subgraph OrbStack Docker Network  
        B  
        C  
    end  
    D\[Kestra Workflows\] \--\> B  
    D \--\> C  
    A \--\>|npx @graphmemory/cli| F\[Update Manager\]

**Core Components:**

1. **IDE Plugins** (TypeScript/Rust)  
2. **MCP Server** (Python 3.11+)  
3. **Kuzu DB Container** (Docker)  
4. **OrbStack CI/CD Pipeline**  
5. **NPX Update System**

### ---

**6\. Functional Requirements**

| ID | Description |
| :---- | :---- |
| FR-1 | The system SHALL ingest IDE telemetry (file open/save, symbol index, test runs, user chat) into Kuzu via the MCP resources endpoint. |
| FR-2 | The IDE plugin SHALL request top-K relevant nodes/snippets via MCP tools/query. |
| FR-3 | The system SHALL support read-only mode toggled with KUZU\_READ\_ONLY=true. |
| FR-4 | An npx CLI (@graphmemory/cli) SHALL perform install/upgrade/diagnostics on all supported OSes. |
| FR-5 | The build pipeline SHALL run unit, integration and e2e suites inside OrbStack. |
| FR-6 | The system SHALL clone and analyze GitHub repositories. |

### ---

**7\. Non-Functional Requirements**

* **Performance:**  
  * p95 ≤ 50 ms query latency.  
  * Ingest ≥ 2 k events /s.  
  * Repository Ingestion (1GB) \< 2 minutes.  
  * Cold Start Time \< 5s.  
  * Memory Usage (DB Container) \< 512MB.  
* **Portability:** Single codebase, ARM & AMD64 containers via OrbStack multi-arch.  
* **Security:**  
  * Default local-only network; opt-in TCP exposure behind mTLS.  
  * Read-only filesystems and Seccomp profiles for DB container.  
  * Resource limits via OrbStack.  
  * JWT-based authentication.  
* **Updatability:** CLI update path via npx @graphmemory/cli@latest upgrade.  
* **Observability:** Structured logs, Prometheus metrics, Kestra-surfaced dashboards.

### ---

**8\. Implementation Details**

#### **8.1 Repository Cloning & Analysis**

Kestra will be used for batch processing of repository cloning and analysis.

Python

class RepoIngester:  
    def clone\_and\_analyze(self, repo\_url: str):  
        """  
        Example output structure:  
        {  
            "schema\_version": "0.2.1",  
            "entities": {  
                "files": 142, \# \[cite: 5\]  
                "classes": 89, \# \[cite: 5\]  
                "functions": 1203 \# \[cite: 5\]  
            },  
            "relationships": \["inherits", "calls", "references"\] \# \[cite: 5\]  
        }  
        """  
        \# Uses Kestra for batch processing \[cite: 5\]  
        subprocess.run(\[ \# \[cite: 6\]  
            "kestra", "namespace=dev", \# \[cite: 6\]  
            "flow=repo\_analysis", \# \[cite: 6\]  
            f"repo={repo\_url}" \# \[cite: 6\]  
        \]) \# \[cite: 6\]

#### **8.2 Docker Environment Setup (docker-compose.yml)**

YAML

version: '3.9' \# Using newer version from PRD2

services:  
  kuzu-db:  
    image: kuzudb/kuzu:0.10 \# Using newer version from PRD2 \[cite: 48\]  
    volumes:  
      \- ./data:/database \# Using path from PRD2 \[cite: 48\]  
    networks:  
      \- memory-net \[cite: 48\]

  mcp-server:  
    build: ./docker/mcp-server \# Using path from PRD2 \[cite: 48\]  
    ports:  
      \- "8080:8080" \# Using port from PRD2 \[cite: 48\]  
      \- "50051:50051" \# Adding gRPC port from PRD1 \[cite: 7\]  
    environment:  
      \- KUZU\_DB\_PATH=/database \# Using var from PRD2 \[cite: 48\]  
    depends\_on:  
      \- kuzu-db \[cite: 7, 48\]  
    networks:  
      \- memory-net \[cite: 7, 48\]

networks:  
  memory-net:  
    driver: bridge \[cite: 7, 48\]

#### **8.3 Workspace Structure**

graphmemory/  
├─  .kestra/                 \# Kestra flows \[cite: 47\]  
├─  docker/                  \# Dockerfiles & compose \[cite: 47\]  
│    ├─  kuzu/ \[cite: 47\]  
│    └─  mcp-server/ \[cite: 47\]  
├─  server/                  \# Forked kuzu-mcp-server \+ patches \[cite: 47\]  
├─  plugins/ \[cite: 47\]  
│    ├─  cursor/ \[cite: 47\]  
│    ├─  windsurf/ \[cite: 47\]  
│    └─  zed/ \[cite: 47\]  
└─  cli/                     \# Node CLI published as @graphmemory/cli \[cite: 47\]

### ---

**9\. CI/CD Pipeline (OrbStack \+ Kestra)**

Kestra flows, triggered on PR and main merges, will manage the CI/CD process within OrbStack. Artifacts will be cached to OrbStack volumes.

| Step | Flow ID | Container | Notes |
| :---- | :---- | :---- | :---- |
| Lint & Unit Tests | graphmemory.tests | python:3.11 | Pytest with coverage gate ≥ 90% (PRD1 suggests 70%) |
| Build Images | graphmemory.build | Docker-in-Docker | Multi-arch buildx |
| Integration Tests | graphmemory.it | compose up | Runs against Kuzu MCP container |
| Publish | graphmemory.publish | node:20 | npm publish & docker push |
| Release Docs | graphmemory.docs | mkdocs | Auto-deploy GitHub Pages |

**Testing Workflow Examples:**

* **Unit Tests:** orbstack run \--env TEST\_ENV=ci pytest tests/ \--cov=src \--cov-report=xml  
* **Integration Tests:**  
  Python  
  \# test\_integration.py  
  async def test\_code\_ingestion():  
      async with AsyncKuzuClient("localhost:50051") as client: \# \[cite: 8\]  
          response \= await client.ingest\_repo("https://github.com/example/repo") \# \[cite: 8\]  
          assert response.entity\_count \> 0 \# \[cite: 8\]

* **Performance Benchmarking:** Using K6.  
  YAML  
  \# kestra-flow.yml  
  tasks:  
    \- id: load\_test  
      type: io.kestra.plugin.gcp.runner.LoadTest \# \[cite: 9\]  
      script: |  
        k6 run \--vus 50 \--duration 5m \\ \# \[cite: 9\]  
        tests/load/memory\_query\_test.js \# \[cite: 9\]

### ---

**10\. NPX Update System**

We will publish a CLI as a scoped package: @graphmemory/cli.  
Users will update using npx @graphmemory/cli@latest upgrade.  
**Update Flow:**

1. Run npx @graphmemory/cli@latest upgrade.  
2. The CLI pulls the newest Docker images (docker pull kuzudb/mcp-server:latest).  
3. Re-creates containers via docker compose up \-d \--pull always.  
4. Migrates Kuzu schema if necessary.  
5. The CLI itself can be updated via npm install \-g @graphmemory/cli.

**Features:** Differential updates, Rollback capability, Signature verification.

### ---

**11\. Security Requirements**

1. **Container Security:** Use read-only filesystems, Seccomp profiles, and resource limits via OrbStack.  
2. **Network:** Default to local-only network; provide opt-in TCP exposure with mTLS.  
3. **Authentication:** Implement JWT-based authentication between the IDE plugin and the MCP server.  
   TypeScript  
   // auth.ts  
   const jwt \= await ide.auth.getSessionToken(); // \[cite: 10\]  
   const client \= new KuzuClient({ // \[cite: 10\]  
       endpoint: "localhost:50051", // \[cite: 10\]  
       metadata: new Metadata({ 'authorization': \`Bearer ${jwt}\` }) // \[cite: 10\]  
   });

### ---

**12\. Testing Strategy**

A comprehensive testing pyramid will be implemented:

1. **Unit Tests:** Aim for ≥ 90% coverage (Note: PRD1 suggested 70% ). Run via pytest.  
2. **Integration Tests:** Use docker-compose to test interactions between components, specifically MCP calls. Kestra will manage these tests.  
3. **End-to-End (E2E) Testing:** Utilize Playwright to script headless IDE sessions.  
4. **Performance Testing:** Use Locust or K6 to load test the tools/query endpoint, failing if p95 \> 50 ms.

### ---

**13\. Milestones & Timeline (12 Weeks)**

| Week | Milestone | Key Deliverables |
| :---- | :---- | :---- |
| 1–2 | Project kickoff & env bootstrap | Repos cloned, OrbStack & Kestra pipelines green |
| 3–5 | MCP server hardening | Docker image, schema migrations, read-only mode |
| 6–7 | IDE plugin α release | Cursor \+ Zed basic retrieval |
| 8–9 | CLI \+ npx updater | @graphmemory/cli published |
| 10 | Performance optimisation | p95 latency met |
| 11 | Security & privacy review | Threat model, mTLS |
| 12 | Public beta tag | v1.0-beta, docs, demo video |

*(Note: This timeline aligns with PRD2. PRD1 had an 18-week timeline but PRD2 seems more recent and specific)*.

### ---

**14\. Dependencies & Risks**

| Dependency/Risk | Mitigation |
| :---- | :---- |
| Kuzu 0.10+ compatibility |  |
| IDE API stability (Cursor/Windsurf/Qodo/Zed) |  |
| OrbStack performance & CLI changes | Pin OrbStack version in CI; weekly smoke tests |
| Breaking MCP spec changes | Track spec repo; adapter layer & integration tests |
| Vector search missing in Kuzu | Store embeddings as node attrs; fall back to disk-ANN plugin |
| General DB Issues | Fallback SQLite storage; Circuit breaker pattern for DB queries |
| Deployment Issues | Canary releases via NPX |

### ---

**15\. Developer Setup & Quick Start**

**Prerequisites (macOS/Linux):**

Bash

brew install orbstack     \# installs orb \+ docker CLI \[cite: 46\]  
brew install kestra-io/tap/kestra \# \[cite: 46\]  
brew install kuzu \# \[cite: 46\]  
npm install \-g npx \# \[cite: 46\]  
python \-m pip install mcp \# \[cite: 46\]

**Setup & Run:**

Bash

\# Clone repositories (adjust paths as needed) \[cite: 46\]  
git clone https://github.com/kuzudb/kuzu-mcp-server.git \# \[cite: 46\]  
git clone https://github.com/graphmemory/ide-plugins.git \# \[cite: 46\]

\# Spin up everything \[cite: 63\]  
orb start \# \[cite: 63\]  
docker compose \-f docker/docker-compose.yml up \-d \# \[cite: 63\]

\# Verify MCP health \[cite: 63\]  
curl http://localhost:8080/health \# \[cite: 63\]

\# Upgrade \[cite: 63\]  
npx @graphmemory/cli@latest upgrade \# \[cite: 63\]

### ---

**16\. Open Questions**

* What are the minimum OS versions to support for each IDE?  
* What are the licensing implications for distributing Kuzu binaries with plugins?  
* Will future cloud-sync require GDPR/DPA review?

### ---

**17\. Next Steps**

Confirm scope and milestones with stakeholders. Upon approval, convert this PRD into the Jira/Epic structure and a formal implementation plan.

