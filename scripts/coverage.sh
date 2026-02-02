#!/bin/bash
set -e

pytest \
    --cov=services/ui_iot \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=70 \
    -m "not e2e" \
    "$@"

echo ""
echo "=========================================="
echo "Coverage report generated:"
echo "  - Terminal: above"
echo "  - HTML: htmlcov/index.html"
echo "  - XML: coverage.xml"
echo "=========================================="

if command -v open &> /dev/null; then
    echo "Opening HTML report..."
    open htmlcov/index.html
elif command -v xdg-open &> /dev/null; then
    echo "Opening HTML report..."
    xdg-open htmlcov/index.html
fi
