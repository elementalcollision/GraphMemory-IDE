import { z } from 'zod';

// ============================================================================
// Core MCP Types
// ============================================================================

export interface MCPClientConfig {
  serverUrl: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
  auth: AuthConfig;
  features?: FeatureConfig;
  performance?: PerformanceConfig;
}

export interface AuthConfig {
  method: 'jwt' | 'apikey' | 'mtls';
  token?: string;
  apiKey?: string;
  certificate?: {
    cert: string;
    key: string;
    ca?: string;
  };
}

export interface FeatureConfig {
  autoComplete?: boolean;
  semanticSearch?: boolean;
  graphVisualization?: boolean;
  batchRequests?: boolean;
}

export interface PerformanceConfig {
  cacheEnabled?: boolean;
  cacheSize?: number;
  maxConcurrentRequests?: number;
  requestTimeout?: number;
}

// ============================================================================
// GraphMemory API Types
// ============================================================================

export interface Memory {
  id: string;
  content: string;
  type: MemoryType;
  tags: string[];
  metadata: Record<string, any>;
  embedding?: number[];
  created_at: string;
  updated_at: string;
  relationships?: Relationship[];
}

export type MemoryType = 'procedural' | 'semantic' | 'episodic' | 'declarative';

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  type: RelationshipType;
  weight?: number;
  metadata?: Record<string, any>;
  created_at: string;
}

export type RelationshipType = 
  | 'related_to'
  | 'depends_on'
  | 'part_of'
  | 'similar_to'
  | 'contradicts'
  | 'supports'
  | 'follows'
  | 'precedes';

// ============================================================================
// MCP Tool Schemas
// ============================================================================

// Memory Search Tool
export const MemorySearchSchema = z.object({
  query: z.string().min(1).describe('Search query for semantic search'),
  limit: z.number().int().min(1).max(1000).optional().describe('Maximum number of results'),
  type: z.enum(['procedural', 'semantic', 'episodic', 'declarative']).optional().describe('Filter by memory type'),
  tags: z.array(z.string()).optional().describe('Filter by tags'),
  threshold: z.number().min(0).max(1).optional().describe('Similarity threshold (0-1)')
}).transform((data) => ({
  ...data,
  limit: data.limit ?? 10,
  threshold: data.threshold ?? 0.7
}));

export type MemorySearchParams = z.input<typeof MemorySearchSchema>;

// Memory Create Tool
export const MemoryCreateSchema = z.object({
  content: z.string().min(1).describe('Memory content'),
  type: z.enum(['procedural', 'semantic', 'episodic', 'declarative']).describe('Memory type'),
  tags: z.array(z.string()).optional().describe('Memory tags'),
  metadata: z.record(z.any()).optional().describe('Additional metadata')
}).transform((data) => ({
  ...data,
  tags: data.tags ?? [],
  metadata: data.metadata ?? {}
}));

export type MemoryCreateParams = z.input<typeof MemoryCreateSchema>;

// Memory Update Tool
export const MemoryUpdateSchema = z.object({
  id: z.string().min(1).describe('Memory ID to update'),
  content: z.string().min(1).optional().describe('Updated content'),
  tags: z.array(z.string()).optional().describe('Updated tags'),
  metadata: z.record(z.any()).optional().describe('Updated metadata')
});

export type MemoryUpdateParams = z.input<typeof MemoryUpdateSchema>;

// Memory Delete Tool
export const MemoryDeleteSchema = z.object({
  id: z.string().min(1).describe('Memory ID to delete')
});

export type MemoryDeleteParams = z.input<typeof MemoryDeleteSchema>;

// Memory Relate Tool
export const MemoryRelateSchema = z.object({
  source_id: z.string().min(1).describe('Source memory ID'),
  target_id: z.string().min(1).describe('Target memory ID'),
  type: z.enum([
    'related_to', 'depends_on', 'part_of', 'similar_to',
    'contradicts', 'supports', 'follows', 'precedes'
  ]).describe('Relationship type'),
  weight: z.number().min(0).max(1).optional().describe('Relationship weight (0-1)'),
  metadata: z.record(z.any()).optional().describe('Relationship metadata')
}).transform((data) => ({
  ...data,
  weight: data.weight ?? 1.0,
  metadata: data.metadata ?? {}
}));

export type MemoryRelateParams = z.input<typeof MemoryRelateSchema>;

// Graph Query Tool
export const GraphQuerySchema = z.object({
  query: z.string().describe('Cypher query to execute'),
  parameters: z.record(z.any()).optional().describe('Query parameters')
}).transform((data) => ({
  ...data,
  parameters: data.parameters ?? {}
}));

export type GraphQueryParams = z.input<typeof GraphQuerySchema>;

// Graph Analyze Tool
export const GraphAnalyzeSchema = z.object({
  analysis_type: z.enum([
    'centrality', 'clustering', 'paths', 'communities', 'statistics'
  ]).describe('Type of graph analysis'),
  node_filter: z.string().optional().describe('Filter nodes by type or property'),
  depth: z.number().int().min(1).max(10).optional().describe('Analysis depth')
}).transform((data) => ({
  ...data,
  depth: data.depth ?? 3
}));

export type GraphAnalyzeParams = z.input<typeof GraphAnalyzeSchema>;

// Knowledge Cluster Tool
export const KnowledgeClusterSchema = z.object({
  topic: z.string().optional().describe('Topic to cluster around'),
  algorithm: z.enum(['kmeans', 'hierarchical', 'dbscan']).optional().describe('Clustering algorithm'),
  num_clusters: z.number().int().min(2).max(50).optional().describe('Number of clusters (for kmeans)')
}).transform((data) => ({
  ...data,
  algorithm: data.algorithm ?? 'kmeans',
  num_clusters: data.num_clusters ?? 5
}));

export type KnowledgeClusterParams = z.input<typeof KnowledgeClusterSchema>;

// Knowledge Insights Tool
export const KnowledgeInsightsSchema = z.object({
  context: z.string().optional().describe('Context for generating insights'),
  insight_type: z.enum(['patterns', 'gaps', 'connections', 'trends']).optional().describe('Type of insights to generate'),
  time_range: z.string().optional().describe('Time range for analysis (e.g., "7d", "30d", "1y")')
}).transform((data) => ({
  ...data,
  insight_type: data.insight_type ?? 'patterns'
}));

export type KnowledgeInsightsParams = z.input<typeof KnowledgeInsightsSchema>;

// Knowledge Recommend Tool
export const KnowledgeRecommendSchema = z.object({
  context: z.string().min(1).describe('Current context or topic'),
  limit: z.number().int().min(1).max(100).optional().describe('Number of recommendations'),
  type: z.enum(['similar', 'related', 'complementary', 'next_steps']).optional().describe('Recommendation type')
}).transform((data) => ({
  ...data,
  limit: data.limit ?? 5,
  type: data.type ?? 'related'
}));

export type KnowledgeRecommendParams = z.input<typeof KnowledgeRecommendSchema>;

// ============================================================================
// Response Types
// ============================================================================

export interface MCPResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  metadata?: {
    requestId: string;
    timestamp: string;
    duration: number;
  };
}

export interface SearchResult {
  memories: Memory[];
  total: number;
  query_time: number;
  suggestions?: string[];
}

export interface GraphAnalysisResult {
  analysis_type: string;
  results: Record<string, any>;
  visualization?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  insights: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
  size?: number;
  color?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight?: number;
  color?: string;
}

export interface ClusterResult {
  clusters: Array<{
    id: number;
    memories: Memory[];
    centroid: string;
    keywords: string[];
  }>;
  algorithm: string;
  parameters: Record<string, any>;
}

export interface InsightResult {
  insights: Array<{
    type: string;
    description: string;
    confidence: number;
    supporting_evidence: string[];
  }>;
  context: string;
  generated_at: string;
}

export interface RecommendationResult {
  recommendations: Array<{
    memory: Memory;
    score: number;
    reason: string;
  }>;
  context: string;
  recommendation_type: string;
}

// ============================================================================
// Event Types
// ============================================================================

export interface MCPEvent {
  type: string;
  timestamp: string;
  data: any;
}

export interface ConnectionEvent extends MCPEvent {
  type: 'connection' | 'disconnection' | 'reconnection';
  data: {
    serverUrl: string;
    status: 'connected' | 'disconnected' | 'reconnecting';
  };
}

export interface ErrorEvent extends MCPEvent {
  type: 'error';
  data: {
    error: string;
    context?: string;
    recoverable: boolean;
  };
}

export interface PerformanceEvent extends MCPEvent {
  type: 'performance';
  data: {
    operation: string;
    duration: number;
    success: boolean;
    cacheHit?: boolean;
  };
}

// ============================================================================
// Utility Types
// ============================================================================

export type EventHandler<T extends MCPEvent = MCPEvent> = (event: T) => void;

export interface EventEmitter {
  on<T extends MCPEvent>(eventType: string, handler: EventHandler<T>): void;
  off<T extends MCPEvent>(eventType: string, handler: EventHandler<T>): void;
  emit<T extends MCPEvent>(event: T): void;
}

export interface Cache {
  get<T>(key: string): T | undefined;
  set<T>(key: string, value: T, ttl?: number): void;
  delete(key: string): void;
  clear(): void;
  size(): number;
}

export interface Logger {
  debug(message: string, ...args: any[]): void;
  info(message: string, ...args: any[]): void;
  warn(message: string, ...args: any[]): void;
  error(message: string, ...args: any[]): void;
}

// ============================================================================
// Tool Definitions for MCP
// ============================================================================

export const GRAPHMEMORY_TOOLS = {
  memory_search: {
    name: 'memory_search',
    description: 'Search memories using semantic similarity',
    inputSchema: MemorySearchSchema
  },
  memory_create: {
    name: 'memory_create',
    description: 'Create a new memory entry',
    inputSchema: MemoryCreateSchema
  },
  memory_update: {
    name: 'memory_update',
    description: 'Update an existing memory',
    inputSchema: MemoryUpdateSchema
  },
  memory_delete: {
    name: 'memory_delete',
    description: 'Delete a memory entry',
    inputSchema: MemoryDeleteSchema
  },
  memory_relate: {
    name: 'memory_relate',
    description: 'Create a relationship between memories',
    inputSchema: MemoryRelateSchema
  },
  graph_query: {
    name: 'graph_query',
    description: 'Execute a Cypher query on the memory graph',
    inputSchema: GraphQuerySchema
  },
  graph_analyze: {
    name: 'graph_analyze',
    description: 'Analyze graph structure and patterns',
    inputSchema: GraphAnalyzeSchema
  },
  knowledge_cluster: {
    name: 'knowledge_cluster',
    description: 'Find knowledge clusters in the memory graph',
    inputSchema: KnowledgeClusterSchema
  },
  knowledge_insights: {
    name: 'knowledge_insights',
    description: 'Generate insights from memory patterns',
    inputSchema: KnowledgeInsightsSchema
  },
  knowledge_recommend: {
    name: 'knowledge_recommend',
    description: 'Get knowledge recommendations based on context',
    inputSchema: KnowledgeRecommendSchema
  }
} as const;

export type ToolName = keyof typeof GRAPHMEMORY_TOOLS; 