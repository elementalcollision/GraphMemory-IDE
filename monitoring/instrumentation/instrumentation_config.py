"""
Instrumentation Configuration Management
Environment-specific OpenTelemetry configuration and service discovery
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class InstrumentationConfig:
    """
    Comprehensive instrumentation configuration for GraphMemory-IDE.
    
    Supports environment-specific settings, service discovery,
    and performance optimization configurations.
    """
    
    # Core service configuration
    service_name: str = "graphmemory-ide"
    service_version: str = "1.0.0"
    environment: Environment = Environment.PRODUCTION
    
    # OpenTelemetry endpoints
    otlp_endpoint: str = "http://localhost:4317"
    prometheus_endpoint: str = "http://localhost:9090"
    grafana_endpoint: str = "http://localhost:3000"
    
    # Instrumentation toggles
    tracing_enabled: bool = True
    metrics_enabled: bool = True
    logging_enabled: bool = True
    profiling_enabled: bool = False
    
    # Sampling configuration
    trace_sampling_ratio: float = 1.0
    metrics_export_interval: int = 60
    log_level: str = "INFO"
    
    # Performance settings
    batch_span_processor_max_queue_size: int = 2048
    batch_span_processor_export_timeout: int = 30000
    batch_span_processor_max_export_batch_size: int = 512
    
    # Resource attributes
    resource_attributes: Dict[str, str] = field(default_factory=dict)
    
    # Security settings
    otlp_headers: Dict[str, str] = field(default_factory=dict)
    enable_console_export: bool = False
    
    # Feature flags
    auto_instrument_database: bool = True
    auto_instrument_http: bool = True
    auto_instrument_redis: bool = True
    auto_instrument_asyncio: bool = True
    
    # Custom instrumentation settings
    graphmemory_instrumentation_enabled: bool = True
    session_timeout_seconds: int = 3600
    operation_history_max_size: int = 1000
    
    # Monitoring configuration
    health_check_enabled: bool = True
    health_check_interval: int = 30
    
    # Alert configuration
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "error_rate_threshold": 0.05,  # 5% error rate
        "response_time_p95_threshold": 2.0,  # 2 seconds
        "memory_usage_threshold": 0.8,  # 80% memory usage
        "cpu_usage_threshold": 0.8,  # 80% CPU usage
    })
    
    @classmethod
    def from_environment(cls, env: Optional[Environment] = None) -> "InstrumentationConfig":
        """
        Create configuration from environment variables.
        
        Args:
            env: Optional environment override
            
        Returns:
            InstrumentationConfig instance
        """
        # Determine environment
        env_str = os.getenv("ENVIRONMENT", "production").lower()
        environment = env or Environment(env_str)
        
        # Parse resource attributes from environment
        resource_attributes = {}
        resource_attrs_env = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
        for attr in resource_attrs_env.split(","):
            if "=" in attr:
                key, value = attr.strip().split("=", 1)
                resource_attributes[key] = value
        
        # Parse OTLP headers
        otlp_headers = {}
        headers_env = os.getenv("OTLP_HEADERS", "")
        for header in headers_env.split(","):
            if "=" in header:
                key, value = header.strip().split("=", 1)
                otlp_headers[key] = value
        
        # Parse alert thresholds
        alert_thresholds = {}
        try:
            thresholds_json = os.getenv("ALERT_THRESHOLDS", "{}")
            alert_thresholds = json.loads(thresholds_json) if thresholds_json != "{}" else {}
        except json.JSONDecodeError:
            logger.warning("Invalid ALERT_THRESHOLDS JSON, using defaults")
        
        # Environment-specific defaults
        env_defaults = cls._get_environment_defaults(environment)
        
        return cls(
            service_name=os.getenv("SERVICE_NAME", "graphmemory-ide"),
            service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
            environment=environment,
            
            # Endpoints
            otlp_endpoint=os.getenv("OTLP_ENDPOINT", env_defaults["otlp_endpoint"]),
            prometheus_endpoint=os.getenv("PROMETHEUS_ENDPOINT", env_defaults["prometheus_endpoint"]),
            grafana_endpoint=os.getenv("GRAFANA_ENDPOINT", env_defaults["grafana_endpoint"]),
            
            # Feature toggles
            tracing_enabled=os.getenv("OTEL_TRACING_ENABLED", str(env_defaults["tracing_enabled"])).lower() == "true",
            metrics_enabled=os.getenv("OTEL_METRICS_ENABLED", str(env_defaults["metrics_enabled"])).lower() == "true",
            logging_enabled=os.getenv("OTEL_LOGGING_ENABLED", str(env_defaults["logging_enabled"])).lower() == "true",
            profiling_enabled=os.getenv("OTEL_PROFILING_ENABLED", str(env_defaults["profiling_enabled"])).lower() == "true",
            
            # Sampling
            trace_sampling_ratio=float(os.getenv("OTEL_TRACE_SAMPLING_RATIO", str(env_defaults["trace_sampling_ratio"]))),
            metrics_export_interval=int(os.getenv("OTEL_METRICS_EXPORT_INTERVAL", str(env_defaults["metrics_export_interval"]))),
            log_level=os.getenv("LOG_LEVEL", env_defaults["log_level"]),
            
            # Performance
            batch_span_processor_max_queue_size=int(os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048")),
            batch_span_processor_export_timeout=int(os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "30000")),
            batch_span_processor_max_export_batch_size=int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "512")),
            
            # Resource and security
            resource_attributes=resource_attributes,
            otlp_headers=otlp_headers,
            enable_console_export=os.getenv("OTEL_CONSOLE_EXPORT", str(env_defaults["enable_console_export"])).lower() == "true",
            
            # Auto-instrumentation
            auto_instrument_database=os.getenv("OTEL_AUTO_INSTRUMENT_DATABASE", "true").lower() == "true",
            auto_instrument_http=os.getenv("OTEL_AUTO_INSTRUMENT_HTTP", "true").lower() == "true",
            auto_instrument_redis=os.getenv("OTEL_AUTO_INSTRUMENT_REDIS", "true").lower() == "true",
            auto_instrument_asyncio=os.getenv("OTEL_AUTO_INSTRUMENT_ASYNCIO", "true").lower() == "true",
            
            # GraphMemory-specific
            graphmemory_instrumentation_enabled=os.getenv("GRAPHMEMORY_INSTRUMENTATION_ENABLED", "true").lower() == "true",
            session_timeout_seconds=int(os.getenv("GRAPHMEMORY_SESSION_TIMEOUT", "3600")),
            operation_history_max_size=int(os.getenv("GRAPHMEMORY_OPERATION_HISTORY_SIZE", "1000")),
            
            # Monitoring
            health_check_enabled=os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            
            # Alerts (merge with environment defaults)
            alert_thresholds={**env_defaults.get("alert_thresholds", {}), **alert_thresholds}
        )
    
    @staticmethod
    def _get_environment_defaults(environment: Environment) -> Dict[str, Any]:
        """Get environment-specific default values."""
        
        if environment == Environment.DEVELOPMENT:
            return {
                "otlp_endpoint": "http://localhost:4317",
                "prometheus_endpoint": "http://localhost:9090",
                "grafana_endpoint": "http://localhost:3000",
                "tracing_enabled": True,
                "metrics_enabled": True,
                "logging_enabled": True,
                "profiling_enabled": True,
                "trace_sampling_ratio": 1.0,
                "metrics_export_interval": 15,
                "log_level": "DEBUG",
                "enable_console_export": True,
                "alert_thresholds": {
                    "error_rate_threshold": 0.1,
                    "response_time_p95_threshold": 5.0,
                    "memory_usage_threshold": 0.9,
                    "cpu_usage_threshold": 0.9,
                }
            }
        
        elif environment == Environment.STAGING:
            return {
                "otlp_endpoint": "http://staging-otel-collector:4317",
                "prometheus_endpoint": "http://staging-prometheus:9090",
                "grafana_endpoint": "http://staging-grafana:3000",
                "tracing_enabled": True,
                "metrics_enabled": True,
                "logging_enabled": True,
                "profiling_enabled": False,
                "trace_sampling_ratio": 1.0,
                "metrics_export_interval": 30,
                "log_level": "INFO",
                "enable_console_export": False,
                "alert_thresholds": {
                    "error_rate_threshold": 0.05,
                    "response_time_p95_threshold": 3.0,
                    "memory_usage_threshold": 0.8,
                    "cpu_usage_threshold": 0.8,
                }
            }
        
        elif environment == Environment.PRODUCTION:
            return {
                "otlp_endpoint": "http://otel-collector:4317",
                "prometheus_endpoint": "http://prometheus:9090",
                "grafana_endpoint": "http://grafana:3000",
                "tracing_enabled": True,
                "metrics_enabled": True,
                "logging_enabled": True,
                "profiling_enabled": False,
                "trace_sampling_ratio": 0.1,  # Sample 10% in production
                "metrics_export_interval": 60,
                "log_level": "INFO",
                "enable_console_export": False,
                "alert_thresholds": {
                    "error_rate_threshold": 0.02,
                    "response_time_p95_threshold": 2.0,
                    "memory_usage_threshold": 0.75,
                    "cpu_usage_threshold": 0.75,
                }
            }
        
        else:  # TESTING
            return {
                "otlp_endpoint": "http://test-otel-collector:4317",
                "prometheus_endpoint": "http://test-prometheus:9090",
                "grafana_endpoint": "http://test-grafana:3000",
                "tracing_enabled": False,  # Disable in tests by default
                "metrics_enabled": False,
                "logging_enabled": True,
                "profiling_enabled": False,
                "trace_sampling_ratio": 0.0,
                "metrics_export_interval": 60,
                "log_level": "WARNING",
                "enable_console_export": False,
                "alert_thresholds": {
                    "error_rate_threshold": 1.0,  # Very high thresholds for testing
                    "response_time_p95_threshold": 10.0,
                    "memory_usage_threshold": 0.95,
                    "cpu_usage_threshold": 0.95,
                }
            }
    
    def validate(self) -> List[str]:
        """
        Validates the instrumentation configuration and returns a list of error messages for any invalid fields.
        
        Returns:
            List[str]: A list of validation error messages. The list is empty if the configuration is valid.
        """
        errors = []
        
        # Validate sampling ratio
        if not 0.0 <= self.trace_sampling_ratio <= 1.0:
            errors.append(f"trace_sampling_ratio must be between 0.0 and 1.0, got {self.trace_sampling_ratio}")
        
        # Validate intervals
        if self.metrics_export_interval <= 0:
            errors.append(f"metrics_export_interval must be positive, got {self.metrics_export_interval}")
        
        if self.session_timeout_seconds <= 0:
            errors.append(f"session_timeout_seconds must be positive, got {self.session_timeout_seconds}")
        
        # Validate batch processor settings
        if self.batch_span_processor_max_queue_size <= 0:
            errors.append("batch_span_processor_max_queue_size must be positive")
        
        if self.batch_span_processor_export_timeout <= 0:
            errors.append("batch_span_processor_export_timeout must be positive")
        
        if self.batch_span_processor_max_export_batch_size <= 0:
            errors.append("batch_span_processor_max_export_batch_size must be positive")
        
        # Validate alert thresholds
        for threshold_name, threshold_value in self.alert_thresholds.items():
            if not isinstance(threshold_value, (int, float)):
                errors.append(f"alert threshold {threshold_name} must be numeric, got {type(threshold_value)}")
                continue  # Skip further validation for non-numeric values
            if threshold_value < 0:
                errors.append(f"alert threshold {threshold_name} must be non-negative, got {threshold_value}")
        
        # Validate endpoints
        for endpoint_name in ["otlp_endpoint", "prometheus_endpoint", "grafana_endpoint"]:
            endpoint_value = getattr(self, endpoint_name)
            if not endpoint_value.startswith(("http://", "https://")):
                errors.append(f"{endpoint_name} must be a valid HTTP/HTTPS URL, got {endpoint_value}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {}
        
        for key, value in self.__dict__.items():
            if isinstance(value, Environment):
                result[key] = value.value
            elif isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        
        return result
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def get_otlp_exporter_config(self) -> Dict[str, Any]:
        """Get configuration for OTLP exporters."""
        return {
            "endpoint": self.otlp_endpoint,
            "headers": self.otlp_headers,
            "timeout": 30
        }
    
    def get_batch_processor_config(self) -> Dict[str, Any]:
        """Get configuration for batch span processor."""
        return {
            "max_queue_size": self.batch_span_processor_max_queue_size,
            "export_timeout_millis": self.batch_span_processor_export_timeout,
            "max_export_batch_size": self.batch_span_processor_max_export_batch_size
        }
    
    def get_resource_attributes(self) -> Dict[str, str]:
        """Get complete resource attributes including defaults."""
        attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.environment.value,
            "graphmemory.component": "main-api",
        }
        
        # Add custom attributes
        attributes.update(self.resource_attributes)
        
        # Add environment-specific attributes
        if "HOSTNAME" in os.environ:
            attributes["host.name"] = os.environ["HOSTNAME"]
        
        if "INSTANCE_ID" in os.environ:
            attributes["service.instance.id"] = os.environ["INSTANCE_ID"]
        
        return attributes
    
    def is_instrumentation_enabled(self, component: str) -> bool:
        """
        Check if a specific instrumentation component is enabled.
        
        Args:
            component: Component name (database, http, redis, asyncio, graphmemory)
            
        Returns:
            True if component instrumentation is enabled
        """
        component_map = {
            "database": self.auto_instrument_database,
            "http": self.auto_instrument_http,
            "redis": self.auto_instrument_redis,
            "asyncio": self.auto_instrument_asyncio,
            "graphmemory": self.graphmemory_instrumentation_enabled,
        }
        
        return component_map.get(component, False)


class ConfigurationManager:
    """
    Configuration manager for instrumentation settings.
    
    Provides centralized configuration management with environment
    detection, validation, and runtime updates.
    """
    
    def __init__(self, config: Optional[InstrumentationConfig] = None) -> None:
        self.config = config or InstrumentationConfig.from_environment()
        self._validation_errors = []
        
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            
            # Convert environment string to enum
            if "environment" in config_dict:
                config_dict["environment"] = Environment(config_dict["environment"])
            
            # Create new config from dictionary
            self.config = InstrumentationConfig(**config_dict)
            logger.info(f"Configuration loaded from {config_path}")
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save current configuration to JSON file.
        
        Args:
            config_path: Path to save configuration file
        """
        try:
            with open(config_path, 'w') as f:
                f.write(self.config.to_json())
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def validate(self) -> bool:
        """
        Validate current configuration.
        
        Returns:
            True if configuration is valid
        """
        self._validation_errors = self.config.validate()
        
        if self._validation_errors:
            logger.error(f"Configuration validation failed: {self._validation_errors}")
            return False
        
        logger.info("Configuration validation passed")
        return True
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors from last validation."""
        return self._validation_errors.copy()
    
    def update_config(self, **kwargs) -> None:
        """
        Update configuration attributes.
        
        Args:
            **kwargs: Configuration attributes to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated configuration: {key} = {value}")
            else:
                logger.warning(f"Unknown configuration attribute: {key}")
    
    def reload_from_environment(self) -> None:
        """Reload configuration from environment variables."""
        env = self.config.environment
        self.config = InstrumentationConfig.from_environment(env)
        logger.info("Configuration reloaded from environment")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging."""
        return {
            "service_name": self.config.service_name,
            "service_version": self.config.service_version,
            "environment": self.config.environment.value,
            "tracing_enabled": self.config.tracing_enabled,
            "metrics_enabled": self.config.metrics_enabled,
            "sampling_ratio": self.config.trace_sampling_ratio,
            "otlp_endpoint": self.config.otlp_endpoint,
            "validation_status": "valid" if not self._validation_errors else "invalid"
        }


# Global configuration manager
_config_manager = None

def get_config_manager() -> ConfigurationManager:
    """Get or create global configuration manager."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager()
        _config_manager.validate()
    
    return _config_manager

def get_config() -> InstrumentationConfig:
    """Get current instrumentation configuration."""
    return get_config_manager().config 