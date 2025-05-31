# Task: Production Environment Configuration & SSL Setup
---
title: Production Environment Configuration & SSL Setup
type: task
status: active
created: 2025-01-29T12:41:19
updated: 2025-01-29T12:45:00
id: TASK-018
priority: high
dependencies: []
memory_types: [procedural, semantic]
assignee: developer
estimated_time: 1-2 days
tags: [production, ssl, security, deployment, infrastructure]
---

## Description
Configure production environment settings, SSL certificates, domain setup, and production-specific configurations for GraphMemory-IDE. This includes setting up secure communication protocols, proper environment variables, and production-grade security headers.

## Production-Ready Implementation Plan

### Phase 1: SSL Certificate & Domain Configuration (4-6 hours)

#### 1. SSL Certificate Setup
Based on current best practices for FastAPI production deployment:

**Option A: Let's Encrypt (Recommended)**
```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Generate certificate for domain
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Certificate files will be in:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

**Option B: Commercial Certificate**
- Purchase from DigiCert, GoDaddy, or similar CA
- Generate CSR and private key
- Install certificate files

#### 2. Domain Configuration
```bash
# DNS A Record configuration (in DNS provider)
yourdomain.com       A    YOUR_SERVER_IP
www.yourdomain.com   A    YOUR_SERVER_IP

# Verify DNS propagation
dig yourdomain.com
nslookup yourdomain.com
```

### Phase 2: Production FastAPI Configuration (3-4 hours)

#### 1. Environment Configuration
Create `production.env`:
```bash
# Server Configuration
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-super-secure-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# SSL Configuration
SSL_CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem

# Database Configuration (Production)
DATABASE_URL=postgresql://username:password@db-host:5432/production_db
REDIS_URL=redis://redis-host:6379/0

# Security Headers
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

#### 2. FastAPI Production Settings
Update `server/core/config.py`:
```python
from pydantic import BaseSettings, validator
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Server
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # SSL
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["yourdomain.com", "www.yourdomain.com"]
    CORS_ORIGINS: List[str] = ["https://yourdomain.com"]
    
    # Database
    DATABASE_URL: str
    REDIS_URL: str
    
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

#### 3. Security Middleware Implementation
Create `server/middleware/security.py`:
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Security Headers
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        return response

def setup_security_middleware(app: FastAPI, settings):
    """Setup all security middleware"""
    
    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Custom Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
```

### Phase 3: Reverse Proxy Configuration (2-3 hours)

#### 1. Nginx Configuration
Create `/etc/nginx/sites-available/graphmemory-ide`:
```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Configuration
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Main API Location
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket Support for Collaboration
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static Files (if any)
    location /static/ {
        alias /var/www/graphmemory-ide/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health Check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

#### 2. Enable Nginx Configuration
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/graphmemory-ide /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Phase 4: Production Monitoring Setup (3-4 hours)

#### 1. Prometheus Metrics Integration
Add to `server/main.py`:
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP Requests', 
    ['method', 'status', 'path']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 
    'HTTP Request Duration', 
    ['method', 'status', 'path']
)
REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress', 
    'HTTP Requests in progress', 
    ['method', 'path']
)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    method = request.method
    path = request.url.path
    
    REQUEST_IN_PROGRESS.labels(method=method, path=path).inc()
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    status = response.status_code
    
    REQUEST_COUNT.labels(method=method, status=status, path=path).inc()
    REQUEST_LATENCY.labels(method=method, status=status, path=path).observe(duration)
    REQUEST_IN_PROGRESS.labels(method=method, path=path).dec()
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

#### 2. Health Check Endpoint
```python
from fastapi import HTTPException
import asyncio
import psutil

@app.get("/health")
async def health_check():
    """Production health check endpoint"""
    try:
        # Check database connectivity
        async with database.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis connectivity
        await redis_client.ping()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "database": "connected",
            "redis": "connected",
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
```

### Phase 5: Automated Certificate Renewal (1 hour)

#### 1. Certbot Auto-renewal
```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab for automatic renewal
sudo crontab -e

# Add this line:
0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

### Phase 6: Production Deployment Script (1 hour)

Create `deploy/production_deploy.sh`:
```bash
#!/bin/bash

set -e

# Production deployment script for GraphMemory-IDE

echo "🚀 Starting production deployment..."

# Variables
DOMAIN="yourdomain.com"
EMAIL="admin@yourdomain.com"
APP_DIR="/var/www/graphmemory-ide"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y nginx certbot python3-certbot-nginx

# Setup SSL certificate
echo "🔐 Setting up SSL certificate..."
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email

# Configure Nginx
echo "⚙️ Configuring Nginx..."
sudo cp nginx/graphmemory-ide.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/graphmemory-ide /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Setup systemd service
echo "🔄 Setting up systemd service..."
sudo cp systemd/graphmemory-ide.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable graphmemory-ide
sudo systemctl start graphmemory-ide

# Setup log rotation
echo "📝 Setting up log rotation..."
sudo cp logrotate/graphmemory-ide /etc/logrotate.d/

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "✅ Production deployment completed successfully!"
echo "🌐 Your application is now available at: https://$DOMAIN"
```

## Objectives
- Set up SSL/TLS certificates for secure HTTPS communication
- Configure production domain settings and DNS
- Implement production environment variables and secrets management
- Enable security headers and CORS policies for production
- Configure production-specific FastAPI settings
- Set up production-grade logging and error handling

## Steps
- [x] Research production best practices for FastAPI deployment
- [x] Design SSL certificate management strategy (Let's Encrypt)
- [x] Create production environment configuration structure
- [x] Design security middleware implementation
- [x] Plan Nginx reverse proxy configuration
- [x] Design monitoring and health check endpoints
- [x] Create automated certificate renewal setup
- [x] Design production deployment automation
- [ ] Generate and configure SSL certificates (Let's Encrypt or commercial)
- [ ] Set up production domain DNS configuration
- [ ] Create production environment configuration files
- [ ] Configure HTTPS redirect and security headers middleware
- [ ] Set up production-specific CORS policies
- [ ] Configure production database connection strings
- [ ] Set up production Redis configuration
- [ ] Configure production logging levels and formats
- [ ] Implement production error handling and monitoring
- [ ] Test SSL certificate validation and renewal
- [ ] Validate security headers with security scanners
- [ ] Document production deployment procedures

## Progress
🎯 **Implementation Plan Complete** - Comprehensive production-ready configuration plan developed

### Research Summary:
- **SSL Strategy**: Let's Encrypt with automated renewal (recommended)
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-XSS-Protection
- **Reverse Proxy**: Nginx with rate limiting and WebSocket support
- **Monitoring**: Prometheus metrics with health checks
- **Deployment**: Automated scripts with systemd service management

### Key Technical Decisions:
1. **Let's Encrypt** for SSL certificates (free, automated renewal)
2. **Nginx** as reverse proxy with security headers and rate limiting
3. **Prometheus** integration for production monitoring
4. **Systemd** for service management and auto-restart
5. **Security middleware** for CORS, CSP, and security headers

## Dependencies
- Docker configuration must be complete
- Domain registration and DNS access required
- Production server infrastructure must be available

## Code Context
- file: server/main.py
  relevance: 0.9
  sections: [1-50]
  reason: "Main FastAPI application configuration that needs production settings"
- file: server/core/config.py
  relevance: 0.9
  sections: [all]
  reason: "Configuration management that needs production environment settings"
- file: server/middleware/
  relevance: 0.8
  sections: [all]
  reason: "Middleware components for security headers and HTTPS enforcement"
- file: deploy/
  relevance: 0.9
  sections: [all]
  reason: "Deployment scripts and configuration files"

## Notes
- Use environment-specific configuration patterns from FastAPI best practices
- Implement proper secrets management (never commit secrets to git)
- Consider using Docker secrets or Kubernetes secrets for production
- SSL certificate auto-renewal should be automated (certbot for Let's Encrypt)
- Security headers should include HSTS, CSP, X-Frame-Options, etc.
- Follow OWASP security guidelines for production deployments

## Next Steps
1. Execute Phase 1: SSL Certificate & Domain Configuration
2. Implement Phase 2: Production FastAPI Configuration
3. Set up Phase 3: Reverse Proxy Configuration
4. Deploy Phase 4: Production Monitoring Setup
5. Configure Phase 5: Automated Certificate Renewal
6. Run Phase 6: Production Deployment Script

## Completion Notes
📋 **Comprehensive Implementation Plan Created**

**Production Readiness Features Planned:**
- ✅ SSL/TLS with Let's Encrypt automation
- ✅ Security headers and CORS configuration
- ✅ Nginx reverse proxy with rate limiting
- ✅ Prometheus monitoring integration
- ✅ Health check endpoints
- ✅ Automated deployment scripts
- ✅ Certificate renewal automation
- ✅ Production environment management

**Estimated Implementation Time:** 1-2 days (16-20 hours total)
**Security Level:** Enterprise-grade with OWASP compliance
**Monitoring Level:** Production-ready with Prometheus metrics
**Automation Level:** Fully automated deployment and certificate management 