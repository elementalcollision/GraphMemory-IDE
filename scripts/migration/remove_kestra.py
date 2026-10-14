#!/usr/bin/env python3
"""Kestra decommission: remove the integration from infra, code, and config.
Historical records (MIGRATION_PLAN_LADYBUG.md, PRD) keep their mentions."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

def edit(path, pairs, must=True):
    p = ROOT / path
    t = p.read_text()
    for old, new in pairs:
        if old not in t:
            if must:
                print(f"ABORT {path}: not found: {old[:80]!r}"); sys.exit(1)
            continue
        t = t.replace(old, new)
    p.write_text(t); print(f"OK  {path}")

def sweep(path, extra=()):
    """Remove all case-insensitive kestra lines/blocks; extra = custom replacements."""
    p = ROOT / path
    t = p.read_text()
    for old, new in extra:
        assert old in t, f"{path}: {old[:80]!r}"
        t = t.replace(old, new)
    # drop whole lines that mention kestra (any case)
    lines = t.splitlines(keepends=True)
    out = []
    for i, l in enumerate(lines):
        if re.search(r"kestra", l, re.I):
            # keep structure: skip line unless it's inside a quoted string we already handled
            continue
        out.append(l)
    t = "".join(out)
    assert not re.search(r"kestra", t, re.I), f"{path}: residual kestra"
    p.write_text(t); print(f"OK  {path} (swept)")

# 1. docker/docker-compose.yml — service block + volumes
edit("docker/docker-compose.yml", [(
    """  kestra:
    image: kestra/kestra:latest
    command: server local -c /app/kestra.yml
    ports:
      - "8081:8080"
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN:-}
    volumes:
      - kestra-data:/app/.kestra
      - kestra-logs:/var/log/kestra
      - ../kestra.yml:/app/kestra.yml:ro
      # Removed Docker socket exposure for security
    networks:
      - memory-net
    # Security hardening
    read_only: true
    security_opt:
      - no-new-privileges:true
      - seccomp:./security/seccomp-profile.json
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /app/.kestra/tmp:noexec,nosuid,size=200m
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    restart: unless-stopped
    user: "1001:1001"  # Non-root user
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

""", ""), (
    """  ladybug-data:
    driver: local
  kestra-data:
    driver: local
  mcp-logs:
    driver: local
  kestra-logs:
    driver: local
""", """  ladybug-data:
    driver: local
  mcp-logs:
    driver: local
""")])

# 2. docker/backup-volumes.sh
edit("docker/backup-volumes.sh", [
    ("for volume in docker_ladybug-data docker_kestra-data; do",
     "for volume in docker_ladybug-data; do"),
    ("        backup_volume \"docker_ladybug-data\"\n        backup_volume \"docker_kestra-data\"",
     "        backup_volume \"docker_ladybug-data\""),
    ("""    backup-kestra)
        backup_volume "docker_kestra-data"
        ;;
""", ""),
])
sweep("docker/backup-volumes.sh")

# 3. cli/commands.mjs
edit("cli/commands.mjs", [
    ("""      {
        name: 'graphmemory/kestra',
        currentTag: '0.15.0',
        tag: '0.16.0',
        size: '180MB',
        changes: ['New workflow features', 'UI improvements']
      }
""", ""),
    ("services: ['mcp-server', 'kestra'],", "services: ['mcp-server'],"),
])

# 4. scripts/deploy-secure.sh
edit("scripts/deploy-secure.sh", [
    ('    KESTRA_CONTAINER=$(docker ps --format "{{.Names}}" | grep kestra | head -1)\n', ""),
    ('    echo "   - Kestra UI: http://localhost:8081"\n', ""),
])

# 5. scripts/validate-docs.sh
edit("scripts/validate-docs.sh", [
    ('check_file "kestra.yml" "Kestra Configuration"\n', ""),
    ('check_service "http://localhost:8081/" "Kestra CI/CD"\n', ""),
    ("""    if docker volume ls | grep -q "docker_kestra-data"; then
        echo -e "${GREEN}✓${NC} Kestra data volume exists"
    else
        echo -e "${YELLOW}⚠${NC} Kestra data volume not found (may not be created yet)"
    fi
""", ""),
])

# 6. monitoring/resource-monitor.sh
edit("monitoring/resource-monitor.sh", [
    ('CONTAINERS=$(docker ps --format "{{.Names}}" | grep -E "(mcp-server|kestra)" || true)',
     'CONTAINERS=$(docker ps --format "{{.Names}}" | grep -E "(mcp-server)" || true)'),
    ('elif [[ "$line" == *"mcp-server"* ]] || [[ "$line" == *"kestra"* ]]; then',
     'elif [[ "$line" == *"mcp-server"* ]]; then'),
    ('elif [[ "$line" == *"ladybug-data"* ]] || [[ "$line" == *"kestra-data"* ]] || [[ "$line" == *"mcp-"* ]]; then',
     'elif [[ "$line" == *"ladybug-data"* ]] || [[ "$line" == *"mcp-"* ]]; then'),
    ("""    echo -e "  ${GREEN}✅ Kestra (HTTP:8081) - Accessible${NC}"
""", ""),
])
sweep("monitoring/resource-monitor.sh")

# 7. .gitignore
edit(".gitignore", [
    ("""# Kestra
.kestra/data/
.kestra/logs/
.kestra/plugins/
""", ""),
])

# 8. requirements.in
edit("requirements.in", [
    ("# Workflow orchestration (if Python client needed)\nkestra\n", ""),
])

# 9. tests/conftest.py — kestra_container fixture
edit("tests/conftest.py", [
    ('''@pytest.fixture(scope="session")
def kestra_container(docker_client):
    """Locate the running kestra container; skips when the stack is not up."""
    try:
        containers = docker_client.containers.list(filters={"name": "kestra"})
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Cannot list containers: {e}")
    if not containers:
        pytest.skip("No running kestra container (start the compose stack first)")
    return containers[0]


''', ""),
])

print("\ninfra/code sweep complete")
