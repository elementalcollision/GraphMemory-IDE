# Service Architecture Design: CPython-Codon Hybrid Architecture

## Overview

This document defines the core service architecture for GraphMemory-IDE's hybrid CPython-Codon system, establishing clear boundaries, resource management strategies, and thread safety patterns for production deployment.

## Architecture Principles

### 1. Service Isolation Patterns

#### Process-Level Isolation
- **CPython Services**: Run in separate processes/containers from Codon services
- **Codon Services**: Execute in isolated environments with dedicated resources
- **No Shared Memory**: Services communicate only through serializable IPC mechanisms
- **Container Boundaries**: Each service type runs in its own container with resource limits

#### Service Classification

**CPython Services (Web/API Layer)**
- Authentication & Authorization (`server/auth/`)
- WebSocket Management (`server/collaboration/websocket_*`)
- API Gateway & Routing
- Session Management
- Rate Limiting & Security Middleware

**Codon Services (Compute/ML Layer)**
- Analytics Engine (`server/analytics/engine.py`)
- ML/AI Processing (`monitoring/ai_detection/`)
- Graph Algorithms & Analytics
- GPU-Accelerated Computations
- Real-time Data Processing

**Hybrid Services (Coordination Layer)**
- Collaboration Engine (`server/collaboration/`)
- Real-time Analytics Bridge
- Data Transformation Services
- Event Streaming & Pub/Sub

### 2. Resource Management Strategies

#### Memory Isolation
```python
# Service Resource Configuration
SERVICE_RESOURCE_LIMITS = {
    "cpython_services": {
        "memory_limit": "512Mi",
        "cpu_limit": "0.5",
        "max_workers": 4
    },
    "codon_services": {
        "memory_limit": "2Gi",
        "cpu_limit": "2.0",
        "gpu_memory": "4Gi",
        "max_workers": 2
    },
    "hybrid_services": {
        "memory_limit": "1Gi",
        "cpu_limit": "1.0",
        "max_workers": 3
    }
}
```

#### Resource Cleanup Patterns
```python
class ServiceResourceManager:
    """Manages resource lifecycle for hybrid services"""
    
    def __init__(self):
        self.active_connections = {}
        self.memory_pools = {}
        self.gpu_contexts = {}
    
    async def cleanup_service_resources(self, service_id: str):
        """Clean up all resources associated with a service"""
        # Close database connections
        # Release GPU memory
        # Clear caches
        # Terminate background tasks
        pass
    
    def monitor_resource_usage(self, service_id: str) -> Dict[str, Any]:
        """Monitor current resource usage for a service"""
        return {
            "memory_usage": self.get_memory_usage(service_id),
            "cpu_usage": self.get_cpu_usage(service_id),
            "gpu_usage": self.get_gpu_usage(service_id),
            "connection_count": len(self.active_connections.get(service_id, []))
        }
```

### 3. Thread Safety Patterns

#### Communication Patterns

**REST API Communication**
```python
class ServiceClient:
    """Thread-safe service client for inter-service communication"""
    
    def __init__(self, service_url: str, timeout: int = 30):
        self.service_url = service_url
        self.timeout = timeout
        self.session = aiohttp.ClientSession()
        self._lock = asyncio.Lock()
    
    async def call_service(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Thread-safe service call with proper error handling"""
        async with self._lock:
            try:
                async with self.session.post(
                    f"{self.service_url}/{endpoint}",
                    json=data,
                    timeout=self.timeout
                ) as response:
                    return await response.json()
            except Exception as e:
                logger.error(f"Service call failed: {e}")
                raise ServiceCommunicationError(f"Failed to call {endpoint}")
```

**Message Queue Communication**
```python
class MessageQueueManager:
    """Thread-safe message queue for service communication"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self._publishers = {}
        self._subscribers = {}
        self._lock = asyncio.Lock()
    
    async def publish_message(self, topic: str, message: Dict[str, Any]):
        """Thread-safe message publishing"""
        async with self._lock:
            await self.redis.publish(topic, json.dumps(message))
    
    async def subscribe_to_topic(self, topic: str, callback: Callable):
        """Thread-safe topic subscription"""
        async with self._lock:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(topic)
            self._subscribers[topic] = pubsub
            asyncio.create_task(self._message_handler(pubsub, callback))
```

#### Memory Safety Patterns
```python
class ThreadSafeCache:
    """Thread-safe cache for shared data"""
    
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
        self._cleanup_task = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Thread-safe cache retrieval"""
        async with self._lock:
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Thread-safe cache storage"""
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires": time.time() + ttl
            }
    
    async def cleanup_expired(self):
        """Clean up expired cache entries"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, data in self._cache.items()
                if data["expires"] < current_time
            ]
            for key in expired_keys:
                del self._cache[key]
```

### 4. Service Discovery Architecture

#### Service Registry
```python
class ServiceRegistry:
    """Central service registry for discovery and health monitoring"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.services = {}
        self.health_checkers = {}
    
    async def register_service(self, service_id: str, service_info: Dict[str, Any]):
        """Register a service with health monitoring"""
        service_info["registered_at"] = time.time()
        service_info["last_health_check"] = time.time()
        
        await self.redis.hset("services", service_id, json.dumps(service_info))
        self.services[service_id] = service_info
        
        # Start health monitoring
        self.health_checkers[service_id] = asyncio.create_task(
            self._monitor_service_health(service_id, service_info["health_endpoint"])
        )
    
    async def discover_service(self, service_type: str) -> List[Dict[str, Any]]:
        """Discover available services of a specific type"""
        services = []
        async for service_id, service_data in self.redis.hscan_iter("services"):
            service_info = json.loads(service_data)
            if service_info["type"] == service_type and service_info["status"] == "healthy":
                services.append(service_info)
        return services
    
    async def _monitor_service_health(self, service_id: str, health_endpoint: str):
        """Monitor service health with exponential backoff"""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_endpoint, timeout=5) as response:
                        if response.status == 200:
                            await self._update_service_status(service_id, "healthy")
                        else:
                            await self._update_service_status(service_id, "unhealthy")
            except Exception as e:
                await self._update_service_status(service_id, "unhealthy")
            
            await asyncio.sleep(30)  # Health check interval
```

### 5. Load Balancing for Hybrid Services

#### Intelligent Load Balancer
```python
class HybridLoadBalancer:
    """Load balancer for hybrid CPython-Codon services"""
    
    def __init__(self):
        self.cpython_services = []
        self.codon_services = []
        self.hybrid_services = []
        self._load_metrics = {}
        self._lock = asyncio.Lock()
    
    async def route_request(self, request_type: str, request_data: Dict[str, Any]) -> str:
        """Route request to appropriate service based on type and load"""
        async with self._lock:
            if request_type == "analytics" or request_type == "ml":
                return await self._route_to_codon_service(request_data)
            elif request_type == "auth" or request_type == "web":
                return await self._route_to_cpython_service(request_data)
            else:
                return await self._route_to_hybrid_service(request_data)
    
    async def _route_to_codon_service(self, request_data: Dict[str, Any]) -> str:
        """Route to least loaded Codon service"""
        if not self.codon_services:
            raise ServiceUnavailableError("No Codon services available")
        
        # Select service with lowest load
        selected_service = min(
            self.codon_services,
            key=lambda s: self._load_metrics.get(s["id"], 0)
        )
        
        # Update load metrics
        self._load_metrics[selected_service["id"]] = \
            self._load_metrics.get(selected_service["id"], 0) + 1
        
        return selected_service["url"]
    
    async def update_service_load(self, service_id: str, load: float):
        """Update load metrics for a service"""
        async with self._lock:
            self._load_metrics[service_id] = load
```

### 6. Error Handling and Fallback Mechanisms

#### Circuit Breaker Pattern
```python
class CircuitBreaker:
    """Circuit breaker for service communication"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call_service(self, service_func: Callable, *args, **kwargs):
        """Execute service call with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Service circuit breaker is open")
        
        try:
            result = await service_func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful service call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed service call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

#### Fallback Strategies
```python
class FallbackManager:
    """Manages fallback strategies for service failures"""
    
    def __init__(self):
        self.fallback_strategies = {
            "analytics": self._fallback_to_cpython_analytics,
            "ml": self._fallback_to_basic_ml,
            "auth": self._fallback_to_basic_auth,
            "collaboration": self._fallback_to_offline_mode
        }
    
    async def execute_with_fallback(self, service_type: str, primary_func: Callable, *args, **kwargs):
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
                raise ServiceUnavailableError(f"No fallback available for {service_type}")
    
    async def _fallback_to_cpython_analytics(self, *args, **kwargs):
        """Fallback to CPython-based analytics when Codon analytics fails"""
        # Implement basic analytics using CPython
        pass
    
    async def _fallback_to_basic_ml(self, *args, **kwargs):
        """Fallback to basic ML when GPU-accelerated ML fails"""
        # Implement basic ML using scikit-learn
        pass
```

### 7. Health Monitoring and Observability

#### Service Health Monitoring
```python
class ServiceHealthMonitor:
    """Comprehensive health monitoring for hybrid services"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
        self.health_checks = {}
    
    async def register_health_check(self, service_id: str, health_check: Callable):
        """Register a health check for a service"""
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
                "service_id": service_id
            }
            
            # Update metrics
            self.metrics[service_id] = health_status
            
            # Check for alerts
            if response_time > 5.0:  # Alert if response time > 5s
                await self._create_alert(service_id, "high_response_time", response_time)
            
            return health_status
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": time.time(),
                "service_id": service_id
            }
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
            "severity": "high" if alert_type == "health_check_failed" else "medium"
        }
        self.alerts.append(alert)
        logger.warning(f"Service alert: {alert}")
```

#### Performance Monitoring
```python
class PerformanceMonitor:
    """Monitor performance metrics across hybrid services"""
    
    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            "response_time": 1000,  # ms
            "memory_usage": 0.8,    # 80%
            "cpu_usage": 0.9,       # 90%
            "error_rate": 0.05      # 5%
        }
    
    async def record_metric(self, service_id: str, metric_type: str, value: float):
        """Record a performance metric"""
        if service_id not in self.metrics:
            self.metrics[service_id] = {}
        
        if metric_type not in self.metrics[service_id]:
            self.metrics[service_id][metric_type] = []
        
        self.metrics[service_id][metric_type].append({
            "value": value,
            "timestamp": time.time()
        })
        
        # Keep only last 1000 metrics
        if len(self.metrics[service_id][metric_type]) > 1000:
            self.metrics[service_id][metric_type] = \
                self.metrics[service_id][metric_type][-1000:]
        
        # Check thresholds
        await self._check_thresholds(service_id, metric_type, value)
    
    async def _check_thresholds(self, service_id: str, metric_type: str, value: float):
        """Check if metrics exceed thresholds"""
        threshold = self.thresholds.get(metric_type)
        if threshold and value > threshold:
            await self._create_performance_alert(service_id, metric_type, value, threshold)
    
    async def _create_performance_alert(self, service_id: str, metric_type: str, 
                                       value: float, threshold: float):
        """Create performance alert"""
        alert = {
            "service_id": service_id,
            "metric_type": metric_type,
            "current_value": value,
            "threshold": threshold,
            "timestamp": time.time()
        }
        logger.warning(f"Performance alert: {alert}")
```

## Implementation Guidelines

### 1. Service Deployment Configuration

#### Docker Compose Configuration
```yaml
version: '3.8'

services:
  # CPython Services
  auth-service:
    build: ./server/auth
    environment:
      - SERVICE_TYPE=cpython
      - MEMORY_LIMIT=512Mi
      - CPU_LIMIT=0.5
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/auth/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Codon Services
  analytics-service:
    build: ./server/analytics
    environment:
      - SERVICE_TYPE=codon
      - MEMORY_LIMIT=2Gi
      - CPU_LIMIT=2.0
      - GPU_MEMORY=4Gi
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    runtime: nvidia
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/analytics/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Hybrid Services
  collaboration-service:
    build: ./server/collaboration
    environment:
      - SERVICE_TYPE=hybrid
      - MEMORY_LIMIT=1Gi
      - CPU_LIMIT=1.0
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/collaboration/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2. Service Communication Patterns

#### REST API Communication
```python
# Service client for CPython services
class CPythonServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        self.circuit_breaker = CircuitBreaker()
    
    async def call_service(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.circuit_breaker.call_service(
            self._make_request, endpoint, data
        )
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.session.post(
            f"{self.base_url}/{endpoint}",
            json=data,
            timeout=30
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ServiceCommunicationError(f"Service returned {response.status}")

# Service client for Codon services
class CodonServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = aiohttp.ClientSession()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3)
    
    async def call_service(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.circuit_breaker.call_service(
            self._make_request, endpoint, data
        )
    
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.session.post(
            f"{self.base_url}/{endpoint}",
            json=data,
            timeout=60  # Longer timeout for Codon services
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ServiceCommunicationError(f"Service returned {response.status}")
```

### 3. Error Handling and Recovery

#### Comprehensive Error Handling
```python
class ServiceErrorHandler:
    """Handles errors across hybrid services"""
    
    def __init__(self):
        self.error_counts = {}
        self.recovery_strategies = {}
    
    async def handle_service_error(self, service_id: str, error: Exception) -> Dict[str, Any]:
        """Handle service errors with appropriate recovery strategies"""
        error_type = type(error).__name__
        
        # Update error counts
        if service_id not in self.error_counts:
            self.error_counts[service_id] = {}
        if error_type not in self.error_counts[service_id]:
            self.error_counts[service_id][error_type] = 0
        self.error_counts[service_id][error_type] += 1
        
        # Log error
        logger.error(f"Service {service_id} error: {error}")
        
        # Execute recovery strategy
        recovery_strategy = self.recovery_strategies.get(error_type)
        if recovery_strategy:
            return await recovery_strategy(service_id, error)
        else:
            return {"status": "error", "message": str(error)}
    
    async def _handle_connection_error(self, service_id: str, error: Exception) -> Dict[str, Any]:
        """Handle connection errors with retry logic"""
        # Implement exponential backoff retry
        pass
    
    async def _handle_timeout_error(self, service_id: str, error: Exception) -> Dict[str, Any]:
        """Handle timeout errors with fallback"""
        # Implement fallback to simpler service
        pass
```

## Testing Strategy

### 1. Service Boundary Testing
```python
class ServiceBoundaryTests:
    """Test service boundaries and isolation"""
    
    async def test_service_isolation(self):
        """Test that services are properly isolated"""
        # Test memory isolation
        # Test resource limits
        # Test communication boundaries
        pass
    
    async def test_thread_safety(self):
        """Test thread safety across service boundaries"""
        # Test concurrent requests
        # Test shared resource access
        # Test memory safety
        pass
    
    async def test_error_propagation(self):
        """Test error handling and propagation"""
        # Test circuit breaker patterns
        # Test fallback mechanisms
        # Test error recovery
        pass
```

### 2. Performance Testing
```python
class PerformanceTests:
    """Test performance characteristics of hybrid services"""
    
    async def test_service_performance(self):
        """Test performance of individual services"""
        # Test response times
        # Test throughput
        # Test resource usage
        pass
    
    async def test_load_balancing(self):
        """Test load balancing effectiveness"""
        # Test request distribution
        # Test failover mechanisms
        # Test performance under load
        pass
```

## Monitoring and Observability

### 1. Metrics Collection
- **Service Metrics**: Response time, throughput, error rates
- **Resource Metrics**: CPU, memory, GPU usage
- **Business Metrics**: User activity, feature usage
- **Infrastructure Metrics**: Network, disk, database performance

### 2. Alerting Strategy
- **Critical Alerts**: Service down, high error rates
- **Warning Alerts**: High resource usage, slow response times
- **Info Alerts**: Service restarts, configuration changes

### 3. Logging Strategy
- **Structured Logging**: JSON format with consistent fields
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log Aggregation**: Centralized logging with correlation IDs

## Security Considerations

### 1. Service Communication Security
- **mTLS**: Mutual TLS for service-to-service communication
- **API Authentication**: JWT tokens for API access
- **Network Isolation**: VPC/subnet isolation for different service types

### 2. Resource Security
- **Resource Limits**: Prevent resource exhaustion attacks
- **Input Validation**: Validate all service inputs
- **Error Handling**: Don't expose sensitive information in errors

## Conclusion

This service architecture design provides a robust foundation for the GraphMemory-IDE hybrid CPython-Codon system. The key principles are:

1. **Clear Service Boundaries**: Each service type has well-defined responsibilities and isolation
2. **Thread Safety**: All inter-service communication is thread-safe and memory-safe
3. **Resource Management**: Proper resource allocation, monitoring, and cleanup
4. **Error Handling**: Comprehensive error handling with fallback strategies
5. **Observability**: Full monitoring and alerting for production deployment

The architecture is designed to be scalable, maintainable, and production-ready, with clear patterns for adding new services and handling increased load. 