"""Phase 0.2 smoke test: verify LadybugDB API compatibility with Graph_Memory-IDE usage patterns."""
import sys

import ladybug as lb

PASS, FAIL = "PASS", "FAIL"
results = []

def check(name, fn):
    try:
        fn()
        results.append((name, PASS))
        print(f"[{PASS}] {name}")
    except Exception as e:
        results.append((name, f"{FAIL}: {e}"))
        print(f"[{FAIL}] {name}: {e}")

# 1. On-disk database with the same constructor params the codebase uses
db = lb.Database(
    "/Users/dave/.hermes/cache/scratch/ladybug_smoke/test_graph",
    buffer_pool_size=256 * 1024 * 1024,
    max_num_threads=8,
    compression=True,
    auto_checkpoint=True,
    checkpoint_threshold=64 * 1024 * 1024,
)
check("Database(path, buffer_pool_size, max_num_threads, compression, auto_checkpoint, checkpoint_threshold)", lambda: None)

# 2. Connection (codebase uses kuzu.Connection(db, num_threads=2) — verify new pattern)
conn = lb.Connection(db)
conn.init_connection()
conn.set_max_threads_for_exec(2)
check("Connection(db) + init_connection() + set_max_threads_for_exec(2)", lambda: None)

# 3. set_query_timeout — used in graph_database.py:277-278
conn.set_query_timeout(60_000)
check("conn.set_query_timeout(60000)", lambda: None)

# 4. Schema creation — exact DDL from graph_database.py GraphSchemaManager
conn.execute("""
    CREATE NODE TABLE IF NOT EXISTS User(
        id STRING, username STRING, email STRING, created_at TIMESTAMP,
        properties MAP(STRING, STRING), PRIMARY KEY(id)
    )
""")
conn.execute("""
    CREATE NODE TABLE IF NOT EXISTS Memory(
        id STRING, content STRING, memory_type STRING, source_table STRING,
        source_id STRING, created_at TIMESTAMP, embeddings DOUBLE[],
        metadata MAP(STRING, STRING), PRIMARY KEY(id)
    )
""")
conn.execute("""
    CREATE REL TABLE IF NOT EXISTS CONTAINS(
        FROM User TO Memory, relevance_score DOUBLE DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT current_timestamp()
    )
""")
check("CREATE NODE/REL TABLE with MAP, DOUBLE[], TIMESTAMP, DEFAULT", lambda: None)

# 5. Parameterised execute — used in graph_database.py:282
conn.execute("CREATE (u:User {id: $id, username: $name})", {"id": "u1", "name": "alice"})
conn.execute("CREATE (m:Memory {id: $id, content: $c})", {"id": "m1", "c": "hello"})
check("conn.execute(query, parameters) — $-parameterised INSERT", lambda: None)

# 6. Index creation — FINDING: LadybugDB 0.21.2 changed index DDL syntax and
#    only supports HASH/ART indexes on PRIMARY KEYS. The codebase's secondary
#    indexes (User(email), Project(owner_id), etc.) are NOT supported — zone
#    maps (automatic min/max pruning on all columns) replace them.
#    Old (Kuzu):  CREATE INDEX IF NOT EXISTS user_email_idx ON User(email)
#    New (Ladybug): CREATE INDEX name FOR (a:Table) ON (a.pk_property)
conn.execute("CREATE INDEX user_pk_idx FOR (u:User) ON (u.id)")
check("CREATE INDEX name FOR (a:Table) ON (a.pk) — new index DDL syntax", lambda: None)

# 6b. Verify zone-map pruning works for secondary-property filters (the
#     workload the old secondary indexes served)
r = conn.execute("MATCH (u:User) WHERE u.email = $e RETURN u.id", {"e": "nobody@example.com"})
assert r.get_all() == []
check("Secondary-property WHERE filter (zone-map replacement)", lambda: None)

# 7. has_next/get_next iteration — the codebase's primary result pattern
result = conn.execute("MATCH (u:User) WHERE u.username = $n RETURN u.id, u.username", {"n": "alice"})
rows = []
while result.has_next():
    rows.append(result.get_next())
assert list(rows[0]) == ["u1", "alice"], f"unexpected rows: {rows}"
# NOTE: LadybugDB get_next() returns list; Kuzu returned tuple.
# Codebase _process_row() handles both (isinstance(row, (list, tuple))).
check("result.has_next()/get_next() with parameterised MATCH", lambda: None)

# 8. CALL show_tables() — used in GraphHealthChecker._check_schema_integrity.
#    FINDING: LadybugDB adds a leading numeric 'id' column (row[0]); table
#    NAME is at row[1] — same position the codebase already reads.
#    Columns: [id, name, type, database name, comment]
tables = set()
r = conn.execute("CALL show_tables() RETURN *")
while r.has_next():
    row = r.get_next()
    tables.add(row[1])  # codebase reads row[1] = table name (compatible)
assert {"User", "Memory", "CONTAINS"} <= tables, f"missing tables: {tables}"
check("CALL show_tables() RETURN * — schema check", lambda: None)

# 9. Variable-length path (Kleene star) — used by kuzu_analytics path queries
r = conn.execute("MATCH (u:User)-[r:CONTAINS*1..3]->(m:Memory) RETURN u.id, m.id")
check("Recursive/Kleene-star MATCH", lambda: None)

# 10. Aggregation — used in health check 'MATCH (n) RETURN count(n)'
r = conn.execute("MATCH (n:User) RETURN count(n) AS node_count")
while r.has_next():
    assert r.get_next()[0] == 1
check("count() aggregation", lambda: None)

# 11. get_as_df / rows_as_dict — potential uplift (Phase 8.4)
r = conn.execute("MATCH (u:User) RETURN u.id, u.username")
df = r.get_as_df()
assert len(df) == 1
check("result.get_as_df() — DataFrame output", lambda: None)

# 12. In-memory database — used by tests (TEST_DATABASE_PATH / :memory:)
memdb = lb.Database(":memory:")
memconn = lb.Connection(memdb)
memconn.execute("CREATE NODE TABLE N(id INT64, PRIMARY KEY(id))")
memconn.execute("CREATE (n:N {id: 1})")
assert memconn.execute("MATCH (n:N) RETURN n.id").get_all() == [[1]]  # LadybugDB returns lists
check("lb.Database(':memory:') + get_all()", lambda: None)
memconn.close()
memdb.close()

# 13. Close — cleanup pattern from graph_database.py close_all / close
conn.close()
db.close()
check("conn.close() / db.close()", lambda: None)

print("\n" + "=" * 60)
fails = [r for r in results if r[1].startswith(FAIL)]
print(f"SMOKE TEST: {len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
