"""
Performance Optimization API Routes for GraphMemory-IDE

This module provides REST API endpoints for:
- Performance monitoring and optimization
- Cache management and statistics
- Database optimization controls
- Load testing execution
- Memory and resource monitoring

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from .performance_optimizer import get_performance_optimizer, PerformanceMetrics
from .cache_manager import get_cache_manager, CacheType
from .load_tester import get_load_test_suite, LoadTestConfig


router = APIRouter(prefix="/api/v1/performance", tags=["performance"])


@router.get("/status")
async def get_performance_status():
    """Get current performance status and metrics."""
    try:
        performance_optimizer = get_performance_optimizer()
        cache_manager = get_cache_manager()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        # Get current metrics
        metrics = performance_optimizer.get_current_metrics()
        
        # Get cache stats
        cache_stats = {}
        if cache_manager:
            cache_stats = await cache_manager.get_cache_stats()
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": {
                "memory_usage_mb": metrics.memory_usage,
                "connection_pool_size": metrics.connection_pool_size,
                "active_connections": metrics.active_connections,
                "cache_hit_rate": metrics.cache_hit_rate,
                "background_task_count": metrics.background_task_count,
                "avg_query_time": metrics.get_avg_query_time(),
                "avg_response_time": metrics.get_avg_response_time()
            },
            "cache_stats": cache_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance status: {str(e)}")


@router.post("/optimize")
async def run_performance_optimization(background_tasks: BackgroundTasks):
    """Run comprehensive performance optimization."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        # Run optimization in background
        background_tasks.add_task(performance_optimizer.run_full_optimization)
        
        return {
            "status": "optimization_started",
            "message": "Performance optimization started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting optimization: {str(e)}")


@router.get("/optimization/results")
async def get_optimization_results():
    """Get results from the last performance optimization run."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        # Run optimization and return results
        results = await performance_optimizer.run_full_optimization()
        
        return {
            "status": "success",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting optimization results: {str(e)}")


@router.get("/cache/stats")
async def get_cache_statistics():
    """Get detailed cache performance statistics."""
    try:
        cache_manager = get_cache_manager()
        
        if not cache_manager:
            raise HTTPException(status_code=503, detail="Cache manager not available")
        
        stats = await cache_manager.get_cache_stats()
        
        return {
            "status": "success",
            "cache_statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache statistics: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(cache_type: Optional[str] = None, pattern: Optional[str] = None):
    """Clear cache entries by type or pattern."""
    try:
        cache_manager = get_cache_manager()
        
        if not cache_manager:
            raise HTTPException(status_code=503, detail="Cache manager not available")
        
        cleared_count = 0
        
        if pattern:
            # Clear by pattern
            cleared_count = await cache_manager.invalidate_pattern(pattern)
        elif cache_type:
            # Clear specific cache type
            try:
                cache_type_enum = CacheType(cache_type)
                # This would need to be implemented in cache_manager
                cleared_count = await cache_manager.invalidate_pattern(f"{cache_type_enum.value}:*")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid cache type: {cache_type}")
        else:
            raise HTTPException(status_code=400, detail="Either cache_type or pattern must be specified")
        
        return {
            "status": "success",
            "cleared_entries": cleared_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.get("/database/analysis")
async def get_database_analysis():
    """Get database performance analysis."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        # Get database analysis
        analysis = await performance_optimizer.db_optimizer.analyze_query_performance()
        pool_info = await performance_optimizer.db_optimizer.optimize_connection_pool()
        
        return {
            "status": "success",
            "database_analysis": analysis,
            "connection_pool_info": pool_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting database analysis: {str(e)}")


@router.post("/database/maintenance")
async def run_database_maintenance(background_tasks: BackgroundTasks):
    """Run database maintenance (VACUUM and ANALYZE)."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        # Run maintenance in background
        async def maintenance_task():
            return await performance_optimizer.db_optimizer.vacuum_and_analyze()
        
        background_tasks.add_task(maintenance_task)
        
        return {
            "status": "maintenance_started",
            "message": "Database maintenance started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting database maintenance: {str(e)}")


@router.get("/memory/usage")
async def get_memory_usage():
    """Get current memory usage statistics."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        memory_info = performance_optimizer.memory_optimizer.get_memory_usage()
        leak_info = performance_optimizer.memory_optimizer.monitor_memory_leaks()
        
        return {
            "status": "success",
            "memory_usage": memory_info,
            "memory_leak_analysis": leak_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory usage: {str(e)}")


@router.post("/memory/gc")
async def force_garbage_collection():
    """Force garbage collection to free memory."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        gc_result = performance_optimizer.memory_optimizer.optimize_garbage_collection()
        
        return {
            "status": "success",
            "garbage_collection_result": gc_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running garbage collection: {str(e)}")


@router.get("/response-times")
async def get_response_time_analysis():
    """Get response time analysis for all endpoints."""
    try:
        performance_optimizer = get_performance_optimizer()
        
        if not performance_optimizer:
            raise HTTPException(status_code=503, detail="Performance optimizer not available")
        
        performance_summary = performance_optimizer.response_optimizer.get_performance_summary()
        
        return {
            "status": "success",
            "response_time_analysis": performance_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting response time analysis: {str(e)}")


@router.post("/load-test")
async def run_load_test(
    concurrent_users: int = 10,
    test_duration_seconds: int = 60,
    endpoints: List[str] = None,
    include_websocket: bool = True,
    include_database: bool = True
):
    """Run comprehensive load test."""
    try:
        load_test_suite = get_load_test_suite()
        
        if not load_test_suite:
            raise HTTPException(status_code=503, detail="Load test suite not available")
        
        if endpoints is None:
            endpoints = [
                "/api/v1/analytics/dashboards",
                "/api/v1/analytics/events",
                "/api/v1/analytics/metrics",
                "/api/v1/performance/status"
            ]
        
        # Create load test configuration
        config = LoadTestConfig(
            concurrent_users=concurrent_users,
            test_duration_seconds=test_duration_seconds,
            endpoints_to_test=endpoints,
            include_websocket_tests=include_websocket,
            include_database_tests=include_database
        )
        
        # Run load test
        results = await load_test_suite.run_comprehensive_load_test(config)
        
        # Generate report
        report = load_test_suite.generate_load_test_report(results)
        
        return {
            "status": "success",
            "load_test_results": results,
            "report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running load test: {str(e)}")


@router.get("/load-test/config")
async def get_load_test_config():
    """Get default load test configuration options."""
    return {
        "status": "success",
        "default_config": {
            "concurrent_users": 10,
            "test_duration_seconds": 60,
            "ramp_up_seconds": 10,
            "request_rate_per_second": 5,
            "include_websocket_tests": True,
            "include_database_tests": True,
            "include_cache_tests": True
        },
        "available_endpoints": [
            "/api/v1/analytics/dashboards",
            "/api/v1/analytics/events",
            "/api/v1/analytics/metrics",
            "/api/v1/analytics/alerts",
            "/api/v1/performance/status",
            "/api/v1/auth/status"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/benchmarks")
async def get_performance_benchmarks():
    """Get performance benchmarks and targets."""
    return {
        "status": "success",
        "benchmarks": {
            "response_time_targets": {
                "api_endpoints": {
                    "target_avg_ms": 200,
                    "target_p95_ms": 500,
                    "target_p99_ms": 1000
                },
                "database_queries": {
                    "target_avg_ms": 100,
                    "target_p95_ms": 300,
                    "target_p99_ms": 500
                },
                "websocket_messages": {
                    "target_avg_ms": 50,
                    "target_p95_ms": 100,
                    "target_p99_ms": 200
                }
            },
            "throughput_targets": {
                "api_requests_per_second": 1000,
                "database_queries_per_second": 500,
                "websocket_messages_per_second": 2000
            },
            "resource_targets": {
                "memory_usage_mb": 512,
                "cpu_usage_percent": 70,
                "cache_hit_rate_percent": 85
            },
            "error_rate_targets": {
                "api_error_rate_percent": 1.0,
                "database_error_rate_percent": 0.1,
                "websocket_error_rate_percent": 2.0
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health")
async def get_performance_health():
    """Get overall performance health status."""
    try:
        performance_optimizer = get_performance_optimizer()
        cache_manager = get_cache_manager()
        
        health_status = "healthy"
        issues = []
        
        if performance_optimizer:
            metrics = performance_optimizer.get_current_metrics()
            
            # Check memory usage
            if metrics.memory_usage > 1024:  # > 1GB
                health_status = "warning"
                issues.append("High memory usage detected")
            
            # Check cache hit rate
            if metrics.cache_hit_rate < 0.7:  # < 70%
                health_status = "warning"
                issues.append("Low cache hit rate")
            
            # Check response times
            avg_response_time = metrics.get_avg_response_time()
            if avg_response_time > 1.0:  # > 1 second
                health_status = "critical"
                issues.append("High average response time")
        else:
            health_status = "critical"
            issues.append("Performance optimizer not available")
        
        if not cache_manager:
            health_status = "warning"
            issues.append("Cache manager not available")
        
        return {
            "status": health_status,
            "issues": issues,
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": [
                "Monitor memory usage regularly",
                "Optimize slow database queries",
                "Increase cache TTL for stable data",
                "Consider horizontal scaling for high load"
            ]
        }
        
    except Exception as e:
        return {
            "status": "critical",
            "issues": [f"Error checking performance health: {str(e)}"],
            "timestamp": datetime.utcnow().isoformat()
        } 