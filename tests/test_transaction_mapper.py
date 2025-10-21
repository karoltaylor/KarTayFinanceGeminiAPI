"""Tests for TransactionMapper service."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch

from src.services.transaction_mapper import TransactionMapper
from src.models import (
    TransactionRecord,
    Transaction,
    TransactionType,
    AssetType,
    PyObjectId,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit
from bson import ObjectId


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
        user_id = ObjectId()

        wallet_id = mapper.get_or_create_wallet("Test Wallet", user_id)

        assert isinstance(wallet_id, PyObjectId)
        # Cache key format is now "user_id:wallet_name"
        cache_key = f"{str(user_id)}:Test Wallet"
        assert cache_key in mapper._wallet_cache

        # Should return same ID for same name and user
        wallet_id2 = mapper.get_or_create_wallet("Test Wallet", user_id)
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
        user_id = ObjectId()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "2024-01-11"],
                "asset_price": [150.0, 45000.0],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "fee": [5.0, 10.0],
                "currency": ["USD", "USD"],
                "transaction_type": ["buy", "sell"],
            }
        )

        wallet_id = ObjectId()  # Mock wallet ID
        transactions, errors = mapper.dataframe_to_transactions(
            df=df,
            wallet_id=wallet_id,
            user_id=user_id,
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
        user_id = ObjectId()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL"],
                "date": ["2024-01-10"],
                "volume": [10.0],
                "transaction_amount": [1500.0],
                "currency": ["USD"],
                "transaction_type": ["buy"],
            }
        )

        wallet_id = ObjectId()  # Mock wallet ID
        transactions, errors = mapper.dataframe_to_transactions(
            df=df, wallet_id=wallet_id, user_id=user_id
        )

        assert len(transactions) == 1
        assert transactions[0].item_price == 150.0  # Calculated: 1500 / 10

    def test_transaction_records_to_transactions(self):
        """Test converting TransactionRecord list to Transaction models."""
        mapper = TransactionMapper()
        user_id = ObjectId()

        records = [
            TransactionRecord(
                asset_name="AAPL",
                date=datetime(2024, 1, 10),
                asset_price=150.0,
                volume=10.0,
                transaction_amount=1500.0,
                fee=5.0,
                currency="USD",
                transaction_type="buy",
            ),
            TransactionRecord(
                asset_name="BTC",
                date=datetime(2024, 1, 11),
                asset_price=45000.0,
                volume=0.5,
                transaction_amount=22500.0,
                fee=10.0,
                currency="USD",
                transaction_type="sell",
            ),
        ]

        wallet_id = ObjectId()  # Mock wallet ID
        transactions = mapper.transaction_records_to_transactions(
            records=records,
            wallet_id=wallet_id,
            user_id=user_id,
        )

        assert len(transactions) == 2
        assert all(isinstance(t, Transaction) for t in transactions)
        assert transactions[0].volume == 10.0
        assert transactions[1].volume == 0.5

    def test_clear_cache(self):
        """Test clearing wallet and asset caches."""
        mapper = TransactionMapper()
        user_id = ObjectId()

        # Create some cached entries
        mapper.get_or_create_wallet("Wallet1", user_id)
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
        user_id = ObjectId()

        df = pd.DataFrame(
            {
                "asset_name": ["AAPL", "BTC"],
                "date": ["2024-01-10", "invalid-date"],
                "asset_price": [150.0, 45000.0],
                "volume": [10.0, 0.5],
                "transaction_amount": [1500.0, 22500.0],
                "currency": ["USD", "USD"],
                "transaction_type": ["buy", "sell"],
            }
        )

        wallet_id = ObjectId()  # Mock wallet ID
        transactions, errors = mapper.dataframe_to_transactions(
            df=df, wallet_id=wallet_id, user_id=user_id
        )

        # Only valid rows should be converted
        assert len(transactions) == 1
        assert transactions[0].volume == 10.0

    @pytest.fixture
    def mock_asset_type_mapper(self):
        """Mock AssetTypeMapper for testing."""
        mock_mapper = Mock()
        return mock_mapper

    def test_init_with_api_credentials(self, set_test_env_vars):
        """Test TransactionMapper initialization with API credentials."""
        mapper = TransactionMapper(api_key="test_key", model_name="test_model")
        assert mapper.asset_type_mapper is not None
        assert mapper.asset_type_mapper.api_key == "test_key"
        assert mapper.asset_type_mapper.model_name == "test_model"

    @patch("src.services.asset_type_mapper.Settings")
    def test_init_without_api_credentials_uses_settings(
        self, mock_settings, monkeypatch
    ):
        """Test TransactionMapper initialization without API credentials uses Settings."""
        # Mock Settings to return test values
        mock_settings.GOOGLE_API_KEY = "test_api_key_12345"
        mock_settings.GENAI_MODEL = "gemini-1.5-flash"

        mapper = TransactionMapper()
        assert mapper.asset_type_mapper is not None
        assert mapper.asset_type_mapper.api_key == "test_api_key_12345"
        assert mapper.asset_type_mapper.model_name == "gemini-1.5-flash"

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_with_ai_inference_success(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test asset creation with successful AI inference."""
        # Setup mock
        mock_mapper = Mock()
        mock_mapper.infer_asset_info.return_value = {
            "asset_type": "stock",
            "symbol": "AAPL",
        }
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Mock assets collection
        mock_collection = Mock()
        mock_collection.find_one.return_value = None  # Asset doesn't exist
        mock_collection.insert_one.return_value.inserted_id = ObjectId()

        asset_id = mapper.get_or_create_asset(
            asset_name="Apple Inc.",
            asset_type=AssetType.OTHER,  # Will be overridden by AI
            assets_collection=mock_collection,
        )

        # Verify AI was called
        mock_mapper.infer_asset_info.assert_called_once_with("Apple Inc.")

        # Verify asset was created with AI-determined values
        mock_collection.insert_one.assert_called_once()
        created_asset = mock_collection.insert_one.call_args[0][0]
        assert created_asset["asset_name"] == "Apple Inc."
        assert created_asset["asset_type"] == "stock"
        assert created_asset["symbol"] == "AAPL"

        assert asset_id is not None

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_with_ai_inference_failure(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test asset creation with AI inference failure falls back to provided values."""
        # Setup mock
        mock_mapper = Mock()
        mock_mapper.infer_asset_info.return_value = None  # AI fails
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Mock assets collection
        mock_collection = Mock()
        mock_collection.find_one.return_value = None  # Asset doesn't exist
        mock_collection.insert_one.return_value.inserted_id = ObjectId()

        asset_id = mapper.get_or_create_asset(
            asset_name="Unknown Asset",
            asset_type=AssetType.OTHER,
            symbol="UNKNOWN",
            assets_collection=mock_collection,
        )

        # Verify AI was called
        mock_mapper.infer_asset_info.assert_called_once_with("Unknown Asset")

        # Verify asset was created with fallback values
        mock_collection.insert_one.assert_called_once()
        created_asset = mock_collection.insert_one.call_args[0][0]
        assert created_asset["asset_name"] == "Unknown Asset"
        assert created_asset["asset_type"] == "other"  # Fallback to OTHER
        assert created_asset["symbol"] == "UNKNOWN"

        assert asset_id is not None

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_existing_asset_skips_ai(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test that existing assets skip AI inference."""
        # Setup mock
        mock_mapper = Mock()
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Mock assets collection - asset already exists
        existing_asset = {
            "_id": ObjectId(),
            "asset_name": "Apple Inc.",
            "asset_type": "stock",
        }
        mock_collection = Mock()
        mock_collection.find_one.return_value = existing_asset

        asset_id = mapper.get_or_create_asset(
            asset_name="Apple Inc.",
            asset_type=AssetType.OTHER,
            assets_collection=mock_collection,
        )

        # Verify AI was NOT called for existing asset
        mock_mapper.infer_asset_info.assert_not_called()

        # Verify asset was not inserted (already exists)
        mock_collection.insert_one.assert_not_called()

        assert asset_id == PyObjectId(existing_asset["_id"])

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_cached_asset_skips_ai(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test that cached assets skip AI inference."""
        # Setup mock
        mock_mapper = Mock()
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Pre-populate cache
        cached_asset_id = PyObjectId()
        cache_key = "Apple Inc.:other"
        mapper._asset_cache[cache_key] = cached_asset_id

        asset_id = mapper.get_or_create_asset(
            asset_name="Apple Inc.", asset_type=AssetType.OTHER
        )

        # Verify AI was NOT called for cached asset
        mock_mapper.infer_asset_info.assert_not_called()

        assert asset_id == cached_asset_id

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_ai_provides_symbol(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test that AI-provided symbol is used when available."""
        # Setup mock
        mock_mapper = Mock()
        mock_mapper.infer_asset_info.return_value = {
            "asset_type": "cryptocurrency",
            "symbol": "BTC",
        }
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Mock assets collection
        mock_collection = Mock()
        mock_collection.find_one.return_value = None  # Asset doesn't exist
        mock_collection.insert_one.return_value.inserted_id = ObjectId()

        asset_id = mapper.get_or_create_asset(
            asset_name="Bitcoin",
            asset_type=AssetType.OTHER,
            symbol="UNKNOWN",  # Should be overridden by AI
            assets_collection=mock_collection,
        )

        # Verify asset was created with AI-provided symbol
        created_asset = mock_collection.insert_one.call_args[0][0]
        assert created_asset["symbol"] == "BTC"

    @patch("src.services.transaction_mapper.AssetTypeMapper")
    def test_get_or_create_asset_ai_empty_symbol_uses_provided(
        self, mock_asset_type_mapper_class, set_test_env_vars
    ):
        """Test that when AI returns empty symbol, provided symbol is used."""
        # Setup mock
        mock_mapper = Mock()
        mock_mapper.infer_asset_info.return_value = {"asset_type": "bond", "symbol": ""}
        mock_asset_type_mapper_class.return_value = mock_mapper

        mapper = TransactionMapper()
        mapper.asset_type_mapper = mock_mapper

        # Mock assets collection
        mock_collection = Mock()
        mock_collection.find_one.return_value = None  # Asset doesn't exist
        mock_collection.insert_one.return_value.inserted_id = ObjectId()

        asset_id = mapper.get_or_create_asset(
            asset_name="US Treasury Bond",
            asset_type=AssetType.OTHER,
            symbol="TREASURY",
            assets_collection=mock_collection,
        )

        # Verify asset was created with provided symbol (AI returned empty)
        created_asset = mock_collection.insert_one.call_args[0][0]
        assert created_asset["symbol"] == "TREASURY"
