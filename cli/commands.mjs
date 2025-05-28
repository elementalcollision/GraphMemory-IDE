// CLI command logic for GraphMemory-IDE, refactored for testability

import chalk from 'chalk';
import inquirer from 'inquirer';
import { UpdateFlow } from './update/update-flow.mjs';

export async function install({ inquirer, chalk, execSync, spawnSync }) {
  let output = '';
  output += chalk.cyan('Starting GraphMemory-IDE installation...') + '\n';
  // Check for Docker
  output += chalk.gray('Checking for Docker... ');
  if (!checkCommand('docker', spawnSync)) {
    output += chalk.red('Docker not found! Please install Docker and try again.') + '\n';
    return output;
  } else {
    output += chalk.green('found.') + '\n';
  }
  // Check for OrbStack
  output += chalk.gray('Checking for OrbStack... ');
  if (!checkCommand('orb', spawnSync)) {
    output += chalk.red('OrbStack not found! Please install OrbStack and try again.') + '\n';
    return output;
  } else {
    output += chalk.green('found.') + '\n';
  }
  // Simulate user prompt
  const { proceed } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'proceed',
      message: 'Proceed with Docker Compose setup?',
      default: true,
    },
  ]);
  if (!proceed) {
    output += chalk.yellow('Installation cancelled by user.') + '\n';
    return output;
  }
  // Run Docker Compose up
  output += chalk.green('Running Docker Compose up...') + '\n';
  try {
    execSync('docker compose up -d', { stdio: 'inherit' });
    output += chalk.green('GraphMemory-IDE installation complete!') + '\n';
  } catch (e) {
    output += chalk.red('Failed to run Docker Compose up.') + '\n';
  }
  return output;
}

/**
 * Enhanced upgrade command with enterprise features
 */
export async function upgrade(options) {
  try {
    console.log(chalk.cyan.bold('🚀 GraphMemory-IDE Update System'));
    console.log(chalk.gray('Enterprise-grade updates with signature verification and rollback'));
    console.log();

    // Initialize update flow with options
    const updateFlow = new UpdateFlow({
      verbose: options.verbose || false,
      dryRun: options.dryRun || false,
      strategy: options.strategy || 'blue-green',
      verifySignatures: options.verifySignatures !== false,
      backupDatabase: options.backupDatabase !== false
    });

    // Check for existing update in progress
    const progress = await updateFlow.getProgress();
    if (progress.isUpdateInProgress) {
      console.log(chalk.yellow('⚠️ Update already in progress'));
      console.log(`Current phase: ${progress.currentPhase}`);
      console.log(`Progress: ${progress.progress}%`);
      
      const { action } = await inquirer.prompt([{
        type: 'list',
        name: 'action',
        message: 'What would you like to do?',
        choices: [
          { name: 'Continue monitoring', value: 'monitor' },
          { name: 'Cancel update', value: 'cancel' },
          { name: 'Exit', value: 'exit' }
        ]
      }]);
      
      if (action === 'cancel') {
        await updateFlow.cancel();
        console.log(chalk.yellow('Update cancelled'));
        return;
      } else if (action === 'exit') {
        return;
      }
      // Continue with monitoring...
    }

    // Get available updates
    console.log(chalk.blue('🔍 Checking for updates...'));
    const updatePlan = await getUpdatePlan(options);
    
    if (!updatePlan || (!updatePlan.images?.length && !updatePlan.schemaChanges?.length)) {
      console.log(chalk.green('✅ System is up to date'));
      return;
    }

    // Display update plan
    displayUpdatePlan(updatePlan);

    // Confirm update
    if (!options.yes && !options.dryRun) {
      const { confirm } = await inquirer.prompt([{
        type: 'confirm',
        name: 'confirm',
        message: 'Proceed with update?',
        default: false
      }]);
      
      if (!confirm) {
        console.log(chalk.yellow('Update cancelled'));
        return;
      }
    }

    // Execute update
    console.log();
    const result = await updateFlow.execute(updatePlan, {
      signatureOptions: {
        identityRegexp: options.identityRegexp,
        oidcIssuerRegexp: options.oidcIssuerRegexp
      },
      containerOptions: {
        useCache: options.useCache !== false,
        healthCheckTimeout: options.healthCheckTimeout
      }
    });

    // Display results
    if (result.success) {
      console.log();
      console.log(chalk.green.bold('✅ Update completed successfully!'));
      console.log(`Duration: ${Math.round(result.duration / 1000)}s`);
      console.log(`Strategy: ${result.strategy.toUpperCase()}`);
      
      if (result.result.containerUpdate) {
        console.log(`Updated images: ${result.result.containerUpdate.updatedImages?.length || 0}`);
      }
      
      if (result.result.schemaMigration) {
        console.log(`Schema changes: ${result.result.schemaMigration.appliedChanges?.length || 0}`);
      }
    }

  } catch (error) {
    console.error(chalk.red.bold('❌ Update failed:'), error.message);
    
    if (options.verbose) {
      console.error(chalk.red('Stack trace:'), error.stack);
    }
    
    process.exit(1);
  }
}

/**
 * Get update plan by checking for new versions
 */
async function getUpdatePlan(options) {
  // This would typically fetch from a registry or update server
  // For now, return a sample update plan
  
  const updatePlan = {
    version: '1.1.0',
    images: [
      {
        name: 'graphmemory/mcp-server',
        currentTag: '1.0.0',
        tag: '1.1.0',
        size: '245MB',
        changes: ['Security updates', 'Performance improvements', 'Bug fixes']
      },
      {
        name: 'graphmemory/kestra',
        currentTag: '0.15.0',
        tag: '0.16.0',
        size: '180MB',
        changes: ['New workflow features', 'UI improvements']
      }
    ],
    schemaChanges: [
      {
        type: 'add_node_table',
        tableName: 'UpdateHistory',
        properties: 'id STRING, version STRING, timestamp TIMESTAMP, status STRING',
        description: 'Track update history'
      }
    ],
    schemaVersion: '1.1.0',
    services: ['mcp-server', 'kestra'],
    releaseNotes: 'https://github.com/graphmemory/releases/v1.1.0',
    securityUpdates: true,
    breakingChanges: false
  };

  return updatePlan;
}

/**
 * Display update plan to user
 */
function displayUpdatePlan(updatePlan) {
  console.log();
  console.log(chalk.cyan.bold(`📦 Update Plan - Version ${updatePlan.version}`));
  console.log();

  if (updatePlan.images?.length > 0) {
    console.log(chalk.blue.bold('🐳 Container Images:'));
    updatePlan.images.forEach(image => {
      console.log(`  ${chalk.white(image.name)}`);
      console.log(`    ${chalk.gray(`${image.currentTag} → ${image.tag}`)} ${chalk.yellow(`(${image.size})`)}`);
      if (image.changes?.length > 0) {
        image.changes.forEach(change => {
          console.log(`    ${chalk.gray('•')} ${change}`);
        });
      }
      console.log();
    });
  }

  if (updatePlan.schemaChanges?.length > 0) {
    console.log(chalk.blue.bold('🗄️ Database Schema Changes:'));
    updatePlan.schemaChanges.forEach(change => {
      console.log(`  ${chalk.white(change.type)}: ${change.tableName}`);
      console.log(`    ${chalk.gray(change.description)}`);
      console.log();
    });
  }

  if (updatePlan.securityUpdates) {
    console.log(chalk.red.bold('🔒 Security Updates Included'));
  }

  if (updatePlan.breakingChanges) {
    console.log(chalk.yellow.bold('⚠️ Breaking Changes - Review release notes'));
  }

  if (updatePlan.releaseNotes) {
    console.log(chalk.blue(`📖 Release Notes: ${updatePlan.releaseNotes}`));
  }
}

/**
 * Status command - show current system status
 */
export async function status(options) {
  try {
    console.log(chalk.cyan.bold('📊 GraphMemory-IDE System Status'));
    console.log();

    const updateFlow = new UpdateFlow({ verbose: options.verbose });
    
    // Check update progress
    const progress = await updateFlow.getProgress();
    
    if (progress.isUpdateInProgress) {
      console.log(chalk.yellow.bold('🔄 Update in Progress'));
      console.log(`Phase: ${progress.currentPhase}`);
      console.log(`Progress: ${progress.progress}%`);
      console.log(`Started: ${new Date(progress.startTime).toLocaleString()}`);
      console.log();
    }

    // Get container status
    const containerStatus = await updateFlow.containerUpdater.getContainerStatus();
    
    console.log(chalk.blue.bold('🐳 Container Status:'));
    console.log(`Overall Health: ${getHealthDisplay(containerStatus.health)}`);
    console.log(`Running Containers: ${containerStatus.containers?.length || 0}`);
    
    if (containerStatus.containers?.length > 0) {
      containerStatus.containers.forEach(container => {
        const statusColor = container.status.includes('Up') ? chalk.green : chalk.red;
        console.log(`  ${chalk.white(container.name)}: ${statusColor(container.status)}`);
      });
    }
    console.log();

    // Get database status
    const dbHealth = await updateFlow.databaseMigrator.getHealthStatus();
    
    console.log(chalk.blue.bold('🗄️ Database Status:'));
    console.log(`Accessible: ${dbHealth.databaseAccessible ? chalk.green('Yes') : chalk.red('No')}`);
    console.log(`Backup System: ${dbHealth.backupSystemHealthy ? chalk.green('Healthy') : chalk.red('Unhealthy')}`);
    
    if (dbHealth.lastBackup) {
      console.log(`Last Backup: ${new Date(dbHealth.lastBackup.createdAt).toLocaleString()}`);
    }

  } catch (error) {
    console.error(chalk.red('Failed to get status:'), error.message);
    process.exit(1);
  }
}

/**
 * Rollback command - rollback to previous version
 */
export async function rollback(options) {
  try {
    console.log(chalk.yellow.bold('🔄 GraphMemory-IDE Rollback'));
    console.log();

    const updateFlow = new UpdateFlow({ verbose: options.verbose });
    
    // Get available backups
    const backups = await updateFlow.databaseMigrator.listBackups();
    
    if (backups.length === 0) {
      console.log(chalk.red('No backups available for rollback'));
      return;
    }

    // Select backup to rollback to
    let targetBackup;
    
    if (options.backupId) {
      targetBackup = backups.find(b => b.backupId === options.backupId);
      if (!targetBackup) {
        console.log(chalk.red(`Backup not found: ${options.backupId}`));
        return;
      }
    } else {
      console.log(chalk.blue('Available backups:'));
      backups.slice(0, 10).forEach((backup, index) => {
        console.log(`  ${index + 1}. ${backup.backupId} (${new Date(backup.createdAt).toLocaleString()})`);
      });
      console.log();

      const { selection } = await inquirer.prompt([{
        type: 'list',
        name: 'selection',
        message: 'Select backup to rollback to:',
        choices: backups.slice(0, 10).map((backup, index) => ({
          name: `${backup.backupId} (${new Date(backup.createdAt).toLocaleString()})`,
          value: index
        }))
      }]);

      targetBackup = backups[selection];
    }

    // Confirm rollback
    if (!options.yes) {
      console.log();
      console.log(chalk.yellow.bold('⚠️ Rollback Warning'));
      console.log('This will revert your system to a previous state.');
      console.log('Any changes made after the backup will be lost.');
      console.log();
      console.log(`Target backup: ${targetBackup.backupId}`);
      console.log(`Created: ${new Date(targetBackup.createdAt).toLocaleString()}`);
      console.log();

      const { confirm } = await inquirer.prompt([{
        type: 'confirm',
        name: 'confirm',
        message: 'Are you sure you want to proceed with rollback?',
        default: false
      }]);

      if (!confirm) {
        console.log(chalk.yellow('Rollback cancelled'));
        return;
      }
    }

    // Execute rollback
    console.log(chalk.blue('Executing rollback...'));
    
    const rollbackResult = await updateFlow.databaseMigrator.rollbackDatabase(targetBackup.backupId);
    
    if (rollbackResult.success) {
      console.log();
      console.log(chalk.green.bold('✅ Rollback completed successfully'));
      console.log(`Rolled back to: ${rollbackResult.rolledBackTo}`);
      
      if (rollbackResult.safetyBackupId) {
        console.log(`Safety backup created: ${rollbackResult.safetyBackupId}`);
      }
    }

  } catch (error) {
    console.error(chalk.red.bold('❌ Rollback failed:'), error.message);
    
    if (options.verbose) {
      console.error(chalk.red('Stack trace:'), error.stack);
    }
    
    process.exit(1);
  }
}

/**
 * Backup command - create manual backup
 */
export async function backup(options) {
  try {
    console.log(chalk.blue.bold('💾 Creating Database Backup'));
    console.log();

    const updateFlow = new UpdateFlow({ verbose: options.verbose });
    
    const backupResult = await updateFlow.databaseMigrator.createBackup({
      reason: options.reason || 'manual-backup'
    });

    if (backupResult.success) {
      console.log(chalk.green.bold('✅ Backup created successfully'));
      console.log(`Backup ID: ${backupResult.backupId}`);
      console.log(`Location: ${backupResult.backupPath}`);
      console.log(`Created: ${new Date(backupResult.metadata.createdAt).toLocaleString()}`);
    }

  } catch (error) {
    console.error(chalk.red.bold('❌ Backup failed:'), error.message);
    process.exit(1);
  }
}

/**
 * Get health display with colors
 */
function getHealthDisplay(health) {
  switch (health) {
    case 'healthy':
      return chalk.green('Healthy');
    case 'degraded':
      return chalk.yellow('Degraded');
    case 'unhealthy':
      return chalk.red('Unhealthy');
    default:
      return chalk.gray('Unknown');
  }
}

export async function health({ chalk, execSync, fetch }) {
  let output = '';
  output += chalk.cyan('Performing quick health check...') + '\n';
  let mcpOk = false;
  let kuzuOk = false;
  try {
    const res = await fetch('http://localhost:8080/health');
    if (res.ok) mcpOk = true;
  } catch (e) {}
  try {
    const ps = execSync('docker ps --format "{{.Names}}"', { encoding: 'utf-8' });
    if (ps.includes('kuzu')) kuzuOk = true;
  } catch (e) {}
  if (mcpOk && kuzuOk) {
    output += chalk.green('All core services appear healthy.') + '\n';
  } else {
    if (!mcpOk) output += chalk.red('MCP server is not healthy.') + '\n';
    if (!kuzuOk) output += chalk.red('Kuzu DB container is not running.') + '\n';
  }
  return output;
}

function checkCommand(cmd, spawnSync, args = ['--version']) {
  try {
    const result = spawnSync(cmd, args, { encoding: 'utf-8' });
    if (result.error || result.status !== 0) {
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
} 