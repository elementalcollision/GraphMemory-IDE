"""
Production-ready configuration management for GraphMemory-IDE.
Provides secure, environment-specific settings with validation and secrets management.
"""

import secrets
from typing import List, Optional, Union, Any, Tuple, cast
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class SecuritySettings(BaseModel):
    """Security-related configuration"""
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    # JWT Configuration with EdDSA support
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "EdDSA"  # Updated to use EdDSA (Ed25519) for enhanced security
    JWT_KEY_STORAGE_PATH: str = "./secrets/jwt"
    JWT_KEY_ROTATION_DAYS: int = 30  # Automatic rotation every 30 days
    JWT_MAX_KEY_VERSIONS: int = 5
    JWT_ENABLE_ROTATION: bool = True
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Reduced from 30 for better UX
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Enhanced Key Management
    USE_HSM: bool = False  # Hardware Security Module support
    HSM_PROVIDER: Optional[str] = None
    HSM_SLOT: Optional[str] = None
    ENABLE_KEY_CACHING: bool = False  # In-memory key caching
    
    # Password requirements
    MIN_PASSWORD_LENGTH: int = 12  # Increased from 8
    REQUIRE_PASSWORD_SPECIAL_CHARS: bool = True
    REQUIRE_PASSWORD_NUMBERS: bool = True
    REQUIRE_PASSWORD_UPPERCASE: bool = True
    REQUIRE_PASSWORD_LOWERCASE: bool = True
    
    # Rate limiting (enhanced)
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 20
    RATE_LIMIT_PER_HOUR: int = 1000  # Additional hourly limit
    
    # API Key Management
    API_KEY_LENGTH: int = 32
    API_KEY_ROTATION_DAYS: int = 90  # API keys rotate every 90 days
    API_KEY_SCOPED_PERMISSIONS: bool = True
    
    # Audit and Compliance
    SECURITY_AUDIT_LOGGING: bool = True
    AUDIT_LOG_PATH: str = "./logs/security_audit.log"
    AUDIT_LOG_ROTATION_SIZE: str = "10MB"
    AUDIT_LOG_RETENTION_DAYS: int = 90
    
    class Config:
        env_prefix = "SECURITY_"


class ServerSettings(BaseModel):
    """Server configuration"""
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    LOG_LEVEL: str = "INFO"
    
    # SSL Configuration
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    USE_SSL: bool = False
    
    @field_validator('WORKERS')
    @classmethod
    def validate_workers(cls, v: int, info: Any) -> int:
        if info.data.get('ENVIRONMENT') == Environment.PRODUCTION and v < 2:
            return 4  # Minimum workers for production
        return v
    
    @field_validator('DEBUG')
    @classmethod
    def validate_debug(cls, v: bool, info: Any) -> bool:
        if info.data.get('ENVIRONMENT') == Environment.PRODUCTION:
            return False  # Never debug in production
        return v
    
    class Config:
        env_prefix = "SERVER_"


class DatabaseSettings(BaseModel):
    """Database configuration"""
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/graphmemory_dev"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Kuzu Graph Database
    KUZU_DB_PATH: str = "./data/kuzu"
    KUZU_READ_ONLY: bool = False
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    REDIS_SOCKET_TIMEOUT: int = 5
    
    class Config:
        env_prefix = "DB_"


class SecurityHeadersSettings(BaseModel):
    """Security headers configuration"""
    # CORS Configuration
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Security Headers
    HSTS_MAX_AGE: int = 63072000  # 2 years
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = True
    
    # Content Security Policy
    CSP_DEFAULT_SRC: str = "'self'"
    CSP_SCRIPT_SRC: str = "'self' 'unsafe-inline'"
    CSP_STYLE_SRC: str = "'self' 'unsafe-inline'"
    CSP_IMG_SRC: str = "'self' data: https:"
    CSP_FONT_SRC: str = "'self'"
    CSP_CONNECT_SRC: str = "'self'"
    CSP_FRAME_ANCESTORS: str = "'none'"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(',')]
        return v
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(',')]
        return v
    
    class Config:
        env_prefix = "SECURITY_HEADERS_"


class MonitoringSettings(BaseModel):
    """Monitoring and observability configuration"""
    ENABLE_METRICS: bool = True
    METRICS_ENDPOINT: str = "/metrics"
    HEALTH_ENDPOINT: str = "/health"
    
    # Prometheus settings
    PROMETHEUS_METRICS_PORT: int = 9090
    
    # Logging
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_PATH: Optional[str] = None
    LOG_ROTATION_SIZE: str = "10MB"
    LOG_RETENTION_DAYS: int = 30
    
    # Performance monitoring
    SLOW_REQUEST_THRESHOLD: float = 1.0  # seconds
    ENABLE_REQUEST_TRACING: bool = True
    
    class Config:
        env_prefix = "MONITORING_"


class Settings(BaseModel):
    """Main application settings"""
    
    # Environment
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    APP_NAME: str = "GraphMemory-IDE"
    APP_VERSION: str = "1.0.0"
    
    # Feature flags
    ENABLE_COLLABORATION: bool = True
    ENABLE_STREAMING_ANALYTICS: bool = True
    ENABLE_DASHBOARD: bool = True
    ENABLE_JWT_AUTH: bool = True
    
    # Component settings
    security: SecuritySettings = SecuritySettings()
    server: ServerSettings = ServerSettings()
    database: DatabaseSettings = DatabaseSettings()
    security_headers: SecurityHeadersSettings = SecurityHeadersSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    @field_validator('ENVIRONMENT', mode='before')
    @classmethod
    def validate_environment(cls, v: Union[str, Environment]) -> Environment:
        """Ensure environment is valid"""
        # Convert to string for uniform handling
        v_str = str(v).lower() if v else "development"
        try:
            return cast(Environment, Environment(v_str))
        except ValueError:
            return Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.ENVIRONMENT == Environment.TESTING
    
    def get_database_url(self) -> str:
        """Get database URL with environment-specific defaults"""
        if self.is_production():
            return self.database.DATABASE_URL.replace("_dev", "_prod")
        elif self.is_testing():
            return self.database.DATABASE_URL.replace("_dev", "_test")
        return self.database.DATABASE_URL
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        if self.is_production():
            return [
                "https://graphmemory.com",
                "https://www.graphmemory.com",
                "https://api.graphmemory.com"
            ]
        elif self.is_development():
            return [
                "http://localhost:3000",
                "http://localhost:8080",
                "http://127.0.0.1:3000"
            ]
        return self.security_headers.CORS_ORIGINS
    
    def get_allowed_hosts(self) -> List[str]:
        """Get allowed hosts based on environment"""
        if self.is_production():
            return ["graphmemory.com", "www.graphmemory.com", "api.graphmemory.com"]
        return self.security_headers.ALLOWED_HOSTS
    
    def get_log_level(self) -> str:
        """Get log level based on environment"""
        if self.is_production():
            return "WARNING"
        elif self.is_development():
            return "DEBUG"
        return self.server.LOG_LEVEL
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        @classmethod
        def customise_sources(
            cls,
            init_settings: Any,
            env_settings: Any,
            file_secret_settings: Any,
        ) -> Tuple[Any, Any, Any]:
            """Customize settings sources priority"""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = Settings()
    return _settings


# Environment-specific configurations
PRODUCTION_CONFIG = {
    "ENVIRONMENT": "production",
    "SERVER_DEBUG": False,
    "SERVER_LOG_LEVEL": "INFO",
    "SERVER_WORKERS": 4,
    "SECURITY_RATE_LIMIT_PER_MINUTE": 1000,
    "SECURITY_HEADERS_CORS_ORIGINS": "https://graphmemory-ide.com,https://www.graphmemory-ide.com",
    "SECURITY_HEADERS_ALLOWED_HOSTS": "graphmemory-ide.com,www.graphmemory-ide.com",
    "MONITORING_ENABLE_METRICS": True,
    "MONITORING_ENABLE_REQUEST_TRACING": True,
}

STAGING_CONFIG = {
    "ENVIRONMENT": "staging",
    "SERVER_DEBUG": False,
    "SERVER_LOG_LEVEL": "INFO",
    "SERVER_WORKERS": 2,
    "SECURITY_RATE_LIMIT_PER_MINUTE": 500,
    "SECURITY_HEADERS_CORS_ORIGINS": "https://staging.graphmemory-ide.com",
    "SECURITY_HEADERS_ALLOWED_HOSTS": "staging.graphmemory-ide.com",
}

DEVELOPMENT_CONFIG = {
    "ENVIRONMENT": "development",
    "SERVER_DEBUG": True,
    "SERVER_LOG_LEVEL": "DEBUG",
    "SERVER_WORKERS": 1,
    "SECURITY_RATE_LIMIT_PER_MINUTE": 100,
    "SECURITY_HEADERS_CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
    "SECURITY_HEADERS_ALLOWED_HOSTS": "localhost,127.0.0.1",
} 