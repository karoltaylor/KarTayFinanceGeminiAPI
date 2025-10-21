# Test Categorization Summary

This document outlines the division of tests into unit and integration categories for efficient CI/CD pipeline execution.

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
**Purpose**: Fast, isolated tests that don't require external dependencies (database, APIs, etc.)
**Execution**: `pytest -m unit`
**Use Case**: CI builds, quick development feedback

#### Files:
- `test_data_model.py` - Data model validation and business logic
- `test_column_mapper.py` - Column mapping service with mocked AI
- `test_asset_type_mapper.py` - Asset type inference service with mocked AI
- `test_table_detector.py` - Table detection algorithms
- `test_transaction_mapper.py` - Transaction mapping logic
- `test_config.py` - Configuration management
- `test_logging.py` - Logging utilities
- `test_loaders.py` - File loading utilities

**Total**: 105 unit tests

### Integration Tests (`@pytest.mark.integration`)
**Purpose**: Tests that require external dependencies (database, APIs, file systems)
**Execution**: `pytest -m integration`
**Use Case**: Full system testing, pre-deployment validation

#### Files:
- `test_api_transactions.py` - FastAPI transaction endpoints
- `test_api_wallets.py` - FastAPI wallet endpoints
- `test_database_integration.py` - Real database operations
- `test_database_constraints.py` - Database constraints and relationships
- `test_database_validation.py` - Database field validation
- `test_firebase_auth.py` - Firebase authentication
- `test_cache_integration.py` - Cache integration testing
- `test_column_mapping_cache.py` - Column mapping cache functionality
- `test_pipeline.py` - Data pipeline integration
- `test_edge_cases.py` - Edge cases and performance tests
- `test_all_test_data_files.py` - Real test data file processing
- `test_mongodb_models.py` - MongoDB model validation

**Total**: 201 integration tests

## Test Execution Patterns

### For CI/CD Builds (Fast)
```bash
# Run only unit tests (recommended for builds)
pytest -m unit

# Run unit tests without coverage (fastest)
pytest -m unit --no-cov
```

### For Full Testing (Slow)
```bash
# Run all tests
pytest

# Run only integration tests
pytest -m integration

# Run integration tests without coverage
pytest -m integration --no-cov
```

### For AI Testing
```bash
# Run tests without Gemini API calls (default)
pytest -m "not gemini_api"

# Run only Gemini API tests with real API
USE_REAL_AI=true pytest -m gemini_api
```

## Benefits

1. **Fast CI Builds**: Unit tests run in ~3-7 seconds vs ~30+ seconds for all tests
2. **Clear Separation**: Easy to understand what each test category covers
3. **Flexible Execution**: Can run appropriate test suite for different scenarios
4. **Resource Efficiency**: Unit tests don't require database or external services
5. **Development Speed**: Quick feedback during development with unit tests

## CI/CD Integration

### Recommended CI Pipeline:
1. **Build Stage**: Run unit tests only (`pytest -m unit`)
2. **Integration Stage**: Run integration tests (`pytest -m integration`)
3. **Deploy Stage**: Run full test suite if needed

### GitHub Actions Example:
```yaml
- name: Run Unit Tests
  run: pytest -m unit --no-cov

- name: Run Integration Tests
  run: pytest -m integration --no-cov
  if: github.event_name == 'pull_request'
```

## Test Count Summary

- **Total Tests**: 306
- **Unit Tests**: 105 (34%)
- **Integration Tests**: 201 (66%)
- **Gemini API Tests**: 2 (marked with `@pytest.mark.gemini_api`)

This categorization ensures that CI builds are fast and efficient while maintaining comprehensive test coverage through integration tests.
