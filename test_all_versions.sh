#!/bin/bash
# Test script to run pytest across all supported Python versions

set -e

PYTHON_VERSIONS=("3.11.13" "3.12.11" "3.13.7" "3.14.0rc3")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Testing django-msgspec-field across Python versions"
echo "=============================================="
echo ""

FAILED_VERSIONS=()
PASSED_VERSIONS=()

for version in "${PYTHON_VERSIONS[@]}"; do
    echo "=============================================="
    echo "Testing with Python $version"
    echo "=============================================="
    
    # Set the Python version for this test
    export PYENV_VERSION="$version"
    
    # Check if version is available
    if ! pyenv versions | grep -q "$version"; then
        echo "❌ Python $version not installed, skipping..."
        FAILED_VERSIONS+=("$version (not installed)")
        continue
    fi
    
    # Show Python version
    python --version
    
    # Run tests with uv
    if uv run --python "$version" pytest --tb=short -q; then
        echo "✅ Tests PASSED for Python $version"
        PASSED_VERSIONS+=("$version")
    else
        echo "❌ Tests FAILED for Python $version"
        FAILED_VERSIONS+=("$version")
    fi
    
    echo ""
done

echo "=============================================="
echo "SUMMARY"
echo "=============================================="
echo "Passed (${#PASSED_VERSIONS[@]}):"
for version in "${PASSED_VERSIONS[@]}"; do
    echo "  ✅ Python $version"
done

if [ ${#FAILED_VERSIONS[@]} -gt 0 ]; then
    echo ""
    echo "Failed (${#FAILED_VERSIONS[@]}):"
    for version in "${FAILED_VERSIONS[@]}"; do
        echo "  ❌ Python $version"
    done
    echo ""
    echo "Some tests failed!"
    exit 1
else
    echo ""
    echo "All tests passed! 🎉"
    exit 0
fi
