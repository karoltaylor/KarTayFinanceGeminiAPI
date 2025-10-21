"""Comprehensive database field validation tests."""

import pytest
from datetime import datetime
from bson import ObjectId
from pydantic import ValidationError

from src.models.mongodb_models import (
    User, Wallet, Asset, AssetCurrentValue, Transaction, TransactionError,
    AssetType, TransactionType, PyObjectId
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestUserFieldValidation:
    """Tests for User model field validation."""

    def test_email_validation_valid_formats(self):
        """Test valid email formats."""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "user+tag@example.org",
            "123@test.com"
        ]
        
        for email in valid_emails:
            user = User(
                email=email,
                username="testuser",
                full_name="Test User"
            )
            assert user.email == email.lower().strip()

    def test_email_validation_invalid_formats(self):
        """Test invalid email formats."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com",
            "user@domain.",
            ""  # Removed "user@domain.c" as it's actually valid (single char TLD)
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                User(
                    email=email,
                    username="testuser",
                    full_name="Test User"
                )

    def test_email_normalization(self):
        """Test email normalization (lowercase, strip)."""
        user = User(
            email="  USER@EXAMPLE.COM  ",
            username="testuser",
            full_name="Test User"
        )
        assert user.email == "user@example.com"

    def test_username_validation_valid(self):
        """Test valid username formats."""
        valid_usernames = [
            "testuser",
            "user123",
            "test_user",
            "user-test",
            "TestUser123"
        ]
        
        for username in valid_usernames:
            user = User(
                email="test@example.com",
                username=username,
                full_name="Test User"
            )
            assert user.username == username.lower().strip()

    def test_username_validation_invalid(self):
        """Test invalid username formats."""
        invalid_usernames = [
            "user@test",  # Contains @
            "user.test",  # Contains .
            "user test",  # Contains space
            "user#test",  # Contains #
            "user$test",  # Contains $
            "ab",         # Too short
            "a" * 51,     # Too long
            ""
        ]
        
        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                User(
                    email="test@example.com",
                    username=username,
                    full_name="Test User"
                )

    def test_username_normalization(self):
        """Test username normalization."""
        user = User(
            email="test@example.com",
            username="  TEST_USER  ",
            full_name="Test User"
        )
        assert user.username == "test_user"

    def test_user_field_length_constraints(self):
        """Test field length constraints."""
        # Email too long
        with pytest.raises(ValidationError):
            User(
                email="a" * 256 + "@example.com",
                username="testuser",
                full_name="Test User"
            )
        
        # Username too long
        with pytest.raises(ValidationError):
            User(
                email="test@example.com",
                username="a" * 51,
                full_name="Test User"
            )
        
        # Full name too long
        with pytest.raises(ValidationError):
            User(
                email="test@example.com",
                username="testuser",
                full_name="a" * 201
            )


class TestWalletFieldValidation:
    """Tests for Wallet model field validation."""

    def test_wallet_name_validation(self):
        """Test wallet name validation."""
        # Valid names
        valid_names = [
            "My Wallet",
            "Investment Portfolio",
            "Savings Account",
            "Wallet 123"
        ]
        
        for name in valid_names:
            wallet = Wallet(
                user_id=ObjectId(),
                name=name,
                description="Test wallet"
            )
            assert wallet.name == name.strip()

    def test_wallet_name_whitespace_stripping(self):
        """Test wallet name whitespace stripping."""
        wallet = Wallet(
            user_id=ObjectId(),
            name="  My Wallet  ",
            description="Test wallet"
        )
        assert wallet.name == "My Wallet"

    def test_wallet_name_empty_raises_error(self):
        """Test that empty wallet name raises error."""
        with pytest.raises(ValidationError, match="Wallet name cannot be empty"):
            Wallet(
                user_id=ObjectId(),
                name="   ",
                description="Test wallet"
            )

    def test_wallet_name_length_constraints(self):
        """Test wallet name length constraints."""
        # Too long
        with pytest.raises(ValidationError):
            Wallet(
                user_id=ObjectId(),
                name="a" * 201,
                description="Test wallet"
            )
        
        # Too short (empty after stripping)
        with pytest.raises(ValidationError):
            Wallet(
                user_id=ObjectId(),
                name="",
                description="Test wallet"
            )

    def test_wallet_description_length_constraint(self):
        """Test wallet description length constraint."""
        with pytest.raises(ValidationError):
            Wallet(
                user_id=ObjectId(),
                name="Test Wallet",
                description="a" * 1001
            )


class TestAssetFieldValidation:
    """Tests for Asset model field validation."""

    def test_asset_name_validation(self):
        """Test asset name validation."""
        asset = Asset(
            asset_name="Apple Inc.",
            asset_type=AssetType.STOCK
        )
        assert asset.asset_name == "Apple Inc."

    def test_asset_name_whitespace_stripping(self):
        """Test asset name whitespace stripping."""
        asset = Asset(
            asset_name="  Apple Inc.  ",
            asset_type=AssetType.STOCK
        )
        assert asset.asset_name == "Apple Inc."

    def test_asset_name_empty_raises_error(self):
        """Test that empty asset name raises error."""
        with pytest.raises(ValidationError, match="Asset name cannot be empty"):
            Asset(
                asset_name="   ",
                asset_type=AssetType.STOCK
            )

    def test_asset_name_length_constraints(self):
        """Test asset name length constraints."""
        # Too long
        with pytest.raises(ValidationError):
            Asset(
                asset_name="a" * 201,
                asset_type=AssetType.STOCK
            )

    def test_asset_url_validation_valid(self):
        """Test valid URL formats."""
        valid_urls = [
            "https://api.example.com/stock/AAPL",
            "http://example.com/data",
            "https://www.google.com/finance",
            None  # Optional field
        ]
        
        for url in valid_urls:
            asset = Asset(
                asset_name="Test Asset",
                asset_type=AssetType.STOCK,
                url=url
            )
            assert asset.url == url

    def test_asset_url_validation_invalid(self):
        """Test invalid URL formats."""
        invalid_urls = [
            "invalid-url",
            "ftp://example.com",
            "example.com",
            "www.example.com",
            "javascript:alert('test')"
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError, match="URL must start with http"):
                Asset(
                    asset_name="Test Asset",
                    asset_type=AssetType.STOCK,
                    url=url
                )

    def test_asset_url_whitespace_handling(self):
        """Test URL whitespace handling."""
        asset = Asset(
            asset_name="Test Asset",
            asset_type=AssetType.STOCK,
            url="  https://example.com  "
        )
        assert asset.url == "https://example.com"

    def test_asset_symbol_length_constraint(self):
        """Test asset symbol length constraint."""
        with pytest.raises(ValidationError):
            Asset(
                asset_name="Test Asset",
                asset_type=AssetType.STOCK,
                symbol="a" * 21  # Max is 20
            )

    def test_asset_description_length_constraint(self):
        """Test asset description length constraint."""
        with pytest.raises(ValidationError):
            Asset(
                asset_name="Test Asset",
                asset_type=AssetType.STOCK,
                description="a" * 1001  # Max is 1000
            )


class TestAssetCurrentValueFieldValidation:
    """Tests for AssetCurrentValue model field validation."""

    def test_currency_validation_valid(self):
        """Test valid currency codes."""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]
        
        for currency in valid_currencies:
            value = AssetCurrentValue(
                asset_id=ObjectId(),
                date=datetime.now(),
                price=100.0,
                currency=currency
            )
            assert value.currency == currency

    def test_currency_normalization(self):
        """Test currency normalization (uppercase)."""
        value = AssetCurrentValue(
            asset_id=ObjectId(),
            date=datetime.now(),
            price=100.0,
            currency="usd"
        )
        assert value.currency == "USD"

    def test_currency_validation_invalid_length(self):
        """Test invalid currency length."""
        invalid_currencies = ["US", "USDD", "U", "USDX"]
        
        for currency in invalid_currencies:
            with pytest.raises(ValidationError):
                AssetCurrentValue(
                    asset_id=ObjectId(),
                    date=datetime.now(),
                    price=100.0,
                    currency=currency
                )

    def test_price_validation_positive(self):
        """Test positive price validation."""
        value = AssetCurrentValue(
            asset_id=ObjectId(),
            date=datetime.now(),
            price=100.0,
            currency="USD"
        )
        assert value.price == 100.0

    def test_price_validation_zero_raises_error(self):
        """Test that zero price raises error."""
        with pytest.raises(ValidationError):
            AssetCurrentValue(
                asset_id=ObjectId(),
                date=datetime.now(),
                price=0.0,
                currency="USD"
            )

    def test_price_validation_negative_raises_error(self):
        """Test that negative price raises error."""
        with pytest.raises(ValidationError):
            AssetCurrentValue(
                asset_id=ObjectId(),
                date=datetime.now(),
                price=-100.0,
                currency="USD"
            )

    def test_date_parsing_multiple_formats(self):
        """Test date parsing with multiple formats."""
        test_dates = [
            "2024-01-10",
            "10/01/2024",
            "01/10/2024",
            "2024/01/10",
            "10-01-2024",
            "2024-01-10 15:30:00"
        ]
        
        for date_str in test_dates:
            value = AssetCurrentValue(
                asset_id=ObjectId(),
                date=date_str,
                price=100.0,
                currency="USD"
            )
            assert isinstance(value.date, datetime)

    def test_date_parsing_invalid_formats(self):
        """Test invalid date formats."""
        invalid_dates = [
            "invalid-date",
            "32/01/2024",  # Invalid day
            "13/13/2024",  # Invalid month (unambiguous)
            "2024-13-01",  # Invalid month
            ""
        ]
        
        for date_str in invalid_dates:
            with pytest.raises(ValidationError):
                AssetCurrentValue(
                    asset_id=ObjectId(),
                    date=date_str,
                    price=100.0,
                    currency="USD"
                )


class TestTransactionFieldValidation:
    """Tests for Transaction model field validation."""

    def test_transaction_currency_validation(self):
        """Test transaction currency validation."""
        transaction = Transaction(
            wallet_id=ObjectId(),
            asset_id=ObjectId(),
            date=datetime.now(),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=100.0,
            transaction_amount=1000.0,
            currency="usd"
        )
        assert transaction.currency == "USD"

    def test_transaction_currency_invalid_length(self):
        """Test invalid currency length."""
        with pytest.raises(ValidationError):
            Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=datetime.now(),
                transaction_type=TransactionType.BUY,
                volume=10.0,
                item_price=100.0,
                transaction_amount=1000.0,
                currency="US"
            )

    def test_transaction_volume_validation(self):
        """Test transaction volume validation."""
        # Valid volume
        transaction = Transaction(
            wallet_id=ObjectId(),
            asset_id=ObjectId(),
            date=datetime.now(),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=100.0,
            transaction_amount=1000.0,
            currency="USD"
        )
        assert transaction.volume == 10.0

    def test_transaction_volume_negative_raises_error(self):
        """Test that negative volume raises error."""
        with pytest.raises(ValidationError):
            Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=datetime.now(),
                transaction_type=TransactionType.BUY,
                volume=-10.0,
                item_price=100.0,
                transaction_amount=1000.0,
                currency="USD"
            )

    def test_transaction_item_price_validation(self):
        """Test item price validation."""
        transaction = Transaction(
            wallet_id=ObjectId(),
            asset_id=ObjectId(),
            date=datetime.now(),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=100.0,
            transaction_amount=1000.0,
            currency="USD"
        )
        assert transaction.item_price == 100.0

    def test_transaction_item_price_negative_raises_error(self):
        """Test that negative item price raises error."""
        with pytest.raises(ValidationError):
            Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=datetime.now(),
                transaction_type=TransactionType.BUY,
                volume=10.0,
                item_price=-100.0,
                transaction_amount=1000.0,
                currency="USD"
            )

    def test_transaction_fee_validation(self):
        """Test transaction fee validation."""
        transaction = Transaction(
            wallet_id=ObjectId(),
            asset_id=ObjectId(),
            date=datetime.now(),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=100.0,
            transaction_amount=1000.0,
            currency="USD",
            fee=5.0
        )
        assert transaction.fee == 5.0

    def test_transaction_fee_negative_raises_error(self):
        """Test that negative fee raises error."""
        with pytest.raises(ValidationError):
            Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=datetime.now(),
                transaction_type=TransactionType.BUY,
                volume=10.0,
                item_price=100.0,
                transaction_amount=1000.0,
                currency="USD",
                fee=-5.0
            )

    def test_transaction_fee_default_value(self):
        """Test transaction fee default value."""
        transaction = Transaction(
            wallet_id=ObjectId(),
            asset_id=ObjectId(),
            date=datetime.now(),
            transaction_type=TransactionType.BUY,
            volume=10.0,
            item_price=100.0,
            transaction_amount=1000.0,
            currency="USD"
        )
        assert transaction.fee == 0.0

    def test_transaction_date_parsing_multiple_formats(self):
        """Test transaction date parsing with multiple formats."""
        test_dates = [
            "2024-01-10",
            "10/01/2024",
            "01/10/2024",
            "2024/01/10",
            "10-01-2024",
            "2024-01-10 15:30:00"
        ]
        
        for date_str in test_dates:
            transaction = Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=date_str,
                transaction_type=TransactionType.BUY,
                volume=10.0,
                item_price=100.0,
                transaction_amount=1000.0,
                currency="USD"
            )
            assert isinstance(transaction.date, datetime)

    def test_transaction_notes_length_constraint(self):
        """Test transaction notes length constraint."""
        with pytest.raises(ValidationError):
            Transaction(
                wallet_id=ObjectId(),
                asset_id=ObjectId(),
                date=datetime.now(),
                transaction_type=TransactionType.BUY,
                volume=10.0,
                item_price=100.0,
                transaction_amount=1000.0,
                currency="USD",
                notes="a" * 1001  # Max is 1000
            )


class TestTransactionErrorFieldValidation:
    """Tests for TransactionError model field validation."""

    def test_transaction_error_creation(self):
        """Test transaction error creation."""
        error = TransactionError(
            user_id=ObjectId(),
            wallet_name="Test Wallet",
            filename="test.csv",
            row_index=1,
            raw_data={"test": "data"},
            error_message="Test error",
            error_type="validation",
            transaction_type="buy",
            asset_type="stock"
        )
        
        assert error.user_id is not None
        assert error.wallet_name == "Test Wallet"
        assert error.filename == "test.csv"
        assert error.row_index == 1
        assert error.raw_data == {"test": "data"}
        assert error.error_message == "Test error"
        assert error.error_type == "validation"
        assert error.transaction_type == "buy"
        assert error.asset_type == "stock"
        assert error.resolved is False  # Default value


class TestPyObjectIdValidation:
    """Tests for PyObjectId validation."""

    def test_pyobjectid_creation(self):
        """Test PyObjectId creation."""
        obj_id = PyObjectId()
        assert isinstance(obj_id, ObjectId)
        assert ObjectId.is_valid(obj_id)

    def test_pyobjectid_validation_valid_string(self):
        """Test PyObjectId validation with valid string."""
        valid_id = ObjectId()
        validated = PyObjectId.validate(str(valid_id), None)
        assert isinstance(validated, ObjectId)
        assert validated == valid_id

    def test_pyobjectid_validation_invalid_string(self):
        """Test PyObjectId validation with invalid string."""
        invalid_strings = [
            "invalid-id",
            "123",
            "",
            "not-an-objectid"
        ]
        
        for invalid_str in invalid_strings:
            with pytest.raises(ValueError, match="Invalid ObjectId"):
                PyObjectId.validate(invalid_str, None)

    def test_pyobjectid_validation_objectid_instance(self):
        """Test PyObjectId validation with ObjectId instance."""
        obj_id = ObjectId()
        validated = PyObjectId.validate(obj_id, None)
        assert isinstance(validated, ObjectId)
        assert validated == obj_id
