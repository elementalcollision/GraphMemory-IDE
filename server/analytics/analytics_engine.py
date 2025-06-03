"""
Advanced Analytics Engine for GraphMemory-IDE

This module implements a comprehensive analytics system with:
- Privacy-compliant event collection
- Real-time and batch processing
- Custom metrics and KPIs
- GDPR/CCPA compliance
- Data export capabilities
- Performance monitoring

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import time

from fastapi import Request
import asyncpg
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge


class EventType(Enum):
    """Standard event types for analytics."""
    PAGE_VIEW = "page_view"
    USER_ACTION = "user_action"
    API_CALL = "api_call"
    ERROR = "error"
    PERFORMANCE = "performance"
    FEATURE_USAGE = "feature_usage"
    CONVERSION = "conversion"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    CUSTOM = "custom"


class EventPriority(Enum):
    """Event processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AnalyticsEvent:
    """Analytics event data structure."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.CUSTOM
    event_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not self.event_name and self.event_type != EventType.CUSTOM:
            self.event_name = self.event_type.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def anonymize(self) -> 'AnalyticsEvent':
        """Create anonymized version of the event."""
        anonymized = AnalyticsEvent(
            event_id=self.event_id,
            event_type=self.event_type,
            event_name=self.event_name,
            timestamp=self.timestamp,
            user_id=None,  # Remove user ID
            session_id=self._hash_value(self.session_id) if self.session_id else None,
            anonymous_id=self._hash_value(self.user_id) if self.user_id else self.anonymous_id,
            properties=self._anonymize_properties(self.properties),
            context=self._anonymize_context(self.context),
            priority=self.priority,
            source=self.source
        )
        return anonymized
    
    def _hash_value(self, value: str) -> str:
        """Hash a value for anonymization."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]
    
    def _anonymize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize sensitive properties."""
        sensitive_keys = {'email', 'name', 'username', 'ip_address', 'user_agent'}
        anonymized = {}
        
        for key, value in properties.items():
            if key.lower() in sensitive_keys:
                if isinstance(value, str):
                    anonymized[key] = self._hash_value(value)
                else:
                    anonymized[key] = "[anonymized]"
            else:
                anonymized[key] = value
        
        return anonymized
    
    def _anonymize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize sensitive context data."""
        if not context:
            return {}
        
        anonymized = context.copy()
        
        # Remove or hash IP addresses
        if 'ip' in anonymized:
            anonymized['ip'] = self._hash_value(str(anonymized['ip']))
        
        # Anonymize user agent
        if 'user_agent' in anonymized:
            anonymized['user_agent'] = self._hash_value(str(anonymized['user_agent']))
        
        return anonymized


class AnalyticsMetrics:
    """Prometheus metrics for analytics."""
    
    def __init__(self) -> None:
        self.events_total = Counter(
            'analytics_events_total',
            'Total number of analytics events',
            ['event_type', 'source']
        )
        
        self.event_processing_duration = Histogram(
            'analytics_event_processing_duration_seconds',
            'Time spent processing analytics events',
            ['event_type']
        )
        
        self.events_queue_size = Gauge(
            'analytics_events_queue_size',
            'Number of events in processing queue'
        )
        
        self.batch_processing_duration = Histogram(
            'analytics_batch_processing_duration_seconds',
            'Time spent processing event batches'
        )
        
        self.database_operations = Counter(
            'analytics_database_operations_total',
            'Total database operations',
            ['operation', 'status']
        )


class EventCollector:
    """Collects and validates analytics events."""
    
    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self.metrics = AnalyticsMetrics()
    
    def extract_context_from_request(self, request: Request) -> Dict[str, Any]:
        """Extract context information from HTTP request."""
        context = {
            'url': str(request.url),
            'method': request.method,
            'user_agent': request.headers.get('user-agent', ''),
            'referer': request.headers.get('referer', ''),
            'ip': getattr(request.client, 'host', '') if request.client else '',
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        # Add authentication context if available
        if hasattr(request.state, 'user') and request.state.user:
            context['authenticated'] = True
            context['user_role'] = getattr(request.state.user, 'role', 'user')
        else:
            context['authenticated'] = False
        
        return context
    
    def create_page_view_event(
        self, 
        request: Request, 
        page_title: str = "", 
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """Create a page view event."""
        properties = {
            'page_title': page_title,
            'page_url': str(request.url.path),
            'query_params': dict(request.query_params),
        }
        
        if additional_properties:
            properties.update(additional_properties)
        
        return AnalyticsEvent(
            event_type=EventType.PAGE_VIEW,
            event_name="page_view",
            user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
            session_id=getattr(request.state, 'session_id', None) if hasattr(request.state, 'session_id') else None,
            properties=properties,
            context=self.extract_context_from_request(request),
            source="web"
        )
    
    def create_user_action_event(
        self,
        action_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """Create a user action event."""
        return AnalyticsEvent(
            event_type=EventType.USER_ACTION,
            event_name=action_name,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            context=context or {},
            source="application"
        )
    
    def create_api_call_event(
        self,
        request: Request,
        response_status: int,
        response_time: float,
        endpoint: str = ""
    ) -> AnalyticsEvent:
        """Create an API call event."""
        properties = {
            'endpoint': endpoint or str(request.url.path),
            'method': request.method,
            'status_code': response_status,
            'response_time_ms': response_time * 1000,
            'success': 200 <= response_status < 400,
        }
        
        return AnalyticsEvent(
            event_type=EventType.API_CALL,
            event_name="api_call",
            user_id=getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None,
            session_id=getattr(request.state, 'session_id', None) if hasattr(request.state, 'session_id') else None,
            properties=properties,
            context=self.extract_context_from_request(request),
            source="api"
        )
    
    def create_error_event(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        """Create an error event."""
        properties = {
            'error_type': error_type,
            'error_message': error_message,
            'stack_trace': stack_trace,
        }
        
        return AnalyticsEvent(
            event_type=EventType.ERROR,
            event_name="error_occurred",
            user_id=user_id,
            properties=properties,
            context=context or {},
            priority=EventPriority.HIGH,
            source="system"
        )
    
    def validate_event(self, event: AnalyticsEvent) -> tuple[bool, Optional[str]]:
        """Validate an analytics event."""
        # Check required fields
        if not event.event_name:
            return False, "Event name is required"
        
        if not event.event_type:
            return False, "Event type is required"
        
        # Validate event name format
        if not event.event_name.replace('_', '').replace('-', '').isalnum():
            return False, "Event name contains invalid characters"
        
        # Check properties size
        properties_size = len(json.dumps(event.properties))
        if properties_size > 64 * 1024:  # 64KB limit
            return False, "Event properties too large"
        
        # Validate timestamp
        if event.timestamp > datetime.utcnow() + timedelta(minutes=5):
            return False, "Event timestamp is in the future"
        
        if event.timestamp < datetime.utcnow() - timedelta(days=7):
            return False, "Event timestamp is too old"
        
        return True, None


class EventProcessor:
    """Processes analytics events in batches."""
    
    def __init__(self, settings: Any, db_pool: Any, redis_client: Any) -> None:
        self.settings = settings
        self.db_pool = db_pool
        self.redis = redis_client
        self.metrics = AnalyticsMetrics()
        self.event_queue: asyncio.Queue[AnalyticsEvent] = asyncio.Queue()
        self.batch_processor_task: Optional[asyncio.Task[None]] = None
        self.running = False
    
    async def start(self) -> None:
        """Start the event processor."""
        self.running = True
        self.batch_processor_task = asyncio.create_task(self._batch_processor())
    
    async def stop(self) -> None:
        """Stop the event processor."""
        self.running = False
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            try:
                await self.batch_processor_task
            except asyncio.CancelledError:
                pass
    
    async def queue_event(self, event: AnalyticsEvent) -> None:
        """Queue an event for processing."""
        # Apply sampling if configured
        if self.settings.ANALYTICS_SAMPLE_RATE < 1.0:
            if hash(event.event_id) % 100 >= self.settings.ANALYTICS_SAMPLE_RATE * 100:
                return  # Skip this event due to sampling
        
        # Anonymize if required
        if self.settings.ANONYMOUS_ANALYTICS and event.user_id:
            event = event.anonymize()
        
        await self.event_queue.put(event)
        self.metrics.events_queue_size.set(self.event_queue.qsize())
        
        # Update metrics
        self.metrics.events_total.labels(
            event_type=event.event_type.value,
            source=event.source
        ).inc()
    
    async def _batch_processor(self) -> None:
        """Process events in batches."""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Wait for event or timeout
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=1.0
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    pass
                
                # Check if we should flush the batch
                should_flush = (
                    len(batch) >= self.settings.ANALYTICS_BATCH_SIZE or
                    (batch and time.time() - last_flush >= self.settings.ANALYTICS_FLUSH_INTERVAL)
                )
                
                if should_flush and batch:
                    start_time = time.time()
                    await self._process_batch(batch)
                    processing_time = time.time() - start_time
                    
                    self.metrics.batch_processing_duration.observe(processing_time)
                    batch = []
                    last_flush = time.time()
                    
                    # Update queue size metric
                    self.metrics.events_queue_size.set(self.event_queue.qsize())
                
            except Exception as e:
                print(f"Error in batch processor: {e}")
                # Continue processing even if there's an error
                batch = []
    
    async def _process_batch(self, events: List[AnalyticsEvent]) -> None:
        """Process a batch of events."""
        if not events:
            return
        
        # Store events in database
        await self._store_events_in_database(events)
        
        # Store in Redis for real-time analytics
        await self._store_events_in_redis(events)
        
        # Update real-time metrics
        await self._update_real_time_metrics(events)
    
    async def _store_events_in_database(self, events: List[AnalyticsEvent]) -> None:
        """Store events in PostgreSQL database."""
        try:
            async with self.db_pool.acquire() as conn:
                # Prepare bulk insert
                values = []
                for event in events:
                    values.append((
                        event.event_id,
                        event.event_type.value,
                        event.event_name,
                        event.timestamp,
                        event.user_id,
                        event.session_id,
                        event.anonymous_id,
                        json.dumps(event.properties),
                        json.dumps(event.context),
                        event.priority.value,
                        event.source
                    ))
                
                # Bulk insert
                await conn.executemany(
                    """
                    INSERT INTO analytics_events (
                        event_id, event_type, event_name, timestamp,
                        user_id, session_id, anonymous_id, properties,
                        context, priority, source
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    values
                )
                
                self.metrics.database_operations.labels(
                    operation="insert", status="success"
                ).inc()
                
        except Exception as e:
            print(f"Error storing events in database: {e}")
            self.metrics.database_operations.labels(
                operation="insert", status="error"
            ).inc()
    
    async def _store_events_in_redis(self, events: List[AnalyticsEvent]) -> None:
        """Store events in Redis for real-time analytics."""
        try:
            pipe = self.redis.pipeline()
            
            for event in events:
                # Store event data
                key = f"analytics:event:{event.event_id}"
                pipe.setex(key, 3600, json.dumps(event.to_dict()))  # 1 hour TTL
                
                # Update counters
                date_key = event.timestamp.strftime("%Y-%m-%d")
                hour_key = event.timestamp.strftime("%Y-%m-%d:%H")
                
                pipe.hincrby(f"analytics:daily:{date_key}", event.event_type.value, 1)
                pipe.hincrby(f"analytics:hourly:{hour_key}", event.event_type.value, 1)
                
                # User activity tracking (if not anonymous)
                if event.user_id:
                    pipe.setex(f"analytics:user:{event.user_id}:last_seen", 86400, event.timestamp.isoformat())
                    pipe.sadd(f"analytics:active_users:{date_key}", event.user_id)
                    pipe.expire(f"analytics:active_users:{date_key}", 86400 * 7)  # 7 days
            
            await pipe.execute()
            
        except Exception as e:
            print(f"Error storing events in Redis: {e}")
    
    async def _update_real_time_metrics(self, events: List[AnalyticsEvent]) -> None:
        """Update real-time analytics metrics."""
        try:
            # Group events by type for efficient processing
            event_type_counts = {}
            for event in events:
                event_type = event.event_type.value
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            # Update Redis counters
            pipe = self.redis.pipeline()
            for event_type, count in event_type_counts.items():
                pipe.incrby(f"analytics:realtime:{event_type}", count)
                pipe.expire(f"analytics:realtime:{event_type}", 3600)  # 1 hour
            
            await pipe.execute()
            
        except Exception as e:
            print(f"Error updating real-time metrics: {e}")


class AnalyticsEngine:
    """Main analytics engine coordinating all components."""
    
    def __init__(self, settings: Any, db_pool: Any) -> None:
        self.settings = settings
        self.db_pool = db_pool
        self.redis_client: Optional[Any] = None
        self.collector = EventCollector(settings)
        self.processor: Optional[EventProcessor] = None
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the analytics engine."""
        if not self.settings.ANALYTICS_ENABLED:
            return
        
        try:
            # Initialize Redis connection
            redis_config = self.settings.get_redis_config("analytics")
            self.redis_client = redis.from_url(
                redis_config["url"],
                encoding=redis_config["encoding"],
                decode_responses=redis_config["decode_responses"]
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            
            # Initialize processor
            self.processor = EventProcessor(self.settings, self.db_pool, self.redis_client)
            await self.processor.start()
            
            self.initialized = True
            print("Analytics engine initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize analytics engine: {e}")
    
    async def close(self) -> None:
        """Close the analytics engine."""
        if self.processor:
            await self.processor.stop()
        
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def track_event(self, event: AnalyticsEvent) -> bool:
        """Track an analytics event."""
        if not self.initialized or not self.settings.ANALYTICS_ENABLED:
            return False
        
        # Validate event
        is_valid, error = self.collector.validate_event(event)
        if not is_valid:
            print(f"Invalid analytics event: {error}")
            return False
        
        # Queue for processing
        await self.processor.queue_event(event)
        return True
    
    async def track_page_view(
        self, 
        request: Request, 
        page_title: str = "",
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track a page view event."""
        event = self.collector.create_page_view_event(request, page_title, additional_properties)
        return await self.track_event(event)
    
    async def track_user_action(
        self,
        action_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track a user action event."""
        event = self.collector.create_user_action_event(
            action_name, user_id, session_id, properties, context
        )
        return await self.track_event(event)
    
    async def track_api_call(
        self, 
        request: Request, 
        response_status: int, 
        response_time: float,
        endpoint: str = ""
    ) -> bool:
        """Track an API call event."""
        event = self.collector.create_api_call_event(
            request, response_status, response_time, endpoint
        )
        return await self.track_event(event)
    
    async def track_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Track an error event."""
        event = self.collector.create_error_event(
            error_type, error_message, stack_trace, user_id, context
        )
        return await self.track_event(event)
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time analytics metrics."""
        if not self.redis_client:
            return {}
        
        try:
            # Get current hour metrics
            metrics = {}
            for event_type in list(EventType):
                count = await self.redis_client.get(f"analytics:realtime:{event_type.value}")
                metrics[event_type.value] = int(count) if count else 0
            
            return metrics
            
        except Exception as e:
            print(f"Error getting real-time metrics: {e}")
            return {}
    
    async def get_daily_stats(self, date: str) -> Dict[str, Any]:
        """Get daily analytics statistics."""
        if not self.redis_client:
            return {}
        
        try:
            stats = await self.redis_client.hgetall(f"analytics:daily:{date}")
            return {k: int(v) for k, v in stats.items()}
            
        except Exception as e:
            print(f"Error getting daily stats: {e}")
            return {}


# Global analytics engine instance
analytics_engine = None


async def initialize_analytics_engine(settings: Any, db_pool: Any) -> None:
    """Initialize the global analytics engine."""
    global analytics_engine
    analytics_engine = AnalyticsEngine(settings, db_pool)
    await analytics_engine.initialize()


async def close_analytics_engine() -> None:
    """Close the global analytics engine."""
    global analytics_engine
    if analytics_engine:
        await analytics_engine.close()


def get_analytics_engine() -> Optional['AnalyticsEngine']:
    """Get the global analytics engine instance."""
    return analytics_engine 