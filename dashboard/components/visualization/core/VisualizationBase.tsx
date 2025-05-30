import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRealTimeData } from './RealTimeDataProvider';

// Base interfaces for all visualizations
export interface VisualizationTheme {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  shadow: string;
}

export interface VisualizationDimensions {
  width: number | string;
  height: number | string;
  margin?: {
    top?: number;
    right?: number;
    bottom?: number;
    left?: number;
  };
  padding?: {
    top?: number;
    right?: number;
    bottom?: number;
    left?: number;
  };
}

export interface ExportOptions {
  format: 'png' | 'svg' | 'pdf' | 'json' | 'csv';
  filename?: string;
  quality?: number;
  backgroundColor?: string;
  dimensions?: {
    width: number;
    height: number;
  };
}

export interface AccessibilityOptions {
  enableKeyboardNavigation?: boolean;
  enableScreenReader?: boolean;
  ariaLabel?: string;
  ariaDescription?: string;
  highContrast?: boolean;
  reduceMotion?: boolean;
}

export interface PerformanceOptions {
  enableVirtualization?: boolean;
  lazyLoading?: boolean;
  debounceInterval?: number;
  maxDataPoints?: number;
  enableCaching?: boolean;
  cacheTimeout?: number;
}

export interface InteractionHandlers {
  onClick?: (event: any, data?: any) => void;
  onHover?: (event: any, data?: any) => void;
  onDoubleClick?: (event: any, data?: any) => void;
  onContextMenu?: (event: any, data?: any) => void;
  onSelect?: (selectedItems: any[]) => void;
  onZoom?: (zoomLevel: number, center?: { x: number; y: number }) => void;
  onPan?: (delta: { x: number; y: number }) => void;
}

export interface VisualizationBaseProps {
  id?: string;
  className?: string;
  style?: React.CSSProperties;
  theme?: Partial<VisualizationTheme>;
  dimensions?: VisualizationDimensions;
  data?: any;
  loading?: boolean;
  error?: string | Error;
  title?: string;
  subtitle?: string;
  exportOptions?: ExportOptions;
  accessibility?: AccessibilityOptions;
  performance?: PerformanceOptions;
  interactions?: InteractionHandlers;
  enableRealTime?: boolean;
  realTimeChannel?: string;
  updateInterval?: number;
  customStyles?: Record<string, React.CSSProperties>;
}

// Default themes
export const LIGHT_THEME: VisualizationTheme = {
  primary: '#1890ff',
  secondary: '#722ed1',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  info: '#13c2c2',
  background: '#ffffff',
  surface: '#fafafa',
  text: '#262626',
  textSecondary: '#8c8c8c',
  border: '#d9d9d9',
  shadow: 'rgba(0, 0, 0, 0.1)'
};

export const DARK_THEME: VisualizationTheme = {
  primary: '#177ddc',
  secondary: '#642ab5',
  success: '#49aa19',
  warning: '#d46b08',
  error: '#dc4446',
  info: '#13a8a8',
  background: '#141414',
  surface: '#1f1f1f',
  text: '#ffffff',
  textSecondary: '#a6a6a6',
  border: '#434343',
  shadow: 'rgba(0, 0, 0, 0.3)'
};

// Utility functions
export const mergeTheme = (baseTheme: VisualizationTheme, customTheme?: Partial<VisualizationTheme>): VisualizationTheme => {
  return { ...baseTheme, ...customTheme };
};

export const generateUID = (prefix: string = 'viz'): string => {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const formatNumber = (value: number, precision: number = 2): string => {
  if (value >= 1e9) return `${(value / 1e9).toFixed(precision)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(precision)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(precision)}K`;
  return value.toFixed(precision);
};

export const debounce = <T extends (...args: any[]) => void>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void => {
  let timeoutId: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

// Base visualization hook
export const useVisualizationBase = (props: VisualizationBaseProps) => {
  const {
    id = generateUID(),
    theme: customTheme,
    dimensions = { width: '100%', height: 400 },
    loading = false,
    error,
    enableRealTime = false,
    realTimeChannel,
    updateInterval = 1000,
    accessibility = {},
    performance = {},
    interactions = {}
  } = props;

  // State management
  const [isInitialized, setIsInitialized] = useState(false);
  const [visualizationError, setVisualizationError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());
  
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Real-time data integration
  const realTimeData = enableRealTime ? useRealTimeData() : null;
  
  // Theme calculation
  const theme = useMemo(() => {
    const baseTheme = document.documentElement.classList.contains('dark') ? DARK_THEME : LIGHT_THEME;
    return mergeTheme(baseTheme, customTheme);
  }, [customTheme]);

  // Debounced resize handler
  const debouncedResize = useMemo(
    () => debounce(() => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        // Trigger resize event for child components
        window.dispatchEvent(new CustomEvent('visualization-resize', {
          detail: { id, width: rect.width, height: rect.height }
        }));
      }
    }, performance.debounceInterval || 250),
    [id, performance.debounceInterval]
  );

  // Initialize resize observer
  useEffect(() => {
    if (containerRef.current && window.ResizeObserver) {
      resizeObserverRef.current = new ResizeObserver(debouncedResize);
      resizeObserverRef.current.observe(containerRef.current);
      
      return () => {
        if (resizeObserverRef.current) {
          resizeObserverRef.current.disconnect();
        }
      };
    }
  }, [debouncedResize]);

  // Real-time data subscription
  useEffect(() => {
    if (enableRealTime && realTimeData && realTimeChannel) {
      const subscriptionId = realTimeData.subscribe(
        {
          channel: realTimeChannel,
          dataType: 'analytics',
          bufferSize: performance.maxDataPoints || 1000
        },
        (newData) => {
          setLastUpdate(Date.now());
          // Trigger data update event
          window.dispatchEvent(new CustomEvent('visualization-data-update', {
            detail: { id, data: newData }
          }));
        }
      );

      return () => {
        realTimeData.unsubscribe(subscriptionId);
      };
    }
  }, [enableRealTime, realTimeData, realTimeChannel, id, performance.maxDataPoints]);

  // Error handling
  useEffect(() => {
    if (error) {
      const errorMessage = error instanceof Error ? error.message : error;
      setVisualizationError(errorMessage);
    } else {
      setVisualizationError(null);
    }
  }, [error]);

  // Export functionality
  const exportVisualization = useCallback(async (options: ExportOptions) => {
    setIsExporting(true);
    
    try {
      if (!containerRef.current) {
        throw new Error('Visualization container not found');
      }

      const { format, filename = `visualization_${id}`, quality = 1, backgroundColor = theme.background } = options;
      
      switch (format) {
        case 'png':
        case 'svg':
          // Canvas/SVG export logic would go here
          await exportAsImage(containerRef.current, format, filename, quality, backgroundColor);
          break;
        case 'pdf':
          await exportAsPDF(containerRef.current, filename, backgroundColor);
          break;
        case 'json':
          await exportAsJSON(props.data, filename);
          break;
        case 'csv':
          await exportAsCSV(props.data, filename);
          break;
        default:
          throw new Error(`Unsupported export format: ${format}`);
      }
    } catch (exportError) {
      setVisualizationError(`Export failed: ${exportError}`);
    } finally {
      setIsExporting(false);
    }
  }, [id, theme.background, props.data]);

  // Accessibility helpers
  const getAccessibilityProps = useCallback(() => {
    const {
      enableKeyboardNavigation = true,
      enableScreenReader = true,
      ariaLabel,
      ariaDescription,
      highContrast = false
    } = accessibility;

    return {
      role: 'img',
      'aria-label': ariaLabel || `Visualization: ${props.title || 'Untitled'}`,
      'aria-description': ariaDescription,
      tabIndex: enableKeyboardNavigation ? 0 : -1,
      'data-high-contrast': highContrast,
      'aria-live': enableRealTime ? 'polite' : undefined
    };
  }, [accessibility, props.title, enableRealTime]);

  // Performance monitoring
  const performanceMetrics = useMemo(() => {
    return {
      lastUpdate,
      renderCount: 0, // Would be tracked by individual components
      dataPoints: Array.isArray(props.data) ? props.data.length : 0,
      memoryUsage: performance.memory ? performance.memory.usedJSHeapSize : 0
    };
  }, [lastUpdate, props.data]);

  return {
    // Core properties
    id,
    theme,
    dimensions,
    containerRef,
    
    // State
    isInitialized,
    setIsInitialized,
    loading,
    error: visualizationError,
    isExporting,
    lastUpdate,
    
    // Functions
    exportVisualization,
    getAccessibilityProps,
    
    // Metrics
    performanceMetrics,
    
    // Real-time
    realTimeData: enableRealTime ? realTimeData : null
  };
};

// Export helper functions (simplified implementations)
const exportAsImage = async (
  element: HTMLElement,
  format: 'png' | 'svg',
  filename: string,
  quality: number,
  backgroundColor: string
) => {
  // Implementation would use html2canvas or similar
  console.log(`Exporting as ${format}:`, { filename, quality, backgroundColor });
};

const exportAsPDF = async (element: HTMLElement, filename: string, backgroundColor: string) => {
  // Implementation would use jsPDF or similar
  console.log('Exporting as PDF:', { filename, backgroundColor });
};

const exportAsJSON = async (data: any, filename: string) => {
  const jsonData = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonData], { type: 'application/json' });
  downloadBlob(blob, `${filename}.json`);
};

const exportAsCSV = async (data: any, filename: string) => {
  let csvContent = '';
  
  if (Array.isArray(data) && data.length > 0) {
    // Get headers from first object
    const headers = Object.keys(data[0]);
    csvContent += headers.join(',') + '\n';
    
    // Add data rows
    data.forEach(row => {
      const values = headers.map(header => {
        const value = row[header];
        return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
      });
      csvContent += values.join(',') + '\n';
    });
  }
  
  const blob = new Blob([csvContent], { type: 'text/csv' });
  downloadBlob(blob, `${filename}.csv`);
};

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

// HOC for visualization components
export const withVisualizationBase = <P extends object>(
  WrappedComponent: React.ComponentType<P>
) => {
  return React.forwardRef<HTMLDivElement, P & VisualizationBaseProps>((props, ref) => {
    const baseProps = useVisualizationBase(props);
    
    return (
      <div
        ref={ref || baseProps.containerRef}
        id={baseProps.id}
        className={`visualization-container ${props.className || ''}`}
        style={{
          width: baseProps.dimensions.width,
          height: baseProps.dimensions.height,
          backgroundColor: baseProps.theme.background,
          color: baseProps.theme.text,
          border: `1px solid ${baseProps.theme.border}`,
          borderRadius: 8,
          position: 'relative',
          overflow: 'hidden',
          ...props.style
        }}
        {...baseProps.getAccessibilityProps()}
      >
        {/* Loading State */}
        {baseProps.loading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: `${baseProps.theme.background}cc`,
              zIndex: 1000
            }}
          >
            <div
              style={{
                padding: '20px',
                fontSize: '16px',
                fontWeight: 'bold',
                color: baseProps.theme.textSecondary
              }}
            >
              Loading visualization...
            </div>
          </div>
        )}

        {/* Error State */}
        {baseProps.error && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: baseProps.theme.background,
              zIndex: 1000
            }}
          >
            <div
              style={{
                padding: '20px',
                textAlign: 'center',
                color: baseProps.theme.error,
                border: `1px solid ${baseProps.theme.error}`,
                borderRadius: 8,
                backgroundColor: `${baseProps.theme.error}10`
              }}
            >
              <div style={{ fontSize: '18px', marginBottom: '8px' }}>⚠️ Error</div>
              <div style={{ fontSize: '14px' }}>{baseProps.error}</div>
            </div>
          </div>
        )}

        {/* Export Overlay */}
        {baseProps.isExporting && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: `${baseProps.theme.background}dd`,
              zIndex: 1001
            }}
          >
            <div
              style={{
                padding: '20px',
                fontSize: '16px',
                fontWeight: 'bold',
                color: baseProps.theme.primary
              }}
            >
              Exporting visualization...
            </div>
          </div>
        )}

        {/* Title */}
        {props.title && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 16,
              fontSize: '16px',
              fontWeight: 'bold',
              color: baseProps.theme.text,
              zIndex: 100
            }}
          >
            {props.title}
            {props.subtitle && (
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 'normal',
                  color: baseProps.theme.textSecondary,
                  marginTop: 2
                }}
              >
                {props.subtitle}
              </div>
            )}
          </div>
        )}

        {/* Real-time Indicator */}
        {props.enableRealTime && baseProps.realTimeData?.connectionState.status === 'connected' && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              right: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '12px',
              color: baseProps.theme.success,
              zIndex: 100
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: baseProps.theme.success,
                animation: 'pulse 2s infinite'
              }}
            />
            Live
          </div>
        )}

        {/* Main Component */}
        <WrappedComponent {...props} {...baseProps} />
      </div>
    );
  });
};

export default useVisualizationBase; 