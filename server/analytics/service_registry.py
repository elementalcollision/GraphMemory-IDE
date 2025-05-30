"""
Analytics Service Registry and Discovery System for GraphMemory-IDE

This module provides service discovery, health monitoring, and registry management
for all analytics components in the GraphMemory-IDE ecosystem.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceType(str, Enum):
    """Types of analytics services"""
    ANALYTICS_ENGINE = "analytics_engine"
    STREAMING_ANALYTICS = "streaming_analytics"
    KUZU_DATABASE = "kuzu_database"
    REDIS_CACHE = "redis_cache"
    DRAGONFLY_STREAM = "dragonfly_stream"
    DASHBOARD_API = "dashboard_api"
    MCP_SERVER = "mcp_server"
    REAL_TIME_PROCESSOR = "real_time_processor"
    FEATURE_EXTRACTOR = "feature_extractor"
    PATTERN_DETECTOR = "pattern_detector"

class ServiceHealth(str, Enum):
    """Service health states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"

@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    service_id: str
    service_name: str
    service_type: ServiceType
    endpoint_url: str
    health_check_url: Optional[str] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Health monitoring
    health_status: ServiceHealth = ServiceHealth.UNKNOWN
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    # Performance metrics
    average_response_time: float = 0.0
    request_count: int = 0
    error_count: int = 0
    uptime_seconds: float = 0.0

class AnalyticsServiceRegistry:
    """
    Central registry for all analytics services with health monitoring,
    service discovery, and automatic failover capabilities.
    """
    
    def __init__(self, health_check_interval: int = 30):
        self.services: Dict[str, ServiceEndpoint] = {}
        self.service_subscriptions: Dict[str, Set[str]] = {}
        self.health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Service discovery cache
        self._discovery_cache: Dict[str, List[ServiceEndpoint]] = {}
        self._cache_ttl = 60  # 1 minute cache TTL
        self._last_cache_update: Dict[str, datetime] = {}
        
        # Performance tracking
        self.registry_stats = {
            "total_services": 0,
            "healthy_services": 0,
            "unhealthy_services": 0,
            "health_checks_performed": 0,
            "last_health_check_cycle": None,
            "average_health_check_time": 0.0
        }
        
        logger.info("Analytics Service Registry initialized")
    
    async def start(self):
        """Start the service registry and health monitoring"""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._shutdown_event.clear()
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("Service registry health monitoring started")
    
    async def stop(self):
        """Stop the service registry and health monitoring"""
        self._shutdown_event.set()
        
        if self._health_check_task:
            try:
                await asyncio.wait_for(self._health_check_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._health_check_task.cancel()
        
        logger.info("Service registry stopped")
    
    async def register_service(
        self,
        service_id: str,
        service_name: str,
        service_type: ServiceType,
        endpoint_url: str,
        health_check_url: Optional[str] = None,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> ServiceEndpoint:
        """Register a new analytics service"""
        
        if service_id in self.services:
            logger.warning(f"Service {service_id} is already registered, updating...")
        
        service = ServiceEndpoint(
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            endpoint_url=endpoint_url,
            health_check_url=health_check_url or f"{endpoint_url}/health",
            version=version,
            metadata=metadata or {},
            dependencies=dependencies or [],
            capabilities=capabilities or [],
            tags=tags or []
        )
        
        self.services[service_id] = service
        self._invalidate_discovery_cache()
        self._update_registry_stats()
        
        logger.info(f"Registered service: {service_name} ({service_id}) at {endpoint_url}")
        
        # Perform initial health check
        await self._check_service_health(service)
        
        return service
    
    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service from the registry"""
        if service_id not in self.services:
            logger.warning(f"Attempted to unregister unknown service: {service_id}")
            return False
        
        service = self.services.pop(service_id)
        self._invalidate_discovery_cache()
        self._update_registry_stats()
        
        logger.info(f"Unregistered service: {service.service_name} ({service_id})")
        return True
    
    async def heartbeat(self, service_id: str) -> bool:
        """Update service heartbeat timestamp"""
        if service_id not in self.services:
            return False
        
        self.services[service_id].last_heartbeat = datetime.utcnow()
        return True
    
    async def discover_services(
        self,
        service_type: Optional[ServiceType] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        healthy_only: bool = True
    ) -> List[ServiceEndpoint]:
        """
        Discover services based on criteria with caching
        """
        cache_key = f"{service_type}:{capabilities}:{tags}:{healthy_only}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._discovery_cache[cache_key]
        
        # Filter services
        filtered_services = []
        
        for service in self.services.values():
            # Health filter
            if healthy_only and service.health_status != ServiceHealth.HEALTHY:
                continue
            
            # Type filter
            if service_type and service.service_type != service_type:
                continue
            
            # Capabilities filter
            if capabilities:
                if not all(cap in service.capabilities for cap in capabilities):
                    continue
            
            # Tags filter
            if tags:
                if not any(tag in service.tags for tag in tags):
                    continue
            
            filtered_services.append(service)
        
        # Update cache
        self._discovery_cache[cache_key] = filtered_services
        self._last_cache_update[cache_key] = datetime.utcnow()
        
        logger.debug(f"Discovered {len(filtered_services)} services for criteria: {cache_key}")
        return filtered_services
    
    async def get_service(self, service_id: str) -> Optional[ServiceEndpoint]:
        """Get a specific service by ID"""
        return self.services.get(service_id)
    
    async def get_healthy_services(self, service_type: Optional[ServiceType] = None) -> List[ServiceEndpoint]:
        """Get all healthy services of a specific type"""
        return await self.discover_services(
            service_type=service_type,
            healthy_only=True
        )
    
    async def get_service_dependencies(self, service_id: str) -> List[ServiceEndpoint]:
        """Get all dependencies for a service"""
        service = self.services.get(service_id)
        if not service:
            return []
        
        dependencies = []
        for dep_id in service.dependencies:
            dep_service = self.services.get(dep_id)
            if dep_service:
                dependencies.append(dep_service)
        
        return dependencies
    
    async def check_dependency_health(self, service_id: str) -> Dict[str, bool]:
        """Check health of all service dependencies"""
        dependencies = await self.get_service_dependencies(service_id)
        
        health_status = {}
        for dep in dependencies:
            health_status[dep.service_id] = dep.health_status == ServiceHealth.HEALTHY
        
        return health_status
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get comprehensive registry status"""
        services_by_type = {}
        services_by_health = {
            ServiceHealth.HEALTHY: 0,
            ServiceHealth.DEGRADED: 0,
            ServiceHealth.UNHEALTHY: 0,
            ServiceHealth.UNKNOWN: 0,
            ServiceHealth.MAINTENANCE: 0
        }
        
        for service in self.services.values():
            # Count by type
            service_type = service.service_type.value
            if service_type not in services_by_type:
                services_by_type[service_type] = 0
            services_by_type[service_type] += 1
            
            # Count by health
            services_by_health[service.health_status] += 1
        
        return {
            "total_services": len(self.services),
            "services_by_type": services_by_type,
            "services_by_health": {k.value: v for k, v in services_by_health.items()},
            "registry_stats": self.registry_stats,
            "health_monitoring_active": self._health_check_task is not None and not self._health_check_task.done(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_service_list(self) -> List[Dict[str, Any]]:
        """Get a list of all registered services with basic info"""
        return [
            {
                "service_id": service.service_id,
                "service_name": service.service_name,
                "service_type": service.service_type.value,
                "endpoint_url": service.endpoint_url,
                "health_status": service.health_status.value,
                "version": service.version,
                "uptime_seconds": service.uptime_seconds,
                "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None,
                "capabilities": service.capabilities,
                "tags": service.tags
            }
            for service in self.services.values()
        ]
    
    async def update_service_metrics(
        self,
        service_id: str,
        response_time: Optional[float] = None,
        request_count_increment: int = 0,
        error_count_increment: int = 0
    ):
        """Update service performance metrics"""
        service = self.services.get(service_id)
        if not service:
            return
        
        if response_time is not None:
            # Update average response time
            total_requests = service.request_count + request_count_increment
            if total_requests > 0:
                service.average_response_time = (
                    (service.average_response_time * service.request_count + response_time) /
                    total_requests
                )
        
        service.request_count += request_count_increment
        service.error_count += error_count_increment
        
        # Update uptime
        if service.registered_at:
            service.uptime_seconds = (datetime.utcnow() - service.registered_at).total_seconds()
    
    # Private methods
    
    async def _health_check_loop(self):
        """Main health check loop"""
        while not self._shutdown_event.is_set():
            try:
                start_time = time.time()
                await self._perform_health_checks()
                
                # Update stats
                check_duration = time.time() - start_time
                self.registry_stats["health_checks_performed"] += 1
                self.registry_stats["last_health_check_cycle"] = datetime.utcnow().isoformat()
                
                # Update average check time
                total_checks = self.registry_stats["health_checks_performed"]
                current_avg = self.registry_stats["average_health_check_time"]
                self.registry_stats["average_health_check_time"] = (
                    (current_avg * (total_checks - 1) + check_duration) / total_checks
                )
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check cycle failed: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all registered services"""
        if not self.services:
            return
        
        # Check all services concurrently
        health_check_tasks = [
            self._check_service_health(service)
            for service in self.services.values()
        ]
        
        await asyncio.gather(*health_check_tasks, return_exceptions=True)
        self._update_registry_stats()
    
    async def _check_service_health(self, service: ServiceEndpoint):
        """Check health of a single service"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                if service.health_check_url:
                    async with session.get(service.health_check_url) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        if response.status == 200:
                            service.health_status = ServiceHealth.HEALTHY
                            service.consecutive_failures = 0
                            
                            # Update metrics
                            await self.update_service_metrics(
                                service.service_id,
                                response_time=response_time,
                                request_count_increment=1
                            )
                        else:
                            service.health_status = ServiceHealth.DEGRADED
                            service.consecutive_failures += 1
                            
                            # Update error metrics
                            await self.update_service_metrics(
                                service.service_id,
                                error_count_increment=1
                            )
        
        except Exception as e:
            logger.warning(f"Health check failed for {service.service_name}: {e}")
            service.health_status = ServiceHealth.UNHEALTHY
            service.consecutive_failures += 1
            
            # Update error metrics
            await self.update_service_metrics(
                service.service_id,
                error_count_increment=1
            )
        
        finally:
            service.last_health_check = datetime.utcnow()
    
    def _invalidate_discovery_cache(self):
        """Invalidate the service discovery cache"""
        self._discovery_cache.clear()
        self._last_cache_update.clear()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._discovery_cache:
            return False
        
        last_update = self._last_cache_update.get(cache_key)
        if not last_update:
            return False
        
        return (datetime.utcnow() - last_update).total_seconds() < self._cache_ttl
    
    def _update_registry_stats(self):
        """Update registry statistics"""
        self.registry_stats["total_services"] = len(self.services)
        
        healthy_count = sum(
            1 for service in self.services.values()
            if service.health_status == ServiceHealth.HEALTHY
        )
        unhealthy_count = sum(
            1 for service in self.services.values()
            if service.health_status in [ServiceHealth.UNHEALTHY, ServiceHealth.UNKNOWN]
        )
        
        self.registry_stats["healthy_services"] = healthy_count
        self.registry_stats["unhealthy_services"] = unhealthy_count

# Global registry instance
_global_registry: Optional[AnalyticsServiceRegistry] = None

async def get_service_registry() -> AnalyticsServiceRegistry:
    """Get the global service registry instance"""
    global _global_registry
    
    if _global_registry is None:
        _global_registry = AnalyticsServiceRegistry()
        await _global_registry.start()
    
    return _global_registry

async def initialize_service_registry() -> AnalyticsServiceRegistry:
    """Initialize and return the global service registry"""
    registry = await get_service_registry()
    
    # Register core services
    await _register_core_services(registry)
    
    logger.info("Service registry initialized with core services")
    return registry

async def _register_core_services(registry: AnalyticsServiceRegistry):
    """Register core analytics services"""
    try:
        # Register MCP Server
        await registry.register_service(
            service_id="mcp_server",
            service_name="GraphMemory MCP Server",
            service_type=ServiceType.MCP_SERVER,
            endpoint_url="http://localhost:8000",
            health_check_url="http://localhost:8000/health",
            capabilities=["telemetry", "memory_operations", "user_management"],
            tags=["core", "api"]
        )
        
        # Register Analytics Engine
        await registry.register_service(
            service_id="analytics_engine",
            service_name="Analytics Engine Core",
            service_type=ServiceType.ANALYTICS_ENGINE,
            endpoint_url="http://localhost:8000/analytics",
            health_check_url="http://localhost:8000/analytics/health",
            dependencies=["kuzu_database", "redis_cache"],
            capabilities=["query_analytics", "graph_analytics", "temporal_analytics"],
            tags=["analytics", "core"]
        )
        
        # Register Kuzu Database
        await registry.register_service(
            service_id="kuzu_database",
            service_name="Kuzu GraphDB",
            service_type=ServiceType.KUZU_DATABASE,
            endpoint_url="http://localhost:8080",
            capabilities=["graph_storage", "cypher_queries", "graph_analytics"],
            tags=["database", "graph"]
        )
        
        # Register streaming services if available
        try:
            # Try to register streaming services without importing
            await registry.register_service(
                service_id="streaming_analytics",
                service_name="Streaming Analytics Pipeline",
                service_type=ServiceType.STREAMING_ANALYTICS,
                endpoint_url="http://localhost:8000/streaming",
                health_check_url="http://localhost:8000/streaming/health",
                dependencies=["dragonfly_stream"],
                capabilities=["real_time_processing", "pattern_detection", "feature_extraction"],
                tags=["streaming", "real_time"]
            )
            
            await registry.register_service(
                service_id="dragonfly_stream",
                service_name="DragonflyDB Streaming",
                service_type=ServiceType.DRAGONFLY_STREAM,
                endpoint_url="http://localhost:6379",
                capabilities=["stream_processing", "high_throughput", "redis_compatible"],
                tags=["streaming", "database"]
            )
        except Exception:
            logger.info("Streaming services not available for registration")
        
    except Exception as e:
        logger.error(f"Failed to register core services: {e}")

async def shutdown_service_registry():
    """Shutdown the global service registry"""
    global _global_registry
    
    if _global_registry:
        await _global_registry.stop()
        _global_registry = None
        logger.info("Service registry shutdown complete") 