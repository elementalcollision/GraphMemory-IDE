"""
Layout Components

This module provides layout components for the dashboard including
page configuration, sidebar navigation, and responsive design elements.
"""

import streamlit as st
from typing import Dict, Any
import logging
from utils.api_client import get_api_client
from components.auth import render_logout_button, render_user_info

logger = logging.getLogger(__name__)


def setup_page_config(
    page_title: str = "GraphMemory-IDE Analytics",
    page_icon: str = "📊",
    layout: str = "wide"
) -> None:
    """Setup page configuration with custom styling"""
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/issues',
            'Report a bug': 'https://github.com/your-repo/issues',
            'About': "GraphMemory-IDE Real-time Analytics Dashboard"
        }
    )
    
    # Load custom CSS
    load_custom_css()


def load_custom_css() -> None:
    """Load custom CSS styling"""
    try:
        with open('assets/styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        logger.warning("Custom CSS file not found, using default styling")


def render_sidebar() -> None:
    """Render enhanced sidebar with navigation and controls"""
    with st.sidebar:
        # Header
        st.title("🧠 GraphMemory-IDE")
        st.markdown("---")
        
        # Navigation
        render_navigation()
        
        # Streaming controls
        render_streaming_controls()
        
        # System status
        render_system_status()
        
        # User info and logout
        render_user_info()
        render_logout_button()


def render_navigation() -> None:
    """Render navigation menu"""
    st.header("📍 Navigation")
    
    # Define pages
    pages = {
        "📊 Analytics": "pages/1_📊_Analytics.py",
        "🧠 Memory": "pages/2_🧠_Memory.py", 
        "🔗 Graph": "pages/3_🔗_Graph.py"
    }
    
    # Current page detection
    current_page = st.session_state.get('current_page', '📊 Analytics')
    
    # Navigation buttons
    for page_name, page_file in pages.items():
        if st.button(
            page_name, 
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if page_name == current_page else "secondary"
        ):
            st.session_state.current_page = page_name
            # Note: In a real multi-page app, you'd use st.switch_page(page_file)
            st.rerun()


def render_streaming_controls() -> None:
    """Render streaming control buttons"""
    st.markdown("---")
    st.header("🔄 Streaming Controls")
    
    # Initialize streaming state
    if 'streaming' not in st.session_state:
        st.session_state.streaming = True
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start", 
            disabled=st.session_state.streaming,
            use_container_width=True,
            key="start_streaming"
        ):
            st.session_state.streaming = True
            st.success("🟢 Streaming started")
            st.rerun()
    
    with col2:
        if st.button(
            "⏸️ Stop", 
            disabled=not st.session_state.streaming,
            use_container_width=True,
            key="stop_streaming"
        ):
            st.session_state.streaming = False
            st.warning("🟡 Streaming stopped")
            st.rerun()
    
    # Status indicator
    status_text = "🟢 Streaming" if st.session_state.streaming else "🔴 Stopped"
    st.markdown(f"**Status:** {status_text}")
    
    # Refresh rate control
    st.markdown("### ⚡ Refresh Rate")
    refresh_rate = st.selectbox(
        "Update frequency",
        options=[1, 2, 5, 10],
        index=1,  # Default to 2 seconds
        format_func=lambda x: f"{x} second{'s' if x > 1 else ''}",
        key="refresh_rate"
    )
    st.session_state.refresh_rate = refresh_rate


def render_system_status() -> None:
    """Render system status information"""
    st.markdown("---")
    st.header("🔧 System Status")
    
    try:
        api_client = get_api_client()
        
        # Check server connection
        if api_client.check_server_status():
            st.success("✅ Server Connected")
            
            # Get connection info
            conn_info = api_client.get_connection_info()
            if conn_info:
                st.markdown("### 📊 Connection Stats")
                
                # Active connections
                active_connections = conn_info.get('active_connections', 0)
                st.metric("Active Connections", active_connections)
                
                # Server uptime
                uptime = conn_info.get('uptime', 'Unknown')
                st.markdown(f"**Uptime:** {uptime}")
                
                # Last update
                last_update = conn_info.get('last_update', 'Never')
                st.markdown(f"**Last Update:** {last_update}")
        else:
            st.error("❌ Server Disconnected")
            st.markdown("Please check if the FastAPI server is running on port 8000.")
            
    except Exception as e:
        st.error("❌ Connection Error")
        logger.error(f"System status error: {e}")


def render_main_header(title: str, subtitle: str = None) -> None:
    """Render main page header"""
    st.title(title)
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.markdown("---")


def render_metrics_grid(metrics: Dict[str, Any], columns: int = 4) -> None:
    """Render metrics in a responsive grid"""
    if not metrics:
        st.warning("📊 No metrics data available")
        return
    
    # Create columns
    cols = st.columns(columns)
    
    # Render metrics
    for i, (label, value) in enumerate(metrics.items()):
        with cols[i % columns]:
            if isinstance(value, (int, float)):
                # Format numeric values
                if isinstance(value, float) and 0 < value < 1:
                    # Percentage values
                    st.metric(label, f"{value:.1%}")
                elif isinstance(value, float):
                    # Decimal values
                    st.metric(label, f"{value:.2f}")
                else:
                    # Integer values
                    st.metric(label, f"{value:,}")
            else:
                # String values
                st.metric(label, str(value))


def render_chart_container(title: str, chart_component, height: str = "400px") -> None:
    """Render a chart in a styled container"""
    with st.container():
        st.markdown(f"""
        <div class="chart-container">
            <h3 style="text-align: center; margin-bottom: 20px;">{title}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        chart_component


def render_loading_placeholder(message: str = "Loading data...") -> None:
    """Render loading placeholder"""
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"⏳ {message}")


def render_error_message(error: str, suggestion: str = None) -> None:
    """Render error message with optional suggestion"""
    st.error(f"❌ {error}")
    if suggestion:
        st.info(f"💡 {suggestion}")


def render_footer() -> None:
    """Render dashboard footer"""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8em;">
        GraphMemory-IDE Dashboard v1.0.0 | 
        Built with Streamlit & FastAPI | 
        Real-time Analytics Platform
    </div>
    """, unsafe_allow_html=True) 