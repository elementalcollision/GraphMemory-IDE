import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { EChartsWrapper } from '../charts/EChartsWrapper';
import { useMetricsData, useRealTimeData } from '../core/RealTimeDataProvider';
import { withVisualizationBase } from '../core/VisualizationBase';

// Types for performance metrics
interface SystemMetric {
  id: string;
  name: string;
  value: number;
  unit: string;
  threshold: {
    warning: number;
    critical: number;
  };
  trend: number[];
  status: 'normal' | 'warning' | 'critical';
  category: 'cpu' | 'memory' | 'disk' | 'network' | 'application';
}

interface PerformanceAlert {
  id: string;
  metric: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
  acknowledged: boolean;
  details?: Record<string, any>;
}

interface ResourceUtilization {
  cpu: {
    current: number;
    average: number;
    cores: number[];
    processes: Array<{ name: string; usage: number; pid: number }>;
  };
  memory: {
    used: number;
    total: number;
    available: number;
    buffers: number;
    cached: number;
    swap: {
      used: number;
      total: number;
    };
  };
  disk: {
    drives: Array<{
      name: string;
      used: number;
      total: number;
      available: number;
      type: string;
    }>;
    io: {
      read: number;
      write: number;
    };
  };
  network: {
    interfaces: Array<{
      name: string;
      bytesIn: number;
      bytesOut: number;
      packetsIn: number;
      packetsOut: number;
      errors: number;
    }>;
    bandwidth: {
      upload: number;
      download: number;
    };
  };
}

interface ApplicationMetrics {
  responseTime: number;
  throughput: number;
  errorRate: number;
  activeConnections: number;
  queueSize: number;
  uptime: number;
  memoryLeaks: number;
  cachehitRate: number;
}

interface PerformanceMetricsData {
  metrics: SystemMetric[];
  alerts: PerformanceAlert[];
  resources: ResourceUtilization;
  application: ApplicationMetrics;
  timeline: Array<{
    timestamp: string;
    cpu: number;
    memory: number;
    disk: number;
    network: number;
    response_time: number;
  }>;
}

interface PerformanceMetricsWidgetProps {
  data?: PerformanceMetricsData;
  refreshInterval?: number;
  showResourceDetails?: boolean;
  showAlerts?: boolean;
  showTrendCharts?: boolean;
  alertThresholds?: Record<string, { warning: number; critical: number }>;
  onAlertClick?: (alert: PerformanceAlert) => void;
  onMetricDrillDown?: (metric: SystemMetric) => void;
  className?: string;
  style?: React.CSSProperties;
}

const PerformanceMetricsWidget: React.FC<PerformanceMetricsWidgetProps> = ({
  data: externalData,
  refreshInterval = 5000,
  showResourceDetails = true,
  showAlerts = true,
  showTrendCharts = true,
  alertThresholds,
  onAlertClick,
  onMetricDrillDown,
  className,
  style
}) => {
  const [activeView, setActiveView] = useState<'overview' | 'resources' | 'alerts' | 'trends'>('overview');
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Set<string>>(new Set());
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['cpu', 'memory']));

  // Real-time data integration
  const { data: realTimeMetrics } = useMetricsData([
    { type: 'filter', field: 'category', value: 'system' },
    { type: 'sort', field: 'timestamp', value: 'desc' }
  ]);

  // Generate mock performance data
  const performanceData = useMemo((): PerformanceMetricsData => {
    if (externalData) return externalData;

    return {
      metrics: [
        {
          id: 'cpu_usage',
          name: 'CPU Usage',
          value: 67.5,
          unit: '%',
          threshold: { warning: 70, critical: 90 },
          trend: Array.from({ length: 20 }, () => Math.random() * 100),
          status: 'normal',
          category: 'cpu'
        },
        {
          id: 'memory_usage',
          name: 'Memory Usage',
          value: 82.3,
          unit: '%',
          threshold: { warning: 80, critical: 95 },
          trend: Array.from({ length: 20 }, () => Math.random() * 100),
          status: 'warning',
          category: 'memory'
        },
        {
          id: 'disk_usage',
          name: 'Disk Usage',
          value: 45.8,
          unit: '%',
          threshold: { warning: 80, critical: 95 },
          trend: Array.from({ length: 20 }, () => Math.random() * 100),
          status: 'normal',
          category: 'disk'
        },
        {
          id: 'response_time',
          name: 'Response Time',
          value: 125,
          unit: 'ms',
          threshold: { warning: 200, critical: 500 },
          trend: Array.from({ length: 20 }, () => Math.random() * 300),
          status: 'normal',
          category: 'application'
        }
      ],
      alerts: [
        {
          id: 'alert_1',
          metric: 'memory_usage',
          severity: 'warning',
          message: 'Memory usage exceeds warning threshold (80%)',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          acknowledged: false,
          details: { current: 82.3, threshold: 80 }
        },
        {
          id: 'alert_2',
          metric: 'cpu_usage',
          severity: 'info',
          message: 'CPU usage spike detected',
          timestamp: new Date(Date.now() - 600000).toISOString(),
          acknowledged: true,
          details: { current: 95.2, duration: '2 minutes' }
        }
      ],
      resources: {
        cpu: {
          current: 67.5,
          average: 62.3,
          cores: [65, 72, 61, 69, 58, 74, 63, 71],
          processes: [
            { name: 'graphmemory-server', usage: 23.5, pid: 1234 },
            { name: 'postgres', usage: 12.8, pid: 5678 },
            { name: 'redis', usage: 8.3, pid: 9012 }
          ]
        },
        memory: {
          used: 13.2,
          total: 16.0,
          available: 2.8,
          buffers: 0.8,
          cached: 2.1,
          swap: { used: 0.5, total: 8.0 }
        },
        disk: {
          drives: [
            { name: '/', used: 120, total: 250, available: 130, type: 'SSD' },
            { name: '/data', used: 890, total: 2000, available: 1110, type: 'HDD' }
          ],
          io: { read: 45.2, write: 23.8 }
        },
        network: {
          interfaces: [
            { name: 'eth0', bytesIn: 1024000, bytesOut: 512000, packetsIn: 8500, packetsOut: 6200, errors: 0 }
          ],
          bandwidth: { upload: 50.3, download: 125.7 }
        }
      },
      application: {
        responseTime: 125,
        throughput: 1847,
        errorRate: 0.12,
        activeConnections: 453,
        queueSize: 23,
        uptime: 99.97,
        memoryLeaks: 0,
        cachehitRate: 94.2
      },
      timeline: Array.from({ length: 60 }, (_, i) => ({
        timestamp: new Date(Date.now() - (59 - i) * 60000).toISOString(),
        cpu: Math.random() * 100,
        memory: Math.random() * 100,
        disk: Math.random() * 100,
        network: Math.random() * 100,
        response_time: Math.random() * 300
      }))
    };
  }, [externalData, realTimeMetrics]);

  // Calculate status colors
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical': return '#ff4d4f';
      case 'warning': return '#faad14';
      case 'normal': return '#52c41a';
      default: return '#d9d9d9';
    }
  };

  // Handle alert acknowledgment
  const handleAlertAcknowledge = useCallback((alertId: string) => {
    setAcknowledgedAlerts(prev => new Set([...prev, alertId]));
    const alert = performanceData.alerts.find(a => a.id === alertId);
    if (alert && onAlertClick) {
      onAlertClick({ ...alert, acknowledged: true });
    }
  }, [performanceData.alerts, onAlertClick]);

  // Toggle category expansion
  const toggleCategory = useCallback((category: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  }, []);

  // Render gauge chart for metric
  const renderMetricGauge = useCallback((metric: SystemMetric) => {
    const gaugeData = {
      metrics: [{ 
        name: metric.name, 
        value: metric.value, 
        change: 0, 
        trend: 'stable' as const 
      }]
    };

    return (
      <div key={metric.id} style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontWeight: 'bold' }}>{metric.name}</span>
          <span style={{ 
            color: getStatusColor(metric.status),
            fontSize: 12,
            fontWeight: 'bold',
            textTransform: 'uppercase'
          }}>
            {metric.status}
          </span>
        </div>
        <EChartsWrapper
          data={gaugeData}
          type="gauge"
          height={200}
          options={{
            series: [{
              max: metric.category === 'application' && metric.unit === 'ms' ? 500 : 100,
              axisLine: {
                lineStyle: {
                  color: [
                    [metric.threshold.warning / 100, '#52c41a'],
                    [metric.threshold.critical / 100, '#faad14'],
                    [1, '#ff4d4f']
                  ]
                }
              }
            }]
          }}
          onChartClick={() => onMetricDrillDown?.(metric)}
        />
        <div style={{ textAlign: 'center', marginTop: 8 }}>
          <span style={{ fontSize: 18, fontWeight: 'bold' }}>
            {metric.value}{metric.unit}
          </span>
        </div>
      </div>
    );
  }, [onMetricDrillDown]);

  // Render resource utilization details
  const renderResourceDetails = () => (
    <div style={{ display: 'grid', gap: 24 }}>
      {/* CPU Details */}
      <div style={{ 
        padding: 16, 
        backgroundColor: '#fafafa', 
        borderRadius: 8,
        border: '1px solid #d9d9d9'
      }}>
        <div 
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            cursor: 'pointer',
            marginBottom: expandedCategories.has('cpu') ? 16 : 0
          }}
          onClick={() => toggleCategory('cpu')}
        >
          <h3>CPU Utilization</h3>
          <span>{expandedCategories.has('cpu') ? '▼' : '▶'}</span>
        </div>
        
        {expandedCategories.has('cpu') && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Current</div>
                <div style={{ fontSize: 20, fontWeight: 'bold' }}>{performanceData.resources.cpu.current}%</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Average</div>
                <div style={{ fontSize: 20, fontWeight: 'bold' }}>{performanceData.resources.cpu.average}%</div>
              </div>
            </div>
            
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 'bold', marginBottom: 8 }}>Per Core Usage</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                {performanceData.resources.cpu.cores.map((usage, index) => (
                  <div key={index} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 12, color: '#8c8c8c' }}>Core {index}</div>
                    <div style={{ 
                      fontSize: 14, 
                      fontWeight: 'bold',
                      color: usage > 80 ? '#ff4d4f' : usage > 60 ? '#faad14' : '#52c41a'
                    }}>
                      {usage}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <div style={{ fontSize: 14, fontWeight: 'bold', marginBottom: 8 }}>Top Processes</div>
              {performanceData.resources.cpu.processes.map(process => (
                <div key={process.pid} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  padding: '4px 0',
                  fontSize: 12
                }}>
                  <span>{process.name} (PID: {process.pid})</span>
                  <span style={{ fontWeight: 'bold' }}>{process.usage}%</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Memory Details */}
      <div style={{ 
        padding: 16, 
        backgroundColor: '#fafafa', 
        borderRadius: 8,
        border: '1px solid #d9d9d9'
      }}>
        <div 
          style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            cursor: 'pointer',
            marginBottom: expandedCategories.has('memory') ? 16 : 0
          }}
          onClick={() => toggleCategory('memory')}
        >
          <h3>Memory Usage</h3>
          <span>{expandedCategories.has('memory') ? '▼' : '▶'}</span>
        </div>
        
        {expandedCategories.has('memory') && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Used</div>
                <div style={{ fontSize: 16, fontWeight: 'bold' }}>
                  {performanceData.resources.memory.used} GB
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Available</div>
                <div style={{ fontSize: 16, fontWeight: 'bold' }}>
                  {performanceData.resources.memory.available} GB
                </div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>Total</div>
                <div style={{ fontSize: 16, fontWeight: 'bold' }}>
                  {performanceData.resources.memory.total} GB
                </div>
              </div>
            </div>

            <div style={{ 
              height: 20, 
              backgroundColor: '#f0f0f0', 
              borderRadius: 10, 
              overflow: 'hidden',
              marginBottom: 8
            }}>
              <div style={{
                height: '100%',
                width: `${(performanceData.resources.memory.used / performanceData.resources.memory.total) * 100}%`,
                backgroundColor: '#1890ff',
                transition: 'width 0.3s ease'
              }} />
            </div>
            
            <div style={{ fontSize: 12, color: '#8c8c8c', textAlign: 'center' }}>
              {((performanceData.resources.memory.used / performanceData.resources.memory.total) * 100).toFixed(1)}% Used
            </div>
          </div>
        )}
      </div>
    </div>
  );

  // Render alerts panel
  const renderAlerts = () => (
    <div style={{ display: 'grid', gap: 12 }}>
      <h3>Active Alerts</h3>
      {performanceData.alerts.map(alert => (
        <div
          key={alert.id}
          style={{
            padding: 16,
            backgroundColor: acknowledgedAlerts.has(alert.id) ? '#f6ffed' : '#fff7e6',
            border: `1px solid ${alert.severity === 'critical' ? '#ff4d4f' : alert.severity === 'warning' ? '#faad14' : '#52c41a'}`,
            borderRadius: 8,
            opacity: acknowledgedAlerts.has(alert.id) ? 0.7 : 1
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div>
              <span style={{
                backgroundColor: alert.severity === 'critical' ? '#ff4d4f' : alert.severity === 'warning' ? '#faad14' : '#52c41a',
                color: 'white',
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 'bold',
                textTransform: 'uppercase'
              }}>
                {alert.severity}
              </span>
              <span style={{ marginLeft: 8, fontSize: 12, color: '#8c8c8c' }}>
                {new Date(alert.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {!acknowledgedAlerts.has(alert.id) && (
              <button
                onClick={() => handleAlertAcknowledge(alert.id)}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  border: '1px solid #d9d9d9',
                  borderRadius: 4,
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
              >
                Acknowledge
              </button>
            )}
          </div>
          <div style={{ fontSize: 14, marginBottom: 4 }}>
            {alert.message}
          </div>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>
            Metric: {alert.metric}
          </div>
        </div>
      ))}
    </div>
  );

  // Render trend charts
  const renderTrendCharts = () => {
    const trendData = {
      timeSeries: performanceData.timeline.map(point => [
        { timestamp: point.timestamp, value: point.cpu, category: 'CPU' },
        { timestamp: point.timestamp, value: point.memory, category: 'Memory' },
        { timestamp: point.timestamp, value: point.response_time, category: 'Response Time' }
      ]).flat()
    };

    return (
      <div>
        <h3 style={{ marginBottom: 16 }}>Performance Trends ({selectedTimeRange})</h3>
        <div style={{ marginBottom: 16 }}>
          {['1h', '6h', '24h', '7d'].map(range => (
            <button
              key={range}
              onClick={() => setSelectedTimeRange(range as any)}
              style={{
                padding: '8px 16px',
                marginRight: 8,
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                backgroundColor: selectedTimeRange === range ? '#1890ff' : 'white',
                color: selectedTimeRange === range ? 'white' : '#262626',
                cursor: 'pointer',
                fontSize: 12
              }}
            >
              {range}
            </button>
          ))}
        </div>
        <EChartsWrapper
          data={trendData}
          type="line"
          height={400}
          title="System Performance Over Time"
          enableDataZoom={true}
          enableAnimation={true}
        />
      </div>
    );
  };

  return (
    <div className={`performance-metrics-widget ${className || ''}`} style={style}>
      {/* Tab Navigation */}
      <div style={{ display: 'flex', marginBottom: 24, borderBottom: '1px solid #d9d9d9' }}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'resources', label: 'Resources' },
          { key: 'alerts', label: `Alerts (${performanceData.alerts.filter(a => !acknowledgedAlerts.has(a.id)).length})` },
          { key: 'trends', label: 'Trends' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveView(tab.key as any)}
            style={{
              padding: '12px 16px',
              border: 'none',
              backgroundColor: 'transparent',
              borderBottom: `2px solid ${activeView === tab.key ? '#1890ff' : 'transparent'}`,
              color: activeView === tab.key ? '#1890ff' : '#8c8c8c',
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: activeView === tab.key ? 'bold' : 'normal'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeView === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 24 }}>
          {performanceData.metrics.map(renderMetricGauge)}
        </div>
      )}

      {activeView === 'resources' && showResourceDetails && renderResourceDetails()}

      {activeView === 'alerts' && showAlerts && renderAlerts()}

      {activeView === 'trends' && showTrendCharts && renderTrendCharts()}
    </div>
  );
};

export default withVisualizationBase(PerformanceMetricsWidget); 