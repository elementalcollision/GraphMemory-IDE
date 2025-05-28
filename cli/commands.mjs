// CLI command logic for GraphMemory-IDE, refactored for testability

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

export function upgrade({ chalk, execSync }) {
  let output = '';
  output += chalk.cyan('Starting upgrade process...') + '\n';
  try {
    output += chalk.gray('Pulling latest Docker images...') + '\n';
    execSync('docker compose pull', { stdio: 'inherit' });
    output += chalk.gray('Restarting containers with latest images...') + '\n';
    execSync('docker compose up -d --pull always', { stdio: 'inherit' });
    output += chalk.green('Upgrade complete!') + '\n';
  } catch (e) {
    output += chalk.red('Upgrade failed. Please check Docker and your network connection.') + '\n';
  }
  return output;
}

export async function diagnostics({ chalk, execSync, spawnSync, fetch }) {
  let output = '';
  output += chalk.cyan('Running diagnostics...') + '\n';
  // Docker check
  let dockerOk = false;
  output += chalk.gray('Checking Docker... ');
  if (checkCommand('docker', spawnSync, ['info'])) {
    dockerOk = true;
    output += chalk.green('OK') + '\n';
  } else {
    output += chalk.red('NOT OK') + '\n';
  }
  // OrbStack check
  let orbOk = false;
  output += chalk.gray('Checking OrbStack... ');
  if (checkCommand('orb', spawnSync, ['status'])) {
    orbOk = true;
    output += chalk.green('OK') + '\n';
  } else {
    output += chalk.red('NOT OK') + '\n';
  }
  // Kuzu DB container check
  let kuzuOk = false;
  output += chalk.gray('Checking Kuzu DB container... ');
  try {
    const ps = execSync('docker ps --format "{{.Names}}"', { encoding: 'utf-8' });
    if (ps.includes('kuzu')) {
      kuzuOk = true;
      output += chalk.green('OK') + '\n';
    } else {
      output += chalk.red('NOT RUNNING') + '\n';
    }
  } catch (e) {
    output += chalk.red('ERROR') + '\n';
  }
  // MCP server check
  let mcpOk = false;
  output += chalk.gray('Checking MCP server /health... ');
  try {
    const res = await fetch('http://localhost:8080/health');
    if (res.ok) {
      mcpOk = true;
      output += chalk.green('OK') + '\n';
    } else {
      output += chalk.red('NOT OK') + '\n';
    }
  } catch (e) {
    output += chalk.red('ERROR') + '\n';
  }
  // Network check
  let netOk = false;
  output += chalk.gray('Checking network connectivity... ');
  try {
    const res = await fetch('https://www.google.com');
    if (res.ok) {
      netOk = true;
      output += chalk.green('OK') + '\n';
    } else {
      output += chalk.red('NOT OK') + '\n';
    }
  } catch (e) {
    output += chalk.red('ERROR') + '\n';
  }
  // Summary
  output += '\n' + chalk.bold('Diagnostics Summary:') + '\n';
  output += `  Docker:      ${dockerOk ? chalk.green('OK') : chalk.red('FAIL')}\n`;
  output += `  OrbStack:    ${orbOk ? chalk.green('OK') : chalk.red('FAIL')}\n`;
  output += `  Kuzu DB:     ${kuzuOk ? chalk.green('OK') : chalk.red('FAIL')}\n`;
  output += `  MCP Server:  ${mcpOk ? chalk.green('OK') : chalk.red('FAIL')}\n`;
  output += `  Network:     ${netOk ? chalk.green('OK') : chalk.red('FAIL')}\n`;
  if (dockerOk && orbOk && kuzuOk && mcpOk && netOk) {
    output += chalk.green('\nAll systems healthy.') + '\n';
  } else {
    output += chalk.red('\nOne or more systems are not healthy. Please review the above.') + '\n';
  }
  return output;
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