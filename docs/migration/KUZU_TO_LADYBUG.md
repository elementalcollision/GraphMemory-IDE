# Migration Guide: Kuzu → LadybugDB

This guide covers migrating a **deployed** GraphMemory-IDE instance from Kuzu
(0.10.x, abandoned after its acquisition by Apple) to LadybugDB 0.21.2.

The in-repo code migration is complete on the `feature/ladybug-migration`
branch (see `MIGRATION_PLAN_LADYBUG.md` for the full phase history and
verified API differences). This document covers the **operational** steps for
existing deployments.

---

## 1. Why migrate

- KuzuDB's open-source development halted post-acquisition: no new features,
  bug fixes, or security patches.
- LadybugDB is the direct successor: MIT-licensed, actively developed,
  near-1:1 Python API compatibility, same openCypher dialect.

## 2. Before you start

1. **Back up the existing Kuzu database directory** (e.g. `./data/kuzu`):
   ```bash
   tar -czf kuzu_pre_migration_$(date +%Y%m%d_%H%M%S).tar.gz ./data/kuzu
   ```
2. Install the LadybugDB CLI: `brew install ladybug` (provides `lbug`) —
   or `pip install ladybug` for the Python package only.
3. If any pre-migration containers are running, stop them:
   `docker compose -f docker/production/docker-compose.yml stop`.

## 3. Data migration

**Kuzu database files are NOT readable by LadybugDB** (different storage
format; Kuzu stores a directory, LadybugDB a single `.lbdb` file). Migrate
via export/import:

```bash
# 1. Export from Kuzu (requires the kuzu CLI from your previous install)
kuzu ./data/kuzu -c "EXPORT DATABASE '/tmp/kuzu_export/';"

# 2. Import into a new LadybugDB database
mkdir -p ./data
lbug ./data/ladybug.lbdb -c "IMPORT DATABASE '/tmp/kuzu_export/';"

# 3. Verify
lbug ./data/ladybug.lbdb -c "CALL show_tables() RETURN *;"
lbug ./data/ladybug.lbdb -c "MATCH (n) RETURN count(n);"
```

The repo CLI also automates this: `cli/update/database-migrator.mjs`
(`DatabaseMigrator`, default binary `lbug`).

**If you have no production data** (fresh deployments): no export/import is
needed — `server/init_db.py` (or first app start) creates the schema on the
new `./data/ladybug.lbdb` automatically.

## 4. Environment variables

| Old (Kuzu) | New (LadybugDB) |
|------------|-----------------|
| `KUZU_DB_PATH` | `LADYBUG_DB_PATH` |
| `KUZU_READ_ONLY` | `LADYBUG_READ_ONLY` |
| `KUZU_DATABASE_PATH` | `LADYBUG_DATABASE_PATH` |
| `KUZU_DATA_PATH` | `LADYBUG_DATA_PATH` |
| `TEST_KUZU_DB_PATH` | `TEST_LADYBUG_DB_PATH` |

`server/init_db.py` accepts `KUZU_DB_PATH` as a **deprecated fallback** for
one release cycle; all other components read the new names only.

## 5. Docker volumes

The compose volume was renamed `kuzu-data`/`kuzu_data` →
`ladybug-data`/`ladybug_data`. On a host with an existing volume:

```bash
# Back up the old volume
docker run --rm -v docker_kuzu-data:/from -v "$PWD":/to alpine \
  tar -czf /to/kuzu-data-backup.tar.gz -C /from .

# Restore into the new volume after migration (data restored from the
# LadybugDB export/import step, not from the Kuzu volume directly)
```

Note: the old Kuzu volume's contents cannot be mounted as a LadybugDB
database — the data must go through the export/import in §3.

## 6. API differences relevant to operators and client code

Verified against LadybugDB 0.21.2 (full catalogue in
`MIGRATION_PLAN_LADYBUG.md` §3):

| Area | Change |
|------|--------|
| Python package | `pip install ladybug`; `import ladybug as lb` |
| Connection | `Connection(db)` + `init_connection()`; `Connection(db, num_threads=N)` unsupported |
| Index DDL | `CREATE INDEX name FOR (alias:Table) ON (alias.pk)`; **secondary-property and FULLTEXT indexes unsupported** — automatic zone maps replace them |
| Result iteration | `has_next()`/`get_next()` only (snake_case); rows are lists, not tuples |
| Vector similarity | `array_cosine_similarity()` (was `list_cosine_similarity`) |
| Storage | single `.lbdb` file; parent directory must exist (app creates it) |
| Standalone server | `ghcr.io/ladybugdb/api-server:latest` (was `kuzu/kuzu:latest`); pin a version in production |

## 7. Rollback

Until the old Kuzu volume/data is deleted, rollback is:

```bash
git checkout <pre-migration-tag>
tar -xzf kuzu_pre_migration_<timestamp>.tar.gz -C ./
docker compose -f docker/production/docker-compose.yml up -d
```

Once the deprecated `KUZU_DB_PATH` fallback window closes and the old
backups expire, rollback is no longer possible — treat the backup in §2 as
the point of no return.
