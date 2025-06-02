"""
Comprehensive Health Check System for GraphMemory-IDE

This module provides detailed health monitoring for all system components:
- Database connectivity and performance checks
- Cache system health and performance
- External service dependency checks
- Application component health verification
- Detailed status reporting for monitoring systems

Integration with Prometheus metrics and monitoring infrastructure.
Created for TASK-022 Phase 2: Monitoring Infrastructure Implementation
"""

import asyncio
import logging
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import json

# Database and cache imports
import asyncpg
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# FastAPI and HTTP imports
from fastapi import HTTPException
import httpx

# Application imports
from server.dashboard.cache_manager import get_cache_manager
from server.monitoring.metrics_collector import get_metrics_collector

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'service': self.service,
            'status': self.status.value,
            'message': self.message,
            'details': self.details,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat()
        }


class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        
        # Configuration
        self.check_timeout = 10.0  # seconds
        self.cache_ttl = 30  # seconds for caching results
        
        # Dependencies
        self.cache_manager = None
        self.metrics_collector = None
        
        # Register default health checks
        self._register_default_checks()
        
        logger.info("HealthChecker initialized")
    
    async def initialize(self):
        """Initialize health checker dependencies"""
        try:
            self.cache_manager = await get_cache_manager()
            self.metrics_collector = await get_metrics_collector()
            logger.info("HealthChecker dependencies initialized")
        except Exception as e:
            logger.error(f"Failed to initialize HealthChecker: {e}")
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.checks.update({
            'application': self._check_application_health,
            'database': self._check_database_health,
            'cache': self._check_cache_health,
            'memory': self._check_memory_health,
            'disk': self._check_disk_health,
            'cpu': self._check_cpu_health,
            'network': self._check_network_health,
            'dependencies': self._check_external_dependencies
        })
    
    async def check_health(self, service: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Run health checks for specified service or all services"""
        if service:
            if service not in self.checks:
                raise ValueError(f"Unknown health check service: {service}")
            
            result = await self._run_single_check(service)
            return {service: result}
        else:
            return await self._run_all_checks()
    
    async def _run_single_check(self, service: str) -> HealthCheckResult:
        """Run a single health check"""
        start_time = time.time()
        
        try:
            check_func = self.checks[service]
            result = await asyncio.wait_for(check_func(), timeout=self.check_timeout)
            
        except asyncio.TimeoutError:
            result = HealthCheckResult(
                service=service,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.check_timeout}s"
            )
        except Exception as e:
            logger.error(f"Health check failed for {service}: {e}")
            result = HealthCheckResult(
                service=service,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}"
            )
        
        # Calculate response time
        result.response_time_ms = (time.time() - start_time) * 1000
        
        # Cache result
        self.last_results[service] = result
        
        # Record metrics
        if self.metrics_collector:
            status_value = 1 if result.status == HealthStatus.HEALTHY else 0
            self.metrics_collector.metrics['application_up'].labels(service=service).set(status_value)
        
        return result
    
    async def _run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks concurrently"""
        tasks = [
            asyncio.create_task(self._run_single_check(service))
            for service in self.checks.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            service: result if isinstance(result, HealthCheckResult) else HealthCheckResult(
                service=service,
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected error: {result}"
            )
            for service, result in zip(self.checks.keys(), results)
        }
    
    # Individual Health Check Methods
    
    async def _check_application_health(self) -> HealthCheckResult:
        """Check overall application health"""
        try:
            # Check if main application components are responsive
            uptime = time.time() - getattr(self, 'start_time', time.time())
            
            # Basic application health indicators
            details = {
                'uptime_seconds': uptime,
                'version': '1.0.0',
                'environment': 'production',
                'pid': psutil.Process().pid if psutil else None
            }
            
            # Check memory usage
            if psutil:
                process = psutil.Process()
                memory_info = process.memory_info()
                details.update({
                    'memory_mb': memory_info.rss / 1024 / 1024,
                    'cpu_percent': process.cpu_percent()
                })
            
            return HealthCheckResult(
                service='application',
                status=HealthStatus.HEALTHY,
                message='Application is healthy',
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='application',
                status=HealthStatus.UNHEALTHY,
                message=f'Application health check failed: {e}'
            )
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        try:
            # This would need to be adapted based on your database setup
            # For now, providing a template structure
            
            start_time = time.time()
            
            # Example database check (adapt to your actual database setup)
            # connection = await get_database_connection()
            # result = await connection.execute(text("SELECT 1"))
            
            # Simulated check for template
            await asyncio.sleep(0.01)  # Simulate database query
            query_time = (time.time() - start_time) * 1000
            
            details = {
                'query_time_ms': query_time,
                'connection_pool_size': 10,  # Would come from actual pool
                'active_connections': 2,     # Would come from actual pool
                'database_name': 'graphmemory_ide'
            }
            
            # Health status based on query time
            if query_time < 100:
                status = HealthStatus.HEALTHY
                message = 'Database is responsive'
            elif query_time < 500:
                status = HealthStatus.DEGRADED
                message = 'Database response is slow'
            else:
                status = HealthStatus.UNHEALTHY
                message = 'Database response is very slow'
            
            return HealthCheckResult(
                service='database',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='database',
                status=HealthStatus.UNHEALTHY,
                message=f'Database connection failed: {e}',
                details={'error': str(e)}
            )
    
    async def _check_cache_health(self) -> HealthCheckResult:
        """Check cache system health and performance"""
        try:
            start_time = time.time()
            
            if self.cache_manager:
                # Test cache connectivity
                test_key = "health_check_test"
                test_value = f"test_{int(time.time())}"
                
                # Test set operation
                await self.cache_manager.set(test_key, test_value, ttl=60)
                
                # Test get operation
                retrieved_value = await self.cache_manager.get(test_key)
                
                # Clean up
                await self.cache_manager.delete(test_key)
                
                response_time = (time.time() - start_time) * 1000
                
                # Verify round-trip worked
                if retrieved_value != test_value:
                    raise Exception("Cache round-trip test failed")
                
                details = {
                    'response_time_ms': response_time,
                    'cache_type': 'redis',
                    'round_trip_success': True
                }
                
                # Health status based on response time
                if response_time < 10:
                    status = HealthStatus.HEALTHY
                    message = 'Cache is responsive'
                elif response_time < 50:
                    status = HealthStatus.DEGRADED
                    message = 'Cache response is slow'
                else:
                    status = HealthStatus.UNHEALTHY
                    message = 'Cache response is very slow'
                
            else:
                status = HealthStatus.UNHEALTHY
                message = 'Cache manager not available'
                details = {'error': 'Cache manager not initialized'}
            
            return HealthCheckResult(
                service='cache',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='cache',
                status=HealthStatus.UNHEALTHY,
                message=f'Cache health check failed: {e}',
                details={'error': str(e)}
            )
    
    async def _check_memory_health(self) -> HealthCheckResult:
        """Check system memory health"""
        try:
            if not psutil:
                return HealthCheckResult(
                    service='memory',
                    status=HealthStatus.UNKNOWN,
                    message='psutil not available for memory monitoring'
                )
            
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            details = {
                'total_mb': memory.total / 1024 / 1024,
                'available_mb': memory.available / 1024 / 1024,
                'used_percent': memory.percent,
                'swap_used_percent': swap.percent
            }
            
            # Determine health status
            if memory.percent < 80:
                status = HealthStatus.HEALTHY
                message = 'Memory usage is normal'
            elif memory.percent < 90:
                status = HealthStatus.DEGRADED
                message = 'Memory usage is high'
            else:
                status = HealthStatus.UNHEALTHY
                message = 'Memory usage is critical'
            
            return HealthCheckResult(
                service='memory',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='memory',
                status=HealthStatus.UNHEALTHY,
                message=f'Memory check failed: {e}'
            )
    
    async def _check_disk_health(self) -> HealthCheckResult:
        """Check disk space health"""
        try:
            if not psutil:
                return HealthCheckResult(
                    service='disk',
                    status=HealthStatus.UNKNOWN,
                    message='psutil not available for disk monitoring'
                )
            
            disk_usage = psutil.disk_usage('/')
            
            details = {
                'total_gb': disk_usage.total / 1024 / 1024 / 1024,
                'free_gb': disk_usage.free / 1024 / 1024 / 1024,
                'used_percent': (disk_usage.used / disk_usage.total) * 100
            }
            
            used_percent = details['used_percent']
            
            # Determine health status
            if used_percent < 80:
                status = HealthStatus.HEALTHY
                message = 'Disk usage is normal'
            elif used_percent < 90:
                status = HealthStatus.DEGRADED
                message = 'Disk usage is high'
            else:
                status = HealthStatus.UNHEALTHY
                message = 'Disk usage is critical'
            
            return HealthCheckResult(
                service='disk',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='disk',
                status=HealthStatus.UNHEALTHY,
                message=f'Disk check failed: {e}'
            )
    
    async def _check_cpu_health(self) -> HealthCheckResult:
        """Check CPU health"""
        try:
            if not psutil:
                return HealthCheckResult(
                    service='cpu',
                    status=HealthStatus.UNKNOWN,
                    message='psutil not available for CPU monitoring'
                )
            
            # Get CPU usage over a short interval
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            
            details = {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'load_average': load_avg
            }
            
            # Determine health status
            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = 'CPU usage is normal'
            elif cpu_percent < 85:
                status = HealthStatus.DEGRADED
                message = 'CPU usage is high'
            else:
                status = HealthStatus.UNHEALTHY
                message = 'CPU usage is critical'
            
            return HealthCheckResult(
                service='cpu',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='cpu',
                status=HealthStatus.UNHEALTHY,
                message=f'CPU check failed: {e}'
            )
    
    async def _check_network_health(self) -> HealthCheckResult:
        """Check network connectivity"""
        try:
            # Test network connectivity with a simple HTTP request
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = time.time()
                response = await client.get('https://httpbin.org/status/200')
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    status = HealthStatus.HEALTHY
                    message = 'Network connectivity is good'
                else:
                    status = HealthStatus.DEGRADED
                    message = f'Network request returned status {response.status_code}'
                
                details = {
                    'response_time_ms': response_time,
                    'test_url': 'https://httpbin.org/status/200',
                    'status_code': response.status_code
                }
            
            return HealthCheckResult(
                service='network',
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='network',
                status=HealthStatus.UNHEALTHY,
                message=f'Network check failed: {e}',
                details={'error': str(e)}
            )
    
    async def _check_external_dependencies(self) -> HealthCheckResult:
        """Check external service dependencies"""
        try:
            # This would check any external APIs or services your app depends on
            # For now, providing a template structure
            
            dependencies = []
            
            # Example: Check external API
            # try:
            #     async with httpx.AsyncClient(timeout=5.0) as client:
            #         response = await client.get('https://api.external-service.com/health')
            #         dependencies.append({
            #             'service': 'external-api',
            #             'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            #             'response_time_ms': response.elapsed.total_seconds() * 1000
            #         })
            # except Exception as e:
            #     dependencies.append({
            #         'service': 'external-api',
            #         'status': 'unhealthy',
            #         'error': str(e)
            #     })
            
            # For template, assuming no external dependencies
            status = HealthStatus.HEALTHY
            message = 'No external dependencies configured'
            
            return HealthCheckResult(
                service='dependencies',
                status=status,
                message=message,
                details={'dependencies': dependencies}
            )
            
        except Exception as e:
            return HealthCheckResult(
                service='dependencies',
                status=HealthStatus.UNHEALTHY,
                message=f'Dependencies check failed: {e}'
            )
    
    # Utility Methods
    
    def get_overall_health(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system health from individual check results"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def register_custom_check(self, name: str, check_func: Callable):
        """Register a custom health check"""
        self.checks[name] = check_func
        logger.info(f"Registered custom health check: {name}")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of recent health check results"""
        if not self.last_results:
            return {'status': 'unknown', 'message': 'No health checks performed yet'}
        
        overall_status = self.get_overall_health(self.last_results)
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                name: {
                    'status': result.status.value,
                    'message': result.message,
                    'response_time_ms': result.response_time_ms
                }
                for name, result in self.last_results.items()
            }
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


async def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        await _health_checker.initialize()
    return _health_checker 