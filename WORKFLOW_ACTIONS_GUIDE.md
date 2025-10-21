# GitHub Actions Workflow Guide

## Current Workflows (After Cleanup)

After removing duplication, we now have **3 focused workflows**:

### 1. **CI - Tests and Coverage** (`ci.yml`)
- **Purpose**: Run tests and generate coverage reports
- **Triggers**: Push/PR to main/develop branches
- **What it does**:
  - Runs pytest with coverage for both `src/` and `api/` directories
  - Uploads coverage reports to Codecov
  - Includes branch coverage metrics

### 2. **Python Code Quality** (`python-quality.yml`)
- **Purpose**: Code quality checks and linting
- **Triggers**: Push/PR to main/develop (only when Python files change)
- **What it does**:
  - Black code formatting check
  - PyLint analysis with scoring
  - Flake8 linting
  - MyPy type checking
  - Bandit security analysis
  - Safety dependency vulnerability check
  - Generates quality report artifact

### 3. **CodeQL Security Scan** (`codeql.yml`)
- **Purpose**: Security vulnerability scanning
- **Triggers**: Push/PR to main/develop + weekly schedule (Mondays 3am UTC)
- **What it does**:
  - Static code analysis for security vulnerabilities
  - Uploads results to GitHub Security tab
  - Generates security artifacts

## How to View Visual Results

### 🔍 **GitHub Actions Tab**
1. Go to your repository on GitHub
2. Click the **"Actions"** tab
3. You'll see all workflow runs with status indicators:
   - ✅ Green checkmark = Success
   - ❌ Red X = Failed
   - 🟡 Yellow circle = In progress
   - ⚪ Gray circle = Cancelled

### 📊 **Codecov Coverage Dashboard**
1. Visit: `https://codecov.io/gh/[your-username]/[your-repo]`
2. View:
   - Overall coverage percentage
   - Coverage trends over time
   - Coverage by file/directory
   - Coverage changes in PRs
   - Coverage badges for README

### 🛡️ **GitHub Security Tab**
1. Go to your repository on GitHub
2. Click the **"Security"** tab
3. View:
   - CodeQL alerts
   - Security advisories
   - Dependency vulnerabilities
   - Secret scanning results

### 📋 **Workflow Artifacts**
1. Go to any workflow run in the Actions tab
2. Scroll down to the **"Artifacts"** section
3. Download and view:
   - **quality-report**: Code quality summary
   - **codeql-results**: Security scan results
   - **coverage-badge**: Coverage SVG badge

### 🔗 **Pull Request Checks**
1. Open any Pull Request
2. Scroll down to see **"Checks"** section
3. View:
   - Individual workflow status
   - Coverage changes
   - Code quality scores
   - Security scan results

## Workflow Details

### CI - Tests and Coverage
```yaml
- Runs: pytest with coverage
- Reports to: Codecov
- Artifacts: coverage.xml, coverage reports
```

### Python Code Quality
```yaml
- Tools: Black, PyLint, Flake8, MyPy, Bandit, Safety
- Reports: Quality report artifact
- Scoring: PyLint score with fail-under=7.0
```

### CodeQL Security Scan
```yaml
- Analysis: Static security analysis
- Reports to: GitHub Security tab
- Schedule: Weekly on Mondays
- Artifacts: Security scan results
```

## Monitoring and Alerts

### 📧 **Notifications**
- GitHub will send email notifications for failed workflows
- You can customize notification settings in GitHub Settings

### 📱 **Mobile App**
- GitHub mobile app shows workflow status
- Push notifications for workflow results

### 🔔 **Slack/Teams Integration**
- Connect GitHub to Slack/Teams for workflow notifications
- Get real-time updates on build status

## Troubleshooting Failed Workflows

### Common Issues:
1. **Test Failures**: Check test logs in Actions tab
2. **Coverage Drop**: Review coverage reports in Codecov
3. **Quality Issues**: Check PyLint/Flake8 output in quality report
4. **Security Issues**: Review CodeQL alerts in Security tab

### Debug Steps:
1. Click on failed workflow run
2. Expand failed job
3. Check logs for specific error messages
4. Review artifacts for detailed reports
