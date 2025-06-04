"""
Performance Optimizer for GraphMemory-IDE Analytics

This module provides performance optimization features including:
- Database query optimization
- Connection pool management
- Memory usage optimization
- Response time improvements
- Background task optimization

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncpg
import psutil
import gc

from .cache_manager import get_cache_manager, get_query_cache


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    query_execution_times: List[float]
    memory_usage: float
    connection_pool_size: int
    active_connections: int
    cache_hit_rate: float
    background_task_count: int
    response_times: List[float]
    
    def get_avg_query_time(self) -> float:
        """Get average query execution time."""
        return sum(self.query_execution_times) / len(self.query_execution_times) if self.query_execution_times else 0
    
    def get_avg_response_time(self) -> float:
        """Get average response time."""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0


class DatabaseOptimizer:
    """Database performance optimization."""
    
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self.db_pool = db_pool
        self.query_stats: Dict[str, List[float]] = {}
        self.slow_query_threshold = 1.0  # seconds
        
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze database query performance."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get query statistics from PostgreSQL
                query_stats = await conn.fetch("""
                    SELECT query, calls, total_time, mean_time, min_time, max_time
                    FROM pg_stat_statements
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY total_time DESC
                    LIMIT 20
                """)
                
                # Get database size and index usage
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                
                index_usage = await conn.fetch("""
                    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
                    FROM pg_stat_user_indexes
                    WHERE idx_scan > 0
                    ORDER BY idx_scan DESC
                    LIMIT 10
                """)
                
                # Get table statistics
                table_stats = await conn.fetch("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_live_tup, n_dead_tup
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                    LIMIT 10
                """)
                
                return {
                    "query_stats": [dict(row) for row in query_stats],
                    "database_size": db_size,
                    "index_usage": [dict(row) for row in index_usage],
                    "table_stats": [dict(row) for row in table_stats],
                    "slow_queries": [
                        dict(row) for row in query_stats 
                        if row['mean_time'] > self.slow_query_threshold * 1000
                    ]
                }
                
        except Exception as e:
            print(f"Error analyzing query performance: {e}")
            return {}
    
    async def optimize_connection_pool(self) -> Dict[str, Any]:
        """Optimize database connection pool settings."""
        try:
            current_pool_size = self.db_pool.get_size()
            max_pool_size = self.db_pool.get_max_size()
            min_pool_size = self.db_pool.get_min_size()
            
            # Get current connection usage
            async with self.db_pool.acquire() as conn:
                active_connections = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE state = 'active' AND datname = current_database()
                """)
                
                total_connections = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
            
            # Calculate optimal pool size based on usage
            usage_ratio = active_connections / max(total_connections, 1)
            
            recommendations = []
            if usage_ratio > 0.8:
                recommendations.append("Consider increasing max pool size")
            elif usage_ratio < 0.3:
                recommendations.append("Consider decreasing max pool size")
            
            return {
                "current_pool_size": current_pool_size,
                "max_pool_size": max_pool_size,
                "min_pool_size": min_pool_size,
                "active_connections": active_connections,
                "total_connections": total_connections,
                "usage_ratio": round(usage_ratio, 2),
                "recommendations": recommendations
            }
            
        except Exception as e:
            print(f"Error optimizing connection pool: {e}")
            return {}
    
    async def create_performance_indexes(self) -> List[str]:
        """Create performance-optimized indexes for analytics queries."""
        indexes_created = []
        
        try:
            async with self.db_pool.acquire() as conn:
                # Analytics events indexes
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                    idx_analytics_events_timestamp_type 
                    ON analytics_events(timestamp, event_type)
                """)
                indexes_created.append("idx_analytics_events_timestamp_type")
                
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                    idx_analytics_events_user_timestamp 
                    ON analytics_events(user_id, timestamp) 
                    WHERE user_id IS NOT NULL
                """)
                indexes_created.append("idx_analytics_events_user_timestamp")
                
                # Real-time metrics indexes
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                    idx_real_time_metrics_name_timestamp 
                    ON real_time_metrics(metric_name, timestamp DESC)
                """)
                indexes_created.append("idx_real_time_metrics_name_timestamp")
                
                # User journeys indexes
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                    idx_user_journeys_user_start_time 
                    ON user_journeys(user_id, start_time DESC) 
                    WHERE user_id IS NOT NULL
                """)
                indexes_created.append("idx_user_journeys_user_start_time")
                
                # Dashboard performance indexes
                await conn.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                    idx_dashboards_owner_updated 
                    ON dashboards(owner_id, updated_at DESC)
                """)
                indexes_created.append("idx_dashboards_owner_updated")
                
        except Exception as e:
            print(f"Error creating performance indexes: {e}")
        
        return indexes_created
    
    async def vacuum_and_analyze(self) -> Dict[str, Any]:
        """Perform database maintenance for optimal performance."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get table sizes before maintenance
                table_sizes_before = await conn.fetch("""
                    SELECT tablename, 
                           pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                           pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY size_bytes DESC
                """)
                
                # Analyze tables for query planner
                await conn.execute("ANALYZE")
                
                # Get table sizes after maintenance
                table_sizes_after = await conn.fetch("""
                    SELECT tablename, 
                           pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                           pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY size_bytes DESC
                """)
                
                return {
                    "maintenance_completed": True,
                    "table_sizes_before": [dict(row) for row in table_sizes_before],
                    "table_sizes_after": [dict(row) for row in table_sizes_after],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            print(f"Error performing database maintenance: {e}")
            return {"error": str(e)}


class MemoryOptimizer:
    """Memory usage optimization."""
    
    def __init__(self) -> None:
        """Initialize memory optimizer."""
        self._metrics: Dict[str, Any] = {}
        self.memory_stats: List[float] = []
        self.gc_stats: List[Dict[str, Any]] = []
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # System memory info
            virtual_memory = psutil.virtual_memory()
            
            return {
                "process_memory_mb": memory_info.rss / 1024 / 1024,
                "process_memory_percent": memory_percent,
                "system_memory_total_gb": virtual_memory.total / 1024 / 1024 / 1024,
                "system_memory_used_percent": virtual_memory.percent,
                "system_memory_available_gb": virtual_memory.available / 1024 / 1024 / 1024
            }
        except Exception as e:
            return {"error": f"Failed to get memory usage: {e}"}
    
    def optimize_garbage_collection(self) -> Dict[str, Any]:
        """Optimize Python garbage collection."""
        # Get GC stats before optimization
        gc_stats_before = {
            "collections": gc.get_stats(),
            "count": gc.get_count(),
            "threshold": gc.get_threshold()
        }
        
        # Force garbage collection
        collected = gc.collect()
        
        # Get GC stats after optimization
        gc_stats_after = {
            "collections": gc.get_stats(),
            "count": gc.get_count(),
            "threshold": gc.get_threshold()
        }
        
        # Optimize GC thresholds for analytics workload
        # More frequent collection of generation 0, less frequent for 1 and 2
        gc.set_threshold(500, 10, 10)
        
        result = {
            "objects_collected": collected,
            "gc_stats_before": gc_stats_before,
            "gc_stats_after": gc_stats_after,
            "new_threshold": gc.get_threshold(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.gc_stats.append(result)
        return result
    
    def monitor_memory_leaks(self) -> List[Dict[str, Any]]:
        """Monitor for potential memory leaks."""
        current_memory = self.get_memory_usage()
        self.memory_stats.append(current_memory["process_memory_mb"])
        
        # Keep only last 100 measurements
        if len(self.memory_stats) > 100:
            self.memory_stats = self.memory_stats[-100:]
        
        # Detect memory leaks (consistent upward trend)
        if len(self.memory_stats) >= 10:
            recent_trend = []
            for i in range(1, min(10, len(self.memory_stats))):
                recent_trend.append(self.memory_stats[-i] - self.memory_stats[-i-1])
            
            avg_trend = sum(recent_trend) / len(recent_trend)
            
            return [{
                "memory_trend_mb_per_measurement": round(avg_trend, 2),
                "potential_leak": avg_trend > 1.0,  # Growing by > 1MB per measurement
                "current_memory_mb": current_memory["process_memory_mb"],
                "measurements_count": len(self.memory_stats),
                "timestamp": datetime.utcnow().isoformat()
            }]
        
        return []


class ResponseTimeOptimizer:
    """Response time optimization."""
    
    def __init__(self) -> None:
        self.response_times: Dict[str, List[float]] = {}
        self.slow_endpoints: List[Dict[str, Any]] = []
    
    def record_response_time(self, endpoint: str, response_time: float) -> None:
        """Record response time for an endpoint."""
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        
        self.response_times[endpoint].append(response_time)
        
        # Keep only last 1000 measurements per endpoint
        if len(self.response_times[endpoint]) > 1000:
            self.response_times[endpoint] = self.response_times[endpoint][-1000:]
        
        # Track slow endpoints
        if response_time > 2.0:  # Slower than 2 seconds
            self.slow_endpoints.append({
                "endpoint": endpoint,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep only last 100 slow endpoint records
            if len(self.slow_endpoints) > 100:
                self.slow_endpoints = self.slow_endpoints[-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all endpoints."""
        summary = {}
        
        for endpoint, times in self.response_times.items():
            if times:
                summary[endpoint] = {
                    "avg_response_time": round(sum(times) / len(times), 3),
                    "min_response_time": round(min(times), 3),
                    "max_response_time": round(max(times), 3),
                    "request_count": len(times),
                    "p95_response_time": round(sorted(times)[int(len(times) * 0.95)], 3) if len(times) > 20 else None
                }
        
        return {
            "endpoint_performance": summary,
            "slow_endpoints": self.slow_endpoints[-10:],  # Last 10 slow requests
            "total_endpoints": len(self.response_times),
            "timestamp": datetime.utcnow().isoformat()
        }


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self, db_pool: asyncpg.Pool, settings) -> None:
        self.db_pool = db_pool
        self.settings = settings
        
        self.db_optimizer = DatabaseOptimizer(db_pool)
        self.memory_optimizer = MemoryOptimizer()
        self.response_optimizer = ResponseTimeOptimizer()
        
        # Background optimization task
        self._optimization_task: Optional[asyncio.Task] = None
        self._metrics: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize performance optimization."""
        try:
            # Create performance indexes
            indexes_created = await self.db_optimizer.create_performance_indexes()
            print(f"Created {len(indexes_created)} performance indexes")
            
            # Start background optimization
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            
            print("Performance optimizer initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize performance optimizer: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown performance optimizer."""
        if self._optimization_task:
            self._optimization_task.cancel()
    
    async def run_full_optimization(self) -> Dict[str, Any]:
        """Run comprehensive performance optimization."""
        results: Dict[str, Any] = {}
        
        try:
            # Database optimization
            print("Running database optimization...")
            results["database_analysis"] = await self.db_optimizer.analyze_query_performance()
            results["connection_pool"] = await self.db_optimizer.optimize_connection_pool()
            results["database_maintenance"] = await self.db_optimizer.vacuum_and_analyze()
            
            # Memory optimization
            print("Optimizing memory usage...")
            results["memory_usage"] = self.memory_optimizer.get_memory_usage()
            results["garbage_collection"] = self.memory_optimizer.optimize_garbage_collection()
            memory_leaks = self.memory_optimizer.monitor_memory_leaks()
            results["memory_leaks"] = memory_leaks
            
            # Response time optimization
            print("Analyzing response times...")
            results["response_performance"] = self.response_optimizer.get_performance_summary()
            
            # Cache performance
            cache_manager = get_cache_manager()
            if cache_manager:
                cache_stats = await cache_manager.get_cache_stats()
                results["cache_stats"] = cache_stats
            
            results["optimization_completed"] = True
            results["timestamp"] = datetime.utcnow().isoformat()
            
            return results
            
        except Exception as e:
            print(f"Error during full optimization: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def _optimization_loop(self) -> None:
        """Background optimization loop."""
        while True:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                # Memory monitoring
                self.memory_optimizer.monitor_memory_leaks()
                
                # Periodic garbage collection
                if len(self.memory_optimizer.memory_stats) % 10 == 0:
                    self.memory_optimizer.optimize_garbage_collection()
                
                print("Background optimization cycle completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in optimization loop: {e}")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # Collect query times from cache
        query_cache = get_query_cache()
        query_times = []
        
        # Get memory usage
        memory_info = self.memory_optimizer.get_memory_usage()
        
        # Get cache hit rate
        cache_manager = get_cache_manager()
        cache_hit_rate = 0.0
        if cache_manager:
            total_ops = cache_manager.cache_hits + cache_manager.cache_misses
            if total_ops > 0:
                cache_hit_rate = cache_manager.cache_hits / total_ops
        
        # Get response times
        response_times = []
        for times in self.response_optimizer.response_times.values():
            response_times.extend(times[-10:])  # Last 10 for each endpoint
        
        return PerformanceMetrics(
            query_execution_times=query_times,
            memory_usage=memory_info["process_memory_mb"],
            connection_pool_size=self.db_pool.get_size(),
            active_connections=0,  # Would need to query database
            cache_hit_rate=cache_hit_rate,
            background_task_count=1 if self._optimization_task and not self._optimization_task.done() else 0,
            response_times=response_times
        )


# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None


async def initialize_performance_optimizer(db_pool: asyncpg.Pool, settings) -> None:
    """Initialize performance optimizer."""
    global _performance_optimizer
    _performance_optimizer = PerformanceOptimizer(db_pool, settings)
    await _performance_optimizer.initialize()


def get_performance_optimizer() -> Optional[PerformanceOptimizer]:
    """Get performance optimizer instance."""
    return _performance_optimizer


async def shutdown_performance_optimizer() -> None:
    """Shutdown performance optimizer."""
    global _performance_optimizer
    if _performance_optimizer:
        await _performance_optimizer.shutdown()
        _performance_optimizer = None 