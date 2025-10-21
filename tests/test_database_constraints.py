"""Database constraint and relationship tests."""

import pytest
from datetime import datetime, UTC
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from src.config.mongodb import MongoDBConfig
from src.models.mongodb_models import (
    User,
    Wallet,
    Asset,
    Transaction,
    TransactionError,
    AssetType,
    TransactionType,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def test_db(unique_test_email, unique_test_username):
    """Get test database instance and clean up test data."""
    db = MongoDBConfig.get_database()

    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")
    test_user_id_2 = ObjectId("507f1f77bcf86cd799439012")

    # Clean up test data before each test
    db.transactions.delete_many({})
    db.wallets.delete_many(
        {
            "$or": [
                {"user_id": test_user_id},
                {"user_id": str(test_user_id)},
                {"user_id": test_user_id_2},
                {"user_id": str(test_user_id_2)},
            ]
        }
    )
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    db.transaction_errors.delete_many({})

    # Create test users with unique emails
    test_user_1 = {
        "_id": test_user_id,
        "email": unique_test_email,
        "username": unique_test_username,
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    test_user_2 = {
        "_id": test_user_id_2,
        "email": f"test2_{unique_test_email.split('@')[0].split('_')[1]}@example.com",
        "username": f"{unique_test_username}_2",
        "full_name": "Test User 2",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    db.users.update_one({"_id": test_user_id}, {"$set": test_user_1}, upsert=True)
    db.users.update_one({"_id": test_user_id_2}, {"$set": test_user_2}, upsert=True)

    yield db

    # Clean up test data after each test
    db.transactions.delete_many({})
    db.wallets.delete_many(
        {
            "$or": [
                {"user_id": test_user_id},
                {"user_id": str(test_user_id)},
                {"user_id": test_user_id_2},
                {"user_id": str(test_user_id_2)},
            ]
        }
    )
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    db.transaction_errors.delete_many({})


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Auth headers are now provided by conftest.py fixtures


class TestDatabaseConstraints:
    """Tests for database constraints and relationships."""

    def test_wallet_name_uniqueness_per_user(self, client, test_db, auth_headers):
        """Test that wallet names must be unique per user."""
        # Create first wallet
        wallet_data = {"name": "Unique Wallet", "description": "First wallet"}
        response1 = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response1.status_code == 200

        # Try to create wallet with same name for same user
        response2 = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_wallet_name_uniqueness_different_users(
        self, client, test_db, auth_headers, auth_headers_user2, override_auth_user2
    ):
        """Test that different users can have wallets with same name."""
        from api.main import app
        from api.dependencies import get_current_user
        from src.auth.firebase_auth import get_current_user_from_token
        from bson import ObjectId

        wallet_data = {"name": "Same Name Wallet", "description": "Test wallet"}

        # User 1 creates wallet
        response1 = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response1.status_code == 200

        # Switch to user 2
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2

        # User 2 creates wallet with same name (should succeed)
        response2 = client.post(
            "/api/wallets", json=wallet_data, headers=auth_headers_user2
        )
        assert response2.status_code == 200

        # Switch back to user 1
        test_user_id = ObjectId("507f1f77bcf86cd799439011")

        async def mock_get_user1():
            return test_user_id

        app.dependency_overrides[get_current_user] = mock_get_user1
        app.dependency_overrides[get_current_user_from_token] = mock_get_user1

        # Verify both wallets exist - user 1
        wallets1 = client.get("/api/wallets", headers=auth_headers).json()

        # Switch to user 2
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2

        wallets2 = client.get("/api/wallets", headers=auth_headers_user2).json()

        assert wallets1["count"] == 1
        assert wallets2["count"] == 1
        assert wallets1["wallets"][0]["name"] == "Same Name Wallet"
        assert wallets2["wallets"][0]["name"] == "Same Name Wallet"

    def test_transaction_foreign_key_constraints(self, client, test_db, auth_headers):
        """Test that transactions require valid wallet_id and asset_id."""
        # Create wallet and asset first
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Test Wallet", "description": "For testing"},
            headers=auth_headers,
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]

        # Create asset by uploading a transaction file
        import tempfile
        import csv

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "Asset Name",
                "Date",
                "Price",
                "Volume",
                "Total",
                "Fee",
                "Currency",
                "Transaction Type",
            ]
        )
        writer.writerow(
            [
                "Test Asset",
                "2024-01-15",
                "100.00",
                "10",
                "1000.00",
                "2.50",
                "USD",
                "buy",
            ]
        )
        temp_file.close()

        try:
            with open(temp_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet_id, "asset_type": "stock"},
                )
            assert upload_response.status_code == 200

            # Verify transaction was created with valid foreign keys
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            assert transactions_response.status_code == 200
            transactions = transactions_response.json()["transactions"]
            assert len(transactions) > 0

            transaction = transactions[0]
            assert transaction["wallet_id"] == wallet_id
            assert "asset_id" in transaction
            assert transaction["asset_id"] is not None

        finally:
            import os

            os.unlink(temp_file.name)

    def test_cascading_deletes_wallet_transactions(self, client, test_db, auth_headers):
        """Test that deleting a wallet also deletes its transactions."""
        # Create wallet and transactions
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Wallet to Delete", "description": "For testing"},
            headers=auth_headers,
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]

        # Upload transactions to create some data
        import tempfile
        import csv

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(temp_file)
        writer.writerow(
            ["Asset Name", "Date", "Price", "Volume", "Total", "Fee", "Currency"]
        )
        writer.writerow(
            ["Asset 1", "2024-01-15", "100.00", "10", "1000.00", "2.50", "USD"]
        )
        writer.writerow(
            ["Asset 2", "2024-01-16", "200.00", "5", "1000.00", "2.50", "USD"]
        )
        temp_file.close()

        try:
            with open(temp_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet_id},
                )
            assert upload_response.status_code == 200

            # Verify transactions exist
            from bson import ObjectId

            wallet_obj_id = ObjectId(wallet_id)
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            initial_count = transactions_response.json()["count"]
            assert initial_count > 0

            # Delete wallet
            delete_response = client.delete(
                f"/api/wallets/{wallet_id}", headers=auth_headers
            )
            assert delete_response.status_code == 200

            # Verify transactions are deleted by checking wallet-specific transactions
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            # Should get 404 since wallet no longer exists
            assert transactions_response.status_code == 404

        finally:
            import os

            os.unlink(temp_file.name)

    def test_user_isolation_constraint(
        self, client, test_db, auth_headers, auth_headers_user2, override_auth_user2
    ):
        """Test that users can only access their own data."""
        from api.main import app
        from api.dependencies import get_current_user
        from src.auth.firebase_auth import get_current_user_from_token

        # User 1 creates wallet
        wallet_data = {"name": "User1 Wallet", "description": "Private wallet"}
        response1 = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response1.status_code == 200
        wallet_id = response1.json()["data"]["_id"]

        # Switch to user 2
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2

        # User 2 tries to access User 1's wallet by listing wallets
        response2 = client.get("/api/wallets", headers=auth_headers_user2)
        assert response2.status_code == 200
        # User 2 should not see User 1's wallet
        user2_wallets = response2.json()["wallets"]
        assert len(user2_wallets) == 0

        # User 2 tries to delete User 1's wallet
        response3 = client.delete(
            f"/api/wallets/{wallet_id}", headers=auth_headers_user2
        )
        assert response3.status_code == 404

        # Switch back to user 1
        from bson import ObjectId

        test_user_id = ObjectId("507f1f77bcf86cd799439011")

        async def mock_get_user1():
            return test_user_id

        app.dependency_overrides[get_current_user] = mock_get_user1
        app.dependency_overrides[get_current_user_from_token] = mock_get_user1

        # Verify wallet still exists for User 1
        response4 = client.get("/api/wallets", headers=auth_headers)
        assert response4.json()["count"] == 1

    def test_transaction_user_isolation_constraint(
        self, client, test_db, auth_headers, auth_headers_user2, override_auth_user2
    ):
        """Test that users can only see their own transactions."""
        from api.main import app
        from api.dependencies import get_current_user
        from src.auth.firebase_auth import get_current_user_from_token
        from bson import ObjectId

        # User 1 creates wallet and uploads transactions
        wallet1_response = client.post(
            "/api/wallets", json={"name": "User1 Wallet"}, headers=auth_headers
        )
        assert wallet1_response.status_code == 200
        wallet1_id = wallet1_response.json()["data"]["_id"]

        import tempfile
        import csv

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(temp_file)
        writer.writerow(
            ["Asset Name", "Date", "Price", "Volume", "Total", "Fee", "Currency"]
        )
        writer.writerow(
            ["User1 Asset", "2024-01-15", "100.00", "10", "1000.00", "2.50", "USD"]
        )
        temp_file.close()

        try:
            with open(temp_file.name, "rb") as f:
                response1 = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet1_id},
                )
            assert response1.status_code == 200

            # Switch to user 2
            app.dependency_overrides[get_current_user] = override_auth_user2
            app.dependency_overrides[get_current_user_from_token] = override_auth_user2

            # User 2 creates wallet and uploads transactions
            wallet2_response = client.post(
                "/api/wallets",
                json={"name": "User2 Wallet"},
                headers=auth_headers_user2,
            )
            assert wallet2_response.status_code == 200
            wallet2_id = wallet2_response.json()["data"]["_id"]

            with open(temp_file.name, "rb") as f:
                response2 = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers_user2,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet2_id},
                )
            assert response2.status_code == 200

            # Switch back to user 1
            test_user_id = ObjectId("507f1f77bcf86cd799439011")

            async def mock_get_user1():
                return test_user_id

            app.dependency_overrides[get_current_user] = mock_get_user1
            app.dependency_overrides[get_current_user_from_token] = mock_get_user1

            # User 1 lists transactions (should only see their own)
            response3 = client.get(
                f"/api/transactions?wallet_id={wallet1_id}", headers=auth_headers
            )
            user1_transactions = response3.json()["transactions"]

            # Switch to user 2
            app.dependency_overrides[get_current_user] = override_auth_user2
            app.dependency_overrides[get_current_user_from_token] = override_auth_user2

            # User 2 lists transactions (should only see their own)
            response4 = client.get(
                f"/api/transactions?wallet_id={wallet2_id}", headers=auth_headers_user2
            )
            user2_transactions = response4.json()["transactions"]

            # Verify isolation
            assert len(user1_transactions) >= 1
            assert len(user2_transactions) >= 1

            # Verify different transaction IDs
            user1_ids = {tx["_id"] for tx in user1_transactions}
            user2_ids = {tx["_id"] for tx in user2_transactions}
            assert user1_ids.isdisjoint(user2_ids)

        finally:
            import os

            os.unlink(temp_file.name)

    def test_asset_reference_integrity(self, client, test_db, auth_headers):
        """Test that assets are properly referenced in transactions."""
        # Create wallet first
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Asset Test Wallet", "description": "For testing"},
            headers=auth_headers,
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]

        # Upload transactions to create assets and transactions
        import tempfile
        import csv

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "Asset Name",
                "Date",
                "Price",
                "Volume",
                "Total",
                "Fee",
                "Currency",
                "Transaction Type",
            ]
        )
        writer.writerow(
            [
                "Test Asset",
                "2024-01-15",
                "100.00",
                "10",
                "1000.00",
                "2.50",
                "USD",
                "buy",
            ]
        )
        temp_file.close()

        try:
            with open(temp_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet_id},
                )
            assert upload_response.status_code == 200

            # Get transactions and verify asset references
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            transactions = transactions_response.json()["transactions"]
            assert len(transactions) > 0

            transaction = transactions[0]
            asset_id = transaction["asset_id"]

            # Verify asset exists in database
            asset = test_db.assets.find_one({"_id": ObjectId(asset_id)})
            assert asset is not None
            assert asset["asset_name"] == "Test Asset"

        finally:
            import os

            os.unlink(temp_file.name)

    def test_wallet_reference_integrity(self, client, test_db, auth_headers):
        """Test that wallets are properly referenced in transactions."""
        # Create wallet first
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Reference Test Wallet", "description": "For testing"},
            headers=auth_headers,
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]

        # Upload transactions
        import tempfile
        import csv

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.writer(temp_file)
        writer.writerow(
            [
                "Asset Name",
                "Date",
                "Price",
                "Volume",
                "Total",
                "Fee",
                "Currency",
                "Transaction Type",
            ]
        )
        writer.writerow(
            [
                "Test Asset",
                "2024-01-15",
                "100.00",
                "10",
                "1000.00",
                "2.50",
                "USD",
                "buy",
            ]
        )
        temp_file.close()

        try:
            with open(temp_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={"wallet_id": wallet_id},
                )
            assert upload_response.status_code == 200

            # Get transactions and verify wallet references
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            transactions = transactions_response.json()["transactions"]
            assert len(transactions) > 0

            transaction = transactions[0]
            assert transaction["wallet_id"] == wallet_id

            # Verify wallet exists in database
            wallet = test_db.wallets.find_one({"_id": ObjectId(wallet_id)})
            assert wallet is not None
            assert wallet["name"] == "Reference Test Wallet"

        finally:
            import os

            os.unlink(temp_file.name)

    def test_transaction_error_constraints(self, client, test_db, auth_headers):
        """Test transaction error model constraints."""
        # Create a transaction error directly in database
        error_data = {
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "wallet_name": "Test Wallet",
            "filename": "test.csv",
            "row_index": 1,
            "raw_data": {"test": "data"},
            "error_message": "Test error message",
            "error_type": "validation",
            "transaction_type": "buy",
            "asset_type": "stock",
            "created_at": datetime.now(UTC),
            "resolved": False,
        }

        result = test_db.transaction_errors.insert_one(error_data)
        assert result.inserted_id is not None

        # Verify error was created
        error = test_db.transaction_errors.find_one({"_id": result.inserted_id})
        assert error is not None
        assert error["user_id"] == ObjectId("507f1f77bcf86cd799439011")
        assert error["wallet_name"] == "Test Wallet"
        assert error["filename"] == "test.csv"
        assert error["row_index"] == 1
        assert error["raw_data"] == {"test": "data"}
        assert error["error_message"] == "Test error message"
        assert error["error_type"] == "validation"
        assert error["transaction_type"] == "buy"
        assert error["asset_type"] == "stock"
        assert error["resolved"] is False

    def test_database_indexes_exist(self, test_db):
        """Test that required database indexes exist."""
        # Check wallets collection indexes
        wallet_indexes = test_db.wallets.list_indexes()
        wallet_index_names = [idx["name"] for idx in wallet_indexes]

        # Should have _id_ index and potentially user_id index
        assert "_id_" in wallet_index_names

        # Check transactions collection indexes
        transaction_indexes = test_db.transactions.list_indexes()
        transaction_index_names = [idx["name"] for idx in transaction_indexes]

        # Should have _id_ index
        assert "_id_" in transaction_index_names

        # Check assets collection indexes
        asset_indexes = test_db.assets.list_indexes()
        asset_index_names = [idx["name"] for idx in asset_indexes]

        # Should have _id_ index
        assert "_id_" in asset_index_names

        # Check users collection indexes
        user_indexes = test_db.users.list_indexes()
        user_index_names = [idx["name"] for idx in user_indexes]

        # Should have _id_ index
        assert "_id_" in user_index_names

    def test_concurrent_operations_constraint(self, client, test_db, auth_headers):
        """Test that concurrent operations maintain data integrity."""
        import concurrent.futures
        import tempfile
        import csv

        def create_wallet_and_transactions(wallet_name):
            # Create wallet
            wallet_response = client.post(
                "/api/wallets",
                json={"name": wallet_name, "description": "Concurrent test"},
                headers=auth_headers,
            )
            if wallet_response.status_code != 200:
                return None

            wallet_id = wallet_response.json()["data"]["_id"]

            # Create transaction file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False, newline=""
            )
            writer = csv.writer(temp_file)
            writer.writerow(
                ["Asset Name", "Date", "Price", "Volume", "Total", "Fee", "Currency"]
            )
            writer.writerow(
                [
                    f"Asset_{wallet_name}",
                    "2024-01-15",
                    "100.00",
                    "10",
                    "1000.00",
                    "2.50",
                    "USD",
                ]
            )
            temp_file.close()

            try:
                # Upload transactions
                with open(temp_file.name, "rb") as f:
                    upload_response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": ("transactions.csv", f, "text/csv")},
                        data={"wallet_id": wallet_id},
                    )
                return upload_response.status_code == 200
            finally:
                import os

                os.unlink(temp_file.name)

        # Execute 5 concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    create_wallet_and_transactions, f"Concurrent_Wallet_{i}"
                )
                for i in range(5)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All operations should succeed
        assert all(results)

        # Verify all wallets and transactions were created
        wallets_response = client.get("/api/wallets", headers=auth_headers)
        assert wallets_response.json()["count"] == 5

        # Count transactions across all wallets
        total_transactions = 0
        wallets = wallets_response.json()["wallets"]
        for wallet in wallets:
            wallet_id = wallet["_id"]
            transactions_response = client.get(
                f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers
            )
            if transactions_response.status_code == 200:
                total_transactions += transactions_response.json()["count"]

        assert total_transactions == 5
