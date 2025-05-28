// Mock axios for testing
export default {
  create: jest.fn(() => ({
    get: jest.fn().mockResolvedValue({ 
      status: 200, 
      data: { status: 'healthy' } 
    }),
    post: jest.fn().mockResolvedValue({ 
      status: 200, 
      data: { 
        result: {
          id: 'mock_memory_id',
          content: 'Mock memory content',
          type: 'semantic',
          tags: ['mock', 'test'],
          metadata: { test: true },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          memories: [],
          total: 0,
          query_time: 10
        }
      }
    }),
    interceptors: {
      request: { 
        use: jest.fn((fn) => fn)
      },
      response: { 
        use: jest.fn((fn) => fn)
      }
    }
  })),
  get: jest.fn().mockResolvedValue({ status: 200, data: {} }),
  post: jest.fn().mockResolvedValue({ status: 200, data: {} })
}; 