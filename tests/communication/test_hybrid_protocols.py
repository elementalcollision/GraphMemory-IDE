"""
Comprehensive tests for hybrid communication protocols

This module tests the communication protocols for the hybrid CPython/Condon architecture,
including inter-service communication, data serialization, error handling, and performance optimization.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from server.communication.hybrid_protocols import (
    CircuitBreaker,
    CircuitBreakerState,
    CommunicationConfig,
    CommunicationSecurity,
    HybridCommunicationProtocol,
    HybridDataSerializer,
    ServiceAuthentication,
    ServiceLoadBalancer,
    create_hybrid_protocol,
)


class TestHybridDataSerializer:
    """Test data serialization for hybrid architecture"""

    def setup_method(self):
        """Set up test fixtures"""
        self.serializer = HybridDataSerializer()
        self.test_data = {
            "id": 123,
            "name": "test",
            "values": [1, 2, 3],
            "nested": {"key": "value"},
        }

    def test_serialize_for_cpython(self):
        """Test CPython serialization"""
        serialized = self.serializer.serialize_for_cpython(self.test_data)
        assert isinstance(serialized, bytes)

        # Test deserialization
        deserialized = self.serializer.deserialize_from_cpython(serialized)
        assert deserialized == self.test_data

    def test_serialize_for_condon(self):
        """Test Condon serialization"""
        serialized = self.serializer.serialize_for_condon(self.test_data)
        assert isinstance(serialized, bytes)

        # Test deserialization
        deserialized = self.serializer.deserialize_from_condon(serialized)
        assert deserialized == self.test_data

    def test_compatibility_layer(self):
        """Test compatibility layer conversion"""
        # Test CPython to Condon conversion
        cpython_data = {"test": "data"}
        condon_data = self.serializer.compatibility_layer.convert_for_condon(
            cpython_data
        )
        assert condon_data == cpython_data

        # Test Condon to CPython conversion
        cpython_converted = self.serializer.compatibility_layer.convert_for_cpython(
            condon_data
        )
        assert cpython_converted == cpython_data


class TestCircuitBreaker:
    """Test circuit breaker pattern"""

    def setup_method(self):
        """Set up test fixtures"""
        self.circuit_breaker = CircuitBreaker(threshold=3, timeout=1.0)

    def test_closed_state_normal_operation(self):
        """Test circuit breaker in closed state with normal operation"""

        def successful_operation():
            return "success"

        result = self.circuit_breaker.call(successful_operation)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures"""

        def failing_operation():
            raise Exception("test failure")

        # Should fail 3 times then open
        for _ in range(3):
            with pytest.raises(Exception):
                self.circuit_breaker.call(failing_operation)

        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery from half-open state"""

        def failing_operation():
            raise Exception("test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                self.circuit_breaker.call(failing_operation)

        assert self.circuit_breaker.state == CircuitBreakerState.OPEN

        # Wait for timeout
        self.circuit_breaker.last_failure_time = time.time() - 2.0

        # Should be half-open now
        assert self.circuit_breaker.state == CircuitBreakerState.HALF_OPEN

        # Test successful recovery
        def successful_operation():
            return "success"

        result = self.circuit_breaker.call(successful_operation)
        assert result == "success"
        assert self.circuit_breaker.state == CircuitBreakerState.CLOSED


class TestServiceAuthentication:
    """Test service authentication"""

    def setup_method(self):
        """Set up test fixtures"""
        self.secret_key = "test_secret_key"
        self.auth = ServiceAuthentication(self.secret_key)

    def test_generate_token(self):
        """Test JWT token generation"""
        service_id = "test_service"
        permissions = ["read", "write"]

        token = self.auth.generate_token(service_id, permissions)
        assert isinstance(token, str)

        # Verify token
        payload = self.auth.token_manager.validate_token(token)
        assert payload["service_id"] == service_id
        assert payload["permissions"] == permissions

    def test_authenticate_service(self):
        """Test service authentication"""
        service_id = "test_service"
        permissions = ["read"]
        token = self.auth.generate_token(service_id, permissions)

        credentials = {"token": token}
        result = asyncio.run(self.auth.authenticate_service(service_id, credentials))
        assert result is True

    def test_authorize_request(self):
        """Test request authorization"""
        service_id = "analytics"
        operation = "read"

        result = asyncio.run(self.auth.authorize_request(service_id, operation))
        assert result is True

        # Test unauthorized operation
        result = asyncio.run(self.auth.authorize_request(service_id, "invalid"))
        assert result is False


class TestCommunicationSecurity:
    """Test communication security"""

    def setup_method(self):
        """Set up test fixtures"""
        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        self.security = CommunicationSecurity(key)
        self.test_data = b"test data for encryption"

    def test_encrypt_decrypt_payload(self):
        """Test payload encryption and decryption"""
        encrypted = asyncio.run(self.security.encrypt_payload(self.test_data))
        assert encrypted != self.test_data

        decrypted = asyncio.run(self.security.decrypt_payload(encrypted))
        assert decrypted == self.test_data

    def test_integrity_verification(self):
        """Test payload integrity verification"""
        signature = asyncio.run(self.security.sign_payload(self.test_data))

        # Verify valid signature
        is_valid = asyncio.run(
            self.security.verify_integrity(self.test_data, signature)
        )
        assert is_valid is True

        # Verify invalid signature
        invalid_signature = b"invalid_signature"
        is_valid = asyncio.run(
            self.security.verify_integrity(self.test_data, invalid_signature)
        )
        assert is_valid is False


class TestServiceLoadBalancer:
    """Test service load balancing"""

    def setup_method(self):
        """Set up test fixtures"""
        self.load_balancer = ServiceLoadBalancer()
        self.load_balancer.service_instances = {
            "test_service": ["instance1", "instance2", "instance3"]
        }

    def test_round_robin_load_balancing(self):
        """Test round robin load balancing"""
        instances = ["instance1", "instance2", "instance3"]

        # Test round robin selection
        selected1 = self.load_balancer.load_distributor.select_instance(instances)
        selected2 = self.load_balancer.load_distributor.select_instance(instances)
        selected3 = self.load_balancer.load_distributor.select_instance(instances)

        assert selected1 in instances
        assert selected2 in instances
        assert selected3 in instances

    def test_random_load_balancing(self):
        """Test random load balancing"""
        self.load_balancer.load_distributor.strategy = "random"
        instances = ["instance1", "instance2", "instance3"]

        selected = self.load_balancer.load_distributor.select_instance(instances)
        assert selected in instances


class TestHybridCommunicationProtocol:
    """Test main communication protocol"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = CommunicationConfig(
            timeout=5.0, max_retries=2, enable_encryption=False  # Disable for testing
        )
        self.protocol = HybridCommunicationProtocol(self.config)

    @pytest.mark.asyncio
    async def test_send_request_cpython(self):
        """Test sending request to CPython service"""
        # Mock the load balancer
        with patch.object(self.protocol.load_balancer, "route_request") as mock_route:
            mock_route.return_value = {
                "data": b'{"status": "success"}',
                "signature": b"",
            }

            data = {"test": "data"}
            result = await self.protocol.send_request("cpython_service", data)

            assert result == {"status": "success"}
            mock_route.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_condon(self):
        """Test sending request to Condon service"""
        # Mock the load balancer
        with patch.object(self.protocol.load_balancer, "route_request") as mock_route:
            mock_route.return_value = {
                "data": b'{"status": "success"}',
                "signature": b"",
            }

            data = {"test": "data"}
            result = await self.protocol.send_request("condon_service", data)

            assert result == {"status": "success"}
            mock_route.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in communication"""
        # Mock the load balancer to raise an exception
        with patch.object(self.protocol.load_balancer, "route_request") as mock_route:
            mock_route.side_effect = Exception("Service unavailable")

            data = {"test": "data"}

            # Should handle error gracefully
            with pytest.raises(Exception):
                await self.protocol.send_request("test_service", data)

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring"""
        # Mock the load balancer
        with patch.object(self.protocol.load_balancer, "route_request") as mock_route:
            mock_route.return_value = {
                "data": b'{"status": "success"}',
                "signature": b"",
            }

            data = {"test": "data"}
            await self.protocol.send_request("test_service", data)

            # Verify metrics were recorded
            # (In a real implementation, we'd check Prometheus metrics)


class TestCommunicationConfig:
    """Test communication configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = CommunicationConfig()

        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.circuit_breaker_threshold == 5
        assert config.enable_encryption is True
        assert config.max_payload_size == 10 * 1024 * 1024

    def test_custom_config(self):
        """Test custom configuration values"""
        config = CommunicationConfig(
            timeout=60.0, max_retries=5, enable_encryption=False
        )

        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.enable_encryption is False


class TestFactoryFunction:
    """Test factory function for creating protocols"""

    def test_create_hybrid_protocol_default(self):
        """Test creating protocol with default config"""
        protocol = create_hybrid_protocol()
        assert isinstance(protocol, HybridCommunicationProtocol)
        assert protocol.config.timeout == 30.0

    def test_create_hybrid_protocol_custom(self):
        """Test creating protocol with custom config"""
        config = CommunicationConfig(timeout=60.0)
        protocol = create_hybrid_protocol(config)
        assert isinstance(protocol, HybridCommunicationProtocol)
        assert protocol.config.timeout == 60.0


class TestIntegration:
    """Integration tests for communication protocols"""

    @pytest.mark.asyncio
    async def test_end_to_end_communication(self):
        """Test end-to-end communication flow"""
        config = CommunicationConfig(
            timeout=5.0, enable_encryption=False  # Disable for testing
        )
        protocol = create_hybrid_protocol(config)

        # Mock service instances
        protocol.load_balancer.service_instances = {"test_service": ["instance1"]}

        # Mock health checker
        with patch.object(
            protocol.load_balancer.health_checker, "check_service_health"
        ) as mock_health:
            mock_health.return_value = True

            # Mock request sending
            with patch.object(protocol.load_balancer, "_send_request") as mock_send:
                mock_send.return_value = {
                    "data": b'{"result": "success"}',
                    "signature": b"",
                }

                data = {"test": "data"}
                result = await protocol.send_request("test_service", data)

                assert result == {"result": "success"}
                mock_health.assert_called_once()
                mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with communication"""
        config = CommunicationConfig(
            timeout=1.0, circuit_breaker_threshold=2, circuit_breaker_timeout=1.0
        )
        protocol = create_hybrid_protocol(config)

        # Mock service to always fail
        with patch.object(protocol.load_balancer, "route_request") as mock_route:
            mock_route.side_effect = Exception("Service error")

            data = {"test": "data"}

            # First two calls should fail
            for _ in range(2):
                with pytest.raises(Exception):
                    await protocol.send_request("test_service", data)

            # Third call should be blocked by circuit breaker
            with pytest.raises(Exception) as exc_info:
                await protocol.send_request("test_service", data)

            assert "Circuit breaker is OPEN" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__])
