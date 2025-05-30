"""
Unified Analytics API Gateway for GraphMemory-IDE

This module provides a central API gateway that orchestrates all analytics services,
handles load balancing, caching, and provides a unified interface for analytics operations.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

from fastapi import HTTPException
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class GatewayRequest:
    """Request through the analytics gateway"""

    request_id: str
    service: str
    operation: str
    data: Dict[str, Any]
    headers: Dict[str, str]
    timeout_seconds: int
    user_id: Optional[str] = None
    priority: str = "normal"  # low, normal, high
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class GatewayResponse:
    """Response from the analytics gateway"""

    request_id: str
    service: str
    operation: str
    timestamp: str
    execution_time_ms: float
    status: str
    data: Union[Dict[str, Any], List[Any]]
    metadata: Dict[str, Any]
    error: Optional[str] = None


class AnalyticsGateway:
    """
    Unified analytics API gateway that orchestrates all analytics services
    with load balancing, caching, circuit breaking, and monitoring.
    """

    def __init__(self, service_registry):
        self.service_registry = service_registry
        self.request_cache: Dict[str, Tuple[GatewayResponse, float]] = {}
        self.cache_ttl = 300  # 5 minutes

        # Circuit breaker configuration
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.failure_threshold = 5
        self.recovery_timeout = 60

        # Load balancing
        self.service_counters: Dict[str, int] = {}

        # Performance monitoring
        self.gateway_stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_responses": 0,
            "average_response_time": 0.0,
            "circuit_breaker_trips": 0,
            "load_balanced_requests": 0,
        }

        # Request queues for different priorities
        self.request_queues: Dict[str, asyncio.Queue] = {
            "high": asyncio.Queue(),
            "normal": asyncio.Queue(),
            "low": asyncio.Queue(),
        }

        # Worker tasks for processing requests
        self._workers: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()

        logger.info("Analytics Gateway initialized")

    async def start(self, num_workers: int = 4) -> None:
        """Start the gateway worker tasks"""
        self._shutdown_event.clear()

        for i in range(num_workers):
            worker = asyncio.create_task(self._request_worker(f"worker-{i}"))
            self._workers.append(worker)

        logger.info(f"Analytics Gateway started with {num_workers} workers")

    async def stop(self) -> None:
        """Stop the gateway and cleanup resources"""
        self._shutdown_event.set()

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        logger.info("Analytics Gateway stopped")

    async def execute_request(
        self,
        service: str,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        user_id: Optional[str] = None,
        priority: str = "normal",
        use_cache: bool = True,
    ) -> GatewayResponse:
        """
        Execute a request through the analytics gateway with full orchestration
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # Create gateway request
            gateway_request = GatewayRequest(
                request_id=request_id,
                service=service,
                operation=operation,
                data=data or {},
                headers=headers or {},
                timeout_seconds=timeout_seconds,
                user_id=user_id,
                priority=priority,
            )

            # Check cache first
            if use_cache:
                cached_response = await self._get_cached_response(gateway_request)
                if cached_response:
                    self.gateway_stats["cached_responses"] += 1
                    self._update_gateway_stats(time.time() - start_time, True)
                    return cached_response

            # Check circuit breaker
            if self._is_circuit_breaker_open(service):
                raise HTTPException(
                    status_code=503,
                    detail=f"Service {service} is temporarily unavailable (circuit breaker open)",
                )

            # Execute request based on priority
            if priority == "high":
                response = await self._execute_immediate(gateway_request)
            else:
                response = await self._execute_queued(gateway_request)

            # Cache successful responses
            if use_cache and response.status == "success":
                await self._cache_response(gateway_request, response)

            # Update circuit breaker on success
            self._record_success(service)

            execution_time = time.time() - start_time
            self._update_gateway_stats(execution_time, True)

            return response

        except HTTPException:
            # Let HTTPException propagate (e.g., circuit breaker, service unavailable)
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_failure(service)
            self._update_gateway_stats(execution_time, False)

            logger.error(f"Gateway request {request_id} failed: {e}")

            return GatewayResponse(
                request_id=request_id,
                service=service,
                operation=operation,
                timestamp=datetime.now(timezone.utc).isoformat(),
                execution_time_ms=execution_time * 1000,
                status="error",
                data={},
                metadata={"error_type": type(e).__name__},
                error=str(e),
            )

    async def execute_batch_requests(
        self, requests: List[Dict[str, Any]], user_id: Optional[str] = None
    ) -> List[GatewayResponse]:
        """Execute multiple requests concurrently"""
        tasks = []

        for req in requests:
            task = self.execute_request(
                service=req["service"],
                operation=req["operation"],
                data=req.get("data"),
                headers=req.get("headers"),
                timeout_seconds=req.get("timeout_seconds", 30),
                user_id=user_id,
                priority=req.get("priority", "normal"),
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        result: List[GatewayResponse] = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                error_response = GatewayResponse(
                    request_id=str(uuid.uuid4()),
                    service=requests[i]["service"],
                    operation=requests[i]["operation"],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    execution_time_ms=0.0,
                    status="error",
                    data={},
                    metadata={},
                    error=str(response),
                )
                result.append(error_response)
            else:
                # response is guaranteed to be GatewayResponse here
                assert isinstance(response, GatewayResponse)  # Type narrowing
                result.append(response)

        return result

    async def get_service_capabilities(
        self, service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get capabilities of available services"""
        services = await self.service_registry.discover_services(
            service_type=service_type, healthy_only=True
        )

        capabilities = {}
        for service in services:
            capabilities[service.service_id] = {
                "service_name": service.service_name,
                "service_type": service.service_type.value,
                "capabilities": service.capabilities,
                "endpoint_url": service.endpoint_url,
                "health_status": service.health_status.value,
                "version": service.version,
            }

        return capabilities

    async def get_gateway_stats(self) -> Dict[str, Any]:
        """Get comprehensive gateway statistics"""
        # Service health summary
        service_health = {}
        for service_id, breaker in self.circuit_breakers.items():
            service_health[service_id] = {
                "circuit_breaker_open": breaker["open"],
                "failure_count": breaker["failures"],
                "last_failure": breaker["last_failure_time"],
            }

        # Request queue sizes
        queue_sizes = {
            priority: queue.qsize() for priority, queue in self.request_queues.items()
        }

        return {
            "gateway_stats": self.gateway_stats,
            "service_health": service_health,
            "queue_sizes": queue_sizes,
            "active_workers": len(self._workers),
            "cache_size": len(self.request_cache),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Private methods

    async def _execute_immediate(self, request: GatewayRequest) -> GatewayResponse:
        """Execute high-priority request immediately"""
        return await self._execute_service_request(request)

    async def _execute_queued(self, request: GatewayRequest) -> GatewayResponse:
        """Execute request through priority queue"""
        # Add to appropriate queue
        queue = self.request_queues[request.priority]
        response_future: asyncio.Future[GatewayResponse] = asyncio.Future()

        await queue.put((request, response_future))

        # Wait for response
        return await response_future

    async def _request_worker(self, worker_id: str) -> None:
        """Worker task to process queued requests"""
        logger.info(f"Gateway worker {worker_id} started")

        while not self._shutdown_event.is_set():
            try:
                # Process high priority first
                for priority in ["high", "normal", "low"]:
                    queue = self.request_queues[priority]

                    try:
                        # Non-blocking get with timeout
                        request, response_future = await asyncio.wait_for(
                            queue.get(), timeout=1.0
                        )

                        # Execute request
                        try:
                            response = await self._execute_service_request(request)
                            response_future.set_result(response)
                        except Exception as e:
                            response_future.set_exception(e)

                        # Mark task done
                        queue.task_done()
                        break  # Process one request per cycle

                    except asyncio.TimeoutError:
                        continue  # Try next priority level

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Gateway worker {worker_id} stopped")

    async def _execute_service_request(
        self, request: GatewayRequest
    ) -> GatewayResponse:
        """Execute the actual service request"""
        start_time = time.time()

        # Discover available services
        services = await self.service_registry.discover_services(
            service_type=request.service, healthy_only=True
        )

        if not services:
            raise HTTPException(
                status_code=503,
                detail=f"No healthy services available for {request.service}",
            )

        # Load balance service selection
        selected_service = self._select_service(services, request.service)

        # Execute request
        try:
            timeout = aiohttp.ClientTimeout(total=request.timeout_seconds)  # type: ignore
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{selected_service.endpoint_url}/{request.operation}"

                async with session.post(
                    url, json=request.data, headers=request.headers
                ) as response:
                    response_data = await response.json()

                    execution_time = (time.time() - start_time) * 1000

                    # Update service metrics
                    await self.service_registry.update_service_metrics(
                        selected_service.service_id,
                        response_time=execution_time,
                        request_count_increment=1,
                        error_count_increment=0 if response.status == 200 else 1,
                    )

                    return GatewayResponse(
                        request_id=request.request_id,
                        service=request.service,
                        operation=request.operation,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        execution_time_ms=execution_time,
                        status="success" if response.status == 200 else "error",
                        data=response_data,
                        metadata={
                            "selected_service": selected_service.service_id,
                            "service_endpoint": selected_service.endpoint_url,
                            "user_id": request.user_id,
                        },
                    )

        except asyncio.TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            await self.service_registry.update_service_metrics(
                selected_service.service_id, error_count_increment=1
            )
            raise HTTPException(
                status_code=504, detail=f"Service request timed out after {request.timeout_seconds} seconds"
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # Update error metrics
            await self.service_registry.update_service_metrics(
                selected_service.service_id, error_count_increment=1
            )

            raise HTTPException(
                status_code=500, detail=f"Service request failed: {str(e)}"
            )

    def _select_service(self, services: List[Any], service_type: str) -> Any:
        """Select service using round-robin load balancing"""
        if service_type not in self.service_counters:
            self.service_counters[service_type] = 0

        # Round-robin selection
        index = self.service_counters[service_type] % len(services)
        self.service_counters[service_type] += 1

        self.gateway_stats["load_balanced_requests"] += 1

        return services[index]

    async def _get_cached_response(
        self, request: GatewayRequest
    ) -> Optional[GatewayResponse]:
        """Get cached response if available and valid"""
        cache_key = f"{request.service}:{request.operation}:{hash(str(request.data))}"

        cached_data = self.request_cache.get(cache_key)
        if not cached_data:
            return None

        response, timestamp = cached_data

        # Check if cache is still valid
        if (time.time() - timestamp) > self.cache_ttl:
            del self.request_cache[cache_key]
            return None

        # Update cache metadata
        response.metadata["cache_hit"] = True
        response.metadata["cache_age_seconds"] = time.time() - timestamp
        response.request_id = request.request_id  # Use current request ID

        return response

    async def _cache_response(
        self, request: GatewayRequest, response: GatewayResponse
    ) -> None:
        """Cache successful response"""
        cache_key = f"{request.service}:{request.operation}:{hash(str(request.data))}"
        self.request_cache[cache_key] = (response, time.time())

        # Cleanup old cache entries (simple approach)
        if len(self.request_cache) > 1000:  # Max 1000 cached items
            # Remove oldest 10% of entries
            sorted_items = sorted(
                self.request_cache.items(), key=lambda x: x[1][1]  # Sort by timestamp
            )

            for key, _ in sorted_items[:100]:  # Remove oldest 100 items
                del self.request_cache[key]

    def _is_circuit_breaker_open(self, service: str) -> bool:
        """Check if circuit breaker is open for a service"""
        breaker = self.circuit_breakers.get(service)
        if not breaker:
            return False

        if not breaker["open"]:
            return False

        # Check if recovery timeout has passed
        if time.time() - breaker["open_time"] > self.recovery_timeout:
            breaker["open"] = False
            breaker["failures"] = 0
            logger.info(f"Circuit breaker closed for service {service}")
            return False

        return True

    def _record_success(self, service: str) -> None:
        """Record successful request for circuit breaker"""
        if service in self.circuit_breakers:
            self.circuit_breakers[service]["failures"] = 0

    def _record_failure(self, service: str) -> None:
        """Record failed request for circuit breaker"""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = {
                "failures": 0,
                "open": False,
                "open_time": 0,
                "last_failure_time": None,
            }

        breaker = self.circuit_breakers[service]
        breaker["failures"] += 1
        breaker["last_failure_time"] = time.time()

        # Open circuit breaker if threshold exceeded
        if breaker["failures"] >= self.failure_threshold:
            breaker["open"] = True
            breaker["open_time"] = time.time()
            self.gateway_stats["circuit_breaker_trips"] += 1
            logger.warning(f"Circuit breaker opened for service {service}")

    def _update_gateway_stats(self, execution_time: float, success: bool) -> None:
        """Update gateway performance statistics"""
        self.gateway_stats["total_requests"] += 1

        if success:
            self.gateway_stats["successful_requests"] += 1
        else:
            self.gateway_stats["failed_requests"] += 1

        # Update average response time
        total_requests = self.gateway_stats["total_requests"]
        current_avg = self.gateway_stats["average_response_time"]
        execution_time_ms = execution_time * 1000

        self.gateway_stats["average_response_time"] = (
            current_avg * (total_requests - 1) + execution_time_ms
        ) / total_requests


# Global gateway instance
_global_gateway: Optional[AnalyticsGateway] = None


async def get_analytics_gateway(service_registry: Any) -> AnalyticsGateway:
    """Get the global analytics gateway instance"""
    global _global_gateway

    if _global_gateway is None:
        _global_gateway = AnalyticsGateway(service_registry)
        await _global_gateway.start()

    return _global_gateway


async def shutdown_analytics_gateway() -> None:
    """Shutdown the global analytics gateway"""
    global _global_gateway

    if _global_gateway:
        await _global_gateway.stop()
        _global_gateway = None
        logger.info("Analytics gateway shutdown complete")
