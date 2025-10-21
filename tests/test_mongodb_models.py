"""Tests for MongoDB models."""

import pytest
from datetime import datetime
from bson import ObjectId

from src.models import (
    Wallet,
    Asset,
    AssetType,
    AssetCurrentValue,
    Transaction,
    TransactionType,
    PyObjectId,
    TransactionRecord,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestWallet:
    """Tests for Wallet model."""

    def test_create_wallet_with_valid_data(self):
        """Test creating a wallet with valid data."""
        user_id = ObjectId()
        wallet = Wallet(user_id=user_id, name="My Savings", description="Personal savings wallet")

        assert wallet.name == "My Savings"
        assert wallet.description == "Personal savings wallet"
        assert wallet.user_id == user_id
        assert wallet.id is not None
        assert isinstance(wallet.id, ObjectId)
        assert isinstance(wallet.created_at, datetime)
        assert isinstance(wallet.updated_at, datetime)

    def test_create_wallet_without_description(self):
        """Test creating a wallet without description."""
        user_id = ObjectId()
        wallet = Wallet(user_id=user_id, name="Investment Portfolio")

        assert wallet.name == "Investment Portfolio"
        assert wallet.description is None

    def test_wallet_name_strips_whitespace(self):
        """Test that wallet name strips whitespace."""
        user_id = ObjectId()
        wallet = Wallet(user_id=user_id, name="  My Wallet  ")

        assert wallet.name == "My Wallet"

    def test_wallet_empty_name_raises_error(self):
        """Test that empty wallet name raises error."""
        user_id = ObjectId()
        with pytest.raises(ValueError, match="Wallet name cannot be empty"):
            Wallet(user_id=user_id, name="   ")


class TestAsset:
    """Tests for Asset model."""

    def test_create_asset_with_valid_data(self):
        """Test creating an asset with valid data."""
        asset = Asset(
            asset_name="Apple Inc.",
            asset_type=AssetType.STOCK,
            symbol="AAPL",
            url="https://api.example.com/stock/AAPL",
            description="Apple stock",
        )

        assert asset.asset_name == "Apple Inc."
        assert asset.asset_type == AssetType.STOCK
        assert asset.symbol == "AAPL"
        assert asset.url == "https://api.example.com/stock/AAPL"
        assert asset.id is not None

    def test_create_asset_with_minimal_data(self):
        """Test creating an asset with minimal required data."""
        asset = Asset(asset_name="Bitcoin", asset_type=AssetType.CRYPTOCURRENCY)

        assert asset.asset_name == "Bitcoin"
        assert asset.asset_type == AssetType.CRYPTOCURRENCY
        assert asset.symbol is None
        assert asset.url is None

    def test_asset_types_enum(self):
        """Test all asset types."""
        assert AssetType.BOND == "bond"
        assert AssetType.STOCK == "stock"
        assert AssetType.REAL_ESTATE == "real_estate"
        assert AssetType.CRYPTOCURRENCY == "cryptocurrency"

    def test_asset_invalid_url_raises_error(self):
        """Test that invalid URL raises error."""
        with pytest.raises(ValueError, match="URL must start with http"):
            Asset(
                asset_name="Test Asset",
                asset_type=AssetType.STOCK,
                url="invalid-url",
            )

    def test_asset_name_strips_whitespace(self):
        """Test that asset name strips whitespace."""
        asset = Asset(asset_name="  Tesla  ", asset_type=AssetType.STOCK)

        assert asset.asset_name == "Tesla"


class TestAssetCurrentValue:
    """Tests for AssetCurrentValue model."""

    def test_create_asset_value_with_valid_data(self):
        """Test creating an asset value with valid data."""
        asset_id = PyObjectId()
        value = AssetCurrentValue(
            asset_id=asset_id, date=datetime(2024, 1, 10), price=150.50, currency="USD"
        )

        assert value.asset_id == asset_id
        assert value.date == datetime(2024, 1, 10)
        assert value.price == 150.50
        assert value.currency == "USD"
        assert value.id is not None

    def test_asset_value_currency_uppercase(self):
        """Test that currency is converted to uppercase."""
        asset_id = PyObjectId()
        value = AssetCurrentValue(
            asset_id=asset_id, date=datetime(2024, 1, 10), price=100.0, currency="usd"
        )

        assert value.currency == "USD"

    def test_asset_value_invalid_currency_length(self):
        """Test that invalid currency length raises error."""
        from pydantic import ValidationError

        asset_id = PyObjectId()

        with pytest.raises(ValidationError):
            AssetCurrentValue(
                asset_id=asset_id,
                date=datetime(2024, 1, 10),
                price=100.0,
                currency="US",
            )

    def test_asset_value_negative_price_raises_error(self):
        """Test that negative price raises error."""
        asset_id = PyObjectId()

        with pytest.raises(ValueError):
            AssetCurrentValue(
                asset_id=asset_id,
                date=datetime(2024, 1, 10),
                price=-100.0,
                currency="USD",
            )

    def test_asset_value_parse_string_date(self):
        """Test parsing string date."""
        asset_id = PyObjectId()
        value = AssetCurrentValue(
            asset_id=asset_id, date="2024-01-10", price=100.0, currency="USD"
        )

        assert value.date == datetime(2024, 1, 10)


class TestTransaction:
    """Tests for Transaction model."""

    def test_create_transaction_with_valid_data(self):
        """Test creating a transaction with valid data."""
        wallet_id = PyObjectId()
        asset_id = PyObjectId()

        transaction = Transaction(
            wallet_id=wallet_id,
            asset_id=asset_id,
            date=datetime(2024, 1, 10),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=150.50,
            transaction_amount=1505.0,
            currency="USD",
            fee=5.0,
            notes="Bought AAPL stock",
        )

        assert transaction.wallet_id == wallet_id
        assert transaction.asset_id == asset_id
        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.volume == 10.0
        assert transaction.item_price == 150.50
        assert transaction.transaction_amount == 1505.0
        assert transaction.fee == 5.0

    def test_transaction_types_enum(self):
        """Test all transaction types."""
        assert TransactionType.BUY == "buy"
        assert TransactionType.SELL == "sell"
        assert TransactionType.TRANSFER_IN == "transfer_in"
        assert TransactionType.DIVIDEND == "dividend"

    def test_transaction_default_fee(self):
        """Test that fee defaults to 0.0."""
        wallet_id = PyObjectId()
        asset_id = PyObjectId()

        transaction = Transaction(
            wallet_id=wallet_id,
            asset_id=asset_id,
            date=datetime(2024, 1, 10),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=150.50,
            transaction_amount=1505.0,
            currency="USD",
        )

        assert transaction.fee == 0.0

    def test_transaction_from_transaction_record(self):
        """Test creating a transaction from TransactionRecord."""
        wallet_id = PyObjectId()
        asset_id = PyObjectId()

        # Create a TransactionRecord
        record = TransactionRecord(
            asset_name="AAPL",
            date=datetime(2024, 1, 10),
            asset_price=150.50,
            volume=10.0,
            transaction_amount=1505.00,
            fee=5.0,
            currency="USD",
            transaction_type="buy",
        )

        # Convert to Transaction
        transaction = Transaction.from_transaction_record(
            record=record,
            wallet_id=wallet_id,
            asset_id=asset_id,
            transaction_type=TransactionType.BUY,
        )

        assert transaction.wallet_id == wallet_id
        assert transaction.asset_id == asset_id
        assert transaction.date == record.date
        assert transaction.volume == record.volume
        assert transaction.item_price == record.asset_price
        assert transaction.transaction_amount == record.transaction_amount
        assert transaction.currency == record.currency
        assert transaction.fee == record.fee

    def test_transaction_negative_volume_raises_error(self):
        """Test that negative volume raises error."""
        wallet_id = PyObjectId()
        asset_id = PyObjectId()

        with pytest.raises(ValueError):
            Transaction(
                wallet_id=wallet_id,
                asset_id=asset_id,
                date=datetime(2024, 1, 10),
                transaction_type=TransactionType.BUY,
                volume=-10.0,
                item_price=150.50,
                transaction_amount=1505.0,
                currency="USD",
            )

    def test_transaction_currency_uppercase(self):
        """Test that currency is converted to uppercase."""
        wallet_id = PyObjectId()
        asset_id = PyObjectId()

        transaction = Transaction(
            wallet_id=wallet_id,
            asset_id=asset_id,
            date=datetime(2024, 1, 10),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=150.50,
            transaction_amount=1505.0,
            currency="usd",
        )

        assert transaction.currency == "USD"


class TestPyObjectId:
    """Tests for PyObjectId."""

    def test_create_pyobjectid(self):
        """Test creating a PyObjectId."""
        obj_id = PyObjectId()

        assert isinstance(obj_id, ObjectId)
        assert ObjectId.is_valid(obj_id)

    def test_validate_valid_objectid(self):
        """Test validating a valid ObjectId."""
        obj_id = ObjectId()
        validated = PyObjectId.validate(str(obj_id), None)

        assert isinstance(validated, ObjectId)

    def test_validate_invalid_objectid(self):
        """Test validating an invalid ObjectId."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate("invalid", None)
