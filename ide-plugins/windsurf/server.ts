#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { GraphMemoryMCPClient } from '../shared/mcp-client.js';
import { MCPClientConfig, GRAPHMEMORY_TOOLS } from '../shared/types.js';
import { ConfigLoader, ValidationHelper, ErrorHelper } from '../shared/utils.js';

/**
 * GraphMemory MCP Server for Windsurf IDE
 * 
 * This server acts as a bridge between Windsurf IDE's Cascade and GraphMemory-IDE,
 * exposing GraphMemory tools through the Model Context Protocol.
 * 
 * Optimized for Windsurf's agentic capabilities and Cascade integration.
 */
class GraphMemoryWindsurfServer {
  private server: Server;
  private client: GraphMemoryMCPClient | null = null;
  private config: MCPClientConfig;

  constructor() {
    this.server = new Server(
      {
        name: 'graphmemory-windsurf',
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
        batchRequests: true,
        // Windsurf-specific optimizations
        cascadeIntegration: true,
        agenticWorkflows: true,
        turboModeSupport: true
      },
      performance: {
        cacheEnabled: true,
        cacheSize: 100,
        maxConcurrentRequests: 5,
        requestTimeout: 30000,
        // Enhanced for Windsurf's agentic capabilities
        batchProcessing: true,
        streamingResponses: true
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
        if (event.data.responseTime > 2000) {
          console.warn(`Slow response detected: ${event.data.responseTime}ms for ${event.data.operation}`);
        }
      });

      await this.client.connect();
      console.log('GraphMemory client connected successfully');

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
        case 'graph_query':
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
      console.error('Error formatting tool result:', error);
      return JSON.stringify(result, null, 2);
    }
  }

  private formatSearchResult(result: any): string {
    if (!result.memories || result.memories.length === 0) {
      return 'No memories found matching your search criteria.';
    }

    const memories = result.memories.slice(0, 10); // Limit for Cascade readability
    let output = `Found ${result.total || memories.length} memories:\n\n`;
    
    memories.forEach((memory: any, index: number) => {
      output += `${index + 1}. **${memory.title || 'Untitled'}**\n`;
      output += `   Content: ${memory.content.substring(0, 150)}${memory.content.length > 150 ? '...' : ''}\n`;
      output += `   Tags: ${memory.tags?.join(', ') || 'None'}\n`;
      output += `   Created: ${memory.created_at}\n\n`;
    });

    return output;
  }

  private formatMemoryResult(memory: any): string {
    return `Memory ${memory.id ? 'updated' : 'created'} successfully:
**Title:** ${memory.title || 'Untitled'}
**Content:** ${memory.content.substring(0, 200)}${memory.content.length > 200 ? '...' : ''}
**Tags:** ${memory.tags?.join(', ') || 'None'}
**Type:** ${memory.type || 'general'}`;
  }

  private formatAnalysisResult(result: any): string {
    let output = '## Graph Analysis Results\n\n';
    
    if (result.nodes) {
      output += `**Nodes:** ${result.nodes.length}\n`;
    }
    
    if (result.relationships) {
      output += `**Relationships:** ${result.relationships.length}\n`;
    }
    
    if (result.clusters) {
      output += `**Clusters:** ${result.clusters.length}\n`;
    }
    
    if (result.insights) {
      output += '\n**Key Insights:**\n';
      result.insights.slice(0, 5).forEach((insight: string, index: number) => {
        output += `${index + 1}. ${insight}\n`;
      });
    }
    
    if (result.query_result) {
      output += '\n**Query Results:**\n';
      output += JSON.stringify(result.query_result, null, 2);
    }
    
    return output;
  }

  private formatClusterResult(result: any): string {
    if (!result.clusters || result.clusters.length === 0) {
      return 'No knowledge clusters found.';
    }

    let output = `## Knowledge Clusters (${result.clusters.length} found)\n\n`;
    
    result.clusters.slice(0, 5).forEach((cluster: any, index: number) => {
      output += `### Cluster ${index + 1}: ${cluster.name || `Cluster ${cluster.id}`}\n`;
      output += `**Size:** ${cluster.size || cluster.memories?.length || 'Unknown'} memories\n`;
      output += `**Theme:** ${cluster.theme || 'Not specified'}\n`;
      
      if (cluster.keywords) {
        output += `**Keywords:** ${cluster.keywords.join(', ')}\n`;
      }
      
      if (cluster.memories) {
        output += `**Sample Memories:** ${cluster.memories.slice(0, 3).map((m: any) => m.title || m.content.substring(0, 50)).join(', ')}\n`;
      }
      
      output += '\n';
    });
    
    return output;
  }

  private formatInsightsResult(result: any): string {
    if (!result.insights || result.insights.length === 0) {
      return 'No insights generated from your knowledge graph.';
    }

    let output = '## Knowledge Insights\n\n';
    
    if (result.summary) {
      output += `**Summary:** ${result.summary}\n\n`;
    }
    
    output += '**Key Insights:**\n';
    result.insights.slice(0, 8).forEach((insight: any, index: number) => {
      if (typeof insight === 'string') {
        output += `${index + 1}. ${insight}\n`;
      } else {
        output += `${index + 1}. **${insight.title || 'Insight'}:** ${insight.description || insight.content}\n`;
        if (insight.confidence) {
          output += `   *Confidence: ${insight.confidence}*\n`;
        }
      }
    });
    
    if (result.patterns) {
      output += '\n**Patterns Detected:**\n';
      result.patterns.slice(0, 3).forEach((pattern: string, index: number) => {
        output += `• ${pattern}\n`;
      });
    }
    
    return output;
  }

  private formatRecommendationsResult(result: any): string {
    if (!result.recommendations || result.recommendations.length === 0) {
      return 'No recommendations available at this time.';
    }

    let output = '## Recommendations\n\n';
    
    result.recommendations.slice(0, 6).forEach((rec: any, index: number) => {
      output += `### ${index + 1}. ${rec.title || rec.type || 'Recommendation'}\n`;
      output += `${rec.description || rec.content}\n`;
      
      if (rec.confidence) {
        output += `*Confidence: ${rec.confidence}*\n`;
      }
      
      if (rec.related_memories) {
        output += `*Related to: ${rec.related_memories.slice(0, 2).map((m: any) => m.title || m.content.substring(0, 30)).join(', ')}*\n`;
      }
      
      output += '\n';
    });
    
    return output;
  }

  private createLogger() {
    return {
      info: (message: string, data?: any) => {
        console.log(`[INFO] ${message}`, data ? JSON.stringify(data) : '');
      },
      warn: (message: string, data?: any) => {
        console.warn(`[WARN] ${message}`, data ? JSON.stringify(data) : '');
      },
      error: (message: string, data?: any) => {
        console.error(`[ERROR] ${message}`, data ? JSON.stringify(data) : '');
      },
      debug: (message: string, data?: any) => {
        if (process.env.GRAPHMEMORY_DEBUG === 'true') {
          console.debug(`[DEBUG] ${message}`, data ? JSON.stringify(data) : '');
        }
      }
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log('GraphMemory Windsurf MCP Server running on stdio');
  }
}

// Start the server
const server = new GraphMemoryWindsurfServer();
server.run().catch((error) => {
  console.error('Failed to start GraphMemory Windsurf MCP Server:', error);
  process.exit(1);
}); 