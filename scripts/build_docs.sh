#!/bin/bash
# Build and validate documentation

set -e

echo "Building Sphinx documentation..."

# Clean previous build
rm -rf docs/build/html

# Build documentation
uv run sphinx-build -b html docs/source docs/build/html -W --keep-going

echo "Documentation built successfully!"
echo "Open docs/build/html/index.html to view the documentation"

# Optional: Run link check
echo "Running link check..."
uv run sphinx-build -b linkcheck docs/source docs/build/linkcheck

echo "Documentation validation complete!"