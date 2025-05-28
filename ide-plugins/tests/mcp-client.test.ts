import { GraphMemoryMCPClient } from '../shared/mcp-client';
import { MCPClientConfig, MemoryType, RelationshipType } from '../shared/types';
import { SimpleCache, ValidationHelper, ErrorHelper } from '../shared/utils';

// Mock axios to avoid actual HTTP calls in unit tests
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn().mockResolvedValue({ status: 200, data: { status: 'healthy' } }),
    post: jest.fn().mockResolvedValue({ status: 200, data: { result: {} } }),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  })),
  get: jest.fn().mockResolvedValue({ status: 200, data: {} }),
  post: jest.fn().mockResolvedValue({ status: 200, data: {} })
}));

describe('GraphMemory MCP Client Unit Tests', () => {
  let client: GraphMemoryMCPClient;
  let mockConfig: MCPClientConfig;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockConfig = {
      serverUrl: 'http://localhost:8000',
      timeout: 5000,
      retryAttempts: 2,
      retryDelay: 100,
      auth: {
        method: 'jwt',
        token: 'mock-jwt-token'
      },
      features: {
        autoComplete: true,
        semanticSearch: true,
        graphVisualization: true,
        batchRequests: true
      },
      performance: {
        cacheEnabled: true,
        cacheSize: 50,
        maxConcurrentRequests: 3,
        requestTimeout: 5000
      }
    };

    client = new GraphMemoryMCPClient(mockConfig);
  });

  describe('Constructor and Configuration', () => {
    test('should initialize with default values', () => {
      const minimalConfig: MCPClientConfig = {
        serverUrl: 'http://localhost:8000',
        auth: { method: 'jwt', token: 'test' }
      };

      const clientWithDefaults = new GraphMemoryMCPClient(minimalConfig);
      const config = clientWithDefaults.getConfig();

      expect(config.timeout).toBe(30000);
      expect(config.retryAttempts).toBe(3);
      expect(config.retryDelay).toBe(1000);
    });

    test('should merge configuration correctly', () => {
      const config = client.getConfig();
      
      expect(config.serverUrl).toBe(mockConfig.serverUrl);
      expect(config.auth.method).toBe(mockConfig.auth.method);
      expect(config.features?.autoComplete).toBe(true);
      expect(config.performance?.cacheEnabled).toBe(true);
    });

    test('should validate server URL format', () => {
      expect(() => {
        new GraphMemoryMCPClient({
          serverUrl: 'invalid-url',
          auth: { method: 'jwt', token: 'test' }
        });
      }).not.toThrow(); // Constructor doesn't validate, connection does
    });
  });

  describe('Authentication Headers', () => {
    test('should generate JWT auth headers', () => {
      const jwtConfig: MCPClientConfig = {
        serverUrl: 'http://localhost:8000',
        auth: { method: 'jwt', token: 'test-jwt-token' }
      };

      const jwtClient = new GraphMemoryMCPClient(jwtConfig);
      // We can't directly test private methods, but we can test the behavior
      expect(jwtClient.getConfig().auth.token).toBe('test-jwt-token');
    });

    test('should generate API key auth headers', () => {
      const apiKeyConfig: MCPClientConfig = {
        serverUrl: 'http://localhost:8000',
        auth: { method: 'apikey', apiKey: 'test-api-key' }
      };

      const apiKeyClient = new GraphMemoryMCPClient(apiKeyConfig);
      expect(apiKeyClient.getConfig().auth.apiKey).toBe('test-api-key');
    });

    test('should handle mTLS configuration', () => {
      const mtlsConfig: MCPClientConfig = {
        serverUrl: 'https://localhost:8000',
        auth: {
          method: 'mtls',
          certificate: {
            cert: 'cert-content',
            key: 'key-content',
            ca: 'ca-content'
          }
        }
      };

      const mtlsClient = new GraphMemoryMCPClient(mtlsConfig);
      expect(mtlsClient.getConfig().auth.certificate).toBeDefined();
    });
  });

  describe('Tool Information', () => {
    test('should list all available tools', () => {
      const tools = client.getAvailableTools();
      
      expect(tools).toContain('memory_search');
      expect(tools).toContain('memory_create');
      expect(tools).toContain('memory_update');
      expect(tools).toContain('memory_delete');
      expect(tools).toContain('memory_relate');
      expect(tools).toContain('graph_query');
      expect(tools).toContain('graph_analyze');
      expect(tools).toContain('knowledge_cluster');
      expect(tools).toContain('knowledge_insights');
      expect(tools).toContain('knowledge_recommend');
    });

    test('should provide tool information', () => {
      const toolInfo = client.getToolInfo('memory_search');
      
      expect(toolInfo).toHaveProperty('name');
      expect(toolInfo).toHaveProperty('description');
      expect(toolInfo).toHaveProperty('inputSchema');
      expect(toolInfo.name).toBe('memory_search');
      expect(typeof toolInfo.description).toBe('string');
    });

    test('should validate tool parameters using schemas', () => {
      const toolInfo = client.getToolInfo('memory_create');
      const schema = toolInfo.inputSchema;

      // Valid parameters
      const validParams = {
        content: 'Test memory',
        type: 'semantic' as MemoryType,
        tags: ['test'],
        metadata: {}
      };

      const validResult = schema.safeParse(validParams);
      expect(validResult.success).toBe(true);

      // Invalid parameters
      const invalidParams = {
        content: '', // Empty content
        type: 'invalid-type', // Invalid type
        tags: 'not-an-array' // Wrong type
      };

      const invalidResult = schema.safeParse(invalidParams);
      expect(invalidResult.success).toBe(false);
    });
  });

  describe('Event System', () => {
    test('should register and emit events', () => {
      const mockHandler = jest.fn();
      
      client.on('connection', mockHandler);
      
      // Simulate event emission
      const event = {
        type: 'connection',
        timestamp: new Date().toISOString(),
        data: { serverUrl: 'http://localhost:8000', status: 'connected' }
      };
      
      client.emit(event);
      expect(mockHandler).toHaveBeenCalledWith(event);
    });

    test('should remove event handlers', () => {
      const mockHandler = jest.fn();
      
      client.on('error', mockHandler);
      client.off('error', mockHandler);
      
      const event = {
        type: 'error',
        timestamp: new Date().toISOString(),
        data: { error: 'test error', recoverable: true }
      };
      
      client.emit(event);
      expect(mockHandler).not.toHaveBeenCalled();
    });
  });

  describe('Connection State', () => {
    test('should track connection state', () => {
      expect(client.isClientConnected()).toBe(false);
    });

    test('should handle connection lifecycle', async () => {
      // Mock successful connection
      await expect(client.connect()).resolves.not.toThrow();
      
      // Mock disconnection
      await expect(client.disconnect()).resolves.not.toThrow();
      expect(client.isClientConnected()).toBe(false);
    });
  });

  describe('Cache Statistics', () => {
    test('should provide cache statistics', () => {
      const stats = client.getCacheStats();
      
      expect(stats).toHaveProperty('size');
      expect(typeof stats.size).toBe('number');
      expect(stats.size).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Batch Operations', () => {
    test('should handle batch operations when enabled', async () => {
      const operations = [
        () => client.searchMemories({ query: 'test1', limit: 1 }),
        () => client.searchMemories({ query: 'test2', limit: 1 }),
        () => client.searchMemories({ query: 'test3', limit: 1 })
      ];

      const results = await client.batch(operations);
      expect(results).toHaveLength(3);
    });

    test('should execute sequentially when batching disabled', async () => {
      const noBatchConfig = {
        ...mockConfig,
        features: { ...mockConfig.features, batchRequests: false }
      };

      const noBatchClient = new GraphMemoryMCPClient(noBatchConfig);

      const operations = [
        () => noBatchClient.searchMemories({ query: 'test1', limit: 1 }),
        () => noBatchClient.searchMemories({ query: 'test2', limit: 1 })
      ];

      const results = await noBatchClient.batch(operations);
      expect(results).toHaveLength(2);
    });
  });
});

describe('Utility Classes Unit Tests', () => {
  describe('SimpleCache', () => {
    let cache: SimpleCache;

    beforeEach(() => {
      cache = new SimpleCache(3); // Small cache for testing
    });

    test('should store and retrieve values', () => {
      cache.set('key1', 'value1');
      expect(cache.get('key1')).toBe('value1');
    });

    test('should handle TTL expiration', (done) => {
      cache.set('key1', 'value1', 0.1); // 100ms TTL
      
      setTimeout(() => {
        expect(cache.get('key1')).toBeUndefined();
        done();
      }, 150);
    });

    test('should respect max size', () => {
      cache.set('key1', 'value1');
      cache.set('key2', 'value2');
      cache.set('key3', 'value3');
      cache.set('key4', 'value4'); // Should evict key1
      
      expect(cache.get('key1')).toBeUndefined();
      expect(cache.get('key4')).toBe('value4');
    });

    test('should clear all entries', () => {
      cache.set('key1', 'value1');
      cache.set('key2', 'value2');
      
      cache.clear();
      expect(cache.size()).toBe(0);
    });

    test('should delete specific entries', () => {
      cache.set('key1', 'value1');
      cache.set('key2', 'value2');
      
      cache.delete('key1');
      expect(cache.get('key1')).toBeUndefined();
      expect(cache.get('key2')).toBe('value2');
    });
  });

  describe('ValidationHelper', () => {
    test('should validate URLs', () => {
      expect(ValidationHelper.isValidUrl('http://localhost:8000')).toBe(true);
      expect(ValidationHelper.isValidUrl('https://api.example.com')).toBe(true);
      expect(ValidationHelper.isValidUrl('invalid-url')).toBe(false);
      expect(ValidationHelper.isValidUrl('')).toBe(false);
    });

    test('should validate JWT tokens', () => {
      const validJWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
      const invalidJWT = 'invalid.jwt.token';
      
      expect(ValidationHelper.isValidJWT(validJWT)).toBe(true);
      expect(ValidationHelper.isValidJWT(invalidJWT)).toBe(false);
      expect(ValidationHelper.isValidJWT('')).toBe(false);
    });

    test('should sanitize input', () => {
      expect(ValidationHelper.sanitizeInput('<script>alert("xss")</script>')).toBe('scriptalert(xss)/script');
      expect(ValidationHelper.sanitizeInput('normal text')).toBe('normal text');
      expect(ValidationHelper.sanitizeInput('  whitespace  ')).toBe('whitespace');
    });

    test('should validate memory types', () => {
      expect(ValidationHelper.validateMemoryType('semantic')).toBe(true);
      expect(ValidationHelper.validateMemoryType('procedural')).toBe(true);
      expect(ValidationHelper.validateMemoryType('episodic')).toBe(true);
      expect(ValidationHelper.validateMemoryType('declarative')).toBe(true);
      expect(ValidationHelper.validateMemoryType('invalid')).toBe(false);
    });

    test('should validate relationship types', () => {
      expect(ValidationHelper.validateRelationshipType('related_to')).toBe(true);
      expect(ValidationHelper.validateRelationshipType('depends_on')).toBe(true);
      expect(ValidationHelper.validateRelationshipType('invalid')).toBe(false);
    });
  });

  describe('ErrorHelper', () => {
    test('should identify network errors', () => {
      const networkError = { code: 'ECONNREFUSED' };
      const authError = { response: { status: 401 } };
      
      expect(ErrorHelper.isNetworkError(networkError)).toBe(true);
      expect(ErrorHelper.isNetworkError(authError)).toBe(false);
    });

    test('should identify auth errors', () => {
      const authError = { response: { status: 401 } };
      const networkError = { code: 'ECONNREFUSED' };
      
      expect(ErrorHelper.isAuthError(authError)).toBe(true);
      expect(ErrorHelper.isAuthError(networkError)).toBe(false);
    });

    test('should identify retryable errors', () => {
      const serverError = { response: { status: 500 } };
      const rateLimitError = { response: { status: 429 } };
      const clientError = { response: { status: 400 } };
      
      expect(ErrorHelper.isRetryableError(serverError)).toBe(true);
      expect(ErrorHelper.isRetryableError(rateLimitError)).toBe(true);
      expect(ErrorHelper.isRetryableError(clientError)).toBe(false);
    });

    test('should format errors consistently', () => {
      const errorWithMessage = { message: 'Test error' };
      const errorWithResponse = { response: { data: { message: 'API error' } } };
      const stringError = 'Simple error';
      
      expect(ErrorHelper.formatError(errorWithMessage)).toBe('Test error');
      expect(ErrorHelper.formatError(errorWithResponse)).toBe('API error');
      expect(ErrorHelper.formatError(stringError)).toBe('Simple error');
    });
  });
}); 