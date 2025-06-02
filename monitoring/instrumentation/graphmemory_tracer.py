"""
GraphMemory-Specific OpenTelemetry Instrumentation
Custom tracing for knowledge graph operations and user workflows
"""

import logging
import time
import uuid
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass, asdict

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

logger = logging.getLogger(__name__)

@dataclass
class NodeOperation:
    """Data class for node operation metadata."""
    node_id: str
    operation_type: str  # create, read, update, delete, search
    node_type: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass 
class GraphRelationship:
    """Data class for relationship operation metadata."""
    source_node_id: str
    target_node_id: str
    relationship_type: str
    operation: str  # create, read, delete
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[float] = None

class GraphMemoryInstrumentor:
    """
    GraphMemory-specific instrumentation for comprehensive observability
    
    Features:
    - Node operation tracing with detailed metadata
    - Graph relationship monitoring
    - User session tracking
    - Performance metrics collection
    - Custom span attributes for GraphMemory context
    """
    
    def __init__(self, service_name: str = "graphmemory-ide") -> None:
        self.service_name = service_name
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        
        # Initialize metrics
        self._setup_metrics()
        
        # Session tracking
        self.active_sessions = {}
        self.operation_history = []
        
        logger.info("GraphMemory instrumentation initialized")
    
    def _setup_metrics(self) -> None:
        """Initialize GraphMemory-specific metrics."""
        # Node operation metrics
        self.node_operations_counter = self.meter.create_counter(
            name="graphmemory_node_operations_total",
            description="Total number of node operations",
            unit="1"
        )
        
        self.node_operation_duration = self.meter.create_histogram(
            name="graphmemory_node_operation_duration_seconds",
            description="Duration of node operations",
            unit="s"
        )
        
        # Search metrics
        self.search_operations_counter = self.meter.create_counter(
            name="graphmemory_search_operations_total",
            description="Total number of search operations",
            unit="1"
        )
        
        self.search_results_histogram = self.meter.create_histogram(
            name="graphmemory_search_results_count",
            description="Number of search results returned",
            unit="1"
        )
        
        # Relationship metrics
        self.relationship_operations_counter = self.meter.create_counter(
            name="graphmemory_relationship_operations_total",
            description="Total number of relationship operations",
            unit="1"
        )
        
        # Session metrics
        self.active_sessions_gauge = self.meter.create_up_down_counter(
            name="graphmemory_active_sessions",
            description="Number of active user sessions",
            unit="1"
        )
        
        # Memory usage metrics
        self.memory_nodes_gauge = self.meter.create_up_down_counter(
            name="graphmemory_total_nodes",
            description="Total number of nodes in memory graph",
            unit="1"
        )
        
        # API performance metrics
        self.api_request_duration = self.meter.create_histogram(
            name="graphmemory_api_request_duration_seconds",
            description="Duration of API requests",
            unit="s"
        )
    
    @contextmanager
    def trace_node_operation(
        self,
        operation: NodeOperation,
        span_name: Optional[str] = None
    ) -> None:
        """
        Trace a node operation with comprehensive metadata.
        
        Args:
            operation: NodeOperation instance with operation details
            span_name: Custom span name (defaults to operation type)
        """
        span_name = span_name or f"graphmemory.node.{operation.operation_type}"
        start_time = time.time()
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set standard attributes
                span.set_attribute("graphmemory.node.id", operation.node_id)
                span.set_attribute("graphmemory.node.operation", operation.operation_type)
                span.set_attribute("graphmemory.service.name", self.service_name)
                
                # Optional attributes
                if operation.node_type:
                    span.set_attribute("graphmemory.node.type", operation.node_type)
                
                if operation.user_id:
                    span.set_attribute("graphmemory.user.id", operation.user_id)
                
                if operation.session_id:
                    span.set_attribute("graphmemory.session.id", operation.session_id)
                
                # Custom metadata as attributes
                if operation.metadata:
                    for key, value in operation.metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"graphmemory.metadata.{key}", value)
                
                # Record operation start
                self.node_operations_counter.add(
                    1,
                    {
                        "operation": operation.operation_type,
                        "node_type": operation.node_type or "unknown",
                        "user_id": operation.user_id or "anonymous"
                    }
                )
                
                yield span
                
                # Mark span as successful
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                # Record error details
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                # Log error
                logger.error(f"Node operation failed: {operation.operation_type}", exc_info=True)
                raise
                
            finally:
                # Record operation duration
                duration = time.time() - start_time
                self.node_operation_duration.record(
                    duration,
                    {
                        "operation": operation.operation_type,
                        "node_type": operation.node_type or "unknown",
                        "success": "true" if span.status.status_code == StatusCode.OK else "false"
                    }
                )
                
                # Update operation history
                operation.timestamp = start_time
                self.operation_history.append(operation)
                
                # Keep history bounded
                if len(self.operation_history) > 1000:
                    self.operation_history = self.operation_history[-500:]
    
    @contextmanager
    def trace_relationship_operation(
        self,
        relationship: GraphRelationship,
        span_name: Optional[str] = None
    ) -> None:
        """
        Trace a relationship operation between nodes.
        
        Args:
            relationship: GraphRelationship instance with operation details
            span_name: Custom span name
        """
        span_name = span_name or f"graphmemory.relationship.{relationship.operation}"
        start_time = time.time()
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set relationship attributes
                span.set_attribute("graphmemory.relationship.source", relationship.source_node_id)
                span.set_attribute("graphmemory.relationship.target", relationship.target_node_id)
                span.set_attribute("graphmemory.relationship.type", relationship.relationship_type)
                span.set_attribute("graphmemory.relationship.operation", relationship.operation)
                
                if relationship.user_id:
                    span.set_attribute("graphmemory.user.id", relationship.user_id)
                
                if relationship.session_id:
                    span.set_attribute("graphmemory.session.id", relationship.session_id)
                
                # Record relationship operation
                self.relationship_operations_counter.add(
                    1,
                    {
                        "operation": relationship.operation,
                        "relationship_type": relationship.relationship_type,
                        "user_id": relationship.user_id or "anonymous"
                    }
                )
                
                yield span
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Relationship operation failed: {relationship.operation}", exc_info=True)
                raise
    
    @contextmanager
    def trace_search_operation(
        self,
        query: str,
        search_type: str = "semantic",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Trace a search operation with query analysis.
        
        Args:
            query: Search query string
            search_type: Type of search (semantic, keyword, hybrid)
            user_id: User performing the search
            session_id: Session identifier
            filters: Search filters applied
        """
        span_name = f"graphmemory.search.{search_type}"
        start_time = time.time()
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set search attributes
                span.set_attribute("graphmemory.search.query", query[:100])  # Truncate long queries
                span.set_attribute("graphmemory.search.type", search_type)
                span.set_attribute("graphmemory.search.query_length", len(query))
                
                if user_id:
                    span.set_attribute("graphmemory.user.id", user_id)
                
                if session_id:
                    span.set_attribute("graphmemory.session.id", session_id)
                
                if filters:
                    span.set_attribute("graphmemory.search.filter_count", len(filters))
                    for key, value in filters.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"graphmemory.search.filter.{key}", value)
                
                # Record search operation
                self.search_operations_counter.add(
                    1,
                    {
                        "search_type": search_type,
                        "user_id": user_id or "anonymous",
                        "has_filters": "true" if filters else "false"
                    }
                )
                
                # Context for result counting
                search_context = {"results_count": 0}
                
                yield span, search_context
                
                # Record search results
                results_count = search_context.get("results_count", 0)
                span.set_attribute("graphmemory.search.results_count", results_count)
                
                self.search_results_histogram.record(
                    results_count,
                    {
                        "search_type": search_type,
                        "user_id": user_id or "anonymous"
                    }
                )
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Search operation failed: {search_type}", exc_info=True)
                raise
    
    def start_user_session(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Start tracking a user session.
        
        Args:
            user_id: User identifier
            session_id: Optional session identifier (generates if not provided)
            
        Returns:
            Session identifier
        """
        session_id = session_id or str(uuid.uuid4())
        
        with self.tracer.start_as_current_span("graphmemory.session.start") as span:
            span.set_attribute("graphmemory.user.id", user_id)
            span.set_attribute("graphmemory.session.id", session_id)
            
            # Track session
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "start_time": time.time(),
                "operation_count": 0,
                "last_activity": time.time()
            }
            
            # Update session metrics
            self.active_sessions_gauge.add(1, {"user_id": user_id})
            
            logger.info(f"Started session {session_id} for user {user_id}")
            return session_id
    
    def end_user_session(self, session_id: str) -> None:
        """
        End tracking a user session.
        
        Args:
            session_id: Session identifier to end
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Attempting to end unknown session: {session_id}")
            return
        
        session_data = self.active_sessions[session_id]
        
        with self.tracer.start_as_current_span("graphmemory.session.end") as span:
            span.set_attribute("graphmemory.session.id", session_id)
            span.set_attribute("graphmemory.user.id", session_data["user_id"])
            
            # Calculate session metrics
            duration = time.time() - session_data["start_time"]
            span.set_attribute("graphmemory.session.duration", duration)
            span.set_attribute("graphmemory.session.operation_count", session_data["operation_count"])
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            # Update session metrics
            self.active_sessions_gauge.add(-1, {"user_id": session_data["user_id"]})
            
            logger.info(f"Ended session {session_id}, duration: {duration:.2f}s")
    
    def update_session_activity(self, session_id: str) -> None:
        """Update last activity time for a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = time.time()
            self.active_sessions[session_id]["operation_count"] += 1
    
    def instrument_api_endpoint(self, endpoint_name: str) -> None:
        """
        Decorator to instrument API endpoints with GraphMemory context.
        
        Args:
            endpoint_name: Name of the API endpoint
            
        Returns:
            Decorator function
        """
        def decorator(func) -> None:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> None:
                start_time = time.time()
                
                with self.tracer.start_as_current_span(f"graphmemory.api.{endpoint_name}") as span:
                    try:
                        span.set_attribute("graphmemory.api.endpoint", endpoint_name)
                        span.set_attribute("graphmemory.api.method", func.__name__)
                        
                        # Extract user and session from kwargs if available
                        user_id = kwargs.get("user_id") or kwargs.get("current_user")
                        session_id = kwargs.get("session_id")
                        
                        if user_id:
                            span.set_attribute("graphmemory.user.id", str(user_id))
                        
                        if session_id:
                            span.set_attribute("graphmemory.session.id", session_id)
                            self.update_session_activity(session_id)
                        
                        # Execute function
                        result = await func(*args, **kwargs)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
                        
                    finally:
                        # Record API request duration
                        duration = time.time() - start_time
                        self.api_request_duration.record(
                            duration,
                            {
                                "endpoint": endpoint_name,
                                "method": func.__name__,
                                "success": "true" if span.status.status_code == StatusCode.OK else "false"
                            }
                        )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> None:
                start_time = time.time()
                
                with self.tracer.start_as_current_span(f"graphmemory.api.{endpoint_name}") as span:
                    try:
                        span.set_attribute("graphmemory.api.endpoint", endpoint_name)
                        span.set_attribute("graphmemory.api.method", func.__name__)
                        
                        # Extract user and session from kwargs if available
                        user_id = kwargs.get("user_id") or kwargs.get("current_user")
                        session_id = kwargs.get("session_id")
                        
                        if user_id:
                            span.set_attribute("graphmemory.user.id", str(user_id))
                        
                        if session_id:
                            span.set_attribute("graphmemory.session.id", session_id)
                            self.update_session_activity(session_id)
                        
                        # Execute function
                        result = func(*args, **kwargs)
                        
                        span.set_status(Status(StatusCode.OK))
                        return result
                        
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
                        
                    finally:
                        # Record API request duration
                        duration = time.time() - start_time
                        self.api_request_duration.record(
                            duration,
                            {
                                "endpoint": endpoint_name,
                                "method": func.__name__,
                                "success": "true" if span.status.status_code == StatusCode.OK else "false"
                            }
                        )
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
                
        return decorator
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get current session metrics."""
        current_time = time.time()
        active_count = len(self.active_sessions)
        
        # Calculate session statistics
        session_durations = []
        operation_counts = []
        
        for session in self.active_sessions.values():
            duration = current_time - session["start_time"]
            session_durations.append(duration)
            operation_counts.append(session["operation_count"])
        
        return {
            "active_sessions": active_count,
            "avg_session_duration": sum(session_durations) / len(session_durations) if session_durations else 0,
            "total_operations": sum(operation_counts),
            "avg_operations_per_session": sum(operation_counts) / len(operation_counts) if operation_counts else 0
        }
    
    def cleanup_stale_sessions(self, timeout_seconds: int = 3600) -> None:
        """Clean up sessions that have been inactive for too long."""
        current_time = time.time()
        stale_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            if current_time - session_data["last_activity"] > timeout_seconds:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            logger.info(f"Cleaning up stale session: {session_id}")
            self.end_user_session(session_id)
        
        return len(stale_sessions)


# Global instrumentor instance
graphmemory_instrumentor = None

def get_graphmemory_instrumentor() -> GraphMemoryInstrumentor:
    """Get or create global GraphMemory instrumentor."""
    global graphmemory_instrumentor
    
    if graphmemory_instrumentor is None:
        graphmemory_instrumentor = GraphMemoryInstrumentor()
    
    return graphmemory_instrumentor

def initialize_graphmemory_instrumentation() -> GraphMemoryInstrumentor:
    """Initialize GraphMemory instrumentation."""
    global graphmemory_instrumentor
    
    graphmemory_instrumentor = GraphMemoryInstrumentor()
    logger.info("GraphMemory instrumentation initialized")
    
    return graphmemory_instrumentor 