import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { RealTimeDataProvider, useRealTimeData } from '../core/RealTimeDataProvider';
import { withVisualizationBase } from '../core/VisualizationBase';
import MemoryInsightsWidget from '../widgets/MemoryInsightsWidget';
import PerformanceMetricsWidget from '../widgets/PerformanceMetricsWidget';
import { KnowledgeGraphVisualization } from '../graphs/KnowledgeGraphVisualization';
import { EChartsWrapper } from '../charts/EChartsWrapper';

// Types for dashboard configuration
interface WidgetConfig {
  id: string;
  type: 'memory-insights' | 'performance-metrics' | 'knowledge-graph' | 'custom-chart' | 'metric-card';
  title: string;
  position: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  props?: Record<string, any>;
  minimized?: boolean;
  visible?: boolean;
  refreshInterval?: number;
  dependencies?: string[];
}

interface DashboardLayout {
  id: string;
  name: string;
  description: string;
  widgets: WidgetConfig[];
  globalFilters?: Record<string, any>;
  theme?: 'light' | 'dark';
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface GlobalFilter {
  id: string;
  type: 'timeRange' | 'category' | 'status' | 'custom';
  label: string;
  value: any;
  options?: Array<{ label: string; value: any }>;
  affectedWidgets?: string[];
}

interface DashboardContextType {
  selectedFilters: Record<string, any>;
  activeTimeRange: string;
  refreshTrigger: number;
  isFullscreen: boolean;
  editMode: boolean;
}

interface CompositeDashboardProps {
  layout?: DashboardLayout;
  predefinedLayouts?: DashboardLayout[];
  enableEditMode?: boolean;
  enableFullscreen?: boolean;
  enableExport?: boolean;
  enableSharing?: boolean;
  globalFilters?: GlobalFilter[];
  onLayoutChange?: (layout: DashboardLayout) => void;
  onWidgetInteraction?: (widgetId: string, interaction: string, data?: any) => void;
  onExport?: (format: string, options?: any) => void;
  className?: string;
  style?: React.CSSProperties;
}

// Default dashboard layouts
const DEFAULT_LAYOUTS: DashboardLayout[] = [
  {
    id: 'overview',
    name: 'System Overview',
    description: 'High-level view of memory and performance metrics',
    theme: 'light',
    autoRefresh: true,
    refreshInterval: 30000,
    widgets: [
      {
        id: 'memory-insights-main',
        type: 'memory-insights',
        title: 'Memory Insights',
        position: { x: 0, y: 0, width: 8, height: 6 },
        props: { showDetailedMetrics: true, enableInteractiveFilters: true }
      },
      {
        id: 'performance-overview',
        type: 'performance-metrics',
        title: 'Performance Overview',
        position: { x: 8, y: 0, width: 4, height: 6 },
        props: { showResourceDetails: false, showAlerts: true }
      },
      {
        id: 'knowledge-graph-summary',
        type: 'knowledge-graph',
        title: 'Knowledge Network',
        position: { x: 0, y: 6, width: 12, height: 6 },
        props: { layout: 'force', enableMiniMap: true }
      }
    ]
  },
  {
    id: 'detailed',
    name: 'Detailed Analysis',
    description: 'In-depth analysis with full widget features',
    theme: 'light',
    autoRefresh: true,
    refreshInterval: 10000,
    widgets: [
      {
        id: 'memory-insights-detailed',
        type: 'memory-insights',
        title: 'Memory Analysis',
        position: { x: 0, y: 0, width: 6, height: 8 },
        props: { 
          showDetailedMetrics: true, 
          showPatternAnalysis: true, 
          showNetworkGraph: true,
          enableInteractiveFilters: true 
        }
      },
      {
        id: 'performance-detailed',
        type: 'performance-metrics',
        title: 'System Performance',
        position: { x: 6, y: 0, width: 6, height: 8 },
        props: { 
          showResourceDetails: true, 
          showAlerts: true, 
          showTrendCharts: true 
        }
      },
      {
        id: 'network-analysis',
        type: 'knowledge-graph',
        title: 'Network Analysis',
        position: { x: 0, y: 8, width: 12, height: 6 },
        props: { 
          layout: 'force', 
          enableSearch: true, 
          enableContextMenu: true,
          enableClustering: true 
        }
      }
    ]
  }
];

// Grid system for layout management
const GRID_COLUMNS = 12;
const GRID_ROW_HEIGHT = 60;

const CompositeDashboard: React.FC<CompositeDashboardProps> = ({
  layout: externalLayout,
  predefinedLayouts = DEFAULT_LAYOUTS,
  enableEditMode = true,
  enableFullscreen = true,
  enableExport = true,
  enableSharing = false,
  globalFilters = [],
  onLayoutChange,
  onWidgetInteraction,
  onExport,
  className,
  style
}) => {
  // State management
  const [currentLayout, setCurrentLayout] = useState<DashboardLayout>(
    externalLayout || predefinedLayouts[0]
  );
  const [selectedFilters, setSelectedFilters] = useState<Record<string, any>>({});
  const [activeTimeRange, setActiveTimeRange] = useState('24h');
  const [isEditMode, setIsEditMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [draggedWidget, setDraggedWidget] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [minimizedWidgets, setMinimizedWidgets] = useState<Set<string>>(new Set());

  // Refs
  const dashboardRef = useRef<HTMLDivElement>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Real-time data integration
  const realTimeData = useRealTimeData();

  // Auto-refresh mechanism
  useEffect(() => {
    if (currentLayout.autoRefresh && currentLayout.refreshInterval) {
      refreshIntervalRef.current = setInterval(() => {
        setRefreshTrigger(prev => prev + 1);
      }, currentLayout.refreshInterval);

      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [currentLayout.autoRefresh, currentLayout.refreshInterval]);

  // Handle layout changes
  const handleLayoutChange = useCallback((newLayout: DashboardLayout) => {
    setCurrentLayout(newLayout);
    if (onLayoutChange) {
      onLayoutChange(newLayout);
    }
  }, [onLayoutChange]);

  // Handle widget position updates
  const handleWidgetMove = useCallback((widgetId: string, newPosition: WidgetConfig['position']) => {
    const updatedLayout = {
      ...currentLayout,
      widgets: currentLayout.widgets.map(widget =>
        widget.id === widgetId ? { ...widget, position: newPosition } : widget
      )
    };
    handleLayoutChange(updatedLayout);
  }, [currentLayout, handleLayoutChange]);

  // Handle widget resize
  const handleWidgetResize = useCallback((widgetId: string, newSize: { width: number; height: number }) => {
    const widget = currentLayout.widgets.find(w => w.id === widgetId);
    if (widget) {
      handleWidgetMove(widgetId, { ...widget.position, ...newSize });
    }
  }, [currentLayout.widgets, handleWidgetMove]);

  // Handle widget minimize/maximize
  const handleWidgetMinimize = useCallback((widgetId: string) => {
    setMinimizedWidgets(prev => {
      const newSet = new Set(prev);
      if (newSet.has(widgetId)) {
        newSet.delete(widgetId);
      } else {
        newSet.add(widgetId);
      }
      return newSet;
    });
  }, []);

  // Handle global filter changes
  const handleFilterChange = useCallback((filterId: string, value: any) => {
    setSelectedFilters(prev => ({ ...prev, [filterId]: value }));
  }, []);

  // Export functionality
  const handleExport = useCallback(async (format: 'png' | 'pdf' | 'json') => {
    if (onExport) {
      onExport(format, {
        layout: currentLayout,
        filters: selectedFilters,
        timestamp: new Date().toISOString()
      });
    }
  }, [currentLayout, selectedFilters, onExport]);

  // Render widget based on type
  const renderWidget = useCallback((widget: WidgetConfig) => {
    const isMinimized = minimizedWidgets.has(widget.id);
    const widgetStyle: React.CSSProperties = {
      position: 'absolute',
      left: `${(widget.position.x / GRID_COLUMNS) * 100}%`,
      top: `${widget.position.y * GRID_ROW_HEIGHT}px`,
      width: `${(widget.position.width / GRID_COLUMNS) * 100}%`,
      height: isMinimized ? '40px' : `${widget.position.height * GRID_ROW_HEIGHT}px`,
      backgroundColor: currentLayout.theme === 'dark' ? '#1f1f1f' : '#ffffff',
      border: `1px solid ${currentLayout.theme === 'dark' ? '#434343' : '#d9d9d9'}`,
      borderRadius: 8,
      overflow: 'hidden',
      transition: 'all 0.3s ease',
      zIndex: draggedWidget === widget.id ? 1000 : 1
    };

    const commonProps = {
      key: widget.id,
      className: 'dashboard-widget',
      style: widgetStyle,
      ...widget.props,
      // Apply global filters
      timeRange: selectedFilters.timeRange || activeTimeRange,
      // Real-time data integration
      enableRealTime: currentLayout.autoRefresh,
      // Event handlers
      onInteraction: (interaction: string, data?: any) => {
        if (onWidgetInteraction) {
          onWidgetInteraction(widget.id, interaction, data);
        }
      }
    };

    // Widget header
    const renderWidgetHeader = () => (
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 12px',
        backgroundColor: currentLayout.theme === 'dark' ? '#2a2a2a' : '#f5f5f5',
        borderBottom: `1px solid ${currentLayout.theme === 'dark' ? '#434343' : '#d9d9d9'}`,
        fontSize: 14,
        fontWeight: 'bold'
      }}>
        <span>{widget.title}</span>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => handleWidgetMinimize(widget.id)}
            style={{
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              fontSize: 12,
              padding: '2px 6px'
            }}
          >
            {isMinimized ? '□' : '−'}
          </button>
          {isEditMode && (
            <button
              style={{
                border: 'none',
                backgroundColor: 'transparent',
                cursor: 'move',
                fontSize: 12,
                padding: '2px 6px'
              }}
              onMouseDown={() => setDraggedWidget(widget.id)}
              onMouseUp={() => setDraggedWidget(null)}
            >
              ⋮⋮
            </button>
          )}
        </div>
      </div>
    );

    const widgetContent = (
      <div style={{ position: 'relative', height: '100%' }}>
        {renderWidgetHeader()}
        {!isMinimized && (
          <div style={{ height: 'calc(100% - 41px)', overflow: 'auto' }}>
            {(() => {
              switch (widget.type) {
                case 'memory-insights':
                  return <MemoryInsightsWidget {...commonProps} />;
                case 'performance-metrics':
                  return <PerformanceMetricsWidget {...commonProps} />;
                case 'knowledge-graph':
                  return (
                    <KnowledgeGraphVisualization
                      data={{ nodes: [], edges: [] }} // Would be populated from real data
                      width="100%"
                      height="100%"
                      {...commonProps}
                    />
                  );
                case 'custom-chart':
                  return (
                    <EChartsWrapper
                      data={{ categories: [] }}
                      type="line"
                      width="100%"
                      height="100%"
                      {...commonProps}
                    />
                  );
                default:
                  return (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '100%',
                      color: '#8c8c8c'
                    }}>
                      Unknown widget type: {widget.type}
                    </div>
                  );
              }
            })()}
          </div>
        )}
      </div>
    );

    return widgetContent;
  }, [
    minimizedWidgets, 
    currentLayout.theme, 
    draggedWidget, 
    selectedFilters, 
    activeTimeRange, 
    isEditMode,
    onWidgetInteraction,
    handleWidgetMinimize
  ]);

  // Calculate dashboard height
  const dashboardHeight = useMemo(() => {
    const maxY = Math.max(...currentLayout.widgets.map(w => w.position.y + w.position.height));
    return Math.max(600, maxY * GRID_ROW_HEIGHT + 40);
  }, [currentLayout.widgets]);

  return (
    <RealTimeDataProvider autoConnect={currentLayout.autoRefresh}>
      <div 
        ref={dashboardRef}
        className={`composite-dashboard ${className || ''}`}
        style={{
          position: 'relative',
          width: '100%',
          minHeight: dashboardHeight,
          backgroundColor: currentLayout.theme === 'dark' ? '#141414' : '#fafafa',
          ...style
        }}
      >
        {/* Dashboard Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 24px',
          backgroundColor: currentLayout.theme === 'dark' ? '#1f1f1f' : '#ffffff',
          borderBottom: `1px solid ${currentLayout.theme === 'dark' ? '#434343' : '#d9d9d9'}`,
          marginBottom: 16
        }}>
          <div>
            <h2 style={{ margin: 0, marginBottom: 4 }}>{currentLayout.name}</h2>
            <p style={{ margin: 0, color: '#8c8c8c', fontSize: 14 }}>
              {currentLayout.description}
            </p>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {/* Layout Selector */}
            <select
              value={currentLayout.id}
              onChange={(e) => {
                const layout = predefinedLayouts.find(l => l.id === e.target.value);
                if (layout) handleLayoutChange(layout);
              }}
              style={{
                padding: '8px 12px',
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                fontSize: 14
              }}
            >
              {predefinedLayouts.map(layout => (
                <option key={layout.id} value={layout.id}>
                  {layout.name}
                </option>
              ))}
            </select>

            {/* Time Range Filter */}
            <select
              value={activeTimeRange}
              onChange={(e) => setActiveTimeRange(e.target.value)}
              style={{
                padding: '8px 12px',
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                fontSize: 14
              }}
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>

            {/* Control Buttons */}
            <div style={{ display: 'flex', gap: 8 }}>
              {enableEditMode && (
                <button
                  onClick={() => setIsEditMode(!isEditMode)}
                  style={{
                    padding: '8px 12px',
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    backgroundColor: isEditMode ? '#1890ff' : 'white',
                    color: isEditMode ? 'white' : '#262626',
                    cursor: 'pointer',
                    fontSize: 14
                  }}
                >
                  {isEditMode ? 'Exit Edit' : 'Edit'}
                </button>
              )}

              {enableFullscreen && (
                <button
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  style={{
                    padding: '8px 12px',
                    border: '1px solid #d9d9d9',
                    borderRadius: 6,
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    fontSize: 14
                  }}
                >
                  {isFullscreen ? 'Exit FS' : 'Fullscreen'}
                </button>
              )}

              <button
                onClick={() => setRefreshTrigger(prev => prev + 1)}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #d9d9d9',
                  borderRadius: 6,
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  fontSize: 14
                }}
              >
                Refresh
              </button>

              {enableExport && (
                <div style={{ position: 'relative' }}>
                  <button
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #d9d9d9',
                      borderRadius: 6,
                      backgroundColor: 'white',
                      cursor: 'pointer',
                      fontSize: 14
                    }}
                  >
                    Export ▼
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Global Filters */}
        {globalFilters.length > 0 && (
          <div style={{
            padding: '12px 24px',
            backgroundColor: currentLayout.theme === 'dark' ? '#1f1f1f' : '#ffffff',
            borderBottom: `1px solid ${currentLayout.theme === 'dark' ? '#434343' : '#d9d9d9'}`,
            marginBottom: 16
          }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <span style={{ fontSize: 14, fontWeight: 'bold' }}>Filters:</span>
              {globalFilters.map(filter => (
                <div key={filter.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ fontSize: 14 }}>{filter.label}:</label>
                  <select
                    value={selectedFilters[filter.id] || filter.value}
                    onChange={(e) => handleFilterChange(filter.id, e.target.value)}
                    style={{
                      padding: '4px 8px',
                      border: '1px solid #d9d9d9',
                      borderRadius: 4,
                      fontSize: 13
                    }}
                  >
                    {filter.options?.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dashboard Grid */}
        <div style={{
          position: 'relative',
          padding: '0 24px',
          minHeight: dashboardHeight - 140
        }}>
          {/* Grid Background (visible in edit mode) */}
          {isEditMode && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage: `
                linear-gradient(to right, #f0f0f0 1px, transparent 1px),
                linear-gradient(to bottom, #f0f0f0 1px, transparent 1px)
              `,
              backgroundSize: `${100 / GRID_COLUMNS}% ${GRID_ROW_HEIGHT}px`,
              pointerEvents: 'none',
              opacity: 0.5
            }} />
          )}

          {/* Widgets */}
          {currentLayout.widgets.map(renderWidget)}
        </div>

        {/* Status Bar */}
        <div style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '8px 24px',
          backgroundColor: currentLayout.theme === 'dark' ? '#1f1f1f' : '#ffffff',
          borderTop: `1px solid ${currentLayout.theme === 'dark' ? '#434343' : '#d9d9d9'}`,
          fontSize: 12,
          color: '#8c8c8c',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            {currentLayout.widgets.length} widgets • {currentLayout.widgets.filter(w => !minimizedWidgets.has(w.id)).length} active
          </div>
          <div>
            Last updated: {new Date().toLocaleTimeString()} • 
            {realTimeData?.connectionState.status === 'connected' && (
              <span style={{ color: '#52c41a', marginLeft: 8 }}>
                🟢 Live
              </span>
            )}
          </div>
        </div>
      </div>
    </RealTimeDataProvider>
  );
};

export default withVisualizationBase(CompositeDashboard); 