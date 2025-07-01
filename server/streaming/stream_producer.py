"""
Stream Producer Service for GraphMemory-IDE Analytics Pipeline

This module handles event collection from MCP operations and streams them
to DragonflyDB for real-time processing and analytics.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum

from .dragonfly_config import get_dragonfly_client

logger = logging.getLogger(__name__)

class EventType(str, Enum):
    """Types of events in the analytics pipeline"""
    MEMORY_OPERATION = "memory_operation"
    USER_INTERACTION = "user_interaction" 
    SYSTEM_METRIC = "system_metric"
    GRAPH_CHANGE = "graph_change"
    TELEMETRY = "telemetry"
    ERROR = "error"

class OperationType(str, Enum):
    """Types of memory operations"""
    CREATE_ENTITY = "create_entity"
    ADD_OBSERVATION = "add_observation"
    CREATE_RELATION = "create_relation"
    DELETE_ENTITY = "delete_entity"
    DELETE_OBSERVATION = "delete_observation"
    DELETE_RELATION = "delete_relation"
    SEARCH_NODES = "search_nodes"
    OPEN_NODES = "open_nodes"

@dataclass
class StreamEvent:
    """Base event structure for the analytics pipeline"""
    event_id: str
    event_type: EventType
    timestamp: str
    source: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

@dataclass
class MemoryOperationEvent(StreamEvent):
    """Event for memory operations (MCP)"""
    operation_type: Optional[OperationType] = None
    entity_count: int = 0
    relation_count: int = 0
    processing_time_ms: float = 0.0
    
    def __post_init__(self) -> None:
        self.event_type = EventType.MEMORY_OPERATION
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

@dataclass
class UserInteractionEvent(StreamEvent):
    """Event for user interactions"""
    interaction_type: Optional[str] = None
    target_resource: Optional[str] = None
    duration_ms: float = 0.0
    
    def __post_init__(self) -> None:
        self.event_type = EventType.USER_INTERACTION

@dataclass
class SystemMetricEvent(StreamEvent):
    """Event for system metrics"""
    metric_name: Optional[str] = None
    metric_value: Optional[Union[int, float]] = None
    metric_unit: str = "count"
    
    def __post_init__(self) -> None:
        self.event_type = EventType.SYSTEM_METRIC

class StreamProducer:
    """
    Handles streaming events to DragonflyDB streams for real-time analytics
    """
    
    def __init__(self, source_identifier: str = "mcp-server") -> None:
        self.source = source_identifier
        self._event_buffer: List[StreamEvent] = []
        self._buffer_size = 100
        self._flush_interval = 5.0  # seconds
        self._flush_task: Optional[asyncio.Task] = None
        self._stats: Dict[str, Any] = {
            "events_produced": 0,
            "events_failed": 0,
            "last_flush": None,
            "buffer_overflows": 0,
        }
        self._streams = {
            EventType.MEMORY_OPERATION: "analytics:memory_operations",
            EventType.USER_INTERACTION: "analytics:user_interactions", 
            EventType.SYSTEM_METRIC: "analytics:system_metrics",
            EventType.GRAPH_CHANGE: "analytics:graph_changes",
            EventType.TELEMETRY: "analytics:telemetry",
            EventType.ERROR: "analytics:errors",
        }
    
    async def start(self) -> None:
        """Start the stream producer"""
        logger.info("Starting stream producer service")
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(f"Stream producer started (buffer_size={self._buffer_size}, flush_interval={self._flush_interval}s)")
    
    async def stop(self) -> None:
        """Stop the stream producer and flush remaining events"""
        logger.info("Stopping stream producer service")
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining events
        await self._flush_buffer()
        logger.info("Stream producer stopped")
    
    async def produce_event(self, event: StreamEvent) -> None:
        """Add event to buffer for streaming"""
        self._event_buffer.append(event)
        
        # Flush immediately if buffer is full
        if len(self._event_buffer) >= self._buffer_size:
            self._stats["buffer_overflows"] += 1
            await self._flush_buffer()
    
    async def produce_memory_operation(
        self,
        operation_type: OperationType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        entity_count: int = 0,
        relation_count: int = 0,
        processing_time_ms: float = 0.0,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce a memory operation event"""
        event = MemoryOperationEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.MEMORY_OPERATION,
            timestamp=datetime.utcnow().isoformat(),
            source=self.source,
            operation_type=operation_type,
            user_id=user_id,
            session_id=session_id,
            entity_count=entity_count,
            relation_count=relation_count,
            processing_time_ms=processing_time_ms,
            data=additional_data or {},
            metadata={
                "source_module": "mcp_operations",
                "api_version": "1.0"
            }
        )
        await self.produce_event(event)
    
    async def produce_user_interaction(
        self,
        interaction_type: str,
        target_resource: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: float = 0.0,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce a user interaction event"""
        event = UserInteractionEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.USER_INTERACTION,
            timestamp=datetime.utcnow().isoformat(),
            source=self.source,
            interaction_type=interaction_type,
            target_resource=target_resource,
            user_id=user_id,
            session_id=session_id,
            duration_ms=duration_ms,
            data=additional_data or {},
            metadata={
                "source_module": "user_tracking",
                "api_version": "1.0"
            }
        )
        await self.produce_event(event)
    
    async def produce_system_metric(
        self,
        metric_name: str,
        metric_value: Union[int, float],
        metric_unit: str = "count",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Produce a system metric event"""
        event = SystemMetricEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SYSTEM_METRIC,
            timestamp=datetime.utcnow().isoformat(),
            source=self.source,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_unit=metric_unit,
            data=additional_data or {},
            metadata={
                "source_module": "system_monitoring",
                "api_version": "1.0"
            }
        )
        await self.produce_event(event)
    
    async def produce_telemetry_event(
        self,
        telemetry_data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Produce a telemetry event from existing telemetry ingestion"""
        event = StreamEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TELEMETRY,
            timestamp=datetime.utcnow().isoformat(),
            source=self.source,
            user_id=user_id,
            session_id=session_id,
            data=telemetry_data,
            metadata={
                "source_module": "telemetry_ingestion",
                "api_version": "1.0"
            }
        )
        await self.produce_event(event)
    
    async def _periodic_flush(self) -> None:
        """Periodically flush events from buffer to streams"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        base_backoff = 1.0
        max_backoff = 60.0
        
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_buffer()
                consecutive_errors = 0  # Reset error count on success
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in periodic flush: {e} (consecutive errors: {consecutive_errors})")
                
                # Implement circuit breaker pattern
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Too many consecutive flush errors ({consecutive_errors}), entering circuit breaker mode")
                    await asyncio.sleep(max_backoff)
                    consecutive_errors = 0  # Reset to try again
                else:
                    # Exponential backoff with jitter
                    backoff_time = min(base_backoff * (2 ** consecutive_errors), max_backoff)
                    jitter = backoff_time * 0.1 * (0.5 - asyncio.get_event_loop().time() % 1)
                    await asyncio.sleep(backoff_time + jitter)
    
    async def _flush_buffer(self) -> None:
        """Flush buffered events to DragonflyDB streams"""
        if not self._event_buffer:
            return
        
        events_to_flush = self._event_buffer.copy()
        self._event_buffer.clear()
        
        try:
            client = await get_dragonfly_client()
            
            # Group events by stream
            streams_data: Dict[str, List[Dict[str, Any]]] = {}
            for event in events_to_flush:
                stream_name = self._streams[event.event_type]
                if stream_name not in streams_data:
                    streams_data[stream_name] = []
                streams_data[stream_name].append(event.to_dict())
            
            # Send events to streams
            for stream_name, events in streams_data.items():
                for event_data in events:
                    try:
                        # Add to DragonflyDB stream
                        stream_id = await client.xadd(
                            stream_name,
                            event_data,
                            maxlen=10000  # Keep last 10k events per stream
                        )
                        
                        self._stats["events_produced"] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to add event to stream {stream_name}: {e}")
                        self._stats["events_failed"] += 1
            
            self._stats["last_flush"] = datetime.utcnow().isoformat()
            logger.debug(f"Flushed {len(events_to_flush)} events to streams")
            
        except Exception as e:
            logger.error(f"Failed to flush events to streams: {e}")
            # Re-add events to buffer on failure
            self._event_buffer.extend(events_to_flush)
            self._stats["events_failed"] += len(events_to_flush)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get producer statistics"""
        stats = self._stats.copy()
        stats.update({
            "buffer_size": len(self._event_buffer),
            "max_buffer_size": self._buffer_size,
            "configured_streams": list(self._streams.values()),
            "source": self.source,
        })
        return stats
    
    async def get_stream_info(self) -> Dict[str, Any]:
        """Get information about all streams"""
        try:
            client = await get_dragonfly_client()
            stream_info = {}
            
            for event_type, stream_name in self._streams.items():
                try:
                    length = await client.xlen(stream_name)
                    stream_info[stream_name] = {
                        "event_type": event_type.value,
                        "length": length,
                        "last_id": None
                    }
                    
                    # Get last entry ID
                    try:
                        last_entry = await client.xrevrange(stream_name, count=1)
                        if last_entry:
                            stream_info[stream_name]["last_id"] = last_entry[0][0]
                    except Exception:
                        pass
                        
                except Exception as e:
                    logger.warning(f"Failed to get info for stream {stream_name}: {e}")
                    stream_info[stream_name] = {"error": str(e)}
            
            return stream_info
            
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return {"error": str(e)}

# Global stream producer instance
_stream_producer: Optional[StreamProducer] = None

async def get_stream_producer() -> StreamProducer:
    """Get the global stream producer instance"""
    global _stream_producer
    if not _stream_producer:
        raise RuntimeError("Stream producer not initialized")
    return _stream_producer

async def initialize_stream_producer(source_identifier: str = "mcp-server") -> None:
    """Initialize the global stream producer"""
    global _stream_producer
    _stream_producer = StreamProducer(source_identifier)
    await _stream_producer.start()

async def shutdown_stream_producer() -> None:
    """Shutdown the global stream producer"""
    global _stream_producer
    if _stream_producer:
        await _stream_producer.stop()
        _stream_producer = None 