# Requirements Files Overview

This document provides an overview of all requirements files in the GraphMemory-IDE project and their purposes.

## Main Requirements Files

### `requirements.txt`
**Purpose**: Main production dependencies
- Auto-generated from `requirements.in` using pip-compile
- Contains all production dependencies with pinned versions
- Used for production deployments and main application

### `requirements.in`
**Purpose**: Source file for main dependencies
- Contains high-level dependency specifications
- Used by pip-compile to generate `requirements.txt`
- Should be edited when adding/removing dependencies

### `requirements-dev.txt`
**Purpose**: Development environment dependencies
- Code formatting and linting tools (black, flake8, mypy, pylint)
- Testing frameworks (pytest, pytest-cov, pytest-mock)
- Development utilities (ipdb, ipython, jupyter)
- Documentation tools (sphinx, mkdocs)
- Security and analysis tools (bandit, safety, semgrep)
- Performance profiling tools (memory-profiler, py-spy)

### `requirements-test.txt`
**Purpose**: Comprehensive testing dependencies
- Core testing framework (pytest and plugins)
- HTTP testing (httpx, requests, responses)
- Database testing (pytest-postgresql, pytest-redis)
- Async testing (pytest-asyncio)
- Performance testing (locust, pytest-benchmark)
- Browser testing (playwright, pytest-playwright)
- Security testing (bandit, safety)
- Mocking and fixtures (factory-boy, faker)
- Test reporting and utilities

### `requirements-codon.txt`
**Purpose**: Condon-specific development environment
- Core Condon dependencies (codon, codon-python, py-codon)
- Python interoperability tools
- Condon-specific testing (codon-test)
- Development and validation tools
- Performance monitoring for Condon code
- Security and validation tools
- Build and distribution tools

## Component-Specific Requirements

### `dashboard/requirements.txt`
**Purpose**: Streamlit dashboard dependencies
- Core Streamlit and visualization (streamlit, plotly, altair)
- HTTP and API communication (requests, httpx)
- Authentication and security (PyJWT, python-multipart)
- Data processing (pandas, numpy, scikit-learn)
- Real-time updates (websockets, python-socketio)
- Development tools (ipdb, rich)

### `monitoring/requirements.txt`
**Purpose**: Monitoring and observability dependencies
- OpenTelemetry core and instrumentation
- Prometheus client and exporters
- Machine learning for anomaly detection
- Performance monitoring tools
- Logging and structured data
- Health checks and alerting

## Installation Instructions

### For Development
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install test dependencies
pip install -r requirements-test.txt
```

### For Condon Development
```bash
# Install Condon-specific dependencies
pip install -r requirements-codon.txt
```

### For Dashboard Development
```bash
# Install dashboard dependencies
pip install -r dashboard/requirements.txt
```

### For Monitoring Development
```bash
# Install monitoring dependencies
pip install -r monitoring/requirements.txt
```

## Version Management

### Updating Dependencies
1. Edit `requirements.in` to add/remove/modify dependencies
2. Run `pip-compile requirements.in --upgrade` to regenerate `requirements.txt`
3. Test the application to ensure compatibility

### Adding New Dependencies
1. Add to appropriate requirements file based on purpose:
   - Production: `requirements.in`
   - Development: `requirements-dev.txt`
   - Testing: `requirements-test.txt`
   - Condon: `requirements-codon.txt`
   - Component-specific: respective component file

### Version Pinning
- Main requirements use pip-compile for automatic version pinning
- Component-specific files use `>=` for flexibility
- Critical security dependencies should be pinned to specific versions

## Compatibility Notes

### Python Version
- All requirements are compatible with Python 3.13
- Some packages may have version constraints
- Test thoroughly when upgrading Python versions

### Virtual Environment
- Always use virtual environments for development
- System Python is externally managed on macOS
- Use `.venv` for project isolation

## Security Considerations

### Regular Updates
- Run `safety check` to identify security vulnerabilities
- Update dependencies regularly
- Monitor for security advisories

### Dependency Scanning
- Use `bandit` for code security analysis
- Use `safety` for dependency vulnerability scanning
- Integrate security scanning in CI/CD pipeline

## Troubleshooting

### Common Issues
1. **Version Conflicts**: Check for incompatible package versions
2. **Missing Dependencies**: Ensure all requirements files are installed
3. **Python Version**: Verify Python 3.13 compatibility
4. **Virtual Environment**: Ensure proper activation

### Resolution Steps
1. Check error messages for specific package conflicts
2. Update requirements files with compatible versions
3. Regenerate requirements.txt if needed
4. Test application functionality

## Best Practices

1. **Use Virtual Environments**: Always isolate project dependencies
2. **Pin Versions**: Use pip-compile for reproducible builds
3. **Regular Updates**: Keep dependencies up to date
4. **Security Scanning**: Regularly check for vulnerabilities
5. **Documentation**: Keep this overview updated
6. **Testing**: Test thoroughly after dependency changes 