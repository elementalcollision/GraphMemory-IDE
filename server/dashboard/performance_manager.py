"""
Advanced Performance Optimization & Resource Management System

This module provides comprehensive performance optimization including connection pooling,
rate limiting, memory management, performance profiling, and resource monitoring.
Integrates seamlessly with all Phase 3 components for optimal system performance.
"""

import asyncio
import gc
import json
import psutil
import threading
import time
import tracemalloc
import weakref
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from memory_profiler import memory_usage
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple, TYPE_CHECKING
import aiofiles
from asyncio_pool import AioPool

try:
    # Import rate limiting
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    if TYPE_CHECKING:
        from slowapi import Limiter
    else:
        Limiter = None

try:
    from .enhanced_circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig
    from .cache_manager import get_cache_manager
    from .analytics_client import get_analytics_client
    from .background_collector import get_background_collector
    from .models.analytics_models import SystemMetricsData
    from .models.error_models import AnalyticsError, ErrorSeverity, ErrorCategory
except ImportError:
    from enhanced_circuit_breaker import get_circuit_breaker_manager, CircuitBreakerConfig
    from cache_manager import get_cache_manager
    from analytics_client import get_analytics_client
    from background_collector import get_background_collector
    from models.analytics_models import SystemMetricsData
    from models.error_models import AnalyticsError, ErrorSeverity, ErrorCategory


class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    CONNECTIONS = "connections"
    THREADS = "threads"


class PerformanceMetric(Enum):
    """Performance monitoring metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CONNECTION_COUNT = "connection_count"
    CACHE_HIT_RATE = "cache_hit_rate"
    QUEUE_LENGTH = "queue_length"


class OptimizationStrategy(Enum):
    """Performance optimization strategies"""
    CONNECTION_POOLING = "connection_pooling"
    REQUEST_BATCHING = "request_batching"
    CACHING = "caching"
    RATE_LIMITING = "rate_limiting"
    GARBAGE_COLLECTION = "garbage_collection"
    MEMORY_OPTIMIZATION = "memory_optimization"
    ASYNC_OPTIMIZATION = "async_optimization"


class AlertLevel(Enum):
    """System alert levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization"""
    
    # Connection pooling settings
    enable_connection_pooling: bool = True
    max_pool_size: int = 50
    min_pool_size: int = 5
    pool_timeout_seconds: int = 30
    connection_max_age_seconds: int = 3600
    
    # Rate limiting settings
    enable_rate_limiting: bool = True
    default_rate_limit: str = "100/minute"
    burst_rate_limit: str = "20/second"
    rate_limit_storage: str = "memory"  # or "redis://localhost:6379/0"
    
    # Memory management settings
    enable_memory_monitoring: bool = True
    memory_threshold_percent: float = 80.0
    enable_auto_gc: bool = True
    gc_threshold_mb: int = 100
    memory_profiling_enabled: bool = False
    
    # Performance monitoring settings
    enable_performance_monitoring: bool = True
    monitoring_interval_seconds: int = 5
    metrics_retention_hours: int = 24
    enable_profiling: bool = False
    
    # Resource monitoring settings
    enable_resource_monitoring: bool = True
    cpu_threshold_percent: float = 80.0
    disk_threshold_percent: float = 85.0
    enable_alerting: bool = True
    
    # Optimization settings
    enable_async_optimization: bool = True
    max_concurrent_tasks: int = 100
    task_timeout_seconds: int = 60
    enable_request_batching: bool = True
    batch_size: int = 10
    batch_timeout_ms: int = 100


@dataclass
class ResourceMetrics:
    """System resource usage metrics"""
    
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    disk_usage_percent: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    connection_count: int = 0
    thread_count: int = 0
    process_count: int = 0
    load_average: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used_mb": self.memory_used_mb,
            "memory_available_mb": self.memory_available_mb,
            "disk_usage_percent": self.disk_usage_percent,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "connection_count": self.connection_count,
            "thread_count": self.thread_count,
            "process_count": self.process_count,
            "load_average": self.load_average,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PerformanceSnapshot:
    """Performance monitoring snapshot"""
    
    response_times: List[float] = field(default_factory=list)
    throughput_rps: float = 0.0
    error_rate_percent: float = 0.0
    active_connections: int = 0
    queue_length: int = 0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_avg_response_time(self) -> float:
        """Get average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
    
    def get_p95_response_time(self) -> float:
        """Get 95th percentile response time"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        p95_index = int(len(sorted_times) * 0.95)
        return sorted_times[p95_index] if sorted_times else 0.0


@dataclass
class SystemAlert:
    """System performance alert"""
    
    alert_id: str
    level: AlertLevel
    resource_type: ResourceType
    metric: PerformanceMetric
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "resource_type": self.resource_type.value,
            "metric": self.metric.value,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved
        }


class ConnectionPool(ABC):
    """Abstract base class for connection pools"""
    
    @abstractmethod
    async def get_connection(self) -> Any:
        """Get connection from pool"""
        pass
    
    @abstractmethod
    async def return_connection(self, connection: Any) -> None:
        """Return connection to pool"""
        pass
    
    @abstractmethod
    async def close_all(self) -> None:
        """Close all connections"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        pass


class GenericConnectionPool(ConnectionPool):
    """Generic connection pool implementation"""
    
    def __init__(self, 
                 connection_factory: Callable,
                 max_size: int = 50,
                 min_size: int = 5,
                 timeout: int = 30,
                 max_age: int = 3600) -> None:
        self.connection_factory = connection_factory
        self.max_size = max_size
        self.min_size = min_size
        self.timeout = timeout
        self.max_age = max_age
        
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._connections: Set[Any] = set()
        self._connection_times: Dict[Any, datetime] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "created": 0,
            "reused": 0,
            "closed": 0,
            "timeouts": 0,
            "errors": 0
        }
    
    async def initialize(self) -> None:
        """Initialize pool with minimum connections"""
        for _ in range(self.min_size):
            try:
                conn = await self._create_connection()
                await self._pool.put(conn)
            except Exception as e:
                print(f"Failed to create initial connection: {e}")
    
    async def _create_connection(self) -> Any:
        """Create new connection"""
        try:
            if asyncio.iscoroutinefunction(self.connection_factory):
                connection = await self.connection_factory()
            else:
                connection = self.connection_factory()
            
            self._connections.add(connection)
            self._connection_times[connection] = datetime.now()
            self.stats["created"] += 1
            return connection
        except Exception as e:
            self.stats["errors"] += 1
            raise
    
    async def get_connection(self) -> Any:
        """Get connection from pool"""
        try:
            # Try to get existing connection
            connection = await asyncio.wait_for(
                self._pool.get(), 
                timeout=self.timeout
            )
            
            # Check if connection is too old
            if self._is_connection_expired(connection):
                await self._close_connection(connection)
                connection = await self._create_connection()
            
            self.stats["reused"] += 1
            return connection
            
        except asyncio.TimeoutError:
            self.stats["timeouts"] += 1
            # Create new connection if pool is empty and under max size
            if len(self._connections) < self.max_size:
                return await self._create_connection()
            raise
    
    async def return_connection(self, connection: Any) -> None:
        """Return connection to pool"""
        if connection in self._connections and not self._is_connection_expired(connection):
            try:
                await self._pool.put(connection)
            except asyncio.QueueFull:
                # Pool is full, close connection
                await self._close_connection(connection)
        else:
            await self._close_connection(connection)
    
    def _is_connection_expired(self, connection: Any) -> bool:
        """Check if connection is expired"""
        creation_time = self._connection_times.get(connection)
        if not creation_time:
            return True
        
        age = (datetime.now() - creation_time).total_seconds()
        return age > self.max_age
    
    async def _close_connection(self, connection: Any) -> None:
        """Close connection"""
        try:
            if hasattr(connection, 'close'):
                if asyncio.iscoroutinefunction(connection.close):
                    await connection.close()
                else:
                    connection.close()
            
            self._connections.discard(connection)
            self._connection_times.pop(connection, None)
            self.stats["closed"] += 1
            
        except Exception as e:
            print(f"Error closing connection: {e}")
    
    async def close_all(self) -> None:
        """Close all connections"""
        async with self._lock:
            connections = list(self._connections)
            for connection in connections:
                await self._close_connection(connection)
            
            # Clear queue
            while not self._pool.empty():
                try:
                    self._pool.get_nowait()
                except asyncio.QueueEmpty:
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            **self.stats,
            "active_connections": len(self._connections),
            "available_connections": self._pool.qsize(),
            "max_size": self.max_size,
            "min_size": self.min_size
        }


class ConnectionPoolManager:
    """Manages multiple connection pools"""
    
    def __init__(self, config: PerformanceConfig) -> None:
        self.config = config
        self.pools: Dict[str, ConnectionPool] = {}
        self._lock = asyncio.Lock()
    
    async def create_pool(self, 
                         name: str, 
                         connection_factory: Callable,
                         max_size: Optional[int] = None,
                         min_size: Optional[int] = None) -> ConnectionPool:
        """Create and register a new connection pool"""
        async with self._lock:
            if name in self.pools:
                await self.pools[name].close_all()
            
            pool = GenericConnectionPool(
                connection_factory=connection_factory,
                max_size=max_size or self.config.max_pool_size,
                min_size=min_size or self.config.min_pool_size,
                timeout=self.config.pool_timeout_seconds,
                max_age=self.config.connection_max_age_seconds
            )
            
            await pool.initialize()
            self.pools[name] = pool
            return pool
    
    async def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get connection pool by name"""
        return self.pools.get(name)
    
    @asynccontextmanager
    async def get_connection(self, pool_name: str) -> None:
        """Context manager for getting and returning connections"""
        pool = await self.get_pool(pool_name)
        if not pool:
            raise ValueError(f"Pool '{pool_name}' not found")
        
        connection = await pool.get_connection()
        try:
            yield connection
        finally:
            await pool.return_connection(connection)
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools"""
        stats = {}
        for name, pool in self.pools.items():
            stats[name] = pool.get_stats()
        return stats
    
    async def shutdown(self) -> None:
        """Shutdown all pools"""
        async with self._lock:
            for pool in self.pools.values():
                await pool.close_all()
            self.pools.clear()


class RateLimitManager:
    """Advanced rate limiting manager"""
    
    def __init__(self, config: PerformanceConfig) -> None:
        self.config = config
        self.limiter: Optional[Limiter] = None
        self.custom_limits: Dict[str, str] = {}
        self.adaptive_limits: Dict[str, float] = {}
        
        if SLOWAPI_AVAILABLE and config.enable_rate_limiting:
            self._initialize_limiter()
    
    def _initialize_limiter(self) -> None:
        """Initialize the rate limiter"""
        try:
            storage_uri = None
            if self.config.rate_limit_storage.startswith("redis://"):
                storage_uri = self.config.rate_limit_storage
            
            self.limiter = Limiter(
                key_func=get_remote_address,
                default_limits=[self.config.default_rate_limit],
                storage_uri=storage_uri
            )
        except Exception as e:
            print(f"Failed to initialize rate limiter: {e}")
            self.limiter = None
    
    def get_limiter(self) -> Optional[Limiter]:
        """Get the rate limiter instance"""
        return self.limiter
    
    def add_custom_limit(self, endpoint: str, limit: str) -> None:
        """Add custom rate limit for specific endpoint"""
        self.custom_limits[endpoint] = limit
    
    def get_limit_for_endpoint(self, endpoint: str) -> str:
        """Get rate limit for specific endpoint"""
        return self.custom_limits.get(endpoint, self.config.default_rate_limit)
    
    async def adjust_adaptive_limits(self, endpoint: str, load_factor: float) -> None:
        """Adjust rate limits based on system load"""
        if endpoint not in self.adaptive_limits:
            self.adaptive_limits[endpoint] = 1.0
        
        # Reduce limits when system is under high load
        if load_factor > 0.8:
            self.adaptive_limits[endpoint] *= 0.9
        elif load_factor < 0.5:
            self.adaptive_limits[endpoint] = min(1.0, self.adaptive_limits[endpoint] * 1.1)
    
    def get_adaptive_limit(self, endpoint: str) -> float:
        """Get adaptive limit factor for endpoint"""
        return self.adaptive_limits.get(endpoint, 1.0)


class MemoryManager:
    """Advanced memory management and monitoring"""
    
    def __init__(self, config: PerformanceConfig) -> None:
        self.config = config
        self.memory_snapshots: deque = deque(maxlen=1000)
        self.memory_alerts: List[SystemAlert] = []
        self.gc_stats: Dict[str, Any] = {
            "collections": 0,
            "freed_objects": 0,
            "last_collection": None
        }
        
        if config.memory_profiling_enabled:
            tracemalloc.start()
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024
        }
    
    def profile_memory_usage(self, func: Callable) -> Tuple[Any, float]:
        """Profile memory usage of a function"""
        if not self.config.memory_profiling_enabled:
            return func(), 0.0
        
        try:
            mem_usage = memory_usage(func, interval=0.1, max_usage=True)
            peak_memory = mem_usage if isinstance(mem_usage, (int, float)) else 0.0
        except Exception:
            peak_memory = 0.0
        
        result = func()
        return result, peak_memory
    
    async def monitor_memory(self) -> None:
        """Continuous memory monitoring"""
        while True:
            try:
                usage = self.get_memory_usage()
                self.memory_snapshots.append({
                    **usage,
                    "timestamp": datetime.now()
                })
                
                # Check thresholds
                if usage["percent"] > self.config.memory_threshold_percent:
                    await self._create_memory_alert(usage)
                
                # Auto garbage collection
                if (self.config.enable_auto_gc and 
                    usage["rss_mb"] > self.config.gc_threshold_mb):
                    await self._perform_gc()
                
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _create_memory_alert(self, usage: Dict[str, float]) -> None:
        """Create memory usage alert"""
        alert = SystemAlert(
            alert_id=f"memory_{int(time.time())}",
            level=AlertLevel.WARNING if usage["percent"] < 90 else AlertLevel.CRITICAL,
            resource_type=ResourceType.MEMORY,
            metric=PerformanceMetric.MEMORY_USAGE,
            current_value=usage["percent"],
            threshold_value=self.config.memory_threshold_percent,
            message=f"Memory usage at {usage['percent']:.1f}% ({usage['rss_mb']:.1f} MB)"
        )
        self.memory_alerts.append(alert)
    
    async def _perform_gc(self) -> None:
        """Perform garbage collection"""
        before_objects = len(gc.get_objects())
        collected = gc.collect()
        after_objects = len(gc.get_objects())
        
        self.gc_stats["collections"] = self.gc_stats["collections"] + 1
        self.gc_stats["freed_objects"] = before_objects - after_objects
        self.gc_stats["last_collection"] = datetime.now()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        current_usage = self.get_memory_usage()
        
        return {
            "current": current_usage,
            "gc_stats": self.gc_stats,
            "snapshots_count": len(self.memory_snapshots),
            "alerts_count": len(self.memory_alerts),
            "profiling_enabled": self.config.memory_profiling_enabled
        }


class PerformanceProfiler:
    """Real-time performance profiling and monitoring"""
    
    def __init__(self, config: PerformanceConfig) -> None:
        self.config = config
        self.performance_snapshots: deque = deque(maxlen=2000)
        self.operation_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.bottlenecks: List[Dict[str, Any]] = []
        self.profiling_enabled = config.enable_profiling
        
        # Performance counters
        self.counters = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0
        }
    
    @asynccontextmanager
    async def profile_operation(self, operation_name: str) -> None:
        """Context manager for profiling operations"""
        start_time = time.time()
        start_memory = 0
        if self.profiling_enabled:
            try:
                process = psutil.Process()
                start_memory = process.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                start_memory = 0
        
        try:
            yield
            self.counters["successful_requests"] += 1
        except Exception as e:
            self.counters["failed_requests"] += 1
            raise
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            
            self.operation_times[operation_name].append(duration)
            self.counters["total_requests"] += 1
            self.counters["total_response_time"] += duration
            
            if self.profiling_enabled:
                try:
                    process = psutil.Process()
                    end_memory = process.memory_info().rss
                    memory_delta = (end_memory - start_memory) / 1024 / 1024  # MB
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    memory_delta = 0.0
                
                await self._record_operation(operation_name, duration, memory_delta)
    
    async def _record_operation(self, operation: str, duration: float, memory_delta: float) -> None:
        """Record operation performance data"""
        snapshot = {
            "operation": operation,
            "duration_ms": duration,
            "memory_delta_mb": memory_delta,
            "timestamp": datetime.now(),
            "cpu_percent": psutil.cpu_percent()
        }
        
        self.performance_snapshots.append(snapshot)
        
        # Detect bottlenecks
        if duration > 1000:  # > 1 second
            bottleneck = {
                "operation": operation,
                "duration_ms": duration,
                "severity": "high" if duration > 5000 else "medium",
                "timestamp": datetime.now()
            }
            self.bottlenecks.append(bottleneck)
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for specific operation"""
        times = list(self.operation_times.get(operation, []))
        if not times:
            return {"operation": operation, "count": 0}
        
        return {
            "operation": operation,
            "count": len(times),
            "avg_duration_ms": sum(times) / len(times),
            "min_duration_ms": min(times),
            "max_duration_ms": max(times),
            "p95_duration_ms": sorted(times)[int(len(times) * 0.95)] if times else 0
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        total_requests = self.counters["total_requests"]
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.counters["successful_requests"],
            "failed_requests": self.counters["failed_requests"],
            "success_rate": (self.counters["successful_requests"] / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time_ms": (self.counters["total_response_time"] / total_requests) if total_requests > 0 else 0,
            "bottlenecks_count": len(self.bottlenecks),
            "operations_tracked": len(self.operation_times)
        }


class ResourceMonitor:
    """Comprehensive system resource monitoring"""
    
    def __init__(self, config: PerformanceConfig) -> None:
        self.config = config
        self.resource_history: deque = deque(maxlen=1000)
        self.alerts: List[SystemAlert] = []
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self) -> None:
        """Start continuous resource monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = await self._collect_resource_metrics()
                self.resource_history.append(metrics)
                
                # Check for threshold violations
                await self._check_thresholds(metrics)
                
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _collect_resource_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics"""
        # CPU metrics - ensure we get a float value
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if isinstance(cpu_percent, list):
            cpu_percent = sum(cpu_percent) / len(cpu_percent) if cpu_percent else 0.0
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        try:
            network = psutil.net_io_counters()
            if network and hasattr(network, 'bytes_sent') and hasattr(network, 'bytes_recv'):
                network_sent_mb = network.bytes_sent / 1024 / 1024
                network_recv_mb = network.bytes_recv / 1024 / 1024
            else:
                network_sent_mb = 0.0
                network_recv_mb = 0.0
        except (AttributeError, TypeError):
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        
        # Process metrics
        try:
            process = psutil.Process()
            connection_count = len(process.connections())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            connection_count = 0
        
        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_available_mb=memory.available / 1024 / 1024,
            disk_usage_percent=disk.percent,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            connection_count=connection_count,
            thread_count=process.num_threads(),
            process_count=len(psutil.pids()),
            load_average=psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0.0, 0.0, 0.0)
        )
    
    async def _check_thresholds(self, metrics: ResourceMetrics) -> None:
        """Check resource thresholds and create alerts"""
        alerts_to_create = []
        
        # CPU threshold
        if metrics.cpu_percent > self.config.cpu_threshold_percent:
            alerts_to_create.append({
                "level": AlertLevel.WARNING if metrics.cpu_percent < 90 else AlertLevel.CRITICAL,
                "resource_type": ResourceType.CPU,
                "metric": PerformanceMetric.CPU_USAGE,
                "current_value": metrics.cpu_percent,
                "threshold_value": self.config.cpu_threshold_percent,
                "message": f"CPU usage at {metrics.cpu_percent:.1f}%"
            })
        
        # Memory threshold
        if metrics.memory_percent > self.config.memory_threshold_percent:
            alerts_to_create.append({
                "level": AlertLevel.WARNING if metrics.memory_percent < 90 else AlertLevel.CRITICAL,
                "resource_type": ResourceType.MEMORY,
                "metric": PerformanceMetric.MEMORY_USAGE,
                "current_value": metrics.memory_percent,
                "threshold_value": self.config.memory_threshold_percent,
                "message": f"Memory usage at {metrics.memory_percent:.1f}% ({metrics.memory_used_mb:.1f} MB)"
            })
        
        # Disk threshold
        if metrics.disk_usage_percent > self.config.disk_threshold_percent:
            alerts_to_create.append({
                "level": AlertLevel.WARNING if metrics.disk_usage_percent < 95 else AlertLevel.CRITICAL,
                "resource_type": ResourceType.DISK,
                "metric": PerformanceMetric.MEMORY_USAGE,
                "current_value": metrics.disk_usage_percent,
                "threshold_value": self.config.disk_threshold_percent,
                "message": f"Disk usage at {metrics.disk_usage_percent:.1f}%"
            })
        
        # Create alerts
        for alert_data in alerts_to_create:
            alert = SystemAlert(
                alert_id=f"{alert_data['resource_type'].value}_{int(time.time())}",
                **alert_data
            )
            self.alerts.append(alert)
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get most recent resource metrics"""
        return self.resource_history[-1] if self.resource_history else None
    
    def get_resource_trends(self, hours: int = 1) -> Dict[str, List[float]]:
        """Get resource usage trends over time"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.resource_history 
            if m.timestamp > cutoff_time
        ]
        
        return {
            "cpu_percent": [m.cpu_percent for m in recent_metrics],
            "memory_percent": [m.memory_percent for m in recent_metrics],
            "disk_usage_percent": [m.disk_usage_percent for m in recent_metrics],
            "timestamps": [m.timestamp.isoformat() for m in recent_metrics]
        }


class PerformanceManager:
    """
    Comprehensive Performance Optimization & Resource Management System
    
    Provides enterprise-grade performance optimization including connection pooling,
    rate limiting, memory management, performance profiling, and resource monitoring.
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None) -> None:
        self.config = config or PerformanceConfig()
        
        # Core components
        self.connection_pool_manager = ConnectionPoolManager(self.config)
        self.rate_limit_manager = RateLimitManager(self.config)
        self.memory_manager = MemoryManager(self.config)
        self.performance_profiler = PerformanceProfiler(self.config)
        self.resource_monitor = ResourceMonitor(self.config)
        
        # Task management
        self.async_pool: Optional[AioPool] = None
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Performance optimization
        self.optimization_strategies: Set[OptimizationStrategy] = set()
        
        # Integration with existing components
        self.circuit_breaker_manager = None
        self.cache_manager = None
        self.analytics_client = None
        self.background_collector = None
        
        # Statistics
        self.startup_time = datetime.now()
        self.performance_stats = {
            "total_optimizations": 0,
            "performance_improvements": {},
            "resource_savings": {}
        }
    
    async def initialize(self) -> None:
        """Initialize performance manager and all components"""
        try:
            # Initialize async pool for concurrent tasks
            if self.config.enable_async_optimization:
                self.async_pool = AioPool(size=self.config.max_concurrent_tasks)
            
            # Start monitoring tasks
            if self.config.enable_memory_monitoring:
                task = asyncio.create_task(self.memory_manager.monitor_memory())
                self.background_tasks.add(task)
            
            if self.config.enable_resource_monitoring:
                await self.resource_monitor.start_monitoring()
            
            # Initialize integrations with existing components
            await self._initialize_integrations()
            
            # Apply optimization strategies
            await self._apply_optimizations()
            
        except Exception as e:
            raise RuntimeError(f"Performance manager initialization failed: {e}")
    
    async def _initialize_integrations(self) -> None:
        """Initialize integrations with existing Phase 3 components"""
        try:
            # Circuit breaker integration
            self.circuit_breaker_manager = get_circuit_breaker_manager()
            
            # Cache manager integration
            self.cache_manager = await get_cache_manager()
            
            # Analytics client integration
            self.analytics_client = await get_analytics_client()
            
            # Background collector integration
            self.background_collector = await get_background_collector()
            
        except Exception as e:
            print(f"Integration initialization warning: {e}")
    
    async def _apply_optimizations(self) -> None:
        """Apply performance optimization strategies"""
        
        # Connection pooling optimization
        if self.config.enable_connection_pooling:
            await self._setup_connection_pools()
            self.optimization_strategies.add(OptimizationStrategy.CONNECTION_POOLING)
        
        # Memory optimization
        if self.config.enable_auto_gc:
            self.optimization_strategies.add(OptimizationStrategy.MEMORY_OPTIMIZATION)
        
        # Caching optimization
        if self.cache_manager:
            self.optimization_strategies.add(OptimizationStrategy.CACHING)
        
        # Rate limiting optimization
        if self.rate_limit_manager.get_limiter():
            self.optimization_strategies.add(OptimizationStrategy.RATE_LIMITING)
    
    async def _setup_connection_pools(self) -> None:
        """Setup connection pools for various services"""
        try:
            # Analytics engine connection pool
            if self.analytics_client:
                await self.connection_pool_manager.create_pool(
                    "analytics_engine",
                    connection_factory=lambda: None,  # Placeholder
                    max_size=20,
                    min_size=2
                )
            
            # Cache connection pool
            if self.cache_manager:
                await self.connection_pool_manager.create_pool(
                    "cache_backend",
                    connection_factory=lambda: None,  # Placeholder
                    max_size=30,
                    min_size=3
                )
        
        except Exception as e:
            print(f"Connection pool setup warning: {e}")
    
    # Public API methods
    
    @asynccontextmanager
    async def profile_operation(self, operation_name: str) -> None:
        """Profile a specific operation"""
        async with self.performance_profiler.profile_operation(operation_name):
            yield
    
    @asynccontextmanager
    async def get_connection(self, pool_name: str) -> None:
        """Get connection from specified pool"""
        async with self.connection_pool_manager.get_connection(pool_name) as conn:
            yield conn
    
    async def execute_with_rate_limit(self, 
                                    operation: Callable,
                                    endpoint: str = "default",
                                    *args, **kwargs) -> Any:
        """Execute operation with rate limiting"""
        # Check rate limits (implementation depends on FastAPI integration)
        # For now, just execute the operation
        async with self.profile_operation(f"rate_limited_{endpoint}"):
            return await operation(*args, **kwargs)
    
    async def optimize_memory_usage(self) -> None:
        """Trigger memory optimization"""
        await self.memory_manager._perform_gc()
        self.performance_stats["total_optimizations"] += 1
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        current_metrics = self.resource_monitor.get_current_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
            "optimization_strategies": [s.value for s in self.optimization_strategies],
            "performance_summary": self.performance_profiler.get_performance_summary(),
            "memory_stats": self.memory_manager.get_memory_stats(),
            "resource_metrics": current_metrics.to_dict() if current_metrics else {},
            "connection_pools": await self.connection_pool_manager.get_all_stats(),
            "alerts": {
                "memory": len(self.memory_manager.memory_alerts),
                "resource": len(self.resource_monitor.alerts),
                "active": len([a for a in self.resource_monitor.alerts if not a.resolved])
            },
            "statistics": self.performance_stats
        }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations"""
        recommendations = []
        current_metrics = self.resource_monitor.get_current_metrics()
        
        if current_metrics:
            # Memory recommendations
            if current_metrics.memory_percent > 70:
                recommendations.append({
                    "category": "memory",
                    "priority": "high" if current_metrics.memory_percent > 85 else "medium",
                    "recommendation": "Consider increasing memory limits or optimizing memory usage",
                    "current_value": current_metrics.memory_percent,
                    "target_value": 70
                })
            
            # CPU recommendations
            if current_metrics.cpu_percent > 80:
                recommendations.append({
                    "category": "cpu",
                    "priority": "high",
                    "recommendation": "Consider scaling horizontally or optimizing CPU-intensive operations",
                    "current_value": current_metrics.cpu_percent,
                    "target_value": 70
                })
        
        # Connection pool recommendations
        pool_stats = await self.connection_pool_manager.get_all_stats()
        for pool_name, stats in pool_stats.items():
            utilization = stats.get("active_connections", 0) / stats.get("max_size", 1)
            if utilization > 0.8:
                recommendations.append({
                    "category": "connections",
                    "priority": "medium",
                    "recommendation": f"Consider increasing {pool_name} pool size",
                    "current_value": utilization * 100,
                    "target_value": 70
                })
        
        return recommendations
    
    async def shutdown(self) -> None:
        """Shutdown performance manager and cleanup resources"""
        try:
            # Stop monitoring
            await self.resource_monitor.stop_monitoring()
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close connection pools
            await self.connection_pool_manager.shutdown()
            
            # Close async pool
            if self.async_pool:
                await self.async_pool.close()
            
        except Exception as e:
            print(f"Performance manager shutdown error: {e}")


# Global performance manager instance
_performance_manager: Optional[PerformanceManager] = None


async def get_performance_manager() -> PerformanceManager:
    """Get global performance manager instance"""
    global _performance_manager
    if _performance_manager is None:
        _performance_manager = PerformanceManager()
        await _performance_manager.initialize()
    return _performance_manager


async def initialize_performance_manager(config: Optional[PerformanceConfig] = None) -> PerformanceManager:
    """Initialize global performance manager instance"""
    global _performance_manager
    _performance_manager = PerformanceManager(config)
    await _performance_manager.initialize()
    return _performance_manager


async def shutdown_performance_manager() -> None:
    """Shutdown global performance manager instance"""
    global _performance_manager
    if _performance_manager:
        await _performance_manager.shutdown()
        _performance_manager = None


# Convenience functions for direct access
@asynccontextmanager
async def profile_operation(operation_name: str) -> None:
    """Profile operation using global performance manager"""
    manager = await get_performance_manager()
    async with manager.profile_operation(operation_name):
        yield


async def get_connection(pool_name: str) -> None:
    """Get connection from pool using global performance manager"""
    manager = await get_performance_manager()
    return manager.get_connection(pool_name)


async def get_performance_report() -> Dict[str, Any]:
    """Get performance report from global performance manager"""
    manager = await get_performance_manager()
    return await manager.get_performance_report()


async def optimize_memory() -> None:
    """Trigger memory optimization"""
    manager = await get_performance_manager()
    await manager.optimize_memory_usage() 