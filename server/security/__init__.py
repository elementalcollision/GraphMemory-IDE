"""
GraphMemory IDE Security Module

This module provides comprehensive security management including:
- JWT token management with EdDSA algorithm
- API key generation and lifecycle management  
- Database credential management with rotation
- SSL certificate management with automated renewal
- Secrets storage and encryption
- Security audit logging and compliance
"""

from .key_storage import SecureKeyStorage, FilesystemKeyStorage, KeyMetadata
from .secrets_manager import (
    SecretsManager, APIKeyManager, APIKeyConfig,
    SecretType, Environment, SecretStatus, SecretMetadata, PermissionScope
)
from .database_credential_manager import (
    DatabaseCredentialManager, DatabaseCredential, DatabaseType, 
    CredentialType, ConnectionSecurityMode
)
from .ssl_certificate_manager import (
    SSLCertificateManager, SSLCertificate, CertificateType,
    CertificateAuthority, CertificateStatus
)
from .audit_logger import (
    SecurityAuditLogger, AuditEvent, AuditLevel, AuditEventType,
    ComplianceFramework, get_audit_logger
)

__all__ = [
    # Key Storage
    'SecureKeyStorage',
    'FilesystemKeyStorage', 
    'KeyMetadata',
    
    # Secrets Management
    'SecretsManager',
    'APIKeyManager',
    'APIKeyConfig',
    'SecretType',
    'Environment',
    'SecretStatus', 
    'SecretMetadata',
    'PermissionScope',
    
    # Database Credentials
    'DatabaseCredentialManager',
    'DatabaseCredential',
    'DatabaseType',
    'CredentialType',
    'ConnectionSecurityMode',
    
    # SSL Certificates
    'SSLCertificateManager',
    'SSLCertificate',
    'CertificateType',
    'CertificateAuthority',
    'CertificateStatus',
    
    # Audit Logging
    'SecurityAuditLogger',
    'AuditEvent',
    'AuditLevel',
    'AuditEventType',
    'ComplianceFramework',
    'get_audit_logger'
]

__version__ = "1.0.0" 