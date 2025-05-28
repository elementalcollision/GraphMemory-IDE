#!/usr/bin/env node
/* istanbul ignore file */

import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { execSync, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const pkg = require('../package.json');
import fetch from 'node-fetch';
import { install, upgrade, status, rollback, backup, health } from './commands.mjs';

const program = new Command();

const deps = { inquirer, chalk, execSync, spawnSync, fetch };

program
  .name('graphmemory')
  .description('GraphMemory-IDE CLI for install, upgrade, diagnostics, and health checks')
  .version(pkg.version);

program
  .command('install')
  .description('Install or set up GraphMemory-IDE components')
  .action(async () => {
    const output = await install(deps);
    process.stdout.write(output);
  });

program
  .command('upgrade')
  .description('Upgrade GraphMemory-IDE components with enterprise features')
  .option('--strategy <type>', 'Update strategy: blue-green|rolling', 'blue-green')
  .option('--verify-signatures', 'Verify image signatures (default: true)')
  .option('--no-verify-signatures', 'Skip signature verification')
  .option('--backup-database', 'Create database backup (default: true)')
  .option('--no-backup-database', 'Skip database backup')
  .option('--dry-run', 'Show what would be updated without executing')
  .option('--yes', 'Skip confirmation prompts')
  .option('--verbose', 'Enable verbose logging')
  .option('--identity-regexp <pattern>', 'Identity regexp for signature verification')
  .option('--oidc-issuer-regexp <pattern>', 'OIDC issuer regexp for signature verification')
  .option('--no-use-cache', 'Disable Docker layer caching')
  .option('--health-check-timeout <seconds>', 'Health check timeout in seconds', '30')
  .action(async (options) => {
    await upgrade(options);
  });

program
  .command('status')
  .description('Show current system status and update progress')
  .option('--verbose', 'Enable verbose output')
  .action(async (options) => {
    await status(options);
  });

program
  .command('rollback')
  .description('Rollback to a previous version')
  .option('--backup-id <id>', 'Specific backup ID to rollback to')
  .option('--yes', 'Skip confirmation prompts')
  .option('--verbose', 'Enable verbose logging')
  .action(async (options) => {
    await rollback(options);
  });

program
  .command('backup')
  .description('Create a manual database backup')
  .option('--reason <reason>', 'Reason for creating backup', 'manual-backup')
  .option('--verbose', 'Enable verbose logging')
  .action(async (options) => {
    await backup(options);
  });

program
  .command('health')
  .description('Quick health check for GraphMemory-IDE services')
  .action(async () => {
    const output = await health(deps);
    process.stdout.write(output);
  });

program.parse(process.argv); 