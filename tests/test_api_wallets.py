"""Integration tests for FastAPI wallet endpoints."""

import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime

from api.main import app
from src.config.mongodb import MongoDBConfig

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="function")
def test_db():
    """
    Get test database instance and set up test user.
    
    NOTE: This uses the database configured in environment.
    For true isolation, consider using a separate test database.
    """
    db = MongoDBConfig.get_database()
    
    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")
    test_user_id_2 = ObjectId("507f1f77bcf86cd799439012")
    
    # Clean up test data before each test
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.transactions.delete_many({})  # Clean all test transactions
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    
    # Create test users (use update with upsert to avoid duplicate key errors)
    test_user_1 = {
        "_id": test_user_id,
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    test_user_2 = {
        "_id": test_user_id_2,
        "email": "test2@example.com",
        "username": "testuser2",
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
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.transactions.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})


@pytest.fixture
def test_user_id():
    """Fixed test user ID for all tests."""
    return "507f1f77bcf86cd799439011"


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(test_user_id):
    """Authentication headers with test user ID."""
    return {"X-User-ID": test_user_id}


class TestListWallets:
    """Tests for GET /api/wallets endpoint."""

    def test_list_wallets_empty(self, client, auth_headers, test_db):
        """Test listing wallets when user has none."""
        response = client.get("/api/wallets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "wallets" in data
        assert "count" in data
        assert data["count"] == 0
        assert data["wallets"] == []

    def test_list_wallets_with_data(self, client, auth_headers, test_db, test_user_id):
        """Test listing wallets when user has wallets."""
        # Create test wallets
        wallet1 = {
            "user_id": ObjectId(test_user_id),
            "name": "Test Wallet 1",
            "description": "First test wallet",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        wallet2 = {
            "user_id": ObjectId(test_user_id),
            "name": "Test Wallet 2",
            "description": "Second test wallet",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        test_db.wallets.insert_many([wallet1, wallet2])
        
        response = client.get("/api/wallets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["wallets"]) == 2
        
        # Check wallet structure
        wallet = data["wallets"][0]
        assert "_id" in wallet
        assert "user_id" in wallet
        assert "name" in wallet
        assert "description" in wallet
        assert "created_at" in wallet
        assert "updated_at" in wallet

    def test_list_wallets_pagination(self, client, auth_headers, test_db, test_user_id):
        """Test wallet listing with pagination."""
        # Create 5 test wallets
        wallets = [
            {
                "user_id": ObjectId(test_user_id),
                "name": f"Wallet {i}",
                "description": f"Test wallet {i}",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            for i in range(5)
        ]
        test_db.wallets.insert_many(wallets)
        
        # Test limit
        response = client.get("/api/wallets?limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        
        # Test skip
        response = client.get("/api/wallets?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_list_wallets_without_auth(self, client):
        """Test that listing wallets without auth header fails."""
        response = client.get("/api/wallets")
        
        assert response.status_code == 422  # Unprocessable Entity (missing required header)

    def test_list_wallets_invalid_user_id(self, client):
        """Test that invalid user ID in header fails."""
        headers = {"X-User-ID": "invalid-id"}
        response = client.get("/api/wallets", headers=headers)
        
        assert response.status_code == 401
        assert "Invalid user ID" in response.json()["detail"]

    def test_list_wallets_only_shows_user_wallets(self, client, auth_headers, test_db, test_user_id):
        """Test that users only see their own wallets."""
        # Create wallet for test user
        test_wallet = {
            "user_id": ObjectId(test_user_id),
            "name": "My Wallet",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create wallet for different user
        other_user_wallet = {
            "user_id": ObjectId("507f1f77bcf86cd799439012"),  # Different user
            "name": "Other User Wallet",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        test_db.wallets.insert_many([test_wallet, other_user_wallet])
        
        response = client.get("/api/wallets", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["wallets"][0]["name"] == "My Wallet"


class TestCreateWallet:
    """Tests for POST /api/wallets endpoint."""

    def test_create_wallet_success(self, client, auth_headers, test_db):
        """Test successful wallet creation."""
        wallet_data = {
            "name": "My Investment Wallet",
            "description": "For tracking investments"
        }
        
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Wallet 'My Investment Wallet' created successfully" in data["message"]
        assert "data" in data
        assert data["data"]["name"] == "My Investment Wallet"
        assert data["data"]["description"] == "For tracking investments"
        assert "_id" in data["data"]
        assert "user_id" in data["data"]

    def test_create_wallet_without_description(self, client, auth_headers, test_db):
        """Test creating wallet without optional description."""
        wallet_data = {
            "name": "Simple Wallet"
        }
        
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "Simple Wallet"
        assert data["data"]["description"] is None

    def test_create_wallet_duplicate_name(self, client, auth_headers, test_db, test_user_id):
        """Test that creating wallet with duplicate name fails."""
        # Create first wallet
        wallet_data = {"name": "My Wallet", "description": "First wallet"}
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response.status_code == 200
        
        # Try to create wallet with same name
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_wallet_invalid_data(self, client, auth_headers, test_db):
        """Test creating wallet with invalid data."""
        # Missing required name field
        wallet_data = {"description": "No name"}
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response.status_code == 422
        
        # Empty name
        wallet_data = {"name": ""}
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        assert response.status_code == 422

    def test_create_wallet_name_too_long(self, client, auth_headers, test_db):
        """Test creating wallet with name exceeding max length."""
        wallet_data = {
            "name": "A" * 201  # Max is 200 characters
        }
        
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        
        assert response.status_code == 422

    def test_create_wallet_without_auth(self, client):
        """Test that creating wallet without auth fails."""
        wallet_data = {"name": "Unauthorized Wallet"}
        response = client.post("/api/wallets", json=wallet_data)
        
        assert response.status_code == 422

    def test_create_wallet_strips_whitespace(self, client, auth_headers, test_db):
        """Test that wallet name whitespace is stripped."""
        wallet_data = {
            "name": "  Wallet With Spaces  "
        }
        
        response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Wallet With Spaces"


class TestDeleteWallet:
    """Tests for DELETE /api/wallets/{wallet_id} endpoint."""

    def test_delete_wallet_success(self, client, auth_headers, test_db, test_user_id):
        """Test successful wallet deletion."""
        # Create a wallet
        wallet = {
            "user_id": ObjectId(test_user_id),
            "name": "Wallet to Delete",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = test_db.wallets.insert_one(wallet)
        wallet_id = str(result.inserted_id)
        
        response = client.delete(f"/api/wallets/{wallet_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted successfully" in data["message"]
        
        # Verify wallet is deleted
        deleted_wallet = test_db.wallets.find_one({"_id": result.inserted_id})
        assert deleted_wallet is None

    def test_delete_wallet_with_transactions(self, client, auth_headers, test_db, test_user_id):
        """Test deleting wallet also deletes its transactions."""
        # Create wallet
        wallet = {
            "user_id": ObjectId(test_user_id),
            "name": "Wallet with Transactions",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = test_db.wallets.insert_one(wallet)
        wallet_id = result.inserted_id
        
        # Create some transactions
        transactions = [
            {
                "wallet_id": wallet_id,
                "asset_id": ObjectId(),
                "date": datetime.utcnow(),
                "transaction_type": "buy",
                "volume": 10.0,
                "item_price": 100.0,
                "transaction_amount": 1000.0,
                "currency": "USD",
                "fee": 5.0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            for _ in range(3)
        ]
        test_db.transactions.insert_many(transactions)
        
        response = client.delete(f"/api/wallets/{str(wallet_id)}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["transactions_deleted"] == 3
        
        # Verify transactions are deleted
        remaining_transactions = test_db.transactions.count_documents({"wallet_id": wallet_id})
        assert remaining_transactions == 0

    def test_delete_wallet_not_found(self, client, auth_headers, test_db):
        """Test deleting non-existent wallet."""
        fake_wallet_id = str(ObjectId())
        
        response = client.delete(f"/api/wallets/{fake_wallet_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_delete_wallet_invalid_id_format(self, client, auth_headers, test_db):
        """Test deleting wallet with invalid ID format."""
        response = client.delete("/api/wallets/invalid-id", headers=auth_headers)
        
        assert response.status_code == 400
        assert "Invalid wallet ID format" in response.json()["detail"]

    def test_delete_wallet_owned_by_another_user(self, client, auth_headers, test_db):
        """Test that users cannot delete other users' wallets."""
        # Create wallet for different user
        other_user_id = ObjectId("507f1f77bcf86cd799439012")
        other_user_wallet = {
            "user_id": other_user_id,
            "name": "Other User Wallet Test",  # Unique name to avoid conflicts
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = test_db.wallets.insert_one(other_user_wallet)
        wallet_id = str(result.inserted_id)
        wallet_obj_id = result.inserted_id
        
        # Try to delete as different user
        response = client.delete(f"/api/wallets/{wallet_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found or not owned by user" in response.json()["detail"]
        
        # Verify wallet still exists for the other user
        wallet = test_db.wallets.find_one({"_id": wallet_obj_id})
        assert wallet is not None
        
        # Clean up this specific test wallet
        test_db.wallets.delete_one({"_id": wallet_obj_id})

    def test_delete_wallet_without_auth(self, client, test_db, test_user_id):
        """Test that deleting wallet without auth fails."""
        # Create a wallet
        wallet = {
            "user_id": ObjectId(test_user_id),
            "name": "Protected Wallet",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = test_db.wallets.insert_one(wallet)
        wallet_id = str(result.inserted_id)
        
        response = client.delete(f"/api/wallets/{wallet_id}")
        
        assert response.status_code == 422


class TestWalletEndpointsIntegration:
    """Integration tests for combined wallet operations."""

    def test_create_list_delete_workflow(self, client, auth_headers, test_db):
        """Test complete workflow: create, list, and delete wallets."""
        # Initially no wallets (or check response structure)
        response = client.get("/api/wallets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        initial_count = data.get("count", 0)
        
        # Create first wallet
        wallet1_data = {"name": "Savings", "description": "My savings account"}
        response = client.post("/api/wallets", json=wallet1_data, headers=auth_headers)
        assert response.status_code == 200
        wallet1_id = response.json()["data"]["_id"]
        
        # Create second wallet
        wallet2_data = {"name": "Investment", "description": "Investment portfolio"}
        response = client.post("/api/wallets", json=wallet2_data, headers=auth_headers)
        assert response.status_code == 200
        wallet2_id = response.json()["data"]["_id"]
        
        # List should show 2 wallets (plus any initial ones)
        response = client.get("/api/wallets", headers=auth_headers)
        assert response.json()["count"] == initial_count + 2
        
        # Delete first wallet
        response = client.delete(f"/api/wallets/{wallet1_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # List should show 1 wallet (plus any initial ones)
        response = client.get("/api/wallets", headers=auth_headers)
        data = response.json()
        assert data["count"] == initial_count + 1
        # Find the Investment wallet in the list
        wallet_names = [w["name"] for w in data["wallets"]]
        assert "Investment" in wallet_names
        
        # Delete second wallet
        response = client.delete(f"/api/wallets/{wallet2_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # List should be back to initial count
        response = client.get("/api/wallets", headers=auth_headers)
        assert response.json()["count"] == initial_count

    def test_multiple_users_isolation(self, client, test_db):
        """Test that wallet operations are isolated between users."""
        user1_headers = {"X-User-ID": "507f1f77bcf86cd799439011"}
        user2_headers = {"X-User-ID": "507f1f77bcf86cd799439012"}
        
        # Get initial counts for both users
        response1 = client.get("/api/wallets", headers=user1_headers)
        assert response1.status_code == 200
        user1_initial = response1.json()["count"]
        
        response2 = client.get("/api/wallets", headers=user2_headers)
        assert response2.status_code == 200
        user2_initial = response2.json()["count"]
        
        # User 1 creates a wallet
        wallet_data = {"name": "User 1 Wallet"}
        response = client.post("/api/wallets", json=wallet_data, headers=user1_headers)
        assert response.status_code == 200
        
        # User 2 creates a wallet with the same name (should succeed - different user)
        response = client.post("/api/wallets", json=wallet_data, headers=user2_headers)
        assert response.status_code == 200
        
        # User 1 sees only their wallet
        response = client.get("/api/wallets", headers=user1_headers)
        assert response.status_code == 200
        assert response.json()["count"] == user1_initial + 1
        
        # User 2 sees only their wallet
        response = client.get("/api/wallets", headers=user2_headers)
        assert response.status_code == 200
        assert response.json()["count"] == user2_initial + 1

