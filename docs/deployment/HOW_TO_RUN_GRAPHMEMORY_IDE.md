# How to Run GraphMemory-IDE: Complete Setup Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Setup Instructions](#detailed-setup)
5. [Database Configuration](#database-configuration)
6. [Backend Services](#backend-services)
7. [Frontend Setup](#frontend-setup)
8. [Dashboard Setup](#dashboard-setup)
9. [Docker Deployment](#docker-deployment)
10. [Kubernetes Deployment](#kubernetes-deployment)
11. [Monitoring & Logging](#monitoring-logging)
12. [Security Configuration](#security-configuration)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance & Updates](#maintenance-updates)

## System Overview

GraphMemory-IDE is a comprehensive AI-powered development platform that combines:
- **MCP (Model Context Protocol) Server**: Core memory management and context handling
- **Analytics Engine**: Machine learning and graph analysis capabilities
- **Interactive Dashboard**: Real-time monitoring and visualization
- **Multi-Database Architecture**: PostgreSQL, Kuzu graph database, and Redis
- **RESTful API**: FastAPI-based backend services
- **Real-time Updates**: Server-sent events and WebSocket support

## Prerequisites

### Hardware Requirements
- **Minimum**: 8GB RAM, 4 CPU cores, 50GB disk space
- **Recommended**: 16GB+ RAM, 8+ CPU cores, 100GB+ SSD
- **Production**: 32GB+ RAM, 16+ CPU cores, 500GB+ NVMe SSD

### Software Requirements
- **Operating System**: Ubuntu 20.04+, macOS 11+, or Windows 10+ with WSL2
- **Python**: Version 3.11 or 3.12
- **Node.js**: Version 18+ with npm/yarn
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Git**: Latest version

### Network Requirements
- Internet connection for package downloads
- Open ports: 8000 (API), 8501 (Dashboard), 3000 (Frontend), 5432 (PostgreSQL), 6379 (Redis)

## Quick Start

For immediate testing and development:

```bash
# Clone the repository
git clone https://github.com/your-org/GraphMemory-IDE.git
cd GraphMemory-IDE

# Run the setup script
chmod +x setup.sh
./setup.sh

# Start all services
docker-compose up -d

# Access the system
# Dashboard: http://localhost:8501
# API: http://localhost:8000
# Frontend: http://localhost:3000
```

## Detailed Setup Instructions

### Step 1: Environment Preparation

#### 1.1 Clone Repository
```bash
git clone https://github.com/your-org/GraphMemory-IDE.git
cd GraphMemory-IDE
```

#### 1.2 Create Python Virtual Environment
```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

#### 1.3 Install Python Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

#### 1.4 Install Node.js Dependencies
```bash
# Install frontend dependencies
cd frontend
npm install
cd ..

# Install dashboard dependencies
cd dashboard
npm install
cd ..
```

### Step 2: Environment Configuration

#### 2.1 Copy Environment Template
```bash
cp .env.example .env
```

#### 2.2 Configure Environment Variables
Edit `.env` file with your specific configuration:

```env
# Environment
ENVIRONMENT=production
DEBUG=false

# Security
SECRET_KEY=your-super-secret-key-here-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Database URLs
DATABASE_URL=postgresql://graphmemory:password@localhost:5432/graphmemory
REDIS_URL=redis://localhost:6379/0
KUZU_DATABASE_PATH=./data/kuzu

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8501

# Dashboard Configuration
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/graphmemory.log

# Analytics
ENABLE_GPU=false
ML_MODEL_PATH=./models
ANALYTICS_BATCH_SIZE=100

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30

# Security
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=100
ENABLE_AUTHENTICATION=true
```

## Database Configuration

### Step 3: PostgreSQL Setup

#### 3.1 Install PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql
brew services start postgresql

# Or use Docker
docker run -d \
  --name graphmemory-postgres \
  -e POSTGRES_DB=graphmemory \
  -e POSTGRES_USER=graphmemory \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15
```

#### 3.2 Create Database and User
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE graphmemory;
CREATE USER graphmemory WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE graphmemory TO graphmemory;
\q
```

#### 3.3 Initialize Database Schema
```bash
# Run database migrations
python -m alembic upgrade head

# Create initial data (optional)
python scripts/init_database.py
```

### Step 4: Redis Setup

#### 4.1 Install Redis
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis
brew services start redis

# Or use Docker
docker run -d \
  --name graphmemory-redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### 4.2 Configure Redis
Edit `/etc/redis/redis.conf` (or use default configuration):
```conf
bind 127.0.0.1
port 6379
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### Step 5: Kuzu Graph Database Setup

#### 5.1 Create Kuzu Database Directory
```bash
mkdir -p ./data/kuzu
chmod 755 ./data/kuzu
```

#### 5.2 Initialize Kuzu Database
```bash
python scripts/init_kuzu.py
```

## Backend Services

### Step 6: Start Backend API Server

#### 6.1 Development Mode
```bash
# Start development server with auto-reload
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

#### 6.2 Production Mode
```bash
# Start production server with Gunicorn
gunicorn server.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

#### 6.3 Start Background Services
```bash
# Start analytics engine
python -m server.analytics.engine &

# Start monitoring services
python -m server.monitoring.health_monitor &

# Start backup service
python -m server.backup.scheduler &
```

### Step 7: Verify Backend Services

#### 7.1 Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-07T12:00:00Z",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "kuzu": "healthy"
  }
}
```

#### 7.2 API Documentation
Visit: http://localhost:8000/docs

## Frontend Setup

### Step 8: Build and Start Frontend

#### 8.1 Development Mode
```bash
cd frontend
npm run dev
```

#### 8.2 Production Build
```bash
cd frontend
npm run build
npm run start
```

#### 8.3 Environment Configuration
Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DASHBOARD_URL=http://localhost:8501
NEXT_PUBLIC_ENVIRONMENT=production
```

## Dashboard Setup

### Step 9: Configure and Start Dashboard

#### 9.1 Dashboard Configuration
Create `dashboard/.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
enableCORS = true
enableXsrfProtection = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[browser]
gatherUsageStats = false
```

#### 9.2 Start Dashboard
```bash
cd dashboard
streamlit run app.py
```

## Docker Deployment

### Step 10: Docker-based Deployment

#### 10.1 Build Docker Images
```bash
# Build all services
docker-compose build

# Or build individual services
docker build -t graphmemory-api -f docker/api/Dockerfile .
docker build -t graphmemory-dashboard -f docker/dashboard/Dockerfile .
docker build -t graphmemory-frontend -f docker/frontend/Dockerfile .
```

#### 10.2 Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale api=3 --scale dashboard=2
```

#### 10.3 Docker Compose Configuration
The `docker-compose.yml` includes:
- PostgreSQL database
- Redis cache
- API server (with scaling)
- Dashboard server
- Frontend server
- Nginx reverse proxy
- Prometheus monitoring
- Grafana dashboards

## Kubernetes Deployment

### Step 11: Kubernetes Deployment

#### 11.1 Prerequisites
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### 11.2 Deploy to Kubernetes
```bash
# Apply namespace
kubectl apply -f kubernetes/manifests/namespace.yaml

# Apply secrets
kubectl apply -f kubernetes/manifests/secrets.yaml

# Apply configurations
kubectl apply -f kubernetes/manifests/configmaps.yaml

# Deploy databases
kubectl apply -f kubernetes/manifests/postgresql.yaml
kubectl apply -f kubernetes/manifests/redis.yaml

# Deploy application services
kubectl apply -f kubernetes/manifests/api.yaml
kubectl apply -f kubernetes/manifests/dashboard.yaml
kubectl apply -f kubernetes/manifests/frontend.yaml

# Deploy ingress
kubectl apply -f kubernetes/manifests/ingress.yaml
```

#### 11.3 Verify Deployment
```bash
# Check pods
kubectl get pods -n graphmemory

# Check services
kubectl get services -n graphmemory

# Check ingress
kubectl get ingress -n graphmemory
```

## Monitoring & Logging

### Step 12: Setup Monitoring

#### 12.1 Prometheus Configuration
```bash
# Start Prometheus
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus:/etc/prometheus \
  prom/prometheus
```

#### 12.2 Grafana Dashboards
```bash
# Start Grafana
docker run -d \
  --name grafana \
  -p 3001:3000 \
  -v $(pwd)/monitoring/grafana:/var/lib/grafana \
  grafana/grafana
```

Access Grafana at http://localhost:3001 (admin/admin)

#### 12.3 Log Aggregation
```bash
# Start ELK stack
docker-compose -f monitoring/elk/docker-compose.yml up -d
```

## Security Configuration

### Step 13: Security Hardening

#### 13.1 SSL/TLS Configuration
```bash
# Generate self-signed certificates (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key -out server.crt

# Or use Let's Encrypt (production)
certbot certonly --standalone -d your-domain.com
```

#### 13.2 Authentication Setup
```bash
# Create admin user
python scripts/create_admin_user.py --email admin@yourcompany.com --password secure_password

# Setup OAuth (optional)
python scripts/setup_oauth.py --provider google --client-id your_client_id
```

#### 13.3 Security Scanning
```bash
# Run security audit
python -m safety check
python -m bandit -r server/
npm audit --audit-level high
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Port Already in Use
```bash
# Find process using port
sudo lsof -i :8000
sudo netstat -tulpn | grep :8000

# Kill process
sudo kill -9 <PID>
```

#### Issue: Database Connection Failed
```bash
# Check database status
sudo systemctl status postgresql
docker logs graphmemory-postgres

# Test connection
pg_isready -h localhost -p 5432 -U graphmemory
```

#### Issue: Memory Issues
```bash
# Check memory usage
free -h
docker stats

# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### Issue: Permission Denied
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./data
chmod -R 755 ./data
```

### Logs and Debugging

#### Application Logs
```bash
# View API logs
tail -f logs/graphmemory.log

# View Docker logs
docker-compose logs -f api
docker-compose logs -f dashboard

# View Kubernetes logs
kubectl logs -f deployment/graphmemory-api -n graphmemory
```

#### Database Logs
```bash
# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

## Maintenance & Updates

### Regular Maintenance Tasks

#### Daily Tasks
```bash
# Check system health
curl http://localhost:8000/health

# Check disk space
df -h

# Check memory usage
free -h
```

#### Weekly Tasks
```bash
# Update dependencies
pip list --outdated
npm outdated

# Database maintenance
python scripts/database_maintenance.py

# Clean up logs
find logs/ -name "*.log" -mtime +7 -delete
```

#### Monthly Tasks
```bash
# Security updates
sudo apt update && sudo apt upgrade
pip install --upgrade pip setuptools wheel

# Backup verification
python scripts/verify_backups.py

# Performance analysis
python scripts/performance_report.py
```

### Updating GraphMemory-IDE

#### Update Process
```bash
# Backup current installation
./scripts/backup_system.sh

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt
npm install

# Run migrations
python -m alembic upgrade head

# Restart services
docker-compose restart
# Or for Kubernetes:
kubectl rollout restart deployment/graphmemory-api -n graphmemory
```

## Performance Tuning

### Database Optimization
```sql
-- PostgreSQL tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Redis Optimization
```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Application Tuning
```env
# .env
WORKERS=4
WORKER_CONNECTIONS=1000
KEEP_ALIVE=2
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=100
PRELOAD_APP=true
```

## Support and Resources

### Documentation
- API Documentation: http://localhost:8000/docs
- Dashboard Help: http://localhost:8501/help
- Source Code: https://github.com/your-org/GraphMemory-IDE

### Community
- Discord: https://discord.gg/graphmemory-ide
- GitHub Issues: https://github.com/your-org/GraphMemory-IDE/issues
- Documentation: https://docs.graphmemory-ide.com

### Commercial Support
- Email: support@yourcompany.com
- Support Portal: https://support.yourcompany.com
- Phone: +1-800-SUPPORT

---

**Congratulations!** You have successfully set up GraphMemory-IDE. The system should now be running and accessible through the various interfaces. For additional help, refer to the troubleshooting section or contact support. 