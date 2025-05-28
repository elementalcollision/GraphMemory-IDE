# GraphMemory Cursor IDE Plugin

A production-ready Model Context Protocol (MCP) server that integrates GraphMemory-IDE's knowledge management capabilities directly into Cursor IDE.

## 🚀 Quick Start

### Prerequisites

- **Cursor IDE** with MCP support
- **Node.js 18+** installed
- **GraphMemory-IDE server** running (see [main README](../../README.md))

### Installation

1. **Clone or download the GraphMemory-IDE repository:**
   ```bash
   git clone https://github.com/your-org/GraphMemory-IDE.git
   cd GraphMemory-IDE/ide-plugins
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build the plugin:**
   ```bash
   npm run build
   ```

4. **Configure Cursor IDE:**
   
   Add the following to your Cursor MCP configuration file (usually `~/.cursor/mcp.json`):
   
   ```json
   {
     "mcpServers": {
       "graphmemory": {
         "command": "node",
         "args": ["server.js"],
         "cwd": "/path/to/GraphMemory-IDE/ide-plugins/cursor",
         "env": {
           "GRAPHMEMORY_SERVER_URL": "http://localhost:8000",
           "GRAPHMEMORY_AUTH_METHOD": "jwt",
           "GRAPHMEMORY_AUTH_TOKEN": "your-jwt-token-here"
         }
       }
     }
   }
   ```

5. **Restart Cursor IDE** to load the plugin.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GRAPHMEMORY_SERVER_URL` | GraphMemory server URL | `http://localhost:8000` | Yes |
| `GRAPHMEMORY_AUTH_METHOD` | Authentication method (`jwt`, `apikey`, `mtls`) | `jwt` | Yes |
| `GRAPHMEMORY_AUTH_TOKEN` | JWT token for authentication | - | If using JWT |
| `GRAPHMEMORY_AUTH_API_KEY` | API key for authentication | - | If using API key |
| `GRAPHMEMORY_DEBUG` | Enable debug logging | `false` | No |

### Authentication Methods

#### JWT Authentication (Recommended)
```json
{
  "env": {
    "GRAPHMEMORY_AUTH_METHOD": "jwt",
    "GRAPHMEMORY_AUTH_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### API Key Authentication
```json
{
  "env": {
    "GRAPHMEMORY_AUTH_METHOD": "apikey",
    "GRAPHMEMORY_AUTH_API_KEY": "your-api-key-here"
  }
}
```

#### mTLS Authentication (Enterprise)
```json
{
  "env": {
    "GRAPHMEMORY_AUTH_METHOD": "mtls",
    "GRAPHMEMORY_CERT_PATH": "/path/to/client.crt",
    "GRAPHMEMORY_KEY_PATH": "/path/to/client.key",
    "GRAPHMEMORY_CA_PATH": "/path/to/ca.crt"
  }
}
```

## 🛠️ Available Tools

The plugin provides 10 GraphMemory tools accessible through Cursor's AI chat:

### Memory Management
- **`memory_search`** - Search your memory graph semantically
- **`memory_create`** - Create new memory entries
- **`memory_update`** - Update existing memories
- **`memory_delete`** - Remove memories
- **`memory_relate`** - Create relationships between memories

### Graph Operations
- **`graph_query`** - Execute Cypher queries on your memory graph
- **`graph_analyze`** - Analyze graph structure and patterns

### Knowledge Discovery
- **`knowledge_cluster`** - Find related knowledge clusters
- **`knowledge_insights`** - Generate insights from memory patterns
- **`knowledge_recommend`** - Get recommendations based on context

## 💡 Usage Examples

### Search Memories
```
@graphmemory search for "React hooks performance optimization"
```

### Create Memory
```
@graphmemory create a memory about "useCallback optimization prevents unnecessary re-renders"
```

### Query Graph
```
@graphmemory query: MATCH (n:Memory)-[r:RELATED_TO]->(m:Memory) WHERE n.type = 'procedural' RETURN n, r, m LIMIT 10
```

### Get Recommendations
```
@graphmemory recommend related memories for "testing strategies"
```

## 🔍 Troubleshooting

### Common Issues

#### Plugin Not Loading
1. Check that Node.js 18+ is installed: `node --version`
2. Verify the `cwd` path in your MCP configuration
3. Ensure GraphMemory server is running and accessible
4. Check Cursor's MCP logs for error messages

#### Authentication Errors
1. Verify your JWT token is valid and not expired
2. Check that the server URL is correct and accessible
3. Ensure the authentication method matches your server configuration
4. Test connectivity: `curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/health`

#### Performance Issues
1. Check network connectivity to GraphMemory server
2. Monitor server logs for performance bottlenecks
3. Verify cache is enabled in configuration
4. Consider increasing timeout values for slow networks

### Debug Mode

Enable debug logging by setting:
```json
{
  "env": {
    "GRAPHMEMORY_DEBUG": "true"
  }
}
```

This will provide detailed logs in Cursor's MCP console.

### Log Locations

- **Cursor MCP Logs**: Available in Cursor's developer console
- **Plugin Logs**: Stdout/stderr from the MCP server process
- **GraphMemory Server Logs**: Check your GraphMemory server logs

## 📊 Performance

### Benchmarks

- **Memory Search**: < 2 seconds average response time
- **Memory Creation**: < 1 second average response time
- **Graph Queries**: < 3 seconds average response time
- **Cache Hit Rate**: > 80% for repeated operations

### Optimization Tips

1. **Enable Caching**: Ensure `cacheEnabled: true` in configuration
2. **Batch Operations**: Use batch requests for multiple operations
3. **Connection Pooling**: The plugin automatically manages connections
4. **Local Server**: Run GraphMemory server locally for best performance

## 🔒 Security

### Best Practices

1. **Secure Token Storage**: Store JWT tokens in environment variables
2. **Network Security**: Use HTTPS for production deployments
3. **Token Rotation**: Regularly rotate authentication tokens
4. **Access Control**: Implement proper user access controls on the server

### Enterprise Security

For enterprise deployments, consider:
- mTLS authentication for enhanced security
- VPN or private network connectivity
- Audit logging and monitoring
- Regular security assessments

## 🧪 Testing

Run the test suite to verify your installation:

```bash
# Run all tests
npm test

# Run specific test suites
npm run test:client
npm run test:integration
npm run test:performance

# Run with coverage
npm run test:coverage
```

## 📚 Additional Resources

- [GraphMemory-IDE Documentation](../../docs/)
- [API Guide](../../docs/API_GUIDE.md)
- [Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)

## 🤝 Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/your-org/GraphMemory-IDE/issues)
- **Discussions**: [Community discussions and Q&A](https://github.com/your-org/GraphMemory-IDE/discussions)
- **Documentation**: [Comprehensive guides and tutorials](../../docs/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.

---

**Made with ❤️ for the developer community** 