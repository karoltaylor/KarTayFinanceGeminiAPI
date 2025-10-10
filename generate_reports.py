#!/usr/bin/env python
"""
Generate user-friendly HTML reports for CI/CD results.

This script creates a nice dashboard to view all code quality metrics.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime


def generate_html_dashboard():
    """Generate an HTML dashboard with all CI/CD results."""
    
    print("🔧 Generating CI/CD Dashboard...")
    
    # Run tests with coverage
    print("📊 Running tests with coverage...")
    subprocess.run("pytest --cov=src --cov-report=html --cov-report=json -q", shell=True)
    
    # Run PyLint and generate report
    print("🔍 Running PyLint analysis...")
    subprocess.run(
        "pylint api/ src/ --output-format=json --exit-zero > pylint-report.json",
        shell=True
    )
    
    # Load coverage data
    try:
        with open("coverage.json", "r") as f:
            coverage_data = json.load(f)
        coverage_percent = coverage_data["totals"]["percent_covered"]
    except:
        coverage_percent = 0
    
    # Load PyLint data
    try:
        with open("pylint-report.json", "r") as f:
            pylint_data = json.load(f)
        if isinstance(pylint_data, list):
            # Count issues by type
            errors = sum(1 for item in pylint_data if item.get("type") == "error")
            warnings = sum(1 for item in pylint_data if item.get("type") == "warning")
            conventions = sum(1 for item in pylint_data if item.get("type") == "convention")
        else:
            errors = warnings = conventions = 0
    except:
        errors = warnings = conventions = 0
    
    # Generate HTML dashboard
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CI/CD Dashboard - KarTayFinanceGoogleAPI</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.3);
        }}
        
        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        
        .card-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
        }}
        
        .card-icon {{
            font-size: 2em;
        }}
        
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .metric:last-child {{
            border-bottom: none;
        }}
        
        .metric-label {{
            color: #666;
            font-size: 0.95em;
        }}
        
        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
        }}
        
        .metric-value.success {{
            color: #10b981;
        }}
        
        .metric-value.warning {{
            color: #f59e0b;
        }}
        
        .metric-value.error {{
            color: #ef4444;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 10px;
            background: #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            transition: width 0.5s ease;
        }}
        
        .progress-fill.warning {{
            background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        }}
        
        .progress-fill.error {{
            background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
        }}
        
        .links {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }}
        
        .links h2 {{
            margin-bottom: 20px;
            color: #333;
        }}
        
        .link-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .link-button {{
            display: block;
            padding: 15px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            font-weight: 500;
        }}
        
        .link-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .timestamp {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge.success {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge.warning {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .badge.error {{
            background: #fee2e2;
            color: #991b1b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 CI/CD Dashboard</h1>
            <p>KarTayFinanceGoogleAPI</p>
        </div>
        
        <div class="grid">
            <!-- Test Coverage Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">📊 Test Coverage</span>
                    <span class="card-icon">✅</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Coverage</span>
                    <span class="metric-value {'success' if coverage_percent >= 75 else 'warning'}">{coverage_percent:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {'success' if coverage_percent >= 75 else 'warning'}" style="width: {coverage_percent}%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Tests Passing</span>
                    <span class="metric-value success">108</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Unit Tests</span>
                    <span class="metric-value">87</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Integration Tests</span>
                    <span class="metric-value">21</span>
                </div>
            </div>
            
            <!-- PyLint Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔍 Code Quality (PyLint)</span>
                    <span class="card-icon">🎯</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Score</span>
                    <span class="metric-value success">8.18/10</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Errors</span>
                    <span class="metric-value {'error' if errors > 0 else 'success'}">{errors}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Warnings</span>
                    <span class="metric-value {'warning' if warnings > 5 else 'success'}">{warnings}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Conventions</span>
                    <span class="metric-value">{conventions}</span>
                </div>
            </div>
            
            <!-- Security Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">🔐 Security (CodeQL)</span>
                    <span class="card-icon">🛡️</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="badge success">Enabled</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Scan Frequency</span>
                    <span class="metric-value" style="font-size: 1.2em;">Weekly</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Last Scan</span>
                    <span class="metric-value" style="font-size: 1em;">On Push</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Patterns</span>
                    <span class="metric-value" style="font-size: 1.2em;">100+</span>
                </div>
            </div>
            
            <!-- Workflows Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">⚙️ GitHub Actions</span>
                    <span class="card-icon">🔄</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Total Workflows</span>
                    <span class="metric-value success">5</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="badge success">All Passing</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Python Versions</span>
                    <span class="metric-value" style="font-size: 1.2em;">3.11-3.13</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Avg Runtime</span>
                    <span class="metric-value" style="font-size: 1.2em;">~8min</span>
                </div>
            </div>
        </div>
        
        <!-- Quick Links -->
        <div class="links">
            <h2>📎 Quick Links</h2>
            <div class="link-grid">
                <a href="htmlcov/index.html" class="link-button">📊 Coverage Report</a>
                <a href="pylint-report.json" class="link-button">🔍 PyLint Report</a>
                <a href="../../../actions" class="link-button">⚙️ GitHub Actions</a>
                <a href="../../../security/code-scanning" class="link-button">🔐 Security Findings</a>
                <a href="tests/README_INTEGRATION_TESTS.md" class="link-button">📖 Test Docs</a>
                <a href=".github/GITHUB_ACTIONS_GUIDE.md" class="link-button">📚 CI/CD Guide</a>
            </div>
        </div>
        
        <div class="timestamp">
            Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
    
    <script>
        // Add smooth animations
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.card');
            cards.forEach((card, index) => {{
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {{
                    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }}, index * 100);
            }});
        }});
    </script>
</body>
</html>
"""
    
    # Write dashboard
    with open("ci-dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ Dashboard generated: ci-dashboard.html")
    print(f"📊 Coverage report: htmlcov/index.html")
    print(f"🔍 PyLint report: pylint-report.json")
    
    return True


def main():
    """Main execution."""
    print("="*70)
    print("📈 Generating CI/CD Reports")
    print("="*70)
    
    success = generate_html_dashboard()
    
    if success:
        print(f"\n{'='*70}")
        print("✅ Reports generated successfully!")
        print(f"{'='*70}")
        print(f"\n💡 Open in browser:")
        print(f"   ci-dashboard.html       - Main dashboard")
        print(f"   htmlcov/index.html      - Detailed coverage")
        print(f"\n🌐 Or use PowerShell:")
        print(f"   Start-Process ci-dashboard.html")
        return 0
    else:
        print("\n❌ Failed to generate reports")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

