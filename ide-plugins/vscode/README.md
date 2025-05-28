# GraphMemory VSCode Extension

AI-powered memory management for developers using GraphMemory-IDE. This extension provides native VSCode integration with the GraphMemory system, enabling seamless knowledge capture, search, and discovery within your development workflow.

## 🚀 Features

### Core Memory Management
- **Search Memories**: Semantic search across your knowledge base with relevance scoring
- **Create Memories**: Capture code snippets, notes, ideas, and documentation
- **Update/Delete**: Full CRUD operations with confirmation dialogs
- **Memory Types**: Support for notes, code, ideas, tasks, and references
- **Tagging System**: Organize memories with flexible tagging

### Advanced Graph Operations
- **Graph Queries**: Execute Cypher queries against your memory graph
- **Relationship Management**: Create and visualize connections between memories
- **Graph Analysis**: Discover patterns and insights in your knowledge structure
- **Knowledge Clustering**: Automatic grouping of related concepts

### VSCode Integration
- **Command Palette**: All operations accessible via `Ctrl+Shift+P`
- **Sidebar Tree View**: Hierarchical memory browser with categories
- **Interactive Webview**: Rich UI for detailed memory management
- **Status Bar**: Connection status and quick actions
- **Context Menus**: Right-click integration for selected text
- **Auto-completion**: Smart suggestions based on your memory graph

### Intelligent Features
- **Semantic Search**: Find memories by meaning, not just keywords
- **Personalized Recommendations**: Context-aware suggestions
- **Insight Generation**: Discover patterns in your development knowledge
- **Workspace Integration**: Automatic context from current file and project

## 📦 Installation

### Prerequisites
- VSCode 1.85.0 or higher
- GraphMemory server running (see [main documentation](../../README.md))
- Node.js 18+ for development

### From VSIX Package
1. Download the latest `.vsix` file from releases
2. Open VSCode
3. Press `Ctrl+Shift+P` and run "Extensions: Install from VSIX..."
4. Select the downloaded `.vsix` file

### From Source
```bash
cd ide-plugins/vscode
npm install
npm run compile
npm run package
code --install-extension graphmemory-vscode-1.0.0.vsix
```

## ⚙️ Configuration

Configure the extension through VSCode settings (`Ctrl+,`):

### Server Connection
```json
{
  "graphmemory.serverUrl": "http://localhost:8000",
  "graphmemory.auth.method": "jwt",
  "graphmemory.auth.token": "your-jwt-token",
  "graphmemory.auth.apiKey": "your-api-key"
}
```

### Features
```json
{
  "graphmemory.features.autoComplete": true,
  "graphmemory.features.semanticSearch": true,
  "graphmemory.features.graphVisualization": true
}
```

### Performance
```json
{
  "graphmemory.performance.cacheEnabled": true,
  "graphmemory.performance.cacheSize": 100,
  "graphmemory.performance.maxConcurrentRequests": 5,
  "graphmemory.performance.requestTimeout": 30000
}
```

## 🎯 Usage

### Quick Start
1. **Connect to Server**: Click the GraphMemory status bar item or use `GraphMemory: Connect to Server`
2. **Create Your First Memory**: Select text and use `GraphMemory: Create Memory`
3. **Search Memories**: Use `GraphMemory: Search Memories` or the sidebar search
4. **Explore Relationships**: Use `GraphMemory: Analyze Memory Graph`

### Command Palette Operations
All commands are available via `Ctrl+Shift+P`:

- `GraphMemory: Search Memories` - Search your knowledge base
- `GraphMemory: Create Memory` - Create new memory from selection or input
- `GraphMemory: Update Memory` - Edit existing memory
- `GraphMemory: Delete Memory` - Remove memory with confirmation
- `GraphMemory: Relate Memories` - Create relationships between memories
- `GraphMemory: Query Graph` - Execute Cypher queries
- `GraphMemory: Analyze Graph` - Analyze memory structure
- `GraphMemory: Get Recommendations` - Get personalized suggestions
- `GraphMemory: Show Memory Panel` - Open interactive webview

### Sidebar Tree View
The GraphMemory sidebar provides:
- **Recent Memories**: Latest 10 memories
- **By Type**: Memories grouped by type (note, code, idea, etc.)
- **By Tag**: Memories organized by tags
- **Quick Actions**: Search and create shortcuts

### Interactive Webview
The webview panel offers:
- **Search Tab**: Advanced search with filters
- **Create Tab**: Rich memory creation form
- **Graph Tab**: Graph analysis and recommendations
- **Insights Tab**: Pattern discovery and clustering

### Context Integration
The extension automatically captures context:
- Current workspace name
- Active file path and language
- Selected text content
- Timestamp and metadata

## 🔧 Development

### Setup Development Environment
```bash
# Clone the repository
git clone https://github.com/your-org/GraphMemory-IDE.git
cd GraphMemory-IDE/ide-plugins/vscode

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch
```

### Build and Package
```bash
# Compile for production
npm run compile

# Package extension
npm run package

# Install locally
code --install-extension graphmemory-vscode-1.0.0.vsix
```

### Testing
```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage

# Integration tests
npm run test:integration
```

### Debugging
1. Open the project in VSCode
2. Press `F5` to launch Extension Development Host
3. Set breakpoints in TypeScript files
4. Test extension functionality in the new window

## 🔍 Architecture

### Extension Structure
```
src/
├── extension.ts          # Main extension entry point
├── memoryTreeProvider.ts # Sidebar tree view provider
├── commands.ts           # Command implementations
├── webviewProvider.ts    # Interactive webview panel
└── types.ts             # TypeScript type definitions

media/                   # Webview assets
├── main.css            # Webview styles
└── main.js             # Webview scripts (if needed)
```

### Key Components

#### GraphMemoryExtension
- Main extension class managing lifecycle
- Command registration and event handling
- Configuration management and auto-connection
- Status bar integration

#### MemoryTreeProvider
- Implements VSCode TreeDataProvider interface
- Hierarchical memory organization
- Real-time updates and refresh capabilities
- Context menu integration

#### GraphMemoryCommands
- All GraphMemory operation implementations
- VSCode-specific UI integration (dialogs, progress, etc.)
- Error handling and user feedback
- Result display and formatting

#### GraphMemoryWebviewProvider
- Rich interactive UI using VSCode webviews
- Bidirectional communication with extension
- Tabbed interface for different operations
- Modal dialogs for detailed views

### Integration with Shared Library
The extension leverages the shared MCP client library:
- `GraphMemoryMCPClient` for server communication
- `MCPClientConfig` for configuration management
- Utility functions for validation and error handling
- Type definitions for consistent interfaces

## 🐛 Troubleshooting

### Common Issues

#### Connection Problems
**Symptom**: "Not connected to GraphMemory server"
**Solutions**:
1. Verify server URL in settings
2. Check authentication credentials
3. Ensure GraphMemory server is running
4. Check network connectivity and firewall

#### Authentication Errors
**Symptom**: "Authentication failed" or 401 errors
**Solutions**:
1. Verify JWT token is valid and not expired
2. Check API key format and permissions
3. Ensure auth method matches server configuration
4. Regenerate credentials if necessary

#### Performance Issues
**Symptom**: Slow search or operation timeouts
**Solutions**:
1. Reduce cache size in settings
2. Lower concurrent request limit
3. Increase request timeout
4. Check server performance and resources

#### Extension Not Loading
**Symptom**: Commands not available or extension inactive
**Solutions**:
1. Restart VSCode
2. Check extension is enabled in Extensions view
3. Verify VSCode version compatibility
4. Check Developer Console for errors

### Debug Information
Enable debug logging:
```json
{
  "graphmemory.debug": true
}
```

Check logs in:
- VSCode Developer Console (`Help > Toggle Developer Tools`)
- Extension Host output channel
- GraphMemory server logs

### Getting Help
1. Check the [main documentation](../../README.md)
2. Review [troubleshooting guide](../../TROUBLESHOOTING.md)
3. Search existing [GitHub issues](https://github.com/your-org/GraphMemory-IDE/issues)
4. Create a new issue with:
   - VSCode version
   - Extension version
   - Error messages
   - Steps to reproduce

## 📝 Configuration Reference

### Complete Settings Schema
```json
{
  "graphmemory.serverUrl": {
    "type": "string",
    "default": "http://localhost:8000",
    "description": "GraphMemory server URL"
  },
  "graphmemory.auth.method": {
    "type": "string",
    "enum": ["jwt", "apikey", "mtls"],
    "default": "jwt",
    "description": "Authentication method"
  },
  "graphmemory.auth.token": {
    "type": "string",
    "description": "JWT token for authentication"
  },
  "graphmemory.auth.apiKey": {
    "type": "string",
    "description": "API key for authentication"
  },
  "graphmemory.features.autoComplete": {
    "type": "boolean",
    "default": true,
    "description": "Enable auto-completion suggestions"
  },
  "graphmemory.features.semanticSearch": {
    "type": "boolean",
    "default": true,
    "description": "Enable semantic search"
  },
  "graphmemory.features.graphVisualization": {
    "type": "boolean",
    "default": true,
    "description": "Enable graph visualization"
  },
  "graphmemory.performance.cacheEnabled": {
    "type": "boolean",
    "default": true,
    "description": "Enable response caching"
  },
  "graphmemory.performance.cacheSize": {
    "type": "number",
    "default": 100,
    "description": "Maximum cache size"
  },
  "graphmemory.performance.maxConcurrentRequests": {
    "type": "number",
    "default": 5,
    "description": "Maximum concurrent requests"
  },
  "graphmemory.performance.requestTimeout": {
    "type": "number",
    "default": 30000,
    "description": "Request timeout in milliseconds"
  },
  "graphmemory.debug": {
    "type": "boolean",
    "default": false,
    "description": "Enable debug logging"
  }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Guidelines
- Follow TypeScript best practices
- Use VSCode extension API patterns
- Maintain backward compatibility
- Add comprehensive error handling
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

## 🔗 Related

- [GraphMemory-IDE Main Documentation](../../README.md)
- [Cursor Plugin](../cursor/README.md)
- [Windsurf Plugin](../windsurf/README.md)
- [Shared Library](../shared/README.md)
- [API Documentation](../../docs/API_GUIDE.md) 