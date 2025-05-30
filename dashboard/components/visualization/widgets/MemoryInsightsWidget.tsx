import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { EChartsWrapper } from '../charts/EChartsWrapper';
import { KnowledgeGraphVisualization } from '../graphs/KnowledgeGraphVisualization';
import { useMemoryData, useAnalyticsData } from '../core/RealTimeDataProvider';
import { withVisualizationBase } from '../core/VisualizationBase';

// Types for memory analytics
interface MemoryMetric {
  id: string;
  name: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  target?: number;
  unit: string;
  category: 'performance' | 'capacity' | 'quality' | 'growth';
}

interface MemoryPattern {
  id: string;
  type: 'temporal' | 'associative' | 'hierarchical' | 'semantic';
  strength: number;
  frequency: number;
  nodes: string[];
  description: string;
  confidence: number;
}

interface MemoryDistribution {
  episodic: number;
  semantic: number;
  procedural: number;
  total: number;
}

interface MemoryInsightsData {
  metrics: MemoryMetric[];
  patterns: MemoryPattern[];
  distribution: MemoryDistribution;
  timeline: Array<{
    timestamp: string;
    added: number;
    modified: number;
    accessed: number;
    connections: number;
  }>;
  topMemories: Array<{
    id: string;
    title: string;
    type: 'episodic' | 'semantic' | 'procedural';
    score: number;
    connections: number;
    recency: number;
  }>;
  networkStats: {
    nodes: number;
    edges: number;
    clusters: number;
    density: number;
    avgPath: number;
  };
}

interface MemoryInsightsWidgetProps {
  data?: MemoryInsightsData;
  timeRange?: 'hour' | 'day' | 'week' | 'month' | 'year';
  showDetailedMetrics?: boolean;
  showPatternAnalysis?: boolean;
  showNetworkGraph?: boolean;
  enableInteractiveFilters?: boolean;
  onMemorySelect?: (memoryId: string) => void;
  onPatternExplore?: (pattern: MemoryPattern) => void;
  className?: string;
  style?: React.CSSProperties;
}

const MemoryInsightsWidget: React.FC<MemoryInsightsWidgetProps> = ({
  data: externalData,
  timeRange = 'day',
  showDetailedMetrics = true,
  showPatternAnalysis = true,
  showNetworkGraph = true,
  enableInteractiveFilters = true,
  onMemorySelect,
  onPatternExplore,
  className,
  style
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'patterns' | 'network' | 'trends'>('overview');
  const [selectedMetricCategory, setSelectedMetricCategory] = useState<string>('all');
  const [selectedPattern, setSelectedPattern] = useState<MemoryPattern | null>(null);
  const [networkLayout, setNetworkLayout] = useState<'force' | 'circular' | 'hierarchical'>('force');

  // Real-time data hooks
  const { data: realTimeMemoryData } = useMemoryData([
    { type: 'aggregate', field: 'connections', operation: 'avg' },
    { type: 'sort', field: 'timestamp', value: 'desc' }
  ]);

  const { data: realTimeAnalyticsData } = useAnalyticsData([
    { type: 'filter', field: 'type', value: 'memory_analysis' }
  ]);

  // Combine external and real-time data
  const insightsData = useMemo(() => {
    if (externalData) return externalData;
    
    // Mock data structure for demonstration
    return {
      metrics: [
        {
          id: 'total_memories',
          name: 'Total Memories',
          value: 1247,
          change: 23,
          trend: 'up' as const,
          unit: 'count',
          category: 'capacity' as const
        },
        {
          id: 'avg_connections',
          name: 'Avg Connections',
          value: 4.2,
          change: 0.3,
          trend: 'up' as const,
          unit: 'connections',
          category: 'quality' as const
        },
        {
          id: 'recall_efficiency',
          name: 'Recall Efficiency',
          value: 87.5,
          change: -2.1,
          trend: 'down' as const,
          target: 90,
          unit: '%',
          category: 'performance' as const
        },
        {
          id: 'growth_rate',
          name: 'Growth Rate',
          value: 15.7,
          change: 4.2,
          trend: 'up' as const,
          unit: '%/week',
          category: 'growth' as const
        }
      ],
      patterns: [
        {
          id: 'pattern_1',
          type: 'temporal' as const,
          strength: 0.85,
          frequency: 12,
          nodes: ['memory_1', 'memory_5', 'memory_12'],
          description: 'Evening learning sessions show stronger retention',
          confidence: 0.92
        },
        {
          id: 'pattern_2',
          type: 'associative' as const,
          strength: 0.78,
          frequency: 8,
          nodes: ['memory_3', 'memory_7', 'memory_9', 'memory_15'],
          description: 'Programming concepts cluster with mathematical principles',
          confidence: 0.87
        }
      ],
      distribution: {
        episodic: 432,
        semantic: 578,
        procedural: 237,
        total: 1247
      },
      timeline: Array.from({ length: 24 }, (_, i) => ({
        timestamp: `${23 - i}:00`,
        added: Math.floor(Math.random() * 10),
        modified: Math.floor(Math.random() * 15),
        accessed: Math.floor(Math.random() * 50),
        connections: Math.floor(Math.random() * 20)
      })),
      topMemories: [
        {
          id: 'mem_1',
          title: 'Advanced React Patterns',
          type: 'procedural' as const,
          score: 92.5,
          connections: 15,
          recency: 2
        },
        {
          id: 'mem_2',
          title: 'Machine Learning Fundamentals',
          type: 'semantic' as const,
          score: 89.2,
          connections: 12,
          recency: 1
        }
      ],
      networkStats: {
        nodes: 1247,
        edges: 2891,
        clusters: 23,
        density: 0.34,
        avgPath: 3.2
      }
    } as MemoryInsightsData;
  }, [externalData, realTimeMemoryData, realTimeAnalyticsData]);

  // Filter metrics by category
  const filteredMetrics = useMemo(() => {
    if (selectedMetricCategory === 'all') return insightsData.metrics;
    return insightsData.metrics.filter(metric => metric.category === selectedMetricCategory);
  }, [insightsData.metrics, selectedMetricCategory]);

  // Generate chart data for distribution
  const distributionChartData = useMemo(() => ({
    categories: [
      { name: 'Episodic', value: insightsData.distribution.episodic, color: '#1890ff' },
      { name: 'Semantic', value: insightsData.distribution.semantic, color: '#52c41a' },
      { name: 'Procedural', value: insightsData.distribution.procedural, color: '#fa8c16' }
    ]
  }), [insightsData.distribution]);

  // Generate timeline chart data
  const timelineChartData = useMemo(() => ({
    timeSeries: insightsData.timeline.map(point => ([
      {
        timestamp: point.timestamp,
        value: point.added,
        category: 'Added'
      },
      {
        timestamp: point.timestamp,
        value: point.modified,
        category: 'Modified'
      },
      {
        timestamp: point.timestamp,
        value: point.accessed,
        category: 'Accessed'
      }
    ])).flat()
  }), [insightsData.timeline]);

  // Generate network data for graph
  const networkGraphData = useMemo(() => {
    // Mock network data - in real implementation, this would come from actual memory connections
    const nodes = insightsData.topMemories.map(memory => ({
      id: memory.id,
      type: memory.type,
      title: memory.title,
      content: `Score: ${memory.score}`,
      timestamp: new Date().toISOString(),
      tags: ['top-memory'],
      connections: memory.connections,
      importance: memory.score / 100,
      cluster: memory.type
    }));

    const edges = [
      { source: 'mem_1', target: 'mem_2', relationship: 'references' as const, strength: 0.8, timestamp: new Date().toISOString() }
    ];

    return { nodes, edges };
  }, [insightsData.topMemories]);

  // Event handlers
  const handleMetricClick = useCallback((params: any) => {
    console.log('Metric clicked:', params);
  }, []);

  const handlePatternSelect = useCallback((pattern: MemoryPattern) => {
    setSelectedPattern(pattern);
    if (onPatternExplore) {
      onPatternExplore(pattern);
    }
  }, [onPatternExplore]);

  const handleMemoryNodeClick = useCallback((memory: any) => {
    if (onMemorySelect) {
      onMemorySelect(memory.id);
    }
  }, [onMemorySelect]);

  // Render metric cards
  const renderMetricCards = () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
      {filteredMetrics.map(metric => (
        <div
          key={metric.id}
          style={{
            padding: 16,
            backgroundColor: '#fafafa',
            border: '1px solid #d9d9d9',
            borderRadius: 8,
            cursor: 'pointer'
          }}
          onClick={() => handleMetricClick(metric)}
        >
          <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>
            {metric.name}
          </div>
          <div style={{ fontSize: 24, fontWeight: 'bold', marginBottom: 8 }}>
            {metric.value}{metric.unit}
            {metric.target && (
              <span style={{ fontSize: 12, color: '#8c8c8c', marginLeft: 8 }}>
                / {metric.target}{metric.unit}
              </span>
            )}
          </div>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            fontSize: 12,
            color: metric.trend === 'up' ? '#52c41a' : metric.trend === 'down' ? '#ff4d4f' : '#8c8c8c'
          }}>
            {metric.trend === 'up' ? '↗' : metric.trend === 'down' ? '↘' : '→'}
            <span style={{ marginLeft: 4 }}>
              {Math.abs(metric.change)}{metric.unit} {timeRange}
            </span>
          </div>
        </div>
      ))}
    </div>
  );

  // Render pattern analysis
  const renderPatternAnalysis = () => (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ marginBottom: 16 }}>Detected Patterns</h3>
      <div style={{ display: 'grid', gap: 12 }}>
        {insightsData.patterns.map(pattern => (
          <div
            key={pattern.id}
            style={{
              padding: 16,
              backgroundColor: selectedPattern?.id === pattern.id ? '#e6f7ff' : '#fafafa',
              border: `1px solid ${selectedPattern?.id === pattern.id ? '#1890ff' : '#d9d9d9'}`,
              borderRadius: 8,
              cursor: 'pointer'
            }}
            onClick={() => handlePatternSelect(pattern)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div>
                <span style={{ 
                  backgroundColor: '#1890ff',
                  color: 'white',
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 'bold',
                  textTransform: 'uppercase'
                }}>
                  {pattern.type}
                </span>
                <span style={{ marginLeft: 8, fontSize: 12, color: '#8c8c8c' }}>
                  Strength: {(pattern.strength * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                {pattern.frequency} occurrences
              </div>
            </div>
            <div style={{ fontSize: 14, marginBottom: 8 }}>
              {pattern.description}
            </div>
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>
              Confidence: {(pattern.confidence * 100).toFixed(1)}% • {pattern.nodes.length} nodes involved
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // Render tab navigation
  const renderTabNavigation = () => (
    <div style={{ display: 'flex', marginBottom: 24, borderBottom: '1px solid #d9d9d9' }}>
      {[
        { key: 'overview', label: 'Overview' },
        { key: 'patterns', label: 'Patterns' },
        { key: 'network', label: 'Network' },
        { key: 'trends', label: 'Trends' }
      ].map(tab => (
        <button
          key={tab.key}
          onClick={() => setActiveTab(tab.key as any)}
          style={{
            padding: '12px 16px',
            border: 'none',
            backgroundColor: 'transparent',
            borderBottom: `2px solid ${activeTab === tab.key ? '#1890ff' : 'transparent'}`,
            color: activeTab === tab.key ? '#1890ff' : '#8c8c8c',
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: activeTab === tab.key ? 'bold' : 'normal'
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );

  return (
    <div className={`memory-insights-widget ${className || ''}`} style={style}>
      {renderTabNavigation()}

      {enableInteractiveFilters && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
          <select
            value={selectedMetricCategory}
            onChange={(e) => setSelectedMetricCategory(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              fontSize: 14
            }}
          >
            <option value="all">All Categories</option>
            <option value="performance">Performance</option>
            <option value="capacity">Capacity</option>
            <option value="quality">Quality</option>
            <option value="growth">Growth</option>
          </select>

          {showNetworkGraph && (
            <select
              value={networkLayout}
              onChange={(e) => setNetworkLayout(e.target.value as any)}
              style={{
                padding: '8px 12px',
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                fontSize: 14
              }}
            >
              <option value="force">Force Layout</option>
              <option value="circular">Circular Layout</option>
              <option value="hierarchical">Hierarchical Layout</option>
            </select>
          )}
        </div>
      )}

      {activeTab === 'overview' && (
        <div>
          {showDetailedMetrics && renderMetricCards()}
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
            <div>
              <h3 style={{ marginBottom: 16 }}>Memory Type Distribution</h3>
              <EChartsWrapper
                data={distributionChartData}
                type="pie"
                height={300}
                title="Memory Types"
                enableAnimation={true}
                onChartClick={handleMetricClick}
              />
            </div>
            
            <div>
              <h3 style={{ marginBottom: 16 }}>Network Statistics</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {Object.entries(insightsData.networkStats).map(([key, value]) => (
                  <div key={key} style={{ padding: 12, backgroundColor: '#fafafa', borderRadius: 6 }}>
                    <div style={{ fontSize: 12, color: '#8c8c8c', textTransform: 'capitalize' }}>
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 'bold' }}>
                      {typeof value === 'number' ? value.toLocaleString() : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'patterns' && showPatternAnalysis && (
        <div>
          {renderPatternAnalysis()}
        </div>
      )}

      {activeTab === 'network' && showNetworkGraph && (
        <div>
          <h3 style={{ marginBottom: 16 }}>Memory Network Graph</h3>
          <KnowledgeGraphVisualization
            data={networkGraphData}
            layout={networkLayout}
            enableSearch={true}
            enableMiniMap={true}
            enableTooltip={true}
            enableContextMenu={true}
            onNodeClick={handleMemoryNodeClick}
            width="100%"
            height={500}
          />
        </div>
      )}

      {activeTab === 'trends' && (
        <div>
          <h3 style={{ marginBottom: 16 }}>Memory Activity Timeline</h3>
          <EChartsWrapper
            data={timelineChartData}
            type="line"
            height={400}
            title="Activity Over Time"
            enableDataZoom={true}
            enableAnimation={true}
            onChartClick={handleMetricClick}
          />
        </div>
      )}
    </div>
  );
};

export default withVisualizationBase(MemoryInsightsWidget); 