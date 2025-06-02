"""
Production monitoring and metrics collection for GraphMemory-IDE.
Provides comprehensive application and system metrics for Prometheus.
"""

import time
import psutil
import logging
from typing import Dict, Optional, List, Any
from fastapi import FastAPI, Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, 
    CONTENT_TYPE_LATEST, CollectorRegistry, REGISTRY
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Centralized metrics collection for application monitoring"""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        self.registry = registry or REGISTRY
        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Initialize all Prometheus metrics"""
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Number of HTTP requests currently being processed',
            registry=self.registry
        )

        # Database Metrics
        self.database_queries_total = Counter(
            'database_queries_total',
            'Total number of database queries',
            ['query_type', 'table'],
            registry=self.registry
        )
        
        self.database_query_duration_seconds = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type'],
            registry=self.registry
        )
        
        self.database_connections_active = Gauge(
            'database_connections_active',
            'Number of active database connections',
            registry=self.registry
        )

        # System Resource Metrics
        self.system_cpu_usage_percent = Gauge(
            'system_cpu_usage_percent',
            'Current CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage_bytes = Gauge(
            'system_memory_usage_bytes',
            'Current memory usage in bytes',
            ['type'],  # available, used, total
            registry=self.registry
        )
        
        self.system_disk_usage_bytes = Gauge(
            'system_disk_usage_bytes',
            'Current disk usage in bytes',
            ['mountpoint', 'type'],  # used, total, free
            registry=self.registry
        )

        # Application-specific metrics
        self.collaboration_active_sessions = Gauge(
            'collaboration_active_sessions',
            'Number of active collaboration sessions',
            registry=self.registry
        )
        
        self.websocket_connections_active = Gauge(
            'websocket_connections_active',
            'Number of active WebSocket connections',
            registry=self.registry
        )
        
        self.graph_operations_total = Counter(
            'graph_operations_total',
            'Total number of graph database operations',
            ['operation_type'],
            registry=self.registry
        )

        # Error Metrics
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """Record HTTP request metrics"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def record_database_query(self, query_type: str, table: str, duration: float) -> None:
        """Record database query metrics"""
        self.database_queries_total.labels(
            query_type=query_type,
            table=table
        ).inc()
        
        self.database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)

    def update_system_metrics(self) -> None:
        """Update system resource metrics"""
        try:
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_cpu_usage_percent.set(cpu_percent)
            
            # Memory Usage
            memory = psutil.virtual_memory()
            self.system_memory_usage_bytes.labels(type='total').set(memory.total)
            self.system_memory_usage_bytes.labels(type='used').set(memory.used)
            self.system_memory_usage_bytes.labels(type='available').set(memory.available)
            
            # Disk Usage for root partition
            disk = psutil.disk_usage('/')
            self.system_disk_usage_bytes.labels(mountpoint='/', type='total').set(disk.total)
            self.system_disk_usage_bytes.labels(mountpoint='/', type='used').set(disk.used)
            self.system_disk_usage_bytes.labels(mountpoint='/', type='free').set(disk.free)
            
        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")
            self.errors_total.labels(error_type='system_metrics', component='monitoring').inc()

    def record_error(self, error_type: str, component: str) -> None:
        """Record error occurrence"""
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def increment_active_sessions(self) -> None:
        """Increment active collaboration sessions"""
        self.collaboration_active_sessions.inc()

    def decrement_active_sessions(self) -> None:
        """Decrement active collaboration sessions"""
        self.collaboration_active_sessions.dec()

    def set_websocket_connections(self, count: int) -> None:
        """Set current WebSocket connection count"""
        self.websocket_connections_active.set(count)

    def record_graph_operation(self, operation_type: str) -> None:
        """Record graph database operation"""
        self.graph_operations_total.labels(operation_type=operation_type).inc()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic HTTP request metrics collection"""

    def __init__(self, app, metrics_collector: MetricsCollector) -> None:
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip metrics collection for metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.time()
        
        # Increment in-progress requests
        self.metrics_collector.http_requests_in_progress.inc()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            self.metrics_collector.record_http_request(
                method=request.method,
                endpoint=self._get_endpoint_name(request),
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            # Record error
            self.metrics_collector.record_error(
                error_type=type(e).__name__,
                component='http_handler'
            )
            raise
        finally:
            # Decrement in-progress requests
            self.metrics_collector.http_requests_in_progress.dec()

    def _get_endpoint_name(self, request: Request) -> str:
        """Extract meaningful endpoint name from request"""
        # Get the route pattern if available
        if hasattr(request, 'scope') and 'route' in request.scope:
            route = request.scope['route']
            if hasattr(route, 'path'):
                return route.path
        
        # Fallback to path with parameter normalization
        path = request.url.path
        
        # Simple parameter normalization for common patterns
        import re
        path = re.sub(r'/\d+', '/{id}', path)  # Replace numeric IDs
        path = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', path)  # Replace UUIDs
        
        return path


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_metrics_endpoint(app: FastAPI, endpoint: str = "/metrics") -> None:
    """Setup Prometheus metrics endpoint"""
    
    @app.get(endpoint, response_class=PlainTextResponse)
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint"""
        # Update system metrics before serving
        collector = get_metrics_collector()
        collector.update_system_metrics()
        
        # Generate and return metrics
        metrics_data = generate_latest(collector.registry)
        return PlainTextResponse(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )


def setup_health_endpoint(app: FastAPI, endpoint: str = "/health") -> Dict[str, Any]:
    """Setup health check endpoint"""
    
    @app.get(endpoint)
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint with system status"""
        try:
            # Basic system checks
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Health status logic
            health_status = "healthy"
            issues = []
            
            # Check CPU usage
            if cpu_percent > 90:
                health_status = "degraded"
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            # Check memory usage
            memory_usage_percent = (memory.used / memory.total) * 100
            if memory_usage_percent > 90:
                health_status = "degraded"
                issues.append(f"High memory usage: {memory_usage_percent:.1f}%")
            
            # Check disk usage
            disk_usage_percent = (disk.used / disk.total) * 100
            if disk_usage_percent > 90:
                health_status = "degraded"
                issues.append(f"High disk usage: {disk_usage_percent:.1f}%")
            
            return {
                "status": health_status,
                "timestamp": time.time(),
                "checks": {
                    "cpu_percent": cpu_percent,
                    "memory_usage_percent": memory_usage_percent,
                    "disk_usage_percent": disk_usage_percent,
                },
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }


def setup_monitoring_middleware(app: FastAPI) -> None:
    """Setup comprehensive monitoring middleware"""
    collector = get_metrics_collector()
    
    # Add metrics collection middleware
    app.add_middleware(MetricsMiddleware, metrics_collector=collector)
    
    logger.info("Monitoring middleware configured")


def create_custom_registry() -> CollectorRegistry:
    """Create a custom Prometheus registry for isolated metrics"""
    return CollectorRegistry() 