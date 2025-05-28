import * as vscode from 'vscode';
import { GraphMemoryMCPClient } from '../../shared/mcp-client';
import { ErrorHelper } from '../../shared/utils';

/**
 * GraphMemory Commands for VSCode Extension
 * 
 * Implements all GraphMemory operations with VSCode-specific UI integration:
 * - Input dialogs and quick picks
 * - Progress indicators
 * - Error handling and user feedback
 * - Result display in appropriate formats
 */
export class GraphMemoryCommands {
  
  /**
   * Search memories with interactive query input
   */
  async searchMemories(client: GraphMemoryMCPClient | null, initialQuery?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const query = initialQuery || await vscode.window.showInputBox({
        prompt: 'Enter search query',
        placeHolder: 'Search memories by content, tags, or metadata...',
        value: this.getSelectedText()
      });

      if (!query) {
        return;
      }

      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Searching memories...',
        cancellable: false
      }, async () => {
        return await client.searchMemories({
          query,
          limit: 20,
          filters: {
            include_content: true,
            include_metadata: true
          }
        });
      });

      await this.displaySearchResults(result, query);

    } catch (error) {
      vscode.window.showErrorMessage(`Search failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Create new memory with content from selection or input
   */
  async createMemory(client: GraphMemoryMCPClient | null, initialContent?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const content = initialContent || this.getSelectedText() || await vscode.window.showInputBox({
        prompt: 'Enter memory content',
        placeHolder: 'What would you like to remember?',
        value: ''
      });

      if (!content) {
        return;
      }

      // Get optional title
      const title = await vscode.window.showInputBox({
        prompt: 'Enter memory title (optional)',
        placeHolder: 'Brief title for this memory...'
      });

      // Get optional tags
      const tagsInput = await vscode.window.showInputBox({
        prompt: 'Enter tags (optional, comma-separated)',
        placeHolder: 'tag1, tag2, tag3...'
      });

      const tags = tagsInput ? tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

      // Select memory type
      const type = await vscode.window.showQuickPick([
        { label: 'Note', value: 'note', description: 'General note or observation' },
        { label: 'Code', value: 'code', description: 'Code snippet or technical solution' },
        { label: 'Idea', value: 'idea', description: 'Creative idea or concept' },
        { label: 'Task', value: 'task', description: 'Task or todo item' },
        { label: 'Reference', value: 'reference', description: 'Reference material or documentation' }
      ], {
        placeHolder: 'Select memory type'
      });

      if (!type) {
        return;
      }

      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Creating memory...',
        cancellable: false
      }, async () => {
        return await client.createMemory({
          content,
          title,
          tags,
          type: type.value,
          metadata: {
            source: 'vscode',
            workspace: vscode.workspace.name,
            file: vscode.window.activeTextEditor?.document.fileName
          }
        });
      });

      vscode.window.showInformationMessage(`Memory created: ${result.memory.title || 'Untitled'}`);
      vscode.commands.executeCommand('graphmemory.refreshMemories');

    } catch (error) {
      vscode.window.showErrorMessage(`Failed to create memory: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Update existing memory
   */
  async updateMemory(client: GraphMemoryMCPClient | null, memoryId?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      // If no memory ID provided, let user search and select
      if (!memoryId) {
        const searchResult = await this.selectMemoryFromSearch(client, 'Select memory to update');
        if (!searchResult) {
          return;
        }
        memoryId = searchResult.id;
      }

      // Get current memory details
      const memory = await client.getMemory({ id: memoryId });

      // Update content
      const newContent = await vscode.window.showInputBox({
        prompt: 'Update memory content',
        value: memory.memory.content,
        valueSelection: [0, memory.memory.content.length]
      });

      if (newContent === undefined) {
        return;
      }

      // Update title
      const newTitle = await vscode.window.showInputBox({
        prompt: 'Update memory title (optional)',
        value: memory.memory.title || ''
      });

      // Update tags
      const currentTags = memory.memory.tags?.join(', ') || '';
      const newTagsInput = await vscode.window.showInputBox({
        prompt: 'Update tags (comma-separated)',
        value: currentTags
      });

      const newTags = newTagsInput ? newTagsInput.split(',').map(tag => tag.trim()).filter(tag => tag) : [];

      await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Updating memory...',
        cancellable: false
      }, async () => {
        await client.updateMemory({
          id: memoryId!,
          content: newContent,
          title: newTitle,
          tags: newTags
        });
      });

      vscode.window.showInformationMessage('Memory updated successfully');
      vscode.commands.executeCommand('graphmemory.refreshMemories');

    } catch (error) {
      vscode.window.showErrorMessage(`Failed to update memory: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Delete memory with confirmation
   */
  async deleteMemory(client: GraphMemoryMCPClient | null, memoryId?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      // If no memory ID provided, let user search and select
      if (!memoryId) {
        const searchResult = await this.selectMemoryFromSearch(client, 'Select memory to delete');
        if (!searchResult) {
          return;
        }
        memoryId = searchResult.id;
      }

      // Get memory details for confirmation
      const memory = await client.getMemory({ id: memoryId });
      const title = memory.memory.title || memory.memory.content.substring(0, 50) + '...';

      // Confirm deletion
      const confirm = await vscode.window.showWarningMessage(
        `Are you sure you want to delete "${title}"?`,
        { modal: true },
        'Delete'
      );

      if (confirm !== 'Delete') {
        return;
      }

      await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Deleting memory...',
        cancellable: false
      }, async () => {
        await client.deleteMemory({ id: memoryId! });
      });

      vscode.window.showInformationMessage('Memory deleted successfully');
      vscode.commands.executeCommand('graphmemory.refreshMemories');

    } catch (error) {
      vscode.window.showErrorMessage(`Failed to delete memory: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Create relationship between memories
   */
  async relateMemories(client: GraphMemoryMCPClient | null, sourceId?: string, targetId?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      // Select source memory
      if (!sourceId) {
        const sourceMemory = await this.selectMemoryFromSearch(client, 'Select source memory');
        if (!sourceMemory) {
          return;
        }
        sourceId = sourceMemory.id;
      }

      // Select target memory
      if (!targetId) {
        const targetMemory = await this.selectMemoryFromSearch(client, 'Select target memory');
        if (!targetMemory) {
          return;
        }
        targetId = targetMemory.id;
      }

      // Select relationship type
      const relationshipType = await vscode.window.showQuickPick([
        { label: 'Related to', value: 'related_to', description: 'General relationship' },
        { label: 'Depends on', value: 'depends_on', description: 'Dependency relationship' },
        { label: 'Similar to', value: 'similar_to', description: 'Similarity relationship' },
        { label: 'Contradicts', value: 'contradicts', description: 'Contradictory relationship' },
        { label: 'Builds on', value: 'builds_on', description: 'Building/extending relationship' }
      ], {
        placeHolder: 'Select relationship type'
      });

      if (!relationshipType) {
        return;
      }

      await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Creating relationship...',
        cancellable: false
      }, async () => {
        await client.relateMemories({
          source_id: sourceId!,
          target_id: targetId!,
          relationship_type: relationshipType.value
        });
      });

      vscode.window.showInformationMessage('Memory relationship created successfully');

    } catch (error) {
      vscode.window.showErrorMessage(`Failed to create relationship: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Execute graph query with Cypher
   */
  async queryGraph(client: GraphMemoryMCPClient | null, initialQuery?: string): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const query = initialQuery || await vscode.window.showInputBox({
        prompt: 'Enter Cypher query',
        placeHolder: 'MATCH (m:Memory) RETURN m LIMIT 10',
        value: 'MATCH (m:Memory) RETURN m LIMIT 10'
      });

      if (!query) {
        return;
      }

      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Executing graph query...',
        cancellable: false
      }, async () => {
        return await client.queryGraph({ query });
      });

      await this.displayQueryResults(result, query);

    } catch (error) {
      vscode.window.showErrorMessage(`Query failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Analyze memory graph structure
   */
  async analyzeGraph(client: GraphMemoryMCPClient | null): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Analyzing memory graph...',
        cancellable: false
      }, async () => {
        return await client.analyzeGraph({});
      });

      await this.displayAnalysisResults(result);

    } catch (error) {
      vscode.window.showErrorMessage(`Analysis failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Cluster knowledge for pattern discovery
   */
  async clusterKnowledge(client: GraphMemoryMCPClient | null): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Clustering knowledge...',
        cancellable: false
      }, async () => {
        return await client.clusterKnowledge({});
      });

      await this.displayClusterResults(result);

    } catch (error) {
      vscode.window.showErrorMessage(`Clustering failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Generate insights from memory patterns
   */
  async generateInsights(client: GraphMemoryMCPClient | null): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Generating insights...',
        cancellable: false
      }, async () => {
        return await client.generateInsights({});
      });

      await this.displayInsights(result);

    } catch (error) {
      vscode.window.showErrorMessage(`Insight generation failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  /**
   * Get personalized recommendations
   */
  async getRecommendations(client: GraphMemoryMCPClient | null): Promise<void> {
    if (!client) {
      vscode.window.showWarningMessage('Not connected to GraphMemory server');
      return;
    }

    try {
      const context = this.getCurrentContext();
      
      const result = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'Getting recommendations...',
        cancellable: false
      }, async () => {
        return await client.getRecommendations({ context });
      });

      await this.displayRecommendations(result);

    } catch (error) {
      vscode.window.showErrorMessage(`Recommendations failed: ${ErrorHelper.formatError(error)}`);
    }
  }

  // Helper methods

  private getSelectedText(): string {
    const editor = vscode.window.activeTextEditor;
    if (editor && !editor.selection.isEmpty) {
      return editor.document.getText(editor.selection);
    }
    return '';
  }

  private getCurrentContext(): any {
    const editor = vscode.window.activeTextEditor;
    return {
      workspace: vscode.workspace.name,
      file: editor?.document.fileName,
      language: editor?.document.languageId,
      selection: this.getSelectedText(),
      timestamp: new Date().toISOString()
    };
  }

  private async selectMemoryFromSearch(client: GraphMemoryMCPClient, prompt: string): Promise<any | null> {
    const query = await vscode.window.showInputBox({
      prompt: 'Search for memory',
      placeHolder: 'Enter search terms...'
    });

    if (!query) {
      return null;
    }

    const searchResult = await client.searchMemories({
      query,
      limit: 20
    });

    if (!searchResult.memories || searchResult.memories.length === 0) {
      vscode.window.showInformationMessage('No memories found');
      return null;
    }

    const selected = await vscode.window.showQuickPick(
      searchResult.memories.map(memory => ({
        label: memory.title || memory.content.substring(0, 50) + '...',
        description: memory.tags?.join(', ') || '',
        detail: memory.content.substring(0, 100) + '...',
        memory
      })),
      { placeHolder: prompt }
    );

    return selected?.memory || null;
  }

  private async displaySearchResults(result: any, query: string): Promise<void> {
    if (!result.memories || result.memories.length === 0) {
      vscode.window.showInformationMessage(`No memories found for "${query}"`);
      return;
    }

    const selected = await vscode.window.showQuickPick(
      result.memories.map((memory: any) => ({
        label: memory.title || memory.content.substring(0, 50) + '...',
        description: `Score: ${memory.score?.toFixed(2) || 'N/A'}`,
        detail: memory.content.substring(0, 100) + '...',
        memory
      })),
      {
        placeHolder: `Found ${result.memories.length} memories for "${query}"`,
        matchOnDescription: true,
        matchOnDetail: true
      }
    );

    if (selected) {
      await this.openMemoryDetails(selected.memory);
    }
  }

  private async displayQueryResults(result: any, query: string): Promise<void> {
    const document = await vscode.workspace.openTextDocument({
      content: `Graph Query Results\n==================\n\nQuery: ${query}\n\nResults:\n${JSON.stringify(result, null, 2)}`,
      language: 'json'
    });
    await vscode.window.showTextDocument(document);
  }

  private async displayAnalysisResults(result: any): Promise<void> {
    const document = await vscode.workspace.openTextDocument({
      content: `Memory Graph Analysis\n====================\n\n${JSON.stringify(result, null, 2)}`,
      language: 'json'
    });
    await vscode.window.showTextDocument(document);
  }

  private async displayClusterResults(result: any): Promise<void> {
    const document = await vscode.workspace.openTextDocument({
      content: `Knowledge Clusters\n=================\n\n${JSON.stringify(result, null, 2)}`,
      language: 'json'
    });
    await vscode.window.showTextDocument(document);
  }

  private async displayInsights(result: any): Promise<void> {
    const insights = result.insights || [];
    const content = `Memory Insights\n==============\n\n${insights.map((insight: any, index: number) => 
      `${index + 1}. ${insight.title}\n   ${insight.description}\n   Confidence: ${insight.confidence}\n`
    ).join('\n')}`;

    const document = await vscode.workspace.openTextDocument({
      content,
      language: 'markdown'
    });
    await vscode.window.showTextDocument(document);
  }

  private async displayRecommendations(result: any): Promise<void> {
    const recommendations = result.recommendations || [];
    
    if (recommendations.length === 0) {
      vscode.window.showInformationMessage('No recommendations available');
      return;
    }

    const selected = await vscode.window.showQuickPick(
      recommendations.map((rec: any) => ({
        label: rec.title || 'Recommendation',
        description: `Relevance: ${rec.relevance?.toFixed(2) || 'N/A'}`,
        detail: rec.description,
        recommendation: rec
      })),
      {
        placeHolder: `${recommendations.length} recommendations available`,
        matchOnDescription: true,
        matchOnDetail: true
      }
    );

    if (selected && selected.recommendation.memory_id) {
      const memory = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Window,
        title: 'Loading memory...'
      }, async () => {
        const client = this.getClient();
        if (client) {
          const result = await client.getMemory({ id: selected.recommendation.memory_id });
          return result.memory;
        }
        return null;
      });

      if (memory) {
        await this.openMemoryDetails(memory);
      }
    }
  }

  private async openMemoryDetails(memory: any): Promise<void> {
    const content = `Memory Details\n=============\n\nTitle: ${memory.title || 'Untitled'}\nType: ${memory.type || 'Unknown'}\nTags: ${memory.tags?.join(', ') || 'None'}\nCreated: ${memory.created_at}\nUpdated: ${memory.updated_at}\n\nContent:\n--------\n${memory.content}\n\nMetadata:\n--------\n${JSON.stringify(memory.metadata || {}, null, 2)}`;

    const document = await vscode.workspace.openTextDocument({
      content,
      language: 'markdown'
    });
    await vscode.window.showTextDocument(document);
  }

  private getClient(): GraphMemoryMCPClient | null {
    // This would need to be injected or accessed through the extension context
    // For now, return null - this will be properly wired in the extension
    return null;
  }
} 