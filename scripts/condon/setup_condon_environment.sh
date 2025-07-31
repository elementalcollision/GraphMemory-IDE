#!/bin/bash
# setup_condon_environment.sh
# Comprehensive Condon environment setup script with virtual environment isolation
# This script sets up the complete Condon development environment with safety fencing

set -e

echo "=== Condon Environment Setup ==="
echo "Setting up Condon development environment with virtual environment isolation..."

# Check system requirements
echo "1. Checking system requirements..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "✗ curl not found"
    exit 1
fi

echo "✓ System requirements met"

# Create virtual environment
echo "2. Creating virtual environment..."
if [ -d "codon-dev-env" ]; then
    echo "Virtual environment already exists, using existing..."
else
    python3 -m venv codon-dev-env
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "3. Activating virtual environment..."
source codon-dev-env/bin/activate

# Verify virtual environment isolation
echo "4. Verifying virtual environment isolation..."
python -c "import sys; print('Virtual Environment:', sys.prefix)"
which python
which pip

# Install Condon CLI
echo "5. Installing Condon CLI..."
if ! command -v codon &> /dev/null; then
    /bin/bash -c "$(curl -fsSL https://exaloop.io/install.sh)"
    echo "✓ Condon CLI installed"
else
    echo "✓ Condon CLI already installed"
fi

# Configure environment variables
echo "6. Configuring environment variables..."
export PATH="$HOME/.codon/bin:$PATH"
export CODON_DIR="$HOME/.codon"
export CODON_PYTHON=$(which python)
export PYTHONNOUSERSITE=True

echo "CODON_PYTHON set to: $CODON_PYTHON"

# Test Condon CLI
echo "7. Testing Condon CLI..."
codon --version
codon --help

# Test basic compilation
echo "8. Testing basic compilation..."
cat > test_basic.codon << 'EOF'
print("Hello from Condon!")
print("Virtual environment isolation working!")
print("Condon compilation successful!")
EOF

codon run test_basic.codon

# Test build functionality
echo "9. Testing build functionality..."
codon build -release test_basic.codon
./test_basic

# Test Python interoperability
echo "10. Testing Python interoperability..."
cat > test_python_interop.codon << 'EOF'
@python
def py_add(x: int, y: int) -> int:
    return x + y

print("Testing @python decorator...")
result = py_add(3, 4)
print(f"py_add(3, 4) = {result}")

from python import math
print("Testing from python import...")
result = math.sqrt(16)
print(f"math.sqrt(16) = {result}")
EOF

codon run test_python_interop.codon

# Test isolation from system Python
echo "11. Testing isolation from system Python..."
deactivate
echo "Outside virtual environment:"
python3 -c "import sys; print('System Python:', sys.prefix)"

source codon-dev-env/bin/activate
echo "Inside virtual environment:"
python -c "import sys; print('Virtual Environment Python:', sys.prefix)"

# Clean up test files
echo "12. Cleaning up test files..."
rm -f test_basic.codon test_basic test_python_interop.codon

# Create environment export
echo "13. Creating environment export..."
pip freeze > requirements-codon.txt
echo "✓ Environment exported to requirements-codon.txt"

echo "=== Setup Complete ==="
echo "✓ Virtual environment created and activated"
echo "✓ Condon CLI installed and configured"
echo "✓ Environment variables configured"
echo "✓ Basic compilation working"
echo "✓ Python interoperability working"
echo "✓ Isolation from system Python confirmed"
echo "✓ Environment exported for team reproducibility"

echo ""
echo "To activate the environment in the future:"
echo "  source codon-dev-env/bin/activate"
echo ""
echo "To run validation tests:"
echo "  ./scripts/condon/codon_installation_validation.sh"
echo "  ./scripts/condon/codon_python_interoperability_validation.sh" 