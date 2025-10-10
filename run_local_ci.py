#!/usr/bin/env python
"""
Local CI script to run checks before pushing to GitHub.

This script mimics what GitHub Actions will do, so you can catch issues early.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, exit_on_error=False):
    """Run a shell command and report results."""
    print(f"\n{'='*70}")
    print(f"🔧 {description}")
    print(f"{'='*70}")
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode != 0:
        print(f"❌ {description} FAILED (exit code: {result.returncode})")
        if exit_on_error:
            sys.exit(1)
        return False
    else:
        print(f"✅ {description} PASSED")
        return True


def main():
    """Run all CI checks locally."""
    print("="*70)
    print("🚀 Running Local CI Checks")
    print("="*70)
    
    results = {}
    
    # 1. Check YAML syntax
    results['yaml'] = run_command(
        'python -c "import yaml; '
        'files = [\'.github/workflows/ci.yml\', \'.github/workflows/codeql.yml\', '
        '\'.github/workflows/pylint.yml\', \'.github/workflows/tests.yml\']; '
        '[yaml.safe_load(open(f)) for f in files]; '
        'print(\'YAML files valid\')"',
        "Validating GitHub Actions YAML files"
    )
    
    # 2. Run PyLint
    results['pylint'] = run_command(
        "pylint api/ src/ --max-line-length=120 --exit-zero",
        "Running PyLint code analysis"
    )
    
    # 3. Check code formatting with Black
    print(f"\n{'='*70}")
    print("🎨 Checking code formatting with Black (informational)")
    print(f"{'='*70}")
    subprocess.run("black --check --diff api/ src/ tests/", shell=True)
    print("💡 To fix formatting, run: black api/ src/ tests/")
    
    # 4. Run all tests (unit + integration)
    results['all_tests'] = run_command(
        'pytest --cov=src --cov-report=term-missing -q',
        "Running all tests with coverage",
        exit_on_error=True
    )
    
    # 6. Security scan with Bandit (if installed)
    try:
        results['security'] = run_command(
            "bandit -r api/ src/ -ll --skip B101,B601",
            "Running Bandit security scan"
        )
    except Exception:
        print("⚠️  Bandit not installed, skipping security scan")
        print("   Install with: pip install bandit")
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 LOCAL CI SUMMARY")
    print(f"{'='*70}")
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n🎉 All checks passed! Ready to push to GitHub.")
        print(f"\n💡 Next steps:")
        print(f"   git add .")
        print(f"   git commit -m \"Add GitHub Actions workflows\"")
        print(f"   git push")
        return 0
    else:
        print(f"\n❌ Some checks failed. Please fix issues before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

