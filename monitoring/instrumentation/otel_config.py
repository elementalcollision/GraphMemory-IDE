"""
OpenTelemetry Configuration for GraphMemory-IDE
Comprehensive instrumentation setup with FastAPI integration
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

from opentelemetry import trace, metrics, _logs
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.trace import TracerProvider, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.semantic_conventions.resource import ResourceAttributes
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.propagators.tracecontext import TraceContextTextMapPropagator
from opentelemetry.instrumentation.middleware import BaseOpenTelemetryMiddleware

logger = logging.getLogger(__name__)

class GraphMemoryOTelConfig:
    """
    Advanced OpenTelemetry configuration for GraphMemory-IDE
    
    Features:
    - FastAPI auto-instrumentation with custom middleware
    - Multi-protocol propagation (TraceContext, B3)
    - OTLP exporters for traces, metrics, and logs
    - Environment-based configuration
    - Resource attribute management
    - Performance optimizations
    """
    
    def __init__(
        self,
        service_name: str = "graphmemory-ide",
        service_version: Optional[str] = None,
        environment: str = "production",
        otlp_endpoint: Optional[str] = None,
        otlp_headers: Optional[Dict[str, str]] = None,
        enable_console_export: bool = False,
        custom_resource_attributes: Optional[Dict[str, str]] = None
    ):
        self.service_name = service_name
        self.service_version = service_version or os.getenv("SERVICE_VERSION", "1.0.0")
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
        self.otlp_headers = otlp_headers or self._parse_otlp_headers()
        self.enable_console_export = enable_console_export
        self.custom_resource_attributes = custom_resource_attributes or {}
        
        # Configuration flags
        self.instrumentation_enabled = os.getenv("OTEL_INSTRUMENTATION_ENABLED", "true").lower() == "true"
        self.trace_sampling_ratio = float(os.getenv("OTEL_TRACE_SAMPLING_RATIO", "1.0"))
        self.metrics_export_interval = int(os.getenv("OTEL_METRICS_EXPORT_INTERVAL", "60"))
        
        # Initialized components
        self.tracer_provider = None
        self.meter_provider = None
        self.logger_provider = None
        self.instrumented_apps = set()
        
        logger.info(f"Initializing OpenTelemetry for {service_name} v{self.service_version}")
    
    def _parse_otlp_headers(self) -> Dict[str, str]:
        """Parse OTLP headers from environment variables."""
        headers = {}
        headers_env = os.getenv("OTLP_HEADERS", "")
        
        for header in headers_env.split(","):
            if "=" in header:
                key, value = header.strip().split("=", 1)
                headers[key] = value
        
        return headers
    
    def _create_resource(self) -> Resource:
        """Create OpenTelemetry resource with comprehensive attributes."""
        resource_attributes = {
            ResourceAttributes.SERVICE_NAME: self.service_name,
            ResourceAttributes.SERVICE_VERSION: self.service_version,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.environment,
            "graphmemory.component": "main-api",
            "graphmemory.node_env": os.getenv("NODE_ENV", "production"),
            "graphmemory.instance_id": os.getenv("INSTANCE_ID", "default"),
            "host.name": os.getenv("HOSTNAME", "localhost"),
        }
        
        # Add custom attributes
        resource_attributes.update(self.custom_resource_attributes)
        
        return Resource.create(resource_attributes)
    
    def setup_tracing(self) -> TracerProvider:
        """Configure distributed tracing with OTLP export."""
        if not self.instrumentation_enabled:
            logger.info("OpenTelemetry tracing disabled")
            return None
        
        resource = self._create_resource()
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(
            resource=resource,
            sampler=trace.TraceIdRatioBasedSampler(self.trace_sampling_ratio)
        )
        
        # Configure OTLP span exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{self.otlp_endpoint}/v1/traces",
            headers=self.otlp_headers,
            timeout=30
        )
        
        # Add batch span processor
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            export_timeout_millis=30000,
            max_export_batch_size=512
        )
        self.tracer_provider.add_span_processor(span_processor)
        
        # Console exporter for development
        if self.enable_console_export:
            from opentelemetry.exporter.console import ConsoleSpanExporter
            console_processor = BatchSpanProcessor(ConsoleSpanExporter())
            self.tracer_provider.add_span_processor(console_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        logger.info("OpenTelemetry tracing configured successfully")
        return self.tracer_provider
    
    def setup_metrics(self) -> MeterProvider:
        """Configure metrics collection with OTLP export."""
        if not self.instrumentation_enabled:
            logger.info("OpenTelemetry metrics disabled")
            return None
        
        resource = self._create_resource()
        
        # Create OTLP metric exporter
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=f"{self.otlp_endpoint}/v1/metrics",
            headers=self.otlp_headers,
            timeout=30
        )
        
        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            exporter=otlp_metric_exporter,
            export_interval_millis=self.metrics_export_interval * 1000
        )
        
        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(self.meter_provider)
        
        logger.info("OpenTelemetry metrics configured successfully")
        return self.meter_provider
    
    def setup_logging(self) -> LoggerProvider:
        """Configure structured logging with OTLP export."""
        if not self.instrumentation_enabled:
            logger.info("OpenTelemetry logging disabled")
            return None
        
        resource = self._create_resource()
        
        # Create logger provider
        self.logger_provider = LoggerProvider(resource=resource)
        
        # Configure OTLP log exporter
        otlp_log_exporter = OTLPLogExporter(
            endpoint=f"{self.otlp_endpoint}/v1/logs",
            headers=self.otlp_headers,
            timeout=30
        )
        
        # Add batch log record processor
        log_processor = BatchLogRecordProcessor(
            otlp_log_exporter,
            max_queue_size=2048,
            export_timeout_millis=30000,
            max_export_batch_size=512
        )
        self.logger_provider.add_log_record_processor(log_processor)
        
        # Set global logger provider
        _logs.set_logger_provider(self.logger_provider)
        
        # Configure Python logging integration
        handler = LoggingHandler(
            level=logging.INFO,
            logger_provider=self.logger_provider
        )
        
        # Add handler to root logger
        logging.getLogger().addHandler(handler)
        
        logger.info("OpenTelemetry logging configured successfully")
        return self.logger_provider
    
    def setup_propagation(self):
        """Configure trace context propagation."""
        # Composite propagator supporting multiple formats
        propagator = CompositeHTTPPropagator([
            TraceContextTextMapPropagator(),
            B3MultiFormat()
        ])
        
        set_global_textmap(propagator)
        logger.info("OpenTelemetry propagation configured")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application with OpenTelemetry."""
        if not self.instrumentation_enabled or app in self.instrumented_apps:
            return
        
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                meter_provider=self.meter_provider,
                excluded_urls=[
                    "/health",
                    "/healthz", 
                    "/metrics",
                    "/favicon.ico"
                ],
                http_capture_headers_server_request=[
                    "content-type",
                    "authorization",
                    "user-agent"
                ],
                http_capture_headers_server_response=[
                    "content-type",
                    "content-length"
                ]
            )
            
            self.instrumented_apps.add(app)
            logger.info("FastAPI instrumentation completed")
            
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
    
    def setup_database_instrumentation(self):
        """Configure database instrumentation."""
        if not self.instrumentation_enabled:
            return
        
        try:
            # SQLAlchemy instrumentation
            SQLAlchemyInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
                enable_commenter=True,
                commenter_options={
                    "opentelemetry_values": True
                }
            )
            
            # PostgreSQL instrumentation
            Psycopg2Instrumentor().instrument(
                tracer_provider=self.tracer_provider
            )
            
            logger.info("Database instrumentation configured")
            
        except Exception as e:
            logger.error(f"Failed to setup database instrumentation: {e}")
    
    def setup_redis_instrumentation(self):
        """Configure Redis instrumentation."""
        if not self.instrumentation_enabled:
            return
        
        try:
            RedisInstrumentor().instrument(
                tracer_provider=self.tracer_provider
            )
            
            logger.info("Redis instrumentation configured")
            
        except Exception as e:
            logger.error(f"Failed to setup Redis instrumentation: {e}")
    
    def setup_http_instrumentation(self):
        """Configure HTTP client instrumentation."""
        if not self.instrumentation_enabled:
            return
        
        try:
            # Requests library instrumentation
            RequestsInstrumentor().instrument(
                tracer_provider=self.tracer_provider
            )
            
            # HTTPX async client instrumentation
            HTTPXClientInstrumentor().instrument(
                tracer_provider=self.tracer_provider
            )
            
            logger.info("HTTP client instrumentation configured")
            
        except Exception as e:
            logger.error(f"Failed to setup HTTP instrumentation: {e}")
    
    def setup_asyncio_instrumentation(self):
        """Configure asyncio instrumentation."""
        if not self.instrumentation_enabled:
            return
        
        try:
            AsyncioInstrumentor().instrument(
                tracer_provider=self.tracer_provider
            )
            
            logger.info("Asyncio instrumentation configured")
            
        except Exception as e:
            logger.error(f"Failed to setup asyncio instrumentation: {e}")
    
    def initialize_all(self, app=None) -> None:
        """Initialize complete OpenTelemetry setup."""
        logger.info("Starting complete OpenTelemetry initialization")
        
        try:
            # Setup core components
            self.setup_tracing()
            self.setup_metrics()
            self.setup_logging()
            self.setup_propagation()
            
            # Setup instrumentation
            self.setup_database_instrumentation()
            self.setup_redis_instrumentation()
            self.setup_http_instrumentation()
            self.setup_asyncio_instrumentation()
            
            # Instrument FastAPI if provided
            if app:
                self.instrument_fastapi(app)
            
            logger.info("OpenTelemetry initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            raise
    
    @contextmanager
    def custom_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Create a custom span with optional attributes."""
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            
            yield span
    
    def get_tracer(self, name: str):
        """Get a tracer instance."""
        return trace.get_tracer(name)
    
    def get_meter(self, name: str):
        """Get a meter instance."""
        return metrics.get_meter(name)
    
    def shutdown(self):
        """Gracefully shutdown OpenTelemetry components."""
        logger.info("Shutting down OpenTelemetry")
        
        try:
            if self.tracer_provider:
                self.tracer_provider.shutdown()
            
            if self.meter_provider:
                self.meter_provider.shutdown()
            
            if self.logger_provider:
                self.logger_provider.shutdown()
            
            logger.info("OpenTelemetry shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during OpenTelemetry shutdown: {e}")


# Global configuration instance
otel_config = None

def get_otel_config() -> GraphMemoryOTelConfig:
    """Get or create global OpenTelemetry configuration."""
    global otel_config
    
    if otel_config is None:
        otel_config = GraphMemoryOTelConfig()
    
    return otel_config

def initialize_otel(app=None, **kwargs) -> GraphMemoryOTelConfig:
    """Initialize OpenTelemetry with optional FastAPI app."""
    global otel_config
    
    otel_config = GraphMemoryOTelConfig(**kwargs)
    otel_config.initialize_all(app)
    
    return otel_config

def shutdown_otel():
    """Shutdown OpenTelemetry gracefully."""
    global otel_config
    
    if otel_config:
        otel_config.shutdown()
        otel_config = None 