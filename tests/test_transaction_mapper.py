"""Tests for TransactionMapper service."""

import pytest
import pandas as pd
from datetime import datetime

from src.services.transaction_mapper import TransactionMapper
from src.models import (
    TransactionRecord,
    Transaction,
    TransactionType,
    AssetType,
    PyObjectId,
)


class TestTransactionMapper:
    """Tests for TransactionMapper."""

    def test_calculate_asset_price_from_amount_and_volume(self):
        """Test calculating asset_price from transaction_amount and volume."""
        mapper = TransactionMapper()

        # DataFrame without asset_price
        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "2024-01-11"],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "currency": ["USD", "USD"],
            }
        )

        result_df = mapper.calculate_missing_values(df)

        assert "asset_price" in result_df.columns
        assert result_df.loc[0, "asset_price"] == 150.0  # 1500 / 10
        assert result_df.loc[1, "asset_price"] == 45000.0  # 22500 / 0.5

    def test_calculate_transaction_amount_from_price_and_volume(self):
        """Test calculating transaction_amount from asset_price and volume."""
        mapper = TransactionMapper()

        # DataFrame without transaction_amount
        df = pd.DataFrame(
            {
                "asset_name": ["AAPL"],
                "date": ["2024-01-10"],
                "asset_price": [150.0],
                "volume": [10.0],
                "currency": ["USD"],
            }
        )

        result_df = mapper.calculate_missing_values(df)

        assert "transaction_amount" in result_df.columns
        assert result_df.loc[0, "transaction_amount"] == 1500.0  # 150 * 10

    def test_add_default_fee_if_missing(self):
        """Test that fee is added with default value if missing."""
        mapper = TransactionMapper()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL"],
                "date": ["2024-01-10"],
                "asset_price": [150.0],
                "volume": [10.0],
                "transaction_amount": [1500.0],
                "currency": ["USD"],
            }
        )

        result_df = mapper.calculate_missing_values(df)

        assert "fee" in result_df.columns
        assert result_df.loc[0, "fee"] == 0.0

    def test_fill_missing_asset_price_values(self):
        """Test filling missing asset_price when some rows have it."""
        mapper = TransactionMapper()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "2024-01-11"],
                "asset_price": [150.0, None],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "currency": ["USD", "USD"],
            }
        )

        result_df = mapper.calculate_missing_values(df)

        assert result_df.loc[0, "asset_price"] == 150.0  # unchanged
        assert result_df.loc[1, "asset_price"] == 45000.0  # calculated

    def test_get_or_create_wallet_in_memory(self):
        """Test creating wallet in memory."""
        mapper = TransactionMapper()

        wallet_id = mapper.get_or_create_wallet("Test Wallet")

        assert isinstance(wallet_id, PyObjectId)
        assert "Test Wallet" in mapper._wallet_cache

        # Should return same ID for same name
        wallet_id2 = mapper.get_or_create_wallet("Test Wallet")
        assert wallet_id == wallet_id2

    def test_get_or_create_asset_in_memory(self):
        """Test creating asset in memory."""
        mapper = TransactionMapper()

        asset_id = mapper.get_or_create_asset("AAPL", AssetType.STOCK, symbol="AAPL")

        assert isinstance(asset_id, PyObjectId)
        cache_key = f"AAPL:{AssetType.STOCK.value}"
        assert cache_key in mapper._asset_cache

        # Should return same ID for same asset
        asset_id2 = mapper.get_or_create_asset("AAPL", AssetType.STOCK)
        assert asset_id == asset_id2

    def test_dataframe_to_transactions(self):
        """Test converting DataFrame to Transaction models."""
        mapper = TransactionMapper()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "2024-01-11"],
                "asset_price": [150.0, 45000.0],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "fee": [5.0, 10.0],
                "currency": ["USD", "USD"],
            }
        )

        transactions = mapper.dataframe_to_transactions(
            df=df,
            wallet_name="My Wallet",
            transaction_type=TransactionType.BUY,
            asset_type=AssetType.STOCK,
        )

        assert len(transactions) == 2
        assert all(isinstance(t, Transaction) for t in transactions)
        assert transactions[0].volume == 10.0
        assert transactions[0].item_price == 150.0
        assert transactions[0].transaction_amount == 1500.0
        assert transactions[0].fee == 5.0
        assert transactions[1].volume == 0.5
        assert transactions[1].item_price == 45000.0

    def test_dataframe_to_transactions_with_missing_asset_price(self):
        """Test conversion when asset_price needs to be calculated."""
        mapper = TransactionMapper()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL"],
                "date": ["2024-01-10"],
                "volume": [10.0],
                "transaction_amount": [1500.0],
                "currency": ["USD"],
            }
        )

        transactions = mapper.dataframe_to_transactions(
            df=df, wallet_name="My Wallet", transaction_type=TransactionType.BUY
        )

        assert len(transactions) == 1
        assert transactions[0].item_price == 150.0  # Calculated: 1500 / 10

    def test_transaction_records_to_transactions(self):
        """Test converting TransactionRecord list to Transaction models."""
        mapper = TransactionMapper()

        records = [
            TransactionRecord(
                asset_name="AAPL",
                date=datetime(2024, 1, 10),
                asset_price=150.0,
                volume=10.0,
                transaction_amount=1500.0,
                fee=5.0,
                currency="USD",
            ),
            TransactionRecord(
                asset_name="BTC",
                date=datetime(2024, 1, 11),
                asset_price=45000.0,
                volume=0.5,
                transaction_amount=22500.0,
                fee=10.0,
                currency="USD",
            ),
        ]

        transactions = mapper.transaction_records_to_transactions(
            records=records,
            wallet_name="Investment Wallet",
            transaction_type=TransactionType.BUY,
            asset_type=AssetType.STOCK,
        )

        assert len(transactions) == 2
        assert all(isinstance(t, Transaction) for t in transactions)
        assert transactions[0].volume == 10.0
        assert transactions[1].volume == 0.5

    def test_clear_cache(self):
        """Test clearing wallet and asset caches."""
        mapper = TransactionMapper()

        # Create some cached entries
        mapper.get_or_create_wallet("Wallet1")
        mapper.get_or_create_asset("AAPL", AssetType.STOCK)

        assert len(mapper._wallet_cache) > 0
        assert len(mapper._asset_cache) > 0

        # Clear cache
        mapper.clear_cache()

        assert len(mapper._wallet_cache) == 0
        assert len(mapper._asset_cache) == 0

    def test_dataframe_with_invalid_rows(self):
        """Test handling DataFrame with some invalid rows."""
        mapper = TransactionMapper()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "invalid-date"],
                "asset_price": [150.0, 45000.0],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "currency": ["USD", "USD"],
            }
        )

        transactions = mapper.dataframe_to_transactions(df=df, wallet_name="My Wallet")

        # Only valid rows should be converted
        assert len(transactions) == 1
        assert transactions[0].volume == 10.0
