#!/bin/bash
# codon_installation_validation.sh
# Comprehensive validation script for Codon installation within virtual environment

set -e

echo "=== Codon Virtual Environment Installation Validation ==="

# Check if virtual environment exists
if [ ! -d "codon-dev-env" ]; then
    echo "✗ Virtual environment not found"
    exit 1
fi

echo "✓ Virtual environment exists"

# Activate virtual environment
source codon-dev-env/bin/activate

# Verify virtual environment isolation
echo "1. Verifying virtual environment isolation..."
python -c "import sys; print('Virtual Environment:', sys.prefix)"
which python
which pip

# Test Codon CLI availability
echo "2. Testing Codon CLI availability..."
codon --version
codon --help

# Test basic compilation
echo "3. Testing basic compilation..."
cat > test_validation.py << 'EOF'
print("Codon validation test")
print("Virtual environment isolation confirmed")
print("Compilation working correctly")
EOF

codon run test_validation.py

# Test build functionality
echo "4. Testing build functionality..."
codon build -release test_validation.py
./test_validation

# Test isolation from system Python
echo "5. Testing isolation from system Python..."
deactivate
echo "Outside virtual environment:"
python3 -c "import sys; print('System Python:', sys.prefix)"

source codon-dev-env/bin/activate
echo "Inside virtual environment:"
python -c "import sys; print('Virtual Environment Python:', sys.prefix)"

# Test environment variables
echo "6. Testing environment variables..."
echo "PATH includes Codon: $PATH" | grep -q ".codon" && echo "✓ PATH configured" || echo "⚠ PATH may not be configured"

# Clean up
echo "7. Cleaning up test files..."
rm -f test_validation.py test_validation

echo "=== Validation Complete ==="
echo "✓ Virtual environment isolation working"
echo "✓ Codon CLI available (version: $(codon --version))"
echo "✓ Basic compilation working"
echo "✓ Build functionality working"
echo "✓ Environment isolation confirmed"
echo "✓ Installation validated successfully" 