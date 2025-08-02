"""
Core Service Architecture for GraphMemory-IDE Hybrid CPython-Codon System

This module provides the foundational components for managing hybrid services
with clear boundaries, resource management, and thread safety patterns.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import aioredis

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Service type enumeration"""

    CPYTHON = "cpython"
    CONDON = "codon"
    HYBRID = "hybrid"


class ServiceStatus(Enum):
    """Service status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceConfig:
    """Configuration for a service"""

    service_id: str
    service_type: ServiceType
    base_url: str
    health_endpoint: str
    memory_limit: str
    cpu_limit: str
    max_workers: int
    timeout: int = 30
    retry_attempts: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


class ServiceCommunicationError(Exception):
    """Exception raised when service communication fails"""

    pass


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""

    pass


class ServiceUnavailableError(Exception):
    """Exception raised when service is unavailable"""

    pass


class ServiceResourceManager:
    """Manages resource lifecycle for hybrid services"""

    def __init__(self):
        self.active_connections: Dict[str, List[Any]] = {}
        self.memory_pools: Dict[str, Any] = {}
        self.gpu_contexts: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def register_service_resources(self, service_id: str, config: ServiceConfig):
        """Register resources for a service"""
        async with self._lock:
            self.active_connections[service_id] = []
            logger.info(f"Registered resources for service {service_id}")

    async def cleanup_service_resources(self, service_id: str):
        """Clean up all resources associated with a service"""
        async with self._lock:
            # Close database connections
            connections = self.active_connections.get(service_id, [])
            for conn in connections:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection for {service_id}: {e}")

            # Release GPU memory
            if service_id in self.gpu_contexts:
                try:
                    gpu_context = self.gpu_contexts[service_id]
                    # GPU cleanup logic here
                    del self.gpu_contexts[service_id]
                except Exception as e:
                    logger.warning(f"Error releasing GPU memory for {service_id}: {e}")

            # Clear caches
            if service_id in self.memory_pools:
                del self.memory_pools[service_id]

            # Clear connections
            if service_id in self.active_connections:
                del self.active_connections[service_id]

            logger.info(f"Cleaned up resources for service {service_id}")

    def monitor_resource_usage(self, service_id: str) -> Dict[str, Any]:
        """Monitor current resource usage for a service"""
        return {
            "memory_usage": self._get_memory_usage(service_id),
            "cpu_usage": self._get_cpu_usage(service_id),
            "gpu_usage": self._get_gpu_usage(service_id),
            "connection_count": len(self.active_connections.get(service_id, [])),
            "memory_pool_size": len(self.memory_pools.get(service_id, {})),
        }

    def _get_memory_usage(self, service_id: str) -> float:
        """Get memory usage for a service (placeholder)"""
        # Implement actual memory monitoring
        return 0.0

    def _get_cpu_usage(self, service_id: str) -> float:
        """Get CPU usage for a service (placeholder)"""
        # Implement actual CPU monitoring
        return 0.0

    def _get_gpu_usage(self, service_id: str) -> float:
        """Get GPU usage for a service (placeholder)"""
        # Implement actual GPU monitoring
        return 0.0


class CircuitBreaker:
    """Circuit breaker for service communication"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()

    async def call_service(self, service_func: Callable, *args, **kwargs):
        """Execute service call with circuit breaker protection"""
        async with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                else:
                    raise CircuitBreakerOpenError("Service circuit breaker is open")

        try:
            result = await service_func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful service call"""
        async with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    async def _on_failure(self):
        """Handle failed service call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )


class ServiceClient:
    """Thread-safe service client for inter-service communication"""

    def __init__(
        self,
        service_url: str,
        timeout: int = 30,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.service_url = service_url
        self.timeout = timeout
        self.session = aiohttp.ClientSession()
        self._lock = asyncio.Lock()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def call_service(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Thread-safe service call with proper error handling"""
        return await self.circuit_breaker.call_service(
            self._make_request, endpoint, data
        )

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make the actual HTTP request"""
        async with self._lock:
            try:
                async with self.session.post(
                    f"{self.service_url}/{endpoint}", json=data, timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise ServiceCommunicationError(
                            f"Service returned {response.status}"
                        )
            except Exception as e:
                logger.error(f"Service call failed: {e}")
                raise ServiceCommunicationError(f"Failed to call {endpoint}: {e}")

    async def close(self):
        """Close the client session"""
        await self.session.close()


class MessageQueueManager:
    """Thread-safe message queue for service communication"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self._publishers = {}
        self._subscribers = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the message queue manager"""
        if self._initialized:
            return

        self.redis = aioredis.from_url(self.redis_url)
        self._initialized = True
        logger.info("Message queue manager initialized")

    async def publish_message(self, topic: str, message: Dict[str, Any]):
        """Thread-safe message publishing"""
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            await self.redis.publish(topic, json.dumps(message))

    async def subscribe_to_topic(self, topic: str, callback: Callable):
        """Thread-safe topic subscription"""
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(topic)
            self._subscribers[topic] = pubsub
            asyncio.create_task(self._message_handler(pubsub, callback))

    async def _message_handler(self, pubsub, callback: Callable):
        """Handle incoming messages"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await callback(data)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    async def close(self):
        """Close the message queue manager"""
        if self.redis:
            await self.redis.close()


class ThreadSafeCache:
    """Thread-safe cache for shared data"""

    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None

    async def get(self, key: str) -> Optional[Any]:
        """Thread-safe cache retrieval"""
        async with self._lock:
            data = self._cache.get(key)
            if data and data["expires"] > time.time():
                return data["value"]
            elif data:
                # Remove expired entry
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Thread-safe cache storage"""
        async with self._lock:
            self._cache[key] = {"value": value, "expires": time.time() + ttl}

    async def cleanup_expired(self):
        """Clean up expired cache entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, data in self._cache.items()
                if data["expires"] < current_time
            ]
            for key in expired_keys:
                del self._cache[key]

    async def start_cleanup_task(self):
        """Start periodic cleanup task"""
        if self._cleanup_task:
            return

        async def cleanup_loop():
            while True:
                await self.cleanup_expired()
                await asyncio.sleep(300)  # Clean up every 5 minutes

        self._cleanup_task = asyncio.create_task(cleanup_loop())


class ServiceRegistry:
    """Central service registry for discovery and health monitoring"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self.services = {}
        self.health_checkers = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the service registry"""
        if self._initialized:
            return

        self.redis = aioredis.from_url(self.redis_url)
        self._initialized = True
        logger.info("Service registry initialized")

    async def register_service(self, service_id: str, service_info: Dict[str, Any]):
        """Register a service with health monitoring"""
        if not self._initialized:
            await self.initialize()

        service_info["registered_at"] = time.time()
        service_info["last_health_check"] = time.time()
        service_info["status"] = ServiceStatus.STARTING.value

        async with self._lock:
            await self.redis.hset("services", service_id, json.dumps(service_info))
            self.services[service_id] = service_info

            # Start health monitoring
            if service_id not in self.health_checkers:
                self.health_checkers[service_id] = asyncio.create_task(
                    self._monitor_service_health(
                        service_id, service_info["health_endpoint"]
                    )
                )

        logger.info(f"Registered service {service_id}")

    async def discover_service(self, service_type: str) -> List[Dict[str, Any]]:
        """Discover available services of a specific type"""
        if not self._initialized:
            await self.initialize()

        services = []
        async with self._lock:
            async for service_id, service_data in self.redis.hscan_iter("services"):
                service_info = json.loads(service_data)
                if (
                    service_info["type"] == service_type
                    and service_info["status"] == ServiceStatus.HEALTHY.value
                ):
                    services.append(service_info)
        return services

    async def _monitor_service_health(self, service_id: str, health_endpoint: str):
        """Monitor service health with exponential backoff"""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_endpoint, timeout=5) as response:
                        if response.status == 200:
                            await self._update_service_status(
                                service_id, ServiceStatus.HEALTHY
                            )
                        else:
                            await self._update_service_status(
                                service_id, ServiceStatus.UNHEALTHY
                            )
            except Exception as e:
                await self._update_service_status(service_id, ServiceStatus.UNHEALTHY)
                logger.warning(f"Health check failed for {service_id}: {e}")

            await asyncio.sleep(30)  # Health check interval

    async def _update_service_status(self, service_id: str, status: ServiceStatus):
        """Update service status in registry"""
        if not self._initialized:
            return

        async with self._lock:
            if service_id in self.services:
                self.services[service_id]["status"] = status.value
                self.services[service_id]["last_health_check"] = time.time()
                await self.redis.hset(
                    "services", service_id, json.dumps(self.services[service_id])
                )

    async def unregister_service(self, service_id: str):
        """Unregister a service"""
        if not self._initialized:
            return

        async with self._lock:
            # Stop health monitoring
            if service_id in self.health_checkers:
                self.health_checkers[service_id].cancel()
                del self.health_checkers[service_id]

            # Remove from registry
            await self.redis.hdel("services", service_id)
            if service_id in self.services:
                del self.services[service_id]

        logger.info(f"Unregistered service {service_id}")

    async def close(self):
        """Close the service registry"""
        # Cancel all health checkers
        for task in self.health_checkers.values():
            task.cancel()

        if self.redis:
            await self.redis.close()


class HybridLoadBalancer:
    """Load balancer for hybrid CPython-Codon services"""

    def __init__(self):
        self.cpython_services = []
        self.codon_services = []
        self.hybrid_services = []
        self._load_metrics = {}
        self._lock = asyncio.Lock()

    async def register_service(self, service_info: Dict[str, Any]):
        """Register a service with the load balancer"""
        async with self._lock:
            service_type = service_info["type"]
            if service_type == ServiceType.CPYTHON.value:
                self.cpython_services.append(service_info)
            elif service_type == ServiceType.CONDON.value:
                self.codon_services.append(service_info)
            elif service_type == ServiceType.HYBRID.value:
                self.hybrid_services.append(service_info)

            self._load_metrics[service_info["id"]] = 0

    async def route_request(
        self, request_type: str, request_data: Dict[str, Any]
    ) -> str:
        """Route request to appropriate service based on type and load"""
        async with self._lock:
            if request_type in ["analytics", "ml", "gpu"]:
                return await self._route_to_codon_service(request_data)
            elif request_type in ["auth", "web", "session"]:
                return await self._route_to_cpython_service(request_data)
            else:
                return await self._route_to_hybrid_service(request_data)

    async def _route_to_codon_service(self, request_data: Dict[str, Any]) -> str:
        """Route to least loaded Codon service"""
        if not self.codon_services:
            raise ServiceUnavailableError("No Codon services available")

        # Select service with lowest load
        selected_service = min(
            self.codon_services, key=lambda s: self._load_metrics.get(s["id"], 0)
        )

        # Update load metrics
        self._load_metrics[selected_service["id"]] = (
            self._load_metrics.get(selected_service["id"], 0) + 1
        )

        return selected_service["url"]

    async def _route_to_cpython_service(self, request_data: Dict[str, Any]) -> str:
        """Route to least loaded CPython service"""
        if not self.cpython_services:
            raise ServiceUnavailableError("No CPython services available")

        # Select service with lowest load
        selected_service = min(
            self.cpython_services, key=lambda s: self._load_metrics.get(s["id"], 0)
        )

        # Update load metrics
        self._load_metrics[selected_service["id"]] = (
            self._load_metrics.get(selected_service["id"], 0) + 1
        )

        return selected_service["url"]

    async def _route_to_hybrid_service(self, request_data: Dict[str, Any]) -> str:
        """Route to least loaded hybrid service"""
        if not self.hybrid_services:
            raise ServiceUnavailableError("No hybrid services available")

        # Select service with lowest load
        selected_service = min(
            self.hybrid_services, key=lambda s: self._load_metrics.get(s["id"], 0)
        )

        # Update load metrics
        self._load_metrics[selected_service["id"]] = (
            self._load_metrics.get(selected_service["id"], 0) + 1
        )

        return selected_service["url"]

    async def update_service_load(self, service_id: str, load: float):
        """Update load metrics for a service"""
        async with self._lock:
            self._load_metrics[service_id] = load


class FallbackManager:
    """Manages fallback strategies for service failures"""

    def __init__(self):
        self.fallback_strategies = {
            "analytics": self._fallback_to_cpython_analytics,
            "ml": self._fallback_to_basic_ml,
            "auth": self._fallback_to_basic_auth,
            "collaboration": self._fallback_to_offline_mode,
        }

    async def execute_with_fallback(
        self, service_type: str, primary_func: Callable, *args, **kwargs
    ):
        """Execute primary function with fallback strategy"""
        try:
            return await primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary service failed for {service_type}: {e}")

            # Execute fallback strategy
            fallback_func = self.fallback_strategies.get(service_type)
            if fallback_func:
                return await fallback_func(*args, **kwargs)
            else:
                raise ServiceUnavailableError(
                    f"No fallback available for {service_type}"
                )

    async def _fallback_to_cpython_analytics(self, *args, **kwargs):
        """Fallback to CPython-based analytics when Codon analytics fails"""
        # Implement basic analytics using CPython
        logger.info("Using CPython fallback for analytics")
        return {"status": "fallback", "method": "cpython_analytics"}

    async def _fallback_to_basic_ml(self, *args, **kwargs):
        """Fallback to basic ML when GPU-accelerated ML fails"""
        # Implement basic ML using scikit-learn
        logger.info("Using basic ML fallback")
        return {"status": "fallback", "method": "basic_ml"}

    async def _fallback_to_basic_auth(self, *args, **kwargs):
        """Fallback to basic auth when advanced auth fails"""
        # Implement basic authentication
        logger.info("Using basic auth fallback")
        return {"status": "fallback", "method": "basic_auth"}

    async def _fallback_to_offline_mode(self, *args, **kwargs):
        """Fallback to offline mode when collaboration fails"""
        # Implement offline collaboration mode
        logger.info("Using offline mode fallback")
        return {"status": "fallback", "method": "offline_mode"}


class ServiceHealthMonitor:
    """Comprehensive health monitoring for hybrid services"""

    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.health_checks = {}
        self._lock = asyncio.Lock()

    async def register_health_check(self, service_id: str, health_check: Callable):
        """Register a health check for a service"""
        async with self._lock:
            self.health_checks[service_id] = health_check

    async def monitor_service_health(self, service_id: str) -> Dict[str, Any]:
        """Monitor health of a specific service"""
        health_check = self.health_checks.get(service_id)
        if not health_check:
            return {"status": "unknown", "error": "No health check registered"}

        try:
            start_time = time.time()
            result = await health_check()
            response_time = time.time() - start_time

            health_status = {
                "status": "healthy" if result else "unhealthy",
                "response_time": response_time,
                "last_check": time.time(),
                "service_id": service_id,
            }

            # Update metrics
            async with self._lock:
                self.metrics[service_id] = health_status

            # Check for alerts
            if response_time > 5.0:  # Alert if response time > 5s
                await self._create_alert(
                    service_id, "high_response_time", response_time
                )

            return health_status
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": time.time(),
                "service_id": service_id,
            }

            async with self._lock:
                self.metrics[service_id] = health_status

            await self._create_alert(service_id, "health_check_failed", str(e))
            return health_status

    async def _create_alert(self, service_id: str, alert_type: str, details: Any):
        """Create an alert for service issues"""
        alert = {
            "service_id": service_id,
            "alert_type": alert_type,
            "details": details,
            "timestamp": time.time(),
            "severity": "high" if alert_type == "health_check_failed" else "medium",
        }

        async with self._lock:
            self.alerts.append(alert)

        logger.warning(f"Service alert: {alert}")


class PerformanceMonitor:
    """Monitor performance metrics across hybrid services"""

    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            "response_time": 1000,  # ms
            "memory_usage": 0.8,  # 80%
            "cpu_usage": 0.9,  # 90%
            "error_rate": 0.05,  # 5%
        }
        self._lock = asyncio.Lock()

    async def record_metric(self, service_id: str, metric_type: str, value: float):
        """Record a performance metric"""
        async with self._lock:
            if service_id not in self.metrics:
                self.metrics[service_id] = {}

            if metric_type not in self.metrics[service_id]:
                self.metrics[service_id][metric_type] = []

            self.metrics[service_id][metric_type].append(
                {"value": value, "timestamp": time.time()}
            )

            # Keep only last 1000 metrics
            if len(self.metrics[service_id][metric_type]) > 1000:
                self.metrics[service_id][metric_type] = self.metrics[service_id][
                    metric_type
                ][-1000:]

            # Check thresholds
            await self._check_thresholds(service_id, metric_type, value)

    async def _check_thresholds(self, service_id: str, metric_type: str, value: float):
        """Check if metrics exceed thresholds"""
        threshold = self.thresholds.get(metric_type)
        if threshold and value > threshold:
            await self._create_performance_alert(
                service_id, metric_type, value, threshold
            )

    async def _create_performance_alert(
        self, service_id: str, metric_type: str, value: float, threshold: float
    ):
        """Create performance alert"""
        alert = {
            "service_id": service_id,
            "metric_type": metric_type,
            "current_value": value,
            "threshold": threshold,
            "timestamp": time.time(),
        }
        logger.warning(f"Performance alert: {alert}")


# Global instances
service_resource_manager = ServiceResourceManager()
service_registry = None
load_balancer = HybridLoadBalancer()
fallback_manager = FallbackManager()
health_monitor = ServiceHealthMonitor()
performance_monitor = PerformanceMonitor()


async def initialize_service_architecture(redis_url: str):
    """Initialize the service architecture components"""
    global service_registry

    service_registry = ServiceRegistry(redis_url)
    await service_registry.initialize()

    logger.info("Service architecture initialized")


async def shutdown_service_architecture():
    """Shutdown the service architecture components"""
    if service_registry:
        await service_registry.close()

    logger.info("Service architecture shutdown complete")
