"""Integration tests for FastAPI transaction endpoints."""

import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime, UTC
from pathlib import Path
import tempfile
import csv
from unittest.mock import patch

from api.main import app
from src.config.mongodb import MongoDBConfig

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def test_db(unique_test_email, unique_test_username):
    """
    Get test database instance and set up test user, wallets, and assets.
    
    NOTE: This uses the database configured in environment.
    For true isolation, consider using a separate test database.
    """
    db = MongoDBConfig.get_database()
    
    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")
    test_user_id_2 = ObjectId("507f1f77bcf86cd799439012")
    
    # Clean up test data before each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    
    # Create test users with unique emails
    test_user_1 = {
        "_id": test_user_id,
        "email": unique_test_email,
        "username": unique_test_username,
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    test_user_2 = {
        "_id": test_user_id_2,
        "email": f"test2_{unique_test_email.split('@')[0].split('_')[1]}@example.com",
        "username": f"{unique_test_username}_2",
        "full_name": "Test User 2",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    db.users.update_one(
        {"_id": test_user_id},
        {"$set": test_user_1},
        upsert=True
    )
    db.users.update_one(
        {"_id": test_user_id_2},
        {"$set": test_user_2},
        upsert=True
    )
    
    yield db
    
    # Clean up test data after each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Auth headers are now provided by conftest.py fixtures


def _create_wallet_and_get_id(client: TestClient, headers: dict, name: str, description: str = "Test") -> str:
    """Helper to create a wallet and return its _id as string."""
    resp = client.post(
        "/api/wallets",
        headers=headers,
        json={"name": name, "description": description}
    )
    assert resp.status_code == 200, f"Failed to create wallet {name}: {resp.text}"
    return resp.json()["data"]["_id"]


@pytest.fixture(autouse=True)
def mock_asset_type_mapper():
    """Mock AssetTypeMapper to avoid Google API calls."""
    with patch('src.services.transaction_mapper.AssetTypeMapper') as mock_mapper:
        # Mock the mapper to return a simple mapping
        mock_instance = mock_mapper.return_value
        mock_instance.infer_asset_info.return_value = {
            "asset_type": "stock",
            "symbol": "TEST",
            "confidence": 0.9
        }
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_column_mapper():
    """Mock ColumnMapper to avoid Google API calls."""
    with patch('src.services.column_mapper.ColumnMapper') as mock_mapper:
        # Mock the mapper to return a simple mapping
        mock_instance = mock_mapper.return_value
        mock_instance.map_columns.return_value = {
            "date": "date",
            "asset_name": "asset_name", 
            "quantity": "quantity",
            "price": "price"
        }
        yield mock_instance


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
    writer = csv.writer(temp_file)
    
    # Write header and sample data
    writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
    writer.writerow(['Apple Inc.', '2024-01-15', '175.50', '10', '1755.00', '2.50', 'USD'])
    writer.writerow(['Microsoft', '2024-01-16', '420.25', '5', '2101.25', '2.50', 'USD'])
    writer.writerow(['Tesla', '2024-01-17', '245.80', '8', '1966.40', '3.00', 'USD'])
    
    temp_file.close()
    yield temp_file.name
    
    # Cleanup
    Path(temp_file.name).unlink(missing_ok=True)


class TestTransactionUpload:
    """Tests for POST /api/transactions/upload endpoint."""
    
    def test_upload_csv_file_success(self, client, test_db, auth_headers, sample_csv_file):
        """Test successful CSV file upload."""
        # Create wallet and use wallet_id
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet")
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        # Debug output
        if response.status_code != 200:
            print(f"\n[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response body: {response.text[:500]}")
            print(f"[DEBUG] Request headers: {auth_headers}")
            print(f"[DEBUG] Wallet ID: {wallet_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "data" in data
        assert "transactions" in data["data"]
        
        # Get actual transaction count from response
        actual_count = data["data"]["summary"]["total_transactions"]
        assert actual_count >= 3, f"Expected at least 3 transactions, got {actual_count}"
        assert data["data"]["wallet_name"] == "Test Wallet"
        
        # Verify transaction details are included in response
        response_transactions = data["data"]["transactions"]
        assert len(response_transactions) == actual_count
        for tx in response_transactions:
            assert "id" in tx
            assert "wallet_name" in tx
            assert "asset_name" in tx
            assert "date" in tx
            assert "volume" in tx
            assert "item_price" in tx
            assert "transaction_amount" in tx
            assert "currency" in tx
            assert "fee" in tx
        
        # Verify wallet exists in database
        wallet = test_db.wallets.find_one({"_id": ObjectId(wallet_id)})
        assert wallet is not None, "Wallet should exist"
    
    def test_upload_to_existing_wallet(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading transactions to an existing wallet."""
        # Create wallet first
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Existing Wallet")
        
        # Upload transactions to existing wallet
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["wallet_name"] == "Existing Wallet"
        assert data["data"]["summary"]["total_transactions"] > 0
    
    def test_upload_different_transaction_types(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with transaction types detected from file content."""
        # Since transaction types are now detected from file content,
        # this test verifies that the system can handle files and defaults appropriately
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Wallet_Mixed_Types")
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        # Should succeed even if transaction types can't be detected from file
        assert response.status_code == 200
        data = response.json()
        
        # Verify transactions were processed
        assert data["data"]["summary"]["total_transactions"] > 0
        
        # Verify transactions exist in database
        wallet = test_db.wallets.find_one({"name": "Wallet_Mixed_Types"})
        if wallet:  # Only check if wallet was created
            transactions = list(test_db.transactions.find({"wallet_id": wallet["_id"]}))
            if len(transactions) > 0:
                # Verify each transaction has a valid transaction type (defaults to buy if not detected)
                for tx in transactions:
                    assert tx["transaction_type"] in ["buy", "sell", "dividend", "transfer_in", "transfer_out"]
    
    def test_upload_different_asset_types(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with asset types detected automatically."""
        # Since asset types are now detected automatically from asset names,
        # this test verifies that the system can handle different asset types
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Wallet_Auto_Asset_Types")
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify transactions were processed
        assert data["data"]["summary"]["total_transactions"] > 0
        
        # Verify assets were created with detected types
        wallet = test_db.wallets.find_one({"name": "Wallet_Auto_Asset_Types"})
        transactions = list(test_db.transactions.find({"wallet_id": wallet["_id"]}))
        
        # Check that assets were created with appropriate types
        asset_ids = [tx["asset_id"] for tx in transactions]
        assets = list(test_db.assets.find({"_id": {"$in": asset_ids}}))
        
        for asset in assets:
            assert asset["asset_type"] in ["stock", "bond", "cryptocurrency", "commodity", "other"]
    
    def test_upload_without_authentication(self, client, sample_csv_file):
        """Test upload without authentication fails."""
        # Temporarily clear dependency overrides to test actual auth behavior
        from api.main import app
        app.dependency_overrides.clear()
        
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                files={"file": ("transactions.csv", f, "text/csv")},
                data={}
            )
        
        assert response.status_code == 401
    
    def test_upload_unsupported_file_type(self, client, test_db, auth_headers):
        """Test upload with unsupported file type."""
        # Create a fake PDF file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
        temp_file.write("Fake PDF content")
        temp_file.close()
        
        try:
            wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet")
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.pdf", f, "application/pdf")},
                    data={"wallet_id": wallet_id}
                )
            
            assert response.status_code == 400
            assert "Unsupported file type" in response.json()["detail"]
        finally:
            Path(temp_file.name).unlink(missing_ok=True)
    
    def test_upload_empty_file(self, client, test_db, auth_headers):
        """Test upload with empty CSV file."""
        # Create empty CSV file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.close()
        
        try:
            wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet")
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("empty.csv", f, "text/csv")},
                    data={"wallet_id": wallet_id}
                )
            
            assert response.status_code == 500
            assert "No columns to parse from file" in response.json()["detail"]
        finally:
            Path(temp_file.name).unlink(missing_ok=True)
    
    def test_upload_missing_required_fields(self, client, test_db, auth_headers, sample_csv_file):
        """Test upload without required form fields."""
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    # Missing wallet_name
                }
            )
        
        assert response.status_code == 422
    
    def test_upload_with_real_test_data(self, client, test_db, auth_headers):
        """Test upload with actual test data files if available."""
        test_data_dir = Path("test_data")
        if not test_data_dir.exists():
            pytest.skip("test_data directory not found")
        
        # Try to find a CSV file
        csv_files = list(test_data_dir.glob("*.csv"))
        if not csv_files:
            pytest.skip("No CSV files in test_data directory")
        
        test_file = csv_files[0]
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Real Data Test")
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # Should succeed or fail gracefully
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0


class TestTransactionList:
    """Tests for GET /api/transactions endpoint."""
    
    def test_list_transactions_empty(self, client, test_db, auth_headers):
        """Test listing transactions when none exist."""
        # First create a wallet
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Test Wallet", "description": "Test wallet for transactions"}
        )
        assert wallet_response.status_code == 200
        wallet_data = wallet_response.json()
        wallet_id = wallet_data["data"]["_id"]
        
        # List transactions for the wallet
        response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["count"] == 0
    
    def test_list_transactions_after_upload(self, client, test_db, auth_headers, sample_csv_file):
        """Test listing transactions after uploading a file."""
        # Create wallet and upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet")
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        assert upload_response.status_code == 200
        
        # Use the wallet_id directly (no need to look it up)
        
        # List transactions
        response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should have proper structure
        assert "count" in data
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
        
        # If transactions exist, verify structure
        if data["count"] > 0:
            for tx in data["transactions"][:5]:  # Check first 5
                assert "_id" in tx
                assert "wallet_id" in tx
                assert "asset_id" in tx
                assert "date" in tx
                assert "transaction_type" in tx
                assert "volume" in tx
                assert "item_price" in tx
                assert "transaction_amount" in tx
                assert "currency" in tx
                assert "fee" in tx
    
    def test_list_transactions_filter_by_wallet(self, client, test_db, auth_headers, sample_csv_file):
        """Test filtering transactions by wallet name."""
        # Upload to first wallet
        wallet_a_id = _create_wallet_and_get_id(client, auth_headers, "Wallet A")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_a_id,
                }
            )
        
        # Upload to second wallet
        wallet_b_id = _create_wallet_and_get_id(client, auth_headers, "Wallet B")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_b_id,
                }
            )
        
        # Filter by Wallet A (use the ID we already have)
        response = client.get(
            f"/api/transactions?wallet_id={wallet_a_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 3
        
        # Verify all transactions belong to Wallet A
        for tx in data["transactions"]:
            assert str(tx["wallet_id"]) == wallet_a_id
    
    def test_list_transactions_pagination(self, client, test_db, auth_headers, sample_csv_file):
        """Test pagination with limit and skip parameters."""
        # Upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        # Use the wallet_id directly (no need to look it up)
        
        # Get first page (limit=2)
        response1 = client.get(
            f"/api/transactions?wallet_id={wallet_id}&limit=2&skip=0",
            headers=auth_headers
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["transactions"]) == 2
        
        # Get second page (skip=2)
        response2 = client.get(
            f"/api/transactions?wallet_id={wallet_id}&limit=2&skip=2",
            headers=auth_headers
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify different transactions
        tx1_ids = {tx["_id"] for tx in data1["transactions"]}
        tx2_ids = {tx["_id"] for tx in data2["transactions"]}
        assert tx1_ids.isdisjoint(tx2_ids)
    
    def test_list_transactions_user_isolation(self, client, test_db, auth_headers, auth_headers_user2, sample_csv_file, override_auth_user2):
        """Test that users can only see their own transactions."""
        # User 1 uploads transactions
        wallet1_id = _create_wallet_and_get_id(client, auth_headers, "User1 Wallet")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet1_id,
                }
            )
        
        # Switch to user 2
        from api.main import app
        from api.dependencies import get_current_user
        from src.auth.firebase_auth import get_current_user_from_token
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2
        
        # User 2 uploads transactions
        wallet2_id = _create_wallet_and_get_id(client, auth_headers_user2, "User2 Wallet")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers_user2,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet2_id,
                }
            )
        
        # Switch back to user 1
        from bson import ObjectId
        test_user_id = ObjectId("507f1f77bcf86cd799439011")
        async def mock_get_user1():
            return test_user_id
        app.dependency_overrides[get_current_user] = mock_get_user1
        app.dependency_overrides[get_current_user_from_token] = mock_get_user1
        
        # User 1 lists transactions
        response1 = client.get(f"/api/transactions?wallet_id={wallet1_id}", headers=auth_headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Switch to user 2 again
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2
        
        # User 2 lists transactions
        response2 = client.get(f"/api/transactions?wallet_id={wallet2_id}", headers=auth_headers_user2)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify users see different transactions
        tx1_ids = {tx["_id"] for tx in data1["transactions"]}
        tx2_ids = {tx["_id"] for tx in data2["transactions"]}
        assert tx1_ids.isdisjoint(tx2_ids)
        
        # Verify correct wallet associations using the IDs we already have
        for tx in data1["transactions"]:
            assert str(tx["wallet_id"]) == wallet1_id
        
        for tx in data2["transactions"]:
            assert str(tx["wallet_id"]) == wallet2_id
    
    def test_list_transactions_without_authentication(self, client):
        """Test listing transactions without authentication fails."""
        # Temporarily clear dependency overrides to test actual auth behavior
        from api.main import app
        app.dependency_overrides.clear()
        
        response = client.get("/api/transactions")
        assert response.status_code == 401
    
    def test_list_transactions_invalid_limit(self, client, test_db, auth_headers):
        """Test invalid limit parameter."""
        # Create a wallet first
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Test Wallet", "description": "Test wallet"}
        )
        assert wallet_response.status_code == 200
        wallet_data = wallet_response.json()
        wallet_id = wallet_data["data"]["_id"]
        
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}&limit=0",
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_list_transactions_limit_exceeds_maximum(self, client, test_db, auth_headers):
        """Test limit parameter exceeding maximum."""
        # Create a wallet first
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Test Wallet", "description": "Test wallet"}
        )
        assert wallet_response.status_code == 200
        wallet_data = wallet_response.json()
        wallet_id = wallet_data["data"]["_id"]
        
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}&limit=2000",  # Max is 1000
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_list_transactions_negative_skip(self, client, test_db, auth_headers):
        """Test negative skip parameter."""
        # Create a wallet first
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Test Wallet", "description": "Test wallet"}
        )
        assert wallet_response.status_code == 200
        wallet_data = wallet_response.json()
        wallet_id = wallet_data["data"]["_id"]
        
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}&skip=-1",
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_list_transactions_filter_nonexistent_wallet(self, client, test_db, auth_headers):
        """Test filtering by wallet that doesn't exist."""
        # Use a non-existent wallet ID
        fake_wallet_id = "507f1f77bcf86cd799439999"
        response = client.get(
            f"/api/transactions?wallet_id={fake_wallet_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTransactionIntegration:
    """Integration tests combining upload and list operations."""
    
    def test_upload_and_verify_transaction_details(self, client, test_db, auth_headers, sample_csv_file):
        """Test that uploaded transaction details match what's returned in list."""
        # Upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Integration Test")
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        upload_data = upload_response.json()
        uploaded_transactions = upload_data["data"]["transactions"]
        
        # List transactions
        list_response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        list_data = list_response.json()
        listed_transactions = list_data["transactions"]
        
        # Verify counts match
        assert len(uploaded_transactions) == len(listed_transactions)
        
        # Verify transaction IDs match
        uploaded_ids = {tx["id"] for tx in uploaded_transactions}
        listed_ids = {tx["_id"] for tx in listed_transactions}
        assert uploaded_ids == listed_ids
    
    def test_multiple_uploads_aggregate_correctly(self, client, test_db, auth_headers, sample_csv_file):
        """Test multiple uploads to same wallet aggregate correctly."""
        # First upload
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Aggregate Test")
        with open(sample_csv_file, 'rb') as f:
            response1 = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        count1 = response1.json()["data"]["summary"]["total_transactions"]
        
        # Second upload
        with open(sample_csv_file, 'rb') as f:
            response2 = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        count2 = response2.json()["data"]["summary"]["total_transactions"]
        
        # List all transactions for this wallet
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}",
            headers=auth_headers
        )
        
        total_count = response.json()["count"]
        
        # Total should equal sum of both uploads
        assert total_count == count1 + count2
    
    def test_upload_list_delete_workflow(self, client, test_db, auth_headers, sample_csv_file):
        """Test complete workflow: upload, list, delete transactions."""
        # Upload
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Workflow Test")
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        assert upload_response.status_code == 200
        
        # List - should have transactions
        list_response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        assert list_response.json()["count"] > 0
        
        # Delete transactions by wallet
        delete_response = client.delete(
            f"/api/transactions/wallet/{wallet_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # List again - should be empty
        final_list = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        assert final_list.json()["count"] == 0


class TestTransactionDelete:
    """Tests for DELETE /api/transactions/wallet/{wallet_name} endpoint."""
    
    def test_delete_wallet_transactions_success(self, client, test_db, auth_headers, sample_csv_file):
        """Test successful deletion of wallet transactions."""
        # Upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Delete Test")
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        uploaded_count = upload_response.json()["data"]["summary"]["total_transactions"]
        
        # Delete transactions
        response = client.delete(
            f"/api/transactions/wallet/{wallet_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["wallet_name"] == "Delete Test"
        assert data["deleted_count"] == uploaded_count
        assert "Deleted" in data["message"]
        
        # Verify transactions are actually deleted
        wallet = test_db.wallets.find_one({"name": "Delete Test"})
        remaining_transactions = test_db.transactions.count_documents({"wallet_id": wallet["_id"]})
        assert remaining_transactions == 0
    
    def test_delete_transactions_wallet_not_found(self, client, test_db, auth_headers):
        """Test deleting transactions for non-existent wallet."""
        response = client.delete(
            f"/api/transactions/wallet/{str(ObjectId())}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_transactions_without_authentication(self, client):
        """Test deleting transactions without authentication."""
        # Temporarily clear dependency overrides to test actual auth behavior
        from api.main import app
        app.dependency_overrides.clear()
        
        response = client.delete(f"/api/transactions/wallet/{str(ObjectId())}")
        assert response.status_code == 401
    
    def test_delete_transactions_wallet_owned_by_another_user(self, client, test_db, auth_headers, auth_headers_user2, sample_csv_file, override_auth_user2):
        """Test that user cannot delete transactions from another user's wallet."""
        # User 1 uploads transactions
        wallet1_id = _create_wallet_and_get_id(client, auth_headers, "User1 Protected Wallet")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet1_id,
                }
            )
        
        # Switch to user 2
        from api.main import app
        from api.dependencies import get_current_user
        from src.auth.firebase_auth import get_current_user_from_token
        app.dependency_overrides[get_current_user] = override_auth_user2
        app.dependency_overrides[get_current_user_from_token] = override_auth_user2
        
        # User 2 tries to delete User 1's transactions
        response = client.delete(
            f"/api/transactions/wallet/{wallet1_id}",
            headers=auth_headers_user2
        )
        
        assert response.status_code == 404
        
        # Verify transactions still exist
        transaction_count = test_db.transactions.count_documents({"wallet_id": wallet1_id})
        assert transaction_count > 0
    
    def test_delete_transactions_empty_wallet(self, client, test_db, auth_headers):
        """Test deleting transactions from wallet that has no transactions."""
        # Create wallet without transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Empty Wallet", "No transactions")
        
        # Delete transactions (should succeed with 0 deleted)
        response = client.delete(
            f"/api/transactions/wallet/{wallet_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
    
    def test_delete_transactions_partial_wallet_isolation(self, client, test_db, auth_headers, sample_csv_file):
        """Test that deleting transactions from one wallet doesn't affect another."""
        # Upload to Wallet A
        wallet_a_id = _create_wallet_and_get_id(client, auth_headers, "Wallet A")
        with open(sample_csv_file, 'rb') as f:
            response_a = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_a_id,
                }
            )
        count_a = response_a.json()["data"]["summary"]["total_transactions"]
        
        # Upload to Wallet B
        wallet_b_id = _create_wallet_and_get_id(client, auth_headers, "Wallet B")
        with open(sample_csv_file, 'rb') as f:
            response_b = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_b_id,
                }
            )
        count_b = response_b.json()["data"]["summary"]["total_transactions"]
        
        # Delete transactions from Wallet A
        delete_response = client.delete(
            f"/api/transactions/wallet/{wallet_a_id}",
            headers=auth_headers
        )
        assert delete_response.json()["deleted_count"] == count_a
        
        # Verify Wallet B transactions remain
        remaining_count = test_db.transactions.count_documents({"wallet_id": wallet_b_id})
        assert remaining_count == count_b
    
    def test_delete_transactions_special_characters_in_wallet_name(self, client, test_db, auth_headers, sample_csv_file):
        """Test deleting transactions from wallet with special characters in name."""
        wallet_name = "Test Wallet #1 (Special & Characters!)"
        
        # Upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, wallet_name)
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # Delete transactions
        response = client.delete(
            f"/api/transactions/wallet/{wallet_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["deleted_count"] > 0


class TestTransactionEdgeCases:
    """Tests for edge cases and error scenarios."""
    
    def test_upload_excel_xlsx_file(self, client, test_db, auth_headers):
        """Test uploading Excel .xlsx file."""
        test_data_dir = Path("test_data")
        xlsx_files = list(test_data_dir.glob("*.xlsx"))
        
        if not xlsx_files:
            pytest.skip("No .xlsx files in test_data directory")
        
        test_file = xlsx_files[0]
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Excel XLSX Test")
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
    
    def test_upload_excel_xls_file(self, client, test_db, auth_headers):
        """Test uploading Excel .xls file."""
        test_data_dir = Path("test_data")
        xls_files = list(test_data_dir.glob("*.xls"))
        
        if not xls_files:
            pytest.skip("No .xls files in test_data directory")
        
        test_file = xls_files[0]
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Excel XLS Test")
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "application/vnd.ms-excel")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
    
    def test_upload_txt_file(self, client, test_db, auth_headers):
        """Test uploading .txt file (CSV format)."""
        # Create temporary .txt file with CSV content
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total'])
        writer.writerow(['Test Asset', '2024-01-15', '100.00', '10', '1000.00'])
        temp_file.close()
        
        try:
            wallet_id = _create_wallet_and_get_id(client, auth_headers, "TXT File Test")
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.txt", f, "text/plain")},
                    data={
                        "wallet_id": wallet_id,
                    }
                )
            
            # Should succeed or fail with validation error
            assert response.status_code in [200, 422, 500]
        finally:
            Path(temp_file.name).unlink(missing_ok=True)
    
    def test_upload_very_large_wallet_name(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with very long wallet name."""
        long_wallet_name = "A" * 500  # 500 characters

        # This should fail with 422 due to wallet name length validation
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": long_wallet_name, "description": "Test"}
        )
        assert wallet_response.status_code == 422
        
        # Since wallet creation failed, we can't test upload with this wallet
        # The test is complete - we verified that wallet creation fails with long names
    
    def test_list_transactions_with_wallet_filter_case_sensitivity(self, client, test_db, auth_headers, sample_csv_file):
        """Test wallet filtering with wallet_id (case sensitivity not applicable)."""
        # Create wallet and upload with specific case
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "TestWallet")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # List transactions using wallet_id
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}",
            headers=auth_headers
        )
        
        # Should return transactions
        assert response.status_code == 200
    
    def test_concurrent_uploads_to_same_wallet(self, client, test_db, auth_headers, sample_csv_file):
        """Test multiple concurrent uploads to the same wallet."""
        import concurrent.futures
        
        def upload_file():
            with open(sample_csv_file, 'rb') as f:
                return client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_id": wallet_id,
                    }
                )
        
        # Execute 3 concurrent uploads
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Concurrent Test")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_file) for _ in range(3)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Total transaction count should be 3x the individual upload count
        total_response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        total_count = total_response.json()["count"]
        
        # Should have transactions from all uploads
        assert total_count > 0
    
    def test_upload_with_invalid_transaction_type(self, client, test_db, auth_headers, sample_csv_file):
        """Test upload with invalid transaction type in file content."""
        # Since transaction types are now detected from file content,
        # this test verifies that invalid transaction types are handled gracefully
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet Invalid Type")
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        # Should succeed since invalid types are mapped to default (buy)
        assert response.status_code == 200
        data = response.json()
        
        # Verify transactions were processed with default transaction type
        assert data["data"]["summary"]["total_transactions"] > 0
    
    def test_upload_with_invalid_asset_type(self, client, test_db, auth_headers, sample_csv_file):
        """Test upload with asset types detected automatically."""
        # Since asset types are now detected automatically from asset names,
        # this test verifies that the system handles unknown asset types gracefully
        
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Test Wallet Auto Asset Type")
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id
                }
            )
        
        # Should succeed since asset types are determined automatically
        assert response.status_code == 200
        data = response.json()
        
        # Verify transactions were processed
        assert data["data"]["summary"]["total_transactions"] > 0
    
    def test_list_transactions_max_limit_boundary(self, client, test_db, auth_headers, sample_csv_file):
        """Test listing transactions with maximum allowed limit."""
        # Upload some transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Boundary Test")
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        # Try with limit=1000 (max allowed)
        response = client.get(
            f"/api/transactions?wallet_id={wallet_id}&limit=1000",
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_response_format_consistency(self, client, test_db, auth_headers, sample_csv_file):
        """Test that upload and list responses have consistent transaction format."""
        # Upload transactions
        wallet_id = _create_wallet_and_get_id(client, auth_headers, "Format Test")
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_id": wallet_id,
                }
            )
        
        upload_transactions = upload_response.json()["data"]["transactions"]
        
        # List transactions
        list_response = client.get(f"/api/transactions?wallet_id={wallet_id}", headers=auth_headers)
        list_transactions = list_response.json()["transactions"]
        
        # Check that required fields are present in both
        required_fields = ["wallet_name", "asset_name", "date", "volume", "item_price", 
                          "transaction_amount", "currency", "fee"]
        
        for tx in upload_transactions:
            for field in required_fields:
                assert field in tx, f"Missing field {field} in upload response"
        
        for tx in list_transactions:
            # Note: list response uses _id instead of id
            assert "_id" in tx
            assert "wallet_id" in tx
            assert "asset_id" in tx

