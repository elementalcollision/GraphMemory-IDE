import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';

// Types for real-time data system
interface WebSocketConfig {
  url: string;
  protocols?: string[];
  options?: {
    maxReconnectAttempts?: number;
    reconnectInterval?: number;
    heartbeatInterval?: number;
    timeout?: number;
  };
}

interface DataTransformation {
  type: 'filter' | 'aggregate' | 'sort' | 'group' | 'transform';
  field?: string;
  operation?: string;
  value?: any;
  custom?: (data: any) => any;
}

interface SubscriptionConfig {
  channel: string;
  dataType: 'memory' | 'analytics' | 'metrics' | 'events';
  transformations?: DataTransformation[];
  bufferSize?: number;
  aggregationWindow?: number;
  updateFrequency?: number;
}

interface DataBuffer<T = any> {
  data: T[];
  timestamp: number;
  size: number;
  maxSize: number;
}

interface ConnectionState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';
  lastConnected?: number;
  reconnectAttempts: number;
  error?: string;
}

interface RealTimeDataContextType {
  // Connection management
  connect: (config: WebSocketConfig) => Promise<void>;
  disconnect: () => void;
  connectionState: ConnectionState;
  
  // Data subscription
  subscribe: (config: SubscriptionConfig, callback: (data: any) => void) => string;
  unsubscribe: (subscriptionId: string) => void;
  
  // Data access
  getLatestData: (channel: string) => any;
  getHistoricalData: (channel: string, timeRange?: { start: number; end: number }) => any[];
  
  // Performance metrics
  getMetrics: () => {
    connectionsCount: number;
    subscriptionsCount: number;
    dataTransferRate: number;
    latency: number;
  };
}

// Create context
const RealTimeDataContext = createContext<RealTimeDataContextType | null>(null);

// Custom hook for accessing real-time data
export const useRealTimeData = () => {
  const context = useContext(RealTimeDataContext);
  if (!context) {
    throw new Error('useRealTimeData must be used within a RealTimeDataProvider');
  }
  return context;
};

// WebSocket manager class
class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig | null = null;
  private subscriptions = new Map<string, SubscriptionConfig>();
  private callbacks = new Map<string, (data: any) => void>();
  private buffers = new Map<string, DataBuffer>();
  private connectionState: ConnectionState = {
    status: 'disconnected',
    reconnectAttempts: 0
  };
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private metrics = {
    messagesReceived: 0,
    messagesSent: 0,
    bytesReceived: 0,
    bytesSent: 0,
    connectionStartTime: 0,
    lastMessageTime: 0
  };

  constructor(private onStateChange: (state: ConnectionState) => void) {}

  async connect(config: WebSocketConfig): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      this.config = config;
      this.updateConnectionState({ status: 'connecting', reconnectAttempts: 0 });

      try {
        this.ws = new WebSocket(config.url, config.protocols);
        this.setupEventListeners(resolve, reject);
      } catch (error) {
        this.updateConnectionState({ 
          status: 'error', 
          error: `Failed to create WebSocket: ${error}` 
        });
        reject(error);
      }
    });
  }

  private setupEventListeners(resolve: () => void, reject: (error: Error) => void) {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.updateConnectionState({ 
        status: 'connected', 
        lastConnected: Date.now(),
        reconnectAttempts: 0 
      });
      this.metrics.connectionStartTime = Date.now();
      this.startHeartbeat();
      resolve();
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(event.data);
      this.metrics.messagesReceived++;
      this.metrics.bytesReceived += event.data.length;
      this.metrics.lastMessageTime = Date.now();
    };

    this.ws.onclose = (event) => {
      this.cleanup();
      if (event.wasClean) {
        this.updateConnectionState({ status: 'disconnected' });
      } else {
        this.handleConnectionLoss();
      }
    };

    this.ws.onerror = (error) => {
      this.updateConnectionState({ 
        status: 'error', 
        error: 'WebSocket connection error' 
      });
      reject(new Error('WebSocket connection failed'));
    };
  }

  private handleMessage(data: string) {
    try {
      const message = JSON.parse(data);
      
      if (message.type === 'heartbeat') {
        this.sendHeartbeatResponse();
        return;
      }

      if (message.channel && this.subscriptions.has(message.channel)) {
        const subscription = this.subscriptions.get(message.channel)!;
        const callback = this.callbacks.get(message.channel);
        
        if (callback) {
          let processedData = message.data;
          
          // Apply transformations
          if (subscription.transformations) {
            processedData = this.applyTransformations(processedData, subscription.transformations);
          }
          
          // Update buffer
          this.updateBuffer(message.channel, processedData, subscription.bufferSize || 100);
          
          // Call subscriber callback
          callback(processedData);
        }
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private applyTransformations(data: any, transformations: DataTransformation[]): any {
    let result = data;
    
    for (const transform of transformations) {
      switch (transform.type) {
        case 'filter':
          if (Array.isArray(result) && transform.field && transform.value) {
            result = result.filter(item => item[transform.field] === transform.value);
          }
          break;
          
        case 'aggregate':
          if (Array.isArray(result) && transform.field && transform.operation) {
            switch (transform.operation) {
              case 'sum':
                result = result.reduce((sum, item) => sum + (item[transform.field] || 0), 0);
                break;
              case 'avg':
                result = result.reduce((sum, item) => sum + (item[transform.field] || 0), 0) / result.length;
                break;
              case 'count':
                result = result.length;
                break;
              case 'max':
                result = Math.max(...result.map(item => item[transform.field] || 0));
                break;
              case 'min':
                result = Math.min(...result.map(item => item[transform.field] || 0));
                break;
            }
          }
          break;
          
        case 'sort':
          if (Array.isArray(result) && transform.field) {
            result = result.sort((a, b) => {
              const aVal = a[transform.field!];
              const bVal = b[transform.field!];
              return transform.value === 'desc' ? bVal - aVal : aVal - bVal;
            });
          }
          break;
          
        case 'group':
          if (Array.isArray(result) && transform.field) {
            const grouped = result.reduce((groups, item) => {
              const key = item[transform.field!];
              if (!groups[key]) groups[key] = [];
              groups[key].push(item);
              return groups;
            }, {} as Record<string, any[]>);
            result = Object.entries(grouped).map(([key, values]) => ({ key, values }));
          }
          break;
          
        case 'transform':
          if (transform.custom) {
            result = transform.custom(result);
          }
          break;
      }
    }
    
    return result;
  }

  private updateBuffer(channel: string, data: any, maxSize: number) {
    let buffer = this.buffers.get(channel);
    
    if (!buffer) {
      buffer = {
        data: [],
        timestamp: Date.now(),
        size: 0,
        maxSize
      };
      this.buffers.set(channel, buffer);
    }
    
    buffer.data.push(data);
    buffer.timestamp = Date.now();
    buffer.size = buffer.data.length;
    
    // Maintain buffer size
    if (buffer.size > maxSize) {
      buffer.data = buffer.data.slice(-maxSize);
      buffer.size = buffer.data.length;
    }
  }

  private startHeartbeat() {
    if (this.config?.options?.heartbeatInterval) {
      this.heartbeatInterval = setInterval(() => {
        this.sendMessage({ type: 'heartbeat', timestamp: Date.now() });
      }, this.config.options.heartbeatInterval);
    }
  }

  private sendHeartbeatResponse() {
    this.sendMessage({ type: 'heartbeat_response', timestamp: Date.now() });
  }

  private handleConnectionLoss() {
    if (this.config?.options?.maxReconnectAttempts && 
        this.connectionState.reconnectAttempts < this.config.options.maxReconnectAttempts) {
      
      this.updateConnectionState({ 
        status: 'reconnecting',
        reconnectAttempts: this.connectionState.reconnectAttempts + 1
      });
      
      const delay = this.config.options.reconnectInterval || 5000;
      this.reconnectTimeout = setTimeout(() => {
        this.connect(this.config!);
      }, delay);
    } else {
      this.updateConnectionState({ status: 'disconnected' });
    }
  }

  subscribe(config: SubscriptionConfig, callback: (data: any) => void): string {
    const subscriptionId = `${config.channel}_${Date.now()}`;
    this.subscriptions.set(subscriptionId, config);
    this.callbacks.set(subscriptionId, callback);
    
    // Send subscription message
    this.sendMessage({
      type: 'subscribe',
      channel: config.channel,
      dataType: config.dataType,
      subscriptionId
    });
    
    return subscriptionId;
  }

  unsubscribe(subscriptionId: string) {
    const subscription = this.subscriptions.get(subscriptionId);
    if (subscription) {
      this.sendMessage({
        type: 'unsubscribe',
        subscriptionId
      });
      
      this.subscriptions.delete(subscriptionId);
      this.callbacks.delete(subscriptionId);
      this.buffers.delete(subscriptionId);
    }
  }

  getLatestData(channel: string): any {
    const buffer = this.buffers.get(channel);
    return buffer && buffer.data.length > 0 ? buffer.data[buffer.data.length - 1] : null;
  }

  getHistoricalData(channel: string, timeRange?: { start: number; end: number }): any[] {
    const buffer = this.buffers.get(channel);
    if (!buffer) return [];
    
    if (timeRange) {
      return buffer.data.filter(item => {
        const timestamp = item.timestamp || buffer.timestamp;
        return timestamp >= timeRange.start && timestamp <= timeRange.end;
      });
    }
    
    return [...buffer.data];
  }

  getMetrics() {
    const now = Date.now();
    const connectionDuration = this.connectionState.status === 'connected' 
      ? now - this.metrics.connectionStartTime 
      : 0;
    
    return {
      connectionsCount: this.ws?.readyState === WebSocket.OPEN ? 1 : 0,
      subscriptionsCount: this.subscriptions.size,
      dataTransferRate: connectionDuration > 0 
        ? (this.metrics.bytesReceived + this.metrics.bytesSent) / (connectionDuration / 1000)
        : 0,
      latency: this.metrics.lastMessageTime > 0 
        ? now - this.metrics.lastMessageTime 
        : 0
    };
  }

  private sendMessage(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const data = JSON.stringify(message);
      this.ws.send(data);
      this.metrics.messagesSent++;
      this.metrics.bytesSent += data.length;
    }
  }

  private updateConnectionState(newState: Partial<ConnectionState>) {
    this.connectionState = { ...this.connectionState, ...newState };
    this.onStateChange(this.connectionState);
  }

  private cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  disconnect() {
    this.cleanup();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
    
    this.subscriptions.clear();
    this.callbacks.clear();
    this.buffers.clear();
    
    this.updateConnectionState({ status: 'disconnected' });
  }
}

// Provider component
interface RealTimeDataProviderProps {
  children: React.ReactNode;
  defaultConfig?: WebSocketConfig;
  autoConnect?: boolean;
}

export const RealTimeDataProvider: React.FC<RealTimeDataProviderProps> = ({
  children,
  defaultConfig,
  autoConnect = false
}) => {
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    status: 'disconnected',
    reconnectAttempts: 0
  });
  
  const wsManagerRef = useRef<WebSocketManager | null>(null);

  // Initialize WebSocket manager
  useEffect(() => {
    wsManagerRef.current = new WebSocketManager(setConnectionState);
    
    return () => {
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect();
      }
    };
  }, []);

  // Auto-connect if enabled
  useEffect(() => {
    if (autoConnect && defaultConfig && wsManagerRef.current) {
      wsManagerRef.current.connect(defaultConfig);
    }
  }, [autoConnect, defaultConfig]);

  const connect = useCallback(async (config: WebSocketConfig) => {
    if (wsManagerRef.current) {
      await wsManagerRef.current.connect(config);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsManagerRef.current) {
      wsManagerRef.current.disconnect();
    }
  }, []);

  const subscribe = useCallback((config: SubscriptionConfig, callback: (data: any) => void) => {
    if (wsManagerRef.current) {
      return wsManagerRef.current.subscribe(config, callback);
    }
    return '';
  }, []);

  const unsubscribe = useCallback((subscriptionId: string) => {
    if (wsManagerRef.current) {
      wsManagerRef.current.unsubscribe(subscriptionId);
    }
  }, []);

  const getLatestData = useCallback((channel: string) => {
    if (wsManagerRef.current) {
      return wsManagerRef.current.getLatestData(channel);
    }
    return null;
  }, []);

  const getHistoricalData = useCallback((channel: string, timeRange?: { start: number; end: number }) => {
    if (wsManagerRef.current) {
      return wsManagerRef.current.getHistoricalData(channel, timeRange);
    }
    return [];
  }, []);

  const getMetrics = useCallback(() => {
    if (wsManagerRef.current) {
      return wsManagerRef.current.getMetrics();
    }
    return {
      connectionsCount: 0,
      subscriptionsCount: 0,
      dataTransferRate: 0,
      latency: 0
    };
  }, []);

  const contextValue: RealTimeDataContextType = {
    connect,
    disconnect,
    connectionState,
    subscribe,
    unsubscribe,
    getLatestData,
    getHistoricalData,
    getMetrics
  };

  return (
    <RealTimeDataContext.Provider value={contextValue}>
      {children}
    </RealTimeDataContext.Provider>
  );
};

// Utility hooks for specific data types
export const useMemoryData = (transformations?: DataTransformation[]) => {
  const { subscribe, unsubscribe, getLatestData } = useRealTimeData();
  const [data, setData] = useState<any>(null);
  const subscriptionRef = useRef<string | null>(null);

  useEffect(() => {
    subscriptionRef.current = subscribe(
      {
        channel: 'memory_updates',
        dataType: 'memory',
        transformations,
        bufferSize: 50
      },
      setData
    );

    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
      }
    };
  }, [subscribe, unsubscribe, transformations]);

  return {
    data,
    latestData: getLatestData('memory_updates')
  };
};

export const useAnalyticsData = (transformations?: DataTransformation[]) => {
  const { subscribe, unsubscribe, getLatestData } = useRealTimeData();
  const [data, setData] = useState<any>(null);
  const subscriptionRef = useRef<string | null>(null);

  useEffect(() => {
    subscriptionRef.current = subscribe(
      {
        channel: 'analytics_updates',
        dataType: 'analytics',
        transformations,
        bufferSize: 100
      },
      setData
    );

    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
      }
    };
  }, [subscribe, unsubscribe, transformations]);

  return {
    data,
    latestData: getLatestData('analytics_updates')
  };
};

export const useMetricsData = (transformations?: DataTransformation[]) => {
  const { subscribe, unsubscribe, getLatestData } = useRealTimeData();
  const [data, setData] = useState<any>(null);
  const subscriptionRef = useRef<string | null>(null);

  useEffect(() => {
    subscriptionRef.current = subscribe(
      {
        channel: 'metrics_updates',
        dataType: 'metrics',
        transformations,
        bufferSize: 200
      },
      setData
    );

    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
      }
    };
  }, [subscribe, unsubscribe, transformations]);

  return {
    data,
    latestData: getLatestData('metrics_updates')
  };
};

export default RealTimeDataProvider; 