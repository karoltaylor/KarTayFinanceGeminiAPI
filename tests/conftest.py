"""Pytest configuration and shared fixtures."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import uuid
import os
from unittest.mock import MagicMock, patch


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

Account,Stock Name,Type,Trade Date,Price,Shares,Curr,Transaction Type
MyWallet,AAPL,Stock,2024-01-10,150.50,10,USD,buy
MyWallet,BTC,Crypto,2024-01-11,45000.00,0.5,USD,sell
Savings,MSFT,Stock,2024-01-12,380.25,5,USD,buy
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
            "transaction_type": ["buy", "sell"],
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
        "transaction_type": "buy",
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


@pytest.fixture(autouse=True)
def mock_ai_calls_if_needed(monkeypatch):
    """
    Automatically mock AI calls unless USE_REAL_AI=true is set.
    
    This speeds up tests significantly by avoiding network calls to Google Gemini API.
    To test with real AI, set environment variable: USE_REAL_AI=true
    """
    use_real_ai = os.getenv("USE_REAL_AI", "false").lower() == "true"
    
    if not use_real_ai:
        # Mock the ColumnMapper.map_columns method
        def mock_map_columns(self, source_df, target_columns, sample_rows=5, file_type="csv"):
            """
            Mock column mapping with intelligent fallback logic.
            
            Tries to match columns by name similarity and common patterns.
            """
            if source_df.empty:
                raise ValueError("Cannot map columns from empty DataFrame")
            
            source_columns = [str(col).lower() for col in source_df.columns]
            mapping = {}
            
            # Common column name patterns for different target columns
            column_patterns = {
                "wallet_name": ["account", "wallet", "portfel", "konto"],
                "asset_name": ["stock", "asset", "symbol", "ticker", "nazwa", "instrument", "papier"],
                "asset_type": ["type", "asset_type", "typ", "rodzaj"],
                "date": ["date", "data", "trade_date", "transaction_date", "dt"],
                "transaction_type": ["transaction_type", "typ_transakcji", "typ", "type"],
                "asset_item_price": ["price", "cena", "kurs", "item_price", "unit_price", "asset_price"],
                "volume": ["volume", "quantity", "shares", "amount", "ilosc", "liczba"],
                "transaction_amount": ["total", "amount", "transaction_amount", "wartosc", "kwota"],
                "fee": ["fee", "commission", "prowizja", "oplata"],
                "currency": ["currency", "curr", "waluta", "ccy"],
                "notes": ["notes", "description", "uwagi", "opis", "comment"],
            }
            
            # Try to match each target column
            for target_col in target_columns:
                target_lower = target_col.lower()
                patterns = column_patterns.get(target_col, [target_lower])
                
                # Try exact match first
                for i, src_col in enumerate(source_columns):
                    if src_col == target_lower:
                        mapping[target_col] = source_df.columns[i]
                        break
                
                # If no exact match, try pattern matching
                if target_col not in mapping:
                    for pattern in patterns:
                        for i, src_col in enumerate(source_columns):
                            if pattern in src_col or src_col in pattern:
                                mapping[target_col] = source_df.columns[i]
                                break
                        if target_col in mapping:
                            break
            
            return mapping
        
        # Patch the ColumnMapper class
        from src.services.column_mapper import ColumnMapper
        monkeypatch.setattr(ColumnMapper, "map_columns", mock_map_columns)
        
        # Also mock the __init__ to avoid requiring API key
        def mock_init(self, api_key=None, model_name=None, db=None, user_id=None):
            self.api_key = api_key or "mock_key"
            self.model_name = model_name or "mock_model"
            self.db = db
            self.user_id = user_id
            self.cache_version = 1
            self.model = MagicMock()
        
        monkeypatch.setattr(ColumnMapper, "__init__", mock_init)
