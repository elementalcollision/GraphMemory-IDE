#!/usr/bin/env python3
"""Phase 6 batch edit: Kuzu -> LadybugDB across documentation."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

FILES = [
    "README.md",
    "docs/analytics/README.md",
    "docs/api/API_GUIDE.md",
    "docs/architecture/ARCHITECTURE_OVERVIEW.md",
    "docs/architecture/CODE_PATHS.md",
    "docs/architecture/README.md",
    "docs/conf.py",
    "docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md",
    "docs/development/COLOR_PALETTE_GUIDE.md",
    "docs/development/DEVELOPER_GUIDE.md",
    "docs/development/DOCUMENTATION.md",
    "docs/ide-plugins/PLUGIN_DEVELOPMENT.md",
    "docs/monitoring/MONITORING_GUIDE.md",
    "docs/operations/OPERATIONS.md",
    "docs/operations/PERFORMANCE_TUNING.md",
    "docs/operations/README.md",
    "docs/project/CONTRIBUTING.md",
    "docs/project/PRD - GraphMemory-IDE - Combined.md",
    "docs/project/SECURITY.md",
    "docs/user-guides/USER_GUIDE.md",
    "docs/user-guides/advanced-configuration.md",
    "docs/user-guides/getting-started.md",
    "docs/user-guides/graph-operations.md",
]

SWEEPS = [
    # versions / installs first
    ("Kuzu 0.10+", "LadybugDB 0.21+"),
    ("Kuzu 0.10", "LadybugDB 0.21.2"),
    ("kuzu==0.10.0", "ladybug==0.21.2"),
    ("kuzu==", "ladybug=="),
    ("pip install kuzu", "pip install ladybug"),
    ("brew install kuzu", "brew install ladybug"),
    ("npm install kuzu", "npm install @ladybugdb/core"),
    ("kuzu/kuzu:latest", "ghcr.io/ladybugdb/api-server:latest"),
    # env vars / paths / modules / volumes
    ("KUZU_DB_PATH", "LADYBUG_DB_PATH"),
    ("KUZU_READ_ONLY", "LADYBUG_READ_ONLY"),
    ("KUZU_DATA_PATH", "LADYBUG_DATA_PATH"),
    ("kuzu_analytics", "ladybug_analytics"),
    ("kuzu_backup", "ladybug_backup"),
    ("kuzu_tenant_manager", "ladybug_tenant_manager"),
    ("kuzu_queries", "ladybug_queries"),
    ("kuzu-data", "ladybug-data"),
    ("kuzu_data", "ladybug_data"),
    ("./data/kuzu", "./data/ladybug"),
    ("./backups/kuzu", "./backups/ladybug"),
    ("/app/data/kuzu", "/app/data/ladybug"),
    # python API
    ("import kuzu\n", "import ladybug as lb\n"),
    ("kuzu.Database", "lb.Database"),
    ("kuzu.Connection", "lb.Connection"),
    # CLI binary (bare + backticked, after installs handled)
    ("'kuzu'", "'lbug'"),
    ("`kuzu`", "`lbug`"),
    # prose
    ("KuzuDB", "LadybugDB"),
    ("Kuzu GraphDB", "LadybugDB"),
    ("Kuzu graph database", "LadybugDB graph database"),
    ("Kuzu", "LadybugDB"),
    ("kuzu", "ladybug"),
    ("KUZU", "LADYBUG"),
]

EXPLICIT = {
    # PERFORMANCE_TUNING.md: stale kuzu kwarg + unsupported secondary indexes
    "docs/operations/PERFORMANCE_TUNING.md": [(
        """    db = kuzu.Database(
        db_path,
        buffer_pool_size=1024 * 1024 * 1024,  # 1GB buffer pool
        max_num_threads=8,  # Use all CPU cores
        enable_compression=True
    )
    
    conn = kuzu.Connection(db)
    
    # Create performance indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_created_at ON Memory(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON Memory(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_tags ON Memory(tags)")""",
        """    db = lb.Database(
        db_path,
        buffer_pool_size=1024 * 1024 * 1024,  # 1GB buffer pool
        max_num_threads=8,  # Use all CPU cores
        compression=True
    )
    
    conn = lb.Connection(db)
    conn.init_connection()
    
    # NOTE (LadybugDB 0.21.x): HASH/ART indexes are only supported on PRIMARY
    # KEYS, and a PK hash index is created automatically on every node table.
    # Secondary-property indexes (e.g. on Memory(type)) are NOT supported —
    # LadybugDB maintains automatic zone maps (min/max pruning) on all columns,
    # which serve the same filter workloads. If a manual index is ever needed:
    #   CREATE INDEX <name> FOR (<alias>:<Table>) ON (<alias>.<pk_property>);""",
    )],
    # graph-operations.md: old openCypher index syntax + unsupported FULLTEXT
    "docs/user-guides/graph-operations.md": [(
        """```cypher
// Create indexes for frequently queried properties
CREATE INDEX ON :Memory(type);
CREATE INDEX ON :Memory(created_at);
CREATE FULLTEXT INDEX memory_content FOR (m:Memory) ON EACH [m.content];
```""",
        """```cypher
// LadybugDB 0.21.x: secondary-property and FULLTEXT indexes are NOT supported.
// Primary-key hash indexes are created automatically on every node table, and
// automatic zone maps (min/max pruning) accelerate filters on all other
// properties. Manual PK index DDL, if ever needed:
CREATE INDEX idx_memory_pk FOR (m:Memory) ON (m.id);
// For full-text matching, use string functions in the WHERE clause instead:
MATCH (m:Memory) WHERE m.content CONTAINS 'search_term' RETURN m;
```""",
    )],
    # ARCHITECTURE_OVERVIEW.md: unverified HNSW claim for LadybugDB
    "docs/architecture/ARCHITECTURE_OVERVIEW.md": [(
        "| Graph Database | Kuzu 0.10 with Cypher queries, HNSW vector indexes | `server/graph_database.py` |",
        "| Graph Database | LadybugDB 0.21.2 with Cypher queries, automatic PK hash indexes + zone maps, vector similarity via `array_cosine_similarity` | `server/graph_database.py` |",
    )],
}

for f in FILES:
    p = ROOT / f
    text = p.read_text()
    for old, new in EXPLICIT.get(f, []):
        if old not in text:
            print(f"ABORT: explicit pattern not found in {f}:\n  {old[:100]!r}")
            sys.exit(1)
        text = text.replace(old, new)
    for old, new in SWEEPS:
        text = text.replace(old, new)
    if re.search(r"kuzu|Kuzu|KUZU", text):
        for l in text.splitlines():
            if re.search(r"kuzu|Kuzu|KUZU", l):
                print("   leftover:", l.strip()[:100])
        print(f"ABORT: leftover kuzu refs in {f}")
        sys.exit(1)
    p.write_text(text)
    print(f"  OK  {f}")

print("\nPhase 6 doc edits complete.")
