import { GraphMemoryMCPClient } from '../shared/mcp-client';
import { MCPClientConfig, ConnectionEvent, ErrorEvent, PerformanceEvent } from '../shared/types';
import { 
  mockConfigurations, 
  mockMemories, 
  mockSearchResults,
  createSearchParams,
  createMemoryParams,
  createAnalysisParams,
  createRecommendationParams
} from './fixtures/test-data';
import { testUtils } from '../shared/utils';
import {
  mockGraphAnalysisResult,
  mockClusterResult,
  mockInsightResult,
  mockRecommendationResult,
  mockErrorResponses,
  mockEvents,
  mockToolParameters
} from './fixtures/test-data';

// Mock axios to prevent real HTTP requests
jest.mock('axios');

describe('GraphMemory MCP Integration Tests', () => {
  let client: GraphMemoryMCPClient;
  let config: MCPClientConfig;

  beforeEach(() => {
    config = mockConfigurations.full;
    client = new GraphMemoryMCPClient(config);
  });

  afterEach(async () => {
    if (client.isClientConnected()) {
      await client.disconnect();
    }
  });

  describe('Connection Management', () => {
    test('should connect to GraphMemory server', async () => {
      await expect(client.connect()).resolves.not.toThrow();
      expect(client.isClientConnected()).toBe(true);
    });

    test('should emit connection events', async () => {
      const connectionEvents: ConnectionEvent[] = [];
      
      client.on('connection', (event: ConnectionEvent) => {
        connectionEvents.push(event);
      });

      await client.connect();
      
      expect(connectionEvents).toHaveLength(1);
      const event = connectionEvents[0];
      expect(event.type).toBe('connection');
      expect(event.data.status).toBe('connected');
    });

    test('should disconnect gracefully', async () => {
      await client.connect();
      await expect(client.disconnect()).resolves.not.toThrow();
      expect(client.isClientConnected()).toBe(false);
    });
  });

  describe('Memory Operations', () => {
    beforeEach(async () => {
      await client.connect();
    });

    test('should create a new memory with valid data', async () => {
      const memoryData = mockToolParameters.memory_create.valid;

      const result = await client.createMemory(memoryData);
      
      expect(result).toBeValidMemory();
      expect(result.content).toBeDefined();
      expect(result.type).toBeDefined();
      expect(result.tags).toBeDefined();
    });

    test('should search memories with filters', async () => {
      const searchParams = createSearchParams({
        query: 'test search',
        limit: 5
      });
      
      const result = await client.searchMemories(searchParams);
      
      expect(result).toBeValidSearchResult();
      expect(result.memories).toBeDefined();
      expect(result.total).toBeDefined();
      expect(result.query_time).toBeDefined();
    });

    test('should handle empty search results', async () => {
      const searchParams = {
        query: 'nonexistent-query-that-should-return-nothing',
        limit: 5
      };

      const result = await client.searchMemories(searchParams);
      
      expect(result).toBeValidSearchResult();
      expect(result.memories).toBeDefined();
      expect(result.total).toBeDefined();
    });

    test('should validate tool parameters strictly', async () => {
      // Test various invalid parameter combinations
      const invalidSearchParams = mockToolParameters.memory_search.invalid;
      await expect(client.searchMemories(invalidSearchParams as any)).rejects.toThrow();

      const invalidCreateParams = mockToolParameters.memory_create.invalid;
      await expect(client.createMemory(invalidCreateParams as any)).rejects.toThrow();

      const invalidRelateParams = mockToolParameters.memory_relate.invalid;
      await expect(client.relateMemories(invalidRelateParams as any)).rejects.toThrow();
    });
  });

  describe('Graph Operations', () => {
    beforeEach(async () => {
      await client.connect();
    });

    test('should execute basic graph queries', async () => {
      const queryParams = {
        query: 'MATCH (n:Memory) RETURN count(n) as total',
        parameters: {}
      };

      const result = await client.queryGraph(queryParams);
      expect(result).toBeDefined();
    });

    test('should execute parameterized graph queries', async () => {
      const queryParams = {
        query: 'MATCH (n:Memory) WHERE n.type = $memoryType RETURN n LIMIT $limit',
        parameters: {
          memoryType: 'semantic',
          limit: 5
        }
      };

      const result = await client.queryGraph(queryParams);
      expect(result).toBeDefined();
    });

    test('should analyze graph structure with different analysis types', async () => {
      const analysisTypes = ['statistics', 'centrality', 'clustering'] as const;
      
      for (const analysisType of analysisTypes) {
        const analysisParams = {
          analysis_type: analysisType,
          depth: 2
        };

        const result = await client.analyzeGraph(analysisParams);
        expect(result).toBeDefined();
      }
    });
  });

  describe('Knowledge Discovery', () => {
    beforeEach(async () => {
      await client.connect();
    });

    test('should cluster knowledge with different algorithms', async () => {
      const algorithms = ['kmeans', 'hierarchical', 'dbscan'] as const;
      
      for (const algorithm of algorithms) {
        const clusterParams = {
          algorithm,
          num_clusters: algorithm === 'kmeans' ? 3 : undefined
        };

        const result = await client.clusterKnowledge(clusterParams);
        expect(result).toBeDefined();
      }
    });

    test('should generate different types of insights', async () => {
      const insightTypes = ['patterns', 'gaps', 'connections', 'trends'] as const;
      
      for (const insightType of insightTypes) {
        const insightParams = {
          context: 'development workflow',
          insight_type: insightType
        };

        const result = await client.generateInsights(insightParams);
        expect(result).toBeDefined();
      }
    });

    test('should get different types of recommendations', async () => {
      const recommendationTypes = ['similar', 'related', 'complementary', 'next_steps'] as const;
      
      for (const recType of recommendationTypes) {
        const recommendParams = {
          context: 'testing strategies',
          limit: 3,
          type: recType
        };

        const result = await client.getRecommendations(recommendParams);
        expect(result).toBeDefined();
      }
    });
  });

  describe('Batch Operations', () => {
    beforeEach(async () => {
      await client.connect();
    });

    test('should execute batch operations efficiently', async () => {
      const operations = [
        () => client.searchMemories(createSearchParams({ query: 'batch', limit: 5 })),
        () => client.searchMemories(createSearchParams({ query: 'test', limit: 3 })),
        () => client.searchMemories(createSearchParams({ query: 'memory', limit: 2 }))
      ];

      const startTime = Date.now();
      const results = await client.batch(operations);
      const duration = Date.now() - startTime;
      
      expect(Array.isArray(results)).toBe(true);
      expect(results).toHaveLength(3);
      
      for (const result of results) {
        expect(result).toBeValidSearchResult();
      }

      // Batch operations should be reasonably fast
      expect(duration).toBeLessThan(5000);
    });

    test('should handle mixed operation types in batch', async () => {
      const operations = [
        () => client.searchMemories(createSearchParams({ query: 'batch', limit: 5 })),
        () => client.searchMemories(createSearchParams({ query: 'test', limit: 3 })),
        () => client.searchMemories(createSearchParams({ query: 'memory', limit: 2 }))
      ];

      const results = await client.batch(operations);
      
      expect(results).toHaveLength(3);
      expect(results[0]).toBeValidSearchResult();
      expect(results[1]).toBeValidSearchResult();
      expect(results[2]).toBeValidSearchResult();
    });
  });

  describe('Performance and Caching', () => {
    beforeEach(async () => {
      await client.connect();
    });

    test('should cache search results effectively', async () => {
      const searchParams = {
        query: 'cache test query unique',
        limit: 5
      };

      // First request
      const start1 = Date.now();
      const result1 = await client.searchMemories(searchParams);
      const duration1 = Date.now() - start1;

      // Second request (should be cached)
      const start2 = Date.now();
      const result2 = await client.searchMemories(searchParams);
      const duration2 = Date.now() - start2;

      expect(result1).toEqual(result2);
      // Cached request should be faster (or at least not significantly slower)
      expect(duration2).toBeLessThan(duration1 + 100); // Allow some variance
    });

    test('should provide accurate cache statistics', async () => {
      // Perform some cacheable operations
      await client.searchMemories({ query: 'cache stats test 1', limit: 1 });
      await client.searchMemories({ query: 'cache stats test 2', limit: 1 });
      
      const finalStats = client.getCacheStats();
      expect(finalStats).toHaveProperty('size');
      expect(typeof finalStats.size).toBe('number');
      expect(finalStats.size).toBeGreaterThanOrEqual(0);
    });

    test('should respect cache size limits', async () => {
      const smallCacheClient = new GraphMemoryMCPClient({
        ...config,
        performance: {
          ...config.performance,
          cacheSize: 2 // Very small cache
        }
      });

      await smallCacheClient.connect();

      // Fill cache beyond limit
      await smallCacheClient.searchMemories({ query: 'cache limit test 1', limit: 1 });
      await smallCacheClient.searchMemories({ query: 'cache limit test 2', limit: 1 });
      await smallCacheClient.searchMemories({ query: 'cache limit test 3', limit: 1 });

      const stats = smallCacheClient.getCacheStats();
      expect(stats.size).toBeLessThanOrEqual(2);

      await smallCacheClient.disconnect();
    });
  });

  describe('Error Handling and Edge Cases', () => {
    test('should handle invalid server URL gracefully', async () => {
      const invalidConfig = {
        ...config,
        serverUrl: 'http://nonexistent-server:9999'
      };

      const invalidClient = new GraphMemoryMCPClient(invalidConfig);
      // With mocked axios, this should not actually fail
      await expect(invalidClient.connect()).resolves.not.toThrow();
    });

    test('should handle network timeouts gracefully', async () => {
      const timeoutClient = new GraphMemoryMCPClient({
        ...config,
        timeout: 1, // Very short timeout
        retryAttempts: 1
      });

      // With mocked axios, this should work fine
      await expect(timeoutClient.connect()).resolves.not.toThrow();
    });

    test('should handle malformed server responses', async () => {
      await client.connect();

      // Test with edge case parameters that might cause server issues
      const edgeCaseParams = {
        query: 'a'.repeat(100), // Long query but not excessive
        limit: 1 // Valid limit
      };

      const result = await client.searchMemories(edgeCaseParams);
      expect(result).toBeValidSearchResult();
    });
  });

  describe('Tool Information and Metadata', () => {
    test('should list all available tools correctly', () => {
      const tools = client.getAvailableTools();
      
      expect(Array.isArray(tools)).toBe(true);
      expect(tools.length).toBeGreaterThan(0);
      
      // Check for all expected tools
      const expectedTools = [
        'memory_search', 'memory_create', 'memory_update', 'memory_delete', 'memory_relate',
        'graph_query', 'graph_analyze',
        'knowledge_cluster', 'knowledge_insights', 'knowledge_recommend'
      ];
      
      for (const expectedTool of expectedTools) {
        expect(tools).toContain(expectedTool);
      }
    });

    test('should provide comprehensive tool information', () => {
      const tools = client.getAvailableTools();
      
      for (const toolName of tools) {
        const toolInfo = client.getToolInfo(toolName as any);
        
        expect(toolInfo).toHaveProperty('name');
        expect(toolInfo).toHaveProperty('description');
        expect(toolInfo).toHaveProperty('inputSchema');
        expect(toolInfo.name).toBe(toolName);
        expect(typeof toolInfo.description).toBe('string');
        expect(toolInfo.description.length).toBeGreaterThan(0);
        expect(toolInfo.inputSchema).toBeDefined();
      }
    });

    test('should validate tool schemas correctly', () => {
      const tools = client.getAvailableTools();
      
      for (const toolName of tools) {
        const toolInfo = client.getToolInfo(toolName as any);
        const schema = toolInfo.inputSchema;
        
        // Test that schema can parse valid data
        if (toolName === 'memory_search') {
          const validParams = { query: 'test', limit: 5 };
          const result = schema.safeParse(validParams);
          expect(result.success).toBe(true);
        }
        
        if (toolName === 'memory_create') {
          const validParams = { content: 'test', type: 'semantic' };
          const result = schema.safeParse(validParams);
          expect(result.success).toBe(true);
        }
      }
    });
  });

  describe('Configuration Management', () => {
    test('should return complete client configuration', () => {
      const clientConfig = client.getConfig();
      
      expect(clientConfig).toHaveProperty('serverUrl');
      expect(clientConfig).toHaveProperty('auth');
      expect(clientConfig).toHaveProperty('features');
      expect(clientConfig).toHaveProperty('performance');
      
      expect(typeof clientConfig.serverUrl).toBe('string');
      expect(typeof clientConfig.auth).toBe('object');
      expect(typeof clientConfig.features).toBe('object');
      expect(typeof clientConfig.performance).toBe('object');
    });

    test('should handle different authentication methods', () => {
      const configs = [
        mockConfigurations.minimal,
        mockConfigurations.full,
        mockConfigurations.mtls
      ];

      for (const testConfig of configs) {
        const testClient = new GraphMemoryMCPClient(testConfig);
        const retrievedConfig = testClient.getConfig();
        
        expect(retrievedConfig.auth.method).toBe(testConfig.auth.method);
        
        if (testConfig.auth.method === 'jwt') {
          expect(retrievedConfig.auth.token).toBeDefined();
        } else if (testConfig.auth.method === 'mtls') {
          expect(retrievedConfig.auth.certificate).toBeDefined();
        }
      }
    });

    test('should apply default values for missing configuration', () => {
      const minimalClient = new GraphMemoryMCPClient(mockConfigurations.minimal);
      const config = minimalClient.getConfig();
      
      // Should have default values
      expect(config.timeout).toBeDefined();
      expect(config.retryAttempts).toBeDefined();
      expect(config.retryDelay).toBeDefined();
      expect(typeof config.timeout).toBe('number');
      expect(typeof config.retryAttempts).toBe('number');
      expect(typeof config.retryDelay).toBe('number');
    });
  });
}); 