"""
Incident Management Dashboard Components

This module provides Streamlit components for visual incident management,
including incident overview, correlation visualization, timeline display,
and incident lifecycle operations.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa visualization patterns + Sequential thinking analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Constants for incident management
INCIDENT_STATUSES = ['OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED', 'REOPENED']
INCIDENT_PRIORITIES = ['P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM', 'P4_LOW', 'P5_INFO']
INCIDENT_CATEGORIES = ['PERFORMANCE', 'AVAILABILITY', 'SECURITY', 'DATA_INTEGRITY', 'CAPACITY', 'NETWORK', 'APPLICATION']

# Priority colors
PRIORITY_COLORS = {
    'P1_CRITICAL': '#dc3545',  # Red
    'P2_HIGH': '#fd7e14',      # Orange
    'P3_MEDIUM': '#ffc107',    # Yellow
    'P4_LOW': '#20c997',       # Teal
    'P5_INFO': '#6c757d'       # Gray
}

# Status icons
INCIDENT_STATUS_ICONS = {
    'OPEN': '🔴',
    'INVESTIGATING': '🔍',
    'RESOLVED': '✅',
    'CLOSED': '🏁',
    'REOPENED': '🔄'
}


def incident_overview_dashboard() -> None:
    """Executive dashboard for incident overview"""
    
    st.subheader("📊 Incident Overview")
    
    # Get incident summary from API
    try:
        # In production, this would call the actual API
        # For now, we'll use mock data
        incident_summary = {
            'total_incidents': 42,
            'open_incidents': 8,
            'investigating': 5,
            'resolved_today': 12,
            'mttr_hours': 2.4,
            'by_priority': {
                'P1_CRITICAL': 2,
                'P2_HIGH': 6,
                'P3_MEDIUM': 15,
                'P4_LOW': 18,
                'P5_INFO': 1
            },
            'by_category': {
                'PERFORMANCE': 12,
                'AVAILABILITY': 8,
                'SECURITY': 3,
                'NETWORK': 10,
                'APPLICATION': 9
            }
        }
    except Exception as e:
        st.error(f"Error loading incident summary: {e}")
        return
    
    # Key metrics cards
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    
    with metric_col1:
        st.metric(
            "Total Incidents",
            incident_summary['total_incidents'],
            delta=f"+{incident_summary.get('delta_total', 0)}"
        )
    
    with metric_col2:
        st.metric(
            "Open",
            incident_summary['open_incidents'],
            delta=f"+{incident_summary.get('delta_open', 0)}",
            delta_color="inverse"
        )
    
    with metric_col3:
        st.metric(
            "Investigating",
            incident_summary['investigating'],
            delta=f"+{incident_summary.get('delta_investigating', 0)}"
        )
    
    with metric_col4:
        st.metric(
            "Resolved Today",
            incident_summary['resolved_today'],
            delta=f"+{incident_summary.get('delta_resolved', 0)}",
            delta_color="normal"
        )
    
    with metric_col5:
        st.metric(
            "MTTR (hours)",
            f"{incident_summary['mttr_hours']:.1f}",
            delta=f"{incident_summary.get('delta_mttr', 0):+.1f}",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Priority and category distribution
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Incidents by Priority")
        priority_data = incident_summary['by_priority']
        if priority_data:
            # Create priority chart
            priority_df = pd.DataFrame(
                list(priority_data.items()),
                columns=['Priority', 'Count']
            )
            st.bar_chart(priority_df.set_index('Priority'))
        else:
            st.info("No priority data available")
    
    with chart_col2:
        st.subheader("Incidents by Category")
        category_data = incident_summary['by_category']
        if category_data:
            # Create category chart
            category_df = pd.DataFrame(
                list(category_data.items()),
                columns=['Category', 'Count']
            )
            st.bar_chart(category_df.set_index('Category'))
        else:
            st.info("No category data available")


def incident_detail_view(incident_id: str) -> None:
    """Detailed incident management interface"""
    
    st.subheader(f"🔍 Incident Details: {incident_id}")
    
    # Get incident details from API
    try:
        # Mock incident data
        incident = {
            'id': incident_id,
            'title': 'High CPU Usage on Production Servers',
            'description': 'Multiple servers showing sustained high CPU usage above 90%',
            'status': 'INVESTIGATING',
            'priority': 'P2_HIGH',
            'category': 'PERFORMANCE',
            'created_at': '2025-01-29T10:30:00Z',
            'acknowledged_at': '2025-01-29T10:32:00Z',
            'investigation_started_at': '2025-01-29T10:35:00Z',
            'assigned_to': 'ops-team',
            'correlation_id': 'corr-12345',
            'alert_ids': ['alert-001', 'alert-002', 'alert-003'],
            'affected_hosts': ['prod-web-01', 'prod-web-02', 'prod-api-01'],
            'timeline': [
                {'timestamp': '2025-01-29T10:30:00Z', 'event': 'Incident created from alert correlation'},
                {'timestamp': '2025-01-29T10:32:00Z', 'event': 'Incident acknowledged by ops-team'},
                {'timestamp': '2025-01-29T10:35:00Z', 'event': 'Investigation started'},
                {'timestamp': '2025-01-29T10:45:00Z', 'event': 'Root cause analysis in progress'}
            ]
        }
    except Exception as e:
        st.error(f"Error loading incident details: {e}")
        return
    
    # Incident header information
    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
    
    with header_col1:
        st.markdown(f"**{incident['title']}**")
        st.caption(f"Created: {_format_timestamp(incident['created_at'])}")
    
    with header_col2:
        priority = incident['priority']
        priority_color = PRIORITY_COLORS.get(priority, '#gray')
        st.markdown(f"<span style='color: {priority_color}; font-weight: bold;'>{priority}</span>", 
                   unsafe_allow_html=True)
    
    with header_col3:
        status = incident['status']
        status_icon = INCIDENT_STATUS_ICONS.get(status, '⚪')
        st.markdown(f"{status_icon} **{status}**")
    
    # Incident details tabs
    detail_tab1, detail_tab2, detail_tab3, detail_tab4 = st.tabs(["Details", "Timeline", "Alerts", "Actions"])
    
    with detail_tab1:
        _display_incident_details(incident)
    
    with detail_tab2:
        _display_incident_timeline(incident)
    
    with detail_tab3:
        _display_incident_alerts(incident)
    
    with detail_tab4:
        _display_incident_actions(incident)


def incident_timeline_display(incidents: List[Dict]) -> None:
    """Visual timeline of incident events"""
    
    st.subheader("📅 Incident Timeline")
    
    if not incidents:
        st.info("No incidents to display in timeline")
        return
    
    # Create timeline visualization
    timeline_data = []
    for incident in incidents:
        timeline_data.append({
            'id': incident['id'],
            'title': incident['title'],
            'created': pd.to_datetime(incident['created_at']),
            'status': incident['status'],
            'priority': incident['priority']
        })
    
    # Convert to DataFrame
    timeline_df = pd.DataFrame(timeline_data)
    timeline_df = timeline_df.sort_values('created', ascending=False)
    
    # Display as interactive timeline
    for _, incident in timeline_df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([0.1, 2, 1, 1])
            
            with col1:
                priority_color = PRIORITY_COLORS.get(incident['priority'], '#gray')
                st.markdown(f"<div style='background-color: {priority_color}; width: 5px; height: 40px; border-radius: 2px;'></div>", 
                          unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{incident['title']}**")
                st.caption(f"ID: {incident['id']} • {_format_timestamp(incident['created'])}")
            
            with col3:
                st.text(incident['priority'])
            
            with col4:
                status_icon = INCIDENT_STATUS_ICONS.get(incident['status'], '⚪')
                st.text(f"{status_icon} {incident['status']}")
            
            if st.button(f"View Details", key=f"view_{incident['id']}"):
                st.session_state.selected_incident = incident['id']
                st.rerun()
            
            st.divider()


def incident_correlation_viewer(correlation_id: str) -> None:
    """Visual display of alert correlations"""
    
    st.subheader(f"🔗 Alert Correlation: {correlation_id}")
    
    # Get correlation details
    try:
        # Mock correlation data
        correlation = {
            'id': correlation_id,
            'strategy': 'TEMPORAL',
            'confidence': 'HIGH',
            'confidence_score': 0.85,
            'alert_count': 5,
            'alerts': [
                {
                    'id': 'alert-001',
                    'title': 'High CPU Usage - prod-web-01',
                    'severity': 'HIGH',
                    'timestamp': '2025-01-29T10:30:00Z',
                    'host': 'prod-web-01'
                },
                {
                    'id': 'alert-002',
                    'title': 'High CPU Usage - prod-web-02',
                    'severity': 'HIGH',
                    'timestamp': '2025-01-29T10:31:00Z',
                    'host': 'prod-web-02'
                },
                {
                    'id': 'alert-003',
                    'title': 'High Memory Usage - prod-web-01',
                    'severity': 'MEDIUM',
                    'timestamp': '2025-01-29T10:32:00Z',
                    'host': 'prod-web-01'
                }
            ],
            'correlation_factors': {
                'temporal_proximity': 0.9,
                'host_similarity': 0.8,
                'metric_correlation': 0.7
            }
        }
    except Exception as e:
        st.error(f"Error loading correlation details: {e}")
        return
    
    # Correlation overview
    overview_col1, overview_col2, overview_col3 = st.columns(3)
    
    with overview_col1:
        st.metric("Strategy", correlation['strategy'])
    
    with overview_col2:
        st.metric("Confidence", correlation['confidence'])
        st.caption(f"Score: {correlation['confidence_score']:.2f}")
    
    with overview_col3:
        st.metric("Alert Count", correlation['alert_count'])
    
    # Correlation factors
    st.subheader("Correlation Factors")
    factors = correlation['correlation_factors']
    
    for factor, score in factors.items():
        st.metric(factor.replace('_', ' ').title(), f"{score:.2f}")
    
    # Correlated alerts
    st.subheader("Correlated Alerts")
    
    for alert in correlation['alerts']:
        with st.container():
            alert_col1, alert_col2, alert_col3, alert_col4 = st.columns([2, 1, 1, 1])
            
            with alert_col1:
                st.markdown(f"**{alert['title']}**")
                st.caption(f"ID: {alert['id']}")
            
            with alert_col2:
                st.text(alert['severity'])
            
            with alert_col3:
                st.text(alert['host'])
            
            with alert_col4:
                st.caption(_format_timestamp(alert['timestamp']))
            
            st.divider()


def incident_management_controls() -> None:
    """Bulk incident management operations"""
    
    st.subheader("🔧 Incident Management")
    
    if 'selected_incidents' not in st.session_state:
        st.session_state.selected_incidents = set()
    
    # Bulk operations
    control_col1, control_col2, control_col3, control_col4 = st.columns(4)
    
    with control_col1:
        if st.button("🔍 Start Investigation", disabled=len(st.session_state.selected_incidents) == 0):
            _bulk_start_investigation(list(st.session_state.selected_incidents))
            st.success(f"Started investigation for {len(st.session_state.selected_incidents)} incidents")
            st.session_state.selected_incidents.clear()
            st.rerun()
    
    with control_col2:
        if st.button("✅ Resolve Selected", disabled=len(st.session_state.selected_incidents) == 0):
            _bulk_resolve_incidents(list(st.session_state.selected_incidents))
            st.success(f"Resolved {len(st.session_state.selected_incidents)} incidents")
            st.session_state.selected_incidents.clear()
            st.rerun()
    
    with control_col3:
        if st.button("🔄 Merge Selected", disabled=len(st.session_state.selected_incidents) < 2):
            _merge_incidents(list(st.session_state.selected_incidents))
            st.success(f"Merged {len(st.session_state.selected_incidents)} incidents")
            st.session_state.selected_incidents.clear()
            st.rerun()
    
    with control_col4:
        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_incidents.clear()
            st.rerun()
    
    # Display current selection
    if st.session_state.selected_incidents:
        st.info(f"Selected: {len(st.session_state.selected_incidents)} incidents")


# Helper functions

def _display_incident_details(incident: Dict) -> None:
    """Display detailed incident information"""
    
    # Basic details
    detail_col1, detail_col2 = st.columns(2)
    
    with detail_col1:
        st.write("**Description:**")
        st.write(incident['description'])
        
        st.write("**Category:**", incident['category'])
        st.write("**Assigned To:**", incident['assigned_to'])
        st.write("**Correlation ID:**", incident['correlation_id'])
    
    with detail_col2:
        st.write("**Status Timeline:**")
        if incident.get('acknowledged_at'):
            st.write(f"• Acknowledged: {_format_timestamp(incident['acknowledged_at'])}")
        if incident.get('investigation_started_at'):
            st.write(f"• Investigation Started: {_format_timestamp(incident['investigation_started_at'])}")
        
        st.write("**Affected Hosts:**")
        for host in incident['affected_hosts']:
            st.write(f"• {host}")


def _display_incident_timeline(incident: Dict) -> None:
    """Display incident timeline events"""
    
    st.write("**Event Timeline:**")
    
    for event in reversed(incident['timeline']):
        event_col1, event_col2 = st.columns([1, 3])
        
        with event_col1:
            st.caption(_format_timestamp(event['timestamp']))
        
        with event_col2:
            st.write(f"• {event['event']}")


def _display_incident_alerts(incident: Dict) -> None:
    """Display related alerts for incident"""
    
    st.write(f"**Related Alerts ({len(incident['alert_ids'])}):**")
    
    for alert_id in incident['alert_ids']:
        alert_col1, alert_col2 = st.columns([2, 1])
        
        with alert_col1:
            st.write(f"• Alert ID: {alert_id}")
        
        with alert_col2:
            if st.button(f"View Alert", key=f"view_alert_{alert_id}"):
                st.session_state.selected_alert = alert_id
                st.rerun()


def _display_incident_actions(incident: Dict) -> None:
    """Display incident action controls"""
    
    st.write("**Available Actions:**")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if incident['status'] in ['OPEN', 'REOPENED']:
            if st.button("🔍 Start Investigation"):
                _start_investigation(incident['id'])
                st.success("Investigation started")
                st.rerun()
    
    with action_col2:
        if incident['status'] in ['INVESTIGATING']:
            if st.button("✅ Resolve Incident"):
                _resolve_incident(incident['id'])
                st.success("Incident resolved")
                st.rerun()
    
    with action_col3:
        if incident['status'] in ['RESOLVED']:
            if st.button("🏁 Close Incident"):
                _close_incident(incident['id'])
                st.success("Incident closed")
                st.rerun()
    
    # Add notes
    st.write("**Add Notes:**")
    notes = st.text_area("Investigation notes", placeholder="Add notes about investigation progress...")
    
    if st.button("💾 Save Notes") and notes:
        _add_incident_notes(incident['id'], notes)
        st.success("Notes added")
        st.rerun()


def _format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp_str


# Incident action functions (mock implementations)

def _bulk_start_investigation(incident_ids: List[str]) -> None:
    """Start investigation for multiple incidents"""
    # Mock implementation
    pass


def _bulk_resolve_incidents(incident_ids: List[str]) -> None:
    """Resolve multiple incidents"""
    # Mock implementation
    pass


def _merge_incidents(incident_ids: List[str]) -> None:
    """Merge multiple incidents"""
    # Mock implementation
    pass


def _start_investigation(incident_id: str) -> None:
    """Start investigation for single incident"""
    # Mock implementation
    pass


def _resolve_incident(incident_id: str) -> None:
    """Resolve single incident"""
    # Mock implementation
    pass


def _close_incident(incident_id: str) -> None:
    """Close single incident"""
    # Mock implementation
    pass


def _add_incident_notes(incident_id: str, notes: str) -> None:
    """Add notes to incident"""
    # Mock implementation
    pass


# Main incident dashboard component

def incident_dashboard() -> None:
    """Main incident management dashboard"""
    
    st.title("🚨 Incident Management Dashboard")
    
    # Overview dashboard
    incident_overview_dashboard()
    
    st.divider()
    
    # Incident management controls
    incident_management_controls()
    
    st.divider()
    
    # If specific incident selected, show details
    if hasattr(st.session_state, 'selected_incident'):
        incident_detail_view(st.session_state.selected_incident)
    else:
        # Show incident timeline
        # In production, this would fetch real incidents
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


# Export main functions
__all__ = [
    'incident_dashboard',
    'incident_overview_dashboard',
    'incident_detail_view',
    'incident_timeline_display',
    'incident_correlation_viewer',
    'incident_management_controls'
] 