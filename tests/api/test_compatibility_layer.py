"""
Comprehensive tests for API compatibility layer

This module tests the API compatibility layer for the hybrid CPython/Condon
architecture, including API versioning, backward compatibility, schema validation,
and performance monitoring.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from server.api.compatibility_layer import (
    APICompatibilityLayer,
    APIPerformanceMonitor,
    APISchemaManager,
    APISecurityManager,
    APIVersionConfig,
    APIVersionManager,
    CompatibilityChecker,
    SchemaValidationConfig,
    SchemaValidator,
    create_api_compatibility_layer,
)


class TestAPIVersionManager:
    """Test API versioning functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = APIVersionConfig()
        self.version_manager = APIVersionManager(self.config)

    def test_register_api_version(self):
        """Test API version registration"""
        service = "test_service"
        version = "v1"
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        self.version_manager.register_api_version(service, version, schema)

        assert service in self.version_manager.version_registry
        assert version in self.version_manager.version_registry[service]
        assert (
            self.version_manager.version_registry[service][version]["schema"] == schema
        )

    def test_check_backward_compatibility(self):
        """Test backward compatibility checking"""
        service = "test_service"
        old_version = "v1"
        new_version = "v2"

        # Register both versions
        old_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        new_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        self.version_manager.register_api_version(service, old_version, old_schema)
        self.version_manager.register_api_version(service, new_version, new_schema)

        # Test backward compatibility
        result = self.version_manager.check_backward_compatibility(
            service, old_version, new_version
        )
        assert result is True

    def test_migrate_request(self):
        """Test request migration between versions"""
        request = {"name": "test", "data": "value"}
        from_version = "v1"
        to_version = "v2"
        service = "test_service"

        result = self.version_manager.migrate_request(
            request, from_version, to_version, service
        )
        assert result == request  # Default migration is pass-through

    def test_get_version_from_request_uri_path(self):
        """Test version extraction from URI path"""
        self.config.strategy = APIVersionConfig.strategy.__class__.URI_PATH

        request = {"path": "/v2/api/users"}
        service = "test_service"

        version = self.version_manager.get_version_from_request(request, service)
        assert version == "v2"

    def test_get_version_from_request_header(self):
        """Test version extraction from header"""
        self.config.strategy = APIVersionConfig.strategy.__class__.HEADER_BASED

        request = {"headers": {"API-Version": "v3"}}
        service = "test_service"

        version = self.version_manager.get_version_from_request(request, service)
        assert version == "v3"

    def test_get_version_from_request_query_param(self):
        """Test version extraction from query parameter"""
        self.config.strategy = APIVersionConfig.strategy.__class__.QUERY_PARAM

        request = {"query_params": {"version": "v4"}}
        service = "test_service"

        version = self.version_manager.get_version_from_request(request, service)
        assert version == "v4"


class TestSchemaValidator:
    """Test schema validation functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.config = SchemaValidationConfig()
        self.validator = SchemaValidator(self.config)

    def test_validate_request_schema_success(self):
        """Test successful request schema validation"""
        service = "test_service"
        version = "v1"
        request = {"name": "test"}

        # Mock schema loading
        with patch.object(self.validator, "_get_schema", return_value=None):
            result = self.validator.validate_request_schema(service, version, request)
            assert result is True

    def test_validate_response_schema_success(self):
        """Test successful response schema validation"""
        service = "test_service"
        version = "v1"
        response = {"status": "success", "data": "test"}

        # Mock schema loading
        with patch.object(self.validator, "_get_response_schema", return_value=None):
            result = self.validator.validate_response_schema(service, version, response)
            assert result is True

    def test_generate_schema_documentation(self):
        """Test schema documentation generation"""
        service = "test_service"
        version = "v1"

        # Mock schema loading
        with patch.object(self.validator, "_get_schema", return_value=None):
            result = self.validator.generate_schema_documentation(service, version)
            assert isinstance(result, dict)
            assert result["service"] == service
            assert result["version"] == version


class TestCompatibilityChecker:
    """Test compatibility checking functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.checker = CompatibilityChecker()

    def test_check_cpython_condon_compatibility(self):
        """Test CPython/Condon compatibility checking"""
        cpython_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        condon_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = self.checker.check_cpython_condon_compatibility(
            cpython_schema, condon_schema
        )
        assert result is True

    def test_generate_compatibility_layer(self):
        """Test compatibility layer generation"""
        cpython_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        condon_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = self.checker.generate_compatibility_layer(
            cpython_schema, condon_schema
        )

        assert isinstance(result, dict)
        assert "type_mappings" in result
        assert "conversion_rules" in result
        assert "validation_rules" in result


class TestAPIPerformanceMonitor:
    """Test API performance monitoring"""

    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = APIPerformanceMonitor()

    @pytest.mark.asyncio
    async def test_monitor_api_performance(self):
        """Test API performance monitoring"""
        service = "test_service"
        endpoint = "/api/users"
        duration = 0.1
        success = True

        await self.monitor.monitor_api_performance(service, endpoint, duration, success)

        # Check that metrics were recorded
        metrics = await self.monitor.metrics_collector.get_metrics(service)
        assert service in self.monitor.metrics_collector.metrics_store
        assert endpoint in self.monitor.metrics_collector.metrics_store[service]

    @pytest.mark.asyncio
    async def test_analyze_performance_trends(self):
        """Test performance trend analysis"""
        service = "test_service"

        result = await self.monitor.analyze_performance_trends(service)

        assert isinstance(result, dict)
        assert result["service"] == service
        assert "trend" in result

    @pytest.mark.asyncio
    async def test_generate_performance_report(self):
        """Test performance report generation"""
        service = "test_service"

        result = await self.monitor.generate_performance_report(service)

        assert isinstance(result, dict)
        assert result["service"] == service
        assert "metrics" in result
        assert "trends" in result
        assert "alerts" in result


class TestAPISecurityManager:
    """Test API security functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.secret_key = "test-secret-key"
        self.security_manager = APISecurityManager(self.secret_key)

    @pytest.mark.asyncio
    async def test_authenticate_api_request_success(self):
        """Test successful API authentication"""
        # Mock JWT token
        with patch("jwt.decode", return_value={"user": "test"}):
            request = {"headers": {"Authorization": "Bearer valid-token"}}
            result = await self.security_manager.authenticate_api_request(request)
            assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_api_request_failure(self):
        """Test failed API authentication"""
        request = {"headers": {}}  # No authorization header
        result = await self.security_manager.authenticate_api_request(request)
        assert result is False

    @pytest.mark.asyncio
    async def test_authorize_api_request(self):
        """Test API authorization"""
        request = {"path": "/api/users", "method": "GET"}
        user = "test_user"

        result = await self.security_manager.authorize_api_request(request, user)
        assert result is True  # Simplified authorization always returns True

    @pytest.mark.asyncio
    async def test_validate_api_input(self):
        """Test API input validation"""
        request = {"data": "test"}

        result = await self.security_manager.validate_api_input(request)
        assert result is True  # Simplified validation always returns True

    @pytest.mark.asyncio
    async def test_sanitize_api_output(self):
        """Test API output sanitization"""
        response = {"data": "test", "sensitive": "value"}

        result = await self.security_manager.sanitize_api_output(response)
        assert result == response  # Simplified sanitization returns original


class TestAPISchemaManager:
    """Test API schema management"""

    def setup_method(self):
        """Set up test fixtures"""
        self.schema_manager = APISchemaManager()

    def test_register_schema(self):
        """Test schema registration"""
        service = "test_service"
        version = "v1"
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        self.schema_manager.register_schema(service, version, schema)

        assert service in self.schema_manager.schema_registry
        assert version in self.schema_manager.schema_registry[service]
        assert self.schema_manager.schema_registry[service][version]["schema"] == schema

    def test_generate_documentation(self):
        """Test documentation generation"""
        service = "test_service"
        version = "v1"

        result = self.schema_manager.generate_documentation(service, version)

        assert isinstance(result, dict)
        assert "openapi" in result
        assert "markdown" in result
        assert "examples" in result

    def test_validate_schema_compatibility(self):
        """Test schema compatibility validation"""
        schema_a = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema_b = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = self.schema_manager.validate_schema_compatibility(schema_a, schema_b)
        assert result is True


class TestAPICompatibilityLayer:
    """Test main API compatibility layer"""

    def setup_method(self):
        """Set up test fixtures"""
        self.version_config = APIVersionConfig()
        self.schema_config = SchemaValidationConfig()
        self.compatibility_layer = APICompatibilityLayer(
            self.version_config, self.schema_config
        )

    @pytest.mark.asyncio
    async def test_route_request_success(self):
        """Test successful request routing"""
        service = "test_service"
        api_version = "v1"
        request = {
            "path": "/api/users",
            "method": "GET",
            "headers": {"Authorization": "Bearer valid-token"},
            "data": {"name": "test"},
        }

        # Mock authentication and validation
        with patch.object(
            self.compatibility_layer.security_manager,
            "authenticate_api_request",
            return_value=True,
        ), patch.object(
            self.compatibility_layer.security_manager,
            "validate_api_input",
            return_value=True,
        ), patch.object(
            self.compatibility_layer.schema_validator,
            "validate_request_schema",
            return_value=True,
        ), patch.object(
            self.compatibility_layer.schema_validator,
            "validate_response_schema",
            return_value=True,
        ), patch.object(
            self.compatibility_layer.security_manager,
            "sanitize_api_output",
            return_value={"status": "success"},
        ):

            result = await self.compatibility_layer.route_request(
                service, api_version, request
            )

            assert isinstance(result, dict)
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_route_request_authentication_failure(self):
        """Test request routing with authentication failure"""
        service = "test_service"
        api_version = "v1"
        request = {
            "path": "/api/users",
            "method": "GET",
            "headers": {},
            "data": {"name": "test"},
        }

        # Mock authentication failure
        with patch.object(
            self.compatibility_layer.security_manager,
            "authenticate_api_request",
            return_value=False,
        ):
            with pytest.raises(ValueError, match="Authentication failed"):
                await self.compatibility_layer.route_request(
                    service, api_version, request
                )

    @pytest.mark.asyncio
    async def test_validate_compatibility_success(self):
        """Test successful compatibility validation"""
        service = "test_service"
        api_version = "v1"

        # Register service and version
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        self.compatibility_layer.version_manager.register_api_version(
            service, api_version, schema
        )

        result = await self.compatibility_layer.validate_compatibility(
            service, api_version
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_compatibility_failure(self):
        """Test failed compatibility validation"""
        service = "unknown_service"
        api_version = "v1"

        result = await self.compatibility_layer.validate_compatibility(
            service, api_version
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_version_migration_success(self):
        """Test successful version migration"""
        service = "test_service"
        old_version = "v1"
        new_version = "v2"

        # Register both versions
        old_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        new_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        self.compatibility_layer.version_manager.register_api_version(
            service, old_version, old_schema
        )
        self.compatibility_layer.version_manager.register_api_version(
            service, new_version, new_schema
        )

        result = await self.compatibility_layer.handle_version_migration(
            old_version, new_version, service
        )

        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["migration"] == f"{old_version} -> {new_version}"

    @pytest.mark.asyncio
    async def test_handle_version_migration_failure(self):
        """Test failed version migration"""
        service = "test_service"
        old_version = "v1"
        new_version = "v2"

        # Don't register versions to cause failure
        result = await self.compatibility_layer.handle_version_migration(
            old_version, new_version, service
        )

        assert isinstance(result, dict)
        assert result["status"] == "error"


class TestFactoryFunction:
    """Test factory function for creating API compatibility layers"""

    def test_create_api_compatibility_layer_default(self):
        """Test creating API compatibility layer with default configuration"""
        layer = create_api_compatibility_layer()

        assert isinstance(layer, APICompatibilityLayer)
        assert isinstance(layer.version_config, APIVersionConfig)
        assert isinstance(layer.schema_config, SchemaValidationConfig)

    def test_create_api_compatibility_layer_custom(self):
        """Test creating API compatibility layer with custom configuration"""
        version_config = APIVersionConfig(default_version="v2")
        schema_config = SchemaValidationConfig(enable_request_validation=False)

        layer = create_api_compatibility_layer(version_config, schema_config)

        assert isinstance(layer, APICompatibilityLayer)
        assert layer.version_config.default_version == "v2"
        assert layer.schema_config.enable_request_validation is False


class TestIntegration:
    """Integration tests for API compatibility layer"""

    @pytest.mark.asyncio
    async def test_cpython_condon_integration(self):
        """Test CPython/Condon API integration"""
        # Create compatibility layer
        layer = create_api_compatibility_layer()

        # Register CPython and Condon schemas
        cpython_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        condon_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        layer.version_manager.register_api_version(
            "cpython_service", "v1", cpython_schema
        )
        layer.version_manager.register_api_version(
            "condon_service", "v1", condon_schema
        )

        # Test compatibility
        compatibility = layer.compatibility_checker.check_cpython_condon_compatibility(
            cpython_schema, condon_schema
        )
        assert compatibility is True

        # Test request routing
        request = {
            "path": "/api/users",
            "method": "GET",
            "headers": {"Authorization": "Bearer valid-token"},
            "data": {"name": "test"},
        }

        with patch.object(
            layer.security_manager, "authenticate_api_request", return_value=True
        ), patch.object(
            layer.security_manager, "validate_api_input", return_value=True
        ), patch.object(
            layer.schema_validator, "validate_request_schema", return_value=True
        ), patch.object(
            layer.schema_validator, "validate_response_schema", return_value=True
        ), patch.object(
            layer.security_manager,
            "sanitize_api_output",
            return_value={"status": "success"},
        ):

            result = await layer.route_request("cpython_service", "v1", request)
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_api_migration(self):
        """Test API migration between versions"""
        layer = create_api_compatibility_layer()

        # Register multiple versions
        v1_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        v2_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }

        layer.version_manager.register_api_version("test_service", "v1", v1_schema)
        layer.version_manager.register_api_version("test_service", "v2", v2_schema)

        # Test migration
        result = await layer.handle_version_migration("v1", "v2", "test_service")
        assert result["status"] == "success"

        # Test backward compatibility
        compatibility = layer.version_manager.check_backward_compatibility(
            "test_service", "v1", "v2"
        )
        assert compatibility is True


if __name__ == "__main__":
    pytest.main([__file__])
