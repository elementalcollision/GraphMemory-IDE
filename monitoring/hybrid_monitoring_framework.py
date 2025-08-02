"""
Hybrid Monitoring Framework for CPython/Codon Architecture
Comprehensive monitoring and observability patterns for hybrid services
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import psutil
from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.propagators.tracecontext import TraceContextTextMapPropagator
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import Resource, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semantic_conventions.resource import ResourceAttributes
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Service types for hybrid architecture"""

    CPYTHON = "cpython"
    CONDON = "codon"
    HYBRID = "hybrid"


class MetricType(Enum):
    """Metric types for monitoring"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"
    ENUM = "enum"


@dataclass
class ServiceMetrics:
    """Service-specific metrics configuration"""

    service_name: str
    service_type: ServiceType
    metrics: Dict[str, Any] = field(default_factory=dict)
    custom_labels: Dict[str, str] = field(default_factory=dict)


class HybridMonitoringFramework:
    """
    Comprehensive monitoring framework for hybrid CPython/Codon architecture

    Features:
    - Unified monitoring for CPython and Codon services
    - Production-ready observability patterns
    - Distributed tracing across service boundaries
    - Custom metrics for hybrid architecture
    - Alerting and notification systems
    - Performance optimization
    """

    def __init__(
        self,
        service_name: str = "graphmemory-hybrid",
        service_version: str = "1.0.0",
        environment: str = "production",
        otlp_endpoint: Optional[str] = None,
        prometheus_port: int = 8000,
        enable_prometheus: bool = True,
        enable_otel: bool = True,
        custom_resource_attributes: Optional[Dict[str, str]] = None,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint or os.getenv(
            "OTLP_ENDPOINT", "http://localhost:4317"
        )
        self.prometheus_port = prometheus_port
        self.enable_prometheus = enable_prometheus
        self.enable_otel = enable_otel
        self.custom_resource_attributes = custom_resource_attributes or {}

        # Service registries
        self.cpython_services: Dict[str, ServiceMetrics] = {}
        self.codon_services: Dict[str, ServiceMetrics] = {}
        self.hybrid_services: Dict[str, ServiceMetrics] = {}

        # Monitoring components
        self.tracer_provider: Optional[TracerProvider] = None
        self.meter_provider: Optional[MeterProvider] = None
        self.logger_provider: Optional[LoggerProvider] = None
        self.prometheus_registry: Optional[CollectorRegistry] = None

        # Performance metrics
        self.performance_monitors: Dict[str, Any] = {}
        self.alert_managers: Dict[str, Any] = {}

        # Thread safety
        self._lock = threading.RLock()

        logger.info(f"Initializing Hybrid Monitoring Framework for {service_name}")

    def initialize(self) -> None:
        """Initialize the complete monitoring framework"""
        try:
            if self.enable_otel:
                self._setup_opentelemetry()

            if self.enable_prometheus:
                self._setup_prometheus()

            self._setup_custom_metrics()
            self._setup_performance_monitoring()
            self._setup_alerting()

            logger.info("Hybrid Monitoring Framework initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize monitoring framework: {e}")
            raise

    def _setup_opentelemetry(self) -> None:
        """Setup OpenTelemetry tracing, metrics, and logging"""
        # Create resource with hybrid architecture attributes
        resource_attributes = {
            ResourceAttributes.SERVICE_NAME: self.service_name,
            ResourceAttributes.SERVICE_VERSION: self.service_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.environment,
            "graphmemory.architecture": "hybrid",
            "graphmemory.service_type": "hybrid-monitoring",
            **self.custom_resource_attributes,
        }

        resource = Resource.create(attributes=resource_attributes)

        # Setup tracing
        self.tracer_provider = TracerProvider(resource=resource)
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=self.otlp_endpoint)
        )
        self.tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(self.tracer_provider)

        # Setup metrics
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=self.otlp_endpoint),
            export_interval_millis=60000,
        )
        self.meter_provider = MeterProvider(
            resource=resource, metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(self.meter_provider)

        # Setup logging
        log_processor = BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=self.otlp_endpoint)
        )
        self.logger_provider = LoggerProvider(
            resource=resource, processors=[log_processor]
        )
        _logs.set_logger_provider(self.logger_provider)

        # Setup propagation
        propagator = CompositeHTTPPropagator(
            [TraceContextTextMapPropagator(), B3MultiFormat()]
        )
        set_global_textmap(propagator)

        logger.info("OpenTelemetry setup completed")

    def _setup_prometheus(self) -> None:
        """Setup Prometheus metrics collection"""
        # Create registry for multiprocess support
        self.prometheus_registry = CollectorRegistry()

        # Start HTTP server for metrics exposure
        if self.enable_prometheus:
            start_http_server(self.prometheus_port, registry=self.prometheus_registry)
            logger.info(
                f"Prometheus metrics server started on port {self.prometheus_port}"
            )

    def _setup_custom_metrics(self) -> None:
        """Setup custom metrics for hybrid architecture"""
        # System metrics
        self.system_metrics = {
            "cpu_usage": Gauge("system_cpu_usage_percent", "CPU usage percentage"),
            "memory_usage": Gauge("system_memory_usage_bytes", "Memory usage in bytes"),
            "disk_usage": Gauge("system_disk_usage_percent", "Disk usage percentage"),
            "network_io": Counter(
                "system_network_io_bytes_total", "Network I/O in bytes"
            ),
        }

        # Service metrics
        self.service_metrics = {
            "request_count": Counter(
                "service_requests_total", "Total requests", ["service", "type"]
            ),
            "request_duration": Histogram(
                "service_request_duration_seconds",
                "Request duration",
                ["service", "type"],
            ),
            "error_count": Counter(
                "service_errors_total",
                "Total errors",
                ["service", "type", "error_type"],
            ),
            "active_connections": Gauge(
                "service_active_connections", "Active connections", ["service", "type"]
            ),
        }

        # Hybrid-specific metrics
        self.hybrid_metrics = {
            "service_boundary_calls": Counter(
                "hybrid_boundary_calls_total",
                "Calls across service boundaries",
                ["from_service", "to_service"],
            ),
            "data_transfer_bytes": Counter(
                "hybrid_data_transfer_bytes_total",
                "Data transfer in bytes",
                ["direction", "service"],
            ),
            "thread_safety_events": Counter(
                "hybrid_thread_safety_events_total",
                "Thread safety events",
                ["event_type", "service"],
            ),
            "compilation_metrics": Histogram(
                "codon_compilation_duration_seconds",
                "Codon compilation duration",
                ["compilation_type"],
            ),
        }

        logger.info("Custom metrics setup completed")

    def _setup_performance_monitoring(self) -> None:
        """Setup performance monitoring for hybrid services"""
        # CPython performance monitoring
        self.cpython_performance = {
            "gil_contention": Gauge(
                "cpython_gil_contention_ratio", "GIL contention ratio"
            ),
            "memory_allocation": Counter(
                "cpython_memory_allocation_bytes_total", "Memory allocation"
            ),
            "gc_collections": Counter(
                "cpython_gc_collections_total", "Garbage collection events"
            ),
            "async_tasks": Gauge("cpython_async_tasks_active", "Active async tasks"),
        }

        # Codon performance monitoring
        self.codon_performance = {
            "compilation_time": Histogram(
                "codon_compilation_time_seconds", "Compilation time"
            ),
            "memory_usage": Gauge("codon_memory_usage_bytes", "Memory usage"),
            "thread_count": Gauge("codon_thread_count", "Active thread count"),
            "cache_hit_ratio": Gauge("codon_cache_hit_ratio", "Cache hit ratio"),
        }

        # Hybrid performance monitoring
        self.hybrid_performance = {
            "boundary_latency": Histogram(
                "hybrid_boundary_latency_seconds", "Service boundary latency"
            ),
            "data_serialization_time": Histogram(
                "hybrid_serialization_time_seconds", "Data serialization time"
            ),
            "protocol_overhead": Gauge(
                "hybrid_protocol_overhead_bytes", "Protocol overhead"
            ),
        }

        logger.info("Performance monitoring setup completed")

    def _setup_alerting(self) -> None:
        """Setup alerting and notification systems"""
        # Alert thresholds
        self.alert_thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "error_rate": 5.0,
            "response_time": 2.0,
            "boundary_latency": 1.0,
        }

        # Alert managers
        self.alert_managers = {
            "performance": self._create_performance_alert_manager(),
            "errors": self._create_error_alert_manager(),
            "resources": self._create_resource_alert_manager(),
            "hybrid": self._create_hybrid_alert_manager(),
        }

        logger.info("Alerting system setup completed")

    def register_cpython_service(
        self, service_name: str, custom_labels: Optional[Dict[str, str]] = None
    ) -> ServiceMetrics:
        """Register a CPython service for monitoring"""
        with self._lock:
            service_metrics = ServiceMetrics(
                service_name=service_name,
                service_type=ServiceType.CPYTHON,
                custom_labels=custom_labels or {},
            )
            self.cpython_services[service_name] = service_metrics

            # Initialize service-specific metrics
            self._initialize_service_metrics(service_metrics)

            logger.info(f"Registered CPython service: {service_name}")
            return service_metrics

    def register_codon_service(
        self, service_name: str, custom_labels: Optional[Dict[str, str]] = None
    ) -> ServiceMetrics:
        """Register a Codon service for monitoring"""
        with self._lock:
            service_metrics = ServiceMetrics(
                service_name=service_name,
                service_type=ServiceType.CONDON,
                custom_labels=custom_labels or {},
            )
            self.codon_services[service_name] = service_metrics

            # Initialize service-specific metrics
            self._initialize_service_metrics(service_metrics)

            logger.info(f"Registered Codon service: {service_name}")
            return service_metrics

    def register_hybrid_service(
        self, service_name: str, custom_labels: Optional[Dict[str, str]] = None
    ) -> ServiceMetrics:
        """Register a hybrid service for monitoring"""
        with self._lock:
            service_metrics = ServiceMetrics(
                service_name=service_name,
                service_type=ServiceType.HYBRID,
                custom_labels=custom_labels or {},
            )
            self.hybrid_services[service_name] = service_metrics

            # Initialize service-specific metrics
            self._initialize_service_metrics(service_metrics)

            logger.info(f"Registered hybrid service: {service_name}")
            return service_metrics

    def _initialize_service_metrics(self, service_metrics: ServiceMetrics) -> None:
        """Initialize metrics for a specific service"""
        service_name = service_metrics.service_name
        service_type = service_metrics.service_type.value

        # Create service-specific metrics
        service_metrics.metrics = {
            "request_count": Counter(
                f"{service_name}_requests_total",
                "Request count",
                ["endpoint", "method"],
            ),
            "request_duration": Histogram(
                f"{service_name}_request_duration_seconds",
                "Request duration",
                ["endpoint"],
            ),
            "error_count": Counter(
                f"{service_name}_errors_total",
                "Error count",
                ["error_type", "endpoint"],
            ),
            "active_requests": Gauge(
                f"{service_name}_active_requests", "Active requests"
            ),
            "memory_usage": Gauge(f"{service_name}_memory_usage_bytes", "Memory usage"),
            "cpu_usage": Gauge(f"{service_name}_cpu_usage_percent", "CPU usage"),
        }

        # Add service type label
        for metric in service_metrics.metrics.values():
            if hasattr(metric, "labels"):
                metric.labels(service_type=service_type)

    @contextmanager
    def monitor_request(self, service_name: str, endpoint: str, method: str = "GET"):
        """Context manager for monitoring requests"""
        start_time = time.time()
        active_requests = None
        request_count = None
        request_duration = None

        try:
            # Get service metrics
            service = self._get_service(service_name)
            if service:
                active_requests = service.metrics.get("active_requests")
                request_count = service.metrics.get("request_count")
                request_duration = service.metrics.get("request_duration")

                if active_requests:
                    active_requests.inc()
                if request_count:
                    request_count.labels(endpoint=endpoint, method=method).inc()

            yield

        except Exception as e:
            # Record error
            if service:
                error_count = service.metrics.get("error_count")
                if error_count:
                    error_count.labels(
                        error_type=type(e).__name__, endpoint=endpoint
                    ).inc()
            raise

        finally:
            # Record duration and decrement active requests
            duration = time.time() - start_time

            if service:
                if request_duration:
                    request_duration.labels(endpoint=endpoint).observe(duration)
                if active_requests:
                    active_requests.dec()

    @contextmanager
    def monitor_boundary_call(self, from_service: str, to_service: str):
        """Context manager for monitoring service boundary calls"""
        start_time = time.time()

        try:
            # Record boundary call
            boundary_calls = self.hybrid_metrics.get("service_boundary_calls")
            if boundary_calls:
                boundary_calls.labels(
                    from_service=from_service, to_service=to_service
                ).inc()

            yield

        finally:
            # Record boundary latency
            duration = time.time() - start_time
            boundary_latency = self.hybrid_performance.get("boundary_latency")
            if boundary_latency:
                boundary_latency.observe(duration)

    def record_thread_safety_event(self, event_type: str, service_name: str):
        """Record thread safety events for Codon services"""
        thread_safety_events = self.hybrid_metrics.get("thread_safety_events")
        if thread_safety_events:
            thread_safety_events.labels(
                event_type=event_type, service=service_name
            ).inc()

    def record_compilation_metrics(self, compilation_type: str, duration: float):
        """Record Codon compilation metrics"""
        compilation_metrics = self.hybrid_metrics.get("compilation_metrics")
        if compilation_metrics:
            compilation_metrics.labels(compilation_type=compilation_type).observe(
                duration
            )

    def update_system_metrics(self):
        """Update system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_metrics["cpu_usage"].set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            self.system_metrics["memory_usage"].set(memory.used)

            # Disk usage
            disk = psutil.disk_usage("/")
            self.system_metrics["disk_usage"].set(disk.percent)

        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    def _get_service(self, service_name: str) -> Optional[ServiceMetrics]:
        """Get service metrics by name"""
        return (
            self.cpython_services.get(service_name)
            or self.codon_services.get(service_name)
            or self.hybrid_services.get(service_name)
        )

    def _create_performance_alert_manager(self):
        """Create performance alert manager"""

        def check_performance_alerts():
            # Check CPU usage
            cpu_usage = self.system_metrics["cpu_usage"]._value.get()
            if cpu_usage and cpu_usage > self.alert_thresholds["cpu_usage"]:
                self._send_alert("performance", f"High CPU usage: {cpu_usage}%")

            # Check memory usage
            memory_usage = self.system_metrics["memory_usage"]._value.get()
            if memory_usage:
                memory_percent = (memory_usage / psutil.virtual_memory().total) * 100
                if memory_percent > self.alert_thresholds["memory_usage"]:
                    self._send_alert(
                        "performance", f"High memory usage: {memory_percent:.1f}%"
                    )

        return check_performance_alerts

    def _create_error_alert_manager(self):
        """Create error alert manager"""

        def check_error_alerts():
            # Check error rates across services
            for service_name, service in {
                **self.cpython_services,
                **self.codon_services,
                **self.hybrid_services,
            }.items():
                error_count = service.metrics.get("error_count")
                request_count = service.metrics.get("request_count")

                if error_count and request_count:
                    # Calculate error rate (simplified)
                    error_rate = 0  # This would need actual calculation
                    if error_rate > self.alert_thresholds["error_rate"]:
                        self._send_alert(
                            "errors",
                            f"High error rate in {service_name}: {error_rate}%",
                        )

        return check_error_alerts

    def _create_resource_alert_manager(self):
        """Create resource alert manager"""

        def check_resource_alerts():
            # Check disk usage
            disk_usage = self.system_metrics["disk_usage"]._value.get()
            if disk_usage and disk_usage > 90:
                self._send_alert("resources", f"Critical disk usage: {disk_usage}%")

        return check_resource_alerts

    def _create_hybrid_alert_manager(self):
        """Create hybrid-specific alert manager"""

        def check_hybrid_alerts():
            # Check boundary latency
            boundary_latency = self.hybrid_performance.get("boundary_latency")
            if boundary_latency:
                # This would need actual latency calculation
                pass

        return check_hybrid_alerts

    def _send_alert(self, alert_type: str, message: str):
        """Send alert notification"""
        logger.warning(f"ALERT [{alert_type}]: {message}")
        # Here you would integrate with your alerting system
        # (e.g., Slack, email, PagerDuty, etc.)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        summary = {
            "system": {
                "cpu_usage": self.system_metrics["cpu_usage"]._value.get(),
                "memory_usage": self.system_metrics["memory_usage"]._value.get(),
                "disk_usage": self.system_metrics["disk_usage"]._value.get(),
            },
            "services": {
                "cpython": len(self.cpython_services),
                "codon": len(self.codon_services),
                "hybrid": len(self.hybrid_services),
            },
            "alerts": {
                "active_alerts": 0,  # This would be tracked
                "alert_thresholds": self.alert_thresholds,
            },
        }

        return summary

    def shutdown(self):
        """Shutdown monitoring framework"""
        try:
            # Shutdown OpenTelemetry
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            if self.logger_provider:
                self.logger_provider.shutdown()

            logger.info("Hybrid Monitoring Framework shutdown completed")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global instance
_hybrid_monitoring = None


def get_hybrid_monitoring() -> HybridMonitoringFramework:
    """Get global hybrid monitoring instance"""
    global _hybrid_monitoring
    if _hybrid_monitoring is None:
        _hybrid_monitoring = HybridMonitoringFramework()
        _hybrid_monitoring.initialize()
    return _hybrid_monitoring


def initialize_hybrid_monitoring(**kwargs) -> HybridMonitoringFramework:
    """Initialize hybrid monitoring framework"""
    global _hybrid_monitoring
    _hybrid_monitoring = HybridMonitoringFramework(**kwargs)
    _hybrid_monitoring.initialize()
    return _hybrid_monitoring


def shutdown_hybrid_monitoring():
    """Shutdown hybrid monitoring framework"""
    global _hybrid_monitoring
    if _hybrid_monitoring:
        _hybrid_monitoring.shutdown()
        _hybrid_monitoring = None
