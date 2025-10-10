# GitHub Actions & CI/CD Configuration

## 📁 Files Created

### Workflow Files (`.github/workflows/`)
1. **`ci.yml`** - Main CI/CD pipeline
2. **`codeql.yml`** - Security scanning
3. **`pylint.yml`** - Code quality analysis
4. **`tests.yml`** - Dedicated test suite
5. **`python-quality.yml`** - Advanced quality checks

### Configuration Files
- **`.pylintrc`** - PyLint configuration
- **`requirements-dev.txt`** - Development dependencies
- **`run_local_ci.py`** - Local CI testing script

### Documentation
- **`GITHUB_ACTIONS_GUIDE.md`** - Complete usage guide
- **`GITHUB_ACTIONS_SETUP.md`** - Setup summary

---

## 🚀 Quick Reference

### Run Checks Locally
```bash
# Quick check (recommended before commit)
python run_local_ci.py

# Or manually:
pytest                                    # All tests
pylint api/ src/ --max-line-length=120   # Linting
black --check api/ src/ tests/           # Format check
```

### Run on GitHub
- **Automatic**: Push to `main` or `develop`
- **Pull Requests**: Checks run automatically
- **Manual**: Actions tab → Select workflow → Run workflow

---

## 📊 What Gets Checked

✅ **Code Quality (PyLint)**
- Code style and best practices
- Maximum line length: 120
- Minimum score: 7.0/10

✅ **Security (CodeQL)**  
- SQL injection
- XSS vulnerabilities
- Path traversal
- Insecure crypto
- 100+ security patterns

✅ **Tests**
- 108 tests (87 unit + 21 integration)
- 79.81% code coverage
- Multiple Python versions

✅ **Formatting (Black)**
- PEP 8 compliance
- Consistent code style

---

## 🎯 Workflow Status Badges

Add to README.md:
```markdown
![CI](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CI/badge.svg)
![PyLint](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/PyLint/badge.svg)
![CodeQL](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/CodeQL%20Security%20Scan/badge.svg)
![Tests](https://github.com/karoltaylor/KarTayFinanceGeminiAPI/workflows/Tests/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Coverage](https://img.shields.io/badge/coverage-79.81%25-brightgreen)
```

---

## ⚡ Next Steps

1. **Commit and push**:
   ```bash
   git add .github/ .pylintrc requirements-dev.txt run_local_ci.py
   git commit -m "Add GitHub Actions CI/CD workflows"
   git push
   ```

2. **Monitor first run**:
   - Go to Actions tab
   - Watch workflows execute
   - Check for any failures

3. **Enable CodeQL** (if needed):
   - Settings → Security & analysis
   - Enable "Code scanning"

4. **Add badges to README.md**

---

## 📚 Documentation

- **`GITHUB_ACTIONS_GUIDE.md`**: Complete guide with examples
- **`GITHUB_ACTIONS_SETUP.md`**: Setup summary and overview
- **`tests/README_INTEGRATION_TESTS.md`**: Integration test guide
- **`tests/QUICK_TEST_GUIDE.md`**: Test command reference

---

## 🔧 Customization

### Change Python versions:
Edit workflow matrix in any `.yml` file:
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
```

### Adjust PyLint strictness:
Edit `.pylintrc`:
```ini
[MESSAGES CONTROL]
disable=
    C0111,  # Add/remove rules here
```

### Modify CodeQL schedule:
Edit `codeql.yml`:
```yaml
schedule:
  - cron: '0 3 * * 1'  # Weekly on Monday 3am UTC
```

---

## ✅ Pre-Push Checklist

Before pushing code:

- [ ] Run `python run_local_ci.py`
- [ ] All tests pass locally
- [ ] PyLint score > 7.0
- [ ] No security issues with Bandit
- [ ] Code formatted with Black (optional)
- [ ] Integration tests pass

---

## 🎓 Learn More

- [GitHub Actions Docs](https://docs.github.com/actions)
- [CodeQL Documentation](https://codeql.github.com/docs)
- [PyLint User Guide](https://pylint.readthedocs.io)
- [Black Code Style](https://black.readthedocs.io)

