"""
Server-Sent Events (SSE) Response Models

This module contains Pydantic models for SSE responses using Generic types
for type-safe real-time data streaming to the dashboard.
"""

import json
from typing import Generic, TypeVar, Optional, Dict, Any, Union, cast
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from .validation_models import BaseValidationModel, TimestampStr
from .analytics_models import SystemMetricsData, MemoryInsightsData, GraphMetricsData, AnalyticsStatus

# Generic type variable for SSE response data
T = TypeVar('T')


class SSEEventType(str, Enum):
    """Types of SSE events that can be sent to the dashboard"""
    ANALYTICS = "analytics"
    MEMORY = "memory"
    GRAPH = "graph"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    PERFORMANCE = "performance"


class SSEEvent(BaseValidationModel, Generic[T]):
    """Generic SSE event container for type-safe streaming"""
    
    event_type: SSEEventType = Field(description="Type of SSE event")
    data: T = Field(description="Event data payload")
    timestamp: TimestampStr = Field(description="Event timestamp")
    event_id: Optional[str] = Field(default=None, description="Unique event identifier")
    retry: Optional[int] = Field(default=None, description="Retry interval in milliseconds")
    
    def to_sse_format(self) -> str:
        """Convert to SSE format string for streaming"""
        lines = []
        
        # Add event type
        lines.append(f"event: {self.event_type.value}")
        
        # Add event ID if provided
        if self.event_id:
            lines.append(f"id: {self.event_id}")
        
        # Add retry if provided
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # Add data (JSON serialized)
        data_dict = {
            "data": self.data.model_dump() if hasattr(self.data, 'model_dump') else self.data,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value
        }
        
        data_json = json.dumps(data_dict, default=str)
        lines.append(f"data: {data_json}")
        
        # SSE format requires double newline at the end
        lines.append("")
        lines.append("")
        
        return "\n".join(lines)
    
    @classmethod
    def create_analytics_event(
        cls, 
        data: SystemMetricsData, 
        event_id: Optional[str] = None
    ) -> "SSEEvent[SystemMetricsData]":
        """Create an analytics SSE event"""
        return cast("SSEEvent[SystemMetricsData]", cls(
            event_type=SSEEventType.ANALYTICS,
            data=data,
            timestamp=data.timestamp,
            event_id=event_id
        ))
    
    @classmethod
    def create_memory_event(
        cls, 
        data: MemoryInsightsData, 
        event_id: Optional[str] = None
    ) -> "SSEEvent[MemoryInsightsData]":
        """Create a memory insights SSE event"""
        return cast("SSEEvent[MemoryInsightsData]", cls(
            event_type=SSEEventType.MEMORY,
            data=data,
            timestamp=data.timestamp,
            event_id=event_id
        ))
    
    @classmethod
    def create_graph_event(
        cls, 
        data: GraphMetricsData, 
        event_id: Optional[str] = None
    ) -> "SSEEvent[GraphMetricsData]":
        """Create a graph metrics SSE event"""
        return cast("SSEEvent[GraphMetricsData]", cls(
            event_type=SSEEventType.GRAPH,
            data=data,
            timestamp=data.timestamp,
            event_id=event_id
        ))


class SSEResponse(BaseValidationModel, Generic[T]):
    """Generic SSE response wrapper for consistent API responses"""
    
    success: bool = Field(description="Whether the response is successful")
    data: Optional[T] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: TimestampStr = Field(description="Response timestamp")
    status: AnalyticsStatus = Field(default=AnalyticsStatus.HEALTHY, description="System status")
    
    @classmethod
    def success_response(
        cls, 
        data: T, 
        message: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> "SSEResponse[T]":
        """Create a successful SSE response"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        return cls(
            success=True,
            data=data,
            message=message,
            timestamp=timestamp,
            status=AnalyticsStatus.HEALTHY
        )
    
    @classmethod
    def error_response(
        cls, 
        error: str, 
        message: Optional[str] = None,
        timestamp: Optional[str] = None,
        status: AnalyticsStatus = AnalyticsStatus.ERROR
    ) -> "SSEResponse[None]":
        """Create an error SSE response"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        return cls(
            success=False,
            data=None,
            message=message,
            error=error,
            timestamp=timestamp,
            status=status
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "success": self.success,
            "timestamp": self.timestamp,
            "status": self.status.value
        }
        
        if self.data is not None:
            result["data"] = self.data.dict() if hasattr(self.data, 'dict') else self.data
        
        if self.message:
            result["message"] = self.message
        
        if self.error:
            result["error"] = self.error
        
        return result


# Specialized SSE response types for each data stream
class AnalyticsSSEResponse(SSEResponse[SystemMetricsData]):
    """SSE response specifically for analytics data"""
    
    @classmethod
    def from_metrics(cls, metrics: SystemMetricsData) -> "AnalyticsSSEResponse":
        """Create analytics SSE response from metrics data"""
        response = cls.success_response(
            data=metrics,
            message="Analytics metrics updated",
            timestamp=metrics.timestamp
        )
        return cast("AnalyticsSSEResponse", response)


class MemorySSEResponse(SSEResponse[MemoryInsightsData]):
    """SSE response specifically for memory insights data"""
    
    @classmethod
    def from_insights(cls, insights: MemoryInsightsData) -> "MemorySSEResponse":
        """Create memory SSE response from insights data"""
        response = cls.success_response(
            data=insights,
            message="Memory insights updated",
            timestamp=insights.timestamp
        )
        return cast("MemorySSEResponse", response)


class GraphSSEResponse(SSEResponse[GraphMetricsData]):
    """SSE response specifically for graph metrics data"""
    
    @classmethod
    def from_metrics(cls, metrics: GraphMetricsData) -> "GraphSSEResponse":
        """Create graph SSE response from metrics data"""
        response = cls.success_response(
            data=metrics,
            message="Graph metrics updated",
            timestamp=metrics.timestamp
        )
        return cast("GraphSSEResponse", response)


class ErrorSSEResponse(SSEResponse[None]):
    """SSE response specifically for error conditions"""
    
    @classmethod
    def from_exception(
        cls, 
        exception: Exception, 
        context: Optional[str] = None
    ) -> "ErrorSSEResponse":
        """Create error SSE response from exception"""
        error_msg = f"{type(exception).__name__}: {str(exception)}"
        if context:
            error_msg = f"{context} - {error_msg}"
        
        response = cls.error_response(
            error=error_msg,
            message="An error occurred during data processing",
            status=AnalyticsStatus.ERROR
        )
        return cast("ErrorSSEResponse", response)
    
    @classmethod
    def analytics_unavailable(cls) -> "ErrorSSEResponse":
        """Create error response for analytics engine unavailability"""
        response = cls.error_response(
            error="Analytics engine is currently unavailable",
            message="Using fallback data",
            status=AnalyticsStatus.UNAVAILABLE
        )
        return cast("ErrorSSEResponse", response)
    
    @classmethod
    def validation_error(cls, validation_errors: list[str]) -> "ErrorSSEResponse":
        """Create error response for validation failures"""
        error_msg = "Validation failed: " + "; ".join(validation_errors)
        response = cls.error_response(
            error=error_msg,
            message="Data validation failed",
            status=AnalyticsStatus.ERROR
        )
        return cast("ErrorSSEResponse", response)


# Heartbeat and status models
class HeartbeatData(BaseValidationModel):
    """Heartbeat data for connection health monitoring"""
    
    server_time: TimestampStr = Field(description="Server timestamp")
    uptime_seconds: float = Field(description="Server uptime in seconds")
    active_connections: int = Field(default=0, description="Number of active SSE connections")
    last_data_update: TimestampStr = Field(description="Timestamp of last data update")
    status: AnalyticsStatus = Field(description="Overall system status")


class StatusData(BaseValidationModel):
    """System status data for dashboard health monitoring"""
    
    analytics_engine_status: AnalyticsStatus = Field(description="Analytics engine status")
    memory_system_status: AnalyticsStatus = Field(description="Memory system status")
    graph_system_status: AnalyticsStatus = Field(description="Graph system status")
    sse_server_status: AnalyticsStatus = Field(description="SSE server status")
    last_health_check: TimestampStr = Field(description="Last health check timestamp")
    error_count: int = Field(default=0, description="Number of recent errors")
    warning_count: int = Field(default=0, description="Number of recent warnings")


# Specialized event types
HeartbeatEvent = SSEEvent[HeartbeatData]
StatusEvent = SSEEvent[StatusData]
AnalyticsEvent = SSEEvent[SystemMetricsData]
MemoryEvent = SSEEvent[MemoryInsightsData]
GraphEvent = SSEEvent[GraphMetricsData]


# Utility functions for creating SSE events
def create_heartbeat_event(
    uptime_seconds: float,
    active_connections: int,
    last_data_update: str,
    status: AnalyticsStatus = AnalyticsStatus.HEALTHY
) -> HeartbeatEvent:
    """Create a heartbeat SSE event"""
    timestamp = datetime.now().isoformat()
    
    heartbeat_data = HeartbeatData(
        server_time=timestamp,
        uptime_seconds=uptime_seconds,
        active_connections=active_connections,
        last_data_update=last_data_update,
        status=status
    )
    
    return SSEEvent(
        event_type=SSEEventType.HEARTBEAT,
        data=heartbeat_data,
        timestamp=timestamp
    )


def create_status_event(
    analytics_status: AnalyticsStatus,
    memory_status: AnalyticsStatus,
    graph_status: AnalyticsStatus,
    sse_status: AnalyticsStatus,
    error_count: int = 0,
    warning_count: int = 0
) -> StatusEvent:
    """Create a status SSE event"""
    timestamp = datetime.now().isoformat()
    
    status_data = StatusData(
        analytics_engine_status=analytics_status,
        memory_system_status=memory_status,
        graph_system_status=graph_status,
        sse_server_status=sse_status,
        last_health_check=timestamp,
        error_count=error_count,
        warning_count=warning_count
    )
    
    return SSEEvent(
        event_type=SSEEventType.STATUS,
        data=status_data,
        timestamp=timestamp
    )


# Stream formatting utilities
class SSEFormatter:
    """Utility class for formatting SSE streams"""
    
    @staticmethod
    def format_event(event: SSEEvent[Any]) -> str:
        """Format an SSE event for streaming"""
        return event.to_sse_format()
    
    @staticmethod
    def format_data_only(data: Dict[str, Any], event_type: str = "data") -> str:
        """Format raw data as SSE event"""
        lines = [
            f"event: {event_type}",
            f"data: {json.dumps(data, default=str)}",
            "",
            ""
        ]
        return "\n".join(lines)
    
    @staticmethod
    def format_error(error_message: str, event_id: Optional[str] = None) -> str:
        """Format an error as SSE event"""
        lines = ["event: error"]
        
        if event_id:
            lines.append(f"id: {event_id}")
        
        error_data = {
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }
        
        lines.extend([
            f"data: {json.dumps(error_data)}",
            "",
            ""
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_heartbeat() -> str:
        """Format a simple heartbeat event"""
        heartbeat_data = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "server": "healthy"
        }
        
        return SSEFormatter.format_data_only(heartbeat_data, "heartbeat") 