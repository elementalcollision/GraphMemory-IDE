#!/usr/bin/env python3
"""Phase 1 batch edit: Kuzu -> LadybugDB across server/ source files.
Every replacement is asserted; any drift aborts before writing."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

# Ordered generic sweeps applied AFTER file-specific edits (longest/most-specific first).
SWEEPS = [
    ("KuzuAnalyticsEngine", "LadybugAnalyticsEngine"),
    ("TestKuzuAnalyticsEngine", "TestLadybugAnalyticsEngine"),
    ("KuzuTenantManager", "LadybugTenantManager"),
    ("KuzuQueryRequest", "LadybugQueryRequest"),
    ("KuzuQueryResult", "LadybugQueryResult"),
    ("KuzuBackupType", "LadybugBackupType"),
    ("KuzuBackupStatus", "LadybugBackupStatus"),
    ("KuzuBackupMetadata", "LadybugBackupMetadata"),
    ("KuzuBackupManager", "LadybugBackupManager"),
    ("KuzuQuery", "LadybugQuery"),
    ("KUZU_DATABASE", "LADYBUG_DATABASE"),
    ("KUZU_DB_PATH", "LADYBUG_DB_PATH"),
    ("KUZU_READ_ONLY", "LADYBUG_READ_ONLY"),
    ("Kuzu GraphDB", "LadybugDB"),
    ("KuzuDB", "LadybugDB"),
    ("kuzu.Database", "lb.Database"),
    ("kuzu.Connection", "lb.Connection"),
    ("kuzu_analytics", "ladybug_analytics"),
    ("kuzu_backup", "ladybug_backup"),
    ("kuzu_tenant_manager", "ladybug_tenant_manager"),
    ("kuzu_queries", "ladybug_queries"),
    ("idx_kuzu", "idx_ladybug"),
    ("ck_kuzu", "ck_ladybug"),
    ("collect_kuzu_metrics", "collect_ladybug_metrics"),
    ("_check_kuzu_health", "_check_ladybug_health"),
    ("_transform_kuzu_query", "_transform_ladybug_query"),
    ("_execute_kuzu_query", "_execute_ladybug_query"),
    ("setup_kuzu_manager", "setup_ladybug_manager"),
    ("test_kuzu_performance_monitoring", "test_ladybug_performance_monitoring"),
    ("kuzu_fs_backup", "ladybug_fs_backup"),
    ("kuzu_export", "ladybug_export"),
    ("kuzu_query_latency", "ladybug_query_latency"),
    ("kuzu_database", "ladybug_database"),
    ("kuzu_manager", "ladybug_manager"),
    ("kuzu_connection", "ladybug_connection"),
    ("kuzu_conn", "ladybug_conn"),
    ("kuzu_db", "ladybug_db"),
    ("kuzu_result", "ladybug_result"),
    ("existing_kuzu", "existing_ladybug"),
    ("kuzu_to_create", "ladybug_to_create"),
    ("kuzu_metrics", "ladybug_metrics"),
    ("kuzu_time", "ladybug_time"),
    ("kuzu_backup", "ladybug_backup"),
    ("kuzu_test", "ladybug_test"),
    ("kuzu_path", "ladybug_path"),
    ("Kuzu", "LadybugDB"),
    ("kuzu", "ladybug"),
    ("KUZU", "LADYBUG"),
]

edited = []

def apply(path, specific, sweeps=True, allow_kuzu=False):
    """specific: list of (old, new) — each must occur at least once."""
    p = ROOT / path
    text = p.read_text()
    for old, new in specific:
        if old not in text:
            print(f"ABORT: pattern not found in {path}:\n  {old[:120]!r}")
            sys.exit(1)
        text = text.replace(old, new)
    if sweeps:
        for old, new in SWEEPS:
            text = text.replace(old, new)
    if not allow_kuzu and re.search(r"kuzu|Kuzu|KUZU", text):
        leftovers = [l for l in text.splitlines() if re.search(r"kuzu|Kuzu|KUZU", l)]
        print(f"ABORT: leftover kuzu refs in {path}:")
        for l in leftovers[:5]:
            print("   ", l.strip()[:100])
        sys.exit(1)
    p.write_text(text)
    edited.append(path)
    print(f"  OK  {path}")

# ---------------------------------------------------------------
# 1. server/graph_database.py
# ---------------------------------------------------
apply("server/graph_database.py", [
    ("""try:
    import kuzu
except ImportError:
    kuzu = None
    logging.warning("Kuzu not installed. Graph database features disabled.")""",
     """try:
    import ladybug as lb
except ImportError:
    lb = None
    logging.warning("LadybugDB not installed. Graph database features disabled.")"""),
    ("Provides production-ready integration with Kuzu graph database including:",
     "Provides production-ready integration with LadybugDB graph database including:"),
    ('"""Configuration for Kuzu graph database"""',
     '"""Configuration for LadybugDB graph database"""'),
    ('database_path: str = "./data/kuzu_graph"',
     'database_path: str = "./data/ladybug_graph.lbdb"'),
    ('"""Thread-safe connection pool for Kuzu database"""',
     '"""Thread-safe connection pool for LadybugDB database"""'),
    ("""                conn = kuzu.Connection(self.database, num_threads=2)""",
     """                # LadybugDB: Connection(db, num_threads=N) is not supported.
                # Use Connection(db) + init_connection() + set_max_threads_for_exec(N).
                conn = lb.Connection(self.database)
                conn.init_connection()
                conn.set_max_threads_for_exec(2)"""),
    ("""        if kuzu is None:
            logger.error("Kuzu not available. Cannot initialize graph database.")""",
     """        if lb is None:
            logger.error("LadybugDB not available. Cannot initialize graph database.")"""),
    ("""            self.database = kuzu.Database(""",
     """            self.database = lb.Database("""),
    ("""    def _create_indexes(self) -> None:
        \"\"\"Create indexes for better query performance\"\"\"
        index_queries = [
            "CREATE INDEX IF NOT EXISTS user_email_idx ON User(email)",
            "CREATE INDEX IF NOT EXISTS project_owner_idx ON Project(owner_id)",
            "CREATE INDEX IF NOT EXISTS memory_type_idx ON Memory(memory_type)",
            "CREATE INDEX IF NOT EXISTS memory_source_idx ON Memory(source_table, source_id)",
        ]""",
     """    def _create_indexes(self) -> None:
        \"\"\"Create indexes for better query performance.

        LadybugDB 0.21.x notes (Kuzu -> LadybugDB migration):
        - HASH/ART indexes are only supported on PRIMARY KEYS, and a PK hash
          index is created automatically on every node table
          (`enable_default_hash_index=true` by default), so no manual PK
          indexes are needed.
        - Secondary-property indexes (e.g. on User(email)) are NOT supported.
          LadybugDB maintains automatic zone maps (min/max pruning) on all
          columns, which serve the same filter workloads.
        - Index DDL (if ever needed) is now:
          CREATE INDEX <name> FOR (<alias>:<Table>) ON (<alias>.<property>)
        \"\"\"
        index_queries: List[str] = []"""),
])

# ---------------------------------------------------------------
# 2. server/main.py
# ---------------------------------------------------
apply("server/main.py", [
    ("import kuzu\n", "import ladybug as lb\n"),
    ("""        app.state.kuzu_db = kuzu.Database(kuzu_db_path)  # type: ignore
        app.state.kuzu_conn = kuzu.Connection(app.state.kuzu_db)  # type: ignore""",
     """        app.state.ladybug_db = lb.Database(ladybug_db_path)  # type: ignore
        app.state.ladybug_conn = lb.Connection(app.state.ladybug_db)  # type: ignore"""),
    # LadybugDB: camelCase iteration not supported — use snake_case.
    ("while result.hasNext():", "while result.has_next():"),
    ("row = result.getNext()", "row = result.get_next()"),
    # LadybugDB renamed list_cosine_similarity -> array_cosine_similarity.
    ("list_cosine_similarity(n.{req.embedding_field}, $query_embedding)",
     "array_cosine_similarity(n.{req.embedding_field}, $query_embedding)"),
])

# ---------------------------------------------------------------
# 3. server/init_db.py — full rewrite (keeps KUZU_DB_PATH env fallback)
# ---------------------------------------------------
init_db = '''#!/usr/bin/env python3
"""
Database initialization script for GraphMemory-IDE MCP Server.
Sets up the LadybugDB database with required node types and schema.
"""

import ladybug as lb
import os

def init_database() -> None:
    """Initialize the LadybugDB database with required schema."""

    # Get database path (LADYBUG_DB_PATH preferred; KUZU_DB_PATH kept as a
    # deprecated fallback for existing deployments mid-migration)
    LADYBUG_DB_PATH = os.environ.get("LADYBUG_DB_PATH") or os.environ.get("KUZU_DB_PATH", "./data")

    print(f"Initializing LadybugDB database at: {LADYBUG_DB_PATH}")

    # Create database and connection
    db = lb.Database(LADYBUG_DB_PATH)
    conn = lb.Connection(db)

    try:
        # Create node table for TelemetryEvent if it doesn't exist
        # In LadybugDB, we need to create node tables explicitly
        print("Creating TelemetryEvent node table...")
        conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS TelemetryEvent(
                event_type STRING,
                timestamp STRING,
                user_id STRING,
                session_id STRING,
                data STRING,
                PRIMARY KEY(timestamp)
            )
        """)

        # Create a simple test node to verify the table works
        print("Creating test TelemetryEvent node...")
        conn.execute("""
            CREATE (e:TelemetryEvent {
                event_type: 'init_test',
                timestamp: '2025-01-27T12:41:19',
                user_id: 'system',
                session_id: 'init',
                data: '{"action": "database_initialization"}'
            })
        """)

        # Verify the node was created
        result = conn.execute("MATCH (e:TelemetryEvent) WHERE e.event_type = 'init_test' RETURN e")
        if isinstance(result, list):
            result = result[0]

        count = 0
        while result.has_next():
            result.get_next()
            count += 1

        print(f"Database initialization successful! Created {count} test node(s).")

        # Clean up test node
        conn.execute("MATCH (e:TelemetryEvent) WHERE e.event_type = 'init_test' DELETE e")
        print("Cleaned up test node.")

    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise

    finally:
        # Close connection
        conn.close()
        print("Database initialization complete.")

if __name__ == "__main__":
    init_database()
'''
(ROOT / "server/init_db.py").write_text(init_db)
edited.append("server/init_db.py")
print("  OK  server/init_db.py (rewritten; KUZU_DB_PATH env fallback retained)")

# ---------------------------------------------------------------
# 4. server/analytics/engine.py
# ---------------------------------------------------
apply("server/analytics/engine.py", [
    ("import kuzu\n", "import ladybug as lb\n"),
    # Kuzu.Connection had no connect(); LadybugDB Connection initialises via
    # init_connection() (idempotent, called automatically by execute()).
    ("""            # Initialize database connection
            await self.kuzu_conn.connect()""",
     """            # Initialize database connection (idempotent; execute() also
            # initialises lazily, but make it explicit at engine startup)
            if hasattr(self.ladybug_conn, 'init_connection'):
                self.ladybug_conn.init_connection()"""),
])

# ---------------------------------------------------------------
# 5-23: remaining files — sweeps cover everything
# ---------------------------------------------------
for f in [
    "server/analytics/kuzu_analytics.py",
    "server/backup/kuzu_backup.py",
    "server/backup/backup_orchestrator.py",
    "server/analytics_routes.py",
    "server/dashboard/analytics_client.py",
    "server/data_seeding.py",
    "server/database_models.py",
    "server/database_sync.py",
    "server/migrations.py",
    "server/models.py",
    "server/health_monitoring.py",
    "server/collaboration/vector_consistency.py",
    "server/collaboration/fastapi_tenant_middleware.py",
    "server/analytics/service_registry.py",
    "server/analytics/monitoring.py",
    "server/analytics/__init__.py",
    "server/monitoring/production_performance_optimizer.py",
    # Tests — mechanical renames only so collection doesn't break on renamed
    # modules/classes; deeper test remediation is Phase 4.
    "server/tests/benchmark_analytics.py",
    "server/tests/test_performance_analytics.py",
    "server/tests/test_analytics_integration.py",
    "server/tests/test_analytics_client.py",
    "server/collaboration/test_tenant_isolation.py",
    "server/collaboration/test_rbac_integration.py",
]:
    apply(f, [])

# ---------------------------------------------------------------
# 24. server/core/config.py — explicit field renames + path defaults
# ---------------------------------------------------
apply("server/core/config.py", [
    ("""    # Kuzu Graph Database
    KUZU_DB_PATH: str = "./data/kuzu"
    KUZU_READ_ONLY: bool = False""",
     """    # LadybugDB Graph Database (Kuzu successor)
    LADYBUG_DB_PATH: str = "./data/ladybug.lbdb"
    LADYBUG_READ_ONLY: bool = False"""),
])

# ---------------------------------------------------------------
# File renames (git mv)
# ---------------------------------------------------
import subprocess
renames = [
    ("server/analytics/kuzu_analytics.py", "server/analytics/ladybug_analytics.py"),
    ("server/backup/kuzu_backup.py", "server/backup/ladybug_backup.py"),
    ("server/collaboration/kuzu_tenant_manager.py", "server/collaboration/ladybug_tenant_manager.py"),
]
for old, new in renames:
    r = subprocess.run(["git", "mv", old, new], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ABORT: git mv {old} -> {new} failed: {r.stderr}")
        sys.exit(1)
    print(f"  OK  renamed {old} -> {new}")
    edited.append(new)

print(f"\n{len(edited)} files edited/renamed.")
