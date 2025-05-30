import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import Graphin, { Utils, Behaviors } from '@antv/graphin';
import { Tooltip, MiniMap, ContextMenu, Legend, Hull } from '@antv/graphin-components';
import { INode, IEdge, GraphinData } from '@antv/graphin';
import '@antv/graphin/dist/index.css';
import '@antv/graphin-components/dist/index.css';

// Types for GraphMemory-IDE specific data structures
interface MemoryNode {
  id: string;
  type: 'episodic' | 'semantic' | 'procedural';
  title: string;
  content: string;
  timestamp: string;
  tags: string[];
  connections: number;
  importance: number;
  cluster?: string;
}

interface MemoryEdge {
  source: string;
  target: string;
  relationship: 'associates' | 'contains' | 'derives' | 'references';
  strength: number;
  timestamp: string;
}

interface KnowledgeGraphData {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  clusters?: Array<{
    id: string;
    label: string;
    nodes: string[];
    color: string;
  }>;
}

interface KnowledgeGraphVisualizationProps {
  data: KnowledgeGraphData;
  onNodeClick?: (node: MemoryNode) => void;
  onEdgeClick?: (edge: MemoryEdge) => void;
  onNodeHover?: (node: MemoryNode | null) => void;
  layout?: 'force' | 'circular' | 'dagre' | 'grid' | 'concentric' | 'radial';
  theme?: 'light' | 'dark';
  enableClustering?: boolean;
  enableSearch?: boolean;
  enableMiniMap?: boolean;
  enableTooltip?: boolean;
  enableContextMenu?: boolean;
  width?: number;
  height?: number;
  className?: string;
  style?: React.CSSProperties;
}

// Color schemes for different memory types and themes
const COLOR_SCHEMES = {
  light: {
    episodic: '#1890ff',
    semantic: '#52c41a', 
    procedural: '#fa8c16',
    background: '#ffffff',
    text: '#000000',
    edge: '#d9d9d9'
  },
  dark: {
    episodic: '#177ddc',
    semantic: '#49aa19',
    procedural: '#d46b08',
    background: '#141414',
    text: '#ffffff',
    edge: '#434343'
  }
};

// Transform GraphMemory data to Graphin format
const transformDataToGraphin = (
  data: KnowledgeGraphData,
  theme: 'light' | 'dark' = 'light'
): GraphinData => {
  const colors = COLOR_SCHEMES[theme];
  
  const nodes: INode[] = data.nodes.map(node => ({
    id: node.id,
    data: {
      ...node,
      // Calculate node size based on importance and connections
      size: Math.max(20, Math.min(60, node.importance * 30 + node.connections * 2)),
      color: colors[node.type],
      label: node.title,
      cluster: node.cluster
    },
    style: {
      keyshape: {
        fill: colors[node.type],
        stroke: theme === 'dark' ? '#fff' : '#000',
        strokeWidth: 1,
        opacity: 0.9
      },
      label: {
        value: node.title.length > 20 ? `${node.title.substring(0, 17)}...` : node.title,
        fontSize: 12,
        fontWeight: 'bold',
        fill: colors.text,
        offset: [0, 5]
      },
      icon: {
        type: 'text',
        value: getMemoryTypeIcon(node.type),
        size: 14,
        fill: '#fff'
      },
      badges: node.tags.length > 0 ? [{
        position: 'top',
        type: 'text',
        value: node.tags.length.toString(),
        size: 8,
        fill: '#fff',
        stroke: colors[node.type]
      }] : undefined
    }
  }));

  const edges: IEdge[] = data.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    data: edge,
    style: {
      keyshape: {
        stroke: colors.edge,
        strokeWidth: Math.max(1, edge.strength * 3),
        opacity: 0.6,
        lineDash: edge.relationship === 'references' ? [5, 5] : undefined
      },
      label: {
        value: edge.relationship,
        fontSize: 10,
        fill: colors.text,
        background: {
          fill: colors.background,
          stroke: colors.edge,
          padding: [2, 4]
        }
      }
    }
  }));

  return { nodes, edges };
};

// Get icon for memory type
const getMemoryTypeIcon = (type: string): string => {
  switch (type) {
    case 'episodic': return '📝';
    case 'semantic': return '🧠';  
    case 'procedural': return '⚙️';
    default: return '❓';
  }
};

// Custom behaviors for GraphMemory-IDE
const CUSTOM_BEHAVIORS = [
  'drag-canvas',
  'zoom-canvas', 
  'drag-node',
  'activate-relations',
  'brush-select'
];

export const KnowledgeGraphVisualization: React.FC<KnowledgeGraphVisualizationProps> = ({
  data,
  onNodeClick,
  onEdgeClick,
  onNodeHover,
  layout = 'force',
  theme = 'light',
  enableClustering = true,
  enableSearch = true,
  enableMiniMap = true,
  enableTooltip = true,
  enableContextMenu = true,
  width = 800,
  height = 600,
  className,
  style
}) => {
  const graphRef = useRef<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Transform data to Graphin format
  const graphinData = useMemo(() => 
    transformDataToGraphin(data, theme), 
    [data, theme]
  );

  // Filter data based on search term
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return graphinData;
    
    const searchLower = searchTerm.toLowerCase();
    const filteredNodes = graphinData.nodes.filter(node => 
      node.data.title?.toLowerCase().includes(searchLower) ||
      node.data.content?.toLowerCase().includes(searchLower) ||
      node.data.tags?.some((tag: string) => tag.toLowerCase().includes(searchLower))
    );
    
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = graphinData.edges.filter(edge => 
      nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );
    
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphinData, searchTerm]);

  // Layout configuration based on data size and layout type
  const layoutConfig = useMemo(() => {
    const nodeCount = filteredData.nodes.length;
    
    const baseConfig = {
      type: layout,
      preset: {
        type: 'concentric'
      },
      animation: true,
      defSpringLen: 120,
      minNodeSpacing: 30
    };

    switch (layout) {
      case 'force':
        return {
          ...baseConfig,
          linkDistance: nodeCount > 100 ? 80 : 120,
          nodeStrength: nodeCount > 100 ? -50 : -30,
          edgeStrength: 0.1,
          alpha: 0.3,
          alphaDecay: 0.028,
          velocityDecay: 0.09,
          collideStrength: 0.8
        };
      case 'circular':
        return {
          ...baseConfig,
          radius: Math.max(200, nodeCount * 3),
          startAngle: 0,
          endAngle: 2 * Math.PI
        };
      case 'dagre':
        return {
          ...baseConfig,
          rankdir: 'TB',
          align: 'DR',
          nodesep: 40,
          ranksep: 70
        };
      case 'grid':
        return {
          ...baseConfig,
          rows: Math.ceil(Math.sqrt(nodeCount)),
          cols: Math.ceil(Math.sqrt(nodeCount))
        };
      default:
        return baseConfig;
    }
  }, [layout, filteredData.nodes.length]);

  // Handle node interactions
  const handleNodeClick = useCallback((evt: any) => {
    const { item } = evt;
    if (item && item.getModel) {
      const model = item.getModel();
      setSelectedNodeId(model.id);
      
      if (onNodeClick && model.data) {
        onNodeClick(model.data);
      }
    }
  }, [onNodeClick]);

  const handleNodeMouseEnter = useCallback((evt: any) => {
    const { item } = evt;
    if (item && item.getModel) {
      const model = item.getModel();
      setHoveredNodeId(model.id);
      
      if (onNodeHover && model.data) {
        onNodeHover(model.data);
      }
    }
  }, [onNodeHover]);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNodeId(null);
    if (onNodeHover) {
      onNodeHover(null);
    }
  }, [onNodeHover]);

  const handleEdgeClick = useCallback((evt: any) => {
    const { item } = evt;
    if (item && item.getModel && onEdgeClick) {
      const model = item.getModel();
      if (model.data) {
        onEdgeClick(model.data);
      }
    }
  }, [onEdgeClick]);

  // Context menu options
  const contextMenuItems = [
    {
      key: 'expand',
      icon: '🔍',
      name: 'Expand Node',
      onClick: (node: any) => {
        console.log('Expanding node:', node);
        // Implement node expansion logic
      }
    },
    {
      key: 'hide',
      icon: '👁️',
      name: 'Hide Node',
      onClick: (node: any) => {
        console.log('Hiding node:', node);
        // Implement node hiding logic
      }
    },
    {
      key: 'cluster',
      icon: '🔗',
      name: 'Group Similar',
      onClick: (node: any) => {
        console.log('Clustering similar nodes:', node);
        // Implement clustering logic
      }
    }
  ];

  // Update graph when data changes
  useEffect(() => {
    if (graphRef.current && filteredData) {
      setIsLoading(true);
      const graph = graphRef.current.getGraph();
      
      // Smooth transition to new data
      graph.changeData(filteredData);
      graph.fitView(20);
      
      // Add event listeners
      graph.on('node:click', handleNodeClick);
      graph.on('node:mouseenter', handleNodeMouseEnter);
      graph.on('node:mouseleave', handleNodeMouseLeave);
      graph.on('edge:click', handleEdgeClick);
      
      setIsLoading(false);
      
      return () => {
        graph.off('node:click', handleNodeClick);
        graph.off('node:mouseenter', handleNodeMouseEnter);
        graph.off('node:mouseleave', handleNodeMouseLeave);
        graph.off('edge:click', handleEdgeClick);
      };
    }
  }, [filteredData, handleNodeClick, handleNodeMouseEnter, handleNodeMouseLeave, handleEdgeClick]);

  return (
    <div 
      className={`knowledge-graph-container ${className || ''}`}
      style={{
        width,
        height,
        border: `1px solid ${COLOR_SCHEMES[theme].edge}`,
        borderRadius: 8,
        backgroundColor: COLOR_SCHEMES[theme].background,
        position: 'relative',
        overflow: 'hidden',
        ...style
      }}
    >
      {/* Search Bar */}
      {enableSearch && (
        <div 
          style={{
            position: 'absolute',
            top: 10,
            left: 10,
            zIndex: 1000,
            display: 'flex',
            gap: 8,
            alignItems: 'center'
          }}
        >
          <input
            type="text"
            placeholder="Search memories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '8px 12px',
              border: `1px solid ${COLOR_SCHEMES[theme].edge}`,
              borderRadius: 6,
              backgroundColor: COLOR_SCHEMES[theme].background,
              color: COLOR_SCHEMES[theme].text,
              fontSize: 14,
              width: 200
            }}
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              style={{
                padding: '6px 10px',
                border: 'none',
                borderRadius: 4,
                backgroundColor: COLOR_SCHEMES[theme].edge,
                color: COLOR_SCHEMES[theme].text,
                cursor: 'pointer',
                fontSize: 12
              }}
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <div 
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1000,
            color: COLOR_SCHEMES[theme].text,
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          Loading graph...
        </div>
      )}

      {/* Main Graph Component */}
      <Graphin
        ref={graphRef}
        data={filteredData}
        layout={layoutConfig}
        theme={{
          mode: theme
        }}
        style={{ width: '100%', height: '100%' }}
        behaviors={CUSTOM_BEHAVIORS}
        animate={true}
        fitView={true}
        fitViewPadding={20}
      >
        {/* Interactive Components */}
        {enableTooltip && (
          <Tooltip
            bindType="node"
            placement="top"
            hasArrow={true}
          >
            {(model: any) => {
              const data = model?.data;
              if (!data) return null;
              
              return (
                <div style={{
                  padding: 12,
                  maxWidth: 300,
                  backgroundColor: COLOR_SCHEMES[theme].background,
                  border: `1px solid ${COLOR_SCHEMES[theme].edge}`,
                  borderRadius: 6,
                  color: COLOR_SCHEMES[theme].text,
                  fontSize: 13
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
                    {getMemoryTypeIcon(data.type)} {data.title}
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <strong>Type:</strong> {data.type}
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <strong>Connections:</strong> {data.connections}
                  </div>
                  <div style={{ marginBottom: 6 }}>
                    <strong>Tags:</strong> {data.tags?.join(', ') || 'None'}
                  </div>
                  <div style={{ 
                    maxHeight: 60, 
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {data.content}
                  </div>
                </div>
              );
            }}
          </Tooltip>
        )}

        {enableMiniMap && (
          <MiniMap 
            visible={true}
            type="keyShape"
            size={[150, 100]}
            className="graphin-minimap"
          />
        )}

        {enableContextMenu && (
          <ContextMenu 
            bindType="node"
            options={contextMenuItems}
            style={{
              backgroundColor: COLOR_SCHEMES[theme].background,
              border: `1px solid ${COLOR_SCHEMES[theme].edge}`,
              borderRadius: 6
            }}
          />
        )}

        {enableClustering && data.clusters && (
          <Hull
            options={data.clusters.map(cluster => ({
              id: cluster.id,
              members: cluster.nodes,
              type: 'round-convex',
              style: {
                fill: cluster.color,
                stroke: cluster.color,
                opacity: 0.2,
                strokeOpacity: 0.5
              },
              label: {
                text: cluster.label,
                position: 'top',
                style: {
                  fontSize: 12,
                  fontWeight: 'bold',
                  fill: COLOR_SCHEMES[theme].text
                }
              }
            }))}
          />
        )}

        {/* Behaviors for interaction */}
        <Behaviors.DragCanvas disabled={false} />
        <Behaviors.ZoomCanvas disabled={false} />
        <Behaviors.DragNode disabled={false} />
        <Behaviors.ActivateRelations trigger="mouseenter" />
        <Behaviors.BrushSelect trigger="shift" />
      </Graphin>

      {/* Graph Statistics */}
      <div
        style={{
          position: 'absolute',
          bottom: 10,
          right: 10,
          padding: '8px 12px',
          backgroundColor: COLOR_SCHEMES[theme].background,
          border: `1px solid ${COLOR_SCHEMES[theme].edge}`,
          borderRadius: 6,
          fontSize: 12,
          color: COLOR_SCHEMES[theme].text,
          zIndex: 1000
        }}
      >
        Nodes: {filteredData.nodes.length} | Edges: {filteredData.edges.length}
        {selectedNodeId && ` | Selected: ${selectedNodeId}`}
      </div>
    </div>
  );
};

export default KnowledgeGraphVisualization; 