/* istanbul ignore file */
#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { execSync, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const pkg = require('../package.json');
import fetch from 'node-fetch';
import { install, upgrade, diagnostics, health } from './commands.mjs';

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
  .description('Upgrade GraphMemory-IDE components to the latest version')
  .action(() => {
    const output = upgrade(deps);
    process.stdout.write(output);
  });

program
  .command('diagnostics')
  .description('Run diagnostics and health checks for GraphMemory-IDE')
  .action(async () => {
    const output = await diagnostics(deps);
    process.stdout.write(output);
  });

program
  .command('health')
  .description('Quick health check for GraphMemory-IDE services')
  .action(async () => {
    const output = await health(deps);
    process.stdout.write(output);
  });

program.parse(process.argv); 