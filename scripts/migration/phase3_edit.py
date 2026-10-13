#!/usr/bin/env python3
"""Phase 3 batch edit: Kuzu -> LadybugDB across Docker/infra (OrbStack), k8s, deploy, monitoring."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

SWEEPS = [
    # Specific first
    ("KUZU_DATABASE_PATH", "LADYBUG_DATABASE_PATH"),
    ("KUZU_DATA_PATH", "LADYBUG_DATA_PATH"),
    ("KUZU_DB_PATH", "LADYBUG_DB_PATH"),
    ("KUZU_READ_ONLY", "LADYBUG_READ_ONLY"),
    ("kuzu_database_path", "ladybug_database_path"),
    ("get_kuzu_path", "get_ladybug_path"),
    ("check_kuzu", "check_ladybug"),
    ("restore_kuzu", "restore_ladybug"),
    ("backup-kuzu", "backup-ladybug"),
    ("graphmemory-kuzu", "graphmemory-ladybug"),
    ("kuzu-data", "ladybug-data"),
    ("kuzu_data", "ladybug_data"),
    ("kuzu_path", "ladybug_path"),
    # Generic last
    ("Kuzu", "LadybugDB"),
    ("kuzu", "ladybug"),
    ("KUZU", "LADYBUG"),
]

def apply(path, specific=(), check=True):
    p = ROOT / path
    text = p.read_text()
    for old, new in specific:
        if old not in text:
            print(f"ABORT: pattern not found in {path}:\n  {old[:120]!r}")
            sys.exit(1)
        text = text.replace(old, new)
    for old, new in SWEEPS:
        text = text.replace(old, new)
    if check and re.search(r"kuzu|Kuzu|KUZU", text):
        for l in text.splitlines():
            if re.search(r"kuzu|Kuzu|KUZU", l):
                print("   leftover:", l.strip()[:100])
        print(f"ABORT: leftover kuzu refs in {path}")
        sys.exit(1)
    p.write_text(text)
    print(f"  OK  {path}")

# ---------------------------------------------------------------
# 1. docker/production/docker-compose.yml — rewrite the standalone
#    kuzu server service to the LadybugDB api-server image, then sweep
# ---------------------------------------------------------------
apply("docker/production/docker-compose.yml", specific=[
    ("""  # Kuzu graph database
  kuzu:
    image: kuzu/kuzu:latest
    container_name: graphmemory-kuzu
    restart: unless-stopped
    
    volumes:
      - kuzu_data:/kuzu/data
      - ./kuzu/config:/kuzu/config:ro
      - ./kuzu/init:/kuzu/init:ro
    
    networks:
      - graphmemory_network
    
    healthcheck:
      test: ["CMD-SHELL", "test -f /kuzu/data/.healthy || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5""",
     """  # LadybugDB graph database (Kuzu successor) — official api-server image.
  # NOTE: the app embeds LadybugDB in-process; this sidecar serves external/
  #  admin access. Mount the data dir at /database; db file defaults to
  #  database.lbdb (override with LBUG_FILE). Validate image tag on first
  #  deployment and pin a version in production.
  ladybug:
    image: ghcr.io/ladybugdb/api-server:latest
    container_name: graphmemory-ladybug
    restart: unless-stopped
    environment:
      - MODE=READ_WRITE
    
    volumes:
      - ladybug_data:/database
    
    networks:
      - graphmemory_network
    
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O /dev/null http://localhost:8000/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5"""),
])

# ---------------------------------------------------------------
# 2. Everything else — sweeps only
# ---------------------------------------------------------------
for f in [
    "docker/mcp-server/Dockerfile",
    "docker/Dockerfile.codon",
    "docker/docker-compose.yml",
    "docker/production/docker-compose.prod.yml",
    "docker/backup-volumes.sh",
    "docker/production/scripts/analytics-entrypoint.sh",
    "docker/production/scripts/streamlit-entrypoint.sh",
    "docker/production/scripts/fastapi-entrypoint.sh",
    "docker/production/scripts/backup/backup.sh",
    "docker/production/scripts/backup/restore.sh",
    "deploy/scripts/production_deploy.sh",
    "deploy/digitalocean/env_config.py",
    "deploy/digitalocean/app.yaml",
    "deploy/digitalocean/staging-app.yaml",
    "kubernetes/manifests/deployments.yaml",
    "monitoring/resource-monitor.sh",
]:
    apply(f)

print("\nPhase 3 edits complete.")
