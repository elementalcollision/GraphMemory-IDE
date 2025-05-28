import { Memory, Relationship, SearchResult } from '../shared/types';

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidMemory(): R;
      toBeValidRelationship(): R;
      toBeValidSearchResult(): R;
    }
  }
} 