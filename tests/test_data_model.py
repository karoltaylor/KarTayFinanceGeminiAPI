"""Tests for data models."""

import pytest
from datetime import datetime
import pandas as pd

from src.models.data_model import FinancialRecord, FinancialDataModel


class TestFinancialRecord:
    """Tests for FinancialRecord model."""

    def test_create_valid_record(self, valid_financial_record_data):
        """Test creating a valid financial record."""
        record = FinancialRecord(**valid_financial_record_data)

        assert record.wallet_name == "MyWallet"
        assert record.asset_name == "AAPL"
        assert record.asset_type == "Stock"
        assert isinstance(record.date, datetime)
        assert record.asset_item_price == 150.50
        assert record.volume == 10
        assert record.currency == "USD"

    def test_date_parsing_multiple_formats(self):
        """Test that various date formats are parsed correctly."""
        date_formats = [
            ("2024-01-10", "YYYY-MM-DD"),
            ("10/01/2024", "DD/MM/YYYY"),
            ("01/10/2024", "MM/DD/YYYY"),
        ]

        for date_str, _ in date_formats:
            data = {
                "wallet_name": "Test",
                "asset_name": "Test",
                "asset_type": "Test",
                "date": date_str,
                "asset_item_price": 100.0,
                "volume": 1,
                "currency": "USD",
            }
            record = FinancialRecord(**data)
            assert isinstance(record.date, datetime)

    def test_negative_price_raises_error(self, valid_financial_record_data):
        """Test that negative prices are rejected."""
        valid_financial_record_data["asset_item_price"] = -100.0

        with pytest.raises(ValueError, match="must be non-negative"):
            FinancialRecord(**valid_financial_record_data)

    def test_negative_volume_raises_error(self, valid_financial_record_data):
        """Test that negative volume values are rejected."""
        valid_financial_record_data["volume"] = -5

        with pytest.raises(ValueError, match="must be non-negative"):
            FinancialRecord(**valid_financial_record_data)

    def test_empty_wallet_name_raises_error(self, valid_financial_record_data):
        """Test that empty wallet name is rejected."""
        valid_financial_record_data["wallet_name"] = ""

        with pytest.raises(ValueError):
            FinancialRecord(**valid_financial_record_data)

    def test_invalid_date_raises_error(self, valid_financial_record_data):
        """Test that invalid date format raises error."""
        valid_financial_record_data["date"] = "not-a-date"

        with pytest.raises(ValueError, match="Unable to parse date"):
            FinancialRecord(**valid_financial_record_data)


class TestFinancialDataModel:
    """Tests for FinancialDataModel."""

    def test_initialize_empty_model(self):
        """Test initializing an empty data model."""
        model = FinancialDataModel()

        assert len(model.df) == 0
        assert list(model.df.columns) == model.columns

    def test_add_single_record(self, valid_financial_record_data):
        """Test adding a single record."""
        model = FinancialDataModel()
        record = FinancialRecord(**valid_financial_record_data)

        model.add_record(record)

        assert len(model.df) == 1
        assert model.df.iloc[0]["wallet_name"] == "MyWallet"

    def test_add_multiple_records(self, valid_financial_record_data):
        """Test adding multiple records at once."""
        model = FinancialDataModel()
        records = [
            FinancialRecord(**valid_financial_record_data),
            FinancialRecord(
                **{**valid_financial_record_data, "wallet_name": "Wallet2"}
            ),
        ]

        model.add_records(records)

        assert len(model.df) == 2
        assert model.df.iloc[1]["wallet_name"] == "Wallet2"

    def test_load_from_dataframe_valid(self, sample_dataframe):
        """Test loading valid data from DataFrame."""
        model = FinancialDataModel()
        errors = model.load_from_dataframe(sample_dataframe)

        assert len(errors) == 0
        assert len(model.df) == 2

    def test_load_from_dataframe_with_invalid_rows(self):
        """Test loading DataFrame with some invalid rows."""
        df = pd.DataFrame(
            {
                "wallet_name": ["Valid", ""],
                "asset_name": ["AAPL", "BTC"],
                "asset_type": ["Stock", "Crypto"],
                "date": ["2024-01-10", "2024-01-11"],
                "asset_item_price": [150.50, -100.0],  # negative price
                "volume": [10, 0.5],
                "currency": ["USD", "USD"],
            }
        )

        model = FinancialDataModel()
        errors = model.load_from_dataframe(df)

        assert len(errors) > 0
        assert len(model.df) < 2  # Some records should be rejected

    def test_to_dataframe(self, valid_financial_record_data):
        """Test exporting to DataFrame."""
        model = FinancialDataModel()
        record = FinancialRecord(**valid_financial_record_data)
        model.add_record(record)

        df = model.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "wallet_name" in df.columns

    def test_get_summary_empty(self):
        """Test summary of empty model."""
        model = FinancialDataModel()
        summary = model.get_summary()

        assert summary["total_records"] == 0
        assert summary["unique_wallets"] == 0

    def test_get_summary_with_data(self, sample_dataframe):
        """Test summary with data."""
        model = FinancialDataModel()
        model.load_from_dataframe(sample_dataframe)
        summary = model.get_summary()

        assert summary["total_records"] == 2
        assert summary["unique_wallets"] == 2
        assert summary["unique_assets"] == 2

    def test_to_csv(self, tmp_path, valid_financial_record_data):
        """Test exporting to CSV."""
        model = FinancialDataModel()
        record = FinancialRecord(**valid_financial_record_data)
        model.add_record(record)

        filepath = tmp_path / "output.csv"
        model.to_csv(str(filepath))

        assert filepath.exists()
        loaded = pd.read_csv(filepath)
        assert len(loaded) == 1
