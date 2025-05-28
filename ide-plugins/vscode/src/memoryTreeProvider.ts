import * as vscode from 'vscode';
import { GraphMemoryMCPClient } from '../../shared/mcp-client';

/**
 * Memory Tree Item for VSCode Tree View
 */
export class MemoryTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly memory?: any,
    public readonly itemType: 'category' | 'memory' | 'tag' | 'relationship' = 'memory'
  ) {
    super(label, collapsibleState);
    
    this.tooltip = this.getTooltip();
    this.description = this.getDescription();
    this.contextValue = this.getContextValue();
    this.iconPath = this.getIconPath();
    
    if (memory) {
      this.command = {
        command: 'graphmemory.openMemory',
        title: 'Open Memory',
        arguments: [memory.id]
      };
    }
  }

  private getTooltip(): string {
    if (this.memory) {
      return `${this.memory.title || 'Untitled'}\n\nContent: ${this.memory.content.substring(0, 200)}${this.memory.content.length > 200 ? '...' : ''}\n\nTags: ${this.memory.tags?.join(', ') || 'None'}\nCreated: ${this.memory.created_at}`;
    }
    return this.label;
  }

  private getDescription(): string {
    if (this.memory) {
      const tags = this.memory.tags?.slice(0, 2).join(', ') || '';
      return tags ? `[${tags}]` : '';
    }
    return '';
  }

  private getContextValue(): string {
    switch (this.itemType) {
      case 'memory':
        return 'memory';
      case 'category':
        return 'category';
      case 'tag':
        return 'tag';
      case 'relationship':
        return 'relationship';
      default:
        return 'item';
    }
  }

  private getIconPath(): vscode.ThemeIcon {
    switch (this.itemType) {
      case 'memory':
        return new vscode.ThemeIcon('note');
      case 'category':
        return new vscode.ThemeIcon('folder');
      case 'tag':
        return new vscode.ThemeIcon('tag');
      case 'relationship':
        return new vscode.ThemeIcon('link');
      default:
        return new vscode.ThemeIcon('circle-outline');
    }
  }
}

/**
 * Memory Tree Provider for VSCode Sidebar
 * 
 * Provides hierarchical view of memories organized by:
 * - Recent memories
 * - Memory types
 * - Tags
 * - Relationships
 */
export class MemoryTreeProvider implements vscode.TreeDataProvider<MemoryTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<MemoryTreeItem | undefined | null | void> = new vscode.EventEmitter<MemoryTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<MemoryTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

  private client: GraphMemoryMCPClient | null = null;
  private memories: any[] = [];
  private isLoading = false;

  constructor() {}

  setClient(client: GraphMemoryMCPClient | null): void {
    this.client = client;
    this.refresh();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: MemoryTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: MemoryTreeItem): Promise<MemoryTreeItem[]> {
    if (!this.client) {
      return [
        new MemoryTreeItem(
          'Not connected to GraphMemory server',
          vscode.TreeItemCollapsibleState.None,
          undefined,
          'category'
        )
      ];
    }

    if (this.isLoading) {
      return [
        new MemoryTreeItem(
          'Loading memories...',
          vscode.TreeItemCollapsibleState.None,
          undefined,
          'category'
        )
      ];
    }

    try {
      if (!element) {
        // Root level - show main categories
        return this.getRootCategories();
      } else {
        // Child level - show category contents
        return this.getCategoryChildren(element);
      }
    } catch (error) {
      console.error('Error getting tree children:', error);
      return [
        new MemoryTreeItem(
          `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          vscode.TreeItemCollapsibleState.None,
          undefined,
          'category'
        )
      ];
    }
  }

  private async getRootCategories(): Promise<MemoryTreeItem[]> {
    await this.loadMemories();

    const categories: MemoryTreeItem[] = [];

    // Recent memories
    if (this.memories.length > 0) {
      categories.push(
        new MemoryTreeItem(
          `Recent Memories (${Math.min(this.memories.length, 10)})`,
          vscode.TreeItemCollapsibleState.Expanded,
          undefined,
          'category'
        )
      );
    }

    // Memory types
    const types = this.getUniqueTypes();
    if (types.length > 0) {
      categories.push(
        new MemoryTreeItem(
          `By Type (${types.length})`,
          vscode.TreeItemCollapsibleState.Collapsed,
          undefined,
          'category'
        )
      );
    }

    // Tags
    const tags = this.getUniqueTags();
    if (tags.length > 0) {
      categories.push(
        new MemoryTreeItem(
          `By Tag (${tags.length})`,
          vscode.TreeItemCollapsibleState.Collapsed,
          undefined,
          'category'
        )
      );
    }

    // Add search and create actions
    categories.push(
      new MemoryTreeItem(
        'Search Memories',
        vscode.TreeItemCollapsibleState.None,
        undefined,
        'category'
      )
    );

    categories.push(
      new MemoryTreeItem(
        'Create New Memory',
        vscode.TreeItemCollapsibleState.None,
        undefined,
        'category'
      )
    );

    return categories;
  }

  private async getCategoryChildren(element: MemoryTreeItem): Promise<MemoryTreeItem[]> {
    const label = element.label;

    if (label.startsWith('Recent Memories')) {
      return this.getRecentMemories();
    } else if (label.startsWith('By Type')) {
      return this.getTypeCategories();
    } else if (label.startsWith('By Tag')) {
      return this.getTagCategories();
    } else if (this.getUniqueTypes().includes(label)) {
      return this.getMemoriesByType(label);
    } else if (this.getUniqueTags().includes(label)) {
      return this.getMemoriesByTag(label);
    } else if (label === 'Search Memories') {
      // Trigger search command
      vscode.commands.executeCommand('graphmemory.searchMemories');
      return [];
    } else if (label === 'Create New Memory') {
      // Trigger create command
      vscode.commands.executeCommand('graphmemory.createMemory');
      return [];
    }

    return [];
  }

  private async loadMemories(): Promise<void> {
    if (!this.client || this.isLoading) {
      return;
    }

    try {
      this.isLoading = true;
      
      // Search for recent memories
      const result = await this.client.searchMemories({
        query: '',
        limit: 50,
        filters: {
          sort_by: 'created_at',
          sort_order: 'desc'
        }
      });

      this.memories = result.memories || [];
    } catch (error) {
      console.error('Failed to load memories:', error);
      this.memories = [];
    } finally {
      this.isLoading = false;
    }
  }

  private getRecentMemories(): MemoryTreeItem[] {
    return this.memories
      .slice(0, 10)
      .map(memory => new MemoryTreeItem(
        memory.title || memory.content.substring(0, 50) + '...',
        vscode.TreeItemCollapsibleState.None,
        memory,
        'memory'
      ));
  }

  private getTypeCategories(): MemoryTreeItem[] {
    const types = this.getUniqueTypes();
    return types.map(type => {
      const count = this.memories.filter(m => m.type === type).length;
      return new MemoryTreeItem(
        `${type} (${count})`,
        vscode.TreeItemCollapsibleState.Collapsed,
        undefined,
        'category'
      );
    });
  }

  private getTagCategories(): MemoryTreeItem[] {
    const tags = this.getUniqueTags();
    return tags.map(tag => {
      const count = this.memories.filter(m => m.tags?.includes(tag)).length;
      return new MemoryTreeItem(
        `${tag} (${count})`,
        vscode.TreeItemCollapsibleState.Collapsed,
        undefined,
        'tag'
      );
    });
  }

  private getMemoriesByType(type: string): MemoryTreeItem[] {
    return this.memories
      .filter(memory => memory.type === type)
      .map(memory => new MemoryTreeItem(
        memory.title || memory.content.substring(0, 50) + '...',
        vscode.TreeItemCollapsibleState.None,
        memory,
        'memory'
      ));
  }

  private getMemoriesByTag(tag: string): MemoryTreeItem[] {
    return this.memories
      .filter(memory => memory.tags?.includes(tag))
      .map(memory => new MemoryTreeItem(
        memory.title || memory.content.substring(0, 50) + '...',
        vscode.TreeItemCollapsibleState.None,
        memory,
        'memory'
      ));
  }

  private getUniqueTypes(): string[] {
    const types = new Set<string>();
    this.memories.forEach(memory => {
      if (memory.type) {
        types.add(memory.type);
      }
    });
    return Array.from(types).sort();
  }

  private getUniqueTags(): string[] {
    const tags = new Set<string>();
    this.memories.forEach(memory => {
      if (memory.tags) {
        memory.tags.forEach((tag: string) => tags.add(tag));
      }
    });
    return Array.from(tags).sort();
  }

  // Public methods for external use
  async searchMemories(query: string): Promise<void> {
    if (!this.client) {
      return;
    }

    try {
      this.isLoading = true;
      this.refresh();

      const result = await this.client.searchMemories({
        query,
        limit: 50
      });

      this.memories = result.memories || [];
      this.refresh();
    } catch (error) {
      console.error('Search failed:', error);
      vscode.window.showErrorMessage(`Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      this.isLoading = false;
    }
  }

  async createMemory(content: string, title?: string, tags?: string[]): Promise<void> {
    if (!this.client) {
      return;
    }

    try {
      await this.client.createMemory({
        content,
        title,
        tags,
        type: 'note'
      });

      // Refresh the tree to show the new memory
      await this.loadMemories();
      this.refresh();
    } catch (error) {
      console.error('Create memory failed:', error);
      throw error;
    }
  }

  async deleteMemory(memoryId: string): Promise<void> {
    if (!this.client) {
      return;
    }

    try {
      await this.client.deleteMemory({ id: memoryId });

      // Remove from local cache and refresh
      this.memories = this.memories.filter(m => m.id !== memoryId);
      this.refresh();
    } catch (error) {
      console.error('Delete memory failed:', error);
      throw error;
    }
  }
} 