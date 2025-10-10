# GitHub Actions CI/CD Guide

This repository uses GitHub Actions for continuous integration and code quality checks.

## 📋 Available Workflows

### 1. **CI Workflow** (`ci.yml`) - Main Pipeline
Runs on every push and pull request to `main` or `develop` branches.

**What it does:**
- ✅ Runs all tests (unit + integration)
- ✅ Generates coverage reports
- ✅ Runs PyLint code analysis
- ✅ Uploads results to Codecov
- ✅ Tests on multiple Python versions (3.11, 3.13)

**Badge:**
```markdown
![CI](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CI/badge.svg)
```

---

### 2. **PyLint** (`pylint.yml`) - Code Quality
Dedicated PyLint workflow for code quality checks.

**What it does:**
- ✅ Lints `api/` and `src/` directories
- ✅ Tests on Python 3.11, 3.12, 3.13
- ✅ Generates JSON reports
- ✅ Uses relaxed rules (exit-zero)

**Badge:**
```markdown
![PyLint](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/PyLint/badge.svg)
```

---

### 3. **CodeQL** (`codeql.yml`) - Security Scanning
GitHub's advanced security analysis.

**What it does:**
- ✅ Scans for security vulnerabilities
- ✅ Detects common coding errors
- ✅ Finds SQL injection, XSS, etc.
- ✅ Runs weekly on schedule
- ✅ Results appear in Security tab

**Badge:**
```markdown
![CodeQL](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CodeQL%20Security%20Scan/badge.svg)
```

---

### 4. **Tests** (`tests.yml`) - Dedicated Test Suite
Comprehensive test execution with MongoDB service.

**What it does:**
- ✅ Runs unit tests with coverage
- ✅ Runs integration tests
- ✅ Spins up MongoDB service
- ✅ Uploads coverage reports
- ✅ Tests on multiple Python versions

**Badge:**
```markdown
![Tests](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/Tests/badge.svg)
```

---

### 5. **Python Code Quality** (`python-quality.yml`) - Comprehensive Quality
Advanced code quality checks (optional).

**What it does:**
- ✅ Black formatting check
- ✅ PyLint (strict mode)
- ✅ Flake8 linting
- ✅ MyPy type checking
- ✅ Bandit security scanning
- ✅ Safety dependency check

---

## 🚀 Viewing Results

### In Pull Requests:
- Checks appear automatically at the bottom of PR
- Click "Details" to see full logs
- Green checkmark = all passed
- Red X = something failed

### In Actions Tab:
1. Go to repository → Actions tab
2. See all workflow runs
3. Click on any run to see detailed logs
4. Download artifacts (reports)

### In Security Tab:
1. Go to repository → Security tab
2. Click "Code scanning alerts"
3. View CodeQL findings
4. See recommended fixes

---

## 🔧 Configuration

### PyLint Configuration
Located in `.pylintrc` (auto-generated):
- Max line length: 120
- Disabled: docstring requirements, some naming rules
- Minimum score: 7.0

### CodeQL Configuration
Uses default Python queries:
- Security vulnerabilities
- Code quality issues
- Best practice violations

### Test Configuration
See `pytest.ini`:
- Unit tests: Must pass with 79% coverage
- Integration tests: Run without coverage
- All tests must pass for CI to succeed

---

## 📊 Adding Badges to README

Add these to your `README.md`:

```markdown
# Your Project Name

![CI](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CI/badge.svg)
![PyLint](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/PyLint/badge.svg)
![CodeQL](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CodeQL%20Security%20Scan/badge.svg)
![Tests](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/Tests/badge.svg)
![Coverage](https://img.shields.io/codecov/c/github/karoltaylor/KarTayFinanceGeminiAPI)
```

---

## ⚙️ Workflow Triggers

### Automatic Triggers:
- **Push to main/develop**: Runs all workflows
- **Pull Request**: Runs all checks before merge
- **Weekly**: CodeQL runs every Monday at 3am UTC

### Manual Triggers:
You can manually trigger workflows:
1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch

---

## 🛠️ Customization

### Change PyLint strictness:
Edit `.github/workflows/pylint.yml`:
```yaml
- name: Lint with PyLint
  run: |
    pylint api/ src/ --fail-under=8.0  # Increase score requirement
```

### Add more Python versions:
Edit `strategy.matrix.python-version`:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
```

### Modify CodeQL schedule:
Edit `codeql.yml`:
```yaml
schedule:
  - cron: '0 3 * * 1'  # Every Monday at 3am
  # Change to daily: '0 3 * * *'
```

---

## 🔍 Troubleshooting

### Workflow fails with "MongoDB connection error"
- Check that MongoDB service is healthy
- Verify connection string in environment variables
- Ensure ports are mapped correctly

### PyLint score too low
- Review PyLint output for issues
- Update `.pylintrc` to disable specific rules
- Use `--exit-zero` for non-blocking linting

### CodeQL false positives
- Review findings in Security tab
- Add `.github/codeql/codeql-config.yml` to customize
- Suppress specific findings if needed

### Coverage failing
- Check that all test dependencies are installed
- Verify MongoDB is accessible
- Review coverage report for missing lines

---

## 📈 Best Practices

1. **Always run tests locally before pushing**
   ```bash
   pytest
   ```

2. **Check PyLint score**
   ```bash
   pylint api/ src/ --max-line-length=120
   ```

3. **Format code with Black**
   ```bash
   black api/ src/ tests/
   ```

4. **Review security findings regularly**
   - Check Security tab weekly
   - Address high-severity issues promptly

5. **Keep dependencies updated**
   ```bash
   pip list --outdated
   ```

---

## 🔐 Secrets Configuration

For workflows that need secrets:

1. Go to Settings → Secrets and variables → Actions
2. Add secrets:
   - `GOOGLE_API_KEY` (if needed for tests)
   - `MONGODB_ATLAS_URI` (if using Atlas for CI)
   - `CODECOV_TOKEN` (for Codecov uploads)

---

## 📝 Workflow Status

| Workflow | Status | Purpose |
|----------|--------|---------|
| CI | ![CI](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CI/badge.svg) | Main pipeline |
| PyLint | ![PyLint](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/PyLint/badge.svg) | Code quality |
| CodeQL | ![CodeQL](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CodeQL%20Security%20Scan/badge.svg) | Security |
| Tests | ![Tests](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/Tests/badge.svg) | Test suite |

---

## 🎯 Quick Commands

```bash
# Run what CI runs locally
pytest --cov=src --cov-report=term-missing

# Run PyLint like CI
pylint api/ src/ --max-line-length=120

# Run all quality checks
black --check api/ src/ tests/
flake8 api/ src/ --max-line-length=120
pytest

# Fix formatting
black api/ src/ tests/
```

