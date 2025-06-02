"""
Alert Actions Dashboard Components

This module provides Streamlit components for alert acknowledgment, resolution,
and bulk alert operations. It includes interactive UI controls for managing
alert lifecycle and user actions.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa UI patterns + Sequential thinking analysis
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import json

# Constants for alert actions
ACTION_TYPES = ['ACKNOWLEDGE', 'RESOLVE', 'SUPPRESS', 'ESCALATE', 'REASSIGN']
ESCALATION_LEVELS = ['L1_SUPPORT', 'L2_ENGINEERING', 'L3_SENIOR', 'MANAGER', 'EXECUTIVE']
TEAMS = ['ops-team', 'dev-team', 'security-team', 'network-team', 'platform-team']

# Action colors
ACTION_COLORS = {
    'ACKNOWLEDGE': '#ffc107',
    'RESOLVE': '#28a745', 
    'SUPPRESS': '#6c757d',
    'ESCALATE': '#dc3545',
    'REASSIGN': '#17a2b8'
}

# Action icons
ACTION_ICONS = {
    'ACKNOWLEDGE': '✅',
    'RESOLVE': '🔧',
    'SUPPRESS': '🔇',
    'ESCALATE': '🔺',
    'REASSIGN': '👤'
}


def alert_action_panel(alert_id: str, current_status: str = 'ACTIVE') -> None:
    """Individual alert action panel with available actions"""
    
    st.subheader(f"🔧 Alert Actions: {alert_id}")
    
    # Current alert status
    status_col1, status_col2 = st.columns([1, 2])
    
    with status_col1:
        st.write("**Current Status:**")
    
    with status_col2:
        status_color = _get_status_color(current_status)
        st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{current_status}</span>", 
                   unsafe_allow_html=True)
    
    # Available actions based on status
    available_actions = _get_available_actions(current_status)
    
    if not available_actions:
        st.info("No actions available for this alert status")
        return
    
    # Action tabs
    action_tabs = st.tabs([f"{ACTION_ICONS[action]} {action.title()}" for action in available_actions])
    
    for i, action in enumerate(available_actions):
        with action_tabs[i]:
            _render_action_form(alert_id, action, current_status)


def bulk_alert_actions() -> None:
    """Bulk alert operation controls"""
    
    st.subheader("🔄 Bulk Alert Operations")
    
    # Get selected alerts from session state
    if 'selected_alerts' not in st.session_state:
        st.session_state.selected_alerts = set()
    
    selected_count = len(st.session_state.selected_alerts)
    
    if selected_count == 0:
        st.info("No alerts selected. Select alerts from the alert list to perform bulk operations.")
        return
    
    st.info(f"Selected {selected_count} alerts for bulk operations")
    
    # Bulk action selection
    bulk_col1, bulk_col2 = st.columns([1, 2])
    
    with bulk_col1:
        bulk_action = st.selectbox(
            "Bulk Action",
            ['ACKNOWLEDGE', 'RESOLVE', 'SUPPRESS', 'ESCALATE', 'REASSIGN'],
            help="Select action to apply to all selected alerts"
        )
    
    with bulk_col2:
        # Action-specific parameters
        if bulk_action == 'ESCALATE':
            escalation_level = st.selectbox("Escalation Level", ESCALATION_LEVELS)
        elif bulk_action == 'REASSIGN':
            new_team = st.selectbox("Assign to Team", TEAMS)
        else:
            escalation_level = None
            new_team = None
    
    # Bulk action notes
    bulk_notes = st.text_area(
        "Notes (optional)",
        placeholder=f"Add notes for this {bulk_action.lower()} operation..."
    )
    
    # Confirmation and execution
    st.write("**Confirm Bulk Operation:**")
    
    confirm_col1, confirm_col2, confirm_col3 = st.columns([1, 1, 2])
    
    with confirm_col1:
        if st.button(f"{ACTION_ICONS[bulk_action]} Execute {bulk_action.title()}", 
                     type="primary",
                     help=f"Apply {bulk_action.lower()} to {selected_count} selected alerts"):
            # Execute bulk operation
            result = _execute_bulk_operation(
                list(st.session_state.selected_alerts),
                bulk_action,
                bulk_notes,
                escalation_level=escalation_level,
                new_team=new_team
            )
            
            if result['success']:
                st.success(f"Successfully {bulk_action.lower()}ed {result['processed']} alerts")
                if result['failed'] > 0:
                    st.warning(f"{result['failed']} alerts failed to process")
                
                # Clear selection
                st.session_state.selected_alerts.clear()
                st.rerun()
            else:
                st.error(f"Bulk operation failed: {result['error']}")
    
    with confirm_col2:
        if st.button("🗑️ Clear Selection"):
            st.session_state.selected_alerts.clear()
            st.rerun()
    
    with confirm_col3:
        st.caption(f"This action will affect {selected_count} selected alerts")


def alert_workflow_manager() -> None:
    """Alert workflow and automation management"""
    
    st.subheader("⚙️ Alert Workflow Manager")
    
    # Workflow tabs
    workflow_tab1, workflow_tab2, workflow_tab3 = st.tabs([
        "🔄 Auto-Actions", "📝 Templates", "📊 Workflow Stats"
    ])
    
    with workflow_tab1:
        _alert_auto_actions()
    
    with workflow_tab2:
        _alert_action_templates()
    
    with workflow_tab3:
        _alert_workflow_statistics()


def _alert_auto_actions() -> None:
    """Configure automatic alert actions"""
    
    st.write("**Automatic Action Rules**")
    
    # Get current auto-action rules
    auto_rules = _get_auto_action_rules()
    
    # Add new rule
    with st.expander("➕ Add New Auto-Action Rule", expanded=False):
        rule_col1, rule_col2 = st.columns(2)
        
        with rule_col1:
            rule_name = st.text_input("Rule Name", placeholder="e.g., Auto-ack low severity")
            
            # Conditions
            st.write("**Conditions:**")
            severity_condition = st.multiselect("Severity", ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'])
            category_condition = st.multiselect("Category", ['PERFORMANCE', 'AVAILABILITY', 'SECURITY', 'NETWORK'])
            time_condition = st.number_input("After (minutes)", min_value=0, max_value=1440, value=15)
        
        with rule_col2:
            # Actions
            st.write("**Actions:**")
            auto_action = st.selectbox("Action", ['ACKNOWLEDGE', 'SUPPRESS'])
            auto_notes = st.text_area("Auto Notes", placeholder="Automatically processed by rule")
            
            # Rule settings
            st.write("**Settings:**")
            rule_enabled = st.checkbox("Enable Rule", value=True)
            rule_priority = st.number_input("Priority", min_value=1, max_value=10, value=5)
        
        if st.button("💾 Save Auto-Action Rule") and rule_name:
            new_rule = {
                'name': rule_name,
                'enabled': rule_enabled,
                'priority': rule_priority,
                'conditions': {
                    'severity': severity_condition,
                    'category': category_condition,
                    'time_threshold': time_condition
                },
                'action': auto_action,
                'notes': auto_notes
            }
            
            if _save_auto_action_rule(new_rule):
                st.success(f"Auto-action rule '{rule_name}' saved successfully")
                st.rerun()
            else:
                st.error("Failed to save auto-action rule")
    
    # Display existing rules
    if auto_rules:
        st.write("**Existing Auto-Action Rules:**")
        
        for rule in auto_rules:
            with st.container():
                rule_header_col1, rule_header_col2, rule_header_col3 = st.columns([2, 1, 1])
                
                with rule_header_col1:
                    status_icon = "🟢" if rule['enabled'] else "🔴"
                    st.markdown(f"{status_icon} **{rule['name']}**")
                
                with rule_header_col2:
                    st.write(f"Action: {rule['action']}")
                
                with rule_header_col3:
                    if st.button("🗑️ Delete", key=f"delete_rule_{rule['id']}"):
                        if _delete_auto_action_rule(rule['id']):
                            st.success("Rule deleted")
                            st.rerun()
                
                # Rule details
                st.caption(f"Conditions: {', '.join(rule['conditions']['severity'])} severity, "
                          f"{rule['conditions']['time_threshold']}min threshold")
                
                st.divider()
    else:
        st.info("No auto-action rules configured")


def _alert_action_templates() -> None:
    """Manage alert action templates"""
    
    st.write("**Action Templates**")
    
    # Get existing templates
    templates = _get_action_templates()
    
    # Add new template
    with st.expander("➕ Create Action Template", expanded=False):
        template_col1, template_col2 = st.columns(2)
        
        with template_col1:
            template_name = st.text_input("Template Name", placeholder="e.g., Standard Resolution")
            template_action = st.selectbox("Action Type", ACTION_TYPES)
        
        with template_col2:
            template_notes = st.text_area("Default Notes", placeholder="Template notes...")
            template_tags = st.text_input("Tags", placeholder="comma,separated,tags")
        
        if st.button("💾 Save Template") and template_name:
            new_template = {
                'name': template_name,
                'action': template_action,
                'notes': template_notes,
                'tags': [tag.strip() for tag in template_tags.split(',') if tag.strip()]
            }
            
            if _save_action_template(new_template):
                st.success(f"Template '{template_name}' saved successfully")
                st.rerun()
            else:
                st.error("Failed to save template")
    
    # Display existing templates
    if templates:
        st.write("**Existing Templates:**")
        
        template_cols = st.columns(3)
        
        for i, template in enumerate(templates):
            with template_cols[i % 3]:
                with st.container():
                    st.markdown(f"**{template['name']}**")
                    st.caption(f"Action: {template['action']}")
                    
                    if st.button(f"Use Template", key=f"use_template_{template['id']}"):
                        st.session_state.selected_template = template
                        st.success(f"Template '{template['name']}' selected")
                    
                    if st.button(f"🗑️ Delete", key=f"delete_template_{template['id']}"):
                        if _delete_action_template(template['id']):
                            st.success("Template deleted")
                            st.rerun()
    else:
        st.info("No action templates available")


def _alert_workflow_statistics() -> None:
    """Display alert workflow statistics"""
    
    st.write("**Workflow Performance Statistics**")
    
    # Get workflow stats
    stats = _get_workflow_statistics()
    
    # Key metrics
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.metric("Actions Today", stats['actions_today'])
    
    with stats_col2:
        st.metric("Avg Response Time", f"{stats['avg_response_time']:.1f}m")
    
    with stats_col3:
        st.metric("Auto-Actions", f"{stats['auto_action_rate']:.1f}%")
    
    with stats_col4:
        st.metric("Manual Actions", stats['manual_actions'])
    
    # Action distribution chart
    st.subheader("Action Distribution (Last 7 Days)")
    
    action_data = stats['action_distribution']
    if action_data:
        import pandas as pd
        df = pd.DataFrame(list(action_data.items()), columns=['Action', 'Count'])
        st.bar_chart(df.set_index('Action'))
    else:
        st.info("No action distribution data available")
    
    # Response time trends
    st.subheader("Response Time Trends")
    
    response_trends = stats['response_time_trends']
    if response_trends:
        import pandas as pd
        df = pd.DataFrame(response_trends)
        st.line_chart(df.set_index('date'))
    else:
        st.info("No response time trend data available")


def quick_action_bar(alert_ids: List[str]) -> None:
    """Quick action bar for rapid alert processing"""
    
    if not alert_ids:
        return
    
    st.subheader("⚡ Quick Actions")
    
    quick_col1, quick_col2, quick_col3, quick_col4, quick_col5 = st.columns(5)
    
    with quick_col1:
        if st.button("✅ Acknowledge All", help="Acknowledge all visible alerts"):
            result = _execute_bulk_operation(alert_ids, 'ACKNOWLEDGE', 'Bulk acknowledged')
            st.success(f"Acknowledged {result['processed']} alerts")
    
    with quick_col2:
        if st.button("🔧 Resolve All", help="Resolve all visible alerts"):
            result = _execute_bulk_operation(alert_ids, 'RESOLVE', 'Bulk resolved')
            st.success(f"Resolved {result['processed']} alerts")
    
    with quick_col3:
        if st.button("🔇 Suppress All", help="Suppress all visible alerts"):
            result = _execute_bulk_operation(alert_ids, 'SUPPRESS', 'Bulk suppressed')
            st.success(f"Suppressed {result['processed']} alerts")
    
    with quick_col4:
        if st.button("🔺 Escalate All", help="Escalate all visible alerts"):
            result = _execute_bulk_operation(alert_ids, 'ESCALATE', 'Bulk escalated', escalation_level='L2_ENGINEERING')
            st.success(f"Escalated {result['processed']} alerts")
    
    with quick_col5:
        if st.button("📊 Export", help="Export alert data"):
            export_data = _export_alert_data(alert_ids)
            st.download_button("📥 Download CSV", export_data, "alerts.csv", "text/csv")


# Helper functions

def _render_action_form(alert_id: str, action: str, current_status: str) -> None:
    """Render action-specific form"""
    
    st.write(f"**{action.title()} Alert**")
    
    # Common fields
    notes = st.text_area(
        "Notes",
        placeholder=f"Add notes for {action.lower()} action...",
        key=f"{action}_{alert_id}_notes"
    )
    
    # Action-specific fields
    if action == 'ESCALATE':
        escalation_level = st.selectbox(
            "Escalation Level",
            ESCALATION_LEVELS,
            key=f"{action}_{alert_id}_level"
        )
        escalation_reason = st.text_area(
            "Escalation Reason",
            placeholder="Why is this alert being escalated?",
            key=f"{action}_{alert_id}_reason"
        )
    
    elif action == 'REASSIGN':
        new_team = st.selectbox(
            "Assign to Team",
            TEAMS,
            key=f"{action}_{alert_id}_team"
        )
        priority_change = st.selectbox(
            "Change Priority",
            ['Keep Current', 'Increase', 'Decrease'],
            key=f"{action}_{alert_id}_priority"
        )
    
    elif action == 'RESOLVE':
        resolution_category = st.selectbox(
            "Resolution Category",
            ['Fixed', 'Not an Issue', 'Duplicate', 'Configuration Change', 'External Issue'],
            key=f"{action}_{alert_id}_category"
        )
        
        root_cause = st.text_area(
            "Root Cause (optional)",
            placeholder="Describe the root cause...",
            key=f"{action}_{alert_id}_root_cause"
        )
    
    # Action button
    action_color = ACTION_COLORS[action]
    action_icon = ACTION_ICONS[action]
    
    if st.button(
        f"{action_icon} {action.title()} Alert",
        type="primary",
        key=f"{action}_{alert_id}_submit"
    ):
        # Prepare action data
        action_data = {
            'alert_id': alert_id,
            'action': action,
            'notes': notes,
            'user': _get_current_user()
        }
        
        # Add action-specific data
        if action == 'ESCALATE':
            action_data['escalation_level'] = escalation_level
            action_data['escalation_reason'] = escalation_reason
        elif action == 'REASSIGN':
            action_data['new_team'] = new_team
            action_data['priority_change'] = priority_change
        elif action == 'RESOLVE':
            action_data['resolution_category'] = resolution_category
            action_data['root_cause'] = root_cause
        
        # Execute action
        result = _execute_single_action(action_data)
        
        if result['success']:
            st.success(f"Alert {action.lower()}ed successfully")
            st.rerun()
        else:
            st.error(f"Failed to {action.lower()} alert: {result['error']}")


def _get_available_actions(status: str) -> List[str]:
    """Get available actions based on alert status"""
    
    if status == 'ACTIVE':
        return ['ACKNOWLEDGE', 'RESOLVE', 'SUPPRESS', 'ESCALATE', 'REASSIGN']
    elif status == 'ACKNOWLEDGED':
        return ['RESOLVE', 'ESCALATE', 'REASSIGN']
    elif status == 'SUPPRESSED':
        return ['ACKNOWLEDGE', 'RESOLVE']
    else:  # RESOLVED
        return []


def _get_status_color(status: str) -> str:
    """Get color for alert status"""
    
    status_colors = {
        'ACTIVE': '#dc3545',
        'ACKNOWLEDGED': '#ffc107',
        'RESOLVED': '#28a745',
        'SUPPRESSED': '#6c757d'
    }
    
    return status_colors.get(status, '#6c757d')


def _execute_single_action(action_data: Dict) -> Dict[str, Any]:
    """Execute single alert action"""
    
    # Mock implementation
    try:
        # Simulate API call
        return {
            'success': True,
            'alert_id': action_data['alert_id'],
            'action': action_data['action']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _execute_bulk_operation(alert_ids: List[str], action: str, notes: str, **kwargs) -> Dict[str, Any]:
    """Execute bulk alert operation"""
    
    # Mock implementation
    try:
        processed = len(alert_ids)
        failed = 0
        
        # Simulate some failures
        if processed > 10:
            failed = max(1, processed // 20)
            processed -= failed
        
        return {
            'success': True,
            'processed': processed,
            'failed': failed,
            'action': action
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'processed': 0,
            'failed': len(alert_ids)
        }


def _get_auto_action_rules() -> List[Dict]:
    """Get configured auto-action rules"""
    
    # Mock data
    return [
        {
            'id': 'rule-001',
            'name': 'Auto-acknowledge low severity',
            'enabled': True,
            'priority': 5,
            'conditions': {
                'severity': ['LOW', 'INFO'],
                'category': ['PERFORMANCE'],
                'time_threshold': 30
            },
            'action': 'ACKNOWLEDGE',
            'notes': 'Automatically acknowledged low severity alert'
        }
    ]


def _get_action_templates() -> List[Dict]:
    """Get action templates"""
    
    # Mock data
    return [
        {
            'id': 'template-001',
            'name': 'Standard Resolution',
            'action': 'RESOLVE',
            'notes': 'Issue resolved through standard procedure',
            'tags': ['standard', 'resolved']
        }
    ]


def _get_workflow_statistics() -> Dict[str, Any]:
    """Get workflow statistics"""
    
    # Mock data
    return {
        'actions_today': 45,
        'avg_response_time': 12.5,
        'auto_action_rate': 35.2,
        'manual_actions': 29,
        'action_distribution': {
            'ACKNOWLEDGE': 25,
            'RESOLVE': 15,
            'ESCALATE': 3,
            'SUPPRESS': 2
        },
        'response_time_trends': [
            {'date': '2025-01-23', 'avg_time': 15.2},
            {'date': '2025-01-24', 'avg_time': 12.8},
            {'date': '2025-01-25', 'avg_time': 14.1},
            {'date': '2025-01-26', 'avg_time': 11.5},
            {'date': '2025-01-27', 'avg_time': 13.2},
            {'date': '2025-01-28', 'avg_time': 10.8},
            {'date': '2025-01-29', 'avg_time': 12.5}
        ]
    }


def _save_auto_action_rule(rule: Dict) -> bool:
    """Save auto-action rule"""
    # Mock implementation
    return True


def _delete_auto_action_rule(rule_id: str) -> bool:
    """Delete auto-action rule"""
    # Mock implementation
    return True


def _save_action_template(template: Dict) -> bool:
    """Save action template"""
    # Mock implementation
    return True


def _delete_action_template(template_id: str) -> bool:
    """Delete action template"""
    # Mock implementation
    return True


def _get_current_user() -> str:
    """Get current user"""
    # Mock implementation
    return "current_user"


def _export_alert_data(alert_ids: List[str]) -> str:
    """Export alert data as CSV"""
    
    # Mock CSV data
    csv_data = "id,title,severity,status,created_at\n"
    for alert_id in alert_ids:
        csv_data += f"{alert_id},Sample Alert,HIGH,ACTIVE,2025-01-29T10:30:00Z\n"
    
    return csv_data


# Main alert actions dashboard

def alert_actions_dashboard() -> None:
    """Main alert actions and workflow management dashboard"""
    
    st.title("🔧 Alert Actions & Workflow Management")
    
    # Dashboard tabs
    action_tab1, action_tab2, action_tab3 = st.tabs([
        "🔄 Bulk Operations", "⚙️ Workflow Manager", "⚡ Quick Actions"
    ])
    
    with action_tab1:
        bulk_alert_actions()
    
    with action_tab2:
        alert_workflow_manager()
    
    with action_tab3:
        # Quick actions for demo
        sample_alert_ids = ['alert-001', 'alert-002', 'alert-003']
        quick_action_bar(sample_alert_ids)


# Export main functions
__all__ = [
    'alert_actions_dashboard',
    'alert_action_panel',
    'bulk_alert_actions',
    'alert_workflow_manager',
    'quick_action_bar'
] 