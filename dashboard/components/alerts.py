"""
Real-time Alert Dashboard Components

This module provides Streamlit components for displaying and managing alerts
in real-time. It integrates with the Step 8 alerting system to provide
a comprehensive alert management interface within the dashboard.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa Streamlit patterns + Sequential thinking analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import asyncio
import time
from uuid import UUID

# Streamlit specific imports
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.state import get_session_state

# Import dashboard utilities
from ..utils.api_client import get_api_client, APIClient
from ..utils.auth import get_current_user, require_authentication
from ..utils.formatting import format_timestamp, format_duration, get_severity_color

# Constants for alert management
ALERT_SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
ALERT_STATUSES = ['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'SUPPRESSED']
ALERT_CATEGORIES = ['PERFORMANCE', 'AVAILABILITY', 'SECURITY', 'DATA_INTEGRITY', 'CAPACITY', 'NETWORK', 'APPLICATION']

# Color mapping for severity levels
SEVERITY_COLORS = {
    'CRITICAL': '#dc3545',  # Red
    'HIGH': '#fd7e14',      # Orange  
    'MEDIUM': '#ffc107',    # Yellow
    'LOW': '#20c997',       # Teal
    'INFO': '#6c757d'       # Gray
}

# Status icons
STATUS_ICONS = {
    'ACTIVE': '🔴',
    'ACKNOWLEDGED': '🟡', 
    'RESOLVED': '🟢',
    'SUPPRESSED': '⚫'
}


class AlertStreamConnection:
    """Manages SSE connection for real-time alert updates"""
    
    def __init__(self, user_id: str, api_client: APIClient) -> None:
        self.user_id = user_id
        self.api_client = api_client
        self.connected = False
        self.last_event_time = datetime.utcnow()
        
    def connect(self) -> None:
        """Establish SSE connection for alert streaming"""
        try:
            # In a real implementation, this would establish EventSource connection
            # For now, we'll simulate with polling
            self.connected = True
            self.last_event_time = datetime.utcnow()
            return True
        except Exception as e:
            st.error(f"Failed to connect to alert stream: {e}")
            return False
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts from the API"""
        try:
            response = self.api_client.get(f"/alerts/recent?limit={limit}")
            if response.status_code == 200:
                return response.json().get('alerts', [])
            return []
        except Exception as e:
            st.error(f"Error fetching alerts: {e}")
            return []


@st.fragment(run_every=2)
def realtime_alert_feed() -> None:
    """Live alert feed with real-time updates"""
    
    # Get current user and API client
    user = get_current_user()
    if not user:
        st.error("Authentication required")
        return
    
    api_client = get_api_client()
    
    # Initialize alert stream connection
    if 'alert_stream' not in st.session_state:
        st.session_state.alert_stream = AlertStreamConnection(user['user_id'], api_client)
        st.session_state.alert_stream.connect()
    
    # Header with live indicator
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("🚨 Live Alert Feed")
    
    with col2:
        if st.session_state.alert_stream.connected:
            st.success("🟢 Live")
        else:
            st.error("🔴 Disconnected")
    
    with col3:
        if st.button("🔄 Refresh", key="refresh_alerts"):
            st.rerun()
    
    # Alert filters
    with st.expander("🔧 Alert Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            severity_filter = st.multiselect(
                "Severity",
                ALERT_SEVERITIES,
                default=['CRITICAL', 'HIGH', 'MEDIUM'],
                key="severity_filter"
            )
        
        with filter_col2:
            status_filter = st.multiselect(
                "Status", 
                ALERT_STATUSES,
                default=['ACTIVE'],
                key="status_filter"
            )
        
        with filter_col3:
            category_filter = st.multiselect(
                "Category",
                ALERT_CATEGORIES,
                default=ALERT_CATEGORIES,
                key="category_filter"
            )
    
    # Get recent alerts
    alerts = st.session_state.alert_stream.get_recent_alerts(100)
    
    # Apply filters
    if alerts:
        filtered_alerts = []
        for alert in alerts:
            if (alert.get('severity') in severity_filter and
                alert.get('status') in status_filter and
                alert.get('category') in category_filter):
                filtered_alerts.append(alert)
        
        if filtered_alerts:
            _display_alert_cards(filtered_alerts[:10])  # Show top 10
        else:
            st.info("No alerts match the current filters")
    else:
        st.info("No recent alerts found")


def _display_alert_cards(alerts: List[Dict]) -> None:
    """Display alerts as interactive cards"""
    
    for alert in alerts:
        severity = alert.get('severity', 'INFO')
        status = alert.get('status', 'ACTIVE')
        
        # Create alert card with severity-based coloring
        with st.container():
            # Alert header with severity indicator
            col1, col2, col3, col4 = st.columns([0.1, 2, 1, 1])
            
            with col1:
                st.markdown(f"<div style='background-color: {SEVERITY_COLORS[severity]}; width: 5px; height: 50px; border-radius: 2px;'></div>", 
                          unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{alert.get('title', 'Unknown Alert')}**")
                st.caption(f"{STATUS_ICONS[status]} {status} • {alert.get('source_component', 'Unknown')} • {format_timestamp(alert.get('created_at'))}")
            
            with col3:
                severity_color = SEVERITY_COLORS[severity]
                st.markdown(f"<span style='color: {severity_color}; font-weight: bold;'>{severity}</span>", 
                          unsafe_allow_html=True)
            
            with col4:
                if status == 'ACTIVE':
                    if st.button("✅ Acknowledge", key=f"ack_{alert.get('id')}", help="Acknowledge this alert"):
                        _acknowledge_alert(alert.get('id'))
                        st.rerun()
            
            # Alert details
            if alert.get('description'):
                st.write(alert['description'])
            
            # Alert metadata
            metadata_col1, metadata_col2 = st.columns(2)
            with metadata_col1:
                if alert.get('source_host'):
                    st.caption(f"🖥️ Host: {alert['source_host']}")
                if alert.get('rule_id'):
                    st.caption(f"📏 Rule: {alert['rule_id']}")
            
            with metadata_col2:
                if alert.get('value') and alert.get('threshold'):
                    st.caption(f"📊 Value: {alert['value']} (Threshold: {alert['threshold']})")
                if alert.get('correlation_id'):
                    st.caption(f"🔗 Correlation: {alert['correlation_id'][:8]}...")
            
            st.divider()


def alert_summary_cards() -> None:
    """Summary cards showing alert metrics"""
    
    api_client = get_api_client()
    
    # Get alert summary data
    try:
        response = api_client.get("/alerts/summary")
        if response.status_code == 200:
            summary = response.json()
        else:
            summary = {'total': 0, 'by_severity': {}, 'by_status': {}}
    except Exception as e:
        st.error(f"Error loading alert summary: {e}")
        return
    
    # Display summary cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_alerts = summary.get('total', 0)
        st.metric("Total Alerts", total_alerts)
    
    with col2:
        critical_alerts = summary.get('by_severity', {}).get('CRITICAL', 0)
        st.metric("Critical", critical_alerts, delta=None, delta_color="inverse")
    
    with col3:
        high_alerts = summary.get('by_severity', {}).get('HIGH', 0)
        st.metric("High", high_alerts, delta=None, delta_color="inverse")
    
    with col4:
        active_alerts = summary.get('by_status', {}).get('ACTIVE', 0)
        st.metric("Active", active_alerts, delta=None, delta_color="inverse")
    
    with col5:
        acknowledged_alerts = summary.get('by_status', {}).get('ACKNOWLEDGED', 0)
        st.metric("Acknowledged", acknowledged_alerts)


def alert_severity_distribution() -> None:
    """Display alert severity distribution chart"""
    
    api_client = get_api_client()
    
    try:
        response = api_client.get("/alerts/summary")
        if response.status_code == 200:
            summary = response.json()
            severity_data = summary.get('by_severity', {})
        else:
            severity_data = {}
    except Exception as e:
        st.error(f"Error loading severity data: {e}")
        return
    
    if severity_data:
        # Create pie chart for severity distribution
        severities = list(severity_data.keys())
        counts = list(severity_data.values())
        colors = [SEVERITY_COLORS.get(s, '#gray') for s in severities]
        
        fig = go.Figure(data=[go.Pie(
            labels=severities,
            values=counts,
            marker_colors=colors,
            hole=0.4
        )])
        
        fig.update_layout(
            title="Alert Severity Distribution",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alert data available for severity distribution")


def alert_timeline_chart() -> None:
    """Display alert timeline over the last 24 hours"""
    
    api_client = get_api_client()
    
    try:
        # Get hourly alert counts for the last 24 hours
        response = api_client.get("/alerts/timeline?hours=24")
        if response.status_code == 200:
            timeline_data = response.json()
        else:
            timeline_data = []
    except Exception as e:
        st.error(f"Error loading timeline data: {e}")
        return
    
    if timeline_data:
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(timeline_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create line chart
        fig = px.line(df, x='timestamp', y='count', 
                     title='Alert Volume (Last 24 Hours)',
                     labels={'count': 'Number of Alerts', 'timestamp': 'Time'})
        
        fig.update_layout(height=400)
        fig.update_traces(line_color='#dc3545')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No timeline data available")


def alert_acknowledgment_controls() -> None:
    """UI controls for bulk alert operations"""
    
    if 'selected_alerts' not in st.session_state:
        st.session_state.selected_alerts = set()
    
    st.subheader("🔧 Alert Management")
    
    # Bulk operations
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Acknowledge Selected", disabled=len(st.session_state.selected_alerts) == 0):
            _bulk_acknowledge_alerts(list(st.session_state.selected_alerts))
            st.success(f"Acknowledged {len(st.session_state.selected_alerts)} alerts")
            st.session_state.selected_alerts.clear()
            st.rerun()
    
    with col2:
        if st.button("🔇 Suppress Selected", disabled=len(st.session_state.selected_alerts) == 0):
            _bulk_suppress_alerts(list(st.session_state.selected_alerts))
            st.success(f"Suppressed {len(st.session_state.selected_alerts)} alerts")
            st.session_state.selected_alerts.clear()
            st.rerun()
    
    with col3:
        if st.button("✅ Resolve Selected", disabled=len(st.session_state.selected_alerts) == 0):
            _bulk_resolve_alerts(list(st.session_state.selected_alerts))
            st.success(f"Resolved {len(st.session_state.selected_alerts)} alerts")
            st.session_state.selected_alerts.clear()
            st.rerun()
    
    with col4:
        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_alerts.clear()
            st.rerun()
    
    # Display current selection
    if st.session_state.selected_alerts:
        st.info(f"Selected: {len(st.session_state.selected_alerts)} alerts")


def alert_history_table() -> None:
    """Paginated alert history with search and filtering"""
    
    st.subheader("📋 Alert History")
    
    # Search and pagination controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_query = st.text_input("🔍 Search alerts", placeholder="Search by title, description, or host...")
    
    with col2:
        page_size = st.selectbox("Results per page", [10, 25, 50, 100], index=1)
    
    with col3:
        sort_by = st.selectbox("Sort by", ["Created (newest)", "Created (oldest)", "Severity", "Status"])
    
    # Get alert history
    api_client = get_api_client()
    
    try:
        params = {
            'page_size': page_size,
            'search': search_query if search_query else None,
            'sort': sort_by.lower().replace(' ', '_').replace('(', '').replace(')', '')
        }
        
        response = api_client.get("/alerts/history", params=params)
        if response.status_code == 200:
            history_data = response.json()
            alerts = history_data.get('alerts', [])
            total_pages = history_data.get('total_pages', 1)
        else:
            alerts = []
            total_pages = 1
    except Exception as e:
        st.error(f"Error loading alert history: {e}")
        return
    
    if alerts:
        # Create DataFrame for display
        alert_rows = []
        for alert in alerts:
            alert_rows.append({
                'Select': False,
                'Severity': alert.get('severity', 'INFO'),
                'Status': f"{STATUS_ICONS.get(alert.get('status', 'ACTIVE'), '⚪')} {alert.get('status', 'ACTIVE')}",
                'Title': alert.get('title', 'Unknown'),
                'Component': alert.get('source_component', 'Unknown'),
                'Host': alert.get('source_host', 'Unknown'),
                'Created': format_timestamp(alert.get('created_at')),
                'Duration': format_duration(alert.get('created_at'), alert.get('resolved_at')),
                'ID': alert.get('id')
            })
        
        # Display as editable dataframe for selection
        edited_df = st.data_editor(
            pd.DataFrame(alert_rows),
            hide_index=True,
            use_container_width=True,
            column_config={
                'Select': st.column_config.CheckboxColumn('Select'),
                'Severity': st.column_config.TextColumn('Severity'),
                'Status': st.column_config.TextColumn('Status'),
                'Title': st.column_config.TextColumn('Title', width='large'),
                'Component': st.column_config.TextColumn('Component'),
                'Host': st.column_config.TextColumn('Host'),
                'Created': st.column_config.TextColumn('Created'),
                'Duration': st.column_config.TextColumn('Duration'),
                'ID': None  # Hide ID column
            },
            disabled=['Severity', 'Status', 'Title', 'Component', 'Host', 'Created', 'Duration', 'ID']
        )
        
        # Update selected alerts based on checkboxes
        selected_ids = set()
        for idx, row in edited_df.iterrows():
            if row['Select']:
                selected_ids.add(row['ID'])
        
        st.session_state.selected_alerts = selected_ids
        
        # Pagination controls
        if total_pages > 1:
            page_col1, page_col2, page_col3 = st.columns([1, 1, 1])
            with page_col2:
                current_page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                st.caption(f"Page {current_page} of {total_pages}")
    
    else:
        st.info("No alerts found matching the criteria")


def alert_detail_modal(alert_id: str) -> None:
    """Display detailed alert information in a modal-style container"""
    
    api_client = get_api_client()
    
    try:
        response = api_client.get(f"/alerts/{alert_id}")
        if response.status_code == 200:
            alert = response.json()
        else:
            st.error("Alert not found")
            return
    except Exception as e:
        st.error(f"Error loading alert details: {e}")
        return
    
    # Alert detail display
    st.subheader(f"🚨 Alert Details")
    
    # Basic information
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.write("**Title:**", alert.get('title', 'Unknown'))
        st.write("**Severity:**", alert.get('severity', 'INFO'))
        st.write("**Status:**", f"{STATUS_ICONS.get(alert.get('status'), '⚪')} {alert.get('status')}")
        st.write("**Category:**", alert.get('category', 'Unknown'))
    
    with info_col2:
        st.write("**Source Host:**", alert.get('source_host', 'Unknown'))
        st.write("**Component:**", alert.get('source_component', 'Unknown'))
        st.write("**Created:**", format_timestamp(alert.get('created_at')))
        if alert.get('acknowledged_at'):
            st.write("**Acknowledged:**", format_timestamp(alert.get('acknowledged_at')))
    
    # Description
    if alert.get('description'):
        st.write("**Description:**")
        st.write(alert['description'])
    
    # Metrics and values
    if alert.get('current_value') or alert.get('threshold'):
        st.write("**Metrics:**")
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            if alert.get('current_value'):
                st.metric("Current Value", alert['current_value'])
        with metric_col2:
            if alert.get('threshold'):
                st.metric("Threshold", alert['threshold'])
    
    # Timeline and history
    if alert.get('timeline'):
        st.write("**Timeline:**")
        for event in alert['timeline']:
            st.write(f"• {format_timestamp(event['timestamp'])}: {event['event']}")


# Alert action functions

def _acknowledge_alert(alert_id: str) -> None:
    """Acknowledge a single alert"""
    api_client = get_api_client()
    user = get_current_user()
    
    try:
        response = api_client.post(f"/alerts/{alert_id}/acknowledge", 
                                 json={'user': user['username'], 'notes': 'Acknowledged via dashboard'})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error acknowledging alert: {e}")
        return False


def _bulk_acknowledge_alerts(alert_ids: List[str]) -> None:
    """Acknowledge multiple alerts"""
    api_client = get_api_client()
    user = get_current_user()
    
    try:
        response = api_client.post("/alerts/bulk/acknowledge", 
                                 json={'alert_ids': alert_ids, 'user': user['username']})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error bulk acknowledging alerts: {e}")
        return False


def _bulk_suppress_alerts(alert_ids: List[str]) -> None:
    """Suppress multiple alerts"""
    api_client = get_api_client()
    user = get_current_user()
    
    try:
        response = api_client.post("/alerts/bulk/suppress", 
                                 json={'alert_ids': alert_ids, 'user': user['username']})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error bulk suppressing alerts: {e}")
        return False


def _bulk_resolve_alerts(alert_ids: List[str]) -> None:
    """Resolve multiple alerts"""
    api_client = get_api_client()
    user = get_current_user()
    
    try:
        response = api_client.post("/alerts/bulk/resolve", 
                                 json={'alert_ids': alert_ids, 'user': user['username']})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error bulk resolving alerts: {e}")
        return False


# Main alert dashboard component

def alert_dashboard() -> None:
    """Main alert dashboard with all components"""
    
    # Require authentication
    if not require_authentication():
        return
    
    st.title("🚨 Alert Management Dashboard")
    
    # Summary cards at the top
    alert_summary_cards()
    
    st.divider()
    
    # Two column layout for charts and live feed
    chart_col, feed_col = st.columns([1, 1])
    
    with chart_col:
        alert_severity_distribution()
        alert_timeline_chart()
    
    with feed_col:
        realtime_alert_feed()
    
    st.divider()
    
    # Alert management controls
    alert_acknowledgment_controls()
    
    st.divider()
    
    # Alert history table
    alert_history_table()


# Export main functions
__all__ = [
    'alert_dashboard',
    'realtime_alert_feed',
    'alert_summary_cards',
    'alert_severity_distribution',
    'alert_timeline_chart',
    'alert_acknowledgment_controls',
    'alert_history_table',
    'alert_detail_modal'
] 