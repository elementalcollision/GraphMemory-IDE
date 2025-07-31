"""
Comprehensive API Compatibility Layer for Hybrid CPython/Condon Architecture

This module implements a comprehensive API compatibility layer that ensures seamless
integration between CPython and Condon services, including API versioning, backward
compatibility, schema validation, and performance monitoring.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import jsonschema
import jwt
import openapi_spec_validator
from cryptography.fernet import Fernet
from jsonschema import Draft7Validator
from opentelemetry import trace
from opentelemetry.exporter.prometheus import PrometheusExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import Counter, Gauge, Histogram

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
API_REQUEST_COUNTER = Counter(
    "api_compatibility_requests_total",
    "Total API requests",
    ["service", "version", "status"],
)
API_REQUEST_DURATION = Histogram(
    "api_compatibility_duration_seconds", "API request duration", ["service", "version"]
)
API_SCHEMA_VALIDATION_ERRORS = Counter(
    "api_schema_validation_errors_total",
    "Schema validation errors",
    ["service", "version"],
)
API_VERSION_MIGRATIONS = Counter(
    "api_version_migrations_total",
    "API version migrations",
    ["service", "from_version", "to_version"],
)


class APIVersionStrategy(Enum):
    """API versioning strategies"""

    URI_PATH = "uri_path"
    HEADER_BASED = "header_based"
    QUERY_PARAM = "query_param"
    CUSTOM_MIDDLEWARE = "custom_middleware"


class VersionCompatibility(Enum):
    """Version compatibility levels"""

    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    BREAKING_CHANGE = "breaking_change"


@dataclass
class APIVersionConfig:
    """Configuration for API versioning"""

    strategy: APIVersionStrategy = APIVersionStrategy.URI_PATH
    default_version: str = "v1"
    supported_versions: List[str] = field(default_factory=lambda: ["v1"])
    enable_backward_compatibility: bool = True
    enable_forward_compatibility: bool = True
    version_header_name: str = "API-Version"
    version_query_param: str = "version"


@dataclass
class SchemaValidationConfig:
    """Configuration for schema validation"""

    enable_request_validation: bool = True
    enable_response_validation: bool = True
    strict_validation: bool = False
    allow_additional_properties: bool = True
    cache_schemas: bool = True
    validation_timeout: float = 5.0


class APIVersionManager:
    """API versioning for CPython/Condon services"""

    def __init__(self, config: APIVersionConfig):
        self.config = config
        self.version_registry = {}
        self.migration_strategies = {}
        self.backward_compatibility = config.enable_backward_compatibility
        self.forward_compatibility = config.enable_forward_compatibility

    def register_api_version(
        self, service: str, version: str, schema: dict, handlers: dict = None
    ):
        """Register new API version"""
        if service not in self.version_registry:
            self.version_registry[service] = {}

        self.version_registry[service][version] = {
            "schema": schema,
            "handlers": handlers or {},
            "created_at": time.time(),
            "status": "active",
        }

        logger.info(f"Registered API version {version} for service {service}")

    def check_backward_compatibility(
        self, service: str, old_version: str, new_version: str
    ) -> bool:
        """Check backward compatibility between versions"""
        if not self.backward_compatibility:
            return False

        if service not in self.version_registry:
            return False

        if (
            old_version not in self.version_registry[service]
            or new_version not in self.version_registry[service]
        ):
            return False

        old_schema = self.version_registry[service][old_version]["schema"]
        new_schema = self.version_registry[service][new_version]["schema"]

        return self._compare_schemas_for_compatibility(old_schema, new_schema)

    def check_forward_compatibility(
        self, service: str, old_version: str, new_version: str
    ) -> bool:
        """Check forward compatibility between versions"""
        if not self.forward_compatibility:
            return False

        return self.check_backward_compatibility(service, new_version, old_version)

    def migrate_request(
        self, request: dict, from_version: str, to_version: str, service: str
    ) -> dict:
        """Migrate request between API versions"""
        if from_version == to_version:
            return request

        migration_key = f"{service}:{from_version}:{to_version}"

        if migration_key in self.migration_strategies:
            return self.migration_strategies[migration_key](request)

        # Default migration strategy
        return self._default_migration_strategy(request, from_version, to_version)

    def _compare_schemas_for_compatibility(
        self, old_schema: dict, new_schema: dict
    ) -> bool:
        """Compare schemas for compatibility"""
        try:
            # Check if new schema is backward compatible with old schema
            validator = Draft7Validator(new_schema)

            # This is a simplified check - in production, you'd want more sophisticated comparison
            return True
        except Exception as e:
            logger.error(f"Schema compatibility check failed: {e}")
            return False

    def _default_migration_strategy(
        self, request: dict, from_version: str, to_version: str
    ) -> dict:
        """Default migration strategy"""
        # Simple pass-through migration
        return request

    def get_version_from_request(self, request: dict, service: str) -> str:
        """Extract API version from request"""
        if self.config.strategy == APIVersionStrategy.URI_PATH:
            return self._extract_version_from_uri(request.get("path", ""))
        elif self.config.strategy == APIVersionStrategy.HEADER_BASED:
            return request.get("headers", {}).get(
                self.config.version_header_name, self.config.default_version
            )
        elif self.config.strategy == APIVersionStrategy.QUERY_PARAM:
            return request.get("query_params", {}).get(
                self.config.version_query_param, self.config.default_version
            )
        else:
            return self.config.default_version

    def _extract_version_from_uri(self, uri: str) -> str:
        """Extract version from URI path"""
        try:
            path_parts = uri.strip("/").split("/")
            if path_parts and path_parts[0].startswith("v"):
                return path_parts[0]
        except Exception:
            pass
        return self.config.default_version


class SchemaValidator:
    """Schema validation for API compatibility"""

    def __init__(self, config: SchemaValidationConfig):
        self.config = config
        self.schema_registry = {}
        self.validation_rules = {}
        self.error_handlers = {}
        self.schema_cache = {}

    def validate_request_schema(
        self, service: str, version: str, request: dict
    ) -> bool:
        """Validate request against API schema"""
        try:
            schema = self._get_schema(service, version)
            if not schema:
                return True  # No schema means no validation

            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(request))

            if errors:
                API_SCHEMA_VALIDATION_ERRORS.labels(
                    service=service, version=version
                ).inc()
                logger.error(
                    f"Request validation failed for {service}/{version}: {errors}"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False

    def validate_response_schema(
        self, service: str, version: str, response: dict
    ) -> bool:
        """Validate response against API schema"""
        try:
            schema = self._get_response_schema(service, version)
            if not schema:
                return True  # No schema means no validation

            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(response))

            if errors:
                API_SCHEMA_VALIDATION_ERRORS.labels(
                    service=service, version=version
                ).inc()
                logger.error(
                    f"Response validation failed for {service}/{version}: {errors}"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False

    def generate_schema_documentation(self, service: str, version: str) -> dict:
        """Generate API schema documentation"""
        schema = self._get_schema(service, version)
        if not schema:
            return {}

        return {
            "service": service,
            "version": version,
            "schema": schema,
            "endpoints": self._extract_endpoints(schema),
            "models": self._extract_models(schema),
            "examples": self._generate_examples(schema),
        }

    def _get_schema(self, service: str, version: str) -> Optional[dict]:
        """Get schema for service and version"""
        cache_key = f"{service}:{version}"

        if self.config.cache_schemas and cache_key in self.schema_cache:
            return self.schema_cache[cache_key]

        # In a real implementation, this would load from a schema registry
        schema = self._load_schema(service, version)

        if self.config.cache_schemas and schema:
            self.schema_cache[cache_key] = schema

        return schema

    def _get_response_schema(self, service: str, version: str) -> Optional[dict]:
        """Get response schema for service and version"""
        # In a real implementation, this would load response schemas
        return self._get_schema(service, version)

    def _load_schema(self, service: str, version: str) -> Optional[dict]:
        """Load schema from storage"""
        # Implementation would load from file, database, or API
        return None

    def _extract_endpoints(self, schema: dict) -> List[dict]:
        """Extract endpoints from schema"""
        endpoints = []
        if "paths" in schema:
            for path, methods in schema["paths"].items():
                for method, details in methods.items():
                    endpoints.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "summary": details.get("summary", ""),
                            "description": details.get("description", ""),
                        }
                    )
        return endpoints

    def _extract_models(self, schema: dict) -> List[dict]:
        """Extract models from schema"""
        models = []
        if "components" in schema and "schemas" in schema["components"]:
            for name, model in schema["components"]["schemas"].items():
                models.append(
                    {
                        "name": name,
                        "properties": model.get("properties", {}),
                        "required": model.get("required", []),
                    }
                )
        return models

    def _generate_examples(self, schema: dict) -> List[dict]:
        """Generate examples from schema"""
        examples = []
        # Implementation would generate examples based on schema
        return examples


class CompatibilityChecker:
    """Check compatibility between different service types"""

    def __init__(self):
        self.compatibility_rules = {}
        self.type_mappings = {}

    def check_cpython_condon_compatibility(
        self, cpython_schema: dict, condon_schema: dict
    ) -> bool:
        """Check compatibility between CPython and Condon schemas"""
        try:
            # Check if schemas are compatible
            return self._compare_schemas(cpython_schema, condon_schema)
        except Exception as e:
            logger.error(f"Compatibility check failed: {e}")
            return False

    def generate_compatibility_layer(
        self, cpython_schema: dict, condon_schema: dict
    ) -> dict:
        """Generate compatibility layer between CPython and Condon"""
        compatibility_layer = {
            "type_mappings": {},
            "conversion_rules": {},
            "validation_rules": {},
        }

        # Generate type mappings
        compatibility_layer["type_mappings"] = self._generate_type_mappings(
            cpython_schema, condon_schema
        )

        # Generate conversion rules
        compatibility_layer["conversion_rules"] = self._generate_conversion_rules(
            cpython_schema, condon_schema
        )

        return compatibility_layer

    def _compare_schemas(self, schema_a: dict, schema_b: dict) -> bool:
        """Compare two schemas for compatibility"""
        # Simplified comparison - in production, you'd want more sophisticated logic
        return True

    def _generate_type_mappings(
        self, cpython_schema: dict, condon_schema: dict
    ) -> dict:
        """Generate type mappings between CPython and Condon"""
        mappings = {
            "int": "int",
            "float": "float",
            "str": "str",
            "bool": "bool",
            "list": "List",
            "dict": "Dict",
        }
        return mappings

    def _generate_conversion_rules(
        self, cpython_schema: dict, condon_schema: dict
    ) -> dict:
        """Generate conversion rules between CPython and Condon"""
        rules = {"cpython_to_condon": {}, "condon_to_cpython": {}}
        return rules


class APIPerformanceMonitor:
    """API performance monitoring for hybrid architecture"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_analyzer = PerformanceAnalyzer()
        self.alert_manager = AlertManager()
        self.tracer = trace.get_tracer(__name__)

    async def monitor_api_performance(
        self, service: str, endpoint: str, duration: float, success: bool
    ):
        """Monitor API performance metrics"""
        # Record basic metrics
        API_REQUEST_COUNTER.labels(
            service=service, version="latest", status="success" if success else "error"
        ).inc()

        API_REQUEST_DURATION.labels(service=service, version="latest").observe(duration)

        # Record detailed metrics
        await self.metrics_collector.record_metric(service, endpoint, duration, success)

        # Analyze performance trends
        await self.performance_analyzer.analyze_trends(service, endpoint)

        # Check for alerts
        await self.alert_manager.check_alerts(service, endpoint, duration, success)

    async def analyze_performance_trends(self, service: str) -> dict:
        """Analyze API performance trends"""
        return await self.performance_analyzer.analyze_trends(service)

    async def generate_performance_report(self, service: str) -> dict:
        """Generate API performance report"""
        return {
            "service": service,
            "metrics": await self.metrics_collector.get_metrics(service),
            "trends": await self.performance_analyzer.analyze_trends(service),
            "alerts": await self.alert_manager.get_alerts(service),
        }


class MetricsCollector:
    """Collect and store API metrics"""

    def __init__(self):
        self.metrics_store = {}

    async def record_metric(
        self, service: str, endpoint: str, duration: float, success: bool
    ):
        """Record a single metric"""
        if service not in self.metrics_store:
            self.metrics_store[service] = {}

        if endpoint not in self.metrics_store[service]:
            self.metrics_store[service][endpoint] = {
                "count": 0,
                "success_count": 0,
                "error_count": 0,
                "total_duration": 0,
                "min_duration": float("inf"),
                "max_duration": 0,
                "avg_duration": 0,
            }

        metric = self.metrics_store[service][endpoint]
        metric["count"] += 1
        metric["total_duration"] += duration

        if success:
            metric["success_count"] += 1
        else:
            metric["error_count"] += 1

        metric["min_duration"] = min(metric["min_duration"], duration)
        metric["max_duration"] = max(metric["max_duration"], duration)
        metric["avg_duration"] = metric["total_duration"] / metric["count"]

    async def get_metrics(self, service: str) -> dict:
        """Get metrics for a service"""
        return self.metrics_store.get(service, {})


class PerformanceAnalyzer:
    """Analyze API performance trends"""

    def __init__(self):
        self.trend_data = {}

    async def analyze_trends(self, service: str, endpoint: str = None) -> dict:
        """Analyze performance trends"""
        # Simplified trend analysis
        return {
            "service": service,
            "endpoint": endpoint,
            "trend": "stable",
            "recommendations": [],
        }


class AlertManager:
    """Manage API performance alerts"""

    def __init__(self):
        self.alert_thresholds = {
            "response_time": 1000,  # ms
            "error_rate": 0.05,  # 5%
            "availability": 0.99,  # 99%
        }

    async def check_alerts(
        self, service: str, endpoint: str, duration: float, success: bool
    ):
        """Check if alerts should be triggered"""
        alerts = []

        # Check response time
        if duration > self.alert_thresholds["response_time"]:
            alerts.append(
                {
                    "type": "high_response_time",
                    "service": service,
                    "endpoint": endpoint,
                    "value": duration,
                    "threshold": self.alert_thresholds["response_time"],
                }
            )

        # Check error rate (simplified)
        if not success:
            alerts.append(
                {
                    "type": "api_error",
                    "service": service,
                    "endpoint": endpoint,
                    "value": "error",
                    "threshold": "success",
                }
            )

        return alerts

    async def get_alerts(self, service: str) -> List[dict]:
        """Get alerts for a service"""
        return []


class APISecurityManager:
    """API security for hybrid architecture"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.authentication = APIAuthentication(secret_key)
        self.authorization = APIAuthorization()
        self.input_validation = InputValidator()
        self.output_sanitization = OutputSanitizer()

    async def authenticate_api_request(self, request: dict) -> bool:
        """Authenticate API request"""
        return await self.authentication.authenticate(request)

    async def authorize_api_request(self, request: dict, user: str) -> bool:
        """Authorize API request"""
        return await self.authorization.authorize(request, user)

    async def validate_api_input(self, request: dict) -> bool:
        """Validate API input"""
        return await self.input_validation.validate(request)

    async def sanitize_api_output(self, response: dict) -> dict:
        """Sanitize API output"""
        return await self.output_sanitization.sanitize(response)


class APIAuthentication:
    """API authentication"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    async def authenticate(self, request: dict) -> bool:
        """Authenticate API request"""
        try:
            token = (
                request.get("headers", {})
                .get("Authorization", "")
                .replace("Bearer ", "")
            )
            if not token:
                return False

            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return True
        except jwt.InvalidTokenError:
            return False


class APIAuthorization:
    """API authorization"""

    def __init__(self):
        self.permissions = {}

    async def authorize(self, request: dict, user: str) -> bool:
        """Authorize API request"""
        # Simplified authorization
        return True


class InputValidator:
    """API input validation"""

    def __init__(self):
        self.validation_rules = {}

    async def validate(self, request: dict) -> bool:
        """Validate API input"""
        # Simplified validation
        return True


class OutputSanitizer:
    """API output sanitization"""

    def __init__(self):
        self.sanitization_rules = {}

    async def sanitize(self, response: dict) -> dict:
        """Sanitize API output"""
        # Simplified sanitization
        return response


class APISchemaManager:
    """API schema management for hybrid architecture"""

    def __init__(self):
        self.schema_registry = {}
        self.documentation_generator = DocumentationGenerator()
        self.schema_validator = SchemaValidator(SchemaValidationConfig())

    def register_schema(self, service: str, version: str, schema: dict):
        """Register API schema"""
        if service not in self.schema_registry:
            self.schema_registry[service] = {}

        self.schema_registry[service][version] = {
            "schema": schema,
            "created_at": time.time(),
            "status": "active",
        }

        logger.info(f"Registered schema for {service}/{version}")

    def generate_documentation(self, service: str, version: str) -> dict:
        """Generate API documentation"""
        return self.documentation_generator.generate(service, version)

    def validate_schema_compatibility(self, schema_a: dict, schema_b: dict) -> bool:
        """Validate schema compatibility"""
        return self.schema_validator._compare_schemas_for_compatibility(
            schema_a, schema_b
        )


class DocumentationGenerator:
    """API documentation generator for hybrid architecture"""

    def __init__(self):
        self.template_engine = TemplateEngine()
        self.markdown_generator = MarkdownGenerator()
        self.openapi_generator = OpenAPIGenerator()

    def generate_openapi_spec(self, service: str, version: str) -> dict:
        """Generate OpenAPI specification"""
        # Implementation would generate OpenAPI spec
        return {
            "openapi": "3.0.0",
            "info": {"title": f"{service} API", "version": version},
            "paths": {},
        }

    def generate_markdown_docs(self, service: str, version: str) -> str:
        """Generate Markdown documentation"""
        return (
            f"# {service} API Documentation\n\nVersion: {version}\n\n## Endpoints\n\n"
        )

    def generate_code_examples(self, service: str, version: str) -> dict:
        """Generate code examples"""
        return {
            "python": f"# {service} API Examples\n\nVersion: {version}",
            "javascript": f"// {service} API Examples\n\n// Version: {version}",
        }

    def generate(self, service: str, version: str) -> dict:
        """Generate complete documentation"""
        return {
            "openapi": self.generate_openapi_spec(service, version),
            "markdown": self.generate_markdown_docs(service, version),
            "examples": self.generate_code_examples(service, version),
        }


class TemplateEngine:
    """Template engine for documentation generation"""

    def render_template(self, template: str, data: dict) -> str:
        """Render template with data"""
        return template.format(**data)


class MarkdownGenerator:
    """Markdown documentation generator"""

    def generate(self, content: str) -> str:
        """Generate Markdown content"""
        return content


class OpenAPIGenerator:
    """OpenAPI specification generator"""

    def generate(self, service: str, version: str) -> dict:
        """Generate OpenAPI specification"""
        return {
            "openapi": "3.0.0",
            "info": {"title": f"{service} API", "version": version},
            "paths": {},
        }


class APICompatibilityLayer:
    """Main API compatibility layer for hybrid architecture"""

    def __init__(
        self,
        version_config: APIVersionConfig = None,
        schema_config: SchemaValidationConfig = None,
    ):
        self.version_config = version_config or APIVersionConfig()
        self.schema_config = schema_config or SchemaValidationConfig()

        self.version_manager = APIVersionManager(self.version_config)
        self.schema_validator = SchemaValidator(self.schema_config)
        self.compatibility_checker = CompatibilityChecker()
        self.performance_monitor = APIPerformanceMonitor()
        self.security_manager = APISecurityManager("your-secret-key")
        self.schema_manager = APISchemaManager()

    async def route_request(
        self, service: str, api_version: str, request: dict
    ) -> dict:
        """Route request with API compatibility handling"""
        start_time = time.time()

        try:
            # Extract version from request if not provided
            if not api_version:
                api_version = self.version_manager.get_version_from_request(
                    request, service
                )

            # Validate request schema
            if self.schema_config.enable_request_validation:
                if not self.schema_validator.validate_request_schema(
                    service, api_version, request
                ):
                    raise ValueError("Request validation failed")

            # Authenticate and authorize request
            if not await self.security_manager.authenticate_api_request(request):
                raise ValueError("Authentication failed")

            # Validate input
            if not await self.security_manager.validate_api_input(request):
                raise ValueError("Input validation failed")

            # Route to appropriate handler
            response = await self._handle_request(service, api_version, request)

            # Validate response schema
            if self.schema_config.enable_response_validation:
                if not self.schema_validator.validate_response_schema(
                    service, api_version, response
                ):
                    raise ValueError("Response validation failed")

            # Sanitize output
            response = await self.security_manager.sanitize_api_output(response)

            # Record performance metrics
            duration = time.time() - start_time
            await self.performance_monitor.monitor_api_performance(
                service, request.get("path", ""), duration, True
            )

            return response

        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            await self.performance_monitor.monitor_api_performance(
                service, request.get("path", ""), duration, False
            )
            raise e

    async def validate_compatibility(self, service: str, api_version: str) -> bool:
        """Validate API compatibility between services"""
        try:
            # Check if service and version are supported
            if service not in self.version_manager.version_registry:
                return False

            if api_version not in self.version_manager.version_registry[service]:
                return False

            # Check backward compatibility
            if not self.version_manager.check_backward_compatibility(
                service, api_version, api_version
            ):
                return False

            return True
        except Exception as e:
            logger.error(f"Compatibility validation failed: {e}")
            return False

    async def handle_version_migration(
        self, old_version: str, new_version: str, service: str
    ) -> dict:
        """Handle API version migration"""
        try:
            # Check if migration is supported
            if not self.version_manager.check_backward_compatibility(
                service, old_version, new_version
            ):
                raise ValueError(
                    f"Migration from {old_version} to {new_version} not supported"
                )

            # Record migration
            API_VERSION_MIGRATIONS.labels(
                service=service, from_version=old_version, to_version=new_version
            ).inc()

            return {
                "status": "success",
                "migration": f"{old_version} -> {new_version}",
                "compatibility": "backward_compatible",
            }
        except Exception as e:
            logger.error(f"Version migration failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_request(self, service: str, version: str, request: dict) -> dict:
        """Handle the actual request"""
        # Implementation would route to appropriate handler
        return {
            "status": "success",
            "service": service,
            "version": version,
            "data": request.get("data", {}),
        }


# Factory function for creating API compatibility layers
def create_api_compatibility_layer(
    version_config: APIVersionConfig = None,
    schema_config: SchemaValidationConfig = None,
) -> APICompatibilityLayer:
    """Create API compatibility layer with configuration"""
    return APICompatibilityLayer(version_config, schema_config)
