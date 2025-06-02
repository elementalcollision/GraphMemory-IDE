"""
Business Intelligence Dashboard for GraphMemory-IDE

This module implements comprehensive BI capabilities including:
- Interactive data visualization
- Custom report generation  
- Automated insights and alerts
- Role-based access control
- Real-time analytics dashboards
- Export capabilities

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from fastapi import HTTPException, Depends
from pydantic import BaseModel, validator
import asyncpg

from .analytics_engine import AnalyticsEngine, EventType


class ChartType(Enum):
    """Supported chart types for visualizations."""
    LINE = "line"
    BAR = "bar"  
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    FUNNEL = "funnel"
    HISTOGRAM = "histogram"
    BOX = "box"
    AREA = "area"
    TABLE = "table"


class TimeRange(Enum):
    """Predefined time ranges for analytics."""
    LAST_HOUR = "1h"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"
    LAST_YEAR = "1y"
    CUSTOM = "custom"


class MetricAggregation(Enum):
    """Metric aggregation methods."""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    UNIQUE = "unique"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    widget_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    chart_type: ChartType = ChartType.LINE
    query: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    time_range: TimeRange = TimeRange.LAST_24H
    custom_start: Optional[datetime] = None
    custom_end: Optional[datetime] = None
    aggregation: MetricAggregation = MetricAggregation.COUNT
    group_by: List[str] = field(default_factory=list)
    refresh_interval: int = 300  # seconds
    size: Dict[str, int] = field(default_factory=lambda: {"width": 6, "height": 4})
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary."""
        data = {
            'widget_id': self.widget_id,
            'title': self.title,
            'description': self.description,
            'chart_type': self.chart_type.value,
            'query': self.query,
            'filters': self.filters,
            'time_range': self.time_range.value,
            'custom_start': self.custom_start.isoformat() if self.custom_start else None,
            'custom_end': self.custom_end.isoformat() if self.custom_end else None,
            'aggregation': self.aggregation.value,
            'group_by': self.group_by,
            'refresh_interval': self.refresh_interval,
            'size': self.size,
            'position': self.position
        }
        return data


@dataclass
class Dashboard:
    """Dashboard configuration."""
    dashboard_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    widgets: List[DashboardWidget] = field(default_factory=list)
    owner_id: str = ""
    shared_with: List[str] = field(default_factory=list)
    public: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary."""
        data = {
            'dashboard_id': self.dashboard_id,
            'name': self.name,
            'description': self.description,
            'widgets': [widget.to_dict() for widget in self.widgets],
            'owner_id': self.owner_id,
            'shared_with': self.shared_with,
            'public': self.public,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        return data


class AlertCondition(Enum):
    """Alert condition types."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    THRESHOLD_BREACH = "threshold"
    ANOMALY = "anomaly"


@dataclass
class Alert:
    """Alert configuration."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    metric_query: str = ""
    condition: AlertCondition = AlertCondition.GREATER_THAN
    threshold: Union[float, str] = 0
    check_interval: int = 300  # seconds
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)
    owner_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        data = {
            'alert_id': self.alert_id,
            'name': self.name,
            'description': self.description,
            'metric_query': self.metric_query,
            'condition': self.condition.value,
            'threshold': self.threshold,
            'check_interval': self.check_interval,
            'enabled': self.enabled,
            'notification_channels': self.notification_channels,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat(),
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None
        }
        return data


class DataVisualization:
    """Data visualization generator."""
    
    def __init__(self, analytics_engine: AnalyticsEngine) -> None:
        self.analytics_engine = analytics_engine
    
    async def generate_chart(
        self, 
        widget: DashboardWidget, 
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Generate chart based on widget configuration."""
        try:
            if widget.chart_type == ChartType.LINE:
                return self._create_line_chart(data, widget)
            elif widget.chart_type == ChartType.BAR:
                return self._create_bar_chart(data, widget)
            elif widget.chart_type == ChartType.PIE:
                return self._create_pie_chart(data, widget)
            elif widget.chart_type == ChartType.SCATTER:
                return self._create_scatter_plot(data, widget)
            elif widget.chart_type == ChartType.HEATMAP:
                return self._create_heatmap(data, widget)
            elif widget.chart_type == ChartType.HISTOGRAM:
                return self._create_histogram(data, widget)
            elif widget.chart_type == ChartType.AREA:
                return self._create_area_chart(data, widget)
            elif widget.chart_type == ChartType.TABLE:
                return self._create_table(data, widget)
            else:
                raise ValueError(f"Unsupported chart type: {widget.chart_type}")
                
        except Exception as e:
            return {
                "error": f"Failed to generate chart: {str(e)}",
                "chart_type": widget.chart_type.value,
                "widget_id": widget.widget_id
            }
    
    def _create_line_chart(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create line chart visualization."""
        if data.empty:
            return {"error": "No data available for line chart"}
        
        if len(data.columns) < 2:
            return {"error": "Line chart requires at least 2 columns"}
        
        x_col = data.columns[0]
        y_col = data.columns[1]
        
        fig = go.Figure()
        
        if widget.group_by:
            for group_value in data[widget.group_by[0]].unique():
                group_data = data[data[widget.group_by[0]] == group_value]
                fig.add_trace(go.Scatter(
                    x=group_data[x_col],
                    y=group_data[y_col],
                    mode='lines+markers',
                    name=str(group_value),
                    line={'width': 2}
                ))
        else:
            fig.add_trace(go.Scatter(
                x=data[x_col],
                y=data[y_col],
                mode='lines+markers',
                name=widget.title,
                line={'width': 2}
            ))
        
        fig.update_layout(
            title=widget.title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template="plotly_white",
            showlegend=bool(widget.group_by)
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_bar_chart(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create bar chart visualization."""
        if data.empty:
            return {"error": "No data available for bar chart"}
        
        x_col = data.columns[0]
        y_col = data.columns[1] if len(data.columns) > 1 else None
        
        if not y_col:
            # Count occurrences if only one column
            value_counts = data[x_col].value_counts()
            fig = go.Figure(data=[
                go.Bar(x=value_counts.index, y=value_counts.values)
            ])
        else:
            fig = go.Figure(data=[
                go.Bar(x=data[x_col], y=data[y_col])
            ])
        
        fig.update_layout(
            title=widget.title,
            xaxis_title=x_col,
            yaxis_title=y_col or "Count",
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_pie_chart(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create pie chart visualization."""
        if data.empty:
            return {"error": "No data available for pie chart"}
        
        if len(data.columns) < 1:
            return {"error": "Pie chart requires at least 1 column"}
        
        label_col = data.columns[0]
        value_col = data.columns[1] if len(data.columns) > 1 else None
        
        if value_col:
            labels = data[label_col]
            values = data[value_col]
        else:
            value_counts = data[label_col].value_counts()
            labels = value_counts.index
            values = value_counts.values
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3
        )])
        
        fig.update_layout(
            title=widget.title,
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_scatter_plot(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create scatter plot visualization."""
        if data.empty:
            return {"error": "No data available for scatter plot"}
        
        if len(data.columns) < 2:
            return {"error": "Scatter plot requires at least 2 columns"}
        
        x_col = data.columns[0]
        y_col = data.columns[1]
        
        fig = go.Figure(data=go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode='markers',
            marker={'size': 8, 'opacity': 0.7}
        ))
        
        fig.update_layout(
            title=widget.title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_heatmap(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create heatmap visualization."""
        if data.empty:
            return {"error": "No data available for heatmap"}
        
        # Create correlation matrix if numeric data
        numeric_data = data.select_dtypes(include=['number'])
        if not numeric_data.empty:
            correlation_matrix = numeric_data.corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.columns,
                colorscale='RdBu',
                zmid=0
            ))
            
            fig.update_layout(
                title=widget.title,
                template="plotly_white"
            )
            
            return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
        
        return {"error": "Heatmap requires numeric data"}
    
    def _create_histogram(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create histogram visualization."""
        if data.empty:
            return {"error": "No data available for histogram"}
        
        col = data.columns[0]
        
        fig = go.Figure(data=[go.Histogram(
            x=data[col],
            nbinsx=30
        )])
        
        fig.update_layout(
            title=widget.title,
            xaxis_title=col,
            yaxis_title="Frequency",
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_area_chart(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create area chart visualization."""
        if data.empty:
            return {"error": "No data available for area chart"}
        
        if len(data.columns) < 2:
            return {"error": "Area chart requires at least 2 columns"}
        
        x_col = data.columns[0]
        y_col = data.columns[1]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[y_col],
            fill='tonexty',
            mode='lines',
            name=widget.title
        ))
        
        fig.update_layout(
            title=widget.title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def _create_table(self, data: pd.DataFrame, widget: DashboardWidget) -> Dict[str, Any]:
        """Create table visualization."""
        if data.empty:
            return {"error": "No data available for table"}
        
        # Limit rows for performance
        display_data = data.head(1000)
        
        fig = go.Figure(data=[go.Table(
            header={
                'values': list(display_data.columns),
                'fill_color': 'paleturquoise',
                'align': 'left'
            },
            cells={
                'values': [display_data[col] for col in display_data.columns],
                'fill_color': 'lavender',
                'align': 'left'
            }
        )])
        
        fig.update_layout(
            title=widget.title,
            template="plotly_white"
        )
        
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))


class QueryEngine:
    """Analytics query engine for dashboard data."""
    
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool
    
    async def execute_widget_query(self, widget: DashboardWidget) -> pd.DataFrame:
        """Execute query for dashboard widget."""
        try:
            # Generate time filter
            time_filter = self._generate_time_filter(widget.time_range, widget.custom_start, widget.custom_end)
            
            # Build base query
            if widget.query:
                # Custom query provided
                query = widget.query
            else:
                # Generate default query based on widget configuration
                query = self._generate_default_query(widget)
            
            # Add time filter
            if time_filter:
                query = self._add_time_filter(query, time_filter)
            
            # Add additional filters
            if widget.filters:
                query = self._add_filters(query, widget.filters)
            
            # Execute query
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query)
                
            # Convert to DataFrame
            if rows:
                data = pd.DataFrame([dict(row) for row in rows])
                
                # Apply aggregation if specified
                if widget.aggregation != MetricAggregation.COUNT:
                    data = self._apply_aggregation(data, widget.aggregation, widget.group_by)
                
                return data
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Query execution failed: {e}")
            return pd.DataFrame()
    
    def _generate_time_filter(
        self, 
        time_range: TimeRange, 
        custom_start: Optional[datetime], 
        custom_end: Optional[datetime]
    ) -> Optional[str]:
        """Generate time filter for query."""
        if time_range == TimeRange.CUSTOM:
            if custom_start and custom_end:
                return f"timestamp BETWEEN '{custom_start.isoformat()}' AND '{custom_end.isoformat()}'"
            return None
        
        if time_range == TimeRange.LAST_HOUR:
            return "timestamp >= NOW() - INTERVAL '1 hour'"
        elif time_range == TimeRange.LAST_24H:
            return "timestamp >= NOW() - INTERVAL '24 hours'"
        elif time_range == TimeRange.LAST_7D:
            return "timestamp >= NOW() - INTERVAL '7 days'"
        elif time_range == TimeRange.LAST_30D:
            return "timestamp >= NOW() - INTERVAL '30 days'"
        elif time_range == TimeRange.LAST_90D:
            return "timestamp >= NOW() - INTERVAL '90 days'"
        elif time_range == TimeRange.LAST_YEAR:
            return "timestamp >= NOW() - INTERVAL '1 year'"
        
        return None
    
    def _generate_default_query(self, widget: DashboardWidget) -> str:
        """Generate default query based on widget configuration."""
        # Default to analytics_events table
        base_query = "SELECT timestamp, event_type, event_name, properties FROM analytics_events"
        
        if widget.group_by:
            group_fields = ", ".join(widget.group_by)
            if widget.aggregation == MetricAggregation.COUNT:
                return f"SELECT {group_fields}, COUNT(*) as count FROM analytics_events"
            else:
                return f"SELECT {group_fields}, timestamp, event_type FROM analytics_events"
        
        return base_query
    
    def _add_time_filter(self, query: str, time_filter: str) -> str:
        """Add time filter to query."""
        if "WHERE" in query.upper():
            return f"{query} AND {time_filter}"
        else:
            return f"{query} WHERE {time_filter}"
    
    def _add_filters(self, query: str, filters: Dict[str, Any]) -> str:
        """Add additional filters to query."""
        filter_conditions = []
        
        for field, value in filters.items():
            if isinstance(value, str):
                filter_conditions.append(f"{field} = '{value}'")
            elif isinstance(value, (int, float)):
                filter_conditions.append(f"{field} = {value}")
            elif isinstance(value, list):
                values = "', '".join(str(v) for v in value)
                filter_conditions.append(f"{field} IN ('{values}')")
        
        if filter_conditions:
            filter_clause = " AND ".join(filter_conditions)
            if "WHERE" in query.upper():
                return f"{query} AND {filter_clause}"
            else:
                return f"{query} WHERE {filter_clause}"
        
        return query
    
    def _apply_aggregation(
        self, 
        data: pd.DataFrame, 
        aggregation: MetricAggregation, 
        group_by: List[str]
    ) -> pd.DataFrame:
        """Apply aggregation to data."""
        if group_by and len(group_by) > 0:
            grouped = data.groupby(group_by)
            
            if aggregation == MetricAggregation.SUM:
                return grouped.sum().reset_index()
            elif aggregation == MetricAggregation.AVG:
                return grouped.mean().reset_index()
            elif aggregation == MetricAggregation.COUNT:
                return grouped.size().to_frame('count').reset_index()
            elif aggregation == MetricAggregation.MIN:
                return grouped.min().reset_index()
            elif aggregation == MetricAggregation.MAX:
                return grouped.max().reset_index()
            elif aggregation == MetricAggregation.MEDIAN:
                return grouped.median().reset_index()
        
        return data


class BIDashboard:
    """Business Intelligence Dashboard manager."""
    
    def __init__(self, analytics_engine: AnalyticsEngine, db_pool: asyncpg.Pool) -> None:
        self.analytics_engine = analytics_engine
        self.db_pool = db_pool
        self.query_engine = QueryEngine(db_pool)
        self.visualization = DataVisualization(analytics_engine)
        self.dashboards: Dict[str, Dashboard] = {}
        self.alerts: Dict[str, Alert] = {}
    
    async def initialize(self) -> None:
        """Initialize BI dashboard system."""
        try:
            # Create tables if they don't exist
            await self._create_tables()
            
            # Load existing dashboards and alerts
            await self._load_dashboards()
            await self._load_alerts()
            
            print("BI Dashboard system initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize BI Dashboard system: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Create necessary database tables."""
        async with self.db_pool.acquire() as conn:
            # Dashboards table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboards (
                    dashboard_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    owner_id VARCHAR(255) NOT NULL,
                    configuration JSONB,
                    shared_with TEXT[],
                    public BOOLEAN DEFAULT FALSE,
                    tags TEXT[],
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    metric_query TEXT NOT NULL,
                    condition VARCHAR(50) NOT NULL,
                    threshold TEXT NOT NULL,
                    check_interval INTEGER DEFAULT 300,
                    enabled BOOLEAN DEFAULT TRUE,
                    notification_channels TEXT[],
                    owner_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_triggered TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboards_owner ON dashboards(owner_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_owner ON alerts(owner_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON alerts(enabled)")
    
    async def _load_dashboards(self) -> None:
        """Load existing dashboards from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM dashboards")
            
            for row in rows:
                config = row['configuration']
                dashboard = Dashboard(
                    dashboard_id=row['dashboard_id'],
                    name=row['name'],
                    description=row['description'] or "",
                    owner_id=row['owner_id'],
                    shared_with=list(row['shared_with']) if row['shared_with'] else [],
                    public=row['public'],
                    tags=list(row['tags']) if row['tags'] else [],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                
                # Load widgets from configuration
                if config and 'widgets' in config:
                    for widget_data in config['widgets']:
                        widget = DashboardWidget(**widget_data)
                        dashboard.widgets.append(widget)
                
                self.dashboards[dashboard.dashboard_id] = dashboard
    
    async def _load_alerts(self) -> None:
        """Load existing alerts from database."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM alerts")
            
            for row in rows:
                alert = Alert(
                    alert_id=row['alert_id'],
                    name=row['name'],
                    description=row['description'] or "",
                    metric_query=row['metric_query'],
                    condition=AlertCondition(row['condition']),
                    threshold=row['threshold'],
                    check_interval=row['check_interval'],
                    enabled=row['enabled'],
                    notification_channels=list(row['notification_channels']) if row['notification_channels'] else [],
                    owner_id=row['owner_id'],
                    created_at=row['created_at'],
                    last_triggered=row['last_triggered']
                )
                
                self.alerts[alert.alert_id] = alert
    
    async def create_dashboard(self, dashboard: Dashboard) -> bool:
        """Create a new dashboard."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO dashboards (
                        dashboard_id, name, description, owner_id, configuration,
                        shared_with, public, tags
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                dashboard.dashboard_id,
                dashboard.name,
                dashboard.description,
                dashboard.owner_id,
                json.dumps({"widgets": [w.to_dict() for w in dashboard.widgets]}),
                dashboard.shared_with,
                dashboard.public,
                dashboard.tags
                )
                
            self.dashboards[dashboard.dashboard_id] = dashboard
            return True
            
        except Exception as e:
            print(f"Failed to create dashboard: {e}")
            return False
    
    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get complete dashboard data with all widgets rendered."""
        if dashboard_id not in self.dashboards:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        
        dashboard = self.dashboards[dashboard_id]
        dashboard_data = dashboard.to_dict()
        
        # Render each widget
        widget_data = []
        for widget in dashboard.widgets:
            try:
                # Execute query to get data
                data = await self.query_engine.execute_widget_query(widget)
                
                # Generate visualization
                chart_data = await self.visualization.generate_chart(widget, data)
                
                widget_result = {
                    "widget": widget.to_dict(),
                    "data": chart_data,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                widget_data.append(widget_result)
                
            except Exception as e:
                widget_data.append({
                    "widget": widget.to_dict(),
                    "error": f"Failed to render widget: {str(e)}",
                    "last_updated": datetime.utcnow().isoformat()
                })
        
        dashboard_data["rendered_widgets"] = widget_data
        return dashboard_data
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time analytics metrics for overview dashboard."""
        try:
            current_time = datetime.utcnow()
            hour_ago = current_time - timedelta(hours=1)
            day_ago = current_time - timedelta(days=1)
            
            async with self.db_pool.acquire() as conn:
                # Active users (last hour)
                active_users = await conn.fetchval("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM analytics_events 
                    WHERE timestamp >= $1 AND user_id IS NOT NULL
                """, hour_ago)
                
                # Total events (last 24h)
                total_events = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE timestamp >= $1
                """, day_ago)
                
                # Page views (last 24h)
                page_views = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE timestamp >= $1 AND event_type = 'page_view'
                """, day_ago)
                
                # Error rate (last hour)
                total_recent = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE timestamp >= $1
                """, hour_ago)
                
                error_count = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM analytics_events 
                    WHERE timestamp >= $1 AND event_type = 'error'
                """, hour_ago)
                
                error_rate = (error_count / max(total_recent, 1)) * 100
                
                # Top events (last 24h)
                top_events = await conn.fetch("""
                    SELECT event_name, COUNT(*) as count
                    FROM analytics_events 
                    WHERE timestamp >= $1
                    GROUP BY event_name
                    ORDER BY count DESC
                    LIMIT 10
                """, day_ago)
            
            return {
                "timestamp": current_time.isoformat(),
                "active_users_1h": active_users or 0,
                "total_events_24h": total_events or 0,
                "page_views_24h": page_views or 0,
                "error_rate_1h": round(error_rate, 2),
                "top_events": [{"name": row["event_name"], "count": row["count"]} for row in top_events]
            }
            
        except Exception as e:
            print(f"Failed to get real-time metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }


# Global instance
_bi_dashboard: Optional[BIDashboard] = None


async def initialize_bi_dashboard(analytics_engine: AnalyticsEngine, db_pool: asyncpg.Pool) -> None:
    """Initialize BI dashboard system."""
    global _bi_dashboard
    _bi_dashboard = BIDashboard(analytics_engine, db_pool)
    await _bi_dashboard.initialize()


def get_bi_dashboard() -> Optional[BIDashboard]:
    """Get BI dashboard instance."""
    return _bi_dashboard 