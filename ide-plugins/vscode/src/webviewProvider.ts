import * as vscode from 'vscode';
import { GraphMemoryMCPClient } from '../../shared/mcp-client';

/**
 * GraphMemory Webview Provider
 * 
 * Provides rich interactive UI for memory management using VSCode webviews:
 * - Memory browser with search and filtering
 * - Memory editor with rich text support
 * - Graph visualization
 * - Relationship management
 * - Bulk operations
 */
export class GraphMemoryWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'graphmemoryPanel';

  private _view?: vscode.WebviewView;
  private client: GraphMemoryMCPClient | null = null;

  constructor(private readonly _extensionContext: vscode.ExtensionContext) {}

  setClient(client: GraphMemoryMCPClient | null): void {
    this.client = client;
    if (this._view) {
      this.updateWebview();
    }
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        this._extensionContext.extensionUri
      ]
    };

    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    // Handle messages from the webview
    webviewView.webview.onDidReceiveMessage(
      message => this.handleMessage(message),
      undefined,
      this._extensionContext.subscriptions
    );

    // Update webview when it becomes visible
    webviewView.onDidChangeVisibility(() => {
      if (webviewView.visible) {
        this.updateWebview();
      }
    });

    // Initial update
    this.updateWebview();
  }

  public async show(): Promise<void> {
    if (this._view) {
      this._view.show?.(true);
    }
  }

  private async handleMessage(message: any): Promise<void> {
    switch (message.type) {
      case 'searchMemories':
        await this.handleSearchMemories(message.query, message.filters);
        break;
      case 'createMemory':
        await this.handleCreateMemory(message.data);
        break;
      case 'updateMemory':
        await this.handleUpdateMemory(message.id, message.data);
        break;
      case 'deleteMemory':
        await this.handleDeleteMemory(message.id);
        break;
      case 'getMemory':
        await this.handleGetMemory(message.id);
        break;
      case 'relateMemories':
        await this.handleRelateMemories(message.sourceId, message.targetId, message.relationshipType);
        break;
      case 'analyzeGraph':
        await this.handleAnalyzeGraph();
        break;
      case 'getRecommendations':
        await this.handleGetRecommendations(message.context);
        break;
      case 'ready':
        await this.updateWebview();
        break;
    }
  }

  private async handleSearchMemories(query: string, filters?: any): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.searchMemories({
        query,
        limit: 50,
        filters
      });

      this.sendMessage({
        type: 'searchResults',
        data: result
      });
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleCreateMemory(data: any): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.createMemory({
        ...data,
        metadata: {
          ...data.metadata,
          source: 'vscode-webview',
          workspace: vscode.workspace.name
        }
      });

      this.sendMessage({
        type: 'memoryCreated',
        data: result
      });

      // Refresh the tree view
      vscode.commands.executeCommand('graphmemory.refreshMemories');
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to create memory: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleUpdateMemory(id: string, data: any): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.updateMemory({
        id,
        ...data
      });

      this.sendMessage({
        type: 'memoryUpdated',
        data: result
      });

      // Refresh the tree view
      vscode.commands.executeCommand('graphmemory.refreshMemories');
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to update memory: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleDeleteMemory(id: string): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      await this.client.deleteMemory({ id });

      this.sendMessage({
        type: 'memoryDeleted',
        id
      });

      // Refresh the tree view
      vscode.commands.executeCommand('graphmemory.refreshMemories');
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to delete memory: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleGetMemory(id: string): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.getMemory({ id });

      this.sendMessage({
        type: 'memoryDetails',
        data: result
      });
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to get memory: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleRelateMemories(sourceId: string, targetId: string, relationshipType: string): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.relateMemories({
        source_id: sourceId,
        target_id: targetId,
        relationship_type: relationshipType
      });

      this.sendMessage({
        type: 'relationshipCreated',
        data: result
      });
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to create relationship: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleAnalyzeGraph(): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.analyzeGraph({});

      this.sendMessage({
        type: 'graphAnalysis',
        data: result
      });
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Graph analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private async handleGetRecommendations(context?: any): Promise<void> {
    if (!this.client) {
      this.sendMessage({ type: 'error', message: 'Not connected to GraphMemory server' });
      return;
    }

    try {
      const result = await this.client.getRecommendations({
        context: context || this.getCurrentContext()
      });

      this.sendMessage({
        type: 'recommendations',
        data: result
      });
    } catch (error) {
      this.sendMessage({
        type: 'error',
        message: `Failed to get recommendations: ${error instanceof Error ? error.message : 'Unknown error'}`
      });
    }
  }

  private getCurrentContext(): any {
    const editor = vscode.window.activeTextEditor;
    return {
      workspace: vscode.workspace.name,
      file: editor?.document.fileName,
      language: editor?.document.languageId,
      timestamp: new Date().toISOString()
    };
  }

  private sendMessage(message: any): void {
    if (this._view) {
      this._view.webview.postMessage(message);
    }
  }

  private async updateWebview(): Promise<void> {
    if (!this._view) {
      return;
    }

    const connectionStatus = {
      connected: !!this.client,
      serverUrl: this.client ? 'Connected' : 'Not connected'
    };

    this.sendMessage({
      type: 'connectionStatus',
      data: connectionStatus
    });
  }

  private getHtmlForWebview(webview: vscode.Webview): string {
    // Get the local path to main script run in the webview
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionContext.extensionUri, 'media', 'main.js'));
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(this._extensionContext.extensionUri, 'media', 'main.css'));

    // Use a nonce to only allow specific scripts to be run
    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="${styleUri}" rel="stylesheet">
    <title>GraphMemory</title>
</head>
<body>
    <div id="app">
        <div class="header">
            <h2>GraphMemory</h2>
            <div id="connection-status" class="status-disconnected">Disconnected</div>
        </div>

        <div class="tabs">
            <button class="tab-button active" onclick="showTab('search')">Search</button>
            <button class="tab-button" onclick="showTab('create')">Create</button>
            <button class="tab-button" onclick="showTab('graph')">Graph</button>
            <button class="tab-button" onclick="showTab('insights')">Insights</button>
        </div>

        <!-- Search Tab -->
        <div id="search-tab" class="tab-content active">
            <div class="search-section">
                <input type="text" id="search-input" placeholder="Search memories..." />
                <button onclick="searchMemories()">Search</button>
            </div>
            <div class="filters">
                <select id="type-filter">
                    <option value="">All Types</option>
                    <option value="note">Notes</option>
                    <option value="code">Code</option>
                    <option value="idea">Ideas</option>
                    <option value="task">Tasks</option>
                    <option value="reference">References</option>
                </select>
                <input type="text" id="tag-filter" placeholder="Filter by tags..." />
            </div>
            <div id="search-results" class="results-container">
                <p class="placeholder">Enter a search query to find memories</p>
            </div>
        </div>

        <!-- Create Tab -->
        <div id="create-tab" class="tab-content">
            <form id="create-form">
                <div class="form-group">
                    <label for="memory-title">Title (optional)</label>
                    <input type="text" id="memory-title" placeholder="Brief title for this memory..." />
                </div>
                <div class="form-group">
                    <label for="memory-content">Content *</label>
                    <textarea id="memory-content" placeholder="What would you like to remember?" required></textarea>
                </div>
                <div class="form-group">
                    <label for="memory-type">Type</label>
                    <select id="memory-type">
                        <option value="note">Note</option>
                        <option value="code">Code</option>
                        <option value="idea">Idea</option>
                        <option value="task">Task</option>
                        <option value="reference">Reference</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="memory-tags">Tags (comma-separated)</label>
                    <input type="text" id="memory-tags" placeholder="tag1, tag2, tag3..." />
                </div>
                <button type="submit">Create Memory</button>
            </form>
        </div>

        <!-- Graph Tab -->
        <div id="graph-tab" class="tab-content">
            <div class="graph-controls">
                <button onclick="analyzeGraph()">Analyze Graph</button>
                <button onclick="getRecommendations()">Get Recommendations</button>
            </div>
            <div id="graph-results" class="results-container">
                <p class="placeholder">Click "Analyze Graph" to see memory relationships</p>
            </div>
        </div>

        <!-- Insights Tab -->
        <div id="insights-tab" class="tab-content">
            <div class="insights-controls">
                <button onclick="generateInsights()">Generate Insights</button>
                <button onclick="clusterKnowledge()">Cluster Knowledge</button>
            </div>
            <div id="insights-results" class="results-container">
                <p class="placeholder">Generate insights to discover patterns in your memories</p>
            </div>
        </div>

        <!-- Memory Details Modal -->
        <div id="memory-modal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <div id="memory-details"></div>
            </div>
        </div>
    </div>

    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        
        // Tab management
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(tabName + '-tab').classList.add('active');
            event.target.classList.add('active');
        }

        // Search functionality
        function searchMemories() {
            const query = document.getElementById('search-input').value;
            const typeFilter = document.getElementById('type-filter').value;
            const tagFilter = document.getElementById('tag-filter').value;
            
            const filters = {};
            if (typeFilter) filters.type = typeFilter;
            if (tagFilter) filters.tags = tagFilter.split(',').map(t => t.trim());
            
            vscode.postMessage({
                type: 'searchMemories',
                query,
                filters
            });
        }

        // Create memory
        document.getElementById('create-form').addEventListener('submit', (e) => {
            e.preventDefault();
            
            const title = document.getElementById('memory-title').value;
            const content = document.getElementById('memory-content').value;
            const type = document.getElementById('memory-type').value;
            const tagsInput = document.getElementById('memory-tags').value;
            const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()) : [];
            
            vscode.postMessage({
                type: 'createMemory',
                data: { title, content, type, tags }
            });
        });

        // Graph operations
        function analyzeGraph() {
            vscode.postMessage({ type: 'analyzeGraph' });
        }

        function getRecommendations() {
            vscode.postMessage({ type: 'getRecommendations' });
        }

        function generateInsights() {
            vscode.postMessage({ type: 'generateInsights' });
        }

        function clusterKnowledge() {
            vscode.postMessage({ type: 'clusterKnowledge' });
        }

        // Modal management
        function showMemoryDetails(memoryId) {
            vscode.postMessage({
                type: 'getMemory',
                id: memoryId
            });
        }

        function closeModal() {
            document.getElementById('memory-modal').style.display = 'none';
        }

        // Message handling
        window.addEventListener('message', event => {
            const message = event.data;
            
            switch (message.type) {
                case 'connectionStatus':
                    updateConnectionStatus(message.data);
                    break;
                case 'searchResults':
                    displaySearchResults(message.data);
                    break;
                case 'memoryCreated':
                    handleMemoryCreated(message.data);
                    break;
                case 'memoryDetails':
                    showMemoryModal(message.data);
                    break;
                case 'graphAnalysis':
                    displayGraphAnalysis(message.data);
                    break;
                case 'recommendations':
                    displayRecommendations(message.data);
                    break;
                case 'error':
                    showError(message.message);
                    break;
            }
        });

        function updateConnectionStatus(status) {
            const statusEl = document.getElementById('connection-status');
            statusEl.textContent = status.connected ? 'Connected' : 'Disconnected';
            statusEl.className = status.connected ? 'status-connected' : 'status-disconnected';
        }

        function displaySearchResults(results) {
            const container = document.getElementById('search-results');
            
            if (!results.memories || results.memories.length === 0) {
                container.innerHTML = '<p class="placeholder">No memories found</p>';
                return;
            }
            
            const html = results.memories.map(memory => \`
                <div class="memory-item" onclick="showMemoryDetails('\${memory.id}')">
                    <h4>\${memory.title || 'Untitled'}</h4>
                    <p>\${memory.content.substring(0, 100)}...</p>
                    <div class="memory-meta">
                        <span class="type">\${memory.type}</span>
                        <span class="tags">\${memory.tags ? memory.tags.join(', ') : ''}</span>
                    </div>
                </div>
            \`).join('');
            
            container.innerHTML = html;
        }

        function handleMemoryCreated(result) {
            document.getElementById('create-form').reset();
            showSuccess('Memory created successfully');
        }

        function showMemoryModal(result) {
            const memory = result.memory;
            const modal = document.getElementById('memory-modal');
            const details = document.getElementById('memory-details');
            
            details.innerHTML = \`
                <h3>\${memory.title || 'Untitled'}</h3>
                <div class="memory-meta">
                    <span>Type: \${memory.type}</span>
                    <span>Created: \${new Date(memory.created_at).toLocaleDateString()}</span>
                </div>
                <div class="memory-tags">
                    \${memory.tags ? memory.tags.map(tag => \`<span class="tag">\${tag}</span>\`).join('') : ''}
                </div>
                <div class="memory-content">
                    <pre>\${memory.content}</pre>
                </div>
            \`;
            
            modal.style.display = 'block';
        }

        function displayGraphAnalysis(result) {
            const container = document.getElementById('graph-results');
            container.innerHTML = \`
                <h4>Graph Analysis</h4>
                <pre>\${JSON.stringify(result, null, 2)}</pre>
            \`;
        }

        function displayRecommendations(result) {
            const container = document.getElementById('insights-results');
            
            if (!result.recommendations || result.recommendations.length === 0) {
                container.innerHTML = '<p class="placeholder">No recommendations available</p>';
                return;
            }
            
            const html = result.recommendations.map(rec => \`
                <div class="recommendation-item">
                    <h4>\${rec.title || 'Recommendation'}</h4>
                    <p>\${rec.description}</p>
                    <div class="relevance">Relevance: \${rec.relevance ? rec.relevance.toFixed(2) : 'N/A'}</div>
                </div>
            \`).join('');
            
            container.innerHTML = \`<h4>Recommendations</h4>\${html}\`;
        }

        function showError(message) {
            // Simple error display - could be enhanced with better UI
            alert('Error: ' + message);
        }

        function showSuccess(message) {
            // Simple success display - could be enhanced with better UI
            const statusEl = document.getElementById('connection-status');
            const originalText = statusEl.textContent;
            statusEl.textContent = message;
            statusEl.className = 'status-success';
            setTimeout(() => {
                statusEl.textContent = originalText;
                statusEl.className = statusEl.textContent === 'Connected' ? 'status-connected' : 'status-disconnected';
            }, 3000);
        }

        // Initialize
        vscode.postMessage({ type: 'ready' });
    </script>
</body>
</html>`;
  }
}

function getNonce() {
  let text = '';
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
} 