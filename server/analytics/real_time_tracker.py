"""
Real-Time Event Tracking for GraphMemory-IDE

This module provides real-time analytics tracking including:
- Authentication event tracking
- User journey monitoring
- Live metrics streaming
- Session correlation
- Real-time dashboard updates

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import time

from fastapi import WebSocket, WebSocketDisconnect
import asyncpg
import redis.asyncio as redis
from pydantic import BaseModel

from .analytics_engine import AnalyticsEngine, EventType, AnalyticsEvent


class UserActivityType(Enum):
    """Types of user activities to track."""
    LOGIN = "login"
    LOGOUT = "logout"
    SSO_LOGIN = "sso_login"
    MFA_SETUP = "mfa_setup"
    MFA_VERIFY = "mfa_verify"
    PASSWORD_CHANGE = "password_change"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PAGE_VIEW = "page_view"
    FEATURE_USE = "feature_use"
    ERROR_ENCOUNTER = "error_encounter"
    API_CALL = "api_call"


@dataclass
class UserJourney:
    """Represents a user's journey through the application."""
    journey_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    events: List[Dict[str, Any]] = field(default_factory=list)
    current_page: str = ""
    referrer: str = ""
    user_agent: str = ""
    ip_address: str = ""
    authentication_method: str = ""
    conversion_goals: List[str] = field(default_factory=list)
    
    def add_event(self, event: Dict[str, Any]):
        """Add an event to the user journey."""
        event['timestamp'] = datetime.utcnow().isoformat()
        event['sequence_number'] = len(self.events) + 1
        self.events.append(event)
        self.last_activity = datetime.utcnow()
    
    def get_duration(self) -> float:
        """Get journey duration in seconds."""
        return (self.last_activity - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert journey to dictionary."""
        return {
            'journey_id': self.journey_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'duration_seconds': self.get_duration(),
            'events': self.events,
            'current_page': self.current_page,
            'referrer': self.referrer,
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'authentication_method': self.authentication_method,
            'conversion_goals': self.conversion_goals,
            'event_count': len(self.events)
        }


@dataclass
class RealTimeMetric:
    """Real-time metric data structure."""
    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            'metric_name': self.metric_name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'unit': self.unit
        }


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow(),
            'last_ping': datetime.utcnow()
        }
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_users(self, message: Dict[str, Any], user_ids: List[str]):
        """Broadcast message to specific users."""
        disconnected = []
        for connection in self.active_connections:
            metadata = self.connection_metadata.get(connection)
            if metadata and metadata.get('user_id') in user_ids:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    def get_active_user_count(self) -> int:
        """Get count of active users."""
        user_ids = set()
        for metadata in self.connection_metadata.values():
            if metadata.get('user_id'):
                user_ids.add(metadata['user_id'])
        return len(user_ids)


class RealTimeTracker:
    """Real-time analytics tracking system."""
    
    def __init__(self, analytics_engine: AnalyticsEngine, redis_client, db_pool: asyncpg.Pool):
        self.analytics_engine = analytics_engine
        self.redis_client = redis_client
        self.db_pool = db_pool
        self.websocket_manager = WebSocketManager()
        
        # In-memory stores for real-time data
        self.active_journeys: Dict[str, UserJourney] = {}
        self.real_time_metrics: Dict[str, List[RealTimeMetric]] = {}
        self.event_handlers: Dict[UserActivityType, List[Callable]] = {}
        
        # Configuration
        self.journey_timeout = 1800  # 30 minutes
        self.metrics_retention = 3600  # 1 hour
        self.broadcast_interval = 5  # seconds
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the real-time tracking system."""
        try:
            # Create database tables if needed
            await self._create_tables()
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_data())
            self._broadcast_task = asyncio.create_task(self._broadcast_metrics())
            
            # Register default event handlers
            self._register_default_handlers()
            
            print("Real-time tracker initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize real-time tracker: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the real-time tracking system."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._broadcast_task:
            self._broadcast_task.cancel()
    
    async def _create_tables(self):
        """Create necessary database tables."""
        async with self.db_pool.acquire() as conn:
            # User journeys table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_journeys (
                    journey_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255),
                    session_id VARCHAR(255),
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER,
                    event_count INTEGER DEFAULT 0,
                    conversion_goals TEXT[],
                    referrer TEXT,
                    user_agent TEXT,
                    ip_address VARCHAR(45),
                    authentication_method VARCHAR(100),
                    journey_data JSONB
                )
            """)
            
            # Real-time metrics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS real_time_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(255) NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    labels JSONB,
                    unit VARCHAR(50)
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_journeys_user_id ON user_journeys(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_journeys_session ON user_journeys(session_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_journeys_start_time ON user_journeys(start_time)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON real_time_metrics(metric_name, timestamp)")
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        
        async def handle_authentication_event(event_data: Dict[str, Any]):
            """Handle authentication-related events."""
            await self.record_metric(
                "authentication_events",
                1,
                labels={
                    "auth_type": event_data.get("auth_type", "unknown"),
                    "success": str(event_data.get("success", False))
                }
            )
        
        async def handle_session_event(event_data: Dict[str, Any]):
            """Handle session-related events."""
            await self.record_metric(
                "active_sessions",
                1 if event_data.get("action") == "start" else -1,
                labels={"action": event_data.get("action", "unknown")}
            )
        
        async def handle_error_event(event_data: Dict[str, Any]):
            """Handle error events."""
            await self.record_metric(
                "error_rate",
                1,
                labels={
                    "error_type": event_data.get("error_type", "unknown"),
                    "severity": event_data.get("severity", "medium")
                }
            )
        
        # Register handlers
        self.register_event_handler(UserActivityType.LOGIN, handle_authentication_event)
        self.register_event_handler(UserActivityType.SSO_LOGIN, handle_authentication_event)
        self.register_event_handler(UserActivityType.MFA_VERIFY, handle_authentication_event)
        self.register_event_handler(UserActivityType.SESSION_START, handle_session_event)
        self.register_event_handler(UserActivityType.SESSION_END, handle_session_event)
        self.register_event_handler(UserActivityType.ERROR_ENCOUNTER, handle_error_event)
    
    def register_event_handler(self, activity_type: UserActivityType, handler: Callable):
        """Register an event handler for a specific activity type."""
        if activity_type not in self.event_handlers:
            self.event_handlers[activity_type] = []
        self.event_handlers[activity_type].append(handler)
    
    async def track_user_activity(
        self,
        activity_type: UserActivityType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """Track a user activity event."""
        if event_data is None:
            event_data = {}
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Create event for analytics engine
            event = AnalyticsEvent(
                event_type=EventType.USER_ACTION,
                event_name=activity_type.value,
                user_id=user_id,
                session_id=session_id,
                properties=event_data
            )
            await self.analytics_engine.track_event(event)
            
            # Update user journey
            await self._update_user_journey(session_id, activity_type, event_data, user_id)
            
            # Update metrics
            await self.record_metric(f"user_activity_{activity_type.value}", 1.0)
            
            # Trigger event handlers
            if activity_type in self.event_handlers:
                for handler in self.event_handlers[activity_type]:
                    try:
                        await handler({
                            'activity_type': activity_type.value,
                            'user_id': user_id,
                            'session_id': session_id,
                            'event_data': event_data,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        print(f"Error in event handler: {e}")
            
            # Broadcast update to connected clients
            await self._broadcast_activity_update(activity_type, {
                'user_id': user_id,
                'session_id': session_id,
                'event_data': event_data
            })
            
        except Exception as e:
            print(f"Error tracking user activity: {e}")
    
    async def _update_user_journey(
        self,
        session_id: str,
        activity_type: UserActivityType,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Update or create user journey."""
        try:
            # Get or create journey
            if session_id in self.active_journeys:
                journey = self.active_journeys[session_id]
            else:
                journey = UserJourney(
                    session_id=session_id,
                    user_id=user_id
                )
                self.active_journeys[session_id] = journey
            
            # Update journey properties
            if user_id and not journey.user_id:
                journey.user_id = user_id
            
            # Add event to journey
            journey.add_event({
                'activity_type': activity_type.value,
                'event_data': event_data,
                'user_id': user_id
            })
            
            # Update current page if it's a page view
            if activity_type == UserActivityType.PAGE_VIEW and 'page' in event_data:
                journey.current_page = str(event_data['page'])
            
            # Save to database periodically (every 10 events or 5 minutes)
            if (len(journey.events) % 10 == 0 or 
                (datetime.utcnow() - journey.last_activity).total_seconds() > 300):
                await self._save_journey_to_database(journey)
            
        except Exception as e:
            print(f"Error updating user journey: {e}")
    
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        unit: str = ""
    ):
        """Record a real-time metric."""
        if labels is None:
            labels = {}
        
        try:
            metric = RealTimeMetric(
                metric_name=metric_name,
                value=value,
                labels=labels,
                unit=unit
            )
            
            # Store in memory with time-based key
            time_key = datetime.utcnow().strftime("%Y%m%d%H%M")
            storage_key = f"{metric_name}:{time_key}"
            
            if storage_key not in self.real_time_metrics:
                self.real_time_metrics[storage_key] = []
            
            self.real_time_metrics[storage_key].append(metric)
            
            # Store in Redis for persistence
            if self.redis_client:
                await self.redis_client.lpush(
                    f"metrics:{metric_name}",
                    json.dumps(metric.to_dict())
                )
                # Keep only last 1000 entries
                await self.redis_client.ltrim(f"metrics:{metric_name}", 0, 999)
            
            # Save to database for historical analysis
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO real_time_metrics (metric_name, value, timestamp, labels, unit)
                    VALUES ($1, $2, $3, $4, $5)
                """, metric_name, value, metric.timestamp, json.dumps(labels), unit)
            
        except Exception as e:
            print(f"Error recording metric: {e}")
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics summary."""
        try:
            metrics: Dict[str, Any] = {
                'active_users': len(set(j.user_id for j in self.active_journeys.values() if j.user_id)),
                'active_sessions': len(self.active_journeys),
                'connected_clients': self.websocket_manager.get_active_user_count()
            }
            
            # Calculate metrics from recent data
            current_time = datetime.utcnow()
            recent_cutoff = current_time - timedelta(minutes=5)
            
            # Aggregate recent metrics
            for storage_key, metric_list in self.real_time_metrics.items():
                metric_name = storage_key.split(':')[0]
                recent = [m for m in metric_list if m.timestamp >= recent_cutoff]
                
                if recent:
                    metrics[f"{metric_name}_total"] = sum(m.value for m in recent)
                    metrics[f"{metric_name}_avg"] = sum(m.value for m in recent) / len(recent)
                    metrics[f"{metric_name}_count"] = len(recent)
            
            return metrics
            
        except Exception as e:
            print(f"Error getting current metrics: {e}")
            return {}
    
    async def get_user_journey(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user journey data."""
        if session_id in self.active_journeys:
            return self.active_journeys[session_id].to_dict()
        
        # Check database for completed journeys
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_journeys WHERE session_id = $1",
                session_id
            )
            if row:
                return dict(row)
        
        return None
    
    async def _broadcast_activity_update(self, activity_type: UserActivityType, event_data: Dict[str, Any]):
        """Broadcast activity update to connected clients."""
        message = {
            'type': 'activity_update',
            'activity_type': activity_type.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data': event_data
        }
        
        await self.websocket_manager.broadcast(message)
    
    async def _broadcast_metrics(self):
        """Periodically broadcast metrics to connected clients."""
        while True:
            try:
                await asyncio.sleep(self.broadcast_interval)
                
                metrics = await self.get_current_metrics()
                message = {
                    'type': 'metrics_update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'metrics': metrics
                }
                
                await self.websocket_manager.broadcast(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error broadcasting metrics: {e}")
    
    async def _cleanup_expired_data(self):
        """Clean up expired journeys and metrics."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                current_time = datetime.utcnow()
                
                # Clean up expired journeys
                expired_journeys = []
                for session_id, journey in self.active_journeys.items():
                    if (current_time - journey.last_activity).total_seconds() > self.journey_timeout:
                        expired_journeys.append(session_id)
                
                # Move expired journeys to database
                for session_id in expired_journeys:
                    journey = self.active_journeys.pop(session_id)
                    await self._save_journey_to_database(journey)
                
                # Clean up old metrics
                cutoff_time = current_time - timedelta(seconds=self.metrics_retention)
                for metric_name in list(self.real_time_metrics.keys()):
                    self.real_time_metrics[metric_name] = [
                        m for m in self.real_time_metrics[metric_name]
                        if m.timestamp >= cutoff_time
                    ]
                    
                    # Remove empty lists
                    if not self.real_time_metrics[metric_name]:
                        del self.real_time_metrics[metric_name]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in cleanup task: {e}")
    
    async def _save_journey_to_database(self, journey: UserJourney):
        """Save completed journey to database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_journeys (
                        journey_id, user_id, session_id, start_time, end_time,
                        duration_seconds, event_count, conversion_goals,
                        referrer, user_agent, ip_address, authentication_method,
                        journey_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                journey.journey_id,
                journey.user_id,
                journey.session_id,
                journey.start_time,
                journey.last_activity,
                int(journey.get_duration()),
                len(journey.events),
                journey.conversion_goals,
                journey.referrer,
                journey.user_agent,
                journey.ip_address,
                journey.authentication_method,
                json.dumps(journey.to_dict())
                )
        except Exception as e:
            print(f"Failed to save journey to database: {e}")


# Global instance
_real_time_tracker: Optional[RealTimeTracker] = None


async def initialize_real_time_tracker(
    analytics_engine: AnalyticsEngine,
    redis_client,
    db_pool: asyncpg.Pool
):
    """Initialize real-time tracking system."""
    global _real_time_tracker
    _real_time_tracker = RealTimeTracker(analytics_engine, redis_client, db_pool)
    await _real_time_tracker.initialize()


def get_real_time_tracker() -> Optional[RealTimeTracker]:
    """Get real-time tracker instance."""
    return _real_time_tracker


async def shutdown_real_time_tracker():
    """Shutdown real-time tracking system."""
    global _real_time_tracker
    if _real_time_tracker:
        await _real_time_tracker.shutdown()
        _real_time_tracker = None 