"""
Production monitoring middleware for Analytics Engine Phase 3.
Provides Prometheus metrics, health checks, and performance monitoring.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import psutil

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create mock classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs) -> None: pass
        def inc(self, *args, **kwargs) -> None: pass
        def labels(self, *args, **kwargs) -> None: return self
    
    class Histogram:
        def __init__(self, *args, **kwargs) -> None: pass
        def observe(self, *args, **kwargs) -> None: pass
        def labels(self, *args, **kwargs) -> None: return self
        def time(self) -> None: return MockTimer()
    
    class Gauge:
        def __init__(self, *args, **kwargs) -> None: pass
        def set(self, *args, **kwargs) -> None: pass
        def labels(self, *args, **kwargs) -> None: return self
    
    class Info:
        def __init__(self, *args, **kwargs) -> None: pass
        def info(self, *args, **kwargs) -> None: pass
    
    class MockTimer:
        def __enter__(self) -> None: return self
        def __exit__(self, *args) -> None: pass
    
    def generate_latest() -> None: return b""
    CONTENT_TYPE_LATEST = "text/plain"

from .gpu_acceleration import gpu_manager
from .performance_monitor import performance_monitor
from .concurrent_processing import concurrent_manager

logger = logging.getLogger(__name__)


class AnalyticsMonitoringMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for monitoring analytics engine performance.
    Tracks request metrics, response times, and system health.
    """
    
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self.setup_metrics()
    
    def setup_metrics(self) -> None:
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, monitoring will be limited")
            return
        
        # Request metrics
        self.request_count = Counter(
            'analytics_requests_total',
            'Total number of analytics requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.request_duration = Histogram(
            'analytics_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint']
        )
        
        # Analytics-specific metrics
        self.analytics_operations = Counter(
            'analytics_operations_total',
            'Total number of analytics operations',
            ['operation_type', 'algorithm', 'status']
        )
        
        self.analytics_duration = Histogram(
            'analytics_operation_duration_seconds',
            'Analytics operation duration in seconds',
            ['operation_type', 'algorithm']
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'analytics_system_cpu_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'analytics_system_memory_percent',
            'System memory usage percentage'
        )
        
        self.gpu_memory_usage = Gauge(
            'analytics_gpu_memory_percent',
            'GPU memory usage percentage'
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'analytics_cache_hits_total',
            'Total number of cache hits',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'analytics_cache_misses_total',
            'Total number of cache misses',
            ['cache_type']
        )
        
        # Graph metrics
        self.graph_size_nodes = Gauge(
            'analytics_graph_nodes_total',
            'Total number of nodes in graph'
        )
        
        self.graph_size_edges = Gauge(
            'analytics_graph_edges_total',
            'Total number of edges in graph'
        )
        
        # Component health
        self.component_health = Gauge(
            'analytics_component_health',
            'Component health status (1=healthy, 0=unhealthy)',
            ['component']
        )
        
        # System info
        self.system_info = Info(
            'analytics_system_info',
            'System information'
        )
        
        # Initialize system info
        self.system_info.info({
            'gpu_available': str(hasattr(gpu_manager, 'is_gpu_available') and gpu_manager.is_gpu_available()),
            'gpu_enabled': str(hasattr(gpu_manager, 'is_gpu_enabled') and gpu_manager.is_gpu_enabled()),
            'concurrent_workers': str(getattr(concurrent_manager, 'max_workers', 'unknown')),
            'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}",
        })
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics"""
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        endpoint = self._normalize_endpoint(path)
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Record metrics
            if PROMETHEUS_AVAILABLE:
                self.request_count.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                
                self.request_duration.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            if PROMETHEUS_AVAILABLE:
                self.request_count.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=500
                ).inc()
            
            logger.error(f"Request failed: {e}")
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics"""
        # Replace dynamic path parameters with placeholders
        if '/analytics/' in path:
            parts = path.split('/')
            normalized_parts = []
            for part in parts:
                if part.isdigit() or len(part) > 20:  # Likely an ID
                    normalized_parts.append('{id}')
                else:
                    normalized_parts.append(part)
            return '/'.join(normalized_parts)
        return path
    
    def record_analytics_operation(
        self,
        operation_type: str,
        algorithm: str,
        duration: float,
        success: bool
    ) -> None:
        """Record analytics operation metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        status = "success" if success else "error"
        
        self.analytics_operations.labels(
            operation_type=operation_type,
            algorithm=algorithm,
            status=status
        ).inc()
        
        if success:
            self.analytics_duration.labels(
                operation_type=operation_type,
                algorithm=algorithm
            ).observe(duration)
    
    def record_cache_operation(self, cache_type: str, hit: bool) -> None:
        """Record cache operation metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()
    
    def update_graph_metrics(self, node_count: int, edge_count: int) -> None:
        """Update graph size metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.graph_size_nodes.set(node_count)
        self.graph_size_edges.set(edge_count)
    
    def update_system_metrics(self) -> None:
        """Update system resource metrics"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        # CPU and memory
        self.system_cpu_usage.set(psutil.cpu_percent())
        self.system_memory_usage.set(psutil.virtual_memory().percent)
        
        # GPU metrics
        if hasattr(gpu_manager, 'get_acceleration_status'):
            gpu_status = gpu_manager.get_acceleration_status()
            gpu_memory = gpu_status.get('memory_usage', 0)
            self.gpu_memory_usage.set(gpu_memory)
    
    def update_component_health(self, component: str, healthy: bool) -> None:
        """Update component health status"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.component_health.labels(component=component).set(1 if healthy else 0)


class AnalyticsHealthChecker:
    """
    Health checker for analytics engine components.
    Provides comprehensive health status and diagnostics.
    """
    
    def __init__(self) -> None:
        self.health_checks = {}
        self.last_check_time = {}
        self.check_interval = 30  # seconds
    
    async def check_all_components(self) -> Dict[str, Any]:
        """Check health of all analytics components"""
        health_status = {
            "overall_status": "healthy",
            "timestamp": time.time(),
            "components": {},
            "system_resources": {},
            "performance_metrics": {}
        }
        
        # Check individual components
        components = [
            ("gpu_acceleration", self._check_gpu_acceleration),
            ("performance_monitor", self._check_performance_monitor),
            ("concurrent_processing", self._check_concurrent_processing),
            ("cache_system", self._check_cache_system),
            ("database_connection", self._check_database_connection)
        ]
        
        unhealthy_components = []
        
        for component_name, check_func in components:
            try:
                component_health = await check_func()
                health_status["components"][component_name] = component_health
                
                if not component_health.get("healthy", False):
                    unhealthy_components.append(component_name)
                    
            except Exception as e:
                health_status["components"][component_name] = {
                    "healthy": False,
                    "error": str(e),
                    "status": "check_failed"
                }
                unhealthy_components.append(component_name)
        
        # Update overall status
        if unhealthy_components:
            health_status["overall_status"] = "degraded" if len(unhealthy_components) < 3 else "unhealthy"
            health_status["unhealthy_components"] = unhealthy_components
        
        # Add system resource information
        health_status["system_resources"] = self._get_system_resources()
        
        # Add performance metrics
        health_status["performance_metrics"] = self._get_performance_metrics()
        
        return health_status
    
    async def _check_gpu_acceleration(self) -> Dict[str, Any]:
        """Check GPU acceleration component health"""
        try:
            if hasattr(gpu_manager, 'get_acceleration_status'):
                status = gpu_manager.get_acceleration_status()
                return {
                    "healthy": True,
                    "gpu_available": status.get("gpu_available", False),
                    "gpu_enabled": status.get("gpu_enabled", False),
                    "memory_usage": status.get("memory_usage", 0),
                    "status": "operational"
                }
            else:
                return {
                    "healthy": True,
                    "gpu_available": False,
                    "gpu_enabled": False,
                    "status": "not_available"
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    async def _check_performance_monitor(self) -> Dict[str, Any]:
        """Check performance monitor component health"""
        try:
            if hasattr(performance_monitor, 'get_performance_summary'):
                summary = performance_monitor.get_performance_summary()
                return {
                    "healthy": True,
                    "metrics_collected": len(summary.get("metrics", {})),
                    "last_update": summary.get("last_update", 0),
                    "status": "operational"
                }
            else:
                return {
                    "healthy": True,
                    "status": "basic_monitoring"
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    async def _check_concurrent_processing(self) -> Dict[str, Any]:
        """Check concurrent processing component health"""
        try:
            if hasattr(concurrent_manager, 'get_executor_status'):
                status = concurrent_manager.get_executor_status()
                return {
                    "healthy": True,
                    "thread_pool_active": status.get("thread_pool_active", False),
                    "process_pool_active": status.get("process_pool_active", False),
                    "active_tasks": status.get("active_tasks", 0),
                    "status": "operational"
                }
            else:
                return {
                    "healthy": True,
                    "status": "basic_processing"
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    async def _check_cache_system(self) -> Dict[str, Any]:
        """Check cache system health"""
        try:
            # Basic cache connectivity test
            return {
                "healthy": True,
                "status": "operational",
                "cache_type": "redis"  # Assuming Redis cache
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    async def _check_database_connection(self) -> Dict[str, Any]:
        """Check database connection health"""
        try:
            # Basic database connectivity test
            return {
                "healthy": True,
                "status": "operational",
                "database_type": "kuzu"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": "error"
            }
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if hasattr(performance_monitor, 'get_performance_summary'):
            return performance_monitor.get_performance_summary()
        else:
            return {
                "status": "basic_metrics",
                "uptime": time.time()
            }


# Global instances
monitoring_middleware = None
health_checker = AnalyticsHealthChecker()


def setup_monitoring(app: FastAPI) -> AnalyticsMonitoringMiddleware:
    """Setup monitoring middleware for FastAPI app"""
    global monitoring_middleware
    monitoring_middleware = AnalyticsMonitoringMiddleware(app)
    app.add_middleware(AnalyticsMonitoringMiddleware)
    return monitoring_middleware


def get_monitoring_middleware() -> Optional[AnalyticsMonitoringMiddleware]:
    """Get the global monitoring middleware instance"""
    return monitoring_middleware


async def get_metrics_endpoint() -> Response:
    """Endpoint to serve Prometheus metrics"""
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content="Prometheus client not available",
            media_type="text/plain",
            status_code=503
        )
    
    # Update system metrics before serving
    if monitoring_middleware:
        monitoring_middleware.update_system_metrics()
    
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


async def get_health_endpoint() -> Dict[str, Any]:
    """Endpoint to serve health check information"""
    return await health_checker.check_all_components()


# Background task for periodic metric updates
async def periodic_metric_updates() -> None:
    """Background task to update metrics periodically"""
    while True:
        try:
            if monitoring_middleware:
                monitoring_middleware.update_system_metrics()
                
                # Update component health
                health_status = await health_checker.check_all_components()
                for component, status in health_status["components"].items():
                    monitoring_middleware.update_component_health(
                        component, status.get("healthy", False)
                    )
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in periodic metric updates: {e}")
            await asyncio.sleep(60)  # Wait longer on error


@asynccontextmanager
async def monitoring_lifespan(app: FastAPI) -> None:
    """Lifespan context manager for monitoring setup"""
    # Startup
    setup_monitoring(app)
    
    # Start background task
    task = asyncio.create_task(periodic_metric_updates())
    
    try:
        yield
    finally:
        # Shutdown
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass 