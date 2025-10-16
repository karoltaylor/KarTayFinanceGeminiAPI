"""Pytest configuration and shared fixtures."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import uuid


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def unique_test_email():
    """Generate a unique test email address."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test_{unique_id}@example.com"


@pytest.fixture
def unique_test_username():
    """Generate a unique test username."""
    unique_id = str(uuid.uuid4())[:8]
    return f"testuser_{unique_id}"


@pytest.fixture
def sample_csv_content():
    """Sample CSV content with header not at top."""
    return """Financial Data Export
Report Generated: 2024-01-15

Account,Stock Name,Type,Trade Date,Price,Shares,Curr
MyWallet,AAPL,Stock,2024-01-10,150.50,10,USD
MyWallet,BTC,Crypto,2024-01-11,45000.00,0.5,USD
Savings,MSFT,Stock,2024-01-12,380.25,5,USD
"""


@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_content):
    """Create a sample CSV file."""
    filepath = temp_dir / "test_data.csv"
    filepath.write_text(sample_csv_content)
    return filepath


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "asset_name": ["AAPL", "BTC"],
            "date": ["2024-01-10", "2024-01-11"],
            "asset_price": [150.50, 45000.00],
            "volume": [10, 0.5],
            "transaction_amount": [1505.00, 22500.00],
            "fee": [5.0, 10.0],
            "currency": ["USD", "USD"],
        }
    )


@pytest.fixture
def valid_financial_record_data():
    """Valid data for creating TransactionRecord."""
    return {
        "asset_name": "AAPL",
        "date": "2024-01-10",
        "asset_price": 150.50,
        "volume": 10,
        "transaction_amount": 1505.00,
        "fee": 5.0,
        "currency": "USD",
    }


@pytest.fixture
def mock_genai_response():
    """Mock response from Google GenAI."""
    return {
        "wallet_name": "Account",
        "asset_name": "Stock Name",
        "asset_type": "Type",
        "date": "Trade Date",
        "asset_item_price": "Price",
        "volume": "Shares",
        "currency": "Curr",
    }


@pytest.fixture
def set_test_env_vars(monkeypatch):
    """Set test environment variables."""
    # Delete existing env vars first to ensure clean test state
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GENAI_MODEL", raising=False)
    # Set test values
    monkeypatch.setenv("GOOGLE_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("GENAI_MODEL", "gemini-1.5-flash")
