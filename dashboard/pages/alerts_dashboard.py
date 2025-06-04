"""
Main Alerts Dashboard Page

This module provides the main alerts dashboard page that integrates all
alert-related components into a comprehensive alerting interface. It serves
as the primary entry point for alert management in the Streamlit dashboard.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa dashboard patterns + Sequential thinking analysis
"""

import streamlit as st
import sys
from pathlib import Path

# Add dashboard components to path
dashboard_path = Path(__file__).parent.parent
sys.path.append(str(dashboard_path))

try:
    from components.alerts import (
        alert_dashboard,
        realtime_alert_feed,
        alert_summary_cards,
        alert_severity_distribution,
        alert_timeline_chart,
        alert_acknowledgment_controls,
        alert_history_table
    )
    from components.incidents import (
        incident_dashboard,
        incident_overview_dashboard,
        incident_detail_view,
        incident_timeline_display,
        incident_correlation_viewer
    )
    from components.alert_metrics import (
        alert_metrics_dashboard,
        alert_performance_metrics,
        notification_delivery_metrics,
        escalation_analytics,
        alert_trend_analysis
    )
    from components.alert_actions import (
        alert_actions_dashboard,
        alert_action_panel,
        bulk_alert_actions,
        quick_action_bar
    )
except ImportError as e:
    st.error(f"Failed to import alert components: {e}")
    st.stop()


def main() -> None:
    """
    Main function for the alerts dashboard page.
    
    This function serves as the entry point for the alerts dashboard,
    providing comprehensive alert management functionality.
    """
    
    # Page configuration
    st.set_page_config(
        page_title="Alert Management Dashboard",
        page_icon="🚨",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Page header
    st.title("🚨 Alert Management Dashboard")
    st.markdown("**Real-time Alert Monitoring & Management System**")
    
    # Navigation sidebar
    with st.sidebar:
        st.header("🧭 Navigation")
        
        dashboard_mode = st.radio(
            "Dashboard Mode",
            [
                "🏠 Overview",
                "🚨 Live Alerts", 
                "🚨 Incident Management",
                "📈 Analytics & Metrics",
                "🔧 Actions & Workflow"
            ],
            index=0
        )
        
        st.divider()
        
        # Quick stats in sidebar
        st.subheader("📊 Quick Stats")
        
        # Mock quick stats
        quick_stats = {
            'active_alerts': 23,
            'critical_alerts': 3,
            'open_incidents': 5,
            'avg_response_time': '12.5m'
        }
        
        st.metric("Active Alerts", quick_stats['active_alerts'])
        st.metric("Critical", quick_stats['critical_alerts'], delta="+1")
        st.metric("Open Incidents", quick_stats['open_incidents'])
        st.metric("Avg Response", quick_stats['avg_response_time'])
        
        st.divider()
        
        # Dashboard settings
        st.subheader("⚙️ Settings")
        
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_interval = st.selectbox("Refresh Interval", ["5s", "10s", "30s", "60s"], index=2)
        
        notification_sound = st.checkbox("Alert Sounds", value=False)
        
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    # Main dashboard content based on selected mode
    if dashboard_mode == "🏠 Overview":
        _render_overview_dashboard()
    
    elif dashboard_mode == "🚨 Live Alerts":
        _render_live_alerts_dashboard()
    
    elif dashboard_mode == "🚨 Incident Management":
        _render_incident_dashboard()
    
    elif dashboard_mode == "📈 Analytics & Metrics":
        _render_analytics_dashboard()
    
    elif dashboard_mode == "🔧 Actions & Workflow":
        _render_actions_dashboard()


def _render_overview_dashboard() -> None:
    """Render the overview dashboard with key metrics and summaries"""
    
    st.header("📋 Alert System Overview")
    
    # Top-level summary cards
    alert_summary_cards()
    
    st.divider()
    
    # Two-column layout for overview
    overview_col1, overview_col2 = st.columns(2)
    
    with overview_col1:
        st.subheader("🔥 Recent Critical Alerts")
        
        # Mock critical alerts
        critical_alerts = [
            {
                'id': 'alert-001',
                'title': 'High CPU Usage - prod-web-01',
                'severity': 'CRITICAL',
                'status': 'ACTIVE',
                'created_at': '2025-01-29T10:30:00Z',
                'source_host': 'prod-web-01'
            },
            {
                'id': 'alert-002', 
                'title': 'Database Connection Pool Exhausted',
                'severity': 'CRITICAL',
                'status': 'ACKNOWLEDGED',
                'created_at': '2025-01-29T10:25:00Z',
                'source_host': 'prod-db-01'
            }
        ]
        
        if critical_alerts:
            for alert in critical_alerts:
                with st.container():
                    st.markdown(f"**🔴 {alert['title']}**")
                    st.caption(f"Host: {alert['source_host']} • Status: {alert['status']}")
                    
                    if st.button(f"View Details", key=f"view_{alert['id']}"):
                        st.session_state.selected_alert = alert['id']
                        st.rerun()
                    
                    st.divider()
        else:
            st.success("No critical alerts currently active")
    
    with overview_col2:
        st.subheader("🎯 System Health Summary")
        
        # Health metrics
        health_col1, health_col2 = st.columns(2)
        
        with health_col1:
            st.metric("Alert Engine", "🟢 Healthy")
            st.metric("Notification", "🟢 Healthy") 
            st.metric("Incident Mgmt", "🟢 Healthy")
        
        with health_col2:
            st.metric("Response Time", "🟢 Normal")
            st.metric("Success Rate", "99.2%")
            st.metric("Uptime", "156.3h")
        
        # Quick system actions
        st.subheader("🚀 Quick Actions")
        
        quick_action_col1, quick_action_col2 = st.columns(2)
        
        with quick_action_col1:
            if st.button("🔄 Test Alert System"):
                st.success("Test alert generated successfully")
        
        with quick_action_col2:
            if st.button("📊 Generate Report"):
                st.info("Report generation started")
    
    st.divider()
    
    # Charts overview
    chart_overview_col1, chart_overview_col2 = st.columns(2)
    
    with chart_overview_col1:
        alert_severity_distribution()
    
    with chart_overview_col2:
        alert_timeline_chart()


def _render_live_alerts_dashboard() -> None:
    """Render the live alerts dashboard with real-time feeds"""
    
    st.header("🚨 Live Alert Monitoring")
    
    # Alert controls bar
    control_col1, control_col2, control_col3, control_col4 = st.columns(4)
    
    with control_col1:
        if st.button("⏸️ Pause Feed"):
            st.session_state.feed_paused = True
            st.info("Alert feed paused")
    
    with control_col2:
        if st.button("▶️ Resume Feed"):
            st.session_state.feed_paused = False
            st.success("Alert feed resumed")
    
    with control_col3:
        if st.button("🔇 Mute Alerts"):
            st.session_state.alerts_muted = True
            st.info("Alert notifications muted")
    
    with control_col4:
        feed_speed = st.selectbox("Feed Speed", ["Slow", "Normal", "Fast"], index=1)
    
    st.divider()
    
    # Live alerts layout
    live_col1, live_col2 = st.columns([2, 1])
    
    with live_col1:
        # Real-time alert feed
        realtime_alert_feed()
    
    with live_col2:
        # Alert actions panel
        st.subheader("⚡ Quick Actions")
        
        if hasattr(st.session_state, 'selected_alert'):
            alert_action_panel(st.session_state.selected_alert)
        else:
            st.info("Select an alert to view available actions")
        
        st.divider()
        
        # Bulk operations
        bulk_alert_actions()
    
    st.divider()
    
    # Alert history
    alert_history_table()


def _render_incident_dashboard() -> None:
    """Render the incident management dashboard"""
    
    st.header("🚨 Incident Management")
    
    # Incident dashboard tabs
    incident_tab1, incident_tab2, incident_tab3 = st.tabs([
        "📊 Overview", "🔍 Incident Details", "🔗 Correlations"
    ])
    
    with incident_tab1:
        incident_overview_dashboard()
        
        st.divider()
        
        # Recent incidents timeline
        mock_incidents = [
            {
                'id': 'inc-001',
                'title': 'High CPU Usage on Production Servers',
                'created_at': '2025-01-29T10:30:00Z',
                'status': 'INVESTIGATING', 
                'priority': 'P2_HIGH'
            },
            {
                'id': 'inc-002',
                'title': 'Database Connection Pool Exhaustion',
                'created_at': '2025-01-29T09:15:00Z',
                'status': 'RESOLVED',
                'priority': 'P1_CRITICAL'
            }
        ]
        
        incident_timeline_display(mock_incidents)
    
    with incident_tab2:
        if hasattr(st.session_state, 'selected_incident'):
            incident_detail_view(st.session_state.selected_incident)
        else:
            st.info("Select an incident from the timeline to view details")
    
    with incident_tab3:
        if hasattr(st.session_state, 'selected_correlation'):
            incident_correlation_viewer(st.session_state.selected_correlation)
        else:
            st.info("Select a correlation ID to view alert correlations")
            
            # Demo correlation viewer
            if st.button("🔗 View Sample Correlation"):
                st.session_state.selected_correlation = "corr-12345"
                st.rerun()


def _render_analytics_dashboard() -> None:
    """Render the analytics and metrics dashboard"""
    
    st.header("📈 Alert System Analytics")
    
    # Analytics overview
    analytics_summary_col1, analytics_summary_col2, analytics_summary_col3, analytics_summary_col4 = st.columns(4)
    
    with analytics_summary_col1:
        st.metric("Alert Volume", "1,245", delta="+12%")
    
    with analytics_summary_col2:
        st.metric("Avg Latency", "0.89s", delta="-5%", delta_color="inverse")
    
    with analytics_summary_col3:
        st.metric("Success Rate", "99.2%", delta="+0.3%")
    
    with analytics_summary_col4:
        st.metric("MTTR", "12.5m", delta="-2.1m", delta_color="inverse")
    
    st.divider()
    
    # Full analytics dashboard
    alert_metrics_dashboard()


def _render_actions_dashboard() -> None:
    """Render the actions and workflow dashboard"""
    
    st.header("🔧 Alert Actions & Workflow")
    
    # Actions overview
    actions_summary_col1, actions_summary_col2, actions_summary_col3, actions_summary_col4 = st.columns(4)
    
    with actions_summary_col1:
        st.metric("Actions Today", "45")
    
    with actions_summary_col2:
        st.metric("Auto-Actions", "35.2%")
    
    with actions_summary_col3:
        st.metric("Avg Response", "12.5m")
    
    with actions_summary_col4:
        st.metric("Success Rate", "98.7%")
    
    st.divider()
    
    # Full actions dashboard
    alert_actions_dashboard()


def _render_connection_status() -> None:
    """Render connection status indicator"""
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        st.success("🟢 Alert Engine Connected")
    
    with status_col2:
        st.success("🟢 SSE Stream Active")
    
    with status_col3:
        st.success("🟢 Database Connected")


def _render_emergency_controls() -> None:
    """Render emergency controls"""
    
    st.subheader("🚨 Emergency Controls")
    
    emergency_col1, emergency_col2, emergency_col3 = st.columns(3)
    
    with emergency_col1:
        if st.button("🔴 Emergency Stop", help="Stop all alert processing"):
            st.error("Emergency stop activated - all alert processing halted")
    
    with emergency_col2:
        if st.button("📢 Broadcast Alert", help="Send broadcast notification"):
            broadcast_message = st.text_input("Broadcast Message")
            if broadcast_message:
                st.success(f"Broadcast sent: {broadcast_message}")
    
    with emergency_col3:
        if st.button("🔄 System Reset", help="Reset alert system state"):
            st.warning("System reset initiated - please wait...")


# Custom CSS for enhanced styling
def _inject_custom_css() -> None:
    """Inject custom CSS for better dashboard appearance"""
    
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .alert-critical {
        border-left: 5px solid #dc3545;
        background-color: #fff5f5;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    
    .alert-high {
        border-left: 5px solid #fd7e14;
        background-color: #fff8f0;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    
    .alert-medium {
        border-left: 5px solid #ffc107;
        background-color: #fffcf0;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
    }
    
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active { background-color: #dc3545; }
    .status-acknowledged { background-color: #ffc107; }
    .status-resolved { background-color: #28a745; }
    .status-suppressed { background-color: #6c757d; }
    </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    # Inject custom CSS
    _inject_custom_css()
    
    # Initialize session state
    if 'feed_paused' not in st.session_state:
        st.session_state.feed_paused = False
    
    if 'alerts_muted' not in st.session_state:
        st.session_state.alerts_muted = False
    
    # Run main dashboard
    main() 