"""
Alert Metrics Dashboard Components

This module provides Streamlit components for displaying real-time alert system
performance metrics, analytics, and monitoring dashboards. It visualizes
alerting system health, performance trends, and operational metrics.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa metrics visualization patterns + Sequential thinking analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Constants for metrics display
METRIC_TIMEFRAMES = ['1h', '6h', '24h', '7d', '30d']
CHART_COLORS = {
    'primary': '#1f77b4',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8'
}


def alert_performance_metrics() -> None:
    """Real-time alert system performance dashboard"""
    
    st.subheader("⚡ Alert System Performance")
    
    # Time range selector
    time_col1, time_col2 = st.columns([1, 3])
    
    with time_col1:
        timeframe = st.selectbox("Time Range", METRIC_TIMEFRAMES, index=2)
    
    with time_col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=True)
    
    # Get performance metrics
    try:
        # Mock performance data
        performance_metrics = {
            'alert_generation_rate': {
                'current': 125.4,
                'average': 98.7,
                'peak': 340.2,
                'trend': '+12%'
            },
            'alert_processing_latency': {
                'p50': 0.23,
                'p95': 0.89,
                'p99': 1.45,
                'trend': '-5%'
            },
            'notification_delivery_rate': {
                'success_rate': 99.2,
                'failed_rate': 0.8,
                'retry_rate': 2.1,
                'trend': '+0.3%'
            },
            'system_health': {
                'cpu_usage': 34.5,
                'memory_usage': 67.2,
                'disk_usage': 45.8,
                'uptime_hours': 156.3
            }
        }
    except Exception as e:
        st.error(f"Error loading performance metrics: {e}")
        return
    
    # Key performance indicators
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        gen_rate = performance_metrics['alert_generation_rate']
        st.metric(
            "Alert Generation Rate",
            f"{gen_rate['current']:.1f}/min",
            delta=gen_rate['trend'],
            help="Current alerts generated per minute"
        )
    
    with kpi_col2:
        latency = performance_metrics['alert_processing_latency']
        st.metric(
            "Processing Latency (P95)",
            f"{latency['p95']:.2f}s",
            delta=latency['trend'],
            delta_color="inverse",
            help="95th percentile alert processing time"
        )
    
    with kpi_col3:
        delivery = performance_metrics['notification_delivery_rate']
        st.metric(
            "Notification Success Rate",
            f"{delivery['success_rate']:.1f}%",
            delta=delivery['trend'],
            help="Successful notification deliveries"
        )
    
    with kpi_col4:
        health = performance_metrics['system_health']
        st.metric(
            "System Uptime",
            f"{health['uptime_hours']:.1f}h",
            help="Continuous system operation time"
        )
    
    # Performance trends chart
    st.subheader("📈 Performance Trends")
    
    # Generate mock time series data
    time_series_data = _generate_mock_timeseries(timeframe)
    
    chart_tab1, chart_tab2, chart_tab3 = st.tabs(["Alert Volume", "Latency", "Success Rate"])
    
    with chart_tab1:
        if time_series_data:
            df = pd.DataFrame(time_series_data['alert_volume'])
            st.line_chart(df.set_index('timestamp'))
        else:
            st.info("No alert volume data available")
    
    with chart_tab2:
        if time_series_data:
            df = pd.DataFrame(time_series_data['latency'])
            st.line_chart(df.set_index('timestamp'))
        else:
            st.info("No latency data available")
    
    with chart_tab3:
        if time_series_data:
            df = pd.DataFrame(time_series_data['success_rate'])
            st.line_chart(df.set_index('timestamp'))
        else:
            st.info("No success rate data available")


def notification_delivery_metrics() -> None:
    """Multi-channel notification delivery analytics"""
    
    st.subheader("📬 Notification Delivery Analytics")
    
    # Get delivery metrics
    try:
        # Mock delivery data
        delivery_metrics = {
            'by_channel': {
                'WebSocket': {'sent': 1245, 'delivered': 1243, 'failed': 2, 'avg_latency': 0.15},
                'Email': {'sent': 456, 'delivered': 442, 'failed': 14, 'avg_latency': 2.34},
                'Webhook': {'sent': 234, 'delivered': 229, 'failed': 5, 'avg_latency': 1.87},
                'Slack': {'sent': 123, 'delivered': 121, 'failed': 2, 'avg_latency': 0.92}
            },
            'failure_reasons': {
                'Network timeout': 12,
                'Invalid endpoint': 5,
                'Rate limit exceeded': 3,
                'Authentication failed': 2,
                'Service unavailable': 1
            },
            'delivery_times': {
                'under_1s': 78.5,
                '1s_to_5s': 18.2,
                '5s_to_30s': 2.8,
                'over_30s': 0.5
            }
        }
    except Exception as e:
        st.error(f"Error loading delivery metrics: {e}")
        return
    
    # Channel performance overview
    channel_data = delivery_metrics['by_channel']
    
    # Create summary table
    channel_rows = []
    for channel, stats in channel_data.items():
        success_rate = (stats['delivered'] / stats['sent'] * 100) if stats['sent'] > 0 else 0
        channel_rows.append({
            'Channel': channel,
            'Sent': stats['sent'],
            'Delivered': stats['delivered'],
            'Failed': stats['failed'],
            'Success Rate': f"{success_rate:.1f}%",
            'Avg Latency': f"{stats['avg_latency']:.2f}s"
        })
    
    st.dataframe(
        pd.DataFrame(channel_rows),
        use_container_width=True,
        hide_index=True
    )
    
    # Delivery metrics charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Failure Reasons")
        failure_data = delivery_metrics['failure_reasons']
        if failure_data:
            failure_df = pd.DataFrame(
                list(failure_data.items()),
                columns=['Reason', 'Count']
            )
            st.bar_chart(failure_df.set_index('Reason'))
        else:
            st.info("No failure data available")
    
    with chart_col2:
        st.subheader("Delivery Time Distribution")
        time_data = delivery_metrics['delivery_times']
        if time_data:
            time_df = pd.DataFrame(
                list(time_data.items()),
                columns=['Time Range', 'Percentage']
            )
            st.bar_chart(time_df.set_index('Time Range'))
        else:
            st.info("No delivery time data available")


def escalation_analytics() -> None:
    """Escalation policy effectiveness analysis"""
    
    st.subheader("🔄 Escalation Analytics")
    
    # Get escalation metrics
    try:
        # Mock escalation data
        escalation_metrics = {
            'escalation_stats': {
                'total_escalations': 67,
                'avg_escalation_time': 15.3,
                'escalation_rate': 5.2,
                'prevented_escalations': 23
            },
            'by_severity': {
                'CRITICAL': {'escalated': 8, 'total': 15, 'rate': 53.3},
                'HIGH': {'escalated': 23, 'total': 89, 'rate': 25.8},
                'MEDIUM': {'escalated': 36, 'total': 234, 'rate': 15.4},
                'LOW': {'escalated': 0, 'total': 123, 'rate': 0.0}
            },
            'response_times': {
                'first_response': {
                    'target': 5.0,
                    'actual': 3.2,
                    'compliance': 94.5
                },
                'escalation_response': {
                    'target': 15.0,
                    'actual': 12.8,
                    'compliance': 87.3
                }
            },
            'escalation_reasons': {
                'No acknowledgment': 45,
                'No resolution in SLA': 18,
                'Manual escalation': 4
            }
        }
    except Exception as e:
        st.error(f"Error loading escalation metrics: {e}")
        return
    
    # Escalation overview metrics
    stats = escalation_metrics['escalation_stats']
    
    escalation_col1, escalation_col2, escalation_col3, escalation_col4 = st.columns(4)
    
    with escalation_col1:
        st.metric(
            "Total Escalations",
            stats['total_escalations'],
            help="Total number of escalated alerts"
        )
    
    with escalation_col2:
        st.metric(
            "Avg Escalation Time",
            f"{stats['avg_escalation_time']:.1f}m",
            help="Average time to escalation"
        )
    
    with escalation_col3:
        st.metric(
            "Escalation Rate",
            f"{stats['escalation_rate']:.1f}%",
            help="Percentage of alerts that escalate"
        )
    
    with escalation_col4:
        st.metric(
            "Prevented Escalations",
            stats['prevented_escalations'],
            help="Escalations prevented by early response"
        )
    
    # Escalation by severity chart
    st.subheader("Escalation by Severity")
    
    severity_data = escalation_metrics['by_severity']
    severity_rows = []
    
    for severity, data in severity_data.items():
        severity_rows.append({
            'Severity': severity,
            'Escalated': data['escalated'],
            'Total': data['total'],
            'Rate': f"{data['rate']:.1f}%"
        })
    
    st.dataframe(
        pd.DataFrame(severity_rows),
        use_container_width=True,
        hide_index=True
    )
    
    # Response time compliance
    st.subheader("Response Time Compliance")
    
    response_data = escalation_metrics['response_times']
    
    compliance_col1, compliance_col2 = st.columns(2)
    
    with compliance_col1:
        first_response = response_data['first_response']
        st.metric(
            "First Response Time",
            f"{first_response['actual']:.1f}m",
            delta=f"Target: {first_response['target']:.1f}m"
        )
        st.progress(first_response['compliance'] / 100)
        st.caption(f"{first_response['compliance']:.1f}% compliance")
    
    with compliance_col2:
        escalation_response = response_data['escalation_response']
        st.metric(
            "Escalation Response Time",
            f"{escalation_response['actual']:.1f}m",
            delta=f"Target: {escalation_response['target']:.1f}m"
        )
        st.progress(escalation_response['compliance'] / 100)
        st.caption(f"{escalation_response['compliance']:.1f}% compliance")


def alert_trend_analysis() -> None:
    """Historical alert trends and patterns"""
    
    st.subheader("📊 Alert Trend Analysis")
    
    # Time period selector
    period_col1, period_col2 = st.columns([1, 3])
    
    with period_col1:
        analysis_period = st.selectbox(
            "Analysis Period",
            ['7 days', '30 days', '90 days', '1 year'],
            index=1
        )
    
    # Get trend data
    try:
        # Mock trend data
        trend_data = {
            'daily_counts': _generate_daily_trend_data(analysis_period),
            'hourly_patterns': _generate_hourly_pattern_data(),
            'category_trends': {
                'PERFORMANCE': [45, 52, 38, 61, 47, 55, 49],
                'AVAILABILITY': [23, 18, 29, 25, 31, 22, 27],
                'SECURITY': [5, 8, 3, 7, 6, 9, 4],
                'NETWORK': [12, 15, 11, 18, 14, 16, 13]
            },
            'severity_trends': {
                'CRITICAL': [3, 5, 2, 8, 4, 6, 3],
                'HIGH': [18, 23, 15, 27, 21, 25, 19],
                'MEDIUM': [42, 38, 47, 35, 44, 39, 43],
                'LOW': [22, 19, 28, 21, 25, 23, 26]
            }
        }
    except Exception as e:
        st.error(f"Error loading trend data: {e}")
        return
    
    # Daily trend chart
    st.subheader(f"Daily Alert Trends ({analysis_period})")
    
    daily_data = trend_data['daily_counts']
    if daily_data:
        df = pd.DataFrame(daily_data)
        st.line_chart(df.set_index('date'))
    else:
        st.info("No daily trend data available")
    
    # Pattern analysis
    trend_tab1, trend_tab2, trend_tab3 = st.tabs(["Hourly Patterns", "Category Trends", "Severity Trends"])
    
    with trend_tab1:
        st.subheader("Hourly Alert Patterns")
        hourly_data = trend_data['hourly_patterns']
        if hourly_data:
            df = pd.DataFrame(hourly_data)
            st.bar_chart(df.set_index('hour'))
        else:
            st.info("No hourly pattern data available")
    
    with trend_tab2:
        st.subheader("Category Trends (Last 7 Days)")
        category_data = trend_data['category_trends']
        if category_data:
            df = pd.DataFrame(category_data)
            st.line_chart(df)
        else:
            st.info("No category trend data available")
    
    with trend_tab3:
        st.subheader("Severity Trends (Last 7 Days)")
        severity_data = trend_data['severity_trends']
        if severity_data:
            df = pd.DataFrame(severity_data)
            st.line_chart(df)
        else:
            st.info("No severity trend data available")
    
    # Trend insights
    st.subheader("📈 Trend Insights")
    
    insights = _generate_trend_insights(trend_data)
    for insight in insights:
        st.info(f"💡 {insight}")


def alert_sla_dashboard() -> None:
    """SLA compliance and performance dashboard"""
    
    st.subheader("📋 SLA Compliance Dashboard")
    
    # Get SLA metrics
    try:
        # Mock SLA data
        sla_metrics = {
            'overall_compliance': 94.2,
            'by_severity': {
                'CRITICAL': {'target': 99.0, 'actual': 97.8, 'incidents': 15},
                'HIGH': {'target': 95.0, 'actual': 96.2, 'incidents': 89},
                'MEDIUM': {'target': 90.0, 'actual': 92.1, 'incidents': 234},
                'LOW': {'target': 80.0, 'actual': 94.5, 'incidents': 123}
            },
            'response_times': {
                'CRITICAL': {'target': 5, 'actual': 3.2, 'compliance': 98.5},
                'HIGH': {'target': 15, 'actual': 12.8, 'compliance': 94.3},
                'MEDIUM': {'target': 60, 'actual': 45.2, 'compliance': 89.7},
                'LOW': {'target': 240, 'actual': 156.8, 'compliance': 92.1}
            },
            'breach_reasons': {
                'Resource unavailable': 8,
                'Complex investigation': 5,
                'External dependency': 3,
                'Escalation delay': 2
            }
        }
    except Exception as e:
        st.error(f"Error loading SLA metrics: {e}")
        return
    
    # Overall compliance metric
    st.metric(
        "Overall SLA Compliance",
        f"{sla_metrics['overall_compliance']:.1f}%",
        help="Overall SLA compliance across all severity levels"
    )
    
    # SLA compliance by severity
    st.subheader("SLA Compliance by Severity")
    
    compliance_data = sla_metrics['by_severity']
    compliance_rows = []
    
    for severity, data in compliance_data.items():
        compliance_rows.append({
            'Severity': severity,
            'Target': f"{data['target']:.1f}%",
            'Actual': f"{data['actual']:.1f}%",
            'Incidents': data['incidents'],
            'Status': '✅' if data['actual'] >= data['target'] else '❌'
        })
    
    st.dataframe(
        pd.DataFrame(compliance_rows),
        use_container_width=True,
        hide_index=True
    )
    
    # Response time compliance
    st.subheader("Response Time Compliance")
    
    response_data = sla_metrics['response_times']
    
    for severity, data in response_data.items():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.write(f"**{severity}**")
        
        with col2:
            st.progress(data['compliance'] / 100)
            st.caption(f"Target: {data['target']}m | Actual: {data['actual']:.1f}m")
        
        with col3:
            st.write(f"{data['compliance']:.1f}%")
    
    # SLA breach analysis
    st.subheader("SLA Breach Analysis")
    
    breach_data = sla_metrics['breach_reasons']
    if breach_data:
        breach_df = pd.DataFrame(
            list(breach_data.items()),
            columns=['Reason', 'Count']
        )
        st.bar_chart(breach_df.set_index('Reason'))
    else:
        st.info("No SLA breach data available")


# Helper functions for generating mock data

def _generate_mock_timeseries(timeframe: str) -> Dict[str, List[Dict]]:
    """Generate mock time series data for charts"""
    
    # Determine time range
    if timeframe == '1h':
        periods = 60
        freq = 'T'  # Minutes
    elif timeframe == '6h':
        periods = 72
        freq = '5T'  # 5 minutes
    elif timeframe == '24h':
        periods = 96
        freq = '15T'  # 15 minutes
    elif timeframe == '7d':
        periods = 168
        freq = 'H'  # Hours
    else:  # 30d
        periods = 30
        freq = 'D'  # Days
    
    # Generate timestamps
    end_time = datetime.utcnow()
    timestamps = pd.date_range(end=end_time, periods=periods, freq=freq)
    
    # Generate mock data
    alert_volume = []
    latency = []
    success_rate = []
    
    for i, ts in enumerate(timestamps):
        # Simulate realistic patterns
        base_volume = 50 + 20 * (i % 24) / 24  # Daily pattern
        alert_volume.append({
            'timestamp': ts.isoformat(),
            'count': max(0, base_volume + (i % 7) * 5)  # Weekly variation
        })
        
        base_latency = 0.5 + 0.3 * (i % 12) / 12  # Semi-daily pattern
        latency.append({
            'timestamp': ts.isoformat(),
            'latency': max(0.1, base_latency + (i % 5) * 0.1)
        })
        
        base_success = 95 + 3 * (i % 6) / 6  # Pattern variation
        success_rate.append({
            'timestamp': ts.isoformat(),
            'success_rate': min(100, max(85, base_success))
        })
    
    return {
        'alert_volume': alert_volume,
        'latency': latency,
        'success_rate': success_rate
    }


def _generate_daily_trend_data(period: str) -> List[Dict]:
    """Generate daily trend data"""
    
    if period == '7 days':
        days = 7
    elif period == '30 days':
        days = 30
    elif period == '90 days':
        days = 90
    else:  # 1 year
        days = 365
    
    daily_data = []
    end_date = datetime.utcnow().date()
    
    for i in range(days):
        date = end_date - timedelta(days=i)
        # Simulate realistic daily counts
        base_count = 85 + 15 * (i % 7) / 7  # Weekly pattern
        count = max(0, base_count + (i % 14) * 5)  # Bi-weekly variation
        
        daily_data.append({
            'date': date.isoformat(),
            'alerts': int(count)
        })
    
    return list(reversed(daily_data))


def _generate_hourly_pattern_data() -> List[Dict]:
    """Generate hourly pattern data"""
    
    hourly_data = []
    
    for hour in range(24):
        # Simulate realistic hourly patterns (higher during business hours)
        if 9 <= hour <= 17:  # Business hours
            base_count = 15 + 10 * (hour - 9) / 8
        elif 18 <= hour <= 22:  # Evening
            base_count = 20 - 5 * (hour - 18) / 4
        else:  # Night/early morning
            base_count = 5 + 3 * abs(hour - 3) / 3
        
        hourly_data.append({
            'hour': f"{hour:02d}:00",
            'average_alerts': max(1, int(base_count))
        })
    
    return hourly_data


def _generate_trend_insights(trend_data: Dict) -> List[str]:
    """Generate trend insights based on data"""
    
    insights = [
        "Alert volume has increased by 12% compared to last period",
        "Performance alerts show a decreasing trend (-8% week over week)",
        "Peak alert times are between 10 AM and 2 PM",
        "Weekend alert volumes are 35% lower than weekdays",
        "Critical alerts have maintained stable levels with no significant spikes"
    ]
    
    return insights


# Main alert metrics dashboard

def alert_metrics_dashboard() -> None:
    """Main alert metrics and analytics dashboard"""
    
    st.title("📈 Alert System Analytics")
    
    # Dashboard tabs
    metrics_tab1, metrics_tab2, metrics_tab3, metrics_tab4, metrics_tab5 = st.tabs([
        "Performance", "Delivery", "Escalation", "Trends", "SLA"
    ])
    
    with metrics_tab1:
        alert_performance_metrics()
    
    with metrics_tab2:
        notification_delivery_metrics()
    
    with metrics_tab3:
        escalation_analytics()
    
    with metrics_tab4:
        alert_trend_analysis()
    
    with metrics_tab5:
        alert_sla_dashboard()


# Export main functions
__all__ = [
    'alert_metrics_dashboard',
    'alert_performance_metrics',
    'notification_delivery_metrics',
    'escalation_analytics',
    'alert_trend_analysis',
    'alert_sla_dashboard'
] 