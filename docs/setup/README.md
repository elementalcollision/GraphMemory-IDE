# Setup and Configuration

This section contains all documentation related to project setup, configuration, and environment preparation.

## 📋 Setup Documentation

### Core Setup Guides
- **[GitHub Setup](GITHUB_SETUP.md)** - GitHub repository setup and development environment configuration

### Environment Configuration
- **[Requirements Management](../requirements/README.md)** - Dependency installation and management
- **[Development Environment](../development/README.md)** - Development workflow and tools setup

## 🚀 Quick Setup

### 1. Repository Setup
1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd GraphMemory-IDE-1
   ```

2. **Setup GitHub**: See [GitHub Setup Guide](GITHUB_SETUP.md)

### 2. Environment Setup
1. **Create Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**: See [Requirements Guide](../requirements/REQUIREMENTS_OVERVIEW.md)

### 3. Development Setup
1. **Install Development Tools**: See [Development Guide](../development/README.md)
2. **Configure IDE**: See [IDE Plugins](../ide-plugins/README.md)
3. **Setup Testing**: See [Testing Guide](../testing/test-summary.md)

## 🔧 Configuration Files

### Core Configuration
- **[requirements.txt](../../requirements.txt)** - Production dependencies
- **[requirements.in](../../requirements.in)** - Source dependencies
- **[pyproject.toml](../../pyproject.toml)** - Project configuration
- **[mypy.ini](../../mypy.ini)** - Type checking configuration
- **[.pylintrc](../../.pylintrc)** - Code linting configuration

### Component Configuration
- **[dashboard/requirements.txt](../../dashboard/requirements.txt)** - Dashboard dependencies
- **[monitoring/requirements.txt](../../monitoring/requirements.txt)** - Monitoring dependencies
- **[docker/docker-compose.yml](../../docker/docker-compose.yml)** - Docker configuration

### Development Configuration
- **[.gitignore](../../.gitignore)** - Git ignore patterns
- **[.bandit](../../.bandit)** - Security scanning configuration
- **[.semgrep.yml](../../.semgrep.yml)** - Code analysis configuration

## 🛠️ Environment Variables

### Required Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/graphmemory

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Monitoring
PROMETHEUS_PORT=9090
OTEL_ENDPOINT=http://localhost:4317

# Development
DEBUG=True
LOG_LEVEL=INFO
```

### Optional Environment Variables
```bash
# Analytics
ANALYTICS_ENABLED=True
ANALYTICS_BATCH_SIZE=100

# Performance
WORKER_PROCESSES=4
MAX_CONNECTIONS=100

# Security
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

## 🔍 Validation

### Environment Validation
```bash
# Check Python version
python3 --version

# Validate requirements
python scripts/validate_requirements.py

# Check configuration
python -c "import config; print('Configuration valid')"
```

### Component Validation
```bash
# Test database connection
python -c "from server.core.config import get_database_url; print('Database config valid')"

# Test Redis connection
python -c "import redis; r = redis.Redis.from_url('redis://localhost:6379'); print('Redis config valid')"

# Test monitoring
python -c "from monitoring.instrumentation.otel_config import setup_telemetry; print('Monitoring config valid')"
```

## 🚨 Troubleshooting

### Common Setup Issues

#### 1. Python Version Issues
```bash
# Check Python version
python3 --version

# Should be Python 3.13+
# If not, install Python 3.13
```

#### 2. Virtual Environment Issues
```bash
# Create new virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Verify activation
which python
# Should point to .venv/bin/python
```

#### 3. Dependency Issues
```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 4. Configuration Issues
```bash
# Check configuration files
ls -la *.ini *.toml *.yml

# Validate configuration
python scripts/validate_requirements.py
```

## 📖 Best Practices

### Environment Management
1. **Always use virtual environments** for project isolation
2. **Pin dependency versions** for reproducible builds
3. **Use environment variables** for configuration
4. **Validate setup** before starting development

### Configuration Management
1. **Keep configuration files** in version control
2. **Use templates** for environment-specific configs
3. **Document all configuration options**
4. **Validate configuration** on startup

### Security Considerations
1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive data
3. **Validate security configuration** regularly
4. **Follow security best practices** for all components

## 🔗 Related Documentation

- **[Development Guide](../development/README.md)** - Development workflow and tools
- **[Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)** - Production deployment
- **[Monitoring Guide](../monitoring/README.md)** - System monitoring setup
- **[Testing Guide](../testing/test-summary.md)** - Testing environment setup

## 📊 Setup Checklist

### ✅ Repository Setup
- [ ] Repository cloned
- [ ] GitHub access configured
- [ ] Branch strategy understood

### ✅ Environment Setup
- [ ] Python 3.13+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Configuration validated

### ✅ Development Setup
- [ ] IDE configured
- [ ] Code quality tools installed
- [ ] Testing framework setup
- [ ] Monitoring configured

### ✅ Validation
- [ ] All tests pass
- [ ] Configuration validated
- [ ] Security checks passed
- [ ] Performance baseline established

---

*Last updated: January 2025*
*Setup version: 2.0* 