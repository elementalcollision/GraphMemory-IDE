"""
Test Suite for Enhanced Circuit Breaker System

This module contains comprehensive tests for the enhanced circuit breaker
functionality including state transitions, error classification, recovery
strategies, and metrics collection.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import Dict

from server.dashboard.enhanced_circuit_breaker import (
    EnhancedCircuitBreaker, CircuitBreakerConfig, CircuitState, ErrorType,
    ErrorClassifier, ExponentialBackoffStrategy, AdaptiveRecoveryStrategy,
    CircuitBreakerOpenError, CircuitBreakerManager, RequestResult,
    get_circuit_breaker_manager, create_circuit_breaker
)


class TestErrorClassifier:
    """Test error classification functionality"""
    
    def test_classify_transient_errors(self) -> None:
        """Test classification of transient errors"""
        errors = [
            ConnectionError("Network connection failed"),
            TimeoutError("Request timed out"),
            Exception("ServiceUnavailable: Service temporarily down")
        ]
        
        for error in errors:
            assert ErrorClassifier.classify_error(error) == ErrorType.TRANSIENT
    
    def test_classify_rate_limit_errors(self) -> None:
        """Test classification of rate limit errors"""
        errors = [
            Exception("RateLimitError: Too many requests"),
            Exception("TooManyRequests"),
            Exception("QuotaExceeded: API quota exceeded")
        ]
        
        for error in errors:
            assert ErrorClassifier.classify_error(error) == ErrorType.RATE_LIMIT
    
    def test_classify_authentication_errors(self) -> None:
        """Test classification of authentication errors"""
        errors = [
            PermissionError("Access denied"),
            Exception("Unauthorized: Invalid credentials"),
            Exception("Forbidden: Insufficient permissions")
        ]
        
        for error in errors:
            assert ErrorClassifier.classify_error(error) == ErrorType.AUTHENTICATION
    
    def test_classify_data_validation_errors(self) -> None:
        """Test classification of data validation errors"""
        errors = [
            ValueError("ValidationError: Invalid data format"),
            Exception("DataError: Corrupted data"),
            Exception("ParseError: Unable to parse response")
        ]
        
        for error in errors:
            assert ErrorClassifier.classify_error(error) == ErrorType.DATA_VALIDATION
    
    def test_classify_permanent_errors(self) -> None:
        """Test classification of permanent errors"""
        errors = [
            NotImplementedError("Feature not implemented"),
            Exception("ConfigurationError: Invalid config"),
            ImportError("Module not found")
        ]
        
        for error in errors:
            assert ErrorClassifier.classify_error(error) == ErrorType.PERMANENT
    
    def test_classify_unknown_errors(self) -> None:
        """Test classification of unknown errors"""
        error = Exception("Some random error message")
        assert ErrorClassifier.classify_error(error) == ErrorType.UNKNOWN


class TestRecoveryStrategies:
    """Test recovery strategy implementations"""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(self) -> None:
        """Test exponential backoff recovery strategy"""
        strategy = ExponentialBackoffStrategy(initial_delay=1.0, max_delay=10.0, multiplier=2.0)
        
        # Should always attempt recovery
        metrics = MagicMock()
        assert await strategy.should_attempt_recovery(metrics) is True
        
        # Test backoff delays
        assert strategy.get_backoff_delay(0) == 1.0
        assert strategy.get_backoff_delay(1) == 2.0
        assert strategy.get_backoff_delay(2) == 4.0
        assert strategy.get_backoff_delay(3) == 8.0
        assert strategy.get_backoff_delay(4) == 10.0  # Capped at max_delay
    
    @pytest.mark.asyncio
    async def test_adaptive_recovery_strategy(self) -> None:
        """Test adaptive recovery strategy"""
        strategy = AdaptiveRecoveryStrategy(min_success_rate=0.2)
        
        # Mock metrics with good success rate
        metrics = MagicMock()
        metrics.success_rate = 0.5
        metrics.state_duration_seconds = 30
        
        assert await strategy.should_attempt_recovery(metrics) is True
        
        # Mock metrics with poor success rate but long duration
        metrics.success_rate = 0.1
        metrics.state_duration_seconds = 70
        
        assert await strategy.should_attempt_recovery(metrics) is True
        
        # Mock metrics with poor success rate and short duration
        metrics.success_rate = 0.1
        metrics.state_duration_seconds = 30
        
        assert await strategy.should_attempt_recovery(metrics) is False
        
        # Test fixed backoff delay
        assert strategy.get_backoff_delay(0) == 30.0
        assert strategy.get_backoff_delay(5) == 30.0


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration"""
    
    def test_default_config(self) -> None:
        """Test default configuration values"""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.failure_rate_threshold == 0.5
        assert config.failure_window_seconds == 60
        assert config.open_timeout_seconds == 30
        assert config.half_open_max_requests == 3
        assert config.monitored_exceptions == (Exception,)
        assert config.ignored_exceptions == ()
        assert config.exponential_backoff is True
        assert config.enable_metrics is True
    
    def test_custom_config(self) -> None:
        """Test custom configuration values"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            failure_rate_threshold=0.8,
            open_timeout_seconds=60,
            monitored_exceptions=(ValueError, TypeError)
        )
        
        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.failure_rate_threshold == 0.8
        assert config.open_timeout_seconds == 60
        assert config.monitored_exceptions == (ValueError, TypeError)


class TestEnhancedCircuitBreaker:
    """Test enhanced circuit breaker functionality"""
    
    @pytest.fixture
    def circuit_breaker(self) -> EnhancedCircuitBreaker:
        """Create circuit breaker for testing"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=1,  # Short timeout for testing
            failure_window_seconds=10
        )
        return EnhancedCircuitBreaker("test-breaker", config)
    
    def test_initial_state(self, circuit_breaker) -> None:
        """Test initial circuit breaker state"""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed is True
        assert circuit_breaker.is_open is False
        assert circuit_breaker.is_half_open is False
        assert circuit_breaker.name == "test-breaker"
    
    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker) -> None:
        """Test successful function call through circuit breaker"""
        
        async def success_func() -> str:
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_closed is True
        
        # Check metrics
        metrics = await circuit_breaker.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_failed_call(self, circuit_breaker) -> None:
        """Test failed function call through circuit breaker"""
        
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_closed is True  # Still closed after one failure
        
        # Check metrics
        metrics = await circuit_breaker.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.failure_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker) -> None:
        """Test circuit opens after threshold failures"""
        
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        # Generate failures to trip circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)
        
        # Circuit should now be open
        assert circuit_breaker.is_open is True
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(fail_func)
        
        # Check metrics
        metrics = await circuit_breaker.get_metrics()
        assert metrics.total_requests == 3  # Only the actual calls, not the rejected one
        assert metrics.failed_requests == 3
        assert metrics.current_state == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker) -> None:
        """Test circuit transitions from open to half-open"""
        
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        # Trip the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open is True
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open
        async def success_func() -> str:
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_half_open is True
    
    @pytest.mark.asyncio
    async def test_circuit_closes_from_half_open(self, circuit_breaker) -> None:
        """Test circuit closes from half-open after successful calls"""
        
        # Trip the circuit
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)
        
        # Wait for transition to half-open
        await asyncio.sleep(1.1)
        
        # Make successful calls to close circuit
        async def success_func() -> str:
            return "success"
        
        # First success should transition to half-open
        await circuit_breaker.call(success_func)
        assert circuit_breaker.is_half_open is True
        
        # Second success should close the circuit
        await circuit_breaker.call(success_func)
        assert circuit_breaker.is_closed is True
        
        # Check metrics
        metrics = await circuit_breaker.get_metrics()
        assert metrics.current_state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_opens_from_half_open_on_failure(self, circuit_breaker) -> None:
        """Test circuit opens from half-open on any failure"""
        
        # Trip the circuit
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)
        
        # Wait for transition to half-open
        await asyncio.sleep(1.1)
        
        # Any failure in half-open should go back to open
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open is True
    
    @pytest.mark.asyncio
    async def test_context_manager_usage(self, circuit_breaker) -> None:
        """Test circuit breaker as context manager"""
        
        # Successful context
        async with circuit_breaker.protect():
            result = "success"
        
        assert circuit_breaker.is_closed is True
        
        # Failed context
        with pytest.raises(ValueError):
            async with circuit_breaker.protect():
                raise ValueError("Test error")
        
        # Check metrics
        metrics = await circuit_breaker.get_metrics()
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 1
    
    @pytest.mark.asyncio
    async def test_ignored_exceptions(self) -> None:
        """Test ignored exceptions are not monitored"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            ignored_exceptions=(KeyError,),
            monitored_exceptions=(ValueError, TypeError)
        )
        breaker = EnhancedCircuitBreaker("test", config)
        
        # KeyError should be ignored
        with pytest.raises(KeyError):
            async with breaker.protect():
                raise KeyError("Ignored error")
        
        # Should still be closed since error was ignored
        assert breaker.is_closed is True
        
        # ValueError should be monitored
        with pytest.raises(ValueError):
            async with breaker.protect():
                raise ValueError("Monitored error")
        
        metrics = await breaker.get_metrics()
        assert metrics.failed_requests == 1  # Only the ValueError
    
    @pytest.mark.asyncio
    async def test_failure_rate_threshold(self) -> None:
        """Test failure rate threshold triggering"""
        config = CircuitBreakerConfig(
            failure_threshold=10,  # High count threshold
            failure_rate_threshold=0.6,  # 60% failure rate
            failure_window_seconds=60
        )
        breaker = EnhancedCircuitBreaker("test", config)
        
        # Generate mixed success/failure pattern
        for i in range(10):
            try:
                if i < 4:  # 4 successes
                    async with breaker.protect():
                        pass
                else:  # 6 failures = 60% failure rate
                    async with breaker.protect():
                        raise ValueError("Test error")
            except (ValueError, CircuitBreakerOpenError):
                pass
        
        # Should trip on failure rate
        assert breaker.is_open is True
    
    @pytest.mark.asyncio
    async def test_metrics_accuracy(self, circuit_breaker) -> None:
        """Test metrics accuracy and completeness"""
        
        # Generate some requests
        for i in range(5):
            try:
                if i < 3:
                    async with circuit_breaker.protect():
                        await asyncio.sleep(0.01)  # Small delay for timing
                else:
                    async with circuit_breaker.protect():
                        raise ValueError("Test error")
            except ValueError:
                pass
        
        metrics = await circuit_breaker.get_metrics()
        
        assert metrics.total_requests == 5
        assert metrics.successful_requests == 3
        assert metrics.failed_requests == 2
        assert metrics.success_rate == 0.6
        assert metrics.failure_rate == 0.4
        assert metrics.avg_response_time_ms > 0
        assert len(metrics.recent_results) == 5
        assert len(metrics.error_counts) > 0
        # ValueError without validation pattern gets classified as UNKNOWN
        assert ErrorType.UNKNOWN in metrics.error_counts
    
    @pytest.mark.asyncio
    async def test_reset_functionality(self, circuit_breaker) -> None:
        """Test circuit breaker reset"""
        
        # Trip the circuit
        async def fail_func() -> None:
            raise ValueError("Test error")
        
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(fail_func)
        
        assert circuit_breaker.is_open is True
        
        # Reset the circuit
        await circuit_breaker.reset()
        
        assert circuit_breaker.is_closed is True
        
        # Should work normally after reset
        async def success_func() -> str:
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality"""
    
    def test_create_and_get_breaker(self) -> None:
        """Test creating and retrieving circuit breakers"""
        manager = CircuitBreakerManager()
        
        # Create a breaker
        breaker = manager.create_breaker("test-breaker")
        assert breaker.name == "test-breaker"
        assert breaker.is_closed is True
        
        # Retrieve the breaker
        retrieved = manager.get_breaker("test-breaker")
        assert retrieved is breaker
        
        # Non-existent breaker should return None
        assert manager.get_breaker("non-existent") is None
    
    def test_duplicate_breaker_names(self) -> None:
        """Test handling of duplicate breaker names"""
        manager = CircuitBreakerManager()
        
        manager.create_breaker("test-breaker")
        
        with pytest.raises(ValueError, match="already exists"):
            manager.create_breaker("test-breaker")
    
    @pytest.mark.asyncio
    async def test_global_metrics(self) -> None:
        """Test global metrics collection"""
        manager = CircuitBreakerManager()
        
        # Create multiple breakers
        breaker1 = manager.create_breaker("breaker-1")
        breaker2 = manager.create_breaker("breaker-2")
        
        # Generate some activity
        async with breaker1.protect():
            pass
        
        try:
            async with breaker2.protect():
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Get global metrics
        metrics = await manager.get_all_metrics()
        
        assert "global" in metrics
        assert "breakers" in metrics
        assert metrics["global"]["total_breakers"] == 2
        assert metrics["global"]["closed_breakers"] == 2
        assert metrics["global"]["total_requests"] == 2
        assert metrics["global"]["total_failures"] == 1
        
        assert "breaker-1" in metrics["breakers"]
        assert "breaker-2" in metrics["breakers"]
    
    @pytest.mark.asyncio
    async def test_reset_all_breakers(self) -> None:
        """Test resetting all circuit breakers"""
        manager = CircuitBreakerManager()
        
        # Create and trip a breaker
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = manager.create_breaker("test-breaker", config)
        
        try:
            async with breaker.protect():
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert breaker.is_open is True
        
        # Reset all breakers
        await manager.reset_all()
        
        assert breaker.is_closed is True


class TestGlobalFunctions:
    """Test global circuit breaker functions"""
    
    def test_global_manager_singleton(self) -> None:
        """Test global manager is singleton"""
        manager1 = get_circuit_breaker_manager()
        manager2 = get_circuit_breaker_manager()
        
        assert manager1 is manager2
    
    def test_create_global_circuit_breaker(self) -> None:
        """Test creating circuit breaker through global function"""
        breaker = create_circuit_breaker("global-test")
        assert breaker.name == "global-test"
        
        # Should be retrievable through manager
        manager = get_circuit_breaker_manager()
        retrieved = manager.get_breaker("global-test")
        assert retrieved is breaker


@pytest.mark.asyncio
async def test_real_world_scenario() -> None:
    """Test realistic usage scenario"""
    
    # Create circuit breaker for database operations
    db_config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        failure_rate_threshold=0.7,
        open_timeout_seconds=2
    )
    
    db_breaker = create_circuit_breaker("database", db_config)
    
    # Simulate database operations
    success_count = 0
    failure_count = 0
    
    async def db_operation(should_fail=False) -> Dict[str, str]:
        async with db_breaker.protect():
            if should_fail:
                raise ConnectionError("Database connection failed")
            await asyncio.sleep(0.001)  # Simulate DB query time
            return {"data": "result"}
    
    # Normal operations
    for i in range(10):
        try:
            result = await db_operation(should_fail=i > 7)  # Fail last 2
            success_count += 1
        except (ConnectionError, CircuitBreakerOpenError):
            failure_count += 1
    
    # Check breaker is still closed (not enough failures)
    assert db_breaker.is_closed is True
    
    # Generate more failures to trip circuit
    for i in range(5):
        try:
            await db_operation(should_fail=True)
        except (ConnectionError, CircuitBreakerOpenError):
            failure_count += 1
    
    # Circuit should be open now
    assert db_breaker.is_open is True
    
    # Wait for recovery
    await asyncio.sleep(2.1)
    
    # Successful operations should gradually close circuit
    for i in range(3):
        try:
            result = await db_operation(should_fail=False)
            success_count += 1
        except CircuitBreakerOpenError:
            failure_count += 1
    
    # Circuit should be closed again
    assert db_breaker.is_closed is True
    
    # Verify metrics
    metrics = await db_breaker.get_metrics()
    assert metrics.total_requests > 0
    assert metrics.successful_requests > 0
    assert metrics.failed_requests > 0
    assert len(metrics.state_transitions) >= 2  # At least open and close transitions


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 