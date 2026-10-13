# Graph_Memory-IDE: Kuzu → LadybugDB Tactical Remediation & Uplift Plan

**Date:** 2026-10-13  
**Prepared for:** Dave Graham, Elemental Collision  
**Status:** FOR REVIEW — awaiting approval before execution  
**Scope:** Migrate Graph_Memory-IDE from Kuzu 0.10.0 (abandoned, Apple-acquired) to LadybugDB 0.21.2 (MIT, actively developed successor)

---

## 1. Executive Summary

KuzuDB's open-source development halted after acquisition by Apple. No new features, bug fixes, or security patches will be released. LadybugDB ("DuckDB for Graphs") is the direct successor — built by a committed team, MIT-licensed, and carrying forward the Kuzu vision with active development and enterprise support.

**The migration is low-risk.** LadybugDB's Python API is nearly 1:1 compatible with Kuzu's:

| Aspect | Kuzu 0.10.0 | LadybugDB 0.21.2 |
|--------|-------------|------------------|
| PyPI package | `kuzu==0.10.0` | `ladybug==0.21.2` |
| Import | `import kuzu` | `import ladybug as lb` |
| Database ctor | `kuzu.Database(path, buffer_pool_size=, max_num_threads=, compression=, auto_checkpoint=, checkpoint_threshold=)` | **Identical signature** + new params (`read_only`, `lazy_init`, `max_db_size`, `enable_checksums`) |
| Connection ctor | `kuzu.Connection(db, num_threads=N)` | `lb.Connection(db)` then `conn.set_max_threads_for_exec(N)` |
| `conn.execute(query)` | ✓ | ✓ (identical) |
| `conn.execute(query, parameters)` | ✓ | ✓ (identical — `dict[str, Any] \| None`) |
| `result.has_next()` / `result.get_next()` | ✓ | ✓ (identical) |
| `conn.set_query_timeout(ms)` | ✓ | ✓ (identical) |
| `conn.close()` / `db.close()` | ✓ | ✓ (identical) |
| Cypher syntax (openCypher) | ✓ | ✓ (identical — `CREATE NODE TABLE`, `CREATE REL TABLE`, `MATCH`, `CALL show_tables()`, etc.) |
| Storage | Directory-based | `.lbdb` file (single file) |
| CLI binary | `kuzu` | `lbug` |
| License | MIT | MIT |

**94 files** reference Kuzu across the codebase. The migration touches 6 layers: Python source, dependency manifests, Docker/infra, tests, CLI tooling, and documentation.

---

## 2. Impact Assessment — File Inventory

### 2.1 Python Source Files with `import kuzu` (11 files — **CRITICAL**)

| File | Lines | Role | Change Type |
|------|-------|------|-------------|
| `server/graph_database.py` | 547 | Core graph DB manager (pool, schema, query, health) | **Major** — import swap + Connection ctor + type hints |
| `server/main.py` | 583 | FastAPI app — `setup_database()` inits kuzu | **Moderate** — import swap + Database/Connection ctor |
| `server/init_db.py` | 74 | Schema init script | **Minor** — import swap + var rename |
| `server/analytics/engine.py` | 724 | Analytics engine with kuzu_connection | **Moderate** — import swap + type hints |
| `server/analytics/kuzu_analytics.py` | 661 | Advanced graph analytics (centrality, community, paths) | **Moderate** — import swap + class rename |
| `server/backup/kuzu_backup.py` | 585 | Backup/restore manager (filesystem, export JSON/Parquet/CSV) | **Moderate** — import swap + class rename |
| `server/database_sync.py` | 669 | PG↔graph sync engine (uses `get_graph_database()`) | **Minor** — no direct kuzu import, indirect only |
| `server/analytics_routes.py` | 527 | Analytics router init (`kuzu_connection` global) | **Minor** — import swap + var rename |
| `server/dashboard/analytics_client.py` | 437 | Dashboard analytics client | **Minor** — import swap + type hints |
| `server/data_seeding.py` | — | Data seeding (references `kuzu_result` vars) | **Trivial** — var rename only |
| `server/core/config.py` | — | Settings (`KUZU_DB_PATH`, `KUZU_READ_ONLY`) | **Minor** — field rename + env var rename |

### 2.2 Test Files (11 files)

| File | Role | Change Type |
|------|------|-------------|
| `tests/conftest.py` | Pytest fixtures: `kuzu_db`, `kuzu_connection`, `check_kuzu_health` | **Moderate** — fixture rename + import swap |
| `tests/fixtures/database.py` | `kuzu_test_database`, `kuzu_test_connection`, `_initialize_kuzu_test_schema` | **Moderate** — fixture rename + import swap |
| `tests/fixtures/advanced_database_fixtures.py` | Advanced test fixtures | **Moderate** — import swap + method rename |
| `tests/fixtures/real_services.py` | Real service test fixtures (`kuzu_db`, `kuzu_conn`) | **Moderate** — import swap + var rename |
| `tests/fixtures/application.py` | Application fixture | **Minor** — indirect refs |
| `tests/integration/test_database_integration.py` | DB integration tests | **Minor** — import swap in test body |
| `tests/analytics/test_integration_suite.py` | Analytics integration | **Minor** — import swap |
| `tests/integration_test.py` | Top-level integration test | **Trivial** — config key ref |
| `tests/test_main.py` | Main app tests | **Trivial** — ref update |
| `tests/functional/test_phase1_async_infrastructure.py` | Async infra tests | **Trivial** — ref update |
| `tests/utils/cleanup.py` | Test cleanup utilities | **Trivial** — path ref |

### 2.3 Dependency Manifests (4 files — **CRITICAL**)

| File | Current | Target |
|------|---------|--------|
| `requirements.in` | `kuzu` (unpinned) | `ladybug` (unpinned) |
| `requirements.txt` | `kuzu==0.10.0` (line 160) | `ladybug==0.21.2` |
| `docker/production/Dockerfile.analytics` | `kuzu==0.10.0` (line 81) | `ladybug==0.21.2` |
| `package.json` | keyword `"kuzu"` (line 21) | keyword `"ladybug"` |

### 2.4 Docker / Infra (10+ files)

| File | Change |
|------|--------|
| `docker/mcp-server/Dockerfile` | `ENV KUZU_DB_PATH=/database` → `ENV LADYBUG_DB_PATH=/database` |
| `docker/docker-compose.yml` | `KUZU_DB_PATH` env vars (lines 10, 66) |
| `docker/production/docker-compose.prod.yml` | env var + volume name `kuzu-data` → `ladybug-data` |
| `docker/production/docker-compose.yml` | same |
| `docker/backup-volumes.sh` | `docker_kuzu-data` volume refs (lines 123, 146, 151-152, 162, 186-187, 197) |
| `docker/production/scripts/analytics-entrypoint.sh` | `"kuzu"` in service check + `/app/data/kuzu` dir (lines 129, 145-147) |
| `docker/production/scripts/backup/backup.sh` | backup paths |
| `docker/production/scripts/backup/restore.sh` | restore paths + `restore_kuzu()` function |
| `deploy/scripts/production_deploy.sh` | `KUZU_DB_PATH=${APP_DIR}/data/kuzu` (line 212) |
| `kubernetes/manifests/deployments.yaml` | env vars + volume mounts |

### 2.5 CLI Tooling (3 files)

| File | Change |
|------|--------|
| `cli/update/database-migrator.mjs` | `this.kuzuPath` → `this.lbugPath`, CLI binary `kuzu` → `lbug`, `EXPORT DATABASE`/`IMPORT DATABASE` commands (same Cypher syntax) |
| `cli/commands.mjs` | kuzu references in command definitions |
| `cli/index.test.mjs` | test references |

### 2.6 Documentation (20+ files)

| Category | Files |
|----------|-------|
| Root | `README.md` |
| Architecture | `docs/architecture/README.md`, `ARCHITECTURE_OVERVIEW.md`, `CODE_PATHS.md` |
| User Guides | `docs/user-guides/getting-started.md`, `advanced-configuration.md`, `graph-operations.md`, `USER_GUIDE.md` |
| Operations | `docs/operations/README.md`, `OPERATIONS.md`, `PERFORMANCE_TUNING.md` |
| Development | `docs/development/DEVELOPER_GUIDE.md`, `DOCUMENTATION.md`, `COLOR_PALETTE_GUIDE.md` |
| Deployment | `docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md` |
| API | `docs/api/API_GUIDE.md` |
| Monitoring | `docs/monitoring/MONITORING_GUIDE.md`, `docs/analytics/README.md` |
| Project | `docs/project/SECURITY.md`, `CONTRIBUTING.md` |
| IDE Plugins | `docs/ide-plugins/PLUGIN_DEVELOPMENT.md` |
| Other | `docs/conf.py`, `mypy.ini` |

---

## 3. Technical Change Catalogue

### 3.1 Python Import Swap (Mechanical)

**Before:**
```python
import kuzu
# ...
db = kuzu.Database(path)
conn = kuzu.Connection(db)
result = conn.execute("MATCH (n) RETURN n")
```

**After:**
```python
import ladybug as lb
# ...
db = lb.Database(path)
conn = lb.Connection(db)
result = conn.execute("MATCH (n) RETURN n")
```

**Pattern:** Global find-and-replace `import kuzu` → `import ladybug as lb`, then replace all `kuzu.` references with `lb.` in the same files. The conditional import guard pattern (`try: import kuzu except ImportError:`) follows the same swap.

### 3.2 Connection Constructor (Breaking — Requires Code Change)

**Before:**
```python
conn = kuzu.Connection(self.database, num_threads=2)
```

**After:**
```python
conn = lb.Connection(self.database)
conn.init_connection()
conn.set_max_threads_for_exec(2)
```

**Affected files:** `server/graph_database.py` (line 75), `server/main.py` (line 112), all test fixtures.

### 3.3 Database Constructor (Compatible — No Change Needed)

The `Database()` constructor signature is a superset:

```python
# Current codebase call (graph_database.py:470-477) — WORKS AS-IS:
self.database = kuzu.Database(
    database_path=str(db_path),
    buffer_pool_size=self.config.buffer_pool_size,
    max_num_threads=self.config.max_num_threads,
    compression=self.config.compression,
    auto_checkpoint=self.config.auto_checkpoint,
    checkpoint_threshold=self.config.checkpoint_threshold
)

# Ladybug equivalent — identical params, just swap `kuzu` → `lb`:
self.database = lb.Database(
    database_path=str(db_path),
    buffer_pool_size=self.config.buffer_pool_size,
    max_num_threads=self.config.max_num_threads,
    compression=self.config.compression,
    auto_checkpoint=self.config.auto_checkpoint,
    checkpoint_threshold=self.config.checkpoint_threshold
)
```

**Bonus:** Ladybug's `Database()` now accepts `read_only` as a constructor param, replacing the separate `KUZU_READ_ONLY` config pattern. Consider wiring `settings.database.KUZU_READ_ONLY` → `read_only=settings.database.LADYBUG_READ_ONLY` in the constructor.

### 3.4 Environment Variables / Config

| Current | Proposed | Scope |
|---------|----------|-------|
| `KUZU_DB_PATH` | `LADYBUG_DB_PATH` | `server/core/config.py`, all Dockerfiles, docker-compose files, deploy scripts, k8s manifests |
| `KUZU_READ_ONLY` | `LADYBUG_READ_ONLY` | `server/core/config.py` |
| `TEST_KUZU_DB_PATH` | `TEST_LADYBUG_DB_PATH` | `tests/conftest.py` |
| `GRAPH_DATABASE_PATH` | (keep or alias) | `server/graph_database.py` — already generic |

**Backward-compat note:** Consider keeping `KUZU_DB_PATH` as a deprecated alias that falls back to `LADYBUG_DB_PATH` during a transition period, to avoid breaking existing deployments.

### 3.6 Index DDL Syntax (Breaking — discovered in Phase 0 smoke test)

**Before (Kuzu — graph_database.py:244-249):**
```python
"CREATE INDEX IF NOT EXISTS user_email_idx ON User(email)"
```

**After (LadybugDB 0.21.2):**
```python
"CREATE INDEX user_pk_idx FOR (u:User) ON (u.id)"
```

**Functional limitation:** LadybugDB 0.21.2 supports HASH/ART indexes **only on primary keys**. The codebase's four secondary indexes (`User(email)`, `Project(owner_id)`, `Memory(memory_type)`, `Memory(source_table, source_id)`) are **not supported**. LadybugDB maintains automatic **zone maps** (min/max pruning) on all columns, which partially compensates. Additionally, `IF NOT EXISTS` is not part of the `CREATE INDEX` grammar.

**Remediation:** Replace `_create_indexes()` index queries with either (a) PK-only indexes where meaningful, or (b) drop the secondary-index queries and rely on zone maps. The existing try/except-with-warning (graph_database.py:251-259) already degrades gracefully if left unchanged — but explicit remediation is preferred.

### 3.7 `show_tables()` Result Shape (Compatible — verified)

LadybugDB's `CALL show_tables() RETURN *` returns columns `[id, name, type, database name, comment]` — a leading numeric `id` column is added compared to Kuzu. The **table name is still at index 1**, which is exactly what `GraphHealthChecker._check_schema_integrity` reads (`row[1]`). **No code change required.**

### 3.8 `get_next()` Returns List, Not Tuple (Minor — compatible)

LadybugDB's `result.get_next()` / `get_all()` return Python **lists**; Kuzu returned tuples. `GraphQueryEngine._process_row()` already handles both (`isinstance(row, (list, tuple))`). **No code change required**, but any test asserting tuple equality must use lists.

### 3.9 Storage Migration (Data Path)

Kuzu stores data in a **directory** (`./data/kuzu/`); LadybugDB stores data in a **single `.lbdb file** (`./data/ladybug_graph.lbdb`). Existing Kuzu data is **not directly readable** by LadybugDB.

**Migration procedure:**
1. Export all data from the existing Kuzu database using `EXPORT DATABASE '/path/to/export/';` via the Kuzu CLI
2. Create a new LadybugDB database: `lb.Database("./data/ladybug_graph.lbdb")`
3. Import the exported data: `IMPORT DATABASE '/path/to/export/';` via the `lbug` CLI
4. Verify row counts and schema integrity with `CALL show_tables() RETURN *`

The `cli/update/database-migrator.mjs` already implements this export/import pattern — it just needs the CLI binary path swapped from `kuzu` to `lbug`.

### 3.6 Docker Volume Naming

| Current | Target |
|---------|--------|
| `docker_kuzu-data` | `docker_ladybug-data` |
| `kuzu-data` (backup) | `ladybug-data` (backup) |
| `/app/data/kuzu` (entrypoint) | `/app/data/ladybug` (entrypoint) |

**Note:** Volume renames require a migration step in deployed environments — the old volume must be backed up, new volume created, and data restored.

### 3.7 CLI Binary Migration

| Current | Target |
|---------|--------|
| `kuzu` CLI binary | `lbug` CLI binary |
| `brew install kuzu` (if used) | `brew install ladybug` |
| `pip install kuzu` | `pip install ladybug` |

The `database-migrator.mjs` uses `this.kuzuPath` (defaults to `'kuzu'`) for CLI commands — this becomes `this.lbugPath` (defaults to `'lbug'`). The `EXPORT DATABASE` and `IMPORT DATABASE` Cypher commands are identical in LadybugDB.

---

### 3.10 CamelCase Result Iteration Not Supported (Breaking — discovered in Phase 1)

`main.py` used `result.hasNext()` / `result.getNext()` (lines 379-380, 450-451, 514-515) — a Kuzu-era API variant. LadybugDB 0.21.2's `QueryResult` only exposes **snake_case** `has_next()` / `get_next()`. All camelCase calls converted. ✅ Fixed in Phase 1.

### 3.11 `list_cosine_similarity` Renamed (Breaking — discovered in Phase 1)

The vector-similarity endpoint (`main.py` Top-K search) used Kuzu's `list_cosine_similarity()`. In LadybugDB 0.21.2 the function is **`array_cosine_similarity`** (verified via `CALL show_functions()`). ✅ Fixed in Phase 1.

### 3.12 Parent Directory Must Exist (Minor — discovered in Phase 1)

Kuzu auto-created the database directory; LadybugDB raises `IO exception: Cannot open file` if the parent directory is missing. `graph_database.py` already guarded (`db_path.parent.mkdir(...)`); `init_db.py` needed an explicit `mkdir` — added. ✅ Fixed in Phase 1.

### 3.13 Pre-Existing Defect (Not a Migration Regression — Flagged)

Every `MetricsCollector()` instantiation (`server/monitoring/metrics.py`) registers duplicate collectors into the global prometheus `REGISTRY`; `graph_database.py` creates several instances, so the second raises `Duplicated timeseries in CollectorRegistry`. This defect predates the migration (same behaviour with Kuzu). **Recommend a follow-up task** (out of migration scope): make `MetricsCollector` use `create_custom_registry()` or guard against re-registration.

---

## 4. Execution Phases

### Phase 0: Pre-Flight (Day 0 — no code changes) — ✅ COMPLETED 2026-10-13

| # | Task | Owner | Gate | Status |
|---|------|-------|------|--------|
| 0.1 | Snapshot the existing Kuzu database (`EXPORT DATABASE` to backup) | Operator | Backup verified | ✅ N/A — **no existing Kuzu database found** (no `data/` dir; searched repo + common paths). Nothing to migrate. |
| 0.2 | Install `ladybug` Python package in a throwaway venv, run smoke test (`lb.Database(":memory:")`, `CREATE NODE TABLE`, `MATCH`) | Agent | Smoke test passes | ✅ **14/14 checks passed** against `ladybug==0.21.2` (smoke test replicates the codebase's exact API usage: Database ctor params, Connection + `set_max_threads_for_exec`, `$`-parameterised execute, `has_next`/`get_next`, `CALL show_tables()`, Kleene-star MATCH, `get_as_df`, `:memory:`, close). Surfaced 3 findings — see §3.6-3.8. |
| 0.3 | Install `lbug` CLI via `brew install ladybug`, verify `lbug :memory:` interactive shell | Operator | CLI confirmed | ✅ `lbug 0.21.2` installed via Homebrew; non-interactive query execution verified. |
| 0.4 | Create a feature branch: `feature/ladybug-migration` | Operator | Branch created | ✅ Branch created from `main`. |

### Phase 1: Core Python Source (Day 1) — ✅ COMPLETED 2026-10-13

| # | Task | Files | Risk | Status |
|---|------|-------|------|--------|
| 1.1 | Swap `import kuzu` → `import ladybug as lb` in all Python source files | §2.1 | Low | ✅ All `server/` source migrated |
| 1.2 | Fix Connection constructor: `Connection(db, num_threads=N)` → `Connection(db)` + `init_connection()` + `set_max_threads_for_exec(N)` | `graph_database.py`, `main.py` | Low | ✅ Fixed |
| 1.3 | Rename config fields: `KUZU_DB_PATH` → `LADYBUG_DB_PATH`, `KUZU_READ_ONLY` → `LADYBUG_READ_ONLY` | `config.py` | Low | ✅ Done (defaults `./data/ladybug.lbdb`) |
| 1.4 | Update `graph_database.py` default paths | `graph_database.py` | Low | ✅ `./data/ladybug_graph.lbdb` |
| 1.5 | Rename classes/vars: `KuzuAnalyticsEngine` → `LadybugAnalyticsEngine`, `KuzuBackupManager` → `LadybugBackupManager`, `kuzu_connection` → `ladybug_connection`, `KuzuQuery` → `LadybugQuery` (table `ladybug_queries`), `KuzuTenantManager` → `LadybugTenantManager`, etc. | 28 files | Medium | ✅ All renamed; files `kuzu_analytics.py` → `ladybug_analytics.py`, `kuzu_backup.py` → `ladybug_backup.py`, `kuzu_tenant_manager.py` → `ladybug_tenant_manager.py` (git mv) |
| 1.6 | Update `init_db.py` | `init_db.py` | Low | ✅ Rewritten; `KUZU_DB_PATH` env kept as deprecated fallback |
| 1.7 | Update health endpoint response: `"kuzu_path"` → `"ladybug_path"` | `main.py` | Low | ✅ Done |
| 1.9 | **Fix index DDL** (Phase 0 finding §3.6): `_create_indexes()` now documents the PK-only/zone-map model; unsupported secondary-index queries removed | `graph_database.py` | Medium | ✅ Done — verified no parser errors |
| 1.10 | Wire `read_only` — deferred to Phase 8 (uplift) as no current consumer requires it | `graph_database.py` | Low | ⏸ Deferred to Phase 8 |
| 1.11 | **NEW (§3.10):** camelCase `hasNext()`/`getNext()` → `has_next()`/`get_next()` in `main.py` (3 endpoints) | `main.py` | High | ✅ Fixed — would have crashed at runtime |
| 1.12 | **NEW (§3.11):** `list_cosine_similarity` → `array_cosine_similarity` in vector-search endpoint | `main.py` | High | ✅ Fixed — would have crashed at runtime |
| 1.13 | **NEW (§3.12):** `init_db.py` parent-directory `mkdir` (LadybugDB does not auto-create) | `init_db.py` | Medium | ✅ Fixed |

**Phase 1 verification:** 28 files compile clean; residual `kuzu` in `server/*.py` = only the intentional deprecated `KUZU_DB_PATH` env fallback in `init_db.py`. Functional verification against live LadybugDB: `GraphDatabaseManager.initialize()` (all 8 schema tables), parameterised INSERT/MATCH via `QueryEngine`, `GraphHealthChecker` (pool/access/schema-integrity healthy), clean close, singleton init — **all passed**. `init_db.py` verified with both `LADYBUG_DB_PATH` and fallback `KUZU_DB_PATH`. Pre-existing `MetricsCollector` duplicate-registration defect flagged (§3.13) — out of migration scope.

### Phase 2: Dependency Manifests (Day 1)

| # | Task | Files | Risk | Verification |
|---|------|-------|------|-------------|
| 2.1 | `requirements.in`: replace `kuzu` with `ladybug` | `requirements.in:4` | Low | — |
| 2.2 | `requirements.txt`: regenerate via `pip-compile requirements.in` | `requirements.txt` | Low | `ladybug==0.21.2` present, `kuzu==` absent |
| 2.3 | `Dockerfile.analytics`: replace `kuzu==0.10.0` with `ladybug==0.21.2` | `docker/production/Dockerfile.analytics:81` | Low | Docker build succeeds |
| 2.4 | `package.json`: replace keyword `"kuzu"` with `"ladybug"` | `package.json:21` | Trivial | — |
| 2.5 | `mypy.ini`: update any kuzu-specific ignores/type refs | `mypy.ini` | Trivial | — |

### Phase 3: Docker / Infra (Day 2)

| # | Task | Files | Risk | Verification |
|---|------|-------|------|-------------|
| 3.1 | Rename env vars: `KUZU_DB_PATH` → `LADYBUG_DB_PATH` in all Dockerfiles, compose files, entrypoint scripts | `docker/mcp-server/Dockerfile`, `docker/docker-compose.yml`, `docker/production/docker-compose*.yml`, `deploy/scripts/production_deploy.sh` | Medium | Env vars resolve |
| 3.2 | Rename Docker volumes: `kuzu-data` → `ladybug-data` in compose files and `backup-volumes.sh` | `docker/docker-compose.yml`, `docker/production/docker-compose*.yml`, `docker/backup-volumes.sh` | Medium | Volumes create |
| 3.3 | Update entrypoint scripts: `/app/data/kuzu` → `/app/data/ladybug`, service check `"kuzu"` → `"ladybug"` | `docker/production/scripts/analytics-entrypoint.sh`, `streamlit-entrypoint.sh`, `fastapi-entrypoint.sh` | Medium | Entrypoint runs |
| 3.4 | Update backup/restore scripts: paths, function names (`restore_kuzu()` → `restore_ladybug()`), S3 keys | `docker/production/scripts/backup/backup.sh`, `restore.sh` | Medium | Backup script runs |
| 3.5 | Update k8s manifests: env vars, volume mounts, volume names | `kubernetes/manifests/deployments.yaml`, `statefulsets.yaml`, `configmaps-secrets.yaml` | Medium | kubectl apply dry-run |
| 3.6 | Update DigitalOcean deploy config | `deploy/digitalocean/env_config.py`, `app.yaml`, `staging-app.yaml` | Low | Config valid |

### Phase 4: Tests (Day 2)

| # | Task | Files | Risk | Verification |
|---|------|-------|------|-------------|
| 4.1 | Swap imports in all test files | `tests/conftest.py`, `tests/fixtures/*.py`, `tests/integration/*.py`, etc. | Low | — |
| 4.2 | Rename fixtures: `kuzu_db` → `ladybug_db`, `kuzu_connection` → `ladybug_connection`, `check_kuzu_health` → `check_ladybug_health` | `tests/conftest.py` | Medium | Fixtures resolve |
| 4.3 | Update test fixture DB paths: `./test_data` → `./test_data/ladybug_test.lbdb` or `:memory:` | `tests/conftest.py:47`, `tests/fixtures/database.py` | Low | Tests create DB |
| 4.4 | Fix Connection constructor calls in fixtures (same as §3.2) | `tests/fixtures/*.py` | Low | — |
| 4.5 | Run full test suite: `pytest tests/ -v` | — | — | All tests pass |
| 4.6 | Update integration test config key: `settings.database.KUZU_DB_PATH` → `settings.database.LADYBUG_DB_PATH` | `tests/integration_test.py:147` | Trivial | — |

### Phase 5: CLI Tooling (Day 3)

| # | Task | Files | Risk | Verification |
|---|------|-------|------|-------------|
| 5.1 | Swap CLI binary path: `this.kuzuPath` → `this.lbugPath` (default `'lbug'`), all `_executeKuzuCommand` → `_executeLbugCommand` | `cli/update/database-migrator.mjs` | Medium | CLI runs |
| 5.2 | Update backup dir paths: `./backups/kuzu` → `./backups/ladybug`, `./temp/kuzu-migration` → `./temp/ladybug-migration` | `cli/update/database-migrator.mjs` | Low | — |
| 5.3 | Update `cli/commands.mjs` and `cli/index.test.mjs` references | `cli/commands.mjs`, `cli/index.test.mjs` | Low | CLI tests pass |

### Phase 6: Documentation (Day 3)

| # | Task | Files | Risk |
|---|------|-------|------|
| 6.1 | Update README.md: project description, architecture refs, setup instructions | `README.md` | Low |
| 6.2 | Update all docs/ files: replace "Kuzu" → "LadybugDB", update code examples, update env var docs | 20+ doc files (see §2.6) | Low (mechanical) |
| 6.3 | Add migration guide: `docs/migration/KUZU_TO_LADYBUG.md` documenting the data migration procedure for deployed instances | New file | Low |
| 6.4 | Update `docs/conf.py` if it references kuzu | `docs/conf.py` | Trivial |

### Phase 7: Data Migration & Integration Testing (Day 4)

| # | Task | Owner | Gate |
|---|------|-------|------|
| 7.1 | Export existing Kuzu data: `kuzu ./data/kuzu -c "EXPORT DATABASE '/tmp/kuzu_export/';"` | Operator | Export verified |
| 7.2 | Import to LadybugDB: `lbug ./data/ladybug_graph.lbdb -c "IMPORT DATABASE '/tmp/kuzu_export/';"` | Operator | Import verified |
| 7.3 | Verify schema: `lbug ./data/ladybug_graph.lbdb -c "CALL show_tables() RETURN *;"` — check all 8 tables present | Operator | 8 tables confirmed |
| 7.4 | Verify row counts: `MATCH (n) RETURN count(n)` for each node/rel table | Operator | Counts match |
| 7.5 | Run full integration test suite against migrated database | Agent | All tests pass |
| 7.6 | Run `server/init_db.py` to verify schema init on fresh DB | Agent | Init succeeds |
| 7.7 | Start FastAPI server locally, hit health endpoint, verify `ladybug_path` in response | Agent | Server healthy |

### Phase 8: Uplift Opportunities (Post-Migration — Optional)

These are LadybugDB features not available in Kuzu 0.10.0 that could improve the codebase:

| # | Feature | Benefit | Effort |
|---|---------|---------|--------|
| 8.1 | **Native `AsyncConnection`** — Replace custom `GraphConnectionPool` (graph_database.py:57-121) with LadybugDB's built-in `AsyncConnection` (`lb.AsyncConnection(db, max_concurrent_queries=10)`) | Eliminates ~65 lines of thread-pool boilerplate; native async, better throughput | Medium |
| 8.2 | **Native JSON type** — Replace `data STRING` (storing JSON as strings) with `data JSON` in node/rel tables | Type-safe JSON queries (`u.data.name`), no manual parse | Low (schema change) |
| 8.3 | **Parquet/Arrow storage** — Use `WITH (storage='path/to/file.parquet')` for cold data | Columnar analytics on graph data without import | Medium |
| 8.4 | **DataFrame interop** — Use `result.get_as_df()` / `get_as_pl()` / `get_as_arrow()` in analytics routes | Eliminates manual `_process_row()` / `_serialize_value()` (graph_database.py:325-343) | Low |
| 8.5 | **`read_only` Database param** — Wire `read_only` into `Database()` constructor for analytics replicas | Proper read-only mode, multi-reader | Low |
| 8.6 | **`debug_enable_multi_writes`** — Enable MVCC for concurrent write workloads | Concurrent writers (was `enable_concurrent_writes` in Kuzu) | Low (CALL setting) |
| 8.7 | **UDFs** — Register Python UDFs for custom analytics (centrality, similarity) | Move graph algorithms into the query engine | Medium |
| 8.8 | **Torch Geometric integration** — LadybugDB ships `torch_geometric_feature_store.py` / `graph_store.py` | Direct PyG integration for GNN workloads | Medium |

---

## 5. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Storage format incompatibility — Kuzu data not readable by LadybugDB | **Certain** | High | Phase 7 export/import migration; test on backup copy first |
| R2 | `Connection(db, num_threads=N)` constructor change breaks runtime | High | Medium | Phase 1.2 explicit fix; integration tests (Phase 4.5) |
| R3 | Env var rename breaks deployed instances without migration | Medium | High | Keep `KUZU_DB_PATH` as deprecated alias; document in migration guide |
| R4 | Docker volume rename loses data in production | Medium | Critical | Phase 7.1 backup before volume swap; test on staging first |
| R5 | `CALL show_tables()` result schema differs | Low | Low | Phase 7.3 verification; LadybugDB docs confirm same structure (name, type) |
| R6 | `conn.execute(query, parameters)` — parameter binding syntax differs | Low | Medium | LadybugDB Python API confirms `parameters: dict` support (verified in source) |
| R7 | CLI `lbug` binary not available in Docker images | Medium | Medium | Add `brew install ladybug` or `pip install ladybug` to Dockerfiles |
| R8 | Existing Codon modules (`codon/graph_bridge.py`, `codon/data_bridge.py`) reference Kuzu | Low | Low | Check and update if they call kuzu API directly (likely indirect only) |

---

## 6. Verification Checklist (Definition of Done)

- [ ] `grep -ri "kuzu" --include="*.py" .` returns 0 results (excluding migration guide)
- [ ] `grep -ri "kuzu" --include="*.mjs" --include="*.ts" .` returns 0 results
- [ ] `grep -ri "kuzu" --include="*.yml" --include="*.yaml" --include="*.sh" .` returns 0 results (excluding migration guide)
- [ ] `pip install -r requirements.txt` installs `ladybug==0.21.2`, no `kuzu` package
- [ ] `python -c "import ladybug as lb; db = lb.Database(':memory:'); conn = lb.Connection(db); conn.execute('CREATE NODE TABLE N(id INT64, PRIMARY KEY(id))'); conn.execute('CREATE (n:N {id: 1})'); print(conn.execute('MATCH (n:N) RETURN n.id').get_all())"` prints `[(1,)]`
- [ ] `pytest tests/ -v` — all tests pass
- [ ] FastAPI server starts, health endpoint returns `"ladybug_path"` key
- [ ] `CALL show_tables() RETURN *` returns all 8 schema tables
- [ ] Data migration from Kuzu export verified (row counts match)
- [ ] Docker images build successfully
- [ ] Documentation updated — no "Kuzu" references in user-facing docs

---

## 7. Estimated Effort

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 0: Pre-Flight | 0.5 day | Agent + Operator |
| Phase 1: Core Python | 1 day | Agent |
| Phase 2: Dependencies | 0.5 day | Agent |
| Phase 3: Docker/Infra | 1 day | Agent |
| Phase 4: Tests | 1 day | Agent |
| Phase 5: CLI | 0.5 day | Agent |
| Phase 6: Docs | 0.5 day | Agent |
| Phase 7: Data Migration | 1 day | Agent + Operator |
| **Total (core migration)** | **~5 days** | |
| Phase 8: Uplift (optional) | 2-4 days | Agent |

---

## 8. Recommendations

1. **Approve Phases 0-7** as a single migration PR. The change is mechanical and low-risk given the API compatibility.
2. **Defer Phase 8 (uplift)** to a follow-up PR. The `AsyncConnection` replacement (§8.1) is the highest-value uplift and should be prioritised.
3. **Maintain backward-compat env var alias** (`KUZU_DB_PATH` → `LADYBUG_DB_PATH`) for one release cycle to ease deployment transitions.
4. **Test on staging first.** Run the full Phase 7 data migration on a staging instance before touching production.
5. **Consider renaming files** `kuzu_analytics.py` → `ladybug_analytics.py` and `kuzu_backup.py` → `ladybug_backup.py` for consistency — but this requires updating all import sites and is optional in the first pass.

---

*Prepared by Hermes Agent. Awaiting approval to proceed.*
