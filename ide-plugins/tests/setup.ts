// Global test setup for GraphMemory IDE Plugins
import './jest.d.ts';

// Mock console methods to reduce noise in tests
const originalConsole = { ...console };

beforeAll(() => {
  // Suppress console output during tests unless explicitly needed
  if (process.env.TEST_VERBOSE !== 'true') {
    console.log = jest.fn();
    console.info = jest.fn();
    console.warn = jest.fn();
    console.error = jest.fn();
    console.debug = jest.fn();
  }
});

afterAll(() => {
  // Restore console methods
  Object.assign(console, originalConsole);
  jest.restoreAllMocks();
});

// Mock environment variables for tests
process.env.NODE_ENV = 'test';
process.env.GRAPHMEMORY_SERVER_URL = 'http://localhost:8000';
process.env.GRAPHMEMORY_AUTH_METHOD = 'jwt';
process.env.GRAPHMEMORY_AUTH_TOKEN = 'test-jwt-token';

// Global error handler for unhandled promise rejections in tests
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Custom Jest matchers
expect.extend({
  toBeValidMemory(received: any) {
    const pass = received &&
      typeof received.id === 'string' &&
      typeof received.content === 'string' &&
      typeof received.type === 'string' &&
      Array.isArray(received.tags) &&
      typeof received.metadata === 'object' &&
      typeof received.created_at === 'string' &&
      typeof received.updated_at === 'string';

    if (pass) {
      return {
        message: () => `expected ${JSON.stringify(received)} not to be a valid memory`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${JSON.stringify(received)} to be a valid memory`,
        pass: false,
      };
    }
  },

  toBeValidRelationship(received: any) {
    const pass = received &&
      typeof received.id === 'string' &&
      typeof received.source_id === 'string' &&
      typeof received.target_id === 'string' &&
      typeof received.type === 'string' &&
      typeof received.created_at === 'string';

    if (pass) {
      return {
        message: () => `expected ${JSON.stringify(received)} not to be a valid relationship`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${JSON.stringify(received)} to be a valid relationship`,
        pass: false,
      };
    }
  },

  toBeValidSearchResult(received: any) {
    const pass = received &&
      Array.isArray(received.memories) &&
      typeof received.total === 'number' &&
      typeof received.query_time === 'number';

    if (pass) {
      return {
        message: () => `expected ${JSON.stringify(received)} not to be a valid search result`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${JSON.stringify(received)} to be a valid search result`,
        pass: false,
      };
    }
  }
});

// Test utilities
export const testUtils = {
  // Wait for a specified amount of time
  wait: (ms: number): Promise<void> => {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  // Create a mock function that resolves after a delay
  createDelayedMock: <T>(value: T, delay: number = 100) => {
    return jest.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(value), delay))
    );
  },

  // Create a mock function that rejects after a delay
  createDelayedRejectMock: (error: any, delay: number = 100) => {
    return jest.fn().mockImplementation(() => 
      new Promise((_, reject) => setTimeout(() => reject(error), delay))
    );
  },

  // Generate a random string for test data
  randomString: (length: number = 10): string => {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  },

  // Generate a mock memory ID
  mockMemoryId: (): string => `mem_${Math.random().toString(36).substr(2, 9)}`,

  // Generate a mock relationship ID
  mockRelationshipId: (): string => `rel_${Math.random().toString(36).substr(2, 9)}`,

  // Create a mock timestamp
  mockTimestamp: (): string => new Date().toISOString()
}; 