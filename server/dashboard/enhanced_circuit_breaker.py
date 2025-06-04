"""
Enhanced Circuit Breaker System

This module provides advanced circuit breaker functionality with three states
(CLOSED, OPEN, HALF_OPEN), configurable thresholds, error classification,
and comprehensive monitoring for the real-time analytics dashboard.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union, Tuple, AsyncIterator
from contextlib import asynccontextmanager

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation, all requests pass through
    OPEN = "open"          # Failing fast, no requests pass through  
    HALF_OPEN = "half_open"  # Testing recovery, limited requests pass through


class ErrorType(Enum):
    """Error type classification for different handling strategies"""
    TRANSIENT = "transient"          # Temporary errors (network, timeout)
    PERMANENT = "permanent"          # Configuration/code errors
    RATE_LIMIT = "rate_limit"        # Rate limiting errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    DATA_VALIDATION = "data_validation"  # Data format/validation errors
    UNKNOWN = "unknown"              # Unclassified errors


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    
    # Failure thresholds
    failure_threshold: int = 5              # Failures to trip circuit
    success_threshold: int = 3              # Successes to reset from half-open
    failure_rate_threshold: float = 0.5     # Failure rate to trip (0.0-1.0)
    
    # Time windows
    failure_window_seconds: int = 60        # Time window for failure counting
    open_timeout_seconds: int = 30          # Time to stay open before half-open
    half_open_timeout_seconds: int = 10     # Max time in half-open state
    
    # Request limits
    half_open_max_requests: int = 3         # Max requests to test in half-open
    
    # Error handling
    monitored_exceptions: Tuple[Type[Exception], ...] = (Exception,)  # Exceptions to monitor
    ignored_exceptions: Tuple[Type[Exception], ...] = ()           # Exceptions to ignore
    
    # Recovery settings
    exponential_backoff: bool = True         # Use exponential backoff
    max_backoff_seconds: int = 300          # Max backoff time
    backoff_multiplier: float = 2.0         # Backoff multiplier
    
    # Monitoring
    enable_metrics: bool = True             # Enable detailed metrics
    metrics_window_size: int = 1000         # Max metrics to store


@dataclass
class RequestResult:
    """Result of a circuit breaker protected request"""
    success: bool
    error: Optional[Exception]
    error_type: ErrorType
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class CircuitMetrics:
    """Comprehensive metrics for circuit breaker"""
    
    # State information
    current_state: CircuitState
    state_since: datetime
    state_duration_seconds: float
    
    # Counters
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Rejected due to open circuit
    
    # Error breakdown
    error_counts: Dict[ErrorType, int] = field(default_factory=dict)
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    
    # State transition history
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recent requests (for analysis)
    recent_results: deque[RequestResult] = field(default_factory=lambda: deque(maxlen=100))


class ErrorClassifier:
    """Classifies exceptions into error types for different handling"""
    
    ERROR_PATTERNS = {
        ErrorType.TRANSIENT: [
            "ConnectionError", "TimeoutError", "TemporaryFailure",
            "NetworkError", "ServiceUnavailable", "RequestTimeout"
        ],
        ErrorType.RATE_LIMIT: [
            "RateLimitError", "TooManyRequests", "QuotaExceeded"
        ],
        ErrorType.AUTHENTICATION: [
            "AuthenticationError", "PermissionError", "Unauthorized", "Forbidden"
        ],
        ErrorType.DATA_VALIDATION: [
            "ValidationError", "DataError", "FormatError", "ParseError"
        ],
        ErrorType.PERMANENT: [
            "NotImplementedError", "ConfigurationError", "ImportError"
        ]
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> ErrorType:
        """Classify an exception into an error type"""
        error_name = type(error).__name__
        error_message = str(error).lower()
        
        for error_type, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_name.lower() or pattern.lower() in error_message:
                    return error_type
        
        return ErrorType.UNKNOWN


class RecoveryStrategy(ABC):
    """Abstract base class for recovery strategies"""
    
    @abstractmethod
    async def should_attempt_recovery(self, metrics: CircuitMetrics) -> bool:
        """Determine if recovery should be attempted"""
        pass
    
    @abstractmethod
    def get_backoff_delay(self, attempt: int) -> float:
        """Get delay before next recovery attempt"""
        pass


class ExponentialBackoffStrategy(RecoveryStrategy):
    """Exponential backoff recovery strategy"""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 300.0, multiplier: float = 2.0) -> None:
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
    
    async def should_attempt_recovery(self, metrics: CircuitMetrics) -> bool:
        """Always attempt recovery with exponential backoff"""
        return True
    
    def get_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.initial_delay * (self.multiplier ** attempt)
        return min(delay, self.max_delay)


class AdaptiveRecoveryStrategy(RecoveryStrategy):
    """Adaptive recovery strategy based on error patterns"""
    
    def __init__(self, min_success_rate: float = 0.1) -> None:
        self.min_success_rate = min_success_rate
    
    async def should_attempt_recovery(self, metrics: CircuitMetrics) -> bool:
        """Only attempt recovery if recent success rate is reasonable"""
        if metrics.success_rate >= self.min_success_rate:
            return True
        
        # Check if enough time has passed for transient errors to resolve
        if metrics.state_duration_seconds > 60:
            return True
        
        return False
    
    def get_backoff_delay(self, attempt: int) -> float:
        """Use fixed delay for adaptive strategy"""
        return 30.0  # Fixed 30 second delay


class EnhancedCircuitBreaker:
    """
    Enhanced circuit breaker with three states, configurable thresholds,
    error classification, and advanced recovery strategies.
    """
    
    def __init__(self, 
                 name: str,
                 config: Optional[CircuitBreakerConfig] = None,
                 recovery_strategy: Optional[RecoveryStrategy] = None) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.recovery_strategy = recovery_strategy or ExponentialBackoffStrategy()
        
        # State management
        self._state = CircuitState.CLOSED
        self._state_since = datetime.now()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._backoff_attempt = 0
        
        # Request tracking
        self._request_history: deque[RequestResult] = deque(maxlen=self.config.metrics_window_size)
        self._recent_results: deque[RequestResult] = deque(maxlen=100)
        
        # Metrics
        self._metrics = CircuitMetrics(
            current_state=self._state,
            state_since=self._state_since,
            state_duration_seconds=0.0
        )
        
        # Locks for thread safety
        self._state_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)"""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection"""
        async with self.protect():
            return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
    
    @asynccontextmanager
    async def protect(self) -> AsyncIterator[None]:
        """Context manager for circuit breaker protection"""
        if not await self._can_execute():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
        
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        try:
            yield
            # Success
            duration_ms = (time.time() - start_time) * 1000
            result = RequestResult(
                success=True,
                error=None,
                error_type=ErrorType.UNKNOWN,
                duration_ms=duration_ms,
                request_id=request_id
            )
            await self._record_success(result)
            
        except Exception as e:
            # Failure
            duration_ms = (time.time() - start_time) * 1000
            error_type = ErrorClassifier.classify_error(e)
            
            result = RequestResult(
                success=False,
                error=e,
                error_type=error_type,
                duration_ms=duration_ms,
                request_id=request_id
            )
            
            if self._should_monitor_error(e):
                await self._record_failure(result)
            
            raise
    
    async def _can_execute(self) -> bool:
        """Check if request can be executed based on current state"""
        async with self._state_lock:
            now = datetime.now()
            
            if self._state == CircuitState.CLOSED:
                return True
            
            elif self._state == CircuitState.OPEN:
                # Check if we should transition to half-open
                time_since_open = (now - self._state_since).total_seconds()
                
                if time_since_open >= self.config.open_timeout_seconds:
                    await self._transition_to_half_open()
                    return True
                
                return False
            
            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                if self._half_open_requests < self.config.half_open_max_requests:
                    self._half_open_requests += 1
                    return True
                
                return False
        
        return False
    
    async def _record_success(self, result: RequestResult) -> None:
        """Record a successful request"""
        async with self._state_lock:
            self._success_count += 1
            self._recent_results.append(result)
            
            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to_closed()
            
            await self._update_metrics(result)
    
    async def _record_failure(self, result: RequestResult) -> None:
        """Record a failed request"""
        async with self._state_lock:
            self._failure_count += 1
            self._recent_results.append(result)
            
            # Check if we should trip the circuit
            if self._state == CircuitState.CLOSED:
                if await self._should_trip_circuit():
                    await self._transition_to_open()
            
            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                await self._transition_to_open()
            
            await self._update_metrics(result)
    
    async def _should_trip_circuit(self) -> bool:
        """Determine if circuit should be tripped based on failure patterns"""
        # Simple failure count threshold
        if self._failure_count >= self.config.failure_threshold:
            return True
        
        # Failure rate threshold (within time window)
        recent_requests = self._get_recent_requests_in_window()
        if len(recent_requests) >= 10:  # Minimum sample size
            failures = sum(1 for r in recent_requests if not r.success)
            failure_rate = failures / len(recent_requests)
            
            if failure_rate >= self.config.failure_rate_threshold:
                return True
        
        return False
    
    def _get_recent_requests_in_window(self) -> List[RequestResult]:
        """Get recent requests within the failure window"""
        cutoff_time = datetime.now() - timedelta(seconds=self.config.failure_window_seconds)
        return [r for r in self._recent_results if r.timestamp >= cutoff_time]
    
    async def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state"""
        await self._change_state(CircuitState.OPEN)
        self._backoff_attempt += 1
    
    async def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state"""
        await self._change_state(CircuitState.HALF_OPEN)
        self._half_open_requests = 0
        self._success_count = 0
        self._failure_count = 0
    
    async def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state"""
        await self._change_state(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._backoff_attempt = 0
    
    async def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit state and record transition"""
        old_state = self._state
        self._state = new_state
        self._state_since = datetime.now()
        
        # Record state transition
        transition = {
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": self._state_since.isoformat(),
            "failure_count": self._failure_count,
            "success_count": self._success_count
        }
        
        async with self._metrics_lock:
            self._metrics.state_transitions.append(transition)
            # Keep only last 50 transitions
            if len(self._metrics.state_transitions) > 50:
                self._metrics.state_transitions = self._metrics.state_transitions[-50:]
    
    def _should_monitor_error(self, error: Exception) -> bool:
        """Check if error should be monitored by circuit breaker"""
        # Check if error is in ignored exceptions
        for ignored_type in self.config.ignored_exceptions:
            if isinstance(error, ignored_type):  # type: ignore[arg-type]
                return False
        
        # Check if error is in monitored exceptions
        for monitored_type in self.config.monitored_exceptions:
            if isinstance(error, monitored_type):  # type: ignore[arg-type]
                return True
        
        return False
    
    async def _update_metrics(self, result: RequestResult) -> None:
        """Update comprehensive metrics"""
        async with self._metrics_lock:
            # Update basic counters
            self._metrics.total_requests += 1
            
            if result.success:
                self._metrics.successful_requests += 1
            else:
                self._metrics.failed_requests += 1
                # Update error counts dictionary
                if result.error_type not in self._metrics.error_counts:
                    self._metrics.error_counts[result.error_type] = 0
                self._metrics.error_counts[result.error_type] += 1
            
            # Update state info
            self._metrics.current_state = self._state
            self._metrics.state_since = self._state_since
            self._metrics.state_duration_seconds = (datetime.now() - self._state_since).total_seconds()
            
            # Calculate rates
            if self._metrics.total_requests > 0:
                self._metrics.success_rate = self._metrics.successful_requests / self._metrics.total_requests
                self._metrics.failure_rate = self._metrics.failed_requests / self._metrics.total_requests
            
            # Update response time metrics
            recent_durations = [r.duration_ms for r in self._recent_results if r.success]
            if recent_durations:
                self._metrics.avg_response_time_ms = sum(recent_durations) / len(recent_durations)
                sorted_durations = sorted(recent_durations)
                p95_index = int(len(sorted_durations) * 0.95)
                self._metrics.p95_response_time_ms = sorted_durations[p95_index] if sorted_durations else 0.0
            
            # Store recent result
            self._metrics.recent_results.append(result)
    
    async def get_metrics(self) -> CircuitMetrics:
        """Get current circuit breaker metrics"""
        async with self._metrics_lock:
            # Update duration
            self._metrics.state_duration_seconds = (datetime.now() - self._state_since).total_seconds()
            return self._metrics
    
    async def reset(self) -> None:
        """Reset circuit breaker to initial state"""
        async with self._state_lock:
            await self._transition_to_closed()
            self._recent_results.clear()
            
            # Reset metrics
            async with self._metrics_lock:
                self._metrics = CircuitMetrics(
                    current_state=self._state,
                    state_since=self._state_since,
                    state_duration_seconds=0.0
                )


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers with centralized monitoring"""
    
    def __init__(self) -> None:
        self._breakers: Dict[str, EnhancedCircuitBreaker] = {}
        self._global_metrics = {
            "total_breakers": 0,
            "open_breakers": 0,
            "half_open_breakers": 0,
            "closed_breakers": 0,
            "total_requests": 0,
            "total_failures": 0
        }
    
    def create_breaker(self, 
                      name: str, 
                      config: Optional[CircuitBreakerConfig] = None,
                      recovery_strategy: Optional[RecoveryStrategy] = None) -> EnhancedCircuitBreaker:
        """Create and register a new circuit breaker"""
        if name in self._breakers:
            raise ValueError(f"Circuit breaker '{name}' already exists")
        
        breaker = EnhancedCircuitBreaker(name, config, recovery_strategy)
        self._breakers[name] = breaker
        self._global_metrics["total_breakers"] += 1
        self._global_metrics["closed_breakers"] += 1
        
        return breaker
    
    def get_breaker(self, name: str) -> Optional[EnhancedCircuitBreaker]:
        """Get circuit breaker by name"""
        return self._breakers.get(name)
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers"""
        metrics: Dict[str, Any] = {
            "global": self._global_metrics.copy(),
            "breakers": {}
        }
        
        # Update global state counts
        updated_metrics = {
            "total_breakers": self._global_metrics["total_breakers"],
            "open_breakers": 0,
            "half_open_breakers": 0,
            "closed_breakers": 0,
            "total_requests": 0,
            "total_failures": 0
        }
        
        for name, breaker in self._breakers.items():
            breaker_metrics = await breaker.get_metrics()
            metrics["breakers"][name] = breaker_metrics
            
            # Update global counts
            if breaker.is_open:
                updated_metrics["open_breakers"] += 1
            elif breaker.is_half_open:
                updated_metrics["half_open_breakers"] += 1
            else:
                updated_metrics["closed_breakers"] += 1
            
            updated_metrics["total_requests"] += breaker_metrics.total_requests
            updated_metrics["total_failures"] += breaker_metrics.failed_requests
        
        # Update global metrics
        self._global_metrics.update(updated_metrics)
        metrics["global"] = self._global_metrics.copy()
        return metrics
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset()


# Global circuit breaker manager
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager instance"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def create_circuit_breaker(name: str, 
                         config: Optional[CircuitBreakerConfig] = None,
                         recovery_strategy: Optional[RecoveryStrategy] = None) -> EnhancedCircuitBreaker:
    """Create and register a circuit breaker"""
    manager = get_circuit_breaker_manager()
    return manager.create_breaker(name, config, recovery_strategy)


def get_circuit_breaker(name: str) -> Optional[EnhancedCircuitBreaker]:
    """Get circuit breaker by name"""
    manager = get_circuit_breaker_manager()
    return manager.get_breaker(name) 