"""Unit tests for Wallet API endpoints."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime, UTC

from api.routers.wallets import (
    list_wallets,
    create_wallet,
    delete_wallet,
    WalletCreate,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestListWallets:
    """Unit tests for list_wallets endpoint."""

    @pytest.mark.asyncio
    async def test_list_wallets_empty(self):
        """Test listing wallets when user has none."""
        # Arrange
        mock_db = Mock()
        mock_db.wallets.find.return_value.skip.return_value.limit.return_value = []
        user_id = ObjectId()

        # Act
        result = await list_wallets(limit=100, skip=0, user_id=user_id, db=mock_db)

        # Assert
        assert result == {"wallets": [], "count": 0}
        mock_db.wallets.find.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_wallets_with_data(self):
        """Test listing wallets with data."""
        # Arrange
        user_id = ObjectId()
        wallet1_id = ObjectId()
        wallet2_id = ObjectId()

        mock_wallets = [
            {
                "_id": wallet1_id,
                "user_id": user_id,
                "name": "Wallet 1",
                "description": "Test wallet 1",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
            {
                "_id": wallet2_id,
                "user_id": user_id,
                "name": "Wallet 2",
                "description": "Test wallet 2",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        ]

        mock_db = Mock()
        mock_db.wallets.find.return_value.skip.return_value.limit.return_value = (
            mock_wallets
        )

        # Act
        result = await list_wallets(limit=100, skip=0, user_id=user_id, db=mock_db)

        # Assert
        assert result["count"] == 2
        assert len(result["wallets"]) == 2
        assert result["wallets"][0]["_id"] == str(wallet1_id)
        assert result["wallets"][1]["_id"] == str(wallet2_id)
        assert result["wallets"][0]["user_id"] == str(user_id)

    @pytest.mark.asyncio
    async def test_list_wallets_with_pagination(self):
        """Test list wallets with skip and limit parameters."""
        # Arrange
        user_id = ObjectId()
        mock_wallets = [
            {"_id": ObjectId(), "user_id": user_id, "name": f"Wallet {i}"}
            for i in range(5)
        ]

        mock_db = Mock()
        mock_db.wallets.find.return_value.skip.return_value.limit.return_value = (
            mock_wallets[:2]
        )

        # Act
        result = await list_wallets(limit=2, skip=3, user_id=user_id, db=mock_db)

        # Assert
        assert result["count"] == 2
        mock_find = mock_db.wallets.find.return_value
        mock_find.skip.assert_called_once_with(3)
        mock_find.skip.return_value.limit.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_list_wallets_converts_objectids_to_strings(self):
        """Test that ObjectIds are converted to strings for JSON serialization."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_wallets = [
            {
                "_id": wallet_id,
                "user_id": user_id,
                "name": "Test Wallet",
            }
        ]

        mock_db = Mock()
        mock_db.wallets.find.return_value.skip.return_value.limit.return_value = (
            mock_wallets
        )

        # Act
        result = await list_wallets(limit=100, skip=0, user_id=user_id, db=mock_db)

        # Assert
        assert isinstance(result["wallets"][0]["_id"], str)
        assert isinstance(result["wallets"][0]["user_id"], str)
        assert result["wallets"][0]["_id"] == str(wallet_id)
        assert result["wallets"][0]["user_id"] == str(user_id)


class TestCreateWallet:
    """Unit tests for create_wallet endpoint."""

    @pytest.mark.asyncio
    async def test_create_wallet_success(self):
        """Test successful wallet creation."""
        # Arrange
        user_id = ObjectId()
        wallet_data = WalletCreate(name="My Wallet", description="Test description")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None  # No existing wallet

        wallet_id = ObjectId()
        mock_db.wallets.insert_one.return_value.inserted_id = wallet_id
        mock_db.wallets.find_one.side_effect = [
            None,  # First call: check for existing wallet
            {  # Second call: get created wallet
                "_id": wallet_id,
                "user_id": user_id,
                "name": "My Wallet",
                "description": "Test description",
            },
        ]

        # Act
        result = await create_wallet(
            wallet_data=wallet_data, user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert "My Wallet" in result["message"]
        assert result["data"]["name"] == "My Wallet"
        assert result["data"]["description"] == "Test description"
        mock_db.wallets.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_wallet_without_description(self):
        """Test creating wallet without optional description."""
        # Arrange
        user_id = ObjectId()
        wallet_data = WalletCreate(name="Simple Wallet")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        wallet_id = ObjectId()
        mock_db.wallets.insert_one.return_value.inserted_id = wallet_id
        mock_db.wallets.find_one.side_effect = [
            None,
            {
                "_id": wallet_id,
                "user_id": user_id,
                "name": "Simple Wallet",
                "description": None,
            },
        ]

        # Act
        result = await create_wallet(
            wallet_data=wallet_data, user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert result["data"]["description"] is None

    @pytest.mark.asyncio
    async def test_create_wallet_duplicate_name(self):
        """Test creating wallet with duplicate name raises 409."""
        # Arrange
        user_id = ObjectId()
        wallet_data = WalletCreate(name="Duplicate Wallet")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": ObjectId(),
            "user_id": user_id,
            "name": "Duplicate Wallet",
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_wallet(wallet_data=wallet_data, user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail
        mock_db.wallets.insert_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_wallet_database_error(self):
        """Test wallet creation with database error."""
        # Arrange
        user_id = ObjectId()
        wallet_data = WalletCreate(name="Error Wallet")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None
        mock_db.wallets.insert_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_wallet(wallet_data=wallet_data, user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 500
        assert "Error creating wallet" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_wallet_checks_both_user_id_formats(self):
        """Test that wallet creation checks for duplicates in both ObjectId and string formats."""
        # Arrange
        user_id = ObjectId()
        wallet_data = WalletCreate(name="Test Wallet")

        wallet_id = ObjectId()
        mock_db = Mock()
        mock_db.wallets.insert_one.return_value.inserted_id = wallet_id
        mock_db.wallets.find_one.side_effect = [
            None,  # First call: check for existing wallet
            {  # Second call: get created wallet
                "_id": wallet_id,
                "user_id": user_id,
                "name": "Test Wallet",
                "description": None,
            },
        ]

        # Act
        await create_wallet(wallet_data=wallet_data, user_id=user_id, db=mock_db)

        # Assert - verify the query includes both formats
        call_args = mock_db.wallets.find_one.call_args_list[0][0][0]
        assert "$or" in call_args
        assert {"user_id": user_id} in call_args["$or"]
        assert {"user_id": str(user_id)} in call_args["$or"]


class TestDeleteWallet:
    """Unit tests for delete_wallet endpoint."""

    @pytest.mark.asyncio
    async def test_delete_wallet_success(self):
        """Test successful wallet deletion."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.count_documents.return_value = 0
        mock_db.wallets.delete_one.return_value = Mock()

        # Act
        result = await delete_wallet(
            wallet_id=str(wallet_id), user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert "deleted successfully" in result["message"]
        assert result["wallet_name"] == "Test Wallet"
        assert result["transactions_deleted"] == 0
        mock_db.wallets.delete_one.assert_called_once_with({"_id": wallet_id})

    @pytest.mark.asyncio
    async def test_delete_wallet_with_transactions(self):
        """Test deleting wallet that has transactions."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Wallet with Transactions",
        }
        mock_db.transactions.count_documents.return_value = 5
        mock_db.transactions.delete_many.return_value = Mock()
        mock_db.wallets.delete_one.return_value = Mock()

        # Act
        result = await delete_wallet(
            wallet_id=str(wallet_id), user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert result["transactions_deleted"] == 5
        mock_db.transactions.delete_many.assert_called_once_with(
            {"wallet_id": wallet_id}
        )
        mock_db.wallets.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_wallet_not_found(self):
        """Test deleting non-existent wallet."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet(wallet_id=str(wallet_id), user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "not found or not owned by user" in exc_info.value.detail
        mock_db.wallets.delete_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_wallet_invalid_id_format(self):
        """Test deleting wallet with invalid ObjectId format."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet(wallet_id="invalid-id", user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid wallet ID format" in exc_info.value.detail
        mock_db.wallets.find_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_wallet_not_owned_by_user(self):
        """Test deleting wallet owned by another user."""
        # Arrange
        user_id = ObjectId()
        other_user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        # Wallet exists but belongs to different user
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet(wallet_id=str(wallet_id), user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert "not found or not owned by user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_wallet_database_error(self):
        """Test wallet deletion with database error."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.count_documents.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet(wallet_id=str(wallet_id), user_id=user_id, db=mock_db)

        assert exc_info.value.status_code == 500
        assert "Error deleting wallet" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_wallet_checks_both_user_id_formats(self):
        """Test that wallet deletion checks ownership in both ObjectId and string formats."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.count_documents.return_value = 0

        # Act
        await delete_wallet(wallet_id=str(wallet_id), user_id=user_id, db=mock_db)

        # Assert - verify the query includes both formats
        call_args = mock_db.wallets.find_one.call_args[0][0]
        assert "_id" in call_args
        assert call_args["_id"] == wallet_id
        assert "$or" in call_args
        assert {"user_id": user_id} in call_args["$or"]
        assert {"user_id": str(user_id)} in call_args["$or"]


class TestWalletCreate:
    """Unit tests for WalletCreate model."""

    def test_wallet_create_valid(self):
        """Test creating valid WalletCreate instance."""
        wallet = WalletCreate(name="Test Wallet", description="Test description")
        assert wallet.name == "Test Wallet"
        assert wallet.description == "Test description"

    def test_wallet_create_without_description(self):
        """Test creating WalletCreate without optional description."""
        wallet = WalletCreate(name="Test Wallet")
        assert wallet.name == "Test Wallet"
        assert wallet.description is None

    def test_wallet_create_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            WalletCreate(name="")

    def test_wallet_create_name_too_long_fails(self):
        """Test that name exceeding max length fails validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            WalletCreate(name="A" * 201)  # Max is 200

    def test_wallet_create_description_too_long_fails(self):
        """Test that description exceeding max length fails validation."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            WalletCreate(name="Test", description="A" * 1001)  # Max is 1000

