"""
Comprehensive Metrics Collection System for GraphMemory-IDE

This module provides centralized metrics collection for all application components:
- API performance metrics (request rate, response time, error rate)
- Database performance metrics (connection pool, query performance)
- Business metrics (user activity, onboarding, collaboration)
- System health metrics (service status, resource utilization)
- Alert correlation metrics (alert generation, escalation)

Integration with Prometheus for monitoring and alerting.
Created for TASK-022 Phase 2: Monitoring Infrastructure Implementation
"""

import time
import logging
import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque

from prometheus_client import (
    Counter, Histogram, Gauge, Enum, Info, 
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from prometheus_client.multiprocess import MultiProcessCollector

# Import application components
from server.dashboard.cache_manager import get_cache_manager, CacheManager
from server.monitoring.alert_correlation_engine import get_correlation_engine, AlertCorrelationEngine
from server.monitoring.enhanced_notification_dispatcher import get_enhanced_notification_dispatcher, EnhancedNotificationDispatcher

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """Definition for a custom metric"""
    name: str
    metric_type: str  # counter, histogram, gauge, enum, info
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # for histograms
    states: Optional[List[str]] = None  # for enums


class GraphMemoryMetricsCollector:
    """Comprehensive metrics collector for GraphMemory-IDE"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.start_time = time.time()
        
        # External dependencies - Fix type annotations
        self.cache_manager: Optional[CacheManager] = None
        self.correlation_engine: Optional[AlertCorrelationEngine] = None
        self.notification_dispatcher: Optional[EnhancedNotificationDispatcher] = None
        
        # Performance tracking
        self.request_times: deque = deque(maxlen=1000)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.user_activity: Dict[str, int] = defaultdict(int)
        
        # Initialize metrics
        self._initialize_metrics()
        
        logger.info("GraphMemoryMetricsCollector initialized")
    
    async def initialize(self):
        """Initialize external dependencies"""
        try:
            self.cache_manager = await get_cache_manager()
            self.correlation_engine = await get_correlation_engine()
            self.notification_dispatcher = await get_enhanced_notification_dispatcher()
            logger.info("MetricsCollector dependencies initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MetricsCollector dependencies: {e}")
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics"""
        
        # API Performance Metrics
        self.metrics['http_requests_total'] = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status', 'user_type'],
            registry=self.registry
        )
        
        self.metrics['http_request_duration_seconds'] = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint', 'status'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.metrics['http_request_size_bytes'] = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry
        )
        
        self.metrics['http_response_size_bytes'] = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint', 'status'],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=self.registry
        )
        
        # Database Metrics
        self.metrics['db_connection_pool_active_connections'] = Gauge(
            'db_connection_pool_active_connections',
            'Active database connections',
            ['database'],
            registry=self.registry
        )
        
        self.metrics['db_connection_pool_max_connections'] = Gauge(
            'db_connection_pool_max_connections',
            'Maximum database connections',
            ['database'],
            registry=self.registry
        )
        
        self.metrics['db_queries_total'] = Counter(
            'db_queries_total',
            'Total database queries',
            ['database', 'operation', 'status'],
            registry=self.registry
        )
        
        self.metrics['db_query_duration_seconds'] = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['database', 'operation'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # Cache Metrics
        self.metrics['cache_operations_total'] = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.metrics['cache_hit_rate'] = Gauge(
            'cache_hit_rate',
            'Cache hit rate percentage',
            ['cache_type'],
            registry=self.registry
        )
        
        self.metrics['cache_memory_usage_bytes'] = Gauge(
            'cache_memory_usage_bytes',
            'Cache memory usage in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        # Business Metrics
        self.metrics['user_authentication_total'] = Counter(
            'user_authentication_total',
            'Total user authentication attempts',
            ['status', 'method'],
            registry=self.registry
        )
        
        self.metrics['user_onboarding_total'] = Counter(
            'user_onboarding_total',
            'Total user onboarding events',
            ['status', 'step'],
            registry=self.registry
        )
        
        self.metrics['collaboration_sessions_total'] = Counter(
            'collaboration_sessions_total',
            'Total collaboration sessions',
            ['type', 'status'],
            registry=self.registry
        )
        
        self.metrics['memory_operations_total'] = Counter(
            'memory_operations_total',
            'Total memory operations',
            ['operation_type', 'status'],
            registry=self.registry
        )
        
        self.metrics['active_users'] = Gauge(
            'active_users',
            'Currently active users',
            ['user_type'],
            registry=self.registry
        )
        
        # System Health Metrics
        self.metrics['application_info'] = Info(
            'application_info',
            'Application information',
            registry=self.registry
        )
        
        self.metrics['application_up'] = Gauge(
            'application_up',
            'Application availability',
            ['service'],
            registry=self.registry
        )
        
        self.metrics['application_start_time'] = Gauge(
            'application_start_time',
            'Application start time',
            registry=self.registry
        )
        
        # Queue Metrics
        self.metrics['queue_size_current'] = Gauge(
            'queue_size_current',
            'Current queue size',
            ['queue_name'],
            registry=self.registry
        )
        
        self.metrics['queue_processed_total'] = Counter(
            'queue_processed_total',
            'Total queue items processed',
            ['queue_name', 'status'],
            registry=self.registry
        )
        
        self.metrics['queue_processing_duration_seconds'] = Histogram(
            'queue_processing_duration_seconds',
            'Queue item processing duration',
            ['queue_name'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Alert Correlation Metrics
        self.metrics['alerts_generated_total'] = Counter(
            'alerts_generated_total',
            'Total alerts generated',
            ['severity', 'category'],
            registry=self.registry
        )
        
        self.metrics['alerts_correlated_total'] = Counter(
            'alerts_correlated_total',
            'Total alerts correlated',
            ['correlation_strategy', 'confidence_level'],
            registry=self.registry
        )
        
        self.metrics['alerts_escalated_total'] = Counter(
            'alerts_escalated_total',
            'Total alerts escalated',
            ['escalation_level', 'policy'],
            registry=self.registry
        )
        
        self.metrics['alert_groups_active_current'] = Gauge(
            'alert_groups_active_current',
            'Currently active alert groups',
            registry=self.registry
        )
        
        self.metrics['notifications_sent_total'] = Counter(
            'notifications_sent_total',
            'Total notifications sent',
            ['channel', 'priority', 'status'],
            registry=self.registry
        )
        
        # Security Metrics
        self.metrics['failed_login_attempts_total'] = Counter(
            'failed_login_attempts_total',
            'Total failed login attempts',
            ['source_ip', 'username'],
            registry=self.registry
        )
        
        self.metrics['api_rate_limit_exceeded_total'] = Counter(
            'api_rate_limit_exceeded_total',
            'Total API rate limit exceeded events',
            ['endpoint', 'user_type'],
            registry=self.registry
        )
        
        # Set static information
        self.metrics['application_info'].info({
            'version': '1.0.0',
            'build_date': datetime.utcnow().isoformat(),
            'environment': 'production'
        })
        
        self.metrics['application_start_time'].set(self.start_time)
        self.metrics['application_up'].labels(service='main').set(1)
    
    # API Metrics Methods
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                           duration: float, request_size: int = 0, response_size: int = 0,
                           user_type: str = 'unknown'):
        """Record HTTP request metrics"""
        status = str(status_code)
        
        self.metrics['http_requests_total'].labels(
            method=method, endpoint=endpoint, status=status, user_type=user_type
        ).inc()
        
        self.metrics['http_request_duration_seconds'].labels(
            method=method, endpoint=endpoint, status=status
        ).observe(duration)
        
        if request_size > 0:
            self.metrics['http_request_size_bytes'].labels(
                method=method, endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.metrics['http_response_size_bytes'].labels(
                method=method, endpoint=endpoint, status=status
            ).observe(response_size)
        
        # Track for internal analytics
        self.request_times.append((time.time(), duration))
    
    # Database Metrics Methods
    def update_db_connection_pool(self, database: str, active: int, max_connections: int):
        """Update database connection pool metrics"""
        self.metrics['db_connection_pool_active_connections'].labels(database=database).set(active)
        self.metrics['db_connection_pool_max_connections'].labels(database=database).set(max_connections)
    
    def record_db_query(self, database: str, operation: str, duration: float, status: str = 'success'):
        """Record database query metrics"""
        self.metrics['db_queries_total'].labels(
            database=database, operation=operation, status=status
        ).inc()
        
        self.metrics['db_query_duration_seconds'].labels(
            database=database, operation=operation
        ).observe(duration)
    
    # Cache Metrics Methods
    def record_cache_operation(self, operation: str, result: str, cache_type: str = 'redis'):
        """Record cache operation metrics"""
        self.metrics['cache_operations_total'].labels(operation=operation, result=result).inc()
    
    def update_cache_metrics(self, cache_type: str, hit_rate: float, memory_usage: int):
        """Update cache performance metrics"""
        self.metrics['cache_hit_rate'].labels(cache_type=cache_type).set(hit_rate)
        self.metrics['cache_memory_usage_bytes'].labels(cache_type=cache_type).set(memory_usage)
    
    # Business Metrics Methods
    def record_user_authentication(self, status: str, method: str = 'password'):
        """Record user authentication event"""
        self.metrics['user_authentication_total'].labels(status=status, method=method).inc()
    
    def record_user_onboarding(self, status: str, step: str):
        """Record user onboarding event"""
        self.metrics['user_onboarding_total'].labels(status=status, step=step).inc()
    
    def record_collaboration_session(self, session_type: str, status: str):
        """Record collaboration session event"""
        self.metrics['collaboration_sessions_total'].labels(type=session_type, status=status).inc()
    
    def record_memory_operation(self, operation_type: str, status: str = 'success'):
        """Record memory operation event"""
        self.metrics['memory_operations_total'].labels(
            operation_type=operation_type, status=status
        ).inc()
    
    def update_active_users(self, user_type: str, count: int):
        """Update active user count"""
        self.metrics['active_users'].labels(user_type=user_type).set(count)
    
    # Queue Metrics Methods
    def update_queue_size(self, queue_name: str, size: int):
        """Update queue size metric"""
        self.metrics['queue_size_current'].labels(queue_name=queue_name).set(size)
    
    def record_queue_processing(self, queue_name: str, duration: float, status: str = 'success'):
        """Record queue processing metrics"""
        self.metrics['queue_processed_total'].labels(queue_name=queue_name, status=status).inc()
        self.metrics['queue_processing_duration_seconds'].labels(queue_name=queue_name).observe(duration)
    
    # Alert Metrics Methods
    def record_alert_generation(self, severity: str, category: str):
        """Record alert generation"""
        self.metrics['alerts_generated_total'].labels(severity=severity, category=category).inc()
    
    def record_alert_correlation(self, strategy: str, confidence_level: str):
        """Record alert correlation"""
        self.metrics['alerts_correlated_total'].labels(
            correlation_strategy=strategy, confidence_level=confidence_level
        ).inc()
    
    def record_alert_escalation(self, escalation_level: str, policy: str):
        """Record alert escalation"""
        self.metrics['alerts_escalated_total'].labels(
            escalation_level=escalation_level, policy=policy
        ).inc()
    
    def update_active_alert_groups(self, count: int):
        """Update active alert groups count"""
        self.metrics['alert_groups_active_current'].set(count)
    
    def record_notification_sent(self, channel: str, priority: str, status: str):
        """Record notification sent"""
        self.metrics['notifications_sent_total'].labels(
            channel=channel, priority=priority, status=status
        ).inc()
    
    # Security Metrics Methods
    def record_failed_login_attempt(self, source_ip: str, username: str = 'unknown'):
        """Record failed login attempt"""
        self.metrics['failed_login_attempts_total'].labels(
            source_ip=source_ip, username=username
        ).inc()
    
    def record_rate_limit_exceeded(self, endpoint: str, user_type: str):
        """Record API rate limit exceeded"""
        self.metrics['api_rate_limit_exceeded_total'].labels(
            endpoint=endpoint, user_type=user_type
        ).inc()
    
    # Context Managers for Automatic Metric Recording
    @asynccontextmanager
    async def time_database_query(self, database: str, operation: str):
        """Context manager for timing database queries"""
        start_time = time.time()
        status = 'success'
        try:
            yield
        except Exception as e:
            status = 'error'
            logger.error(f"Database query failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.record_db_query(database, operation, duration, status)
    
    @asynccontextmanager
    async def time_queue_processing(self, queue_name: str):
        """Context manager for timing queue processing"""
        start_time = time.time()
        status = 'success'
        try:
            yield
        except Exception as e:
            status = 'error'
            logger.error(f"Queue processing failed: {e}")
            raise
        finally:
            duration = time.time() - start_time
            self.record_queue_processing(queue_name, duration, status)
    
    # Health Check and Status Methods
    async def collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # Get correlation engine stats
            if self.correlation_engine:
                stats = self.correlation_engine.get_correlation_stats()
                self.update_active_alert_groups(stats.get('active_groups', 0))
            
            # Get notification dispatcher stats
            if self.notification_dispatcher:
                stats = self.notification_dispatcher.get_enhanced_stats()
                # Update notification metrics based on stats
            
            # Get cache metrics
            if self.cache_manager:
                # Collect cache performance metrics
                # This would depend on the cache manager implementation
                pass
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics"""
        return {
            'total_requests': sum(self.error_counts.values()),
            'average_response_time': self._calculate_average_response_time(),
            'error_rate': self._calculate_error_rate(),
            'active_users': sum(self.user_activity.values()),
            'uptime_seconds': time.time() - self.start_time
        }
    
    def _calculate_average_response_time(self) -> float:
        """Calculate average response time from recent requests"""
        if not self.request_times:
            return 0.0
        
        recent_times = [duration for timestamp, duration in self.request_times 
                       if time.time() - timestamp < 300]  # Last 5 minutes
        
        return sum(recent_times) / len(recent_times) if recent_times else 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        total_requests = sum(self.error_counts.values())
        error_requests = sum(count for status, count in self.error_counts.items() 
                           if status.startswith('5') or status.startswith('4'))
        
        return (error_requests / total_requests * 100) if total_requests > 0 else 0.0
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
_metrics_collector: Optional[GraphMemoryMetricsCollector] = None


async def get_metrics_collector() -> GraphMemoryMetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = GraphMemoryMetricsCollector()
        await _metrics_collector.initialize()
    return _metrics_collector


def get_metrics_collector_sync() -> GraphMemoryMetricsCollector:
    """Get global metrics collector instance (synchronous)"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = GraphMemoryMetricsCollector()
    return _metrics_collector 