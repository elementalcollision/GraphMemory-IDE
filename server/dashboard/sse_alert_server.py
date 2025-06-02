"""
Enhanced SSE Server with Alert Event Streaming

This module extends the existing SSE server infrastructure to provide real-time
alert and incident event streaming to the Streamlit dashboard. It integrates
seamlessly with the Step 8 alerting system components while maintaining
backwards compatibility with the existing dashboard streaming.

Created as part of Step 8 Phase 5: Dashboard Integration & Comprehensive Testing
Research foundation: Exa + Sequential Thinking + Context7 integration patterns
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, AsyncGenerator, Callable
from uuid import UUID
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import time

from fastapi import Request, Depends
from sse_starlette import EventSourceResponse
from starlette.responses import Response

from .sse_server import SSEDataProvider, SSEEventManager, get_sse_manager
from .models.alert_models import Alert, AlertStatus, AlertSeverity, AlertCategory
from .alert_engine import get_alert_engine, AlertEngine
from .alert_manager import get_alert_manager, AlertManager
from .notification_dispatcher import get_notification_dispatcher, NotificationDispatcher
from .alert_correlator import get_alert_correlator, AlertCorrelator, CorrelationResult
from .incident_manager import get_incident_manager, IncidentManager, Incident
from .enhanced_circuit_breaker import get_circuit_breaker_manager

# Configure logging
logger = logging.getLogger(__name__)


class AlertEventType(str, Enum):
    """Alert event types for SSE streaming"""
    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_ESCALATED = "alert_escalated"
    ALERT_EXPIRED = "alert_expired"
    
    INCIDENT_CREATED = "incident_created"
    INCIDENT_ACKNOWLEDGED = "incident_acknowledged"
    INCIDENT_RESOLVED = "incident_resolved"
    INCIDENT_MERGED = "incident_merged"
    
    CORRELATION_FOUND = "correlation_found"
    METRICS_UPDATE = "metrics_update"
    SYSTEM_HEALTH = "system_health"


@dataclass
class AlertEvent:
    """Alert event data for SSE streaming"""
    event_type: AlertEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    alert_id: Optional[UUID] = None
    incident_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    
    # Event-specific data
    severity: Optional[AlertSeverity] = None
    category: Optional[AlertCategory] = None
    title: str = ""
    description: str = ""
    source_host: Optional[str] = None
    source_component: Optional[str] = None
    
    # User interaction data
    user: Optional[str] = None
    notes: Optional[str] = None
    
    # Metrics data
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'alert_id': str(self.alert_id) if self.alert_id else None,
            'incident_id': str(self.incident_id) if self.incident_id else None,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'severity': self.severity.value if self.severity else None,
            'category': self.category.value if self.category else None,
            'title': self.title,
            'description': self.description,
            'source_host': self.source_host,
            'source_component': self.source_component,
            'user': self.user,
            'notes': self.notes,
            'metrics': self.metrics,
            'metadata': self.metadata
        }


@dataclass
class AlertStreamConfig:
    """Configuration for alert event streams"""
    user_id: str
    severity_filter: Optional[Set[AlertSeverity]] = None
    category_filter: Optional[Set[AlertCategory]] = None
    component_filter: Optional[Set[str]] = None
    include_incidents: bool = True
    include_correlations: bool = True
    include_metrics: bool = True
    max_events_per_minute: int = 100
    buffer_size: int = 1000


class AlertEventStream:
    """Real-time alert event stream for individual users"""
    
    def __init__(self, config: AlertStreamConfig) -> None:
        self.config = config
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=config.buffer_size)
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.events_sent = 0
        self.rate_limit_reset = datetime.utcnow() + timedelta(minutes=1)
        self.events_this_minute = 0
        
    async def send_event(self, event: AlertEvent) -> bool:
        """Send event to stream if it passes filters"""
        try:
            # Check rate limiting
            now = datetime.utcnow()
            if now > self.rate_limit_reset:
                self.events_this_minute = 0
                self.rate_limit_reset = now + timedelta(minutes=1)
            
            if self.events_this_minute >= self.config.max_events_per_minute:
                logger.warning(f"Rate limit exceeded for user {self.config.user_id}")
                return False
            
            # Apply filters
            if not self._passes_filters(event):
                return False
            
            # Send event
            if not self.event_queue.full():
                await self.event_queue.put(event)
                self.events_sent += 1
                self.events_this_minute += 1
                self.last_activity = now
                return True
            else:
                logger.warning(f"Event queue full for user {self.config.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending event to stream: {e}")
            return False
    
    def _passes_filters(self, event: AlertEvent) -> bool:
        """Check if event passes user-configured filters"""
        # Severity filter
        if (self.config.severity_filter and 
            event.severity and 
            event.severity not in self.config.severity_filter):
            return False
        
        # Category filter
        if (self.config.category_filter and 
            event.category and 
            event.category not in self.config.category_filter):
            return False
        
        # Component filter
        if (self.config.component_filter and 
            event.source_component and 
            event.source_component not in self.config.component_filter):
            return False
        
        # Event type filters
        if (not self.config.include_incidents and 
            event.event_type.value.startswith('incident_')):
            return False
            
        if (not self.config.include_correlations and 
            event.event_type == AlertEventType.CORRELATION_FOUND):
            return False
            
        if (not self.config.include_metrics and 
            event.event_type == AlertEventType.METRICS_UPDATE):
            return False
        
        return True
    
    async def get_events(self) -> AsyncGenerator[AlertEvent, None]:
        """Get events from the stream"""
        while True:
            try:
                # Use timeout to allow for cleanup checks
                event = await asyncio.wait_for(self.event_queue.get(), timeout=5.0)
                yield event
            except asyncio.TimeoutError:
                # Check if stream should be closed due to inactivity
                if datetime.utcnow() - self.last_activity > timedelta(hours=1):
                    logger.info(f"Closing inactive stream for user {self.config.user_id}")
                    break
            except Exception as e:
                logger.error(f"Error getting events from stream: {e}")
                break


class AlertEventSSEServer:
    """Enhanced SSE server with alert event streaming capabilities"""
    
    def __init__(self) -> None:
        self.streams: Dict[str, AlertEventStream] = {}
        self.event_callbacks: List[Callable] = []
        
        # Component references
        self.alert_engine: Optional[AlertEngine] = None
        self.alert_manager: Optional[AlertManager] = None
        self.notification_dispatcher: Optional[NotificationDispatcher] = None
        self.alert_correlator: Optional[AlertCorrelator] = None
        self.incident_manager: Optional[IncidentManager] = None
        
        # Metrics
        self.total_events_sent = 0
        self.active_streams = 0
        self.event_history = deque(maxlen=1000)
        
        # Base SSE manager integration
        self.base_sse_manager: Optional[SSEEventManager] = None
        
        logger.info("AlertEventSSEServer initialized")
    
    async def initialize(self) -> None:
        """Initialize the alert event SSE server"""
        try:
            # Get base SSE manager
            self.base_sse_manager = await get_sse_manager()
            
            # Get alerting system components
            self.alert_engine = await get_alert_engine()
            self.alert_manager = await get_alert_manager()
            self.notification_dispatcher = await get_notification_dispatcher()
            self.alert_correlator = await get_alert_correlator()
            self.incident_manager = await get_incident_manager()
            
            # Register event callbacks with alerting components
            if self.alert_engine:
                self.alert_engine.add_alert_callback(self._on_alert_engine_event)
            
            if self.alert_manager:
                self.alert_manager.add_alert_callback(self._on_alert_manager_event)
            
            if self.alert_correlator:
                self.alert_correlator.add_correlation_callback(self._on_correlation_event)
            
            if self.incident_manager:
                self.incident_manager.add_incident_callback(self._on_incident_event)
            
            logger.info("AlertEventSSEServer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AlertEventSSEServer: {e}")
            raise
    
    async def create_stream(self, config: AlertStreamConfig) -> AlertEventStream:
        """Create new alert event stream for user"""
        # Close existing stream if exists
        if config.user_id in self.streams:
            await self.close_stream(config.user_id)
        
        # Create new stream
        stream = AlertEventStream(config)
        self.streams[config.user_id] = stream
        self.active_streams = len(self.streams)
        
        logger.info(f"Created alert stream for user {config.user_id}")
        return stream
    
    async def close_stream(self, user_id: str) -> None:
        """Close alert event stream for user"""
        if user_id in self.streams:
            del self.streams[user_id]
            self.active_streams = len(self.streams)
            logger.info(f"Closed alert stream for user {user_id}")
    
    async def broadcast_event(self, event: AlertEvent) -> None:
        """Broadcast event to all active streams"""
        try:
            self.total_events_sent += 1
            self.event_history.append(event)
            
            # Send to all active streams
            tasks = []
            for stream in self.streams.values():
                tasks.append(stream.send_event(event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Trigger external callbacks
            for callback in self.event_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add callback for alert events"""
        self.event_callbacks.append(callback)
    
    async def get_event_generator(self, user_id: str) -> AsyncGenerator[str, None]:
        """Get SSE event generator for user"""
        if user_id not in self.streams:
            logger.warning(f"No stream found for user {user_id}")
            return
        
        stream = self.streams[user_id]
        
        try:
            # Send initial connection event
            connection_event = AlertEvent(
                event_type=AlertEventType.SYSTEM_HEALTH,
                title="Alert Stream Connected",
                description=f"Real-time alert stream established",
                metadata={'stream_id': user_id, 'connected_at': stream.connected_at.isoformat()}
            )
            yield f"data: {json.dumps(connection_event.to_dict())}\n\n"
            
            # Stream events
            async for event in stream.get_events():
                event_data = json.dumps(event.to_dict())
                yield f"event: {event.event_type.value}\ndata: {event_data}\n\n"
                
        except Exception as e:
            logger.error(f"Error in event generator for user {user_id}: {e}")
        finally:
            await self.close_stream(user_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get alert event server metrics"""
        return {
            'active_streams': self.active_streams,
            'total_events_sent': self.total_events_sent,
            'streams_by_user': list(self.streams.keys()),
            'recent_events': len(self.event_history),
            'server_uptime': datetime.utcnow().isoformat()
        }
    
    # Event handlers for alerting system components
    
    async def _on_alert_engine_event(self, event_type: str, alert: Alert) -> None:
        """Handle events from AlertEngine"""
        try:
            if event_type == "alert_created":
                alert_event = AlertEvent(
                    event_type=AlertEventType.ALERT_CREATED,
                    alert_id=alert.id,
                    severity=alert.severity,
                    category=alert.category,
                    title=alert.title,
                    description=alert.description,
                    source_host=alert.source_host,
                    source_component=alert.source_component,
                    metadata={'rule_id': str(alert.rule_id) if alert.rule_id else None}
                )
                await self.broadcast_event(alert_event)
                
        except Exception as e:
            logger.error(f"Error handling alert engine event: {e}")
    
    async def _on_alert_manager_event(self, event_type: str, alert: Alert, **kwargs) -> None:
        """Handle events from AlertManager"""
        try:
            event_type_map = {
                'alert_acknowledged': AlertEventType.ALERT_ACKNOWLEDGED,
                'alert_resolved': AlertEventType.ALERT_RESOLVED,
                'alert_escalated': AlertEventType.ALERT_ESCALATED,
                'alert_expired': AlertEventType.ALERT_EXPIRED
            }
            
            if event_type in event_type_map:
                alert_event = AlertEvent(
                    event_type=event_type_map[event_type],
                    alert_id=alert.id,
                    severity=alert.severity,
                    category=alert.category,
                    title=alert.title,
                    description=alert.description,
                    source_host=alert.source_host,
                    source_component=alert.source_component,
                    user=kwargs.get('user'),
                    notes=kwargs.get('notes'),
                    metadata=kwargs.get('metadata', {})
                )
                await self.broadcast_event(alert_event)
                
        except Exception as e:
            logger.error(f"Error handling alert manager event: {e}")
    
    async def _on_correlation_event(self, correlation: CorrelationResult) -> None:
        """Handle correlation events from AlertCorrelator"""
        try:
            correlation_event = AlertEvent(
                event_type=AlertEventType.CORRELATION_FOUND,
                correlation_id=correlation.correlation_id,
                title=f"Alert Correlation Found",
                description=f"Found {len(correlation.alert_ids)} correlated alerts using {correlation.strategy.value} strategy",
                metadata={
                    'strategy': correlation.strategy.value,
                    'confidence': correlation.confidence.value,
                    'confidence_score': correlation.confidence_score,
                    'alert_count': len(correlation.alert_ids),
                    'correlation_factors': correlation.correlation_factors
                }
            )
            await self.broadcast_event(correlation_event)
            
        except Exception as e:
            logger.error(f"Error handling correlation event: {e}")
    
    async def _on_incident_event(self, event_type: str, incident: Incident) -> None:
        """Handle events from IncidentManager"""
        try:
            event_type_map = {
                'incident_created': AlertEventType.INCIDENT_CREATED,
                'incident_acknowledged': AlertEventType.INCIDENT_ACKNOWLEDGED,
                'incident_resolved': AlertEventType.INCIDENT_RESOLVED,
                'incidents_merged': AlertEventType.INCIDENT_MERGED
            }
            
            if event_type in event_type_map:
                incident_event = AlertEvent(
                    event_type=event_type_map[event_type],
                    incident_id=incident.id,
                    correlation_id=incident.correlation_id,
                    title=incident.title,
                    description=incident.description,
                    metadata={
                        'priority': incident.priority.value,
                        'category': incident.category.value,
                        'status': incident.status.value,
                        'alert_count': len(incident.alert_ids),
                        'assigned_to': incident.assigned_to
                    }
                )
                await self.broadcast_event(incident_event)
                
        except Exception as e:
            logger.error(f"Error handling incident event: {e}")


# Global alert event SSE server instance
_alert_sse_server: Optional[AlertEventSSEServer] = None


async def get_alert_sse_server() -> AlertEventSSEServer:
    """Get the global alert event SSE server instance"""
    global _alert_sse_server
    
    if _alert_sse_server is None:
        _alert_sse_server = AlertEventSSEServer()
        await _alert_sse_server.initialize()
    
    return _alert_sse_server


async def initialize_alert_sse_server() -> AlertEventSSEServer:
    """Initialize the global alert event SSE server"""
    global _alert_sse_server
    
    _alert_sse_server = AlertEventSSEServer()
    await _alert_sse_server.initialize()
    
    return _alert_sse_server


async def shutdown_alert_sse_server() -> None:
    """Shutdown the global alert event SSE server"""
    global _alert_sse_server
    
    if _alert_sse_server is not None:
        # Close all active streams
        for user_id in list(_alert_sse_server.streams.keys()):
            await _alert_sse_server.close_stream(user_id)
        
        _alert_sse_server = None


# FastAPI endpoint functions

async def stream_alerts(request: Request, user_id: str) -> EventSourceResponse:
    """SSE endpoint for alert event streaming"""
    try:
        # Get alert SSE server
        alert_server = await get_alert_sse_server()
        
        # Create default stream configuration
        # In production, this would be loaded from user preferences
        config = AlertStreamConfig(
            user_id=user_id,
            severity_filter={AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM},
            include_incidents=True,
            include_correlations=True,
            include_metrics=False,  # Reduce noise for dashboard
            max_events_per_minute=50
        )
        
        # Create stream
        await alert_server.create_stream(config)
        
        # Return SSE response
        return EventSourceResponse(
            alert_server.get_event_generator(user_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating alert stream for user {user_id}: {e}")
        return Response(content=f"Error: {str(e)}", status_code=500)


async def get_alert_stream_metrics() -> Dict[str, Any]:
    """Get metrics for alert event streaming"""
    try:
        alert_server = await get_alert_sse_server()
        return alert_server.get_metrics()
    except Exception as e:
        logger.error(f"Error getting alert stream metrics: {e}")
        return {"error": str(e)}


# Export main classes and functions
__all__ = [
    'AlertEventSSEServer',
    'AlertEvent',
    'AlertEventType',
    'AlertEventStream',
    'AlertStreamConfig',
    'get_alert_sse_server',
    'initialize_alert_sse_server',
    'shutdown_alert_sse_server',
    'stream_alerts',
    'get_alert_stream_metrics'
] 