"""
Advanced Configuration for GraphMemory-IDE

This module extends the base configuration with settings for:
- Rate limiting and caching
- SSO and authentication 
- Analytics and monitoring
- A/B testing and feature flags
- Advanced security features

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import os
import secrets
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AdvancedSettings(BaseModel):
    """Enhanced settings for GraphMemory-IDE advanced features."""
    
    # Base application settings
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    
    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_REDIS_URL: str = Field(default="redis://localhost:6379/1")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_PER_HOUR: int = Field(default=1000)
    RATE_LIMIT_BURST_ALLOWANCE: int = Field(default=10)
    
    # SSO Configuration
    SSO_ENABLED: bool = Field(default=False)
    SSO_PROVIDERS: List[str] = Field(default=["azure-ad"])
    SSO_AZURE_CLIENT_ID: Optional[str] = Field(default=None)
    SSO_AZURE_CLIENT_SECRET: Optional[str] = Field(default=None)
    SSO_AZURE_TENANT_ID: Optional[str] = Field(default=None)
    SSO_OKTA_DOMAIN: Optional[str] = Field(default=None)
    SSO_OKTA_CLIENT_ID: Optional[str] = Field(default=None)
    SSO_OKTA_CLIENT_SECRET: Optional[str] = Field(default=None)
    
    # SAML Configuration
    SAML_ENABLED: bool = Field(default=False)
    SAML_SP_ENTITY_ID: str = Field(default="https://graphmemory-ide.com")
    SAML_SP_ACS_URL: str = Field(default="https://graphmemory-ide.com/sso/acs")
    SAML_SP_SLS_URL: str = Field(default="https://graphmemory-ide.com/sso/sls")
    SAML_IDP_METADATA_URL: Optional[str] = Field(default=None)
    
    # Analytics Configuration
    ANALYTICS_ENABLED: bool = Field(default=True)
    ANALYTICS_REDIS_URL: str = Field(default="redis://localhost:6379/2")
    ANALYTICS_BATCH_SIZE: int = Field(default=1000)
    ANALYTICS_FLUSH_INTERVAL: int = Field(default=60)  # seconds
    ANALYTICS_RETENTION_DAYS: int = Field(default=365)
    ANALYTICS_SAMPLE_RATE: float = Field(default=1.0)  # 1.0 = 100%
    
    # Privacy and GDPR
    GDPR_ENABLED: bool = Field(default=True)
    DATA_RETENTION_POLICY: int = Field(default=365)  # days
    ANONYMOUS_ANALYTICS: bool = Field(default=True)
    COOKIE_CONSENT_REQUIRED: bool = Field(default=True)
    
    # A/B Testing Configuration
    AB_TESTING_ENABLED: bool = Field(default=True)
    AB_TESTING_REDIS_URL: str = Field(default="redis://localhost:6379/3")
    MIN_SAMPLE_SIZE: int = Field(default=1000)
    STATISTICAL_SIGNIFICANCE: float = Field(default=0.95)
    AB_TEST_DURATION_DAYS: int = Field(default=14)
    
    # Feature Flags
    FEATURE_FLAGS_ENABLED: bool = Field(default=True)
    FEATURE_FLAGS_REDIS_URL: str = Field(default="redis://localhost:6379/4")
    FEATURE_FLAGS_CACHE_TTL: int = Field(default=300)  # seconds
    
    # Advanced Security
    MFA_ENABLED: bool = Field(default=False)
    MFA_REQUIRED: bool = Field(default=False)
    MFA_ISSUER_NAME: str = Field(default="GraphMemory-IDE")
    SESSION_TIMEOUT_MINUTES: int = Field(default=30)
    PASSWORD_POLICY_ENABLED: bool = Field(default=True)
    
    # Security Headers and CORS
    CORS_ENABLED: bool = Field(default=True)
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )
    SECURITY_HEADERS_ENABLED: bool = Field(default=True)
    CSP_ENABLED: bool = Field(default=True)
    
    # IP Whitelisting
    IP_WHITELIST_ENABLED: bool = Field(default=False)
    IP_WHITELIST: List[str] = Field(default=[])
    ADMIN_IP_WHITELIST: List[str] = Field(default=[])
    
    # API Keys and Authentication
    API_KEY_ENABLED: bool = Field(default=True)
    API_KEY_HEADER: str = Field(default="X-API-Key")
    JWT_SECRET_KEY: str = Field(default="your-secret-key-change-this")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_HOURS: int = Field(default=24)
    
    # External Integrations
    MIXPANEL_TOKEN: Optional[str] = Field(default=None)
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(default=None)
    HOTJAR_ID: Optional[str] = Field(default=None)
    SEGMENT_WRITE_KEY: Optional[str] = Field(default=None)
    
    # Email Configuration for notifications
    EMAIL_ENABLED: bool = Field(default=False)
    SMTP_HOST: Optional[str] = Field(default=None)
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_TLS: bool = Field(default=True)
    
    # Webhook Configuration
    WEBHOOKS_ENABLED: bool = Field(default=False)
    WEBHOOK_SECRET: Optional[str] = Field(default=None)
    WEBHOOK_TIMEOUT: int = Field(default=30)  # seconds
    
    # Advanced Monitoring
    ADVANCED_METRICS_ENABLED: bool = Field(default=True)
    PERFORMANCE_MONITORING: bool = Field(default=True)
    ERROR_TRACKING_ENABLED: bool = Field(default=True)
    SENTRY_DSN: Optional[str] = Field(default=None)
    
    # Business Intelligence
    BI_DASHBOARD_ENABLED: bool = Field(default=True)
    BI_EXPORT_ENABLED: bool = Field(default=True)
    BI_SCHEDULED_REPORTS: bool = Field(default=False)
    
    # Collaboration Features
    REAL_TIME_COLLABORATION: bool = Field(default=True)
    WEBSOCKET_ENABLED: bool = Field(default=True)
    PRESENCE_TRACKING: bool = Field(default=True)
    
    # Advanced Permissions
    ROLE_BASED_ACCESS: bool = Field(default=True)
    RESOURCE_LEVEL_PERMISSIONS: bool = Field(default=True)
    AUDIT_LOGGING: bool = Field(default=True)
    
    # Data Processing
    ASYNC_PROCESSING: bool = Field(default=True)
    TASK_QUEUE_ENABLED: bool = Field(default=True)
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/5")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/6")
    
    # Content Delivery
    CDN_ENABLED: bool = Field(default=False)
    CDN_URL: Optional[str] = Field(default=None)
    STATIC_FILE_CACHING: bool = Field(default=True)
    
    # Advanced Caching
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_REDIS_URL: str = Field(default="redis://localhost:6379/7")
    CACHE_DEFAULT_TTL: int = Field(default=3600)  # seconds
    CACHE_MAX_CONNECTIONS: int = Field(default=20)
    
    # File Storage
    FILE_STORAGE_BACKEND: str = Field(default="local")  # local, s3, gcs
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    AWS_S3_BUCKET: Optional[str] = Field(default=None)
    AWS_S3_REGION: str = Field(default="us-east-1")
    
    @field_validator("CORS_ALLOWED_ORIGINS", mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []
    
    @field_validator("SSO_PROVIDERS", mode='before')
    @classmethod
    def parse_sso_providers(cls, v: Any) -> List[str]:
        """Parse SSO providers from string or list."""
        if isinstance(v, str):
            return [provider.strip() for provider in v.split(",") if provider.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []
    
    @field_validator("IP_WHITELIST", mode='before')
    @classmethod
    def parse_ip_whitelist(cls, v: Any) -> List[str]:
        """Parse IP whitelist from string or list."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []
    
    @field_validator("ADMIN_IP_WHITELIST", mode='before')
    @classmethod
    def parse_admin_ip_whitelist(cls, v: Any) -> List[str]:
        """Parse admin IP whitelist from string or list."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        return []
    
    @field_validator("ANALYTICS_SAMPLE_RATE")
    @classmethod
    def validate_sample_rate(cls, v: float) -> float:
        """Validate analytics sample rate is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Analytics sample rate must be between 0 and 1")
        return v
    
    @field_validator("STATISTICAL_SIGNIFICANCE")
    @classmethod
    def validate_statistical_significance(cls, v: float) -> float:
        """Validate statistical significance is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Statistical significance must be between 0 and 1")
        return v
    
    def get_redis_config(self, service: str) -> Dict[str, Any]:
        """Get Redis configuration for a specific service."""
        redis_urls = {
            "rate_limit": self.RATE_LIMIT_REDIS_URL,
            "analytics": self.ANALYTICS_REDIS_URL,
            "ab_testing": self.AB_TESTING_REDIS_URL,
            "feature_flags": self.FEATURE_FLAGS_REDIS_URL,
            "cache": self.CACHE_REDIS_URL,
            "celery": self.CELERY_BROKER_URL,
        }
        
        url = redis_urls.get(service, "redis://localhost:6379/0")
        
        return {
            "url": url,
            "encoding": "utf-8",
            "decode_responses": True,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "max_connections": self.CACHE_MAX_CONNECTIONS,
        }
    
    def get_sso_config(self, provider: str) -> Dict[str, Any]:
        """Get SSO configuration for a specific provider."""
        configs = {
            "azure-ad": {
                "client_id": self.SSO_AZURE_CLIENT_ID,
                "client_secret": self.SSO_AZURE_CLIENT_SECRET,
                "tenant_id": self.SSO_AZURE_TENANT_ID,
                "authority": f"https://login.microsoftonline.com/{self.SSO_AZURE_TENANT_ID}",
                "scope": ["openid", "profile", "email"],
            },
            "okta": {
                "domain": self.SSO_OKTA_DOMAIN,
                "client_id": self.SSO_OKTA_CLIENT_ID,
                "client_secret": self.SSO_OKTA_CLIENT_SECRET,
                "issuer": f"https://{self.SSO_OKTA_DOMAIN}/oauth2/default",
                "scope": ["openid", "profile", "email"],
            },
        }
        
        return configs.get(provider, {})
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT.lower() in ["test", "testing"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = AdvancedSettings()


def get_settings() -> AdvancedSettings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> AdvancedSettings:
    """Reload settings from environment variables."""
    global settings
    settings = AdvancedSettings()
    return settings 