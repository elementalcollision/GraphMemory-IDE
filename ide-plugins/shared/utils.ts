import { Cache } from './types';

/**
 * Simple in-memory cache implementation
 */
export class SimpleCache implements Cache {
  private store: Map<string, { value: any; expiry?: number }> = new Map();
  private maxSize: number;

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize;
  }

  get<T>(key: string): T | undefined {
    const item = this.store.get(key);
    if (!item) {
      return undefined;
    }

    // Check if expired
    if (item.expiry && Date.now() > item.expiry) {
      this.store.delete(key);
      return undefined;
    }

    return item.value as T;
  }

  set<T>(key: string, value: T, ttl?: number): void {
    // Evict oldest items if at capacity
    if (this.store.size >= this.maxSize && !this.store.has(key)) {
      const firstKey = this.store.keys().next().value;
      if (firstKey) {
        this.store.delete(firstKey);
      }
    }

    const expiry = ttl ? Date.now() + (ttl * 1000) : undefined;
    this.store.set(key, { value, expiry });
  }

  delete(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  size(): number {
    return this.store.size;
  }
}

/**
 * Configuration loader that supports multiple sources
 */
export class ConfigLoader {
  static loadFromFile(filePath: string): any {
    try {
      const fs = require('fs');
      const path = require('path');
      
      if (!fs.existsSync(filePath)) {
        return null;
      }

      const content = fs.readFileSync(filePath, 'utf8');
      const ext = path.extname(filePath).toLowerCase();

      switch (ext) {
        case '.json':
          return JSON.parse(content);
        case '.yaml':
        case '.yml':
          const yaml = require('yaml');
          return yaml.parse(content);
        default:
          throw new Error(`Unsupported config file format: ${ext}`);
      }
    } catch (error) {
      console.warn(`Failed to load config from ${filePath}:`, error);
      return null;
    }
  }

  static loadFromEnv(prefix: string = 'GRAPHMEMORY_'): any {
    const config: any = {};
    
    for (const [key, value] of Object.entries(process.env)) {
      if (key.startsWith(prefix)) {
        const configKey = key.slice(prefix.length).toLowerCase();
        const keyPath = configKey.split('_');
        
        let current = config;
        for (let i = 0; i < keyPath.length - 1; i++) {
          if (!current[keyPath[i]]) {
            current[keyPath[i]] = {};
          }
          current = current[keyPath[i]];
        }
        
        current[keyPath[keyPath.length - 1]] = this.parseEnvValue(value);
      }
    }
    
    return config;
  }

  static loadFromHomeDir(): any {
    const os = require('os');
    const path = require('path');
    
    const homeDir = os.homedir();
    const configPaths = [
      path.join(homeDir, '.graphmemory.json'),
      path.join(homeDir, '.graphmemory.yaml'),
      path.join(homeDir, '.graphmemory.yml'),
      path.join(homeDir, '.config', 'graphmemory', 'config.json'),
      path.join(homeDir, '.config', 'graphmemory', 'config.yaml')
    ];

    for (const configPath of configPaths) {
      const config = this.loadFromFile(configPath);
      if (config) {
        return config;
      }
    }

    return null;
  }

  private static parseEnvValue(value: string | undefined): any {
    if (!value) return undefined;
    
    // Try to parse as JSON first
    try {
      return JSON.parse(value);
    } catch {
      // If not JSON, try boolean
      if (value.toLowerCase() === 'true') return true;
      if (value.toLowerCase() === 'false') return false;
      
      // Try number
      const num = Number(value);
      if (!isNaN(num)) return num;
      
      // Return as string
      return value;
    }
  }
}

/**
 * Retry utility with exponential backoff
 */
export class RetryHelper {
  static async withRetry<T>(
    operation: () => Promise<T>,
    maxAttempts: number = 3,
    baseDelay: number = 1000,
    maxDelay: number = 10000
  ): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        if (attempt === maxAttempts) {
          throw lastError;
        }
        
        const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
        await this.sleep(delay);
      }
    }
    
    throw lastError!;
  }

  private static sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Validation utilities
 */
export class ValidationHelper {
  static isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  static isValidJWT(token: string): boolean {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return false;
      
      // Try to decode the header and payload
      JSON.parse(atob(parts[0]));
      JSON.parse(atob(parts[1]));
      
      return true;
    } catch {
      return false;
    }
  }

  static sanitizeInput(input: string): string {
    return input
      .replace(/[<>]/g, '') // Remove potential HTML tags
      .replace(/['"]/g, '') // Remove quotes
      .trim();
  }

  static validateMemoryType(type: string): boolean {
    const validTypes = ['procedural', 'semantic', 'episodic', 'declarative'];
    return validTypes.includes(type);
  }

  static validateRelationshipType(type: string): boolean {
    const validTypes = [
      'related_to', 'depends_on', 'part_of', 'similar_to',
      'contradicts', 'supports', 'follows', 'precedes'
    ];
    return validTypes.includes(type);
  }
}

/**
 * Performance monitoring utilities
 */
export class PerformanceMonitor {
  private static metrics: Map<string, number[]> = new Map();

  static recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    
    const values = this.metrics.get(name)!;
    values.push(value);
    
    // Keep only the last 100 measurements
    if (values.length > 100) {
      values.shift();
    }
  }

  static getMetrics(name: string): { avg: number; min: number; max: number; count: number } | null {
    const values = this.metrics.get(name);
    if (!values || values.length === 0) {
      return null;
    }

    const sum = values.reduce((a, b) => a + b, 0);
    return {
      avg: sum / values.length,
      min: Math.min(...values),
      max: Math.max(...values),
      count: values.length
    };
  }

  static getAllMetrics(): Record<string, any> {
    const result: Record<string, any> = {};
    for (const [name] of this.metrics) {
      result[name] = this.getMetrics(name);
    }
    return result;
  }

  static clearMetrics(): void {
    this.metrics.clear();
  }
}

/**
 * Debounce utility for rate limiting
 */
export class DebounceHelper {
  private static timers: Map<string, NodeJS.Timeout> = new Map();

  static debounce<T extends (...args: any[]) => any>(
    key: string,
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void {
    return (...args: Parameters<T>) => {
      const existingTimer = this.timers.get(key);
      if (existingTimer) {
        clearTimeout(existingTimer);
      }

      const timer = setTimeout(() => {
        func(...args);
        this.timers.delete(key);
      }, delay);

      this.timers.set(key, timer);
    };
  }

  static clearDebounce(key: string): void {
    const timer = this.timers.get(key);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(key);
    }
  }

  static clearAllDebounces(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
  }
}

/**
 * Error handling utilities
 */
export class ErrorHelper {
  static isNetworkError(error: any): boolean {
    return !!(error?.code === 'ECONNREFUSED' ||
           error?.code === 'ENOTFOUND' ||
           error?.code === 'ETIMEDOUT' ||
           error?.message?.includes('Network Error'));
  }

  static isAuthError(error: any): boolean {
    return !!(error?.response?.status === 401 ||
           error?.response?.status === 403 ||
           error?.message?.includes('Unauthorized') ||
           error?.message?.includes('Forbidden'));
  }

  static isRetryableError(error: any): boolean {
    if (this.isNetworkError(error)) return true;
    
    const status = error?.response?.status;
    return status >= 500 || status === 429; // Server errors or rate limiting
  }

  static formatError(error: any): string {
    if (error?.response?.data?.message) {
      return error.response.data.message;
    }
    
    if (error?.message) {
      return error.message;
    }
    
    return String(error);
  }
}

/**
 * Memory formatting utilities
 */
export class MemoryFormatter {
  static formatMemoryContent(content: string, maxLength: number = 200): string {
    if (content.length <= maxLength) {
      return content;
    }
    
    return content.substring(0, maxLength - 3) + '...';
  }

  static formatTags(tags: string[]): string {
    return tags.map(tag => `#${tag}`).join(' ');
  }

  static formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  }

  static formatMemoryType(type: string): string {
    const typeMap: Record<string, string> = {
      procedural: '🔧 Procedural',
      semantic: '📚 Semantic',
      episodic: '📅 Episodic',
      declarative: '📝 Declarative'
    };
    
    return typeMap[type] || type;
  }

  static formatRelationshipType(type: string): string {
    const typeMap: Record<string, string> = {
      related_to: '🔗 Related to',
      depends_on: '⬅️ Depends on',
      part_of: '🧩 Part of',
      similar_to: '🔄 Similar to',
      contradicts: '❌ Contradicts',
      supports: '✅ Supports',
      follows: '➡️ Follows',
      precedes: '⬅️ Precedes'
    };
    
    return typeMap[type] || type;
  }
}

/**
 * Search utilities
 */
export class SearchHelper {
  static highlightMatches(text: string, query: string): string {
    if (!query.trim()) return text;
    
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '**$1**');
  }

  static extractKeywords(text: string, maxKeywords: number = 10): string[] {
    // Simple keyword extraction
    const words = text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3);
    
    // Count word frequency
    const frequency: Record<string, number> = {};
    for (const word of words) {
      frequency[word] = (frequency[word] || 0) + 1;
    }
    
    // Sort by frequency and return top keywords
    return Object.entries(frequency)
      .sort(([, a], [, b]) => b - a)
      .slice(0, maxKeywords)
      .map(([word]) => word);
  }

  static generateSearchSuggestions(query: string, memories: any[]): string[] {
    // Simple suggestion generation based on existing memory content
    const suggestions: Set<string> = new Set();
    
    for (const memory of memories) {
      const content = memory.content.toLowerCase();
      const tags = memory.tags || [];
      
      // Add tag suggestions
      for (const tag of tags) {
        if (tag.toLowerCase().includes(query.toLowerCase())) {
          suggestions.add(tag);
        }
      }
      
      // Add content-based suggestions
      const words = content.split(/\s+/);
      for (let i = 0; i < words.length - 1; i++) {
        const phrase = `${words[i]} ${words[i + 1]}`;
        if (phrase.includes(query.toLowerCase()) && phrase.length > query.length) {
          suggestions.add(phrase);
        }
      }
    }
    
    return Array.from(suggestions).slice(0, 5);
  }
}

/**
 * Test utilities
 */
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