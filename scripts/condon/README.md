# Condon Development Scripts

This directory contains all Condon-related scripts for environment setup, validation, and testing.

## Scripts Overview

### 1. `setup_condon_environment.sh`
**Purpose**: Comprehensive Condon environment setup with virtual environment isolation
**Usage**: `./scripts/condon/setup_condon_environment.sh`
**Features**:
- Creates virtual environment for isolation
- Installs Condon CLI
- Configures environment variables
- Tests basic compilation
- Tests Python interoperability
- Validates isolation from system Python
- Exports environment for team reproducibility

### 2. `codon_installation_validation.sh`
**Purpose**: Validates Condon CLI installation and basic functionality
**Usage**: `./scripts/condon/codon_installation_validation.sh`
**Features**:
- Verifies virtual environment isolation
- Tests Condon CLI availability
- Tests basic compilation functionality
- Tests build functionality
- Tests isolation from system Python
- Comprehensive validation reporting

### 3. `codon_python_interoperability_validation.sh`
**Purpose**: Validates Python interoperability features within virtual environment
**Usage**: `./scripts/condon/codon_python_interoperability_validation.sh`
**Features**:
- Tests @python decorator functionality
- Tests from python import functionality
- Tests data type conversions
- Tests Python module imports
- Validates isolation from system Python
- Comprehensive Python interoperability testing

## Environment Variables

The scripts configure the following environment variables:

- `CODON_PYTHON`: Points to the Python interpreter in the virtual environment
- `PYTHONNOUSERSITE`: Prevents user-level site packages interference
- `PATH`: Includes Condon binary directory
- `CODON_DIR`: Condon installation directory

## Virtual Environment

All scripts work within the `codon-dev-env` virtual environment to ensure:
- Isolation from system Python
- Consistent dependency management
- Thread safety
- Reproducible development environment

## Usage Examples

### Complete Setup
```bash
# Run complete environment setup
./scripts/condon/setup_condon_environment.sh
```

### Validation Only
```bash
# Validate existing installation
./scripts/condon/codon_installation_validation.sh

# Validate Python interoperability
./scripts/condon/codon_python_interoperability_validation.sh
```

### Manual Environment Activation
```bash
# Activate the virtual environment
source codon-dev-env/bin/activate

# Configure environment variables
export CODON_PYTHON=$(which python)
export PYTHONNOUSERSITE=True
```

## Safety Features

- **Virtual Environment Isolation**: All operations performed within isolated environment
- **Thread Safety**: Verified safe concurrent operations
- **Environment Variables**: Process-local within virtual environment
- **Error Handling**: Comprehensive error checking and reporting
- **Cleanup**: Automatic cleanup of test files

## Dependencies

- Python 3.6+
- curl
- Virtual environment support (venv)

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Found**
   - Run `setup_condon_environment.sh` to create the environment

2. **CODON_PYTHON Not Set**
   - Ensure virtual environment is activated
   - Run `export CODON_PYTHON=$(which python)`

3. **Python Interoperability Errors**
   - Verify virtual environment is activated
   - Check that CODON_PYTHON points to virtual environment Python

### Validation Commands

```bash
# Check virtual environment
python -c "import sys; print('Virtual Environment:', sys.prefix)"

# Check Condon CLI
codon --version

# Check environment variables
echo "CODON_PYTHON: $CODON_PYTHON"
echo "PYTHONNOUSERSITE: $PYTHONNOUSERSITE"
```

## Team Usage

These scripts are designed for team use with:
- Reproducible environment setup
- Comprehensive validation
- Clear documentation
- Safety fencing and isolation
- Export capabilities for environment sharing 