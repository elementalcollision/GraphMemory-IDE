"""
SSO Provider Model for GraphMemory-IDE

This module defines the database model for SSO provider configurations
including SAML 2.0 and OAuth2/OIDC providers.

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SSOProviderType(Enum):
    """SSO provider types."""
    SAML = "saml"
    OAUTH2 = "oauth2"
    OIDC = "openid_connect"


class SSOProvider(Base):
    """
    SSO Provider model for storing identity provider configurations.
    
    Supports both SAML 2.0 and OAuth2/OIDC providers.
    """
    __tablename__ = "sso_providers"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic provider information
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), nullable=False)  # SAML, OAUTH2, OIDC
    enabled = Column(Boolean, default=True, nullable=False)
    
    # SAML specific fields
    sso_url = Column(String(500))  # SAML SSO endpoint
    slo_url = Column(String(500))  # SAML Single Logout endpoint
    entity_id = Column(String(500))  # IdP Entity ID
    x509_cert = Column(Text)  # IdP X.509 certificate
    
    # OAuth2/OIDC specific fields
    client_id = Column(String(255))
    client_secret = Column(String(255))  # Should be encrypted in production
    auth_url = Column(String(500))  # Authorization endpoint
    token_url = Column(String(500))  # Token endpoint
    userinfo_url = Column(String(500))  # User info endpoint
    redirect_uri = Column(String(500))  # Callback URL
    scopes = Column(String(500))  # Default scopes
    
    # Configuration and metadata
    metadata = Column(JSON)  # Additional provider-specific configuration
    attribute_mapping = Column(JSON)  # User attribute mapping
    role_mapping = Column(JSON)  # Role mapping from provider groups/roles
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True))
    
    def __repr__(self):
        return f"<SSOProvider(name='{self.name}', type='{self.type}', enabled={self.enabled})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert provider to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'type': self.type,
            'enabled': self.enabled,
            'sso_url': self.sso_url,
            'slo_url': self.slo_url,
            'entity_id': self.entity_id,
            'client_id': self.client_id,
            'auth_url': self.auth_url,
            'token_url': self.token_url,
            'userinfo_url': self.userinfo_url,
            'redirect_uri': self.redirect_uri,
            'scopes': self.scopes,
            'metadata': self.metadata,
            'attribute_mapping': self.attribute_mapping,
            'role_mapping': self.role_mapping,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_azure_ad_provider(
        cls,
        name: str,
        display_name: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> 'SSOProvider':
        """Create Azure AD OAuth2 provider configuration."""
        return cls(
            name=name,
            display_name=display_name,
            description=f"Azure AD tenant: {tenant_id}",
            type=SSOProviderType.OIDC.value,
            client_id=client_id,
            client_secret=client_secret,
            auth_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            redirect_uri=redirect_uri,
            scopes="openid profile email",
            metadata={
                "tenant_id": tenant_id,
                "provider_type": "azure_ad"
            },
            attribute_mapping={
                "email": "mail",
                "first_name": "givenName",
                "last_name": "surname",
                "display_name": "displayName"
            }
        )
    
    @classmethod
    def create_okta_provider(
        cls,
        name: str,
        display_name: str,
        okta_domain: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> 'SSOProvider':
        """Create Okta OAuth2 provider configuration."""
        return cls(
            name=name,
            display_name=display_name,
            description=f"Okta domain: {okta_domain}",
            type=SSOProviderType.OIDC.value,
            client_id=client_id,
            client_secret=client_secret,
            auth_url=f"https://{okta_domain}/oauth2/default/v1/authorize",
            token_url=f"https://{okta_domain}/oauth2/default/v1/token",
            userinfo_url=f"https://{okta_domain}/oauth2/default/v1/userinfo",
            redirect_uri=redirect_uri,
            scopes="openid profile email groups",
            metadata={
                "okta_domain": okta_domain,
                "provider_type": "okta"
            },
            attribute_mapping={
                "email": "email",
                "first_name": "given_name",
                "last_name": "family_name",
                "display_name": "name",
                "groups": "groups"
            }
        )
    
    @classmethod
    def create_google_provider(
        cls,
        name: str,
        display_name: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> 'SSOProvider':
        """Create Google OAuth2 provider configuration."""
        return cls(
            name=name,
            display_name=display_name,
            description="Google Workspace authentication",
            type=SSOProviderType.OIDC.value,
            client_id=client_id,
            client_secret=client_secret,
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            redirect_uri=redirect_uri,
            scopes="openid profile email",
            metadata={
                "provider_type": "google"
            },
            attribute_mapping={
                "email": "email",
                "first_name": "given_name",
                "last_name": "family_name",
                "display_name": "name",
                "picture": "picture"
            }
        )
    
    @classmethod
    def create_saml_provider(
        cls,
        name: str,
        display_name: str,
        entity_id: str,
        sso_url: str,
        x509_cert: str,
        slo_url: Optional[str] = None,
        attribute_mapping: Optional[Dict[str, str]] = None
    ) -> 'SSOProvider':
        """Create SAML 2.0 provider configuration."""
        if attribute_mapping is None:
            attribute_mapping = {
                "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                "display_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
                "groups": "http://schemas.xmlsoap.org/claims/Group"
            }
        
        return cls(
            name=name,
            display_name=display_name,
            description=f"SAML 2.0 provider: {entity_id}",
            type=SSOProviderType.SAML.value,
            entity_id=entity_id,
            sso_url=sso_url,
            slo_url=slo_url,
            x509_cert=x509_cert,
            metadata={
                "provider_type": "saml"
            },
            attribute_mapping=attribute_mapping
        ) 