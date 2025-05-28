import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
  vscode.window.showInformationMessage('Start all tests.');

  test('Extension should be present', () => {
    assert.ok(vscode.extensions.getExtension('graphmemory.graphmemory-vscode'));
  });

  test('Extension should activate', async () => {
    const extension = vscode.extensions.getExtension('graphmemory.graphmemory-vscode');
    assert.ok(extension);
    
    if (extension && !extension.isActive) {
      await extension.activate();
    }
    
    assert.ok(extension?.isActive);
  });

  test('Commands should be registered', async () => {
    const commands = await vscode.commands.getCommands(true);
    
    const expectedCommands = [
      'graphmemory.searchMemories',
      'graphmemory.createMemory',
      'graphmemory.connectServer',
      'graphmemory.disconnectServer',
      'graphmemory.refreshMemories',
      'graphmemory.analyzeGraph',
      'graphmemory.getRecommendations',
      'graphmemory.showMemoryPanel'
    ];

    expectedCommands.forEach(command => {
      assert.ok(commands.includes(command), `Command ${command} should be registered`);
    });
  });

  test('Configuration should be available', () => {
    const config = vscode.workspace.getConfiguration('graphmemory');
    assert.ok(config);
    
    // Test default values
    assert.strictEqual(config.get('serverUrl'), 'http://localhost:8000');
    assert.strictEqual(config.get('auth.method'), 'jwt');
    assert.strictEqual(config.get('features.autoComplete'), true);
    assert.strictEqual(config.get('features.semanticSearch'), true);
    assert.strictEqual(config.get('features.graphVisualization'), true);
  });
}); 