"""
FastAPI Prometheus Integration
Comprehensive metrics collection with exemplar support for GraphMemory-IDE
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum, 
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    multiprocess, values
)
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

@dataclass
class MetricLabels:
    """Standard metric labels for GraphMemory operations."""
    method: str
    endpoint: str
    status_code: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    operation_type: Optional[str] = None
    node_type: Optional[str] = None

class GraphMemoryPrometheusMiddleware(BaseHTTPMiddleware):
    """
    Custom Prometheus middleware for GraphMemory-IDE with advanced features:
    
    - Request/response metrics with detailed labels
    - Exemplar support for trace correlation
    - GraphMemory-specific business metrics
    - Performance histograms with percentiles
    - Error tracking and categorization
    """
    
    def __init__(
        self,
        app: FastAPI,
        registry: Optional[CollectorRegistry] = None,
        enable_exemplars: bool = True,
        track_request_size: bool = True,
        track_response_size: bool = True
    ) -> None:
        super().__init__(app)
        self.registry = registry or CollectorRegistry()
        self.enable_exemplars = enable_exemplars
        self.track_request_size = track_request_size
        self.track_response_size = track_response_size
        
        # Initialize metrics
        self._setup_metrics()
        
        logger.info("GraphMemory Prometheus middleware initialized")
    
    def _setup_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        
        # Request metrics
        self.http_requests_total = Counter(
            name="graphmemory_http_requests_total",
            documentation="Total number of HTTP requests",
            labelnames=["method", "endpoint", "status_code", "user_id"],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            name="graphmemory_http_request_duration_seconds",
            documentation="HTTP request duration in seconds",
            labelnames=["method", "endpoint", "status_code", "user_id"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
            registry=self.registry
        )
        
        # Request/Response size metrics
        if self.track_request_size:
            self.http_request_size_bytes = Histogram(
                name="graphmemory_http_request_size_bytes",
                documentation="HTTP request size in bytes",
                labelnames=["method", "endpoint"],
                buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
                registry=self.registry
            )
        
        if self.track_response_size:
            self.http_response_size_bytes = Histogram(
                name="graphmemory_http_response_size_bytes",
                documentation="HTTP response size in bytes",
                labelnames=["method", "endpoint", "status_code"],
                buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
                registry=self.registry
            )
        
        # Current active requests
        self.http_requests_in_progress = Gauge(
            name="graphmemory_http_requests_in_progress",
            documentation="Number of HTTP requests currently being processed",
            labelnames=["method", "endpoint"],
            registry=self.registry
        )
        
        # Error metrics
        self.http_exceptions_total = Counter(
            name="graphmemory_http_exceptions_total",
            documentation="Total number of HTTP exceptions",
            labelnames=["method", "endpoint", "exception_type"],
            registry=self.registry
        )
        
        # GraphMemory-specific business metrics
        self.graphmemory_operations_total = Counter(
            name="graphmemory_operations_total",
            documentation="Total number of GraphMemory operations",
            labelnames=["operation_type", "node_type", "user_id", "success"],
            registry=self.registry
        )
        
        self.graphmemory_operation_duration_seconds = Histogram(
            name="graphmemory_operation_duration_seconds",
            documentation="GraphMemory operation duration in seconds",
            labelnames=["operation_type", "node_type", "user_id"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Search metrics
        self.graphmemory_search_operations_total = Counter(
            name="graphmemory_search_operations_total",
            documentation="Total number of search operations",
            labelnames=["search_type", "user_id", "has_filters"],
            registry=self.registry
        )
        
        self.graphmemory_search_results_count = Histogram(
            name="graphmemory_search_results_count",
            documentation="Number of search results returned",
            labelnames=["search_type", "user_id"],
            buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500, 1000],
            registry=self.registry
        )
        
        # Memory usage metrics
        self.graphmemory_total_nodes = Gauge(
            name="graphmemory_total_nodes",
            documentation="Total number of nodes in memory graph",
            registry=self.registry
        )
        
        self.graphmemory_total_relationships = Gauge(
            name="graphmemory_total_relationships",
            documentation="Total number of relationships in memory graph",
            registry=self.registry
        )
        
        # Session metrics
        self.graphmemory_active_sessions = Gauge(
            name="graphmemory_active_sessions",
            documentation="Number of active user sessions",
            labelnames=["user_id"],
            registry=self.registry
        )
        
        # API-specific metrics
        self.api_authentication_attempts_total = Counter(
            name="graphmemory_api_authentication_attempts_total",
            documentation="Total number of API authentication attempts",
            labelnames=["result", "user_id"],
            registry=self.registry
        )
        
        # System health metrics
        self.system_health_status = Enum(
            name="graphmemory_system_health_status",
            documentation="Current system health status",
            states=["healthy", "degraded", "unhealthy"],
            registry=self.registry
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request and collect metrics."""
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        
        # Normalize endpoint for consistent labeling
        endpoint = self._normalize_endpoint(path)
        
        # Track in-progress requests
        self.http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        
        # Calculate request size if enabled
        request_size = 0
        if self.track_request_size:
            request_size = self._get_request_size(request)
            self.http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            duration = time.time() - start_time
            status_code = str(response.status_code)
            
            # Extract user information from request if available
            user_id = self._extract_user_id(request)
            
            # Record metrics
            labels = {
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "user_id": user_id
            }
            
            self.http_requests_total.labels(**labels).inc()
            
            # Add exemplar support for trace correlation
            if self.enable_exemplars:
                exemplar = self._get_trace_exemplar(request)
                if exemplar:
                    self.http_request_duration_seconds.labels(**labels).observe(duration, exemplar=exemplar)
                else:
                    self.http_request_duration_seconds.labels(**labels).observe(duration)
            else:
                self.http_request_duration_seconds.labels(**labels).observe(duration)
            
            # Track response size if enabled
            if self.track_response_size:
                response_size = self._get_response_size(response)
                self.http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(response_size)
            
            return response
            
        except Exception as e:
            # Record exception metrics
            exception_type = type(e).__name__
            self.http_exceptions_total.labels(
                method=method,
                endpoint=endpoint,
                exception_type=exception_type
            ).inc()
            
            logger.error(f"Exception in request processing: {e}", exc_info=True)
            raise
            
        finally:
            # Always decrement in-progress counter
            self.http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for consistent metric labeling.
        
        Args:
            path: Raw request path
            
        Returns:
            Normalized endpoint name
        """
        # Remove query parameters
        path = path.split('?')[0]
        
        # Replace common path parameters with placeholders
        import re
        
        # UUID patterns
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path)
        
        # Numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Session IDs
        path = re.sub(r'/sessions/[^/]+', '/sessions/{session_id}', path)
        
        # Node IDs
        path = re.sub(r'/nodes/[^/]+', '/nodes/{node_id}', path)
        
        return path
    
    def _extract_user_id(self, request: Request) -> str:
        """Extract user ID from request context."""
        # Try various methods to extract user ID
        
        # From headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # From path parameters (if available in request state)
        if hasattr(request.state, "user_id"):
            return str(request.state.user_id)
        
        # From query parameters
        user_id = request.query_params.get("user_id")
        if user_id:
            return user_id
        
        return "anonymous"
    
    def _get_request_size(self, request: Request) -> int:
        """Calculate request size in bytes."""
        try:
            # Content-Length header
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # Fallback: approximate from headers
            header_size = sum(len(f"{k}: {v}\r\n".encode()) for k, v in request.headers.items())
            return header_size + len(str(request.url).encode())
            
        except Exception:
            return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Calculate response size in bytes."""
        try:
            # Content-Length header
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
            
            # Fallback: approximate from headers and status
            header_size = sum(len(f"{k}: {v}\r\n".encode()) for k, v in response.headers.items())
            status_line_size = len(f"HTTP/1.1 {response.status_code}\r\n".encode())
            
            return header_size + status_line_size
            
        except Exception:
            return 0
    
    def _get_trace_exemplar(self, request: Request) -> Optional[Dict[str, str]]:
        """Extract trace exemplar for correlation with tracing."""
        if not self.enable_exemplars:
            return None
        
        try:
            # Extract trace context from headers
            trace_id = request.headers.get("traceparent")
            if trace_id:
                # Parse W3C Trace Context format
                parts = trace_id.split("-")
                if len(parts) >= 2:
                    return {"trace_id": parts[1]}
            
            # Alternative: OpenTelemetry headers
            trace_id = request.headers.get("x-trace-id")
            if trace_id:
                return {"trace_id": trace_id}
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract trace exemplar: {e}")
            return None
    
    def record_graphmemory_operation(
        self,
        operation_type: str,
        node_type: str,
        user_id: str,
        duration: float,
        success: bool
    ) -> None:
        """Record GraphMemory-specific operation metrics."""
        labels = {
            "operation_type": operation_type,
            "node_type": node_type,
            "user_id": user_id,
            "success": "true" if success else "false"
        }
        
        self.graphmemory_operations_total.labels(**labels).inc()
        
        # Only record duration for successful operations to avoid skewing metrics
        if success:
            duration_labels = {
                "operation_type": operation_type,
                "node_type": node_type,
                "user_id": user_id
            }
            self.graphmemory_operation_duration_seconds.labels(**duration_labels).observe(duration)
    
    def record_search_operation(
        self,
        search_type: str,
        user_id: str,
        results_count: int,
        has_filters: bool = False
    ) -> None:
        """Record search operation metrics."""
        search_labels = {
            "search_type": search_type,
            "user_id": user_id,
            "has_filters": "true" if has_filters else "false"
        }
        
        self.graphmemory_search_operations_total.labels(**search_labels).inc()
        
        results_labels = {
            "search_type": search_type,
            "user_id": user_id
        }
        
        self.graphmemory_search_results_count.labels(**results_labels).observe(results_count)
    
    def update_memory_stats(self, total_nodes: int, total_relationships: int) -> None:
        """Update memory graph statistics."""
        self.graphmemory_total_nodes.set(total_nodes)
        self.graphmemory_total_relationships.set(total_relationships)
    
    def update_session_count(self, user_id: str, count: int) -> None:
        """Update active session count for a user."""
        self.graphmemory_active_sessions.labels(user_id=user_id).set(count)
    
    def record_authentication_attempt(self, user_id: str, success: bool) -> None:
        """Record API authentication attempt."""
        result = "success" if success else "failure"
        self.api_authentication_attempts_total.labels(
            result=result,
            user_id=user_id
        ).inc()
    
    def set_system_health(self, status: str) -> None:
        """Set current system health status."""
        valid_statuses = ["healthy", "degraded", "unhealthy"]
        if status in valid_statuses:
            self.system_health_status.state(status)
        else:
            logger.warning(f"Invalid health status: {status}")


class GraphMemoryPrometheusInstrumentator:
    """
    High-level Prometheus instrumentator for GraphMemory-IDE.
    
    Provides easy integration with FastAPI applications and
    comprehensive metrics collection setup.
    """
    
    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        enable_default_metrics: bool = True,
        enable_exemplars: bool = True
    ) -> None:
        self.registry = registry or CollectorRegistry()
        self.enable_default_metrics = enable_default_metrics
        self.enable_exemplars = enable_exemplars
        self.middleware = None
        
        # Default instrumentator from prometheus-fastapi-instrumentator
        if enable_default_metrics:
            self._setup_default_instrumentator()
    
    def _setup_default_instrumentator(self) -> None:
        """Setup default FastAPI instrumentator."""
        self.default_instrumentator = Instrumentator(
            registry=self.registry,
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/healthz", "/metrics", "/favicon.ico"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="graphmemory_requests_inprogress",
            inprogress_labels=True
        )
        
        # Add custom metrics
        self.default_instrumentator.add(
            metrics.request_size(
                metric_name="graphmemory_request_size_bytes",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True
            )
        ).add(
            metrics.response_size(
                metric_name="graphmemory_response_size_bytes",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True
            )
        ).add(
            metrics.latency(
                metric_name="graphmemory_request_duration_seconds",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True
            )
        ).add(
            metrics.requests(
                metric_name="graphmemory_requests_total",
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True
            )
        )
    
    def instrument(self, app: FastAPI) -> "GraphMemoryPrometheusInstrumentator":
        """
        Instrument FastAPI application with Prometheus metrics.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            Self for method chaining
        """
        # Add default instrumentation
        if self.enable_default_metrics:
            self.default_instrumentator.instrument(app)
        
        # Add custom middleware
        self.middleware = GraphMemoryPrometheusMiddleware(
            app=app,
            registry=self.registry,
            enable_exemplars=self.enable_exemplars
        )
        
        app.add_middleware(GraphMemoryPrometheusMiddleware, **{
            "registry": self.registry,
            "enable_exemplars": self.enable_exemplars
        })
        
        logger.info("FastAPI application instrumented with Prometheus metrics")
        return self
    
    def expose(self, app: FastAPI, endpoint: str = "/metrics") -> "GraphMemoryPrometheusInstrumentator":
        """
        Expose metrics endpoint.
        
        Args:
            app: FastAPI application instance
            endpoint: Metrics endpoint path
            
        Returns:
            Self for method chaining
        """
        @app.get(endpoint)
        async def metrics_endpoint() -> None:
            """Prometheus metrics endpoint."""
            try:
                # Generate metrics in Prometheus format
                metrics_output = generate_latest(self.registry)
                
                return PlainTextResponse(
                    content=metrics_output.decode("utf-8"),
                    media_type=CONTENT_TYPE_LATEST
                )
                
            except Exception as e:
                logger.error(f"Error generating metrics: {e}")
                return PlainTextResponse(
                    content="# Error generating metrics\n",
                    status_code=500,
                    media_type=CONTENT_TYPE_LATEST
                )
        
        logger.info(f"Metrics endpoint exposed at {endpoint}")
        return self
    
    def get_middleware(self) -> Optional[GraphMemoryPrometheusMiddleware]:
        """Get the custom middleware instance."""
        return self.middleware


# Convenience function for easy setup
def setup_prometheus_instrumentation(
    app: FastAPI,
    registry: Optional[CollectorRegistry] = None,
    metrics_endpoint: str = "/metrics",
    enable_exemplars: bool = True
) -> GraphMemoryPrometheusInstrumentator:
    """
    Setup complete Prometheus instrumentation for GraphMemory-IDE.
    
    Args:
        app: FastAPI application instance
        registry: Optional Prometheus registry
        metrics_endpoint: Endpoint to expose metrics
        enable_exemplars: Enable exemplar support for trace correlation
        
    Returns:
        Configured instrumentator instance
    """
    instrumentator = GraphMemoryPrometheusInstrumentator(
        registry=registry,
        enable_exemplars=enable_exemplars
    )
    
    instrumentator.instrument(app).expose(app, metrics_endpoint)
    
    logger.info("Prometheus instrumentation setup completed")
    return instrumentator 