import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { EventEmitter as NodeEventEmitter } from 'events';
import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import {
  MCPClientConfig,
  MCPResponse,
  Memory,
  SearchResult,
  GraphAnalysisResult,
  ClusterResult,
  InsightResult,
  RecommendationResult,
  EventEmitter,
  Cache,
  Logger,
  GRAPHMEMORY_TOOLS,
  ToolName,
  MemorySearchParams,
  MemoryCreateParams,
  MemoryUpdateParams,
  MemoryDeleteParams,
  MemoryRelateParams,
  GraphQueryParams,
  GraphAnalyzeParams,
  KnowledgeClusterParams,
  KnowledgeInsightsParams,
  KnowledgeRecommendParams,
  ConnectionEvent,
  ErrorEvent,
  PerformanceEvent
} from './types';
import { SimpleCache } from './utils';

/**
 * GraphMemory MCP Client
 * 
 * Provides a Model Context Protocol (MCP) client for interacting with
 * GraphMemory-IDE server. Supports all GraphMemory tools and features
 * including semantic search, graph operations, and knowledge discovery.
 */
export class GraphMemoryMCPClient implements EventEmitter {
  private config: MCPClientConfig;
  private httpClient: AxiosInstance;
  private eventEmitter: NodeEventEmitter;
  private cache: Cache;
  private logger: Logger;
  private isConnected: boolean = false;
  private requestQueue: Map<string, Promise<any>> = new Map();

  constructor(config: MCPClientConfig, logger?: Logger) {
    this.config = {
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      ...config
    };
    
    this.eventEmitter = new NodeEventEmitter();
    this.cache = new SimpleCache(config.performance?.cacheSize || 100);
    this.logger = logger || this.createDefaultLogger();
    
    this.httpClient = this.createHttpClient();
    this.setupEventHandlers();
  }

  // ============================================================================
  // Connection Management
  // ============================================================================

  async connect(): Promise<void> {
    try {
      this.logger.info('Connecting to GraphMemory server...', { url: this.config.serverUrl });
      
      // Test connection with health check
      const response = await this.httpClient.get('/health');
      
      if (response.status === 200) {
        this.isConnected = true;
        this.logger.info('Successfully connected to GraphMemory server');
        
        this.emit({
          type: 'connection',
          timestamp: new Date().toISOString(),
          data: {
            serverUrl: this.config.serverUrl,
            status: 'connected'
          }
        } as ConnectionEvent);
      } else {
        throw new Error(`Health check failed with status: ${response.status}`);
      }
    } catch (error) {
      this.isConnected = false;
      const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
      this.logger.error('Failed to connect to GraphMemory server', { error: errorMessage });
      
      this.emit({
        type: 'error',
        timestamp: new Date().toISOString(),
        data: {
          error: errorMessage,
          context: 'connection',
          recoverable: true
        }
      } as ErrorEvent);
      
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    this.isConnected = false;
    this.cache.clear();
    this.requestQueue.clear();
    
    this.emit({
      type: 'disconnection',
      timestamp: new Date().toISOString(),
      data: {
        serverUrl: this.config.serverUrl,
        status: 'disconnected'
      }
    } as ConnectionEvent);
    
    this.logger.info('Disconnected from GraphMemory server');
  }

  // ============================================================================
  // Tool Implementations
  // ============================================================================

  /**
   * Search memories using semantic similarity
   */
  async searchMemories(params: MemorySearchParams): Promise<SearchResult> {
    return this.callTool('memory_search', params);
  }

  /**
   * Create a new memory entry
   */
  async createMemory(params: MemoryCreateParams): Promise<Memory> {
    const result = await this.callTool('memory_create', params);
    this.invalidateCache('memory_search');
    return result as Memory;
  }

  /**
   * Update an existing memory
   */
  async updateMemory(params: MemoryUpdateParams): Promise<Memory> {
    const result = await this.callTool('memory_update', params);
    this.invalidateCache('memory_search');
    this.cache.delete(`memory_${params.id}`);
    return result as Memory;
  }

  /**
   * Delete a memory entry
   */
  async deleteMemory(params: MemoryDeleteParams): Promise<void> {
    await this.callTool('memory_delete', params);
    this.invalidateCache('memory_search');
    this.cache.delete(`memory_${params.id}`);
  }

  /**
   * Create a relationship between memories
   */
  async relateMemories(params: MemoryRelateParams): Promise<void> {
    await this.callTool('memory_relate', params);
    this.invalidateCache('graph_');
  }

  /**
   * Execute a Cypher query on the memory graph
   */
  async queryGraph(params: GraphQueryParams): Promise<any> {
    return this.callTool('graph_query', params);
  }

  /**
   * Analyze graph structure and patterns
   */
  async analyzeGraph(params: GraphAnalyzeParams): Promise<GraphAnalysisResult> {
    return this.callTool('graph_analyze', params);
  }

  /**
   * Find knowledge clusters in the memory graph
   */
  async clusterKnowledge(params: KnowledgeClusterParams): Promise<ClusterResult> {
    return this.callTool('knowledge_cluster', params);
  }

  /**
   * Generate insights from memory patterns
   */
  async generateInsights(params: KnowledgeInsightsParams): Promise<InsightResult> {
    return this.callTool('knowledge_insights', params);
  }

  /**
   * Get knowledge recommendations based on context
   */
  async getRecommendations(params: KnowledgeRecommendParams): Promise<RecommendationResult> {
    return this.callTool('knowledge_recommend', params);
  }

  // ============================================================================
  // Batch Operations
  // ============================================================================

  /**
   * Execute multiple operations in a batch
   */
  async batch<T>(operations: Array<() => Promise<T>>): Promise<T[]> {
    if (!this.config.features?.batchRequests) {
      // Execute sequentially if batching is disabled
      const results: T[] = [];
      for (const operation of operations) {
        results.push(await operation());
      }
      return results;
    }

    const maxConcurrent = this.config.performance?.maxConcurrentRequests || 5;
    const results: T[] = [];
    
    for (let i = 0; i < operations.length; i += maxConcurrent) {
      const batch = operations.slice(i, i + maxConcurrent);
      const batchResults = await Promise.all(batch.map(op => op()));
      results.push(...batchResults);
    }
    
    return results;
  }

  // ============================================================================
  // Event Emitter Implementation
  // ============================================================================

  on<T extends any>(eventType: string, handler: (event: T) => void): void {
    this.eventEmitter.on(eventType, handler);
  }

  off<T extends any>(eventType: string, handler: (event: T) => void): void {
    this.eventEmitter.off(eventType, handler);
  }

  emit<T extends any>(event: T): void {
    this.eventEmitter.emit((event as any).type, event);
  }

  // ============================================================================
  // Private Methods
  // ============================================================================

  private createHttpClient(): AxiosInstance {
    const client = axios.create({
      baseURL: this.config.serverUrl,
      timeout: this.config.timeout,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'GraphMemory-MCP-Client/1.0.0'
      }
    });

    // Add authentication interceptor
    client.interceptors.request.use((config) => {
      const auth = this.getAuthHeaders();
      if (auth && config.headers) {
        Object.assign(config.headers, auth);
      }
      return config;
    });

    // Add response interceptor for error handling
    client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401 && this.config.auth.method === 'jwt') {
          // Token might be expired, try to refresh if possible
          this.logger.warn('Authentication failed, token may be expired');
        }
        return Promise.reject(error);
      }
    );

    return client;
  }

  private getAuthHeaders(): Record<string, string> | null {
    switch (this.config.auth.method) {
      case 'jwt':
        if (this.config.auth.token) {
          return { Authorization: `Bearer ${this.config.auth.token}` };
        }
        break;
      case 'apikey':
        if (this.config.auth.apiKey) {
          return { 'X-API-Key': this.config.auth.apiKey };
        }
        break;
      case 'mtls':
        // mTLS is handled at the HTTP client level
        return null;
    }
    return null;
  }

  private async callTool<T>(toolName: ToolName, params: any): Promise<T> {
    const startTime = Date.now();
    const requestId = uuidv4();
    
    try {
      // Check cache first
      if (this.config.performance?.cacheEnabled) {
        const cacheKey = this.getCacheKey(toolName, params);
        const cached = this.cache.get<T>(cacheKey);
        if (cached) {
          this.emitPerformanceEvent(toolName, Date.now() - startTime, true, true);
          return cached;
        }
      }

      // Check if we're already making this request
      const requestKey = `${toolName}_${JSON.stringify(params)}`;
      if (this.requestQueue.has(requestKey)) {
        return this.requestQueue.get(requestKey);
      }

      // Make the request
      const requestPromise = this.executeToolRequest<T>(toolName, params, requestId);
      this.requestQueue.set(requestKey, requestPromise);

      try {
        const result = await requestPromise;
        
        // Cache the result
        if (this.config.performance?.cacheEnabled && this.isCacheable(toolName)) {
          const cacheKey = this.getCacheKey(toolName, params);
          this.cache.set(cacheKey, result, this.getCacheTTL(toolName));
        }

        this.emitPerformanceEvent(toolName, Date.now() - startTime, true, false);
        return result;
      } finally {
        this.requestQueue.delete(requestKey);
      }
    } catch (error) {
      this.emitPerformanceEvent(toolName, Date.now() - startTime, false, false);
      throw error;
    }
  }

  private async executeToolRequest<T>(toolName: ToolName, params: any, requestId: string): Promise<T> {
    const tool = GRAPHMEMORY_TOOLS[toolName];
    
    // Validate parameters
    const validationResult = tool.inputSchema.safeParse(params);
    if (!validationResult.success) {
      throw new Error(`Invalid parameters for ${toolName}: ${validationResult.error.message}`);
    }

    const payload = {
      jsonrpc: '2.0',
      id: requestId,
      method: 'tools/call',
      params: {
        name: toolName,
        arguments: validationResult.data
      }
    };

    this.logger.debug(`Calling tool: ${toolName}`, { params: validationResult.data, requestId });

    const response = await this.httpClient.post('/mcp/tools', payload);
    
    if (response.data.error) {
      throw new Error(`Tool call failed: ${response.data.error.message}`);
    }

    return response.data.result;
  }

  private getCacheKey(toolName: string, params: any): string {
    return `${toolName}_${JSON.stringify(params)}`;
  }

  private isCacheable(toolName: string): boolean {
    // Read operations are cacheable, write operations are not
    const readOnlyTools = ['memory_search', 'graph_query', 'graph_analyze', 'knowledge_cluster', 'knowledge_insights', 'knowledge_recommend'];
    return readOnlyTools.includes(toolName);
  }

  private getCacheTTL(toolName: string): number {
    // Different cache TTLs for different operations
    const ttlMap: Record<string, number> = {
      memory_search: 300, // 5 minutes
      graph_analyze: 600, // 10 minutes
      knowledge_cluster: 1800, // 30 minutes
      knowledge_insights: 3600, // 1 hour
      knowledge_recommend: 300 // 5 minutes
    };
    return ttlMap[toolName] || 300;
  }

  private invalidateCache(prefix: string): void {
    // Simple cache invalidation by prefix
    // In a real implementation, you might want a more sophisticated approach
    this.cache.clear();
  }

  private emitPerformanceEvent(operation: string, duration: number, success: boolean, cacheHit: boolean): void {
    this.emit({
      type: 'performance',
      timestamp: new Date().toISOString(),
      data: {
        operation,
        duration,
        success,
        cacheHit
      }
    } as PerformanceEvent);
  }

  private setupEventHandlers(): void {
    // Set up automatic reconnection on connection loss
    this.on('error', (event: ErrorEvent) => {
      if (event.data.recoverable && !this.isConnected) {
        this.logger.info('Attempting to reconnect...');
        setTimeout(() => {
          this.connect().catch(err => {
            this.logger.error('Reconnection failed', { error: err.message });
          });
        }, this.config.retryDelay);
      }
    });
  }

  private createDefaultLogger(): Logger {
    return {
      debug: (message: string, ...args: any[]) => console.debug(`[GraphMemory MCP] ${message}`, ...args),
      info: (message: string, ...args: any[]) => console.info(`[GraphMemory MCP] ${message}`, ...args),
      warn: (message: string, ...args: any[]) => console.warn(`[GraphMemory MCP] ${message}`, ...args),
      error: (message: string, ...args: any[]) => console.error(`[GraphMemory MCP] ${message}`, ...args)
    };
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Get the list of available tools
   */
  getAvailableTools(): string[] {
    return Object.keys(GRAPHMEMORY_TOOLS);
  }

  /**
   * Get tool information
   */
  getToolInfo(toolName: ToolName) {
    return GRAPHMEMORY_TOOLS[toolName];
  }

  /**
   * Check if the client is connected
   */
  isClientConnected(): boolean {
    return this.isConnected;
  }

  /**
   * Get client configuration
   */
  getConfig(): MCPClientConfig {
    return { ...this.config };
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; hitRate?: number } {
    return {
      size: this.cache.size()
    };
  }
} 