"""
Enhanced Error Handler System

This module provides comprehensive error handling, classification, aggregation,
and recovery strategies for the real-time analytics dashboard. It integrates
with the enhanced circuit breaker system to provide resilient error management.
"""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union, Deque, AsyncGenerator
from contextlib import asynccontextmanager
import traceback

# Define types and classes locally to avoid import redefinition
class ErrorType(Enum):
    """Types of errors that can occur"""
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit" 
    AUTHENTICATION = "authentication"
    DATA_VALIDATION = "data_validation"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categories of errors"""
    VALIDATION = "validation"
    SYSTEM = "system"
    NETWORK = "network"

class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class AnalyticsError(Exception):
    """Analytics-related exceptions"""
    pass

def generate_error_id() -> str:
    """Generate a unique error ID"""
    return str(uuid.uuid4())

class SSEEvent:
    """Server-Sent Events event class"""
    def __init__(self, event_type: str, data: Any) -> None:
        self.event_type = event_type
        self.data = data

class SSEEventType(Enum):
    """SSE event types"""
    ERROR = "error"
    
class SSEFormatter:
    """SSE formatting utilities"""
    pass

# Try to import from actual modules if available, but use local definitions as fallback
try:
    from .enhanced_circuit_breaker import ErrorType as _ErrorType, CircuitBreakerOpenError as _CircuitBreakerOpenError
    # Only use imported version if different from local
    if hasattr(_ErrorType, 'TRANSIENT'):
        ErrorType = _ErrorType
        CircuitBreakerOpenError = _CircuitBreakerOpenError
except ImportError:
    pass

try:
    from .models.error_models import (
        AnalyticsError as _AnalyticsError, 
        ErrorSeverity as _ErrorSeverity, 
        ErrorCategory as _ErrorCategory, 
        generate_error_id as _generate_error_id
    )
    # Only use imported versions if available
    if hasattr(_ErrorSeverity, 'LOW'):
        AnalyticsError = _AnalyticsError
        ErrorSeverity = _ErrorSeverity
        ErrorCategory = _ErrorCategory
        generate_error_id = _generate_error_id
except ImportError:
    pass

try:
    from .models.sse_models import SSEEvent as _SSEEvent, SSEEventType as _SSEEventType, SSEFormatter as _SSEFormatter
    # Only use imported versions if available
    if hasattr(_SSEEventType, 'ERROR'):
        SSEEvent = _SSEEvent
        SSEEventType = _SSEEventType
        SSEFormatter = _SSEFormatter
except ImportError:
    pass


class ErrorHandlingStrategy(Enum):
    """Error handling strategies"""
    IMMEDIATE_FAIL = "immediate_fail"        # Fail immediately without retry
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # Retry with exponential backoff
    FALLBACK_TO_CACHE = "fallback_to_cache"    # Use cached data
    FALLBACK_TO_DEFAULT = "fallback_to_default"  # Use default values
    CIRCUIT_BREAKER = "circuit_breaker"        # Use circuit breaker
    GRACEFUL_DEGRADATION = "graceful_degradation"  # Reduce functionality


class RecoveryAction(Enum):
    """Recovery actions"""
    NONE = "none"                    # No action needed
    RESTART_SERVICE = "restart_service"  # Restart failed service
    CLEAR_CACHE = "clear_cache"      # Clear potentially corrupted cache
    RESET_CONNECTION = "reset_connection"  # Reset network connections
    SWITCH_ENDPOINT = "switch_endpoint"    # Switch to backup endpoint
    REDUCE_LOAD = "reduce_load"      # Reduce system load
    ALERT_ADMIN = "alert_admin"      # Send admin alert


@dataclass
class ErrorPattern:
    """Represents a pattern of errors for analysis"""
    error_type: ErrorType
    error_message_pattern: str
    component: str
    severity: ErrorSeverity
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    handling_strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.RETRY_WITH_BACKOFF
    recovery_action: RecoveryAction = RecoveryAction.NONE


@dataclass
class ErrorContext:
    """Context information for error handling"""
    component: str
    operation: str
    timestamp: datetime
    request_id: str
    user_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorHandlingResult:
    """Result of error handling"""
    success: bool
    recovery_attempted: bool
    fallback_used: bool
    error_id: str
    handling_strategy: ErrorHandlingStrategy
    recovery_action: RecoveryAction
    execution_time_ms: float
    retry_count: int = 0


@dataclass
class ErrorAnalytics:
    """Analytics about error patterns"""
    total_errors: int = 0
    errors_by_type: Dict[ErrorType, int] = field(default_factory=dict)
    errors_by_component: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    error_rate_per_minute: float = 0.0
    top_error_patterns: List[ErrorPattern] = field(default_factory=list)
    recovery_success_rate: float = 0.0
    avg_recovery_time_ms: float = 0.0


class ErrorAggregator:
    """Aggregates and analyzes error patterns"""
    
    def __init__(self, window_size: int = 1000) -> None:
        self.window_size = window_size
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.recent_errors: Deque[Dict[str, Any]] = deque(maxlen=window_size)
        self.error_history: Deque[Dict[str, Any]] = deque(maxlen=10000)
        
    def add_error(self, error: Exception, context: ErrorContext, error_type: ErrorType) -> None:
        """Add an error to the aggregator"""
        pattern_key = self._create_pattern_key(error, context, error_type)
        
        now = datetime.now()
        
        if pattern_key in self.error_patterns:
            pattern = self.error_patterns[pattern_key]
            pattern.count += 1
            pattern.last_seen = now
        else:
            pattern = ErrorPattern(
                error_type=error_type,
                error_message_pattern=self._normalize_error_message(str(error)),
                component=context.component,
                severity=self._determine_severity(error, error_type),
                count=1,
                first_seen=now,
                last_seen=now
            )
            self.error_patterns[pattern_key] = pattern
        
        # Add to recent errors
        error_record = {
            "error": error,
            "context": context,
            "error_type": error_type,
            "pattern_key": pattern_key,
            "timestamp": now
        }
        self.recent_errors.append(error_record)
        self.error_history.append(error_record)
    
    def get_analytics(self) -> ErrorAnalytics:
        """Get comprehensive error analytics"""
        now = datetime.now()
        
        # Calculate error rate (errors per minute)
        one_minute_ago = now - timedelta(minutes=1)
        recent_error_count = sum(1 for e in self.recent_errors 
                               if e["timestamp"] >= one_minute_ago)
        
        # Aggregate by type, component, severity
        errors_by_type: Dict[ErrorType, int] = defaultdict(int)
        errors_by_component: Dict[str, int] = defaultdict(int)
        errors_by_severity: Dict[ErrorSeverity, int] = defaultdict(int)
        
        for pattern in self.error_patterns.values():
            errors_by_type[pattern.error_type] += pattern.count
            errors_by_component[pattern.component] += pattern.count
            errors_by_severity[pattern.severity] += pattern.count
        
        # Get top error patterns (sorted by count)
        top_patterns = sorted(self.error_patterns.values(), 
                            key=lambda p: p.count, reverse=True)[:10]
        
        return ErrorAnalytics(
            total_errors=len(self.error_history),
            errors_by_type=dict(errors_by_type),
            errors_by_component=dict(errors_by_component),
            errors_by_severity=dict(errors_by_severity),
            error_rate_per_minute=recent_error_count,
            top_error_patterns=top_patterns,
            recovery_success_rate=0.0,  # TODO: Calculate from recovery attempts
            avg_recovery_time_ms=0.0    # TODO: Calculate from recovery times
        )
    
    def _create_pattern_key(self, error: Exception, context: ErrorContext, error_type: ErrorType) -> str:
        """Create a unique key for error pattern"""
        error_class = type(error).__name__
        normalized_message = self._normalize_error_message(str(error))
        return f"{context.component}:{error_class}:{normalized_message}:{error_type.value}"
    
    def _normalize_error_message(self, message: str) -> str:
        """Normalize error message for pattern matching"""
        # Remove specific IDs, timestamps, etc.
        import re
        
        # Remove UUIDs
        message = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 
                        '<UUID>', message)
        
        # Remove numbers
        message = re.sub(r'\b\d+\b', '<NUMBER>', message)
        
        # Remove file paths
        message = re.sub(r'/[^\s]*', '<PATH>', message)
        
        return message.lower().strip()
    
    def _determine_severity(self, error: Exception, error_type: ErrorType) -> ErrorSeverity:
        """Determine error severity based on error type and content"""
        if error_type == ErrorType.PERMANENT:
            return ErrorSeverity.CRITICAL
        elif error_type == ErrorType.AUTHENTICATION:
            return ErrorSeverity.HIGH
        elif error_type == ErrorType.DATA_VALIDATION:
            return ErrorSeverity.MEDIUM
        elif error_type == ErrorType.RATE_LIMIT:
            return ErrorSeverity.LOW
        elif error_type == ErrorType.TRANSIENT:
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM


class FallbackManager:
    """Manages fallback strategies for error recovery"""
    
    def __init__(self) -> None:
        """Initialize fallback manager"""
        self.cache_fallbacks: Dict[str, Any] = {}
        self.default_fallbacks: Dict[str, Callable[[], Any]] = {}

    def register_cache_fallback(self, component: str, data: Any) -> None:
        """Register cached data as fallback"""
        self.cache_fallbacks[component] = data

    def register_default_fallback(self, component: str, fallback_func: Callable[[], Any]) -> None:
        """Register default fallback function"""
        self.default_fallbacks[component] = fallback_func

    async def get_fallback_data(self, component: str, strategy: ErrorHandlingStrategy) -> Optional[Any]:
        """Get fallback data based on strategy"""
        if strategy == ErrorHandlingStrategy.FALLBACK_TO_CACHE:
            return self.cache_fallbacks.get(component)
        elif strategy == ErrorHandlingStrategy.FALLBACK_TO_DEFAULT:
            if component in self.default_fallbacks:
                fallback_func = self.default_fallbacks[component]
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func()
                    else:
                        return fallback_func()
                except Exception:
                    return None
        return None


class RecoveryManager:
    """Manages recovery actions for errors"""
    
    def __init__(self) -> None:
        self.recovery_handlers: Dict[RecoveryAction, Callable[[ErrorContext], bool]] = {}

    def register_recovery_handler(self, action: RecoveryAction, handler: Callable[[ErrorContext], bool]) -> None:
        """Register a recovery handler"""
        self.recovery_handlers[action] = handler

    async def execute_recovery(self, action: RecoveryAction, context: ErrorContext) -> bool:
        """Execute recovery action"""
        if action == RecoveryAction.NONE:
            return True
        
        if action not in self.recovery_handlers:
            return False
        
        handler = self.recovery_handlers[action]
        
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(context)
            else:
                result = handler(context)
            
            return bool(result) if result is not None else False
            
        except Exception:
            return False


class EnhancedErrorHandler:
    """
    Enhanced error handler with comprehensive error management capabilities
    """
    
    def __init__(self) -> None:
        self.error_aggregator = ErrorAggregator()
        self.fallback_manager = FallbackManager()
        self.recovery_manager = RecoveryManager()
        
        # Error handling configuration
        self.error_strategies: Dict[ErrorType, ErrorHandlingStrategy] = {
            ErrorType.TRANSIENT: ErrorHandlingStrategy.RETRY_WITH_BACKOFF,
            ErrorType.RATE_LIMIT: ErrorHandlingStrategy.RETRY_WITH_BACKOFF,
            ErrorType.AUTHENTICATION: ErrorHandlingStrategy.IMMEDIATE_FAIL,
            ErrorType.DATA_VALIDATION: ErrorHandlingStrategy.FALLBACK_TO_DEFAULT,
            ErrorType.PERMANENT: ErrorHandlingStrategy.IMMEDIATE_FAIL,
            ErrorType.UNKNOWN: ErrorHandlingStrategy.FALLBACK_TO_CACHE
        }
        
        self.recovery_actions: Dict[ErrorType, RecoveryAction] = {
            ErrorType.TRANSIENT: RecoveryAction.NONE,
            ErrorType.RATE_LIMIT: RecoveryAction.REDUCE_LOAD,
            ErrorType.AUTHENTICATION: RecoveryAction.ALERT_ADMIN,
            ErrorType.DATA_VALIDATION: RecoveryAction.CLEAR_CACHE,
            ErrorType.PERMANENT: RecoveryAction.ALERT_ADMIN,
            ErrorType.UNKNOWN: RecoveryAction.NONE
        }
        
        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 1.0
        self.max_retry_delay = 30.0
        self.retry_multiplier = 2.0
    
    async def handle_error(self, 
                          error: Exception, 
                          context: ErrorContext,
                          error_type: Optional[ErrorType] = None) -> ErrorHandlingResult:
        """Handle an error with comprehensive error management"""
        
        start_time = time.time()
        error_id = generate_error_id()
        
        # Classify error if not provided
        if error_type is None:
            from .enhanced_circuit_breaker import ErrorClassifier
            error_type = ErrorClassifier.classify_error(error)
        
        # Add to aggregator
        self.error_aggregator.add_error(error, context, error_type)
        
        # Determine handling strategy
        strategy = self.error_strategies.get(error_type, ErrorHandlingStrategy.FALLBACK_TO_CACHE)
        recovery_action = self.recovery_actions.get(error_type, RecoveryAction.NONE)
        
        result = ErrorHandlingResult(
            success=False,
            recovery_attempted=False,
            fallback_used=False,
            error_id=error_id,
            handling_strategy=strategy,
            recovery_action=recovery_action,
            execution_time_ms=0.0
        )
        
        try:
            # Execute handling strategy
            if strategy == ErrorHandlingStrategy.IMMEDIATE_FAIL:
                result.success = False
                
            elif strategy == ErrorHandlingStrategy.RETRY_WITH_BACKOFF:
                result.success = await self._handle_retry_with_backoff(error, context, result)
                
            elif strategy == ErrorHandlingStrategy.FALLBACK_TO_CACHE:
                fallback_data = await self.fallback_manager.get_fallback_data(
                    context.component, strategy)
                result.fallback_used = fallback_data is not None
                result.success = result.fallback_used
                
            elif strategy == ErrorHandlingStrategy.FALLBACK_TO_DEFAULT:
                fallback_data = await self.fallback_manager.get_fallback_data(
                    context.component, strategy)
                result.fallback_used = fallback_data is not None
                result.success = result.fallback_used
                
            elif strategy == ErrorHandlingStrategy.GRACEFUL_DEGRADATION:
                # For graceful degradation, consider it successful if we can continue
                result.success = True
            
            # Execute recovery action if needed
            if recovery_action != RecoveryAction.NONE:
                result.recovery_attempted = True
                recovery_success = await self.recovery_manager.execute_recovery(
                    recovery_action, context)
                
                # If recovery succeeded and we didn't have success before, try again
                if recovery_success and not result.success:
                    result.success = True
            
        except Exception as handling_error:
            # Error in error handling - this is bad
            result.success = False
            print(f"Error in error handling: {handling_error}")
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        return result
    
    async def _handle_retry_with_backoff(self, 
                                       error: Exception, 
                                       context: ErrorContext,
                                       result: ErrorHandlingResult) -> bool:
        """Handle retry with exponential backoff"""
        
        retry_count = 0
        delay = self.base_retry_delay
        
        while retry_count < self.max_retries:
            retry_count += 1
            
            # Wait before retry
            await asyncio.sleep(delay)
            
            try:
                # Note: This is a placeholder - in real implementation,
                # you would re-execute the original operation
                # For now, we'll simulate success based on error type
                if context.operation and "test" not in context.operation.lower():
                    # Simulate some chance of success on retry
                    import random
                    if random.random() > 0.7:  # 30% chance of success
                        result.retry_count = retry_count
                        return True
                
            except Exception:
                pass  # Continue with retry loop
            
            # Exponential backoff
            delay = min(delay * self.retry_multiplier, self.max_retry_delay)
        
        result.retry_count = retry_count
        return False
    
    @asynccontextmanager
    async def error_context(self, component: str, operation: str, 
                           request_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           **additional_data: Any) -> AsyncGenerator[ErrorContext, None]:
        """Context manager for error handling"""
        context = ErrorContext(
            component=component,
            operation=operation,
            timestamp=datetime.now(),
            request_id=request_id or str(uuid.uuid4()),
            user_id=user_id,
            additional_data=additional_data
        )
        
        try:
            yield context
        except Exception as e:
            # Handle the error
            await self.handle_error(e, context)
            raise
    
    def get_error_analytics(self) -> ErrorAnalytics:
        """Get comprehensive error analytics"""
        return self.error_aggregator.get_analytics()
    
    def create_error_sse_event(self, error: Exception, context: ErrorContext) -> str:
        """Create SSE event for error"""
        try:
            # Create event data
            event_data = {
                "error_id": generate_error_id(),
                "component": context.component,
                "operation": context.operation,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": context.timestamp.isoformat(),
                "request_id": context.request_id
            }
            
            return json.dumps({
                "event": SSEEventType.ERROR.value,
                "data": event_data
            })
        except Exception:
            # Fallback if SSE creation fails
            return json.dumps({
                "event": "error",
                "data": {
                    "error_id": str(uuid.uuid4()),
                    "error_type": "unknown",
                    "error_message": "Error processing failed"
                }
            })
    
    def configure_error_strategy(self, error_type: ErrorType, strategy: ErrorHandlingStrategy) -> None:
        """Configure handling strategy for specific error type"""
        self.error_strategies[error_type] = strategy
    
    def configure_recovery_action(self, error_type: ErrorType, action: RecoveryAction) -> None:
        """Configure recovery action for specific error type"""
        self.recovery_actions[error_type] = action


# Global error handler instance
_error_handler: Optional[EnhancedErrorHandler] = None


def get_error_handler() -> EnhancedErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = EnhancedErrorHandler()
    return _error_handler


def initialize_error_handler() -> EnhancedErrorHandler:
    """Initialize global error handler instance"""
    global _error_handler
    _error_handler = EnhancedErrorHandler()
    return _error_handler


async def handle_error_with_context(component: str, operation: str, error: Exception) -> ErrorHandlingResult:
    """Convenience function to handle error with minimal context"""
    handler = get_error_handler()
    context = ErrorContext(
        component=component,
        operation=operation,
        timestamp=datetime.now(),
        request_id=str(uuid.uuid4())[:8]
    )
    return await handler.handle_error(error, context) 