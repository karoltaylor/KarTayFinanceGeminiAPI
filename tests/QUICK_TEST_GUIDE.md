# Quick Test Guide

## 🎯 Common Test Commands

### Run ALL Tests (Recommended)
```bash
pytest
```
**Result**: 108 tests, 79.81% coverage ✅

---

### Run Only Integration Tests (Wallet API)
```bash
pytest tests/test_api_wallets.py --no-cov
```
**Result**: 21 tests, no coverage check ✅

Or using marker:
```bash
pytest -m integration --no-cov
```

---

### Run Only Unit Tests (Exclude Integration)
```bash
pytest -m "not integration"
```
**Result**: 87 tests, higher coverage ✅

---

### Run Specific Test File
```bash
# Unit tests
pytest tests/test_mongodb_models.py --no-cov
pytest tests/test_transaction_mapper.py --no-cov
pytest tests/test_column_mapper.py --no-cov

# Integration tests
pytest tests/test_api_wallets.py --no-cov
```

---

### Run Specific Test
```bash
pytest tests/test_api_wallets.py::TestListWallets::test_list_wallets_empty -v --no-cov
```

---

### Verbose Output
```bash
pytest -v  # Very verbose
pytest -vv # Even more verbose
```

---

### Stop on First Failure
```bash
pytest -x
pytest -x --pdb  # Drop into debugger on failure
```

---

### Run Last Failed Tests
```bash
pytest --lf  # last failed
pytest --ff  # failed first, then others
```

---

### Watch Mode (Re-run on file changes)
```bash
pytest-watch  # Requires: pip install pytest-watch
```

---

## 📊 Coverage Options

### Skip Coverage (Faster)
```bash
pytest --no-cov
```

### Show Missing Lines
```bash
pytest --cov-report=term-missing
```

### Generate HTML Coverage Report
```bash
pytest --cov-report=html
# Then open: htmlcov/index.html
```

### Coverage for Specific Module
```bash
pytest --cov=src/services
pytest --cov=src/models
```

---

## 🏷️ Using Markers

### Run integration tests only:
```bash
pytest -m integration --no-cov
```

### Run slow tests only:
```bash
pytest -m slow
```

### Skip slow/integration tests:
```bash
pytest -m "not slow and not integration"
```

---

## 🔧 Debugging Tests

### Show print statements:
```bash
pytest -s
```

### Show local variables on failure:
```bash
pytest -l
```

### Drop into debugger on failure:
```bash
pytest --pdb
```

### Set breakpoint in test:
```python
def test_something():
    import pdb; pdb.set_trace()
    # or in Python 3.7+
    breakpoint()
```

---

## 💡 Pro Tips

### Quick Check (Fast)
```bash
pytest tests/test_api_wallets.py --no-cov -q
```

### Full Check (Before commit)
```bash
pytest -v
```

### CI/CD Pipeline
```bash
pytest --cov-fail-under=79 --cov-report=xml
```

### Parallel Execution (Faster)
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

---

## 📁 Test Organization

```
tests/
├── test_api_wallets.py          # Integration tests (marked)
├── test_column_mapper.py         # Unit tests
├── test_config.py                # Unit tests
├── test_data_model.py            # Unit tests
├── test_loaders.py               # Unit tests
├── test_mongodb_models.py        # Unit tests
├── test_pipeline.py              # Unit tests
├── test_table_detector.py        # Unit tests
└── test_transaction_mapper.py    # Unit tests
```

---

## ⚠️ Common Issues

### "Coverage too low" when running integration tests only
**Solution**: Always use `--no-cov` with integration tests
```bash
pytest tests/test_api_wallets.py --no-cov
```

### Tests fail with 401 Unauthorized
**Solution**: Check that `test_db` fixture is included in test signature
```python
def test_something(self, client, auth_headers, test_db):  # ← include test_db
```

### MongoDB connection timeout
**Solution**: Ensure MongoDB is running and accessible
```bash
# Check connection
python -c "from src.config.mongodb import MongoDBConfig; print(MongoDBConfig.get_mongodb_url())"
```

---

## 🎨 Custom Test Run Examples

### Pre-commit: Fast unit tests only
```bash
pytest -m "not integration" --no-cov -q
```

### Full validation: All tests with coverage
```bash
pytest -v --cov-report=html
```

### Integration smoke test: Just run integration
```bash
pytest -m integration --no-cov -q
```

### Development: Watch and re-run
```bash
ptw -- --no-cov  # Requires pytest-watch
```

