#!/usr/bin/env python3
"""Phase 5 batch edit: Kuzu -> LadybugDB in cli/ tooling."""
import re
import sys
from pathlib import Path

ROOT = Path("/Users/dave/Claude_Primary/Graph_Memory")

SWEEPS = [
    ("kuzuPath", "lbugPath"),
    ("_executeKuzuCommand", "_executeLbugCommand"),
    ("Kuzu DB", "LadybugDB"),
    ("Kuzu database", "LadybugDB database"),
    ("Kuzu native", "LadybugDB native"),
    ("Kuzu EXPORT/IMPORT", "LadybugDB EXPORT/IMPORT"),
    ("kuzu-migration", "ladybug-migration"),
    ("./backups/kuzu", "./backups/ladybug"),
    ("./temp/kuzu", "./temp/ladybug"),
    ("./data/kuzu", "./data/ladybug"),
    ("'kuzu'", "'lbug'"),
    ("Kuzu", "LadybugDB"),
    ("kuzu", "ladybug"),
    ("KUZU", "LADYBUG"),
]

for f in [
    "cli/update/database-migrator.mjs",
    "cli/commands.mjs",
    "cli/index.test.mjs",
]:
    p = ROOT / f
    t = p.read_text()
    for old, new in SWEEPS:
        t = t.replace(old, new)
    if re.search(r"kuzu|Kuzu|KUZU", t):
        for l in t.splitlines():
            if re.search(r"kuzu|Kuzu|KUZU", l):
                print("   leftover:", l.strip()[:100])
        print(f"ABORT: leftover kuzu in {f}")
        sys.exit(1)
    p.write_text(t)
    print(f"  OK  {f}")

print("\nPhase 5 edits complete.")
