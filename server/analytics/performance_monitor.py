import time
import psutil
import logging
from typing import Dict, Any, Optional, Generator
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
ALGORITHM_DURATION = Histogram(
    'analytics_algorithm_duration_seconds',
    'Time spent executing analytics algorithms',
    ['algorithm', 'backend', 'graph_size']
)

ALGORITHM_REQUESTS = Counter(
    'analytics_algorithm_requests_total',
    'Total analytics algorithm requests',
    ['algorithm', 'backend', 'status']
)

GPU_MEMORY_USAGE = Gauge(
    'analytics_gpu_memory_bytes',
    'GPU memory usage in bytes'
)

CPU_MEMORY_USAGE = Gauge(
    'analytics_cpu_memory_bytes',
    'CPU memory usage in bytes'
)

GRAPH_PROCESSING_TIME = Histogram(
    'analytics_graph_processing_seconds',
    'Time spent processing graph operations',
    ['operation_type', 'graph_size_category']
)

GRAPH_NODES = Gauge(
    'analytics_graph_nodes_total',
    'Total number of nodes in the graph'
)

GRAPH_EDGES = Gauge(
    'analytics_graph_edges_total',
    'Total number of edges in the graph'
)

CACHE_HIT_RATE = Gauge(
    'analytics_cache_hit_rate',
    'Cache hit rate percentage'
)

class PerformanceMonitor:
    """Monitor algorithm performance and resource usage"""
    
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.cache_stats = {"hits": 0, "misses": 0}
    
    @contextmanager
    def monitor_algorithm(self, algorithm: str, backend: str, graph_size: str) -> Generator[None, None, None]:
        """Context manager for monitoring algorithm execution"""
        start_time = time.time()
        start_memory = self.process.memory_info().rss
        
        try:
            yield
            status = "success"
        except Exception as e:
            status = "error"
            logger.error(f"Algorithm {algorithm} failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            end_memory = self.process.memory_info().rss
            memory_delta = end_memory - start_memory
            
            # Record metrics
            ALGORITHM_DURATION.labels(
                algorithm=algorithm, 
                backend=backend, 
                graph_size=graph_size
            ).observe(duration)
            
            ALGORITHM_REQUESTS.labels(
                algorithm=algorithm,
                backend=backend,
                status=status
            ).inc()
            
            CPU_MEMORY_USAGE.set(end_memory)
            
            # Log performance data
            logger.info(
                f"Algorithm: {algorithm}, Backend: {backend}, "
                f"Duration: {duration:.3f}s, Memory Delta: {memory_delta/1024/1024:.1f}MB"
            )
    
    def monitor_graph_operation(self, operation_type: str, graph_size: str) -> None:
        """Monitor graph operations timing"""
        # Record the graph operation
        GRAPH_PROCESSING_TIME.labels(
            operation_type=operation_type,
            graph_size_category=self._categorize_graph_size(graph_size)
        ).observe(0.1)  # Placeholder timing
    
    def _categorize_graph_size(self, graph_size: str) -> str:
        """Categorize graph size for metrics"""
        try:
            size_int = int(graph_size)
            if size_int < 100:
                return "small"
            elif size_int < 1000:
                return "medium"
            elif size_int < 10000:
                return "large"
            else:
                return "extra_large"
        except (ValueError, TypeError):
            return "unknown"
    
    def record_cache_hit(self) -> None:
        """Record a cache hit"""
        self.cache_stats["hits"] += 1
        self._update_cache_hit_rate()
    
    def record_cache_miss(self) -> None:
        """Record a cache miss"""
        self.cache_stats["misses"] += 1
        if self.cache_stats["hits"] + self.cache_stats["misses"] > 0:
            self._update_cache_hit_rate()
    
    def _update_cache_hit_rate(self) -> None:
        """Update cache hit rate metric"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total > 0:
            hit_rate = self.cache_stats["hits"] / total
            CACHE_HIT_RATE.set(hit_rate)
            
            # Log cache performance when hit rate drops
            if hit_rate < 0.8:
                logger.warning(f"Cache hit rate low: {hit_rate:.2%}")
        else:
            CACHE_HIT_RATE.set(0)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available // (1024 * 1024),
            "memory_used_mb": memory.used // (1024 * 1024),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": disk.free // (1024 * 1024 * 1024),
            "process_memory_mb": self.process.memory_info().rss // (1024 * 1024),
            "process_cpu_percent": self.process.cpu_percent(),
            "cache_hit_rate": self._get_cache_hit_rate()
        }
    
    def _get_cache_hit_rate(self) -> float:
        """Get current cache hit rate"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total == 0:
            return 0.0
        return (self.cache_stats["hits"] / total) * 100
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        system_metrics = self.get_system_metrics()
        
        return {
            "timestamp": time.time(),
            "system_metrics": system_metrics,
            "cache_statistics": {
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "hit_rate_percent": self._get_cache_hit_rate()
            },
            "process_info": {
                "pid": self.process.pid,
                "create_time": self.process.create_time(),
                "num_threads": self.process.num_threads(),
                "open_files": len(self.process.open_files()),
                "connections": len(self.process.connections())
            }
        }
    
    def update_gpu_memory_usage(self, memory_bytes: int) -> None:
        """Update GPU memory usage metric"""
        GPU_MEMORY_USAGE.set(memory_bytes)
    
    def update_graph_size(self, node_count: int, edge_count: int) -> None:
        """Update graph size metrics"""
        GRAPH_NODES.set(node_count)
        GRAPH_EDGES.set(edge_count)
        
        # Log significant graph changes
        if node_count > 1000000:  # 1M nodes
            logger.info(f"Large graph detected: {node_count:,} nodes, {edge_count:,} edges")
    
    def reset_cache_stats(self) -> None:
        """Reset cache statistics"""
        self.cache_stats = {"hits": 0, "misses": 0}
        CACHE_HIT_RATE.set(0)


# Global instance for easy access
performance_monitor = PerformanceMonitor() 