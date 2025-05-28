# Kestra Flows for CI/CD

This directory contains Kestra workflow definitions for automating CI/CD tasks in the GraphMemory-IDE project.

## Purpose
- Automate linting, testing, building, and deployment steps
- Integrate with OrbStack and Docker Compose
- Enable reproducible, declarative CI/CD pipelines

## Structure
- Each flow is defined as a YAML file (e.g., `lint.yml`, `unit-tests.yml`, `integration-tests.yml`, `deploy.yml`)
- Flows can be triggered on PRs, merges, or manually

## Node.js CLI Testing
- All CLI/unit tests for Node.js are run with Vitest (see `unit-tests.yml`).
- Coverage is enforced for all business logic.
- The CLI integration test is skipped in CI/headless environments (see `cli/index.test.mjs` for skip policy).
- This ensures robust coverage and reliable CI runs, even when system dependencies (Docker, OrbStack) are not present.

## Example Flows
- `lint.yml`: Run code linting and formatting checks
- `unit-tests.yml`: Run Python and Node unit tests
- `integration-tests.yml`: Test MCP server and Kùzu integration
- `e2e-tests.yml`: Run end-to-end tests with Playwright
- `deploy.yml`: Build and deploy Docker images, publish artifacts

Refer to the PRD and project documentation for required steps and best practices. 