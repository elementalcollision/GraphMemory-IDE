// Core visualization infrastructure
export { default as RealTimeDataProvider, useRealTimeData, useMemoryData, useAnalyticsData, useMetricsData } from './core/RealTimeDataProvider';
export { default as VisualizationBase, withVisualizationBase, useVisualizationBase, LIGHT_THEME, DARK_THEME } from './core/VisualizationBase';

// Chart components
export { default as EChartsWrapper } from './charts/EChartsWrapper';

// Graph components  
export { default as KnowledgeGraphVisualization } from './graphs/KnowledgeGraphVisualization';

// Widget components
export { default as MemoryInsightsWidget } from './widgets/MemoryInsightsWidget';
export { default as PerformanceMetricsWidget } from './widgets/PerformanceMetricsWidget';

// Dashboard components
export { default as CompositeDashboard } from './dashboard/CompositeDashboard';

// Type exports for external consumption
export type {
  // Core types
  VisualizationTheme,
  VisualizationDimensions,
  ExportOptions,
  AccessibilityOptions,
  PerformanceOptions,
  InteractionHandlers,
  VisualizationBaseProps
} from './core/VisualizationBase';

export type {
  WebSocketConfig,
  DataTransformation,
  SubscriptionConfig
} from './core/RealTimeDataProvider';

// Chart types
export type {
  ChartData,
  TimeSeriesDataPoint,
  MetricData,
  CategoryData
} from './charts/EChartsWrapper';

// Graph types
export type {
  MemoryNode,
  MemoryEdge,
  KnowledgeGraphData
} from './graphs/KnowledgeGraphVisualization';

// Widget types
export type {
  MemoryMetric,
  MemoryPattern,
  MemoryDistribution,
  MemoryInsightsData
} from './widgets/MemoryInsightsWidget';

export type {
  SystemMetric,
  PerformanceAlert,
  ResourceUtilization,
  ApplicationMetrics,
  PerformanceMetricsData
} from './widgets/PerformanceMetricsWidget';

// Dashboard types
export type {
  WidgetConfig,
  DashboardLayout,
  GlobalFilter,
  CompositeDashboardProps
} from './dashboard/CompositeDashboard';

// Utility functions and constants
export const VISUALIZATION_CONSTANTS = {
  GRID_COLUMNS: 12,
  GRID_ROW_HEIGHT: 60,
  DEFAULT_REFRESH_INTERVAL: 30000,
  WEBSOCKET_RECONNECT_INTERVAL: 5000,
  MAX_DATA_POINTS: 1000
};

// Helper functions for common visualization tasks
export const visualizationUtils = {
  formatNumber: (value: number, precision: number = 2): string => {
    if (value >= 1e9) return `${(value / 1e9).toFixed(precision)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(precision)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(precision)}K`;
    return value.toFixed(precision);
  },
  
  generateUID: (prefix: string = 'viz'): string => {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  },
  
  debounce: <T extends (...args: any[]) => void>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => void => {
    let timeoutId: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  },
  
  calculateTrend: (data: number[]): 'up' | 'down' | 'stable' => {
    if (data.length < 2) return 'stable';
    const recent = data.slice(-3);
    const earlier = data.slice(-6, -3);
    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const earlierAvg = earlier.reduce((a, b) => a + b, 0) / earlier.length;
    
    if (recentAvg > earlierAvg * 1.05) return 'up';
    if (recentAvg < earlierAvg * 0.95) return 'down';
    return 'stable';
  },
  
  interpolateColor: (color1: string, color2: string, factor: number): string => {
    if (factor <= 0) return color1;
    if (factor >= 1) return color2;
    
    const hex = (c: string) => parseInt(c.slice(1), 16);
    const c1 = hex(color1);
    const c2 = hex(color2);
    
    const r1 = (c1 >> 16) & 255;
    const g1 = (c1 >> 8) & 255;
    const b1 = c1 & 255;
    
    const r2 = (c2 >> 16) & 255;
    const g2 = (c2 >> 8) & 255;
    const b2 = c2 & 255;
    
    const r = Math.round(r1 + factor * (r2 - r1));
    const g = Math.round(g1 + factor * (g2 - g1));
    const b = Math.round(b1 + factor * (b2 - b1));
    
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
  }
};

// Pre-configured dashboard layouts
export const DASHBOARD_PRESETS = {
  SYSTEM_OVERVIEW: {
    id: 'system-overview',
    name: 'System Overview',
    description: 'Essential metrics and performance indicators',
    widgets: [
      { type: 'performance-metrics', position: { x: 0, y: 0, width: 6, height: 4 } },
      { type: 'memory-insights', position: { x: 6, y: 0, width: 6, height: 4 } }
    ]
  },
  
  MEMORY_ANALYSIS: {
    id: 'memory-analysis',
    name: 'Memory Deep Dive',
    description: 'Comprehensive memory pattern analysis',
    widgets: [
      { type: 'memory-insights', position: { x: 0, y: 0, width: 8, height: 6 } },
      { type: 'knowledge-graph', position: { x: 8, y: 0, width: 4, height: 6 } },
      { type: 'custom-chart', position: { x: 0, y: 6, width: 12, height: 4 } }
    ]
  },
  
  PERFORMANCE_MONITORING: {
    id: 'performance-monitoring',
    name: 'Performance Monitor',
    description: 'Real-time system performance tracking',
    widgets: [
      { type: 'performance-metrics', position: { x: 0, y: 0, width: 12, height: 8 } }
    ]
  }
};

// Export version information
export const VERSION = {
  major: 1,
  minor: 0,
  patch: 0,
  build: Date.now(),
  toString: () => `1.0.0-${Date.now()}`
}; 