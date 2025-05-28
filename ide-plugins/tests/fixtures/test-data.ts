import { Memory, Relationship, MemoryType, RelationshipType } from '../../shared/types';

export const mockMemories: Memory[] = [
  {
    id: 'mem_001',
    content: 'React hooks provide a way to use state and lifecycle methods in functional components',
    type: 'semantic' as MemoryType,
    tags: ['react', 'hooks', 'frontend'],
    metadata: {
      source: 'documentation',
      confidence: 0.95,
      language: 'javascript'
    },
    embedding: [0.1, 0.2, 0.3, 0.4, 0.5],
    created_at: '2025-01-27T10:00:00Z',
    updated_at: '2025-01-27T10:00:00Z',
    relationships: []
  },
  {
    id: 'mem_002',
    content: 'useState is a React hook that allows you to add state to functional components',
    type: 'procedural' as MemoryType,
    tags: ['react', 'hooks', 'useState', 'state'],
    metadata: {
      source: 'code-example',
      confidence: 0.9,
      language: 'javascript'
    },
    embedding: [0.2, 0.3, 0.4, 0.5, 0.6],
    created_at: '2025-01-27T10:15:00Z',
    updated_at: '2025-01-27T10:15:00Z',
    relationships: []
  },
  {
    id: 'mem_003',
    content: 'During the team meeting on 2025-01-27, we decided to migrate from class components to hooks',
    type: 'episodic' as MemoryType,
    tags: ['meeting', 'decision', 'migration', 'hooks'],
    metadata: {
      source: 'meeting-notes',
      confidence: 1.0,
      participants: ['john', 'jane', 'bob'],
      date: '2025-01-27'
    },
    embedding: [0.3, 0.4, 0.5, 0.6, 0.7],
    created_at: '2025-01-27T14:30:00Z',
    updated_at: '2025-01-27T14:30:00Z',
    relationships: []
  },
  {
    id: 'mem_004',
    content: 'TypeScript provides static type checking for JavaScript applications',
    type: 'declarative' as MemoryType,
    tags: ['typescript', 'types', 'javascript'],
    metadata: {
      source: 'documentation',
      confidence: 0.98,
      language: 'typescript'
    },
    embedding: [0.4, 0.5, 0.6, 0.7, 0.8],
    created_at: '2025-01-27T11:00:00Z',
    updated_at: '2025-01-27T11:00:00Z',
    relationships: []
  }
];

export const mockRelationships: Relationship[] = [
  {
    id: 'rel_001',
    source_id: 'mem_001',
    target_id: 'mem_002',
    type: 'related_to' as RelationshipType,
    weight: 0.8,
    metadata: {
      reason: 'Both about React hooks',
      confidence: 0.9
    },
    created_at: '2025-01-27T10:30:00Z'
  },
  {
    id: 'rel_002',
    source_id: 'mem_003',
    target_id: 'mem_001',
    type: 'supports' as RelationshipType,
    weight: 0.7,
    metadata: {
      reason: 'Meeting decision supports using hooks',
      confidence: 0.85
    },
    created_at: '2025-01-27T14:45:00Z'
  },
  {
    id: 'rel_003',
    source_id: 'mem_002',
    target_id: 'mem_004',
    type: 'depends_on' as RelationshipType,
    weight: 0.6,
    metadata: {
      reason: 'useState can be typed with TypeScript',
      confidence: 0.8
    },
    created_at: '2025-01-27T11:15:00Z'
  }
];

export const mockSearchResults = {
  memories: mockMemories.slice(0, 2),
  total: 2,
  query_time: 45,
  suggestions: ['react hooks', 'useState', 'functional components']
};

export const mockGraphAnalysisResult = {
  analysis_type: 'centrality',
  results: {
    betweenness_centrality: {
      'mem_001': 0.8,
      'mem_002': 0.6,
      'mem_003': 0.4,
      'mem_004': 0.3
    },
    closeness_centrality: {
      'mem_001': 0.7,
      'mem_002': 0.5,
      'mem_003': 0.6,
      'mem_004': 0.4
    }
  },
  visualization: {
    nodes: [
      {
        id: 'mem_001',
        label: 'React Hooks',
        type: 'semantic',
        properties: { tags: ['react', 'hooks'] },
        size: 10,
        color: '#ff6b6b'
      },
      {
        id: 'mem_002',
        label: 'useState Hook',
        type: 'procedural',
        properties: { tags: ['react', 'useState'] },
        size: 8,
        color: '#4ecdc4'
      }
    ],
    edges: [
      {
        id: 'rel_001',
        source: 'mem_001',
        target: 'mem_002',
        type: 'related_to',
        weight: 0.8,
        color: '#95e1d3'
      }
    ]
  },
  insights: [
    'mem_001 has the highest betweenness centrality, indicating it\'s a key connector',
    'The graph shows strong clustering around React-related concepts',
    'TypeScript memories are less connected to the main cluster'
  ]
};

export const mockClusterResult = {
  clusters: [
    {
      id: 0,
      memories: [mockMemories[0], mockMemories[1]],
      centroid: 'React development concepts',
      keywords: ['react', 'hooks', 'frontend', 'javascript']
    },
    {
      id: 1,
      memories: [mockMemories[2]],
      centroid: 'Team decisions and meetings',
      keywords: ['meeting', 'decision', 'team', 'migration']
    },
    {
      id: 2,
      memories: [mockMemories[3]],
      centroid: 'TypeScript and type safety',
      keywords: ['typescript', 'types', 'static-analysis']
    }
  ],
  algorithm: 'kmeans',
  parameters: {
    num_clusters: 3,
    max_iterations: 100,
    tolerance: 0.001
  }
};

export const mockInsightResult = {
  insights: [
    {
      type: 'pattern',
      description: 'Strong focus on React development with emphasis on modern patterns like hooks',
      confidence: 0.92,
      supporting_evidence: ['mem_001', 'mem_002', 'mem_003']
    },
    {
      type: 'gap',
      description: 'Limited coverage of testing strategies for React components',
      confidence: 0.78,
      supporting_evidence: []
    },
    {
      type: 'trend',
      description: 'Recent shift towards functional programming paradigms in frontend development',
      confidence: 0.85,
      supporting_evidence: ['mem_003']
    }
  ],
  context: 'React development workflow',
  generated_at: '2025-01-27T12:41:19Z'
};

export const mockRecommendationResult = {
  recommendations: [
    {
      memory: mockMemories[1],
      score: 0.89,
      reason: 'Highly relevant to current React hooks context'
    },
    {
      memory: mockMemories[3],
      score: 0.72,
      reason: 'TypeScript integration with React hooks is valuable'
    },
    {
      memory: mockMemories[2],
      score: 0.65,
      reason: 'Team decision context provides implementation guidance'
    }
  ],
  context: 'React hooks implementation',
  recommendation_type: 'related'
};

export const mockConfigurations = {
  minimal: {
    serverUrl: 'http://localhost:8000',
    auth: { method: 'jwt' as const, token: 'test-token' }
  },
  full: {
    serverUrl: 'http://localhost:8000',
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000,
    auth: {
      method: 'jwt' as const,
      token: 'test-jwt-token'
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
  },
  mtls: {
    serverUrl: 'https://localhost:8000',
    auth: {
      method: 'mtls' as const,
      certificate: {
        cert: '-----BEGIN CERTIFICATE-----\nMOCK_CERT_DATA\n-----END CERTIFICATE-----',
        key: '-----BEGIN PRIVATE KEY-----\nMOCK_KEY_DATA\n-----END PRIVATE KEY-----',
        ca: '-----BEGIN CERTIFICATE-----\nMOCK_CA_DATA\n-----END CERTIFICATE-----'
      }
    }
  }
};

export const mockErrorResponses = {
  networkError: {
    code: 'ECONNREFUSED',
    message: 'Connection refused'
  },
  authError: {
    response: {
      status: 401,
      data: {
        message: 'Invalid authentication token'
      }
    }
  },
  validationError: {
    response: {
      status: 400,
      data: {
        message: 'Invalid request parameters',
        details: {
          content: 'Content is required',
          type: 'Invalid memory type'
        }
      }
    }
  },
  serverError: {
    response: {
      status: 500,
      data: {
        message: 'Internal server error'
      }
    }
  },
  rateLimitError: {
    response: {
      status: 429,
      data: {
        message: 'Rate limit exceeded',
        retry_after: 60
      }
    }
  }
};

export const mockEvents = {
  connection: {
    type: 'connection',
    timestamp: '2025-01-27T12:41:19Z',
    data: {
      serverUrl: 'http://localhost:8000',
      status: 'connected'
    }
  },
  disconnection: {
    type: 'disconnection',
    timestamp: '2025-01-27T12:41:19Z',
    data: {
      serverUrl: 'http://localhost:8000',
      status: 'disconnected'
    }
  },
  error: {
    type: 'error',
    timestamp: '2025-01-27T12:41:19Z',
    data: {
      error: 'Connection timeout',
      context: 'memory_search',
      recoverable: true
    }
  },
  performance: {
    type: 'performance',
    timestamp: '2025-01-27T12:41:19Z',
    data: {
      operation: 'memory_search',
      duration: 150,
      success: true,
      cacheHit: false
    }
  }
};

export const mockToolParameters = {
  memory_search: {
    valid: {
      query: 'React hooks',
      limit: 10,
      type: 'semantic' as MemoryType,
      tags: ['react'],
      threshold: 0.7
    },
    invalid: {
      query: '', // Empty query
      limit: -1, // Negative limit
      type: 'invalid-type', // Invalid type
      threshold: 1.5 // Invalid threshold
    }
  },
  memory_create: {
    valid: {
      content: 'Test memory content',
      type: 'semantic' as MemoryType,
      tags: ['test'],
      metadata: { source: 'test' }
    },
    invalid: {
      content: '', // Empty content
      type: 'invalid-type', // Invalid type
      tags: 'not-an-array' // Wrong type
    }
  },
  memory_relate: {
    valid: {
      source_id: 'mem_001',
      target_id: 'mem_002',
      type: 'related_to' as RelationshipType,
      weight: 0.8,
      metadata: {}
    },
    invalid: {
      source_id: '', // Empty ID
      target_id: 'mem_002',
      type: 'invalid-type', // Invalid type
      weight: 2.0 // Invalid weight
    }
  }
};

// Helper functions for creating properly typed test parameters
export const createSearchParams = (overrides: Partial<{
  query: string;
  limit: number;
  type: 'procedural' | 'semantic' | 'episodic' | 'declarative';
  tags: string[];
  threshold: number;
}> = {}) => ({
  query: 'test query',
  limit: 10,
  threshold: 0.7,
  ...overrides
});

export const createMemoryParams = (overrides: Partial<{
  content: string;
  type: 'procedural' | 'semantic' | 'episodic' | 'declarative';
  tags: string[];
  metadata: Record<string, any>;
}> = {}) => ({
  content: 'Test memory content',
  type: 'semantic' as const,
  tags: ['test'],
  metadata: { test: true },
  ...overrides
});

export const createRelationshipParams = (overrides: Partial<{
  source_id: string;
  target_id: string;
  type: 'related_to' | 'depends_on' | 'part_of' | 'similar_to' | 'contradicts' | 'supports' | 'follows' | 'precedes';
  weight: number;
  metadata: Record<string, any>;
}> = {}) => ({
  source_id: 'mem_123',
  target_id: 'mem_456',
  type: 'related_to' as const,
  weight: 1.0,
  metadata: {},
  ...overrides
});

export const createAnalysisParams = (overrides: Partial<{
  analysis_type: 'centrality' | 'clustering' | 'paths' | 'communities' | 'statistics';
  node_filter: string;
  depth: number;
}> = {}) => ({
  analysis_type: 'statistics' as const,
  depth: 3,
  ...overrides
});

export const createRecommendationParams = (overrides: Partial<{
  context: string;
  limit: number;
  type: 'similar' | 'related' | 'complementary' | 'next_steps';
}> = {}) => ({
  context: 'test context',
  limit: 5,
  type: 'related' as const,
  ...overrides
}); 