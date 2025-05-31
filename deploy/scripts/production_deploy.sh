#!/bin/bash

set -e  # Exit on any error

# Production deployment script for GraphMemory-IDE
# Automates SSL setup, configuration, and service deployment

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
DOMAIN="${DOMAIN:-graphmemory-ide.com}"
EMAIL="${EMAIL:-admin@graphmemory-ide.com}"
APP_DIR="${APP_DIR:-/var/www/graphmemory-ide}"
APP_USER="${APP_USER:-graphmemory}"
DB_PASSWORD="${DB_PASSWORD}"
JWT_SECRET="${JWT_SECRET}"
ENVIRONMENT="production"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Validate required environment variables
validate_environment() {
    log "🔍 Validating environment configuration..."
    
    if [[ -z "$DB_PASSWORD" ]]; then
        error "DB_PASSWORD environment variable is required"
    fi
    
    if [[ -z "$JWT_SECRET" ]]; then
        error "JWT_SECRET environment variable is required"
    fi
    
    # Check domain DNS resolution
    if ! nslookup "$DOMAIN" > /dev/null 2>&1; then
        warn "Domain $DOMAIN does not resolve. Ensure DNS is configured correctly."
    fi
    
    log "✅ Environment validation completed"
}

# Update system packages
update_system() {
    log "📦 Updating system packages..."
    
    apt update
    apt upgrade -y
    apt autoremove -y
    
    log "✅ System packages updated"
}

# Install required dependencies
install_dependencies() {
    log "🔧 Installing dependencies..."
    
    # Install essential packages
    apt install -y \
        nginx \
        certbot \
        python3-certbot-nginx \
        postgresql-client \
        redis-tools \
        curl \
        wget \
        git \
        htop \
        ufw \
        fail2ban \
        logrotate \
        supervisor
    
    # Install Python dependencies
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential
    
    log "✅ Dependencies installed"
}

# Create application user
create_app_user() {
    log "👤 Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
        log "✅ User $APP_USER created"
    else
        info "User $APP_USER already exists"
    fi
}

# Setup application directory
setup_app_directory() {
    log "📁 Setting up application directory..."
    
    # Create directories
    mkdir -p "$APP_DIR"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/static"
    mkdir -p "$APP_DIR/data"
    mkdir -p "/var/www/graphmemory-ide/errors"
    
    # Set permissions
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chmod -R 755 "$APP_DIR"
    
    log "✅ Application directory setup completed"
}

# Setup SSL certificate
setup_ssl() {
    log "🔐 Setting up SSL certificate..."
    
    # Stop nginx if running
    systemctl stop nginx 2>/dev/null || true
    
    # Generate certificate using standalone mode
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --domains "$DOMAIN,www.$DOMAIN"
    
    # Test certificate renewal
    certbot renew --dry-run
    
    log "✅ SSL certificate setup completed"
}

# Configure Nginx
configure_nginx() {
    log "⚙️ Configuring Nginx..."
    
    # Copy production configuration
    cp "$(dirname "$0")/../nginx/production.conf" "/etc/nginx/sites-available/graphmemory-ide"
    
    # Update domain in configuration
    sed -i "s/graphmemory-ide\.com/$DOMAIN/g" "/etc/nginx/sites-available/graphmemory-ide"
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/graphmemory-ide" "/etc/nginx/sites-enabled/"
    
    # Remove default site
    rm -f "/etc/nginx/sites-enabled/default"
    
    # Test configuration
    nginx -t
    
    # Enable and start nginx
    systemctl enable nginx
    systemctl start nginx
    
    log "✅ Nginx configuration completed"
}

# Setup application environment
setup_app_environment() {
    log "🌍 Setting up application environment..."
    
    # Create production environment file
    cat > "$APP_DIR/.env" << EOF
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=False

# Security
SECRET_KEY=${JWT_SECRET}
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
HOST=127.0.0.1
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql://graphmemory:${DB_PASSWORD}@localhost:5432/graphmemory_production
REDIS_URL=redis://localhost:6379/0
KUZU_DB_PATH=${APP_DIR}/data/kuzu

# Security Headers
CORS_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
EOF
    
    # Set secure permissions
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    log "✅ Application environment setup completed"
}

# Setup systemd service
setup_systemd_service() {
    log "🔄 Setting up systemd service..."
    
    cat > "/etc/systemd/system/graphmemory-ide.service" << EOF
[Unit]
Description=GraphMemory-IDE Production Server
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin
ExecStart=$APP_DIR/.venv/bin/gunicorn server.main:app \\
    --bind 127.0.0.1:8000 \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --timeout 30 \\
    --keepalive 5 \\
    --preload \\
    --log-level info \\
    --access-logfile $APP_DIR/logs/access.log \\
    --error-logfile $APP_DIR/logs/error.log
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=graphmemory-ide

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$APP_DIR
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable graphmemory-ide
    
    log "✅ Systemd service setup completed"
}

# Setup log rotation
setup_log_rotation() {
    log "📝 Setting up log rotation..."
    
    cat > "/etc/logrotate.d/graphmemory-ide" << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $APP_USER $APP_USER
    postrotate
        systemctl reload graphmemory-ide
    endscript
}

/var/log/nginx/graphmemory-ide.*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
    postrotate
        systemctl reload nginx
    endscript
}
EOF
    
    log "✅ Log rotation setup completed"
}

# Configure firewall
configure_firewall() {
    log "🔥 Configuring firewall..."
    
    # Reset firewall
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow essential services
    ufw allow OpenSSH
    ufw allow 'Nginx Full'
    
    # Allow database connections (if external)
    # ufw allow from 10.0.0.0/8 to any port 5432
    
    # Enable firewall
    ufw --force enable
    
    log "✅ Firewall configuration completed"
}

# Setup monitoring
setup_monitoring() {
    log "📊 Setting up monitoring..."
    
    # Install prometheus node exporter
    wget -O /tmp/node_exporter.tar.gz \
        https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
    
    tar -xzf /tmp/node_exporter.tar.gz -C /tmp/
    mv /tmp/node_exporter-*/node_exporter /usr/local/bin/
    
    # Create node exporter service
    cat > "/etc/systemd/system/node_exporter.service" << EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF
    
    # Create user and enable service
    useradd -r -s /bin/false node_exporter
    systemctl daemon-reload
    systemctl enable node_exporter
    systemctl start node_exporter
    
    log "✅ Monitoring setup completed"
}

# Setup automatic certificate renewal
setup_cert_renewal() {
    log "🔄 Setting up automatic certificate renewal..."
    
    # Add renewal cron job
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --deploy-hook 'systemctl reload nginx'") | crontab -
    
    log "✅ Automatic certificate renewal setup completed"
}

# Create error pages
create_error_pages() {
    log "📄 Creating custom error pages..."
    
    # 404 page
    cat > "/var/www/graphmemory-ide/errors/404.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #333; }
        p { color: #666; }
    </style>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The requested page could not be found.</p>
    <p><a href="/">Return to Home</a></p>
</body>
</html>
EOF
    
    # 50x page
    cat > "/var/www/graphmemory-ide/errors/50x.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>500 - Internal Server Error</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #333; }
        p { color: #666; }
    </style>
</head>
<body>
    <h1>500 - Internal Server Error</h1>
    <p>Something went wrong on our end. Please try again later.</p>
    <p><a href="/">Return to Home</a></p>
</body>
</html>
EOF
    
    chown -R www-data:www-data "/var/www/graphmemory-ide/errors"
    
    log "✅ Error pages created"
}

# Start services
start_services() {
    log "🚀 Starting services..."
    
    # Start and enable services
    systemctl start postgresql redis-server
    systemctl enable postgresql redis-server
    
    # Start application
    systemctl start graphmemory-ide
    
    # Restart nginx to ensure everything is working
    systemctl restart nginx
    
    log "✅ Services started"
}

# Verify deployment
verify_deployment() {
    log "✅ Verifying deployment..."
    
    # Test HTTPS
    if curl -f -s "https://$DOMAIN/health" > /dev/null; then
        log "✅ HTTPS health check passed"
    else
        warn "HTTPS health check failed"
    fi
    
    # Test SSL certificate
    if echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -issuer | grep -q "Let's Encrypt"; then
        log "✅ SSL certificate verified"
    else
        warn "SSL certificate verification failed"
    fi
    
    # Check services
    systemctl is-active --quiet graphmemory-ide && log "✅ GraphMemory-IDE service is running" || warn "GraphMemory-IDE service is not running"
    systemctl is-active --quiet nginx && log "✅ Nginx service is running" || warn "Nginx service is not running"
    systemctl is-active --quiet postgresql && log "✅ PostgreSQL service is running" || warn "PostgreSQL service is not running"
    systemctl is-active --quiet redis-server && log "✅ Redis service is running" || warn "Redis service is not running"
    
    log "✅ Deployment verification completed"
}

# Main deployment function
main() {
    log "🚀 Starting GraphMemory-IDE production deployment..."
    
    check_root
    validate_environment
    update_system
    install_dependencies
    create_app_user
    setup_app_directory
    setup_ssl
    configure_nginx
    setup_app_environment
    setup_systemd_service
    setup_log_rotation
    configure_firewall
    setup_monitoring
    setup_cert_renewal
    create_error_pages
    start_services
    verify_deployment
    
    log "🎉 Production deployment completed successfully!"
    log "🌐 Your application is now available at: https://$DOMAIN"
    log "📊 Metrics available at: https://$DOMAIN/metrics (restricted access)"
    log "❤️ Health check available at: https://$DOMAIN/health"
    
    info "Next steps:"
    info "1. Configure your database schema"
    info "2. Set up monitoring dashboards"
    info "3. Configure backup procedures"
    info "4. Set up log aggregation"
    info "5. Run security audit"
}

# Run main function
main "$@" 