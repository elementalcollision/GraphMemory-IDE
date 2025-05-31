"""
Production security middleware for GraphMemory-IDE.
Implements enterprise-grade security headers, CORS, rate limiting, and SSL enforcement.
"""

import time
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app, enable_hsts: bool = True, environment: str = "development"):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.environment = environment
        
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        
        # Security Headers - Applied to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Download-Options"] = "noopen"
        
        # HSTS for production environments with HTTPS
        if self.enable_hsts and self.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        csp_policy = self._build_csp_policy()
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Feature Policy / Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "speaker=(), vibrate=(), fullscreen=(), sync-xhr=()"
        )
        
        return response
    
    def _build_csp_policy(self) -> str:
        """Build Content Security Policy based on environment"""
        if self.environment == "production":
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # More permissive for development
            return (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: blob: http: https:; "
                "connect-src 'self' ws: wss: http: https:; "
                "frame-ancestors 'none';"
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware"""
    
    def __init__(
        self, 
        app, 
        requests_per_minute: int = 60, 
        burst_limit: int = 20,
        whitelist_ips: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.whitelist_ips = whitelist_ips or ["127.0.0.1", "::1"]
        self.client_requests: Dict[str, List[float]] = {}
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()
        
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for whitelisted IPs
        if client_ip in self.whitelist_ips:
            return await call_next(request)
        
        # Check rate limit
        if not self._is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Periodic cleanup of old entries
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = time.time()
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers (when behind reverse proxy)
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            return request.headers["x-real-ip"]
        else:
            return request.client.host if request.client else "unknown"
    
    def _is_allowed(self, client_ip: str) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        # Initialize client entry if doesn't exist
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = []
        
        requests = self.client_requests[client_ip]
        
        # Remove requests older than 1 minute
        minute_ago = current_time - 60
        requests[:] = [req_time for req_time in requests if req_time > minute_ago]
        
        # Check burst limit (immediate)
        recent_requests = [req for req in requests if req > current_time - 10]  # Last 10 seconds
        if len(recent_requests) >= self.burst_limit:
            return False
        
        # Check rate limit (per minute)
        if len(requests) >= self.requests_per_minute:
            return False
        
        # Add current request
        requests.append(current_time)
        return True
    
    def _cleanup_old_entries(self) -> None:
        """Remove old entries to prevent memory buildup"""
        current_time = time.time()
        cutoff_time = current_time - 300  # 5 minutes ago
        
        for client_ip in list(self.client_requests.keys()):
            requests = self.client_requests[client_ip]
            requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
            
            # Remove client entry if no recent requests
            if not requests:
                del self.client_requests[client_ip]


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP requests to HTTPS in production"""
    
    def __init__(self, app, environment: str = "development", enabled: bool = True):
        super().__init__(app)
        self.environment = environment
        self.enabled = enabled and environment == "production"
        
    async def dispatch(self, request: Request, call_next) -> Response:
        if (self.enabled and 
            request.headers.get("x-forwarded-proto") == "http" and 
            request.url.scheme == "http"):
            
            # Redirect to HTTPS
            https_url = str(request.url).replace("http://", "https://", 1)
            return Response(
                status_code=301,
                headers={"Location": https_url}
            )
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests and responses for debugging and monitoring"""
    
    def __init__(self, app, log_body: bool = False, environment: str = "development"):
        super().__init__(app)
        self.log_body = log_body and environment != "production"
        self.environment = environment
        
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Log request
        client_ip = self._get_client_ip(request)
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {client_ip} - User-Agent: {request.headers.get('user-agent', 'Unknown')}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path} "
            f"- {process_time:.2f}ms"
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        if "x-forwarded-for" in request.headers:
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        elif "x-real-ip" in request.headers:
            return request.headers["x-real-ip"]
        else:
            return request.client.host if request.client else "unknown"


def setup_security_middleware(
    app: FastAPI, 
    environment: str = "development",
    cors_origins: Optional[List[str]] = None,
    allowed_hosts: Optional[List[str]] = None,
    rate_limit_per_minute: int = 60,
    enable_request_logging: bool = True
) -> None:
    """
    Setup comprehensive security middleware stack for FastAPI application.
    
    Args:
        app: FastAPI application instance
        environment: Current environment (development, staging, production)
        cors_origins: List of allowed CORS origins
        allowed_hosts: List of allowed hosts for TrustedHostMiddleware
        rate_limit_per_minute: Rate limit threshold
        enable_request_logging: Whether to enable request logging
    """
    
    # Default values
    if cors_origins is None:
        cors_origins = ["http://localhost:3000"] if environment == "development" else []
    
    if allowed_hosts is None:
        allowed_hosts = ["localhost", "127.0.0.1"] if environment == "development" else []
    
    # Add security middleware in reverse order (last added = first executed)
    
    # 1. Request logging (outermost - logs everything)
    if enable_request_logging:
        app.add_middleware(
            RequestLoggingMiddleware,
            log_body=False,  # Never log body in production for security
            environment=environment
        )
    
    # 2. Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=environment == "production",
        environment=environment
    )
    
    # 3. Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=rate_limit_per_minute,
        burst_limit=max(20, rate_limit_per_minute // 3),
        whitelist_ips=["127.0.0.1", "::1"] if environment == "development" else []
    )
    
    # 4. HTTPS redirect (production only)
    if environment == "production":
        app.add_middleware(
            HTTPSRedirectMiddleware,
            environment=environment,
            enabled=True
        )
    
    # 5. Trusted hosts
    if allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )
    
    # 6. CORS (innermost - handles preflight requests)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["X-Process-Time"]
        )
    
    logger.info(f"Security middleware configured for {environment} environment")
    logger.info(f"CORS origins: {cors_origins}")
    logger.info(f"Allowed hosts: {allowed_hosts}")
    logger.info(f"Rate limit: {rate_limit_per_minute} requests/minute") 