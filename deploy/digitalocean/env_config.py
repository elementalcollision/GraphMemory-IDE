"""
Environment configuration management for DigitalOcean deployment.
Provides centralized configuration with validation and multi-environment support.
"""

import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class EnvironmentType(Enum):
    """Available environment types."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TESTING = "testing"


@dataclass
class EnvironmentConfig:
    """Centralized environment configuration management."""
    
    name: str
    database_url: Optional[str]
    redis_url: str
    environment_type: str
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    cache_ttl: int = 300
    kuzu_database_path: str = "/tmp/kuzu_db"
    max_workers: int = 4
    timeout_seconds: int = 30
    
    @classmethod
    def from_environment(cls, env_name: str) -> "EnvironmentConfig":
        """Load configuration from environment variables."""
        configs = {
            "production": cls(
                name="production",
                database_url=os.getenv("DATABASE_URL"),
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                environment_type="production",
                debug=False,
                log_level="INFO",
                cors_origins=["https://graphmemory-ide.com"],
                rate_limit_per_minute=1000,
                cache_ttl=600,
                kuzu_database_path="/tmp/kuzu_db",
                max_workers=8,
                timeout_seconds=60
            ),
            "staging": cls(
                name="staging",
                database_url=os.getenv("STAGING_DATABASE_URL"),
                redis_url=os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/1"),
                environment_type="staging",
                debug=True,
                log_level="DEBUG",
                cors_origins=["https://staging.graphmemory-ide.com"],
                rate_limit_per_minute=500,
                cache_ttl=300,
                kuzu_database_path="/tmp/kuzu_staging_db",
                max_workers=4,
                timeout_seconds=45
            ),
            "development": cls(
                name="development",
                database_url=os.getenv("DEV_DATABASE_URL", "sqlite:///./test.db"),
                redis_url=os.getenv("DEV_REDIS_URL", "redis://localhost:6379/2"),
                environment_type="development",
                debug=True,
                log_level="DEBUG",
                cors_origins=["http://localhost:3000", "http://localhost:8080"],
                rate_limit_per_minute=100,
                cache_ttl=60,
                kuzu_database_path="./dev_kuzu_db",
                max_workers=2,
                timeout_seconds=30
            ),
            "testing": cls(
                name="testing",
                database_url=os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:"),
                redis_url=os.getenv("TEST_REDIS_URL", "redis://localhost:6379/3"),
                environment_type="testing",
                debug=True,
                log_level="DEBUG",
                cors_origins=["http://testserver"],
                rate_limit_per_minute=1000,
                cache_ttl=30,
                kuzu_database_path="./test_kuzu_db",
                max_workers=1,
                timeout_seconds=10
            )
        }
        
        if env_name not in configs:
            raise ValueError(f"Unknown environment: {env_name}. Available: {list(configs.keys())}")
        
        return configs[env_name]
    
    def validate(self) -> bool:
        """Validate configuration completeness."""
        validation_errors = []
        
        # Validate required fields
        if not self.database_url:
            validation_errors.append("database_url is required but not provided")
        
        if not self.redis_url:
            validation_errors.append("redis_url is required but not provided")
        
        # Validate CORS origins format
        if self.cors_origins:
            for origin in self.cors_origins:
                if not origin.startswith(("http://", "https://")):
                    validation_errors.append(f"Invalid CORS origin format: {origin}")
        
        # Validate numeric constraints
        if self.rate_limit_per_minute <= 0:
            validation_errors.append("rate_limit_per_minute must be positive")
        
        if self.cache_ttl <= 0:
            validation_errors.append("cache_ttl must be positive")
        
        if self.max_workers <= 0:
            validation_errors.append("max_workers must be positive")
        
        if self.timeout_seconds <= 0:
            validation_errors.append("timeout_seconds must be positive")
        
        if validation_errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(validation_errors)}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "environment_type": self.environment_type,
            "debug": self.debug,
            "log_level": self.log_level,
            "cors_origins": self.cors_origins,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "cache_ttl": self.cache_ttl,
            "kuzu_database_path": self.kuzu_database_path,
            "max_workers": self.max_workers,
            "timeout_seconds": self.timeout_seconds
        }


class CloudEnvironmentManager:
    """Manage cloud environments and configurations."""
    
    def __init__(self):
        self.current_env = os.getenv("ENVIRONMENT", "development")
        self.config = EnvironmentConfig.from_environment(self.current_env)
        self.config.validate()
    
    def get_config(self) -> EnvironmentConfig:
        """Get current environment configuration."""
        return self.config
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.config.environment_type == "production"
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.config.environment_type == "staging"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.config.environment_type == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.config.environment_type == "testing"
    
    def get_database_url(self) -> Optional[str]:
        """Get database URL for current environment."""
        return self.config.database_url
    
    def get_redis_url(self) -> str:
        """Get Redis URL for current environment."""
        return self.config.redis_url
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins for current environment."""
        return self.config.cors_origins
    
    def get_kuzu_path(self) -> str:
        """Get Kuzu database path for current environment."""
        return self.config.kuzu_database_path
    
    def get_rate_limit(self) -> int:
        """Get rate limit for current environment."""
        return self.config.rate_limit_per_minute
    
    def get_cache_ttl(self) -> int:
        """Get cache TTL for current environment."""
        return self.config.cache_ttl
    
    def switch_environment(self, env_name: str) -> None:
        """Switch to a different environment."""
        self.current_env = env_name
        self.config = EnvironmentConfig.from_environment(env_name)
        self.config.validate()
    
    def get_health_check_config(self) -> Dict[str, Any]:
        """Get health check configuration for current environment."""
        return {
            "timeout": self.config.timeout_seconds,
            "max_retries": 3 if self.is_production() else 1,
            "check_database": True,
            "check_redis": True,
            "check_kuzu": True
        }
    
    def get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment-specific configuration."""
        return {
            "instance_count": 2 if self.is_production() else 1,
            "instance_size": "basic-s" if self.is_production() else "basic-xxs",
            "auto_scale": self.is_production(),
            "health_check_path": "/health",
            "deployment_timeout": 600,
            "rollback_enabled": True
        }


# Global environment manager instance
env_manager = CloudEnvironmentManager()


def get_environment_config() -> EnvironmentConfig:
    """Get current environment configuration."""
    return env_manager.get_config()


def get_environment_manager() -> CloudEnvironmentManager:
    """Get the global environment manager."""
    return env_manager 