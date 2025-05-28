"""
Chart Configuration Utilities

This module provides utilities for generating Apache ECharts configurations
for various dashboard visualizations.
"""

from typing import Dict, Any, List


def create_analytics_chart_config(analytics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ECharts configuration for analytics data"""
    return {
        "title": {
            "text": "System Performance",
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.8)",
            "textStyle": {"color": "#fff"}
        },
        "legend": {
            "data": ["Memory Usage", "CPU Usage"],
            "top": "10%"
        },
        "xAxis": {
            "type": "category",
            "data": ["Current"],
            "axisLabel": {"fontSize": 12}
        },
        "yAxis": {
            "type": "value",
            "max": 100,
            "axisLabel": {
                "formatter": "{value}%",
                "fontSize": 12
            }
        },
        "series": [
            {
                "name": "Memory Usage",
                "type": "bar",
                "data": [analytics_data.get('memory_usage', 0)],
                "itemStyle": {
                    "color": "#FF6B6B",
                    "borderRadius": [4, 4, 0, 0]
                },
                "barWidth": "40%"
            },
            {
                "name": "CPU Usage", 
                "type": "bar",
                "data": [analytics_data.get('cpu_usage', 0)],
                "itemStyle": {
                    "color": "#4ECDC4",
                    "borderRadius": [4, 4, 0, 0]
                },
                "barWidth": "40%"
            }
        ],
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": "25%"
        }
    }


def create_memory_distribution_config(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ECharts configuration for memory distribution"""
    return {
        "title": {
            "text": "Memory Distribution",
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: {c} ({d}%)",
            "backgroundColor": "rgba(50, 50, 50, 0.8)",
            "textStyle": {"color": "#fff"}
        },
        "legend": {
            "orient": "horizontal",
            "bottom": "5%",
            "data": ["Procedural", "Semantic", "Episodic"]
        },
        "series": [
            {
                "name": "Memory Types",
                "type": "pie",
                "radius": ["30%", "60%"],
                "center": ["50%", "45%"],
                "data": [
                    {
                        "value": memory_data.get('procedural_memories', 0),
                        "name": "Procedural",
                        "itemStyle": {"color": "#FF6B6B"}
                    },
                    {
                        "value": memory_data.get('semantic_memories', 0),
                        "name": "Semantic",
                        "itemStyle": {"color": "#4ECDC4"}
                    },
                    {
                        "value": memory_data.get('episodic_memories', 0),
                        "name": "Episodic",
                        "itemStyle": {"color": "#45B7D1"}
                    }
                ],
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                },
                "label": {
                    "show": True,
                    "formatter": "{b}: {c}"
                }
            }
        ]
    }


def create_graph_metrics_config(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ECharts configuration for graph metrics"""
    return {
        "title": {
            "text": "Graph Topology Metrics",
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.8)",
            "textStyle": {"color": "#fff"}
        },
        "xAxis": {
            "type": "category",
            "data": ["Nodes", "Edges", "Components", "Diameter"],
            "axisLabel": {"fontSize": 12}
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"fontSize": 12}
        },
        "series": [
            {
                "name": "Count",
                "type": "line",
                "data": [
                    graph_data.get('node_count', 0),
                    graph_data.get('edge_count', 0),
                    graph_data.get('connected_components', 0),
                    graph_data.get('diameter', 0)
                ],
                "itemStyle": {"color": "#45B7D1"},
                "lineStyle": {"width": 3},
                "symbol": "circle",
                "symbolSize": 8,
                "smooth": True
            }
        ],
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": "20%"
        }
    }


def create_response_time_config(analytics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ECharts configuration for response time visualization"""
    return {
        "title": {
            "text": "Response Time",
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": "{b}: {c} ms",
            "backgroundColor": "rgba(50, 50, 50, 0.8)",
            "textStyle": {"color": "#fff"}
        },
        "xAxis": {
            "type": "category",
            "data": ["Current"],
            "axisLabel": {"fontSize": 12}
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {
                "formatter": "{value} ms",
                "fontSize": 12
            }
        },
        "series": [{
            "name": "Response Time",
            "type": "line",
            "data": [analytics_data.get('response_time', 0)],
            "itemStyle": {"color": "#FF9F43"},
            "lineStyle": {"width": 3},
            "symbol": "circle",
            "symbolSize": 10,
            "areaStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "rgba(255, 159, 67, 0.3)"},
                        {"offset": 1, "color": "rgba(255, 159, 67, 0.1)"}
                    ]
                }
            }
        }],
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": "20%"
        }
    }


def create_memory_growth_config(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create ECharts configuration for memory growth visualization"""
    growth_rate = memory_data.get('memory_growth_rate', 0) * 100
    
    return {
        "title": {
            "text": "Memory Growth Rate",
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": "{b}: {c}%",
            "backgroundColor": "rgba(50, 50, 50, 0.8)",
            "textStyle": {"color": "#fff"}
        },
        "xAxis": {
            "type": "category",
            "data": ["Current"],
            "axisLabel": {"fontSize": 12}
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {
                "formatter": "{value}%",
                "fontSize": 12
            }
        },
        "series": [{
            "name": "Growth Rate",
            "type": "bar",
            "data": [growth_rate],
            "itemStyle": {
                "color": "#26DE81",
                "borderRadius": [4, 4, 0, 0]
            },
            "barWidth": "50%"
        }],
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": "20%"
        }
    } 