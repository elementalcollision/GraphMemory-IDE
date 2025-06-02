"""
Advanced Security Middleware for GraphMemory-IDE

This module implements comprehensive security middleware including:
- Security headers injection (CSP, HSTS, X-Frame-Options, etc.)
- CORS policy enforcement
- Input validation enhancement
- Error handling without information leakage
- Request sanitization and validation

Author: GraphMemory-IDE Team
Date: 2025-06-01
"""

import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityConfig:
    """Security configuration for the middleware."""
    
    # Content Security Policy
    CSP_POLICY = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "wss:", "ws:"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "upgrade-insecure-requests": [],
    }
    
    # Allowed origins for CORS
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://yourdomain.com",
    ]
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    }
    
    # Rate limiting for sensitive endpoints
    SENSITIVE_ENDPOINTS = [
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/reset-password",
        "/api/admin",
    ]
    
    # Maximum request size (bytes)
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Blocked user agents (basic bot protection)
    BLOCKED_USER_AGENTS = [
        r".*bot.*",
        r".*crawler.*",
        r".*spider.*",
        r".*scraper.*",
    ]


class RequestValidator:
    """Validates and sanitizes incoming requests."""
    
    @staticmethod
    def validate_json_payload(payload: str, max_depth: int = 10) -> bool:
        """
        Validate JSON payload for security issues.
        
        Args:
            payload: JSON string to validate
            max_depth: Maximum nesting depth allowed
            
        Returns:
            True if valid, False otherwise
        """
        try:
            def check_depth(obj, current_depth=0) -> None:
                if current_depth > max_depth:
                    return False
                
                if isinstance(obj, dict):
                    return all(check_depth(v, current_depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return all(check_depth(item, current_depth + 1) for item in obj)
                
                return True
            
            parsed = json.loads(payload)
            return check_depth(parsed)
            
        except (json.JSONDecodeError, RecursionError):
            return False
    
    @staticmethod
    def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Remove potentially dangerous headers."""
        dangerous_headers = {
            "x-forwarded-host",
            "x-forwarded-server",
            "x-real-ip",
        }
        
        return {
            key: value for key, value in headers.items()
            if key.lower() not in dangerous_headers
        }
    
    @staticmethod
    def validate_content_type(content_type: str, allowed_types: List[str]) -> bool:
        """Validate content type against allowed types."""
        if not content_type:
            return False
        
        content_type = content_type.lower().split(';')[0].strip()
        return content_type in [t.lower() for t in allowed_types]
    
    @staticmethod
    def check_suspicious_patterns(data: str) -> List[str]:
        """Check for suspicious patterns in request data."""
        suspicious_patterns = [
            (r"<script[^>]*>.*?</script>", "XSS attempt"),
            (r"javascript:", "JavaScript protocol"),
            (r"data:text/html", "Data URI HTML"),
            (r"vbscript:", "VBScript protocol"),
            (r"on\w+\s*=", "Event handler"),
            (r"expression\s*\(", "CSS expression"),
            (r"@import", "CSS import"),
            (r"\\x[0-9a-fA-F]{2}", "Hex encoding"),
            (r"%[0-9a-fA-F]{2}", "URL encoding"),
        ]
        
        findings = []
        for pattern, description in suspicious_patterns:
            if re.search(pattern, data, re.IGNORECASE | re.DOTALL):
                findings.append(description)
        
        return findings


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for FastAPI applications.
    
    Features:
    - Security headers injection
    - Request validation and sanitization
    - Content Security Policy enforcement
    - Input validation
    - Error handling without information disclosure
    """
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityConfig] = None) -> None:
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.validator = RequestValidator()
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header."""
        csp_parts = []
        for directive, sources in self.config.CSP_POLICY.items():
            if sources:
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(directive)
        
        return "; ".join(csp_parts)
    
    def _is_safe_origin(self, origin: str) -> bool:
        """Check if origin is in the allowed list."""
        if not origin:
            return False
        
        # Parse the origin URL
        try:
            parsed = urlparse(origin)
            origin_normalized = f"{parsed.scheme}://{parsed.netloc}"
            return origin_normalized in self.config.CORS_ALLOWED_ORIGINS
        except Exception:
            return False
    
    def _check_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is blocked."""
        if not user_agent:
            return True  # Allow empty user agents
        
        user_agent_lower = user_agent.lower()
        for pattern in self.config.BLOCKED_USER_AGENTS:
            if re.match(pattern, user_agent_lower):
                return False
        
        return True
    
    async def _validate_request_size(self, request: Request) -> bool:
        """Validate request size."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                return size <= self.config.MAX_REQUEST_SIZE
            except ValueError:
                return False
        
        return True
    
    async def _validate_request_content(self, request: Request) -> tuple[bool, Optional[str]]:
        """Validate request content for security issues."""
        content_type = request.headers.get("content-type", "")
        
        # Skip validation for certain content types
        if any(ct in content_type.lower() for ct in ["multipart/", "application/octet-stream"]):
            return True, None
        
        # Validate JSON content
        if "application/json" in content_type.lower():
            try:
                body = await request.body()
                body_str = body.decode("utf-8")
                
                # Check JSON structure
                if not self.validator.validate_json_payload(body_str):
                    return False, "Invalid JSON structure or depth"
                
                # Check for suspicious patterns
                suspicious = self.validator.check_suspicious_patterns(body_str)
                if suspicious:
                    return False, f"Suspicious content detected: {', '.join(suspicious)}"
                
            except Exception as e:
                return False, f"Content validation error: {str(e)}"
        
        return True, None
    
    def _add_security_headers(self, response) -> None:
        """Add security headers to response."""
        # Add CSP header
        response.headers["Content-Security-Policy"] = self._build_csp_header()
        
        # Add other security headers
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add custom headers
        response.headers["X-Powered-By"] = "GraphMemory-IDE"
        response.headers["Server"] = "GraphMemory-IDE/1.0"
    
    def _create_error_response(self, status_code: int, message: str, detail: Optional[str] = None) -> JSONResponse:
        """Create standardized error response without information leakage."""
        content = {
            "error": True,
            "message": message,
            "status": status_code,
        }
        
        # Only include detail in development mode
        if detail and hasattr(self.config, 'DEBUG') and self.config.DEBUG:
            content["detail"] = detail
        
        return JSONResponse(
            status_code=status_code,
            content=content,
            headers={"Content-Type": "application/json"}
        )
    
    async def dispatch(self, request: Request, call_next) -> None:
        """Process request through security middleware."""
        try:
            # Skip security checks for health endpoints
            if request.url.path in ["/health", "/metrics"]:
                return await call_next(request)
            
            # Check user agent
            user_agent = request.headers.get("user-agent", "")
            if not self._check_user_agent(user_agent):
                return self._create_error_response(
                    403, "Access denied", "Blocked user agent"
                )
            
            # Validate request size
            if not await self._validate_request_size(request):
                return self._create_error_response(
                    413, "Request too large", "Request exceeds maximum size limit"
                )
            
            # Validate CORS origin
            origin = request.headers.get("origin")
            if origin and not self._is_safe_origin(origin):
                return self._create_error_response(
                    403, "CORS policy violation", f"Origin not allowed: {origin}"
                )
            
            # Validate request content
            content_valid, content_error = await self._validate_request_content(request)
            if not content_valid:
                return self._create_error_response(
                    400, "Invalid request content", content_error
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            return self._create_error_response(
                e.status_code, 
                e.detail if e.detail else "HTTP error occurred"
            )
        
        except Exception as e:
            # Handle unexpected errors without exposing details
            return self._create_error_response(
                500, 
                "Internal server error", 
                str(e) if hasattr(self.config, 'DEBUG') and self.config.DEBUG else None
            )


class EnhancedCORSMiddleware(CORSMiddleware):
    """Enhanced CORS middleware with additional security features."""
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_credentials: bool = False,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 600,
        allow_origin_regex: str = None,
    ) -> None:
        # Default secure configuration
        if allow_origins is None:
            allow_origins = SecurityConfig.CORS_ALLOWED_ORIGINS
        
        if allow_methods is None:
            allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
        
        if allow_headers is None:
            allow_headers = [
                "accept",
                "accept-language",
                "content-language",
                "content-type",
                "authorization",
                "x-api-key",
                "x-requested-with",
            ]
        
        if expose_headers is None:
            expose_headers = [
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-reset",
            ]
        
        super().__init__(
            app=app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            expose_headers=expose_headers,
            max_age=max_age,
            allow_origin_regex=allow_origin_regex,
        )


def create_security_middleware(app: ASGIApp, debug: bool = False) -> ASGIApp:
    """
    Create and configure security middleware stack.
    
    Args:
        app: FastAPI application
        debug: Enable debug mode (exposes error details)
        
    Returns:
        App with security middleware applied
    """
    # Configure security
    config = SecurityConfig()
    if debug:
        config.DEBUG = debug
    
    # Apply security middleware
    app = SecurityMiddleware(app, config)
    
    # Apply enhanced CORS middleware
    app = EnhancedCORSMiddleware(app)
    
    return app 