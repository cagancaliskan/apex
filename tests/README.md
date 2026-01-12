# F1 Race Strategy Workbench - Test Suite

This directory contains comprehensive tests for the F1 Race Strategy Workbench.

## Test Categories

### Unit Tests
- `test_rls.py` - RLS degradation model tests
- `test_features.py` - Feature engineering tests  
- `test_degradation_model.py` - Driver model tests

### Integration Tests
- `test_integration.py` - End-to-end system tests

### Accuracy Tests
- `test_prediction_accuracy.py` - ML prediction accuracy on real F1 data

## Running Tests

### Run All Tests
```bash
cd apex
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_rls.py -v
```

### Run With Coverage
```bash
pytest tests/ --cov=rsw --cov-report=html
```

### Run Only Fast Tests (Skip Accuracy Tests)
```bash
pytest tests/ -v -m "not slow"
```

### Run Only Accuracy Tests  
```bash
pytest tests/test_prediction_accuracy.py -v -s
```

## Expected Results

### Unit Tests
- **test_rls.py**: 10+ tests, all should pass
- **test_features.py**: 8+ tests, all should pass
- **test_degradation_model.py**: 6+ tests, all should pass

### Integration Tests
- **test_integration.py**: 3 tests, requires internet connection

### Accuracy Tests (Real Data)
- **MAE**: < 2.0 seconds
- **RMSE**: < 3.0 seconds  
- **MAPE**: < 5.0%

## Test Flags

Tests use pytest markers:
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.slow` - Tests that take >5s (accuracy tests)

## Troubleshooting

If tests fail:
1. Check internet connection (for OpenF1 API tests)
2. Verify dependencies: `pip install -r requirements.txt`
3. Check PYTHONPATH includes `src/`
