# API Compatibility Layer

## Overview

This document describes the comprehensive API compatibility layer designed for the hybrid CPython/Codon architecture. The layer provides seamless integration between CPython and Codon services, including API versioning, backward compatibility, schema validation, and performance monitoring for production deployment.

## Architecture

The API compatibility layer consists of several key components:

### Core Components

1. **APICompatibilityLayer** - Main orchestrator for API compatibility
2. **APIVersionManager** - Handles API versioning and backward compatibility
3. **SchemaValidator** - Validates API requests and responses against schemas
4. **CompatibilityChecker** - Checks compatibility between CPython and Codon services
5. **APIPerformanceMonitor** - Monitors API performance and generates reports
6. **APISecurityManager** - Handles authentication, authorization, and security
7. **APISchemaManager** - Manages API schemas and documentation

## API Versioning

### Versioning Strategies

The API compatibility layer supports multiple versioning strategies:

#### 1. URI Path Versioning
```python
# Example: /v1/api/users, /v2/api/users
config = APIVersionConfig(strategy=APIVersionStrategy.URI_PATH)
```

#### 2. Header-Based Versioning
```python
# Example: API-Version: v1
config = APIVersionConfig(strategy=APIVersionStrategy.HEADER_BASED)
```

#### 3. Query Parameter Versioning
```python
# Example: ?version=v1
config = APIVersionConfig(strategy=APIVersionStrategy.QUERY_PARAM)
```

#### 4. Custom Middleware Versioning
```python
# Example: Custom logic for version detection
config = APIVersionConfig(strategy=APIVersionStrategy.CUSTOM_MIDDLEWARE)
```

### Semantic Versioning

The layer supports semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (1.X.0): New features (backward compatible)
- **PATCH** (1.0.X): Bug fixes (backward compatible)

### Backward Compatibility

```python
# Check backward compatibility
compatibility = version_manager.check_backward_compatibility(
    service="user_service", 
    old_version="v1", 
    new_version="v2"
)

# Migrate requests between versions
migrated_request = version_manager.migrate_request(
    request=original_request,
    from_version="v1",
    to_version="v2",
    service="user_service"
)
```

## Schema Validation

### Request Validation

```python
# Configure schema validation
config = SchemaValidationConfig(
    enable_request_validation=True,
    enable_response_validation=True,
    strict_validation=False,
    cache_schemas=True
)

# Validate request against schema
is_valid = schema_validator.validate_request_schema(
    service="user_service",
    version="v1",
    request=request_data
)
```

### Response Validation

```python
# Validate response against schema
is_valid = schema_validator.validate_response_schema(
    service="user_service",
    version="v1",
    response=response_data
)
```

### Schema Documentation

```python
# Generate schema documentation
docs = schema_validator.generate_schema_documentation(
    service="user_service",
    version="v1"
)
```

## CPython/Codon Compatibility

### Compatibility Checking

```python
# Check compatibility between CPython and Codon schemas
compatibility = checker.check_cpython_codon_compatibility(
    cpython_schema=cpython_api_schema,
    codon_schema=codon_api_schema
)
```

### Compatibility Layer Generation

```python
# Generate compatibility layer
layer = checker.generate_compatibility_layer(
    cpython_schema=cpython_api_schema,
    codon_schema=codon_api_schema
)

# Layer contains:
# - type_mappings: Type conversions between CPython and Codon
# - conversion_rules: Data conversion rules
# - validation_rules: Validation rules for both environments
```

## Performance Monitoring

### Metrics Collection

The API compatibility layer automatically collects performance metrics:

- **Request Count**: Total API requests by service and version
- **Request Duration**: Response time histograms
- **Schema Validation Errors**: Validation failure counts
- **Version Migrations**: Migration counts between versions

### Performance Analysis

```python
# Monitor API performance
await performance_monitor.monitor_api_performance(
    service="user_service",
    endpoint="/api/users",
    duration=0.15,
    success=True
)

# Analyze performance trends
trends = await performance_monitor.analyze_performance_trends("user_service")

# Generate performance report
report = await performance_monitor.generate_performance_report("user_service")
```

### Alert Management

The system automatically monitors for:

- **High Response Time**: Requests exceeding threshold (default: 1000ms)
- **High Error Rate**: Error rates exceeding threshold (default: 5%)
- **Low Availability**: Availability below threshold (default: 99%)

## Security

### Authentication

```python
# Configure security manager
security_manager = APISecurityManager(secret_key="your-secret-key")

# Authenticate API request
is_authenticated = await security_manager.authenticate_api_request(request)

# Authorize API request
is_authorized = await security_manager.authorize_api_request(request, user)
```

### Input Validation

```python
# Validate API input
is_valid = await security_manager.validate_api_input(request)

# Sanitize API output
sanitized_response = await security_manager.sanitize_api_output(response)
```

## Usage Examples

### Basic Usage

```python
from server.api.compatibility_layer import create_api_compatibility_layer

# Create compatibility layer with default configuration
layer = create_api_compatibility_layer()

# Route request with compatibility handling
response = await layer.route_request(
    service="user_service",
    api_version="v1",
    request={
        "path": "/api/users",
        "method": "GET",
        "headers": {"Authorization": "Bearer token"},
        "data": {"name": "test"}
    }
)
```

### Custom Configuration

```python
from server.api.compatibility_layer import (
    create_api_compatibility_layer,
    APIVersionConfig,
    SchemaValidationConfig
)

# Create custom configuration
version_config = APIVersionConfig(
    strategy=APIVersionStrategy.HEADER_BASED,
    default_version="v2",
    supported_versions=["v1", "v2", "v3"],
    enable_backward_compatibility=True
)

schema_config = SchemaValidationConfig(
    enable_request_validation=True,
    enable_response_validation=True,
    strict_validation=False,
    cache_schemas=True
)

# Create compatibility layer with custom configuration
layer = create_api_compatibility_layer(version_config, schema_config)
```

### Version Migration

```python
# Handle version migration
migration_result = await layer.handle_version_migration(
    old_version="v1",
    new_version="v2",
    service="user_service"
)

# Check compatibility
is_compatible = await layer.validate_compatibility(
    service="user_service",
    api_version="v2"
)
```

## Configuration

### APIVersionConfig

```python
@dataclass
class APIVersionConfig:
    strategy: APIVersionStrategy = APIVersionStrategy.URI_PATH
    default_version: str = "v1"
    supported_versions: List[str] = field(default_factory=lambda: ["v1"])
    enable_backward_compatibility: bool = True
    enable_forward_compatibility: bool = True
    version_header_name: str = "API-Version"
    version_query_param: str = "version"
```

### SchemaValidationConfig

```python
@dataclass
class SchemaValidationConfig:
    enable_request_validation: bool = True
    enable_response_validation: bool = True
    strict_validation: bool = False
    allow_additional_properties: bool = True
    cache_schemas: bool = True
    validation_timeout: float = 5.0
```

## Testing

### Unit Tests

```python
# Test API versioning
def test_api_versioning():
    version_manager = APIVersionManager(APIVersionConfig())
    version_manager.register_api_version("service", "v1", schema)
    assert version_manager.check_backward_compatibility("service", "v1", "v2")

# Test schema validation
def test_schema_validation():
    validator = SchemaValidator(SchemaValidationConfig())
    assert validator.validate_request_schema("service", "v1", request)

# Test compatibility checking
def test_compatibility_checking():
    checker = CompatibilityChecker()
    assert checker.check_cpython_codon_compatibility(schema_a, schema_b)
```

### Integration Tests

```python
# Test CPython/Codon integration
async def test_cpython_codon_integration():
    layer = create_api_compatibility_layer()
    
    # Register schemas
    layer.version_manager.register_api_version("cpython", "v1", cpython_schema)
    layer.version_manager.register_api_version("codon", "v1", codon_schema)
    
    # Test compatibility
    compatibility = layer.compatibility_checker.check_cpython_codon_compatibility(
        cpython_schema, codon_schema
    )
    assert compatibility is True
    
    # Test request routing
    response = await layer.route_request("cpython", "v1", request)
    assert response['status'] == 'success'
```

## Best Practices

### 1. Version Management

- Use semantic versioning for clear communication
- Maintain backward compatibility for at least one major version
- Provide migration guides for breaking changes
- Deprecate old versions with sufficient notice

### 2. Schema Design

- Design schemas with extensibility in mind
- Use additive changes instead of breaking changes
- Document all schema changes
- Validate schemas against real-world data

### 3. Performance Optimization

- Cache schemas for better performance
- Use async operations for I/O-bound tasks
- Monitor performance metrics continuously
- Set appropriate alert thresholds

### 4. Security

- Always validate and sanitize input
- Use secure authentication mechanisms
- Implement proper authorization
- Monitor for security anomalies

### 5. Testing

- Test all version combinations
- Validate schema compatibility
- Test performance under load
- Test error handling scenarios

## Monitoring and Observability

### Metrics

The API compatibility layer exposes Prometheus metrics:

- `api_compatibility_requests_total`: Total API requests
- `api_compatibility_duration_seconds`: Request duration
- `api_schema_validation_errors_total`: Schema validation errors
- `api_version_migrations_total`: Version migrations

### Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log API compatibility events
logger.info(f"API version registered: {service}/{version}")
logger.error(f"Schema validation failed: {errors}")
logger.warning(f"Version migration: {old_version} -> {new_version}")
```

### Tracing

The layer integrates with OpenTelemetry for distributed tracing:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("api_request") as span:
    span.set_attribute("service", service)
    span.set_attribute("version", version)
    # Process request
```

## Deployment

### Production Configuration

```python
# Production-ready configuration
version_config = APIVersionConfig(
    strategy=APIVersionStrategy.HEADER_BASED,
    default_version="v1",
    supported_versions=["v1", "v2"],
    enable_backward_compatibility=True,
    enable_forward_compatibility=True
)

schema_config = SchemaValidationConfig(
    enable_request_validation=True,
    enable_response_validation=True,
    strict_validation=False,
    cache_schemas=True,
    validation_timeout=5.0
)

# Create production layer
layer = create_api_compatibility_layer(version_config, schema_config)
```

### Health Checks

```python
# Health check endpoint
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": list(layer.version_manager.version_registry.keys()),
        "metrics": await layer.performance_monitor.generate_performance_report()
    }
```

## Troubleshooting

### Common Issues

1. **Schema Validation Failures**
   - Check schema definitions
   - Verify request/response format
   - Review validation rules

2. **Version Compatibility Issues**
   - Check backward compatibility settings
   - Verify version registration
   - Review migration strategies

3. **Performance Issues**
   - Monitor request duration
   - Check resource usage
   - Review caching configuration

4. **Security Issues**
   - Verify authentication tokens
   - Check authorization rules
   - Review input validation

### Debug Mode

```python
# Enable debug logging
logging.getLogger("server.api.compatibility_layer").setLevel(logging.DEBUG)

# Enable detailed validation
schema_config = SchemaValidationConfig(
    enable_request_validation=True,
    enable_response_validation=True,
    strict_validation=True
)
```

## Conclusion

The API compatibility layer provides a comprehensive solution for managing API compatibility in hybrid CPython/Codon architectures. It ensures seamless integration, maintains backward compatibility, and provides robust monitoring and security features for production deployment.

For more information, see the individual component documentation and test examples. 