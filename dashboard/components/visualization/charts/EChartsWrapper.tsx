import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import * as echarts from 'echarts';
import { EChartsOption, ECharts } from 'echarts';

// Types for GraphMemory-IDE analytics data
interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  category?: string;
  metadata?: Record<string, any>;
}

interface MetricData {
  name: string;
  value: number;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
}

interface CategoryData {
  name: string;
  value: number;
  percentage?: number;
  color?: string;
  children?: CategoryData[];
}

interface ChartData {
  timeSeries?: TimeSeriesDataPoint[];
  metrics?: MetricData[];
  categories?: CategoryData[];
  heatmap?: Array<[number, number, number]>;
  network?: {
    nodes: Array<{ id: string; name: string; value: number; category?: number }>;
    links: Array<{ source: string; target: string; value?: number }>;
    categories?: Array<{ name: string; color?: string }>;
  };
}

type ChartType = 
  | 'line' | 'bar' | 'pie' | 'scatter' | 'heatmap' | 'gauge' 
  | 'funnel' | 'treemap' | 'sunburst' | 'graph' | 'sankey'
  | 'parallel' | 'radar' | 'candlestick' | 'boxplot';

interface EChartsWrapperProps {
  data: ChartData;
  type: ChartType;
  title?: string;
  subtitle?: string;
  theme?: 'light' | 'dark' | 'custom';
  width?: number | string;
  height?: number | string;
  options?: EChartsOption;
  enableDataZoom?: boolean;
  enableBrush?: boolean;
  enableAnimation?: boolean;
  enableRealTime?: boolean;
  updateInterval?: number;
  onChartClick?: (params: any) => void;
  onDataUpdate?: (data: ChartData) => void;
  className?: string;
  style?: React.CSSProperties;
  loading?: boolean;
  error?: string;
}

// Custom themes for GraphMemory-IDE
const CHART_THEMES = {
  light: {
    backgroundColor: '#ffffff',
    textColor: '#333333',
    lineColor: '#cccccc',
    primaryColor: '#1890ff',
    successColor: '#52c41a',
    warningColor: '#faad14',
    errorColor: '#ff4d4f',
    gradientColors: ['#667eea', '#764ba2', '#f093fb', '#f5576c']
  },
  dark: {
    backgroundColor: '#1e1e1e',
    textColor: '#ffffff',
    lineColor: '#404040',
    primaryColor: '#177ddc',
    successColor: '#49aa19',
    warningColor: '#d46b08',
    errorColor: '#dc4446',
    gradientColors: ['#4facfe', '#00f2fe', '#43e97b', '#38f9d7']
  }
};

// Chart configuration generators
const generateChartOption = (
  type: ChartType,
  data: ChartData,
  theme: 'light' | 'dark',
  props: EChartsWrapperProps
): EChartsOption => {
  const colors = CHART_THEMES[theme];
  
  const baseOption: EChartsOption = {
    backgroundColor: colors.backgroundColor,
    title: {
      text: props.title,
      subtext: props.subtitle,
      textStyle: {
        color: colors.textColor,
        fontSize: 18,
        fontWeight: 'bold'
      },
      subtextStyle: {
        color: colors.textColor,
        fontSize: 12
      },
      left: 'center',
      top: 20
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: colors.backgroundColor,
      borderColor: colors.lineColor,
      textStyle: {
        color: colors.textColor
      },
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.1);'
    },
    legend: {
      textStyle: {
        color: colors.textColor
      },
      top: 60
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '10%',
      top: props.title ? 100 : 60,
      containLabel: true
    },
    color: colors.gradientColors,
    animation: props.enableAnimation !== false,
    animationDuration: 1000,
    animationEasing: 'cubicOut'
  };

  switch (type) {
    case 'line':
      return generateLineChartOption(data, colors, baseOption, props);
    case 'bar':
      return generateBarChartOption(data, colors, baseOption, props);
    case 'pie':
      return generatePieChartOption(data, colors, baseOption, props);
    case 'scatter':
      return generateScatterChartOption(data, colors, baseOption, props);
    case 'heatmap':
      return generateHeatmapChartOption(data, colors, baseOption, props);
    case 'gauge':
      return generateGaugeChartOption(data, colors, baseOption, props);
    case 'treemap':
      return generateTreemapChartOption(data, colors, baseOption, props);
    case 'graph':
      return generateGraphChartOption(data, colors, baseOption, props);
    case 'radar':
      return generateRadarChartOption(data, colors, baseOption, props);
    default:
      return baseOption;
  }
};

// Line chart configuration
const generateLineChartOption = (
  data: ChartData,
  colors: any,
  baseOption: EChartsOption,
  props: EChartsWrapperProps
): EChartsOption => {
  if (!data.timeSeries) return baseOption;

  const categories = [...new Set(data.timeSeries.map(d => d.category))].filter(Boolean);
  const xAxisData = [...new Set(data.timeSeries.map(d => d.timestamp))];

  const series = categories.length > 0 ? categories.map((category, index) => ({
    name: category,
    type: 'line' as const,
    smooth: true,
    data: xAxisData.map(timestamp => {
      const point = data.timeSeries!.find(d => d.timestamp === timestamp && d.category === category);
      return point ? point.value : null;
    }),
    lineStyle: {
      width: 2
    },
    areaStyle: {
      opacity: 0.3,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: colors.gradientColors[index % colors.gradientColors.length] },
        { offset: 1, color: 'transparent' }
      ])
    }
  })) : [{
    name: 'Value',
    type: 'line' as const,
    smooth: true,
    data: data.timeSeries.map(d => [d.timestamp, d.value]),
    lineStyle: {
      width: 3,
      color: colors.primaryColor
    },
    areaStyle: {
      opacity: 0.2,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: colors.primaryColor },
        { offset: 1, color: 'transparent' }
      ])
    }
  }];

  return {
    ...baseOption,
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: {
        lineStyle: { color: colors.lineColor }
      },
      axisLabel: {
        color: colors.textColor,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: { color: colors.lineColor }
      },
      axisLabel: {
        color: colors.textColor
      },
      splitLine: {
        lineStyle: { color: colors.lineColor, opacity: 0.3 }
      }
    },
    series,
    dataZoom: props.enableDataZoom ? [
      {
        type: 'inside',
        start: 70,
        end: 100
      },
      {
        type: 'slider',
        start: 70,
        end: 100,
        textStyle: {
          color: colors.textColor
        }
      }
    ] : undefined
  };
};

// Bar chart configuration
const generateBarChartOption = (
  data: ChartData,
  colors: any,
  baseOption: EChartsOption,
  props: EChartsWrapperProps
): EChartsOption => {
  if (!data.categories) return baseOption;

  return {
    ...baseOption,
    xAxis: {
      type: 'category',
      data: data.categories.map(d => d.name),
      axisLine: {
        lineStyle: { color: colors.lineColor }
      },
      axisLabel: {
        color: colors.textColor,
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: { color: colors.lineColor }
      },
      axisLabel: {
        color: colors.textColor
      },
      splitLine: {
        lineStyle: { color: colors.lineColor, opacity: 0.3 }
      }
    },
    series: [{
      name: 'Value',
      type: 'bar',
      data: data.categories.map((d, index) => ({
        value: d.value,
        itemStyle: {
          color: d.color || colors.gradientColors[index % colors.gradientColors.length]
        }
      })),
      animationDelay: (idx: number) => idx * 100,
      animationDelayUpdate: (idx: number) => idx * 100
    }]
  };
};

// Pie chart configuration
const generatePieChartOption = (
  data: ChartData,
  colors: any,
  baseOption: EChartsOption,
  props: EChartsWrapperProps
): EChartsOption => {
  if (!data.categories) return baseOption;

  return {
    ...baseOption,
    series: [{
      name: 'Distribution',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '60%'],
      data: data.categories.map((d, index) => ({
        name: d.name,
        value: d.value,
        itemStyle: {
          color: d.color || colors.gradientColors[index % colors.gradientColors.length]
        }
      })),
      label: {
        show: true,
        formatter: '{b}: {c} ({d}%)',
        color: colors.textColor
      },
      labelLine: {
        show: true,
        lineStyle: {
          color: colors.textColor
        }
      },
      animationType: 'scale',
      animationEasing: 'elasticOut',
      animationDelay: (idx: number) => Math.random() * 200
    }]
  };
};

// Gauge chart configuration
const generateGaugeChartOption = (
  data: ChartData,
  colors: any,
  baseOption: EChartsOption,
  props: EChartsWrapperProps
): EChartsOption => {
  if (!data.metrics || data.metrics.length === 0) return baseOption;

  const metric = data.metrics[0];
  
  return {
    ...baseOption,
    series: [{
      name: 'Performance',
      type: 'gauge',
      radius: '80%',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 100,
      splitNumber: 5,
      axisLine: {
        lineStyle: {
          width: 15,
          color: [
            [0.3, colors.errorColor],
            [0.7, colors.warningColor],
            [1, colors.successColor]
          ]
        }
      },
      pointer: {
        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
        length: '12%',
        width: 20,
        offsetCenter: [0, '-60%'],
        itemStyle: {
          color: 'auto'
        }
      },
      axisTick: {
        length: 12,
        lineStyle: {
          color: 'auto',
          width: 2
        }
      },
      splitLine: {
        length: 20,
        lineStyle: {
          color: 'auto',
          width: 5
        }
      },
      axisLabel: {
        color: colors.textColor,
        fontSize: 12,
        distance: -60,
        rotate: 'tangential',
        formatter: function(value: number) {
          if (value === 0) return '0%';
          if (value === 100) return '100%';
          return value + '%';
        }
      },
      title: {
        offsetCenter: [0, '-20%'],
        fontSize: 20,
        color: colors.textColor
      },
      detail: {
        fontSize: 30,
        offsetCenter: [0, '-35%'],
        valueAnimation: true,
        formatter: function(value: number) {
          return Math.round(value) + '%';
        },
        color: colors.textColor
      },
      data: [{
        value: metric.value,
        name: metric.name,
        title: {
          show: true
        },
        detail: {
          show: true
        }
      }]
    }]
  };
};

// Graph chart configuration for network visualization
const generateGraphChartOption = (
  data: ChartData,
  colors: any,
  baseOption: EChartsOption,
  props: EChartsWrapperProps
): EChartsOption => {
  if (!data.network) return baseOption;

  return {
    ...baseOption,
    series: [{
      name: 'Network',
      type: 'graph',
      layout: 'force',
      data: data.network.nodes,
      links: data.network.links,
      categories: data.network.categories,
      roam: true,
      label: {
        show: true,
        position: 'right',
        formatter: '{b}',
        color: colors.textColor
      },
      labelLayout: {
        hideOverlap: true
      },
      scaleLimit: {
        min: 0.4,
        max: 2
      },
      lineStyle: {
        color: 'source',
        curveness: 0.3
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: {
          width: 10
        }
      },
      force: {
        repulsion: 100,
        gravity: 0.1,
        edgeLength: 100,
        layoutAnimation: true
      }
    }]
  };
};

// Additional chart type generators (simplified for brevity)
const generateScatterChartOption = (data: ChartData, colors: any, baseOption: EChartsOption, props: EChartsWrapperProps): EChartsOption => baseOption;
const generateHeatmapChartOption = (data: ChartData, colors: any, baseOption: EChartsOption, props: EChartsWrapperProps): EChartsOption => baseOption;
const generateTreemapChartOption = (data: ChartData, colors: any, baseOption: EChartsOption, props: EChartsWrapperProps): EChartsOption => baseOption;
const generateRadarChartOption = (data: ChartData, colors: any, baseOption: EChartsOption, props: EChartsWrapperProps): EChartsOption => baseOption;

// Main component
export const EChartsWrapper: React.FC<EChartsWrapperProps> = ({
  data,
  type,
  title,
  subtitle,
  theme = 'light',
  width = '100%',
  height = 400,
  options,
  enableDataZoom = false,
  enableBrush = false,
  enableAnimation = true,
  enableRealTime = false,
  updateInterval = 1000,
  onChartClick,
  onDataUpdate,
  className,
  style,
  loading = false,
  error
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<ECharts | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Generate chart options
  const chartOption = useMemo(() => {
    const generatedOption = generateChartOption(type, data, theme, {
      data, type, title, subtitle, theme, width, height, options,
      enableDataZoom, enableBrush, enableAnimation, enableRealTime,
      updateInterval, onChartClick, onDataUpdate, className, style, loading, error
    });
    
    // Merge with custom options
    return options ? echarts.util.merge(generatedOption, options) : generatedOption;
  }, [data, type, theme, options, title, subtitle, enableDataZoom, enableBrush, enableAnimation]);

  // Initialize chart
  useEffect(() => {
    if (chartRef.current && !chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current, theme);
      setIsInitialized(true);

      // Add click listener
      if (onChartClick) {
        chartInstanceRef.current.on('click', onChartClick);
      }

      // Handle resize
      const handleResize = () => {
        chartInstanceRef.current?.resize();
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartInstanceRef.current) {
          chartInstanceRef.current.dispose();
          chartInstanceRef.current = null;
        }
      };
    }
  }, [theme, onChartClick]);

  // Update chart options
  useEffect(() => {
    if (chartInstanceRef.current && isInitialized) {
      chartInstanceRef.current.setOption(chartOption, true);
    }
  }, [chartOption, isInitialized]);

  // Real-time updates
  useEffect(() => {
    if (enableRealTime && updateInterval > 0 && onDataUpdate) {
      const interval = setInterval(() => {
        onDataUpdate(data);
      }, updateInterval);

      return () => clearInterval(interval);
    }
  }, [enableRealTime, updateInterval, onDataUpdate, data]);

  // Show loading state
  useEffect(() => {
    if (chartInstanceRef.current) {
      if (loading) {
        chartInstanceRef.current.showLoading('default', {
          text: 'Loading...',
          color: CHART_THEMES[theme].primaryColor,
          textColor: CHART_THEMES[theme].textColor,
          maskColor: 'rgba(255, 255, 255, 0.8)',
          zlevel: 0
        });
      } else {
        chartInstanceRef.current.hideLoading();
      }
    }
  }, [loading, theme]);

  // Error handling
  if (error) {
    return (
      <div 
        className={`echarts-error ${className || ''}`}
        style={{
          width,
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: CHART_THEMES[theme].backgroundColor,
          color: CHART_THEMES[theme].errorColor,
          border: `1px solid ${CHART_THEMES[theme].errorColor}`,
          borderRadius: 8,
          fontSize: 14,
          fontWeight: 'bold',
          ...style
        }}
      >
        <div>
          <div style={{ marginBottom: 8 }}>⚠️ Chart Error</div>
          <div style={{ fontSize: 12, opacity: 0.8 }}>{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={chartRef}
      className={`echarts-container ${className || ''}`}
      style={{
        width,
        height,
        backgroundColor: CHART_THEMES[theme].backgroundColor,
        ...style
      }}
    />
  );
};

export default EChartsWrapper; 