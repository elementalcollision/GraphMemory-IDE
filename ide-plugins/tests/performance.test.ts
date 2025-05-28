import { GraphMemoryMCPClient } from '../shared/mcp-client';
import { MCPClientConfig } from '../shared/types';
import { testUtils } from '../shared/utils';

// Mock axios to prevent real HTTP requests
jest.mock('axios');

describe('GraphMemory MCP Performance Tests', () => {
  let client: GraphMemoryMCPClient;
  let config: MCPClientConfig;

  beforeAll(() => {
    config = {
      serverUrl: process.env.TEST_SERVER_URL || 'http://localhost:8000',
      timeout: 30000,
      retryAttempts: 1,
      retryDelay: 100,
      auth: {
        method: 'jwt',
        token: process.env.TEST_JWT_TOKEN || 'test-token'
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
        maxConcurrentRequests: 10,
        requestTimeout: 30000
      }
    };

    client = new GraphMemoryMCPClient(config);
  });

  beforeEach(async () => {
    await client.connect();
  });

  afterAll(async () => {
    if (client.isClientConnected()) {
      await client.disconnect();
    }
  });

  describe('Search Performance', () => {
    test('should handle rapid sequential searches efficiently', async () => {
      const searchQueries = [
        'React development',
        'TypeScript performance',
        'testing optimization',
        'frontend backend'
      ];

      const searchResults = [];
      const startTime = Date.now();

      for (const query of searchQueries) {
        const result = await client.searchMemories({
          query,
          limit: 10,
          threshold: 0.5
        });
        searchResults.push(result);
      }

      const duration = Date.now() - startTime;
      const avgTimePerSearch = duration / searchQueries.length;

      expect(searchResults).toHaveLength(searchQueries.length);
      searchResults.forEach(result => {
        expect(result).toBeValidSearchResult();
      });

      expect(avgTimePerSearch).toBeLessThan(2000); // Less than 2 seconds per search
      console.log(`Executed ${searchQueries.length} searches in ${duration}ms (${avgTimePerSearch.toFixed(2)}ms avg per search)`);
    });

    test('should handle concurrent searches efficiently', async () => {
      const searchQueries = [
        'React hooks performance',
        'TypeScript optimization',
        'testing strategies',
        'frontend architecture'
      ];

      const startTime = Date.now();
      const searchPromises = searchQueries.map(query =>
        client.searchMemories({
          query,
          limit: 5,
          threshold: 0.6
        })
      );

      const searchResults = await Promise.all(searchPromises);
      const duration = Date.now() - startTime;
      const avgTimePerSearch = duration / searchQueries.length;

      expect(searchResults).toHaveLength(searchQueries.length);
      searchResults.forEach(result => {
        expect(result).toBeValidSearchResult();
      });

      // Concurrent searches should be reasonably fast
      expect(avgTimePerSearch).toBeLessThan(1500);
      console.log(`Executed ${searchQueries.length} concurrent searches in ${duration}ms (${avgTimePerSearch.toFixed(2)}ms avg per search)`);
    });

    test('should demonstrate cache performance benefits', async () => {
      const query = 'cache performance test unique query';
      const searchParams = { query, limit: 10, threshold: 0.7 };

      // First search (cache miss)
      const start1 = Date.now();
      const result1 = await client.searchMemories(searchParams);
      const duration1 = Date.now() - start1;

      // Second search (cache hit)
      const start2 = Date.now();
      const result2 = await client.searchMemories(searchParams);
      const duration2 = Date.now() - start2;

      // Third search (cache hit)
      const start3 = Date.now();
      const result3 = await client.searchMemories(searchParams);
      const duration3 = Date.now() - start3;

      expect(result1).toEqual(result2);
      expect(result2).toEqual(result3);

      // Cache hits should be faster or at least not significantly slower
      expect(duration2).toBeLessThan(duration1 + 50);
      expect(duration3).toBeLessThan(duration1 + 50);

      console.log(`Cache performance: First: ${duration1}ms, Second: ${duration2}ms, Third: ${duration3}ms`);
    });
  });

  describe('Graph Operations Performance', () => {
    test('should handle complex graph queries efficiently', async () => {
      const complexQueries = [
        {
          query: 'MATCH (n:Memory) RETURN count(n) as total_memories',
          parameters: {}
        },
        {
          query: 'MATCH (n:Memory)-[r:RELATED_TO]->(m:Memory) RETURN count(r) as total_relationships',
          parameters: {}
        },
        {
          query: 'MATCH (n:Memory) WHERE n.type = $type RETURN n LIMIT $limit',
          parameters: { type: 'semantic', limit: 10 }
        }
      ];

      const startTime = Date.now();
      const queryResults = [];

      for (const queryParams of complexQueries) {
        const result = await client.queryGraph(queryParams);
        queryResults.push(result);
      }

      const duration = Date.now() - startTime;
      const avgTimePerQuery = duration / complexQueries.length;

      expect(queryResults).toHaveLength(complexQueries.length);
      queryResults.forEach(result => {
        expect(result).toBeDefined();
      });

      expect(avgTimePerQuery).toBeLessThan(3000); // Less than 3 seconds per complex query
      console.log(`Executed ${complexQueries.length} complex graph queries in ${duration}ms (${avgTimePerQuery.toFixed(2)}ms avg per query)`);
    });

    test('should handle graph analysis operations efficiently', async () => {
      const analysisTypes = ['statistics', 'centrality', 'clustering'];
      const analysisResults = [];
      const startTime = Date.now();

      for (const analysisType of analysisTypes) {
        const result = await client.analyzeGraph({
          analysis_type: analysisType as any,
          depth: 2
        });
        analysisResults.push(result);
      }

      const duration = Date.now() - startTime;
      const avgTimePerAnalysis = duration / analysisTypes.length;

      expect(analysisResults).toHaveLength(analysisTypes.length);
      analysisResults.forEach(result => {
        expect(result).toBeDefined();
      });

      expect(avgTimePerAnalysis).toBeLessThan(5000); // Less than 5 seconds per analysis
      console.log(`Executed ${analysisTypes.length} graph analyses in ${duration}ms (${avgTimePerAnalysis.toFixed(2)}ms avg per analysis)`);
    });
  });

  describe('Batch Operations Performance', () => {
    test('should demonstrate batch operation efficiency', async () => {
      const operationCount = 10;
      
      // Sequential operations
      const sequentialStart = Date.now();
      const sequentialResults = [];
      for (let i = 0; i < operationCount; i++) {
        const result = await client.searchMemories({
          query: `sequential test ${i}`,
          limit: 3
        });
        sequentialResults.push(result);
      }
      const sequentialDuration = Date.now() - sequentialStart;

      // Batch operations
      const batchOperations = Array.from({ length: operationCount }, (_, i) =>
        () => client.searchMemories({
          query: `batch test ${i}`,
          limit: 3
        })
      );

      const batchStart = Date.now();
      const batchResults = await client.batch(batchOperations);
      const batchDuration = Date.now() - batchStart;

      expect(sequentialResults).toHaveLength(operationCount);
      expect(batchResults).toHaveLength(operationCount);

      // Both should complete successfully
      expect(sequentialDuration).toBeLessThan(10000);
      expect(batchDuration).toBeLessThan(10000);

      console.log(`Sequential: ${sequentialDuration}ms, Batch: ${batchDuration}ms`);
    });

    test('should handle large batch operations efficiently', async () => {
      const largeBatchSize = 20;
      const operations = Array.from({ length: largeBatchSize }, (_, i) =>
        () => client.searchMemories({
          query: `large batch test ${i % 5}`, // Reuse some queries for cache benefits
          limit: 2
        })
      );

      const startTime = Date.now();
      const results = await client.batch(operations);
      const duration = Date.now() - startTime;
      const avgTimePerOperation = duration / largeBatchSize;

      expect(results).toHaveLength(largeBatchSize);
      results.forEach(result => {
        expect(result).toBeValidSearchResult();
      });

      expect(avgTimePerOperation).toBeLessThan(1000); // Less than 1 second per operation in batch
      expect(duration).toBeLessThan(15000); // Total time less than 15 seconds

      console.log(`Large batch (${largeBatchSize} operations) completed in ${duration}ms (${avgTimePerOperation.toFixed(2)}ms avg per operation)`);
    });
  });

  describe('Memory and Resource Usage', () => {
    test('should handle cache eviction gracefully under memory pressure', async () => {
      // Create a client with a very small cache
      const smallCacheClient = new GraphMemoryMCPClient({
        ...config,
        performance: {
          ...config.performance,
          cacheSize: 3 // Very small cache
        }
      });

      await smallCacheClient.connect();

      // Fill cache beyond capacity
      const searches = [];
      for (let i = 0; i < 10; i++) {
        searches.push(
          smallCacheClient.searchMemories({
            query: `cache eviction test ${i}`,
            limit: 2
          })
        );
      }

      const results = await Promise.all(searches);
      const cacheStats = smallCacheClient.getCacheStats();

      expect(results).toHaveLength(10);
      expect(cacheStats.size).toBeLessThanOrEqual(3); // Should respect cache size limit

      console.log(`Cache size after 10 operations with limit 3: ${cacheStats.size}`);

      await smallCacheClient.disconnect();
    });
  });

  describe('Connection and Network Performance', () => {
    test('should handle connection lifecycle efficiently', async () => {
      const testClient = new GraphMemoryMCPClient(config);
      
      // Test multiple connect/disconnect cycles
      const cycles = 3;
      const cycleTimes = [];

      for (let i = 0; i < cycles; i++) {
        const startTime = Date.now();
        
        await testClient.connect();
        expect(testClient.isClientConnected()).toBe(true);
        
        await testClient.disconnect();
        expect(testClient.isClientConnected()).toBe(false);
        
        const cycleTime = Date.now() - startTime;
        cycleTimes.push(cycleTime);
      }

      const avgCycleTime = cycleTimes.reduce((a, b) => a + b, 0) / cycles;
      const maxCycleTime = Math.max(...cycleTimes);

      expect(avgCycleTime).toBeLessThan(2000); // Less than 2 seconds per cycle on average
      expect(maxCycleTime).toBeLessThan(5000); // No single cycle should take more than 5 seconds

      console.log(`Connection cycles: avg ${avgCycleTime.toFixed(2)}ms, max ${maxCycleTime}ms`);
    });

    test('should maintain performance under concurrent connections', async () => {
      const concurrentClients = 3;
      const clients = Array.from({ length: concurrentClients }, () => 
        new GraphMemoryMCPClient(config)
      );

      const startTime = Date.now();
      
      // Connect all clients concurrently
      await Promise.all(clients.map(client => client.connect()));
      
      // Perform operations with all clients
      const operations = clients.map((client, i) =>
        client.searchMemories({
          query: `concurrent client test ${i}`,
          limit: 3
        })
      );
      
      const results = await Promise.all(operations);
      
      // Disconnect all clients
      await Promise.all(clients.map(client => client.disconnect()));
      
      const totalDuration = Date.now() - startTime;

      expect(results).toHaveLength(concurrentClients);
      results.forEach(result => {
        expect(result).toBeValidSearchResult();
      });

      expect(totalDuration).toBeLessThan(10000); // Should complete within 10 seconds

      console.log(`Concurrent clients test (${concurrentClients} clients) completed in ${totalDuration}ms`);
    });
  });
}); 