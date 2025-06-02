"""
Dashboard and Analytics API Routes for GraphMemory-IDE

This module provides FastAPI routes for:
- BI Dashboard management
- Real-time analytics
- Alert management
- Data export capabilities

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import pandas as pd

from .bi_dashboard import (
    get_bi_dashboard, 
    Dashboard, 
    DashboardWidget, 
    ChartType, 
    TimeRange, 
    MetricAggregation
)
from .real_time_tracker import get_real_time_tracker, UserActivityType
from .alerting_system import get_alerting_system, AlertRule, AlertSeverity


# Pydantic models for API
class CreateDashboardRequest(BaseModel):
    name: str = Field(..., description="Dashboard name")
    description: str = Field("", description="Dashboard description")
    public: bool = Field(False, description="Whether dashboard is public")
    tags: List[str] = Field(default_factory=list, description="Dashboard tags")


class CreateWidgetRequest(BaseModel):
    title: str = Field(..., description="Widget title")
    description: str = Field("", description="Widget description")
    chart_type: str = Field("line", description="Chart type")
    query: str = Field("", description="Custom SQL query")
    time_range: str = Field("24h", description="Time range")
    aggregation: str = Field("count", description="Aggregation method")
    group_by: List[str] = Field(default_factory=list, description="Group by fields")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters")
    size: Dict[str, int] = Field(default_factory=lambda: {"width": 6, "height": 4})
    position: Dict[str, int] = Field(default_factory=lambda: {"x": 0, "y": 0})


class TrackEventRequest(BaseModel):
    activity_type: str = Field(..., description="Activity type")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID") 
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event data")


class CreateAlertRuleRequest(BaseModel):
    name: str = Field(..., description="Alert rule name")
    description: str = Field("", description="Alert description")
    metric_query: str = Field(..., description="SQL query for metric")
    condition: str = Field("gt", description="Alert condition")
    threshold: float = Field(..., description="Alert threshold")
    severity: str = Field("warning", description="Alert severity")
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    check_interval: int = Field(300, description="Check interval in seconds")
    tags: List[str] = Field(default_factory=list, description="Alert tags")


# Create router
router = APIRouter(prefix="/api/analytics", tags=["Analytics & BI"])


# Dashboard endpoints
@router.get("/dashboards")
async def list_dashboards() -> None:
    """Get list of all dashboards."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    dashboards = []
    for dashboard in bi_dashboard.dashboards.values():
        dashboards.append({
            'dashboard_id': dashboard.dashboard_id,
            'name': dashboard.name,
            'description': dashboard.description,
            'owner_id': dashboard.owner_id,
            'public': dashboard.public,
            'tags': dashboard.tags,
            'widget_count': len(dashboard.widgets),
            'created_at': dashboard.created_at.isoformat(),
            'updated_at': dashboard.updated_at.isoformat()
        })
    
    return {"dashboards": dashboards}


@router.post("/dashboards")
async def create_dashboard(request: CreateDashboardRequest) -> None:
    """Create a new dashboard."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    dashboard = Dashboard(
        name=request.name,
        description=request.description,
        public=request.public,
        tags=request.tags,
        owner_id="current_user"  # Would be replaced with actual user from auth
    )
    
    success = await bi_dashboard.create_dashboard(dashboard)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create dashboard")
    
    return {"dashboard_id": dashboard.dashboard_id, "message": "Dashboard created successfully"}


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str) -> None:
    """Get dashboard with rendered widgets."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    try:
        dashboard_data = await bi_dashboard.get_dashboard_data(dashboard_id)
        return dashboard_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard: {str(e)}")


@router.post("/dashboards/{dashboard_id}/widgets")
async def add_widget_to_dashboard(dashboard_id: str, request: CreateWidgetRequest) -> None:
    """Add a widget to a dashboard."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    if dashboard_id not in bi_dashboard.dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    try:
        widget = DashboardWidget(
            title=request.title,
            description=request.description,
            chart_type=ChartType(request.chart_type),
            query=request.query,
            time_range=TimeRange(request.time_range),
            aggregation=MetricAggregation(request.aggregation),
            group_by=request.group_by,
            filters=request.filters,
            size=request.size,
            position=request.position
        )
        
        dashboard = bi_dashboard.dashboards[dashboard_id]
        dashboard.widgets.append(widget)
        dashboard.updated_at = datetime.utcnow()
        
        # Update in database (simplified)
        await bi_dashboard.create_dashboard(dashboard)
        
        return {"widget_id": widget.widget_id, "message": "Widget added successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid widget configuration: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding widget: {str(e)}")


@router.get("/metrics/real-time")
async def get_real_time_metrics() -> None:
    """Get current real-time metrics."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    try:
        metrics = await bi_dashboard.get_real_time_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")


# Real-time tracking endpoints
@router.post("/track/event")
async def track_event(request: TrackEventRequest) -> None:
    """Track a user activity event."""
    tracker = get_real_time_tracker()
    if not tracker:
        raise HTTPException(status_code=503, detail="Real-time tracker not available")
    
    try:
        activity_type = UserActivityType(request.activity_type)
        await tracker.track_user_activity(
            activity_type=activity_type,
            user_id=request.user_id,
            session_id=request.session_id,
            event_data=request.event_data
        )
        
        return {"message": "Event tracked successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid activity type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking event: {str(e)}")


@router.get("/track/journey/{session_id}")
async def get_user_journey(session_id: str) -> None:
    """Get user journey data for a session."""
    tracker = get_real_time_tracker()
    if not tracker:
        raise HTTPException(status_code=503, detail="Real-time tracker not available")
    
    journey_data = await tracker.get_user_journey(session_id)
    if not journey_data:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    return journey_data


@router.get("/track/metrics/current")
async def get_current_tracking_metrics() -> None:
    """Get current tracking metrics."""
    tracker = get_real_time_tracker()
    if not tracker:
        raise HTTPException(status_code=503, detail="Real-time tracker not available")
    
    try:
        metrics = await tracker.get_current_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tracking metrics: {str(e)}")


# WebSocket endpoint for real-time updates
@router.websocket("/ws/real-time")
async def websocket_real_time_updates(websocket: WebSocket, user_id: Optional[str] = None) -> None:
    """WebSocket endpoint for real-time analytics updates."""
    tracker = get_real_time_tracker()
    if not tracker:
        await websocket.close(code=1011, reason="Real-time tracker not available")
        return
    
    await tracker.websocket_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Handle ping/pong for connection health
            message = json.loads(data)
            if message.get('type') == 'ping':
                await websocket.send_text(json.dumps({'type': 'pong'}))
                
    except WebSocketDisconnect:
        tracker.websocket_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        tracker.websocket_manager.disconnect(websocket)


# Alert management endpoints
@router.get("/alerts/rules")
async def list_alert_rules() -> None:
    """Get list of all alert rules."""
    alerting_system = get_alerting_system()
    if not alerting_system:
        raise HTTPException(status_code=503, detail="Alerting system not available")
    
    rules = []
    for rule in alerting_system.alert_rules.values():
        rules.append(rule.to_dict())
    
    return {"alert_rules": rules}


@router.post("/alerts/rules")
async def create_alert_rule(request: CreateAlertRuleRequest) -> None:
    """Create a new alert rule."""
    alerting_system = get_alerting_system()
    if not alerting_system:
        raise HTTPException(status_code=503, detail="Alerting system not available")
    
    try:
        rule = AlertRule(
            name=request.name,
            description=request.description,
            metric_query=request.metric_query,
            condition=request.condition,
            threshold=request.threshold,
            severity=AlertSeverity(request.severity),
            notification_channels=request.notification_channels,
            check_interval=request.check_interval,
            tags=request.tags,
            owner_id="current_user"  # Would be replaced with actual user from auth
        )
        
        success = await alerting_system.create_alert_rule(rule)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to create alert rule")
        
        return {"rule_id": rule.rule_id, "message": "Alert rule created successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid alert configuration: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating alert rule: {str(e)}")


@router.get("/alerts/active")
async def get_active_alerts() -> None:
    """Get all active alerts."""
    alerting_system = get_alerting_system()
    if not alerting_system:
        raise HTTPException(status_code=503, detail="Alerting system not available")
    
    try:
        alerts = await alerting_system.get_active_alerts()
        return {"active_alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> None:
    """Acknowledge an alert."""
    alerting_system = get_alerting_system()
    if not alerting_system:
        raise HTTPException(status_code=503, detail="Alerting system not available")
    
    success = await alerting_system.acknowledge_alert(alert_id, "current_user")
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> None:
    """Resolve an alert."""
    alerting_system = get_alerting_system()
    if not alerting_system:
        raise HTTPException(status_code=503, detail="Alerting system not available")
    
    success = await alerting_system.resolve_alert(alert_id, "current_user")
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert resolved successfully"}


# Data export endpoints
@router.get("/export/dashboard/{dashboard_id}")
async def export_dashboard_data(
    dashboard_id: str, 
    format: str = "json",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> None:
    """Export dashboard data in various formats."""
    bi_dashboard = get_bi_dashboard()
    if not bi_dashboard:
        raise HTTPException(status_code=503, detail="BI Dashboard service not available")
    
    if dashboard_id not in bi_dashboard.dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    try:
        # Get dashboard data
        dashboard_data = await bi_dashboard.get_dashboard_data(dashboard_id)
        
        if format.lower() == "csv":
            # Convert to CSV format
            csv_data = _convert_dashboard_to_csv(dashboard_data)
            
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=dashboard_{dashboard_id}.csv"}
            )
        elif format.lower() == "json":
            # Return JSON format
            return dashboard_data
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting dashboard: {str(e)}")


@router.get("/export/analytics")
async def export_analytics_data(
    start_date: str,
    end_date: str,
    format: str = "json",
    event_types: Optional[List[str]] = None
) -> None:
    """Export analytics data for a date range."""
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Get analytics data
        bi_dashboard = get_bi_dashboard()
        if not bi_dashboard:
            raise HTTPException(status_code=503, detail="BI Dashboard service not available")
        
        # Build query
        query = f"""
            SELECT event_id, event_type, event_name, timestamp, user_id, 
                   session_id, properties, context
            FROM analytics_events 
            WHERE timestamp BETWEEN '{start_dt.isoformat()}' AND '{end_dt.isoformat()}'
        """
        
        if event_types:
            event_types_str = "', '".join(event_types)
            query += f" AND event_type IN ('{event_types_str}')"
        
        query += " ORDER BY timestamp DESC LIMIT 10000"
        
        # Execute query
        async with bi_dashboard.db_pool.acquire() as conn:
            rows = await conn.fetch(query)
        
        # Convert to desired format
        data = [dict(row) for row in rows]
        
        if format.lower() == "csv":
            # Convert to CSV
            if data:
                df = pd.DataFrame(data)
                csv_data = df.to_csv(index=False)
            else:
                csv_data = "No data found for the specified criteria"
            
            return StreamingResponse(
                iter([csv_data]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=analytics_{start_date}_{end_date}.csv"}
            )
        else:
            return {"data": data, "total_records": len(data)}
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting analytics data: {str(e)}")


# Health and status endpoints
@router.get("/health")
async def get_analytics_health() -> None:
    """Get health status of analytics components."""
    bi_dashboard = get_bi_dashboard()
    tracker = get_real_time_tracker()
    alerting_system = get_alerting_system()
    
    return {
        "status": "healthy",
        "components": {
            "bi_dashboard": "available" if bi_dashboard else "unavailable",
            "real_time_tracker": "available" if tracker else "unavailable", 
            "alerting_system": "available" if alerting_system else "unavailable"
        },
        "metrics": {
            "active_dashboards": len(bi_dashboard.dashboards) if bi_dashboard else 0,
            "active_journeys": len(tracker.active_journeys) if tracker else 0,
            "active_alerts": len(alerting_system.active_alerts) if alerting_system else 0,
            "connected_clients": tracker.websocket_manager.get_active_user_count() if tracker else 0
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# Helper functions
def _convert_dashboard_to_csv(dashboard_data: Dict[str, Any]) -> str:
    """Convert dashboard data to CSV format."""
    try:
        # Extract widget data
        csv_rows = []
        csv_rows.append("Widget,Chart Type,Metric,Value,Timestamp")
        
        for widget_data in dashboard_data.get("rendered_widgets", []):
            widget = widget_data.get("widget", {})
            widget_title = widget.get("title", "Unknown")
            chart_type = widget.get("chart_type", "unknown")
            
            # Try to extract data points
            data = widget_data.get("data", {})
            if isinstance(data, dict) and "data" in data:
                # Plotly chart data
                chart_data = data["data"]
                if isinstance(chart_data, list) and chart_data:
                    for trace in chart_data:
                        if "x" in trace and "y" in trace:
                            x_vals = trace["x"]
                            y_vals = trace["y"]
                            for x, y in zip(x_vals, y_vals):
                                csv_rows.append(f'"{widget_title}","{chart_type}","{x}","{y}","{datetime.utcnow().isoformat()}"')
            else:
                # Simple value
                csv_rows.append(f'"{widget_title}","{chart_type}","value","{data}","{datetime.utcnow().isoformat()}"')
        
        return "\n".join(csv_rows)
        
    except Exception as e:
        return f"Error converting to CSV: {str(e)}" 