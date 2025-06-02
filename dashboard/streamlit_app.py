"""
GraphMemory-IDE Dashboard - Main Application

This is the main Streamlit application file for the GraphMemory-IDE
real-time analytics dashboard.
"""

import streamlit as st
import sys
import os
import logging
from pathlib import Path

# Add the dashboard directory to Python path
dashboard_dir = Path(__file__).parent
sys.path.insert(0, str(dashboard_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import components
try:
    from components.auth import check_authentication
    from components.layout import setup_page_config, render_sidebar, render_main_header, render_footer
    from utils.api_client import get_api_client
    from pages.analytics import render_analytics_page
except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.stop()


def main() -> None:
    """Main application function"""
    try:
        # Setup page configuration
        setup_page_config(
            page_title="GraphMemory-IDE Dashboard",
            page_icon="🧠",
            layout="wide"
        )
        
        # Check authentication
        if not check_authentication():
            return
        
        # Initialize API client
        if 'api_client' not in st.session_state:
            st.session_state.api_client = get_api_client()
        
        # Render sidebar
        render_sidebar()
        
        # Main content area
        render_main_content()
        
        # Footer
        render_footer()
        
    except Exception as e:
        st.error(f"❌ Application error: {e}")
        logger.error(f"Main application error: {e}")


def render_main_content() -> None:
    """Render the main content area"""
    # Get current page from session state
    current_page = st.session_state.get('current_page', '📊 Analytics')
    
    # Render appropriate page
    if current_page == '📊 Analytics':
        render_analytics_page()
    elif current_page == '🧠 Memory':
        render_memory_page()
    elif current_page == '🔗 Graph':
        render_graph_page()
    else:
        # Default to analytics
        render_analytics_page()


def render_analytics_page() -> None:
    """Render the analytics dashboard page"""
    render_main_header(
        "📊 Real-time Analytics Dashboard",
        "Live system performance metrics and monitoring"
    )
    
    # Check if streaming is enabled
    streaming = st.session_state.get('streaming', True)
    
    if not streaming:
        st.warning("⏸️ Real-time streaming is paused. Click 'Start' in the sidebar to resume.")
    
    # Import and render analytics components
    try:
        from components.metrics import render_analytics_metrics
        from components.charts import render_analytics_charts
        
        # Metrics section
        st.header("📈 Key Metrics")
        render_analytics_metrics()
        
        # Charts section
        st.header("📊 Performance Charts")
        render_analytics_charts()
        
    except ImportError as e:
        st.error(f"❌ Error loading analytics components: {e}")
        render_fallback_analytics()


def render_memory_page() -> None:
    """Render the memory insights page"""
    render_main_header(
        "🧠 Memory System Insights",
        "Memory distribution, growth tracking, and efficiency metrics"
    )
    
    try:
        from components.metrics import render_memory_metrics
        from components.charts import render_memory_charts
        
        # Memory metrics
        st.header("🧠 Memory Statistics")
        render_memory_metrics()
        
        # Memory charts
        st.header("📊 Memory Visualizations")
        render_memory_charts()
        
    except ImportError as e:
        st.error(f"❌ Error loading memory components: {e}")
        render_fallback_memory()


def render_graph_page() -> None:
    """Render the graph metrics page"""
    render_main_header(
        "🔗 Graph Analytics",
        "Network topology, connectivity analysis, and graph metrics"
    )
    
    try:
        from components.charts import render_graph_charts
        
        # Graph visualizations
        render_graph_charts()
        
    except ImportError as e:
        st.error(f"❌ Error loading graph components: {e}")
        render_fallback_graph()


def render_fallback_analytics() -> None:
    """Render fallback analytics content when components fail to load"""
    st.info("📊 Analytics components are being loaded...")
    
    # Basic metrics display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Nodes", "Loading...")
    with col2:
        st.metric("Active Edges", "Loading...")
    with col3:
        st.metric("Query Rate", "Loading...")
    with col4:
        st.metric("Cache Hit Rate", "Loading...")
    
    st.info("💡 Please ensure all dependencies are installed and the server is running.")


def render_fallback_memory() -> None:
    """Render fallback memory content when components fail to load"""
    st.info("🧠 Memory components are being loaded...")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Memories", "Loading...")
    with col2:
        st.metric("Growth Rate", "Loading...")
    with col3:
        st.metric("Efficiency", "Loading...")


def render_fallback_graph() -> None:
    """Render fallback graph content when components fail to load"""
    st.info("🔗 Graph components are being loaded...")
    st.metric("Graph Metrics", "Loading...")


if __name__ == "__main__":
    main() 