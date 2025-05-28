"""
mTLS Configuration Module for GraphMemory-IDE MCP Server

This module provides SSL context configuration for mutual TLS (mTLS) authentication.
It supports both development and production certificate management.
"""

import ssl
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MTLSConfig:
    """Configuration class for mTLS setup"""
    
    def __init__(self, cert_dir: str = "./certs"):
        self.cert_dir = Path(cert_dir)
        self.ca_cert_path = self.cert_dir / "ca-cert.pem"
        self.server_cert_path = self.cert_dir / "server-cert.pem"
        self.server_key_path = self.cert_dir / "server-key.pem"
        self.client_cert_path = self.cert_dir / "client-cert.pem"
        self.client_key_path = self.cert_dir / "client-key.pem"
    
    def validate_certificates(self) -> bool:
        """Validate that all required certificate files exist"""
        required_files = [
            self.ca_cert_path,
            self.server_cert_path,
            self.server_key_path
        ]
        
        for cert_file in required_files:
            if not cert_file.exists():
                logger.error(f"Required certificate file not found: {cert_file}")
                return False
            
            # Check file permissions
            stat = cert_file.stat()
            if cert_file.name.endswith("-key.pem") and (stat.st_mode & 0o077) != 0:
                logger.warning(f"Private key file {cert_file} has overly permissive permissions")
        
        logger.info("All required certificate files found and validated")
        return True
    
    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for mTLS server"""
        if not self.validate_certificates():
            raise ValueError("Certificate validation failed")
        
        # Create SSL context for server
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # Load server certificate and key
        try:
            context.load_cert_chain(
                certfile=str(self.server_cert_path),
                keyfile=str(self.server_key_path)
            )
            logger.info("Server certificate and key loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load server certificate: {e}")
            raise
        
        # Load CA certificate for client verification
        try:
            context.load_verify_locations(str(self.ca_cert_path))
            logger.info("CA certificate loaded for client verification")
        except Exception as e:
            logger.error(f"Failed to load CA certificate: {e}")
            raise
        
        # Require client certificates
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Set minimum TLS version
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Set maximum TLS version (optional, for compatibility)
        # context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        # Set cipher suites (secure ones only)
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        # Additional security options
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        context.options |= ssl.OP_SINGLE_DH_USE
        context.options |= ssl.OP_SINGLE_ECDH_USE
        
        logger.info("SSL context configured with mTLS requirements")
        return context
    
    def create_client_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for mTLS client"""
        if not self.client_cert_path.exists() or not self.client_key_path.exists():
            raise ValueError("Client certificate files not found")
        
        # Create SSL context for client
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Load client certificate and key
        context.load_cert_chain(
            certfile=str(self.client_cert_path),
            keyfile=str(self.client_key_path)
        )
        
        # Load CA certificate for server verification
        context.load_verify_locations(str(self.ca_cert_path))
        
        # Set minimum TLS version
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        logger.info("Client SSL context configured for mTLS")
        return context


def is_mtls_enabled() -> bool:
    """Check if mTLS is enabled via environment variable"""
    return os.getenv("MTLS_ENABLED", "false").lower() == "true"


def get_mtls_port() -> int:
    """Get mTLS port from environment"""
    return int(os.getenv("MTLS_PORT", "50051"))


def get_cert_directory() -> str:
    """Get certificate directory from environment"""
    return os.getenv("MTLS_CERT_DIR", "./certs")


def create_mtls_context(cert_dir: Optional[str] = None) -> Optional[ssl.SSLContext]:
    """
    Create mTLS SSL context if mTLS is enabled
    
    Args:
        cert_dir: Optional certificate directory path
        
    Returns:
        SSL context if mTLS is enabled, None otherwise
    """
    if not is_mtls_enabled():
        logger.info("mTLS is disabled")
        return None
    
    cert_dir = cert_dir or get_cert_directory()
    mtls_config = MTLSConfig(cert_dir)
    
    try:
        context = mtls_config.create_ssl_context()
        logger.info(f"mTLS enabled on port {get_mtls_port()}")
        return context
    except Exception as e:
        logger.error(f"Failed to create mTLS context: {e}")
        raise


def verify_client_certificate(cert_der: bytes) -> dict:
    """
    Verify and extract information from client certificate
    
    Args:
        cert_der: DER-encoded client certificate
        
    Returns:
        Dictionary with certificate information
    """
    import ssl
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    
    try:
        # Parse certificate
        cert = x509.load_der_x509_certificate(cert_der, default_backend())
        
        # Extract subject information
        subject = cert.subject
        subject_dict = {}
        for attribute in subject:
            subject_dict[attribute.oid._name] = attribute.value
        
        # Extract validity period
        not_before = cert.not_valid_before
        not_after = cert.not_valid_after
        
        # Extract serial number
        serial_number = cert.serial_number
        
        return {
            "subject": subject_dict,
            "serial_number": serial_number,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "is_valid": not_before <= cert.not_valid_before <= not_after
        }
    except Exception as e:
        logger.error(f"Failed to verify client certificate: {e}")
        return {"error": str(e)}


# Configuration constants
DEFAULT_MTLS_PORT = 50051
DEFAULT_CERT_DIR = "./certs"
SUPPORTED_TLS_VERSIONS = [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3]
SECURE_CIPHER_SUITES = 'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS' 