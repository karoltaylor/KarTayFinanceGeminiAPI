"""Unit tests for Transaction API endpoints."""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, mock_open
from fastapi import HTTPException, UploadFile
from bson import ObjectId
from datetime import datetime, UTC
import tempfile
import os
from io import BytesIO

from api.routers.transactions import (
    upload_transactions,
    list_transactions,
    list_transaction_errors,
    delete_wallet_transactions,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestUploadTransactions:
    """Unit tests for upload_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_upload_transactions_success(self):
        """Test successful transaction upload."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.content_type = "text/csv"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"test,data\n1,2")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }

        mock_transaction = Mock()
        mock_transaction.wallet_id = wallet_id
        mock_transaction.asset_id = ObjectId()
        mock_transaction.date = datetime.now(UTC)
        mock_transaction.transaction_type = Mock(value="buy")
        mock_transaction.volume = 10.0
        mock_transaction.item_price = 100.0
        mock_transaction.transaction_amount = 1000.0
        mock_transaction.currency = "USD"
        mock_transaction.fee = 5.0
        mock_transaction.notes = None
        mock_transaction.created_at = datetime.now(UTC)
        mock_transaction.model_dump.return_value = {}

        mock_db.transactions.insert_many.return_value.inserted_ids = [ObjectId()]
        mock_db.assets.find.return_value = []
        mock_db.wallets.find.return_value = [{"_id": wallet_id, "name": "Test Wallet"}]

        with patch("api.routers.transactions.DataPipeline") as mock_pipeline_class:
            mock_pipeline = mock_pipeline_class.return_value
            mock_pipeline.process_file_to_transactions.return_value = (
                [mock_transaction],
                [],
            )
            mock_pipeline.transaction_mapper._asset_cache = {}

            # Act
            result = await upload_transactions(
                file=mock_file, wallet_id=str(wallet_id), user_id=user_id, db=mock_db
            )

        # Assert
        assert result["status"] == "success"
        assert result["data"]["wallet_name"] == "Test Wallet"
        assert result["data"]["summary"]["total_transactions"] == 1
        assert result["data"]["summary"]["failed_transactions"] == 0

    @pytest.mark.asyncio
    async def test_upload_transactions_invalid_wallet_id(self):
        """Test upload with invalid wallet_id format."""
        # Arrange
        user_id = ObjectId()
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_db = Mock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_transactions(
                file=mock_file, wallet_id="invalid-id", user_id=user_id, db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Invalid wallet_id format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_transactions_wallet_not_found(self):
        """Test upload when wallet doesn't exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.csv"

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_transactions(
                file=mock_file, wallet_id=str(wallet_id), user_id=user_id, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Wallet not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_transactions_unsupported_file_type(self):
        """Test upload with unsupported file type."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await upload_transactions(
                file=mock_file, wallet_id=str(wallet_id), user_id=user_id, db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_transactions_no_valid_transactions(self):
        """Test upload when no valid transactions can be created."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.content_type = "text/csv"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"test,data\n1,2")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }

        with patch("api.routers.transactions.DataPipeline") as mock_pipeline_class:
            mock_pipeline = mock_pipeline_class.return_value
            mock_pipeline.process_file_to_transactions.return_value = (
                [],
                [],
            )  # No transactions
            mock_pipeline.transaction_mapper._asset_cache = {}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await upload_transactions(
                    file=mock_file,
                    wallet_id=str(wallet_id),
                    user_id=user_id,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 422
        assert "No valid transactions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_transactions_with_errors(self):
        """Test upload with some errors."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "test.csv"
        mock_file.content_type = "text/csv"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"test,data\n1,2")

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }

        mock_transaction = Mock()
        mock_transaction.wallet_id = wallet_id
        mock_transaction.asset_id = ObjectId()
        mock_transaction.date = datetime.now(UTC)
        mock_transaction.transaction_type = Mock(value="buy")
        mock_transaction.volume = 10.0
        mock_transaction.item_price = 100.0
        mock_transaction.transaction_amount = 1000.0
        mock_transaction.currency = "USD"
        mock_transaction.fee = 5.0
        mock_transaction.notes = None
        mock_transaction.created_at = datetime.now(UTC)
        mock_transaction.model_dump.return_value = {}

        error_record = {
            "row_index": 2,
            "raw_data": {"test": "data"},
            "error_message": "Invalid data",
            "error_type": "validation_error",
        }

        mock_db.transactions.insert_many.return_value.inserted_ids = [ObjectId()]
        mock_db.transaction_errors.insert_many.return_value = Mock()
        mock_db.assets.find.return_value = []
        mock_db.wallets.find.return_value = [{"_id": wallet_id, "name": "Test Wallet"}]

        with patch("api.routers.transactions.DataPipeline") as mock_pipeline_class:
            mock_pipeline = mock_pipeline_class.return_value
            mock_pipeline.process_file_to_transactions.return_value = (
                [mock_transaction],
                [error_record],
            )
            mock_pipeline.transaction_mapper._asset_cache = {}

            # Act
            result = await upload_transactions(
                file=mock_file, wallet_id=str(wallet_id), user_id=user_id, db=mock_db
            )

        # Assert
        assert result["status"] == "success"
        assert result["data"]["summary"]["total_transactions"] == 1
        assert result["data"]["summary"]["failed_transactions"] == 1
        mock_db.transaction_errors.insert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_transactions_supported_file_extensions(self):
        """Test that all supported file extensions are accepted."""
        user_id = ObjectId()
        wallet_id = ObjectId()

        supported_extensions = [".csv", ".txt", ".xls", ".xlsx"]

        for ext in supported_extensions:
            mock_file = Mock(spec=UploadFile)
            mock_file.filename = f"test{ext}"
            mock_file.read = AsyncMock(return_value=b"test,data\n1,2")

            mock_db = Mock()
            mock_db.wallets.find_one.return_value = {
                "_id": wallet_id,
                "user_id": user_id,
                "name": "Test Wallet",
            }

            mock_transaction = Mock()
            mock_transaction.wallet_id = wallet_id
            mock_transaction.asset_id = ObjectId()
            mock_transaction.date = datetime.now(UTC)
            mock_transaction.transaction_type = Mock(value="buy")
            mock_transaction.volume = 10.0
            mock_transaction.item_price = 100.0
            mock_transaction.transaction_amount = 1000.0
            mock_transaction.currency = "USD"
            mock_transaction.fee = 5.0
            mock_transaction.notes = None
            mock_transaction.created_at = datetime.now(UTC)
            mock_transaction.model_dump.return_value = {}

            mock_db.transactions.insert_many.return_value.inserted_ids = [ObjectId()]
            mock_db.assets.find.return_value = []
            mock_db.wallets.find.return_value = [
                {"_id": wallet_id, "name": "Test Wallet"}
            ]

            with patch("api.routers.transactions.DataPipeline") as mock_pipeline_class:
                mock_pipeline = mock_pipeline_class.return_value
                mock_pipeline.process_file_to_transactions.return_value = (
                    [mock_transaction],
                    [],
                )
                mock_pipeline.transaction_mapper._asset_cache = {}

                # Should not raise exception
                result = await upload_transactions(
                    file=mock_file,
                    wallet_id=str(wallet_id),
                    user_id=user_id,
                    db=mock_db,
                )

                assert result["status"] == "success"


class TestListTransactions:
    """Unit tests for list_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_list_transactions_empty(self):
        """Test listing transactions when none exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            []
        )

        # Act
        result = await list_transactions(
            wallet_id=str(wallet_id), limit=100, skip=0, db=mock_db, user_id=user_id
        )

        # Assert
        assert result["transactions"] == []
        assert result["count"] == 0
        assert result["has_next"] is False
        assert result["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_transactions_with_data(self):
        """Test listing transactions with data."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()
        asset_id = ObjectId()
        transaction_id = ObjectId()

        mock_transactions = [
            {
                "_id": transaction_id,
                "wallet_id": wallet_id,
                "asset_id": asset_id,
                "date": datetime.now(UTC),
                "transaction_type": "buy",
                "volume": 10.0,
                "item_price": 100.0,
                "transaction_amount": 1000.0,
                "currency": "USD",
                "fee": 5.0,
                "created_at": datetime.now(UTC),
            }
        ]

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            mock_transactions
        )
        mock_db.assets.find_one.return_value = {
            "_id": asset_id,
            "asset_name": "Test Asset",
            "asset_type": "stock",
        }

        # Act
        result = await list_transactions(
            wallet_id=str(wallet_id), limit=100, skip=0, db=mock_db, user_id=user_id
        )

        # Assert
        assert result["count"] == 1
        assert len(result["transactions"]) == 1
        assert result["transactions"][0]["_id"] == str(transaction_id)
        assert result["transactions"][0]["wallet_name"] == "Test Wallet"
        assert result["transactions"][0]["asset_name"] == "Test Asset"

    @pytest.mark.asyncio
    async def test_list_transactions_invalid_wallet_id(self):
        """Test listing with invalid wallet_id format."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_transactions(
                wallet_id="invalid-id", limit=100, skip=0, db=mock_db, user_id=user_id
            )

        assert exc_info.value.status_code == 400
        assert "Invalid wallet_id format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_transactions_wallet_not_found(self):
        """Test listing when wallet doesn't exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_transactions(
                wallet_id=str(wallet_id), limit=100, skip=0, db=mock_db, user_id=user_id
            )

        assert exc_info.value.status_code == 404
        assert "Wallet not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_transactions_pagination_has_next(self):
        """Test pagination with has_next indicator."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        # Create 3 transactions when limit is 2, so has_next should be True
        mock_transactions = [
            {
                "_id": ObjectId(),
                "wallet_id": wallet_id,
                "asset_id": ObjectId(),
                "date": datetime.now(UTC),
            }
            for _ in range(3)
        ]

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            mock_transactions
        )
        mock_db.assets.find_one.return_value = {
            "asset_name": "Test",
            "asset_type": "stock",
        }

        # Act
        result = await list_transactions(
            wallet_id=str(wallet_id), limit=2, skip=0, db=mock_db, user_id=user_id
        )

        # Assert
        assert result["has_next"] is True
        assert result["has_prev"] is False
        assert result["count"] == 2  # Should only return limit amount

    @pytest.mark.asyncio
    async def test_list_transactions_pagination_has_prev(self):
        """Test pagination with has_prev indicator."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_transactions = [
            {
                "_id": ObjectId(),
                "wallet_id": wallet_id,
                "asset_id": ObjectId(),
                "date": datetime.now(UTC),
            }
            for _ in range(2)
        ]

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            mock_transactions
        )
        mock_db.assets.find_one.return_value = {
            "asset_name": "Test",
            "asset_type": "stock",
        }

        # Act
        result = await list_transactions(
            wallet_id=str(wallet_id),
            limit=2,
            skip=5,  # Skip > 0 means there are previous pages
            db=mock_db,
            user_id=user_id,
        )

        # Assert
        assert result["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_transactions_missing_asset(self):
        """Test listing transactions when asset doesn't exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()
        asset_id = ObjectId()

        mock_transactions = [
            {
                "_id": ObjectId(),
                "wallet_id": wallet_id,
                "asset_id": asset_id,
                "date": datetime.now(UTC),
            }
        ]

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            mock_transactions
        )
        mock_db.assets.find_one.return_value = None  # Asset not found

        # Act
        result = await list_transactions(
            wallet_id=str(wallet_id), limit=100, skip=0, db=mock_db, user_id=user_id
        )

        # Assert
        assert result["transactions"][0]["asset_name"] == "Unknown"
        assert result["transactions"][0]["asset_type"] == "unknown"


class TestListTransactionErrors:
    """Unit tests for list_transaction_errors endpoint."""

    @pytest.mark.asyncio
    async def test_list_errors_empty(self):
        """Test listing errors when none exist."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()
        mock_db.transaction_errors.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            []
        )

        # Act
        result = await list_transaction_errors(
            wallet_id=None,
            resolved=None,
            limit=100,
            skip=0,
            user_id=user_id,
            db=mock_db,
        )

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_list_errors_with_data(self):
        """Test listing errors with data."""
        # Arrange
        user_id = ObjectId()
        error_id = ObjectId()

        mock_errors = [
            {
                "_id": error_id,
                "user_id": user_id,
                "wallet_name": "Test Wallet",
                "filename": "test.csv",
                "row_index": 1,
                "raw_data": {"test": "data"},
                "error_message": "Test error",
                "error_type": "validation",
            }
        ]

        mock_db = Mock()
        mock_db.transaction_errors.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            mock_errors
        )

        # Act
        result = await list_transaction_errors(
            wallet_id=None,
            resolved=None,
            limit=100,
            skip=0,
            user_id=user_id,
            db=mock_db,
        )

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["errors"][0]["_id"] == str(error_id)

    @pytest.mark.asyncio
    async def test_list_errors_filter_by_wallet(self):
        """Test filtering errors by wallet_id."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transaction_errors.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            []
        )

        # Act
        await list_transaction_errors(
            wallet_id=str(wallet_id),
            resolved=None,
            limit=100,
            skip=0,
            user_id=user_id,
            db=mock_db,
        )

        # Assert - verify query includes wallet_name
        call_args = mock_db.transaction_errors.find.call_args[0][0]
        assert "wallet_name" in call_args
        assert call_args["wallet_name"] == "Test Wallet"

    @pytest.mark.asyncio
    async def test_list_errors_filter_by_resolved(self):
        """Test filtering errors by resolved status."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()
        mock_db.transaction_errors.find.return_value.sort.return_value.skip.return_value.limit.return_value = (
            []
        )

        # Act
        await list_transaction_errors(
            wallet_id=None,
            resolved=True,
            limit=100,
            skip=0,
            user_id=user_id,
            db=mock_db,
        )

        # Assert - verify query includes resolved filter
        call_args = mock_db.transaction_errors.find.call_args[0][0]
        assert "resolved" in call_args
        assert call_args["resolved"] is True

    @pytest.mark.asyncio
    async def test_list_errors_invalid_wallet_id(self):
        """Test filtering with invalid wallet_id format."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_transaction_errors(
                wallet_id="invalid-id",
                resolved=None,
                limit=100,
                skip=0,
                user_id=user_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid wallet_id format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_errors_wallet_not_found(self):
        """Test filtering when wallet doesn't exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_transaction_errors(
                wallet_id=str(wallet_id),
                resolved=None,
                limit=100,
                skip=0,
                user_id=user_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "Wallet not found" in exc_info.value.detail


class TestDeleteWalletTransactions:
    """Unit tests for delete_wallet_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_delete_transactions_success(self):
        """Test successful transaction deletion."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.delete_many.return_value.deleted_count = 5

        # Act
        result = await delete_wallet_transactions(
            wallet_id=str(wallet_id), user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert result["wallet_name"] == "Test Wallet"
        assert result["deleted_count"] == 5
        mock_db.transactions.delete_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_transactions_invalid_wallet_id(self):
        """Test deletion with invalid wallet_id format."""
        # Arrange
        user_id = ObjectId()
        mock_db = Mock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet_transactions(
                wallet_id="invalid-id", user_id=user_id, db=mock_db
            )

        assert exc_info.value.status_code == 400
        assert "Invalid wallet_id format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_transactions_wallet_not_found(self):
        """Test deletion when wallet doesn't exist."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_wallet_transactions(
                wallet_id=str(wallet_id), user_id=user_id, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert "Wallet not found or not owned by user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_transactions_empty_wallet(self):
        """Test deleting transactions from empty wallet."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Empty Wallet",
        }
        mock_db.transactions.delete_many.return_value.deleted_count = 0

        # Act
        result = await delete_wallet_transactions(
            wallet_id=str(wallet_id), user_id=user_id, db=mock_db
        )

        # Assert
        assert result["status"] == "success"
        assert result["deleted_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_transactions_checks_both_formats(self):
        """Test that deletion handles both ObjectId and string formats."""
        # Arrange
        user_id = ObjectId()
        wallet_id = ObjectId()

        mock_db = Mock()
        mock_db.wallets.find_one.return_value = {
            "_id": wallet_id,
            "user_id": user_id,
            "name": "Test Wallet",
        }
        mock_db.transactions.delete_many.return_value.deleted_count = 3

        # Act
        await delete_wallet_transactions(
            wallet_id=str(wallet_id), user_id=user_id, db=mock_db
        )

        # Assert - verify deletion query handles both formats
        call_args = mock_db.transactions.delete_many.call_args[0][0]
        assert "$or" in call_args
        assert {"wallet_id": wallet_id} in call_args["$or"]
        assert {"wallet_id": str(wallet_id)} in call_args["$or"]

