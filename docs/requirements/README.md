# Requirements Management

This section contains all documentation related to project dependencies, requirements management, and development environment setup.

## 📋 Requirements Files

### Core Requirements Files
- **[requirements.txt](../requirements.txt)** - Main production dependencies (auto-generated)
- **[requirements.in](../requirements.in)** - Source file for main dependencies
- **[requirements-dev.txt](../requirements-dev.txt)** - Development environment dependencies
- **[requirements-test.txt](../requirements-test.txt)** - Comprehensive testing dependencies
- **[requirements-codon.txt](../requirements-codon.txt)** - Codon-specific development environment

### Component-Specific Requirements
- **[dashboard/requirements.txt](../dashboard/requirements.txt)** - Streamlit dashboard dependencies
- **[monitoring/requirements.txt](../monitoring/requirements.txt)** - Monitoring and observability dependencies

## 📚 Documentation

### Guides
- **[Requirements Overview](REQUIREMENTS_OVERVIEW.md)** - Complete guide to project dependencies and management
- **[Requirements Update Summary](REQUIREMENTS_UPDATE_SUMMARY.md)** - Latest updates and changes to requirements

### Validation
- **[Validation Script](../scripts/validate_requirements.py)** - Script to validate all requirements files

## 🚀 Quick Start

### For New Developers
1. **Create Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Main Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Development Dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install Test Dependencies**:
   ```bash
   pip install -r requirements-test.txt
   ```

### For Codon Development
```bash
pip install -r requirements-codon.txt
```

### For Component-Specific Development
```bash
# Dashboard
pip install -r dashboard/requirements.txt

# Monitoring
pip install -r monitoring/requirements.txt
```

## 🔧 Requirements Management

### Adding New Dependencies
1. **Production Dependencies**: Add to `requirements.in`
2. **Development Dependencies**: Add to `requirements-dev.txt`
3. **Test Dependencies**: Add to `requirements-test.txt`
4. **Codon Dependencies**: Add to `requirements-codon.txt`
5. **Component Dependencies**: Add to respective component file

### Updating Dependencies
1. Edit the appropriate requirements file
2. Run `pip-compile requirements.in --upgrade` to regenerate `requirements.txt`
3. Test the application to ensure compatibility

### Version Management
- **Main Requirements**: Use pip-compile for automatic version pinning
- **Component Requirements**: Use `>=` for flexibility
- **Security Dependencies**: Pin to specific versions

## 🧪 Validation

### Running Validation
```bash
python scripts/validate_requirements.py
```

### What Validation Checks
- ✅ All files exist and are readable
- ✅ No syntax errors detected
- ✅ Compatible with Python 3.13
- ✅ pip-compile compatibility verified
- ✅ Dependency count and structure

## 📊 Current Status

### Dependency Counts
- **Production**: 310 dependencies (requirements.txt)
- **Development**: 49 dependencies (requirements-dev.txt)
- **Testing**: 47 dependencies (requirements-test.txt)
- **Codon**: 32 dependencies (requirements-codon.txt)
- **Dashboard**: 19 dependencies (dashboard/requirements.txt)
- **Monitoring**: 31 dependencies (monitoring/requirements.txt)

### Compatibility
- ✅ Python 3.13 compatible
- ✅ All version conflicts resolved
- ✅ Security vulnerabilities addressed
- ✅ Performance optimized

## 🔍 Troubleshooting

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

## 📖 Best Practices

1. **Use Virtual Environments**: Always isolate project dependencies
2. **Pin Versions**: Use pip-compile for reproducible builds
3. **Regular Updates**: Keep dependencies up to date
4. **Security Scanning**: Regularly check for vulnerabilities
5. **Documentation**: Keep this overview updated
6. **Testing**: Test thoroughly after dependency changes

## 🔗 Related Documentation

- **[Development Guide](../development/README.md)** - Development workflow and best practices
- **[Testing Guide](../testing/test-summary.md)** - Testing strategies and frameworks
- **[Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)** - Deployment procedures
- **[Monitoring Guide](../monitoring/README.md)** - System monitoring and observability

---

*Last updated: January 2025*
*Requirements version: 2.0* 