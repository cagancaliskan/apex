#!/bin/bash
# Quick test runner for F1 Race Strategy Workbench

echo "================================"
echo "F1 RSW - Running Tests"
echo "================================"

cd "$(dirname "$0")/.."

# Run all tests
python tests/run_all_tests.py

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "================================"
    echo "✅ All tests passed!"
    echo "================================"
else
    echo ""
    echo "================================"
    echo "❌ Some tests failed"
    echo "================================"
fi

exit $EXIT_CODE
