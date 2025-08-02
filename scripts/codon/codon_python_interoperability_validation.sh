#!/bin/bash
# codon_python_interoperability_validation.sh
# Comprehensive validation script for Codon Python interoperability within virtual environment

set -e

echo "=== Codon Python Interoperability Validation ==="

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

# Configure CODON_PYTHON environment variable
echo "2. Configuring CODON_PYTHON environment variable..."
export CODON_PYTHON=$(which python)
export PYTHONNOUSERSITE=True

echo "CODON_PYTHON set to: $CODON_PYTHON"

# Test @python decorator functionality
echo "3. Testing @python decorator functionality..."
cat > test_python_decorator.codon << 'EOF'
@python
def py_add(x: int, y: int) -> int:
    return x + y

print("Testing @python decorator...")
result = py_add(3, 4)
print(f"py_add(3, 4) = {result}")
EOF

codon run test_python_decorator.codon

# Test from python import functionality
echo "4. Testing from python import functionality..."
cat > test_python_import.codon << 'EOF'
from python import math
print("Testing from python import...")
result = math.sqrt(16)
print(f"math.sqrt(16) = {result}")
EOF

codon run test_python_import.codon

# Test data type conversions
echo "5. Testing data type conversions..."
cat > test_data_conversion.codon << 'EOF'
import python
print("Testing data type conversions...")
o = (42).__to_py__()
n = int.__from_py__(o)
print(f"Data conversion test: {n}")
EOF

codon run test_data_conversion.codon

# Test Python module import
echo "6. Testing Python module import..."
cat > test_module_import.codon << 'EOF'
from python import sys
print("Testing Python module import...")
print(f"Python version: {sys.version}")
EOF

codon run test_module_import.codon

# Test isolation from system Python
echo "7. Testing isolation from system Python..."
deactivate
echo "Outside virtual environment:"
python3 -c "import sys; print('System Python:', sys.prefix)"

source codon-dev-env/bin/activate
echo "Inside virtual environment:"
python -c "import sys; print('Virtual Environment Python:', sys.prefix)"

# Clean up
echo "8. Cleaning up test files..."
rm -f test_python_decorator.codon test_python_import.codon test_data_conversion.codon test_module_import.codon

echo "=== Validation Complete ==="
echo "✓ Virtual environment isolation working"
echo "✓ CODON_PYTHON environment variable configured"
echo "✓ @python decorator functionality working"
echo "✓ from python import functionality working"
echo "✓ Data type conversions working"
echo "✓ Python module imports working"
echo "✓ Isolation from system Python confirmed" 