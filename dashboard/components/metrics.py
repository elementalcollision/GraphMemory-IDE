"""
Metrics Display Components

This module provides Streamlit components for displaying real-time metrics
using fragments for auto-refresh functionality.
"""

import streamlit as st
from typing import Dict, Any
import logging
from utils.api_client import get_api_client

logger = logging.getLogger(__name__)


@st.fragment(run_every=2)
def render_analytics_metrics():
    """Real-time analytics metrics display"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client
        api_client = get_api_client()
        analytics_data = api_client.fetch_analytics_data()
        
        if analytics_data:
            # Create metrics columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Active Nodes",
                    value=analytics_data.get('active_nodes', 0),
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="Active Edges", 
                    value=analytics_data.get('active_edges', 0),
                    delta=None
                )
            
            with col3:
                query_rate = analytics_data.get('query_rate', 0)
                st.metric(
                    label="Query Rate",
                    value=f"{query_rate}/min",
                    delta=None
                )
            
            with col4:
                cache_hit_rate = analytics_data.get('cache_hit_rate', 0)
                st.metric(
                    label="Cache Hit Rate",
                    value=f"{cache_hit_rate:.1%}",
                    delta=None
                )
            
            # Second row of metrics
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                memory_usage = analytics_data.get('memory_usage', 0)
                st.metric(
                    label="Memory Usage",
                    value=f"{memory_usage:.1f}%",
                    delta=None
                )
            
            with col6:
                cpu_usage = analytics_data.get('cpu_usage', 0)
                st.metric(
                    label="CPU Usage",
                    value=f"{cpu_usage:.1f}%",
                    delta=None
                )
            
            with col7:
                response_time = analytics_data.get('response_time', 0)
                st.metric(
                    label="Response Time",
                    value=f"{response_time:.0f}ms",
                    delta=None
                )
            
            with col8:
                # Calculate uptime or other derived metric
                uptime_hours = analytics_data.get('uptime_seconds', 0) / 3600
                st.metric(
                    label="Uptime",
                    value=f"{uptime_hours:.1f}h",
                    delta=None
                )
        else:
            st.warning("📊 No analytics data available")
            
    except Exception as e:
        st.error(f"❌ Error loading analytics metrics: {e}")
        logger.error(f"Analytics metrics error: {e}")


@st.fragment(run_every=5)
def render_memory_metrics():
    """Real-time memory metrics display"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client
        api_client = get_api_client()
        memory_data = api_client.fetch_memory_data()
        
        if memory_data:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_memories = memory_data.get('total_memories', 0)
                st.metric(
                    label="Total Memories",
                    value=f"{total_memories:,}",
                    delta=None
                )
            
            with col2:
                growth_rate = memory_data.get('memory_growth_rate', 0)
                st.metric(
                    label="Growth Rate",
                    value=f"{growth_rate:.1%}",
                    delta=None
                )
            
            with col3:
                efficiency = memory_data.get('memory_efficiency', 0)
                st.metric(
                    label="Efficiency",
                    value=f"{efficiency:.1%}",
                    delta=None
                )
            
            # Second row - memory type breakdown
            st.markdown("### Memory Type Distribution")
            col4, col5, col6 = st.columns(3)
            
            with col4:
                procedural = memory_data.get('procedural_memories', 0)
                st.metric(
                    label="Procedural",
                    value=f"{procedural:,}",
                    delta=None
                )
            
            with col5:
                semantic = memory_data.get('semantic_memories', 0)
                st.metric(
                    label="Semantic",
                    value=f"{semantic:,}",
                    delta=None
                )
            
            with col6:
                episodic = memory_data.get('episodic_memories', 0)
                st.metric(
                    label="Episodic",
                    value=f"{episodic:,}",
                    delta=None
                )
            
            # Additional memory metrics
            col7, col8, col9 = st.columns(3)
            
            with col7:
                avg_size = memory_data.get('avg_memory_size', 0)
                st.metric(
                    label="Avg Memory Size",
                    value=f"{avg_size:.1f} KB",
                    delta=None
                )
            
            with col8:
                compression_ratio = memory_data.get('compression_ratio', 0)
                st.metric(
                    label="Compression Ratio",
                    value=f"{compression_ratio:.2f}x",
                    delta=None
                )
            
            with col9:
                retrieval_speed = memory_data.get('retrieval_speed', 0)
                st.metric(
                    label="Retrieval Speed",
                    value=f"{retrieval_speed:.0f}ms",
                    delta=None
                )
        else:
            st.warning("🧠 No memory data available")
            
    except Exception as e:
        st.error(f"❌ Error loading memory metrics: {e}")
        logger.error(f"Memory metrics error: {e}")


@st.fragment(run_every=3)
def render_graph_metrics():
    """Real-time graph metrics display"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client
        api_client = get_api_client()
        graph_data = api_client.fetch_graph_data()
        
        if graph_data:
            # Basic graph metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                node_count = graph_data.get('node_count', 0)
                st.metric(
                    label="Nodes",
                    value=f"{node_count:,}",
                    delta=None
                )
            
            with col2:
                edge_count = graph_data.get('edge_count', 0)
                st.metric(
                    label="Edges",
                    value=f"{edge_count:,}",
                    delta=None
                )
            
            with col3:
                components = graph_data.get('connected_components', 0)
                st.metric(
                    label="Components",
                    value=f"{components:,}",
                    delta=None
                )
            
            with col4:
                diameter = graph_data.get('diameter', 0)
                st.metric(
                    label="Diameter",
                    value=f"{diameter}",
                    delta=None
                )
            
            # Advanced graph metrics
            col5, col6, col7, col8 = st.columns(4)
            
            with col5:
                density = graph_data.get('density', 0)
                st.metric(
                    label="Density",
                    value=f"{density:.3f}",
                    delta=None
                )
            
            with col6:
                clustering = graph_data.get('clustering_coefficient', 0)
                st.metric(
                    label="Clustering",
                    value=f"{clustering:.3f}",
                    delta=None
                )
            
            with col7:
                centrality = graph_data.get('avg_centrality', 0)
                st.metric(
                    label="Avg Centrality",
                    value=f"{centrality:.3f}",
                    delta=None
                )
            
            with col8:
                modularity = graph_data.get('modularity', 0)
                st.metric(
                    label="Modularity",
                    value=f"{modularity:.3f}",
                    delta=None
                )
        else:
            st.warning("🔗 No graph data available")
            
    except Exception as e:
        st.error(f"❌ Error loading graph metrics: {e}")
        logger.error(f"Graph metrics error: {e}")


def render_system_health_metrics():
    """Render system health overview metrics"""
    try:
        api_client = get_api_client()
        
        # Check server status
        server_status = api_client.check_server_status()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_text = "🟢 Online" if server_status else "🔴 Offline"
            st.metric(
                label="Server Status",
                value=status_text,
                delta=None
            )
        
        with col2:
            # Get connection info
            conn_info = api_client.get_connection_info()
            active_connections = conn_info.get('active_connections', 0) if conn_info else 0
            st.metric(
                label="Active Connections",
                value=f"{active_connections}",
                delta=None
            )
        
        with col3:
            # Calculate overall health score
            health_score = calculate_health_score(server_status, active_connections)
            st.metric(
                label="Health Score",
                value=f"{health_score}/100",
                delta=None
            )
            
    except Exception as e:
        st.error(f"❌ Error loading system health: {e}")
        logger.error(f"System health error: {e}")


def calculate_health_score(server_status: bool, active_connections: int) -> int:
    """Calculate overall system health score"""
    score = 0
    
    # Server status (50 points)
    if server_status:
        score += 50
    
    # Connection health (30 points)
    if active_connections > 0:
        score += min(30, active_connections * 10)
    
    # Base operational score (20 points)
    score += 20
    
    return min(100, score) 