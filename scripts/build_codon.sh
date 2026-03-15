#!/usr/bin/env bash
# Build Codon modules into Python extension shared libraries.
# Usage: ./scripts/build_codon.sh [--release|--debug]
#
# Prerequisites:
#   - Codon compiler installed (https://github.com/exaloop/codon)
#   - CODON_DIR or codon in PATH
#
# Output: compiled .so/.dylib files in codon/lib/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CODON_SRC="$PROJECT_ROOT/codon"
CODON_LIB="$CODON_SRC/lib"

# Build mode
BUILD_MODE="${1:---release}"

# Find Codon compiler
CODON_CMD=""
if [ -n "${CODON_DIR:-}" ]; then
    CODON_CMD="$CODON_DIR/bin/codon"
elif command -v codon &> /dev/null; then
    CODON_CMD="codon"
else
    echo "ERROR: Codon compiler not found."
    echo "Install from: https://github.com/exaloop/codon"
    echo "Or set CODON_DIR to the Codon installation directory."
    exit 1
fi

echo "Using Codon compiler: $CODON_CMD"
echo "Build mode: $BUILD_MODE"
echo ""

# Create output directory
mkdir -p "$CODON_LIB"

# List of modules to compile
MODULES=(
    "graph_kernels/centrality"
    "graph_kernels/similarity"
    "graph_kernels/community"
    "graph_kernels/path_analysis"
    "data_processing/vector_ops"
    "data_processing/hash_utils"
)

FAILED=0
BUILT=0

for module in "${MODULES[@]}"; do
    src_file="$CODON_SRC/${module}.codon"
    module_name="$(basename "$module")"
    out_file="$CODON_LIB/${module_name}"

    if [ ! -f "$src_file" ]; then
        echo "SKIP: $src_file (not found)"
        continue
    fi

    echo "Building: $module_name..."

    if $CODON_CMD build "$BUILD_MODE" \
        --relocation-model=pic \
        -pyext \
        -o "${out_file}" \
        -module "$module_name" \
        "$src_file" 2>&1; then
        echo "  OK: $module_name"
        ((BUILT++))
    else
        echo "  FAIL: $module_name"
        ((FAILED++))
    fi
done

echo ""
echo "Build complete: $BUILT succeeded, $FAILED failed"
echo "Output directory: $CODON_LIB"

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
