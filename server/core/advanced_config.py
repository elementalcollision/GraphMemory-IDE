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
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator


class AdvancedSettings(BaseSettings):
    """Enhanced settings for GraphMemory-IDE advanced features."""
    
    # Base application settings
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REDIS_URL: str = Field(default="redis://localhost:6379/1", env="RATE_LIMIT_REDIS_URL")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    RATE_LIMIT_BURST_ALLOWANCE: int = Field(default=10, env="RATE_LIMIT_BURST_ALLOWANCE")
    
    # SSO Configuration
    SSO_ENABLED: bool = Field(default=False, env="SSO_ENABLED")
    SSO_PROVIDERS: List[str] = Field(default=["azure-ad"], env="SSO_PROVIDERS")
    SSO_AZURE_CLIENT_ID: Optional[str] = Field(default=None, env="SSO_AZURE_CLIENT_ID")
    SSO_AZURE_CLIENT_SECRET: Optional[str] = Field(default=None, env="SSO_AZURE_CLIENT_SECRET")
    SSO_AZURE_TENANT_ID: Optional[str] = Field(default=None, env="SSO_AZURE_TENANT_ID")
    SSO_OKTA_DOMAIN: Optional[str] = Field(default=None, env="SSO_OKTA_DOMAIN")
    SSO_OKTA_CLIENT_ID: Optional[str] = Field(default=None, env="SSO_OKTA_CLIENT_ID")
    SSO_OKTA_CLIENT_SECRET: Optional[str] = Field(default=None, env="SSO_OKTA_CLIENT_SECRET")
    
    # SAML Configuration
    SAML_ENABLED: bool = Field(default=False, env="SAML_ENABLED")
    SAML_SP_ENTITY_ID: str = Field(default="https://graphmemory-ide.com", env="SAML_SP_ENTITY_ID")
    SAML_SP_ACS_URL: str = Field(default="https://graphmemory-ide.com/sso/acs", env="SAML_SP_ACS_URL")
    SAML_SP_SLS_URL: str = Field(default="https://graphmemory-ide.com/sso/sls", env="SAML_SP_SLS_URL")
    SAML_IDP_METADATA_URL: Optional[str] = Field(default=None, env="SAML_IDP_METADATA_URL")
    
    # Analytics Configuration
    ANALYTICS_ENABLED: bool = Field(default=True, env="ANALYTICS_ENABLED")
    ANALYTICS_REDIS_URL: str = Field(default="redis://localhost:6379/2", env="ANALYTICS_REDIS_URL")
    ANALYTICS_BATCH_SIZE: int = Field(default=1000, env="ANALYTICS_BATCH_SIZE")
    ANALYTICS_FLUSH_INTERVAL: int = Field(default=60, env="ANALYTICS_FLUSH_INTERVAL")  # seconds
    ANALYTICS_RETENTION_DAYS: int = Field(default=365, env="ANALYTICS_RETENTION_DAYS")
    ANALYTICS_SAMPLE_RATE: float = Field(default=1.0, env="ANALYTICS_SAMPLE_RATE")  # 1.0 = 100%
    
    # Privacy and GDPR
    GDPR_ENABLED: bool = Field(default=True, env="GDPR_ENABLED")
    DATA_RETENTION_POLICY: int = Field(default=365, env="DATA_RETENTION_POLICY")  # days
    ANONYMOUS_ANALYTICS: bool = Field(default=True, env="ANONYMOUS_ANALYTICS")
    COOKIE_CONSENT_REQUIRED: bool = Field(default=True, env="COOKIE_CONSENT_REQUIRED")
    
    # A/B Testing Configuration
    AB_TESTING_ENABLED: bool = Field(default=True, env="AB_TESTING_ENABLED")
    AB_TESTING_REDIS_URL: str = Field(default="redis://localhost:6379/3", env="AB_TESTING_REDIS_URL")
    MIN_SAMPLE_SIZE: int = Field(default=1000, env="MIN_SAMPLE_SIZE")
    STATISTICAL_SIGNIFICANCE: float = Field(default=0.95, env="STATISTICAL_SIGNIFICANCE")
    AB_TEST_DURATION_DAYS: int = Field(default=14, env="AB_TEST_DURATION_DAYS")
    
    # Feature Flags
    FEATURE_FLAGS_ENABLED: bool = Field(default=True, env="FEATURE_FLAGS_ENABLED")
    FEATURE_FLAGS_REDIS_URL: str = Field(default="redis://localhost:6379/4", env="FEATURE_FLAGS_REDIS_URL")
    FEATURE_FLAGS_CACHE_TTL: int = Field(default=300, env="FEATURE_FLAGS_CACHE_TTL")  # seconds
    
    # Advanced Security
    MFA_ENABLED: bool = Field(default=False, env="MFA_ENABLED")
    MFA_REQUIRED: bool = Field(default=False, env="MFA_REQUIRED")
    MFA_ISSUER_NAME: str = Field(default="GraphMemory-IDE", env="MFA_ISSUER_NAME")
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    PASSWORD_POLICY_ENABLED: bool = Field(default=True, env="PASSWORD_POLICY_ENABLED")
    
    # Security Headers and CORS
    CORS_ENABLED: bool = Field(default=True, env="CORS_ENABLED")
    CORS_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ALLOWED_ORIGINS"
    )
    SECURITY_HEADERS_ENABLED: bool = Field(default=True, env="SECURITY_HEADERS_ENABLED")
    CSP_ENABLED: bool = Field(default=True, env="CSP_ENABLED")
    
    # IP Whitelisting
    IP_WHITELIST_ENABLED: bool = Field(default=False, env="IP_WHITELIST_ENABLED")
    IP_WHITELIST: List[str] = Field(default=[], env="IP_WHITELIST")
    ADMIN_IP_WHITELIST: List[str] = Field(default=[], env="ADMIN_IP_WHITELIST")
    
    # API Keys and Authentication
    API_KEY_ENABLED: bool = Field(default=True, env="API_KEY_ENABLED")
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    JWT_SECRET_KEY: str = Field(default="your-secret-key-change-this", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # External Integrations
    MIXPANEL_TOKEN: Optional[str] = Field(default=None, env="MIXPANEL_TOKEN")
    GOOGLE_ANALYTICS_ID: Optional[str] = Field(default=None, env="GOOGLE_ANALYTICS_ID")
    HOTJAR_ID: Optional[str] = Field(default=None, env="HOTJAR_ID")
    SEGMENT_WRITE_KEY: Optional[str] = Field(default=None, env="SEGMENT_WRITE_KEY")
    
    # Email Configuration for notifications
    EMAIL_ENABLED: bool = Field(default=False, env="EMAIL_ENABLED")
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_TLS: bool = Field(default=True, env="SMTP_TLS")
    
    # Webhook Configuration
    WEBHOOKS_ENABLED: bool = Field(default=False, env="WEBHOOKS_ENABLED")
    WEBHOOK_SECRET: Optional[str] = Field(default=None, env="WEBHOOK_SECRET")
    WEBHOOK_TIMEOUT: int = Field(default=30, env="WEBHOOK_TIMEOUT")  # seconds
    
    # Advanced Monitoring
    ADVANCED_METRICS_ENABLED: bool = Field(default=True, env="ADVANCED_METRICS_ENABLED")
    PERFORMANCE_MONITORING: bool = Field(default=True, env="PERFORMANCE_MONITORING")
    ERROR_TRACKING_ENABLED: bool = Field(default=True, env="ERROR_TRACKING_ENABLED")
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Business Intelligence
    BI_DASHBOARD_ENABLED: bool = Field(default=True, env="BI_DASHBOARD_ENABLED")
    BI_EXPORT_ENABLED: bool = Field(default=True, env="BI_EXPORT_ENABLED")
    BI_SCHEDULED_REPORTS: bool = Field(default=False, env="BI_SCHEDULED_REPORTS")
    
    # Collaboration Features
    REAL_TIME_COLLABORATION: bool = Field(default=True, env="REAL_TIME_COLLABORATION")
    WEBSOCKET_ENABLED: bool = Field(default=True, env="WEBSOCKET_ENABLED")
    PRESENCE_TRACKING: bool = Field(default=True, env="PRESENCE_TRACKING")
    
    # Advanced Permissions
    ROLE_BASED_ACCESS: bool = Field(default=True, env="ROLE_BASED_ACCESS")
    RESOURCE_LEVEL_PERMISSIONS: bool = Field(default=True, env="RESOURCE_LEVEL_PERMISSIONS")
    AUDIT_LOGGING: bool = Field(default=True, env="AUDIT_LOGGING")
    
    # Data Processing
    ASYNC_PROCESSING: bool = Field(default=True, env="ASYNC_PROCESSING")
    TASK_QUEUE_ENABLED: bool = Field(default=True, env="TASK_QUEUE_ENABLED")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/5", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/6", env="CELERY_RESULT_BACKEND")
    
    # Content Delivery
    CDN_ENABLED: bool = Field(default=False, env="CDN_ENABLED")
    CDN_URL: Optional[str] = Field(default=None, env="CDN_URL")
    STATIC_FILE_CACHING: bool = Field(default=True, env="STATIC_FILE_CACHING")
    
    # Advanced Caching
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    CACHE_REDIS_URL: str = Field(default="redis://localhost:6379/7", env="CACHE_REDIS_URL")
    CACHE_DEFAULT_TTL: int = Field(default=3600, env="CACHE_DEFAULT_TTL")  # seconds
    CACHE_MAX_CONNECTIONS: int = Field(default=20, env="CACHE_MAX_CONNECTIONS")
    
    # File Storage
    FILE_STORAGE_BACKEND: str = Field(default="local", env="FILE_STORAGE_BACKEND")  # local, s3, gcs
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    AWS_S3_REGION: str = Field(default="us-east-1", env="AWS_S3_REGION")
    
    @validator("CORS_ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("SSO_PROVIDERS", pre=True)
    def parse_sso_providers(cls, v):
        """Parse SSO providers from string or list."""
        if isinstance(v, str):
            return [provider.strip() for provider in v.split(",") if provider.strip()]
        return v
    
    @validator("IP_WHITELIST", pre=True)
    def parse_ip_whitelist(cls, v):
        """Parse IP whitelist from string or list."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v
    
    @validator("ADMIN_IP_WHITELIST", pre=True)
    def parse_admin_ip_whitelist(cls, v):
        """Parse admin IP whitelist from string or list."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v
    
    @validator("ANALYTICS_SAMPLE_RATE")
    def validate_sample_rate(cls, v):
        """Validate analytics sample rate is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Analytics sample rate must be between 0 and 1")
        return v
    
    @validator("STATISTICAL_SIGNIFICANCE")
    def validate_statistical_significance(cls, v):
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