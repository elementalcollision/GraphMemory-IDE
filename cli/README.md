# @graphmemory/cli

GraphMemory-IDE CLI for install, upgrade, diagnostics, and health checks.

## Testing & Coverage Policy

- **Business Logic Coverage:** All CLI logic is implemented in `commands.mjs` and is 100% covered by unit and edge case tests.
- **Entrypoint Coverage:** The CLI entrypoint (`index.mjs`) is excluded from coverage reports (see `/* istanbul ignore file */`).
- **Integration Test:** A real CLI subprocess test is included for local/manual validation, but is skipped in CI/headless environments due to system dependencies (Docker, OrbStack) and lack of TTY for prompts.
- **Edge Cases:** All error, type, and system edge cases are robustly tested.
- **How to Run:**
  - `npm test` or `npx vitest run --coverage` for full coverage and test results.
  - Coverage reports are generated using V8 and Vitest.

## Installation & Usage

You can use the CLI directly with npx (recommended):

```sh
npx @graphmemory/cli <command>
```

Or install globally with npm:

```sh
npm install -g @graphmemory/cli
graphmemory <command>
```

## Requirements
- Node.js >= 18
- Docker
- OrbStack (for macOS/Linux)

## Commands

- `install`   — Install or set up GraphMemory-IDE components (checks Docker/OrbStack, runs Docker Compose)
- `upgrade`   — Upgrade GraphMemory-IDE components to the latest version (pulls images, restarts containers)
- `diagnostics` — Run diagnostics and health checks (checks Docker, OrbStack, Kuzu DB, MCP server, network)
- `health`    — Quick health check for core services (MCP server, Kuzu DB)

## Examples

Install (with prompts):
```sh
npx @graphmemory/cli install
```

Upgrade:
```sh
npx @graphmemory/cli upgrade
```

Diagnostics:
```sh
npx @graphmemory/cli diagnostics
```

Health check:
```sh
npx @graphmemory/cli health
```

## Output & Error Handling
- All commands print color-coded output for clarity.
- Errors (e.g., missing Docker/OrbStack, failed health checks) are clearly reported and exit with nonzero status.
- Diagnostics and health commands print a summary table.

## Cross-Platform Support
- Works on macOS, Linux, and Windows (with Docker Desktop).
- OrbStack is required for macOS/Linux integration.

## Development
- See `package.json` for scripts and dependencies.
- Tests are written with Jest.

---
For more details, see the main project README and Product Requirements Document. 