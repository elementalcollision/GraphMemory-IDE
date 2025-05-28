import * as vscode from 'vscode';
import { GraphMemoryMCPClient } from '../../shared/mcp-client';
import { MCPClientConfig } from '../../shared/types';
import { ConfigLoader, ValidationHelper, ErrorHelper } from '../../shared/utils';
import { MemoryTreeProvider } from './memoryTreeProvider';
import { GraphMemoryCommands } from './commands';
import { GraphMemoryWebviewProvider } from './webviewProvider';

/**
 * GraphMemory VSCode Extension
 * 
 * Provides native VSCode integration with GraphMemory-IDE through:
 * - Command palette integration
 * - Sidebar tree view for memory browsing
 * - Webview panels for detailed memory management
 * - Status bar integration
 * - Configuration management
 */
export class GraphMemoryExtension {
  private client: GraphMemoryMCPClient | null = null;
  private treeProvider: MemoryTreeProvider;
  private commands: GraphMemoryCommands;
  private webviewProvider: GraphMemoryWebviewProvider;
  private statusBarItem: vscode.StatusBarItem;
  private context: vscode.ExtensionContext;

  constructor(context: vscode.ExtensionContext) {
    this.context = context;
    this.treeProvider = new MemoryTreeProvider();
    this.commands = new GraphMemoryCommands();
    this.webviewProvider = new GraphMemoryWebviewProvider(context);
    
    // Create status bar item
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.command = 'graphmemory.connectServer';
    this.updateStatusBar('disconnected');
    this.statusBarItem.show();
  }

  async activate(): Promise<void> {
    try {
      // Register tree view
      vscode.window.registerTreeDataProvider('graphmemoryExplorer', this.treeProvider);

      // Register webview provider
      vscode.window.registerWebviewViewProvider('graphmemoryPanel', this.webviewProvider);

      // Register commands
      this.registerCommands();

      // Set up configuration change listener
      vscode.workspace.onDidChangeConfiguration(this.onConfigurationChanged, this);

      // Auto-connect if configuration is available
      await this.autoConnect();

      console.log('GraphMemory extension activated successfully');
    } catch (error) {
      console.error('Failed to activate GraphMemory extension:', error);
      vscode.window.showErrorMessage(`GraphMemory activation failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  deactivate(): void {
    if (this.client) {
      this.client.disconnect();
    }
    this.statusBarItem.dispose();
  }

  private registerCommands(): void {
    const commands = [
      // Connection commands
      vscode.commands.registerCommand('graphmemory.connectServer', () => this.connectToServer()),
      vscode.commands.registerCommand('graphmemory.disconnectServer', () => this.disconnectFromServer()),
      
      // Memory management commands
      vscode.commands.registerCommand('graphmemory.searchMemories', (query?: string) => 
        this.commands.searchMemories(this.client, query)),
      vscode.commands.registerCommand('graphmemory.createMemory', (content?: string) => 
        this.commands.createMemory(this.client, content)),
      vscode.commands.registerCommand('graphmemory.updateMemory', (memoryId: string) => 
        this.commands.updateMemory(this.client, memoryId)),
      vscode.commands.registerCommand('graphmemory.deleteMemory', (memoryId: string) => 
        this.commands.deleteMemory(this.client, memoryId)),
      vscode.commands.registerCommand('graphmemory.relateMemories', (sourceId: string, targetId: string) => 
        this.commands.relateMemories(this.client, sourceId, targetId)),
      
      // Graph operations
      vscode.commands.registerCommand('graphmemory.queryGraph', (query?: string) => 
        this.commands.queryGraph(this.client, query)),
      vscode.commands.registerCommand('graphmemory.analyzeGraph', () => 
        this.commands.analyzeGraph(this.client)),
      
      // Knowledge discovery
      vscode.commands.registerCommand('graphmemory.clusterKnowledge', () => 
        this.commands.clusterKnowledge(this.client)),
      vscode.commands.registerCommand('graphmemory.generateInsights', () => 
        this.commands.generateInsights(this.client)),
      vscode.commands.registerCommand('graphmemory.getRecommendations', () => 
        this.commands.getRecommendations(this.client)),
      
      // UI commands
      vscode.commands.registerCommand('graphmemory.refreshMemories', () => this.refreshMemories()),
      vscode.commands.registerCommand('graphmemory.showMemoryPanel', () => this.showMemoryPanel()),
    ];

    // Add all commands to context subscriptions
    commands.forEach(command => this.context.subscriptions.push(command));
  }

  private async connectToServer(): Promise<void> {
    try {
      this.updateStatusBar('connecting');
      
      const config = this.loadConfiguration();
      this.client = new GraphMemoryMCPClient(config, this.createLogger());
      
      // Set up event handlers
      this.client.on('connection', (event) => {
        console.log('Connected to GraphMemory server:', event.data.serverUrl);
        this.updateStatusBar('connected');
        vscode.commands.executeCommand('setContext', 'graphmemory.connected', true);
        
        // Update tree provider and webview with new client
        this.treeProvider.setClient(this.client);
        this.webviewProvider.setClient(this.client);
        
        vscode.window.showInformationMessage('Connected to GraphMemory server');
      });

      this.client.on('error', (event) => {
        console.error('GraphMemory client error:', event.data.error);
        this.updateStatusBar('error');
        vscode.window.showErrorMessage(`GraphMemory error: ${event.data.error}`);
      });

      this.client.on('disconnection', () => {
        console.log('Disconnected from GraphMemory server');
        this.updateStatusBar('disconnected');
        vscode.commands.executeCommand('setContext', 'graphmemory.connected', false);
        
        // Clear client from providers
        this.treeProvider.setClient(null);
        this.webviewProvider.setClient(null);
      });

      await this.client.connect();
      
    } catch (error) {
      console.error('Failed to connect to GraphMemory server:', error);
      this.updateStatusBar('error');
      vscode.window.showErrorMessage(`Connection failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  private async disconnectFromServer(): Promise<void> {
    if (this.client) {
      await this.client.disconnect();
      this.client = null;
      this.updateStatusBar('disconnected');
      vscode.commands.executeCommand('setContext', 'graphmemory.connected', false);
      
      // Clear client from providers
      this.treeProvider.setClient(null);
      this.webviewProvider.setClient(null);
      
      vscode.window.showInformationMessage('Disconnected from GraphMemory server');
    }
  }

  private async autoConnect(): Promise<void> {
    const config = vscode.workspace.getConfiguration('graphmemory');
    const serverUrl = config.get<string>('serverUrl');
    const authToken = config.get<string>('auth.token');
    const authApiKey = config.get<string>('auth.apiKey');

    if (serverUrl && (authToken || authApiKey)) {
      await this.connectToServer();
    }
  }

  private loadConfiguration(): MCPClientConfig {
    const config = vscode.workspace.getConfiguration('graphmemory');
    
    const serverUrl = config.get<string>('serverUrl') || 'http://localhost:8000';
    const authMethod = config.get<string>('auth.method') || 'jwt';
    const authToken = config.get<string>('auth.token');
    const authApiKey = config.get<string>('auth.apiKey');

    // Validate configuration
    if (!ValidationHelper.isValidUrl(serverUrl)) {
      throw new Error(`Invalid server URL: ${serverUrl}`);
    }

    if (authMethod === 'jwt' && authToken && !ValidationHelper.isValidJWT(authToken)) {
      console.warn('Warning: JWT token appears to be invalid');
    }

    return {
      serverUrl,
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      auth: {
        method: authMethod as 'jwt' | 'apikey' | 'mtls',
        token: authToken,
        apiKey: authApiKey
      },
      features: {
        autoComplete: config.get<boolean>('features.autoComplete', true),
        semanticSearch: config.get<boolean>('features.semanticSearch', true),
        graphVisualization: config.get<boolean>('features.graphVisualization', true),
        batchRequests: true,
        // VSCode-specific optimizations
        nativeIntegration: true,
        commandPalette: true,
        sidebarIntegration: true
      },
      performance: {
        cacheEnabled: config.get<boolean>('performance.cacheEnabled', true),
        cacheSize: config.get<number>('performance.cacheSize', 100),
        maxConcurrentRequests: config.get<number>('performance.maxConcurrentRequests', 5),
        requestTimeout: config.get<number>('performance.requestTimeout', 30000),
        // Enhanced for VSCode integration
        batchProcessing: true,
        streamingResponses: false // VSCode doesn't need streaming
      }
    };
  }

  private onConfigurationChanged(event: vscode.ConfigurationChangeEvent): void {
    if (event.affectsConfiguration('graphmemory')) {
      // Reconnect if server configuration changed
      if (event.affectsConfiguration('graphmemory.serverUrl') || 
          event.affectsConfiguration('graphmemory.auth')) {
        if (this.client) {
          this.disconnectFromServer().then(() => this.autoConnect());
        }
      }
    }
  }

  private updateStatusBar(status: 'connected' | 'connecting' | 'disconnected' | 'error'): void {
    switch (status) {
      case 'connected':
        this.statusBarItem.text = '$(graph) GraphMemory: Connected';
        this.statusBarItem.tooltip = 'Connected to GraphMemory server';
        this.statusBarItem.backgroundColor = undefined;
        break;
      case 'connecting':
        this.statusBarItem.text = '$(loading~spin) GraphMemory: Connecting...';
        this.statusBarItem.tooltip = 'Connecting to GraphMemory server';
        this.statusBarItem.backgroundColor = undefined;
        break;
      case 'disconnected':
        this.statusBarItem.text = '$(debug-disconnect) GraphMemory: Disconnected';
        this.statusBarItem.tooltip = 'Click to connect to GraphMemory server';
        this.statusBarItem.backgroundColor = undefined;
        break;
      case 'error':
        this.statusBarItem.text = '$(error) GraphMemory: Error';
        this.statusBarItem.tooltip = 'GraphMemory connection error';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
        break;
    }
  }

  private async refreshMemories(): Promise<void> {
    if (!this.client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      await this.treeProvider.refresh();
      vscode.window.showInformationMessage('Memories refreshed');
    } catch (error) {
      vscode.window.showErrorMessage(`Failed to refresh memories: ${ErrorHelper.formatError(error)}`);
    }
  }

  private async showMemoryPanel(): Promise<void> {
    await this.webviewProvider.show();
  }

  private createLogger() {
    return {
      info: (message: string, data?: any) => {
        console.log(`[GraphMemory] ${message}`, data || '');
      },
      warn: (message: string, data?: any) => {
        console.warn(`[GraphMemory] ${message}`, data || '');
      },
      error: (message: string, data?: any) => {
        console.error(`[GraphMemory] ${message}`, data || '');
      },
      debug: (message: string, data?: any) => {
        const config = vscode.workspace.getConfiguration('graphmemory');
        if (config.get<boolean>('debug', false)) {
          console.debug(`[GraphMemory] ${message}`, data || '');
        }
      }
    };
  }
}

// Extension activation/deactivation functions
let extension: GraphMemoryExtension;

export function activate(context: vscode.ExtensionContext): void {
  extension = new GraphMemoryExtension(context);
  extension.activate();
}

export function deactivate(): void {
  if (extension) {
    extension.deactivate();
  }
} 