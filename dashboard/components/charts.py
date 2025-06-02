"""
Chart Components

This module provides Streamlit chart components using Apache ECharts
for real-time data visualization.
"""

import streamlit as st
from typing import Dict, Any
import logging
from utils.api_client import get_api_client
from utils.chart_configs import (
    create_analytics_chart_config,
    create_memory_distribution_config,
    create_graph_metrics_config,
    create_response_time_config,
    create_memory_growth_config
)

logger = logging.getLogger(__name__)

# Try to import streamlit-echarts, provide fallback if not available
try:
    from streamlit_echarts import st_echarts
    ECHARTS_AVAILABLE = True
except ImportError:
    ECHARTS_AVAILABLE = False
    logger.warning("streamlit-echarts not available, using fallback charts")


@st.fragment(run_every=3)
def render_analytics_charts() -> None:
    """Render real-time analytics charts"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client and data
        api_client = get_api_client()
        analytics_data = api_client.fetch_analytics_data()
        
        if analytics_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("System Performance")
                if ECHARTS_AVAILABLE:
                    chart_config = create_analytics_chart_config(analytics_data)
                    st_echarts(
                        options=chart_config,
                        height="400px",
                        key="analytics_performance_chart"
                    )
                else:
                    render_fallback_performance_chart(analytics_data)
            
            with col2:
                st.subheader("Response Time Trend")
                if ECHARTS_AVAILABLE:
                    response_time_config = create_response_time_config(analytics_data)
                    st_echarts(
                        options=response_time_config,
                        height="400px",
                        key="response_time_chart"
                    )
                else:
                    render_fallback_response_chart(analytics_data)
        else:
            st.warning("📊 No analytics data available for charts")
            
    except Exception as e:
        st.error(f"❌ Error loading analytics charts: {e}")
        logger.error(f"Analytics charts error: {e}")


@st.fragment(run_every=5)
def render_memory_charts() -> None:
    """Render real-time memory charts"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client and data
        api_client = get_api_client()
        memory_data = api_client.fetch_memory_data()
        
        if memory_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Memory Type Distribution")
                if ECHARTS_AVAILABLE:
                    chart_config = create_memory_distribution_config(memory_data)
                    st_echarts(
                        options=chart_config,
                        height="400px",
                        key="memory_distribution_chart"
                    )
                else:
                    render_fallback_memory_distribution(memory_data)
            
            with col2:
                st.subheader("Memory Growth Trend")
                if ECHARTS_AVAILABLE:
                    growth_config = create_memory_growth_config(memory_data)
                    st_echarts(
                        options=growth_config,
                        height="400px",
                        key="memory_growth_chart"
                    )
                else:
                    render_fallback_memory_growth(memory_data)
        else:
            st.warning("🧠 No memory data available for charts")
            
    except Exception as e:
        st.error(f"❌ Error loading memory charts: {e}")
        logger.error(f"Memory charts error: {e}")


@st.fragment(run_every=2)
def render_graph_charts() -> None:
    """Render real-time graph charts"""
    try:
        # Get streaming state
        streaming = st.session_state.get('streaming', True)
        if not streaming:
            return
        
        # Get API client and data
        api_client = get_api_client()
        graph_data = api_client.fetch_graph_data()
        
        if graph_data:
            st.subheader("Graph Topology Metrics")
            if ECHARTS_AVAILABLE:
                chart_config = create_graph_metrics_config(graph_data)
                st_echarts(
                    options=chart_config,
                    height="500px",
                    key="graph_metrics_chart"
                )
            else:
                render_fallback_graph_metrics(graph_data)
        else:
            st.warning("🔗 No graph data available for charts")
            
    except Exception as e:
        st.error(f"❌ Error loading graph charts: {e}")
        logger.error(f"Graph charts error: {e}")


def render_fallback_performance_chart(analytics_data: Dict[str, Any]) -> None:
    """Fallback chart for system performance using Streamlit native charts"""
    import pandas as pd
    
    # Create data for bar chart
    data = {
        'Metric': ['Memory Usage', 'CPU Usage'],
        'Value': [
            analytics_data.get('memory_usage', 0),
            analytics_data.get('cpu_usage', 0)
        ]
    }
    df = pd.DataFrame(data)
    
    # Use Streamlit bar chart
    st.bar_chart(df.set_index('Metric'))


def render_fallback_response_chart(analytics_data: Dict[str, Any]) -> None:
    """Fallback chart for response time using Streamlit native charts"""
    import pandas as pd
    
    # Create simple line chart data
    data = {
        'Time': ['Current'],
        'Response Time (ms)': [analytics_data.get('response_time', 0)]
    }
    df = pd.DataFrame(data)
    
    # Use Streamlit line chart
    st.line_chart(df.set_index('Time'))


def render_fallback_memory_distribution(memory_data: Dict[str, Any]) -> None:
    """Fallback chart for memory distribution using Streamlit native charts"""
    import pandas as pd
    
    # Create pie chart data (using bar chart as fallback)
    data = {
        'Memory Type': ['Procedural', 'Semantic', 'Episodic'],
        'Count': [
            memory_data.get('procedural_memories', 0),
            memory_data.get('semantic_memories', 0),
            memory_data.get('episodic_memories', 0)
        ]
    }
    df = pd.DataFrame(data)
    
    # Use Streamlit bar chart
    st.bar_chart(df.set_index('Memory Type'))


def render_fallback_memory_growth(memory_data: Dict[str, Any]) -> None:
    """Fallback chart for memory growth using Streamlit native charts"""
    import pandas as pd
    
    growth_rate = memory_data.get('memory_growth_rate', 0) * 100
    
    # Create simple bar chart
    data = {
        'Metric': ['Growth Rate'],
        'Value (%)': [growth_rate]
    }
    df = pd.DataFrame(data)
    
    # Use Streamlit bar chart
    st.bar_chart(df.set_index('Metric'))


def render_fallback_graph_metrics(graph_data: Dict[str, Any]) -> None:
    """Fallback chart for graph metrics using Streamlit native charts"""
    import pandas as pd
    
    # Create line chart data
    data = {
        'Metric': ['Nodes', 'Edges', 'Components', 'Diameter'],
        'Value': [
            graph_data.get('node_count', 0),
            graph_data.get('edge_count', 0),
            graph_data.get('connected_components', 0),
            graph_data.get('diameter', 0)
        ]
    }
    df = pd.DataFrame(data)
    
    # Use Streamlit line chart
    st.line_chart(df.set_index('Metric'))


def render_custom_chart(title: str, chart_config: Dict[str, Any], height: str = "400px") -> None:
    """Render a custom ECharts chart with fallback"""
    st.subheader(title)
    
    if ECHARTS_AVAILABLE:
        st_echarts(
            options=chart_config,
            height=height,
            key=f"custom_chart_{title.lower().replace(' ', '_')}"
        )
    else:
        st.info("📊 ECharts not available. Please install streamlit-echarts for enhanced visualizations.")


def render_real_time_indicator() -> None:
    """Render real-time streaming indicator"""
    streaming = st.session_state.get('streaming', True)
    
    if streaming:
        st.markdown("""
        <div style="text-align: center; color: #28a745; font-weight: bold; animation: pulse 2s infinite;">
            🔴 LIVE - Real-time data streaming
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; color: #6c757d; font-weight: bold;">
            ⏸️ PAUSED - Streaming stopped
        </div>
        """, unsafe_allow_html=True)


def render_chart_controls() -> None:
    """Render chart control options"""
    with st.expander("📊 Chart Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            chart_theme = st.selectbox(
                "Chart Theme",
                options=["default", "dark", "light"],
                index=0,
                key="chart_theme"
            )
        
        with col2:
            auto_scale = st.checkbox(
                "Auto Scale Y-Axis",
                value=True,
                key="auto_scale"
            )
        
        # Store settings in session state
        st.session_state.chart_theme = chart_theme
        st.session_state.auto_scale = auto_scale 