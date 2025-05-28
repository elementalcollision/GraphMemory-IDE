#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { GraphMemoryMCPClient } from '../shared/mcp-client.js';
import { MCPClientConfig, GRAPHMEMORY_TOOLS } from '../shared/types.js';
import { ConfigLoader, ValidationHelper, ErrorHelper } from '../shared/utils.js';

/**
 * GraphMemory MCP Server for Cursor IDE
 * 
 * This server acts as a bridge between Cursor IDE and GraphMemory-IDE,
 * exposing GraphMemory tools through the Model Context Protocol.
 */
class GraphMemoryCursorServer {
  private server: Server;
  private client: GraphMemoryMCPClient | null = null;
  private config: MCPClientConfig;

  constructor() {
    this.server = new Server(
      {
        name: 'graphmemory-cursor',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.config = this.loadConfiguration();
    this.setupHandlers();
  }

  private loadConfiguration(): MCPClientConfig {
    // Load configuration from environment variables and config files
    const envConfig = ConfigLoader.loadFromEnv('GRAPHMEMORY_');
    const fileConfig = ConfigLoader.loadFromHomeDir();
    
    const serverUrl = process.env.GRAPHMEMORY_SERVER_URL || 
                     envConfig?.server?.url || 
                     fileConfig?.server?.url || 
                     'http://localhost:8000';

    const authMethod = process.env.GRAPHMEMORY_AUTH_METHOD || 
                      envConfig?.auth?.method || 
                      fileConfig?.auth?.method || 
                      'jwt';

    const authToken = process.env.GRAPHMEMORY_AUTH_TOKEN || 
                     envConfig?.auth?.token || 
                     fileConfig?.auth?.token;

    const authApiKey = process.env.GRAPHMEMORY_AUTH_API_KEY || 
                      envConfig?.auth?.apiKey || 
                      fileConfig?.auth?.apiKey;

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
        autoComplete: true,
        semanticSearch: true,
        graphVisualization: true,
        batchRequests: true
      },
      performance: {
        cacheEnabled: true,
        cacheSize: 100,
        maxConcurrentRequests: 5,
        requestTimeout: 30000
      }
    };
  }

  private setupHandlers(): void {
    // Handle tool listing
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      const tools = Object.values(GRAPHMEMORY_TOOLS).map(tool => ({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema
      }));

      return { tools };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        // Ensure client is connected
        if (!this.client) {
          await this.connectToGraphMemory();
        }

        // Validate tool name
        if (!(name in GRAPHMEMORY_TOOLS)) {
          throw new Error(`Unknown tool: ${name}`);
        }

        // Call the appropriate tool method
        let result;
        switch (name) {
          case 'memory_search':
            result = await this.client!.searchMemories(args);
            break;
          case 'memory_create':
            result = await this.client!.createMemory(args);
            break;
          case 'memory_update':
            result = await this.client!.updateMemory(args);
            break;
          case 'memory_delete':
            await this.client!.deleteMemory(args);
            result = { success: true, message: 'Memory deleted successfully' };
            break;
          case 'memory_relate':
            await this.client!.relateMemories(args);
            result = { success: true, message: 'Memories related successfully' };
            break;
          case 'graph_query':
            result = await this.client!.queryGraph(args);
            break;
          case 'graph_analyze':
            result = await this.client!.analyzeGraph(args);
            break;
          case 'knowledge_cluster':
            result = await this.client!.clusterKnowledge(args);
            break;
          case 'knowledge_insights':
            result = await this.client!.generateInsights(args);
            break;
          case 'knowledge_recommend':
            result = await this.client!.getRecommendations(args);
            break;
          default:
            throw new Error(`Tool not implemented: ${name}`);
        }

        return {
          content: [
            {
              type: 'text',
              text: this.formatToolResult(name, result)
            }
          ]
        };

      } catch (error) {
        const errorMessage = ErrorHelper.formatError(error);
        console.error(`Tool call failed for ${name}:`, errorMessage);

        return {
          content: [
            {
              type: 'text',
              text: `Error: ${errorMessage}`
            }
          ],
          isError: true
        };
      }
    });
  }

  private async connectToGraphMemory(): Promise<void> {
    try {
      this.client = new GraphMemoryMCPClient(this.config, this.createLogger());
      
      // Set up event handlers
      this.client.on('connection', (event) => {
        console.log('Connected to GraphMemory server:', event.data.serverUrl);
      });

      this.client.on('error', (event) => {
        console.error('GraphMemory client error:', event.data.error);
      });

      this.client.on('performance', (event) => {
        if (process.env.GRAPHMEMORY_DEBUG === 'true') {
          console.debug('Performance metric:', event.data);
        }
      });

      await this.client.connect();
    } catch (error) {
      console.error('Failed to connect to GraphMemory server:', ErrorHelper.formatError(error));
      throw error;
    }
  }

  private formatToolResult(toolName: string, result: any): string {
    try {
      switch (toolName) {
        case 'memory_search':
          return this.formatSearchResult(result);
        case 'memory_create':
        case 'memory_update':
          return this.formatMemoryResult(result);
        case 'graph_analyze':
          return this.formatAnalysisResult(result);
        case 'knowledge_cluster':
          return this.formatClusterResult(result);
        case 'knowledge_insights':
          return this.formatInsightsResult(result);
        case 'knowledge_recommend':
          return this.formatRecommendationsResult(result);
        default:
          return JSON.stringify(result, null, 2);
      }
    } catch (error) {
      console.warn('Failed to format result, returning raw JSON:', error);
      return JSON.stringify(result, null, 2);
    }
  }

  private formatSearchResult(result: any): string {
    const { memories, total, query_time } = result;
    
    let output = `Found ${total} memories (${query_time}ms)\n\n`;
    
    for (const memory of memories) {
      output += `**${memory.type.toUpperCase()}** - ${memory.content.substring(0, 100)}...\n`;
      output += `Tags: ${memory.tags.join(', ')}\n`;
      output += `Created: ${new Date(memory.created_at).toLocaleDateString()}\n\n`;
    }
    
    return output;
  }

  private formatMemoryResult(memory: any): string {
    return `**Memory ${memory.id}**\n` +
           `Type: ${memory.type}\n` +
           `Content: ${memory.content}\n` +
           `Tags: ${memory.tags.join(', ')}\n` +
           `Created: ${new Date(memory.created_at).toLocaleDateString()}`;
  }

  private formatAnalysisResult(result: any): string {
    const { analysis_type, results, insights } = result;
    
    let output = `**Graph Analysis: ${analysis_type}**\n\n`;
    
    if (insights && insights.length > 0) {
      output += '**Key Insights:**\n';
      for (const insight of insights) {
        output += `• ${insight}\n`;
      }
      output += '\n';
    }
    
    output += '**Results:**\n';
    output += JSON.stringify(results, null, 2);
    
    return output;
  }

  private formatClusterResult(result: any): string {
    const { clusters, algorithm } = result;
    
    let output = `**Knowledge Clusters (${algorithm})**\n\n`;
    
    for (const cluster of clusters) {
      output += `**Cluster ${cluster.id}**\n`;
      output += `Keywords: ${cluster.keywords.join(', ')}\n`;
      output += `Memories: ${cluster.memories.length}\n`;
      output += `Centroid: ${cluster.centroid}\n\n`;
    }
    
    return output;
  }

  private formatInsightsResult(result: any): string {
    const { insights, context } = result;
    
    let output = `**Knowledge Insights**\n`;
    if (context) {
      output += `Context: ${context}\n\n`;
    }
    
    for (const insight of insights) {
      output += `**${insight.type.toUpperCase()}** (${Math.round(insight.confidence * 100)}%)\n`;
      output += `${insight.description}\n`;
      if (insight.supporting_evidence.length > 0) {
        output += `Evidence: ${insight.supporting_evidence.join(', ')}\n`;
      }
      output += '\n';
    }
    
    return output;
  }

  private formatRecommendationsResult(result: any): string {
    const { recommendations, context, recommendation_type } = result;
    
    let output = `**${recommendation_type.toUpperCase()} Recommendations**\n`;
    if (context) {
      output += `Context: ${context}\n\n`;
    }
    
    for (const rec of recommendations) {
      output += `**${rec.memory.type.toUpperCase()}** (Score: ${Math.round(rec.score * 100)}%)\n`;
      output += `${rec.memory.content.substring(0, 150)}...\n`;
      output += `Reason: ${rec.reason}\n`;
      output += `Tags: ${rec.memory.tags.join(', ')}\n\n`;
    }
    
    return output;
  }

  private createLogger() {
    const isDebug = process.env.GRAPHMEMORY_DEBUG === 'true';
    
    return {
      debug: (message: string, ...args: any[]) => {
        if (isDebug) console.debug(`[GraphMemory] ${message}`, ...args);
      },
      info: (message: string, ...args: any[]) => {
        console.info(`[GraphMemory] ${message}`, ...args);
      },
      warn: (message: string, ...args: any[]) => {
        console.warn(`[GraphMemory] ${message}`, ...args);
      },
      error: (message: string, ...args: any[]) => {
        console.error(`[GraphMemory] ${message}`, ...args);
      }
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.error('GraphMemory MCP server running on stdio');
  }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.error('Shutting down GraphMemory MCP server...');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('Shutting down GraphMemory MCP server...');
  process.exit(0);
});

// Start the server
const server = new GraphMemoryCursorServer();
server.run().catch((error) => {
  console.error('Failed to start GraphMemory MCP server:', error);
  process.exit(1);
}); 