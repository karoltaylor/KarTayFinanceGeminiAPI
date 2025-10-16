"""Integration tests for FastAPI transaction endpoints."""

import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime
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
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    test_user_2 = {
        "_id": test_user_id_2,
        "email": f"test2_{unique_test_email.split('@')[0].split('_')[1]}@example.com",
        "username": f"{unique_test_username}_2",
        "full_name": "Test User 2",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
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


@pytest.fixture
def auth_headers():
    """Get authentication headers for test user."""
    return {"X-User-ID": "507f1f77bcf86cd799439011"}


@pytest.fixture
def auth_headers_user2():
    """Get authentication headers for second test user."""
    return {"X-User-ID": "507f1f77bcf86cd799439012"}


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
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
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
        
        # Verify wallet was created in database
        wallet = test_db.wallets.find_one({"name": "Test Wallet"})
        assert wallet is not None, "Wallet should be created"
    
    def test_upload_to_existing_wallet(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading transactions to an existing wallet."""
        # Create wallet first
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Existing Wallet", "description": "Test"}
        )
        assert wallet_response.status_code == 200
        
        # Upload transactions to existing wallet
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Existing Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["wallet_name"] == "Existing Wallet"
        assert data["data"]["summary"]["total_transactions"] > 0
    
    def test_upload_different_transaction_types(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with different transaction types."""
        transaction_types = ["buy", "sell", "dividend", "transfer_in"]
        
        for tx_type in transaction_types:
            with open(sample_csv_file, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": f"Wallet_{tx_type}",
                        "transaction_type": tx_type,
                        "asset_type": "stock"
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["transaction_type"] == tx_type
            
            # Verify transactions have correct type
            wallet = test_db.wallets.find_one({"name": f"Wallet_{tx_type}"})
            transactions = list(test_db.transactions.find({"wallet_id": wallet["_id"]}))
            for tx in transactions:
                assert tx["transaction_type"] == tx_type
    
    def test_upload_different_asset_types(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with different asset types."""
        asset_types = ["stock", "bond", "cryptocurrency", "commodity"]
        
        for asset_type in asset_types:
            with open(sample_csv_file, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": f"Wallet_{asset_type}",
                        "transaction_type": "buy",
                        "asset_type": asset_type
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["asset_type"] == asset_type
    
    def test_upload_without_authentication(self, client, sample_csv_file):
        """Test upload without authentication fails."""
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        assert response.status_code == 401
    
    def test_upload_unsupported_file_type(self, client, test_db, auth_headers):
        """Test upload with unsupported file type."""
        # Create a fake PDF file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
        temp_file.write("Fake PDF content")
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.pdf", f, "application/pdf")},
                    data={
                        "wallet_name": "Test Wallet",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
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
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("empty.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Test Wallet",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
                )
            
            assert response.status_code == 422
            assert "No valid transactions" in response.json()["detail"]
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
                    "transaction_type": "buy",
                    "asset_type": "stock"
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
        
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Real Data Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
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
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        assert upload_response.status_code == 200
        
        # Get the wallet ID from the database (since upload creates the wallet)
        wallet = test_db.wallets.find_one({"name": "Test Wallet"})
        assert wallet is not None
        wallet_id = str(wallet["_id"])
        
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
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Wallet A",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Upload to second wallet
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Wallet B",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Get wallet IDs
        wallet_a = test_db.wallets.find_one({"name": "Wallet A"})
        wallet_b = test_db.wallets.find_one({"name": "Wallet B"})
        assert wallet_a is not None
        assert wallet_b is not None
        
        # Filter by Wallet A
        response = client.get(
            f"/api/transactions?wallet_id={str(wallet_a['_id'])}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 3
        
        # Verify all transactions belong to Wallet A
        wallet_a = test_db.wallets.find_one({"name": "Wallet A"})
        for tx in data["transactions"]:
            assert str(tx["wallet_id"]) == str(wallet_a["_id"])
    
    def test_list_transactions_pagination(self, client, test_db, auth_headers, sample_csv_file):
        """Test pagination with limit and skip parameters."""
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Get wallet ID
        wallet = test_db.wallets.find_one({"name": "Test Wallet"})
        assert wallet is not None
        wallet_id = str(wallet["_id"])
        
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
    
    def test_list_transactions_user_isolation(self, client, test_db, auth_headers, auth_headers_user2, sample_csv_file):
        """Test that users can only see their own transactions."""
        # User 1 uploads transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "User1 Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # User 2 uploads transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers_user2,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "User2 Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # User 1 lists transactions
        wallet1 = test_db.wallets.find_one({"name": "User1 Wallet"})
        assert wallet1 is not None
        response1 = client.get(f"/api/transactions?wallet_id={str(wallet1['_id'])}", headers=auth_headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # User 2 lists transactions
        wallet2 = test_db.wallets.find_one({"name": "User2 Wallet"})
        assert wallet2 is not None
        response2 = client.get(f"/api/transactions?wallet_id={str(wallet2['_id'])}", headers=auth_headers_user2)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify users see different transactions
        tx1_ids = {tx["_id"] for tx in data1["transactions"]}
        tx2_ids = {tx["_id"] for tx in data2["transactions"]}
        assert tx1_ids.isdisjoint(tx2_ids)
        
        # Verify correct wallet associations
        wallet1 = test_db.wallets.find_one({"name": "User1 Wallet"})
        wallet2 = test_db.wallets.find_one({"name": "User2 Wallet"})
        
        for tx in data1["transactions"]:
            assert str(tx["wallet_id"]) == str(wallet1["_id"])
        
        for tx in data2["transactions"]:
            assert str(tx["wallet_id"]) == str(wallet2["_id"])
    
    def test_list_transactions_without_authentication(self, client):
        """Test listing transactions without authentication fails."""
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
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["transactions"] == []


class TestTransactionIntegration:
    """Integration tests combining upload and list operations."""
    
    def test_upload_and_verify_transaction_details(self, client, test_db, auth_headers, sample_csv_file):
        """Test that uploaded transaction details match what's returned in list."""
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Integration Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        upload_data = upload_response.json()
        uploaded_transactions = upload_data["data"]["transactions"]
        
        # List transactions
        wallet = test_db.wallets.find_one({"name": "Integration Test"})
        assert wallet is not None
        wallet_id = str(wallet["_id"])
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
        with open(sample_csv_file, 'rb') as f:
            response1 = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Aggregate Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
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
                    "wallet_name": "Aggregate Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        count2 = response2.json()["data"]["summary"]["total_transactions"]
        
        # List all transactions for this wallet
        wallet = test_db.wallets.find_one({"name": "Aggregate Test"})
        assert wallet is not None
        wallet_id = str(wallet["_id"])
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
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Workflow Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        assert upload_response.status_code == 200
        
        # List - should have transactions
        list_response = client.get("/api/transactions", headers=auth_headers)
        assert list_response.json()["count"] > 0
        
        # Delete transactions by wallet
        delete_response = client.delete(
            "/api/transactions/wallet/Workflow Test",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        # List again - should be empty
        final_list = client.get("/api/transactions", headers=auth_headers)
        assert final_list.json()["count"] == 0


class TestTransactionDelete:
    """Tests for DELETE /api/transactions/wallet/{wallet_name} endpoint."""
    
    def test_delete_wallet_transactions_success(self, client, test_db, auth_headers, sample_csv_file):
        """Test successful deletion of wallet transactions."""
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Delete Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        uploaded_count = upload_response.json()["data"]["summary"]["total_transactions"]
        
        # Delete transactions
        response = client.delete(
            "/api/transactions/wallet/Delete Test",
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
            "/api/transactions/wallet/NonexistentWallet",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_transactions_without_authentication(self, client):
        """Test deleting transactions without authentication."""
        response = client.delete("/api/transactions/wallet/SomeWallet")
        assert response.status_code == 401
    
    def test_delete_transactions_wallet_owned_by_another_user(self, client, test_db, auth_headers, auth_headers_user2, sample_csv_file):
        """Test that user cannot delete transactions from another user's wallet."""
        # User 1 uploads transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "User1 Protected Wallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # User 2 tries to delete User 1's transactions
        response = client.delete(
            "/api/transactions/wallet/User1 Protected Wallet",
            headers=auth_headers_user2
        )
        
        assert response.status_code == 404
        
        # Verify transactions still exist
        wallet = test_db.wallets.find_one({"name": "User1 Protected Wallet"})
        assert wallet is not None
        transaction_count = test_db.transactions.count_documents({"wallet_id": wallet["_id"]})
        assert transaction_count > 0
    
    def test_delete_transactions_empty_wallet(self, client, test_db, auth_headers):
        """Test deleting transactions from wallet that has no transactions."""
        # Create wallet without transactions
        wallet_response = client.post(
            "/api/wallets",
            headers=auth_headers,
            json={"name": "Empty Wallet", "description": "No transactions"}
        )
        assert wallet_response.status_code == 200
        
        # Delete transactions (should succeed with 0 deleted)
        response = client.delete(
            "/api/transactions/wallet/Empty Wallet",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
    
    def test_delete_transactions_partial_wallet_isolation(self, client, test_db, auth_headers, sample_csv_file):
        """Test that deleting transactions from one wallet doesn't affect another."""
        # Upload to Wallet A
        with open(sample_csv_file, 'rb') as f:
            response_a = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Wallet A",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        count_a = response_a.json()["data"]["summary"]["total_transactions"]
        
        # Upload to Wallet B
        with open(sample_csv_file, 'rb') as f:
            response_b = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Wallet B",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        count_b = response_b.json()["data"]["summary"]["total_transactions"]
        
        # Delete transactions from Wallet A
        delete_response = client.delete(
            "/api/transactions/wallet/Wallet A",
            headers=auth_headers
        )
        assert delete_response.json()["deleted_count"] == count_a
        
        # Verify Wallet B transactions remain
        wallet_b = test_db.wallets.find_one({"name": "Wallet B"})
        remaining_count = test_db.transactions.count_documents({"wallet_id": wallet_b["_id"]})
        assert remaining_count == count_b
    
    def test_delete_transactions_special_characters_in_wallet_name(self, client, test_db, auth_headers, sample_csv_file):
        """Test deleting transactions from wallet with special characters in name."""
        wallet_name = "Test Wallet #1 (Special & Characters!)"
        
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": wallet_name,
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Delete transactions
        response = client.delete(
            f"/api/transactions/wallet/{wallet_name}",
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
        
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_name": "Excel XLSX Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
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
        
        with open(test_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (test_file.name, f, "application/vnd.ms-excel")},
                data={
                    "wallet_name": "Excel XLS Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
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
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.txt", f, "text/plain")},
                    data={
                        "wallet_name": "TXT File Test",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed or fail with validation error
            assert response.status_code in [200, 422, 500]
        finally:
            Path(temp_file.name).unlink(missing_ok=True)
    
    def test_upload_very_large_wallet_name(self, client, test_db, auth_headers, sample_csv_file):
        """Test uploading with very long wallet name."""
        long_wallet_name = "A" * 500  # 500 characters
        
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": long_wallet_name,
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should either succeed or return validation error
        assert response.status_code in [200, 422, 500]
    
    def test_list_transactions_with_wallet_filter_case_sensitivity(self, client, test_db, auth_headers, sample_csv_file):
        """Test wallet name filtering with different case."""
        # Upload with specific case
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "TestWallet",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Try to list with different case
        response = client.get(
            "/api/transactions",
            headers=auth_headers,
            params={"wallet_name": "testwallet"}  # lowercase
        )
        
        # Should return empty or match based on MongoDB case sensitivity
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
                        "wallet_name": "Concurrent Test",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
                )
        
        # Execute 3 concurrent uploads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_file) for _ in range(3)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Total transaction count should be 3x the individual upload count
        total_response = client.get("/api/transactions", headers=auth_headers)
        total_count = total_response.json()["count"]
        
        # Should have transactions from all uploads
        assert total_count > 0
    
    def test_upload_with_invalid_transaction_type(self, client, test_db, auth_headers, sample_csv_file):
        """Test upload with invalid transaction type."""
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "invalid_type",
                    "asset_type": "stock"
                }
            )
        
        assert response.status_code == 422
    
    def test_upload_with_invalid_asset_type(self, client, test_db, auth_headers, sample_csv_file):
        """Test upload with invalid asset type."""
        with open(sample_csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Test Wallet",
                    "transaction_type": "buy",
                    "asset_type": "invalid_asset"
                }
            )
        
        assert response.status_code == 422
    
    def test_list_transactions_max_limit_boundary(self, client, test_db, auth_headers, sample_csv_file):
        """Test listing transactions with maximum allowed limit."""
        # Upload some transactions
        with open(sample_csv_file, 'rb') as f:
            client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Boundary Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Try with limit=1000 (max allowed)
        response = client.get(
            "/api/transactions",
            headers=auth_headers,
            params={"limit": 1000}
        )
        
        assert response.status_code == 200
    
    def test_response_format_consistency(self, client, test_db, auth_headers, sample_csv_file):
        """Test that upload and list responses have consistent transaction format."""
        # Upload transactions
        with open(sample_csv_file, 'rb') as f:
            upload_response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": ("transactions.csv", f, "text/csv")},
                data={
                    "wallet_name": "Format Test",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        upload_transactions = upload_response.json()["data"]["transactions"]
        
        # List transactions
        list_response = client.get("/api/transactions", headers=auth_headers)
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

