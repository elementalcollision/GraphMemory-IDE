# Hybrid Monitoring Framework

Comprehensive monitoring and observability patterns for CPython/Codon hybrid architecture.

## Overview

The Hybrid Monitoring Framework provides production-ready observability solutions for hybrid CPython/Codon architectures, including:

- **Unified Monitoring**: Single framework for both CPython and Codon services
- **Distributed Tracing**: Cross-service boundary tracing with OpenTelemetry
- **Custom Metrics**: Service-specific metrics for hybrid architectures
- **Real-time Dashboard**: Web-based dashboard with WebSocket updates
- **Alerting**: Configurable alerting and notification systems
- **Performance Optimization**: Minimal overhead monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid Monitoring Framework              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ CPython     │  │ Codon       │  │ Hybrid      │       │
│  │ Monitor     │  │ Monitor     │  │ Monitor     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ OpenTelemetry│  │ Prometheus  │  │ Dashboard   │       │
│  │ Tracing     │  │ Metrics     │  │ & Alerts    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Initialize the Framework

```python
from monitoring.hybrid_monitoring_framework import initialize_hybrid_monitoring

# Initialize with default settings
framework = initialize_hybrid_monitoring(
    service_name="my-hybrid-app",
    environment="production"
)
```

### 2. Register Services

```python
# Register CPython services
cpython_service = framework.register_cpython_service(
    "auth-service",
    {"environment": "production", "version": "1.0.0"}
)

# Register Codon services
codon_service = framework.register_codon_service(
    "analytics-service",
    {"environment": "production", "version": "1.0.0"}
)

# Register hybrid services
hybrid_service = framework.register_hybrid_service(
    "api-gateway",
    {"environment": "production", "version": "1.0.0"}
)
```

### 3. Monitor Requests

```python
# Monitor CPython service requests
with framework.monitor_request("auth-service", "/login", "POST"):
    # Your authentication logic here
    authenticate_user(credentials)

# Monitor Codon service requests
with framework.monitor_request("analytics-service", "/process", "POST"):
    # Your analytics processing here
    process_data(data)

# Monitor service boundary calls
with framework.monitor_boundary_call("auth-service", "analytics-service"):
    # Cross-service communication
    send_analytics_event(user_id, event_data)
```

### 4. Start the Dashboard

```python
from monitoring.dashboard.hybrid_dashboard import start_dashboard

# Start dashboard on port 8080
start_dashboard(host="0.0.0.0", port=8080)
```

## CPython Monitoring

### GIL Contention Monitoring

```python
from monitoring.cpython_monitor import CPythonMonitor

monitor = CPythonMonitor("my-cpython-service")

# Monitor GIL contention
with monitor.monitor_gil_contention("database_query"):
    # CPU-intensive operation
    result = perform_heavy_computation()

# Monitor async tasks
with monitor.monitor_async_task("data_processing"):
    await process_large_dataset()
```

### Memory and GC Monitoring

```python
# Monitor garbage collection
with monitor.monitor_gc(generation=0):
    # Operations that may trigger GC
    process_large_objects()

# Record memory operations
monitor.record_cpu_bound_operation("matrix_multiplication")
monitor.record_io_bound_operation("file_reading")
```

## Codon Monitoring

### Compilation Monitoring

```python
from monitoring.codon_monitor import CodonMonitor, CompilationType

monitor = CodonMonitor("my-codon-service")

# Monitor JIT compilation
with monitor.monitor_compilation(CompilationType.JIT, "optimized"):
    # Compilation process
    compiled_function = compile_function(source_code)

# Monitor AOT compilation
with monitor.monitor_compilation(CompilationType.AOT, "release"):
    # Ahead-of-time compilation
    compiled_binary = compile_to_binary(source_code)
```

### Thread Safety Monitoring

```python
from monitoring.codon_monitor import ThreadSafetyEvent

# Record thread safety events
monitor.record_thread_safety_event(
    ThreadSafetyEvent.LOCK_ACQUISITION,
    "info"
)

monitor.record_thread_safety_event(
    ThreadSafetyEvent.DEADLOCK_DETECTED,
    "critical"
)
```

### Native Execution Monitoring

```python
# Monitor native code execution
with monitor.monitor_native_execution("optimized_function", "optimized"):
    # Native code execution
    result = optimized_function(input_data)
```

## Dashboard Features

### Real-time Metrics

The dashboard provides real-time visualization of:

- **System Metrics**: CPU, memory, disk usage
- **Service Metrics**: Request rates, response times, error rates
- **Hybrid Metrics**: Service boundary calls, data transfer
- **Performance Metrics**: GIL contention, compilation times

### Alert Management

```python
# Configure alert thresholds
framework.alert_thresholds = {
    "cpu_usage": 80.0,
    "memory_usage": 85.0,
    "error_rate": 5.0,
    "response_time": 2.0,
    "boundary_latency": 1.0,
}
```

### WebSocket Updates

The dashboard uses WebSocket connections for real-time updates:

```javascript
// Connect to dashboard WebSocket
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};
```

## Configuration

### Environment Variables

```bash
# OpenTelemetry Configuration
OTLP_ENDPOINT=http://localhost:4317
OTEL_INSTRUMENTATION_ENABLED=true
OTEL_TRACE_SAMPLING_RATIO=1.0

# Prometheus Configuration
PROMETHEUS_PORT=8000
PROMETHEUS_ENABLED=true

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
```

### Custom Resource Attributes

```python
framework = initialize_hybrid_monitoring(
    service_name="my-app",
    custom_resource_attributes={
        "deployment.environment": "production",
        "service.version": "1.0.0",
        "team": "platform",
        "datacenter": "us-west-1"
    }
)
```

## Metrics

### System Metrics

- `system_cpu_usage_percent`: CPU usage percentage
- `system_memory_usage_bytes`: Memory usage in bytes
- `system_disk_usage_percent`: Disk usage percentage
- `system_network_io_bytes_total`: Network I/O in bytes

### Service Metrics

- `service_requests_total`: Total requests by service and type
- `service_request_duration_seconds`: Request duration by service
- `service_errors_total`: Error count by service and type
- `service_active_connections`: Active connections by service

### CPython Metrics

- `cpython_gil_contention_seconds`: GIL contention time
- `cpython_gil_acquire_total`: GIL acquisition count
- `cpython_memory_allocated_bytes`: Currently allocated memory
- `cpython_gc_collections_total`: Garbage collection events
- `cpython_async_tasks_active`: Active async tasks

### Codon Metrics

- `codon_compilation_duration_seconds`: Compilation duration
- `codon_compilation_memory_bytes`: Memory used during compilation
- `codon_thread_safety_events_total`: Thread safety events
- `codon_memory_allocation_bytes_total`: Memory allocation
- `codon_native_execution_seconds`: Native code execution time

### Hybrid Metrics

- `hybrid_boundary_calls_total`: Calls across service boundaries
- `hybrid_data_transfer_bytes_total`: Data transfer in bytes
- `hybrid_thread_safety_events_total`: Thread safety events
- `hybrid_boundary_latency_seconds`: Service boundary latency

## Testing

### Run Tests

```bash
# Run all monitoring tests
pytest monitoring/test_hybrid_monitoring.py -v

# Run specific test categories
pytest monitoring/test_hybrid_monitoring.py::TestHybridMonitoringFramework -v
pytest monitoring/test_hybrid_monitoring.py::TestCPythonMonitor -v
pytest monitoring/test_hybrid_monitoring.py::TestCodonMonitor -v
```

### Test Coverage

The test suite covers:

- Framework initialization and configuration
- Service registration and monitoring
- Request and boundary call monitoring
- Error handling and recovery
- Concurrent monitoring operations
- Performance metrics collection

## Performance Considerations

### Overhead

- **Metrics Collection**: < 1ms overhead per metric
- **Tracing**: < 5ms trace overhead
- **Dashboard Updates**: < 10ms processing time
- **Memory Usage**: < 50MB for full framework

### Optimization

```python
# Disable unused components for minimal overhead
framework = initialize_hybrid_monitoring(
    enable_prometheus=False,  # Disable Prometheus
    enable_otel=False,        # Disable OpenTelemetry
    prometheus_port=None      # Disable HTTP server
)
```

### Sampling

```python
# Configure sampling for high-volume services
framework.trace_sampling_ratio = 0.1  # Sample 10% of traces
framework.metrics_export_interval = 300  # Export every 5 minutes
```

## Production Deployment

### Docker Integration

```dockerfile
# Add monitoring to your Dockerfile
COPY monitoring/ /app/monitoring/
RUN pip install -r monitoring/requirements.txt

# Start monitoring with your application
CMD ["python", "-m", "monitoring.start_monitoring"]
```

### Kubernetes Integration

```yaml
# Add monitoring sidecar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-hybrid-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-hybrid-app:latest
      - name: monitoring
        image: monitoring-sidecar:latest
        ports:
        - containerPort: 8000  # Prometheus metrics
        - containerPort: 8080  # Dashboard
```

### Health Checks

```python
# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "monitoring": framework.get_metrics_summary(),
        "timestamp": datetime.now().isoformat()
    }
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Reduce metrics history retention
   - Disable unused metric types
   - Increase garbage collection frequency

2. **Slow Dashboard**
   - Reduce WebSocket update frequency
   - Limit metrics history size
   - Use sampling for high-volume services

3. **Missing Metrics**
   - Check service registration
   - Verify metric collection intervals
   - Review error logs for collection failures

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Initialize with debug mode
framework = initialize_hybrid_monitoring(
    enable_console_export=True,  # Export to console
    log_level="DEBUG"
)
```

## Contributing

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd monitoring

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_hybrid_monitoring.py -v

# Start development dashboard
python -m monitoring.dashboard.hybrid_dashboard
```

### Adding New Metrics

1. Define metric in appropriate monitor class
2. Add collection logic in monitoring loop
3. Update dashboard visualization
4. Add tests for new metric
5. Update documentation

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Add docstrings for all classes and methods
- Write comprehensive tests for new features

## License

This monitoring framework is licensed under the MIT License. See LICENSE file for details.

## Support

For support and questions:

- Create an issue in the repository
- Check the troubleshooting section
- Review the test examples
- Consult the API documentation 