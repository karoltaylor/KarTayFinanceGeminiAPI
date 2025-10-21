"""Unit tests for statistics API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from bson import ObjectId

from api.main import app
from src.config.mongodb import get_db

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database for testing."""
    mock_db = MagicMock()
    mock_db.wallets = MagicMock()
    mock_db.assets = MagicMock()
    mock_db.transactions = MagicMock()
    return mock_db


@pytest.fixture
def client(mock_db):
    """Create test client with mocked database dependency."""
    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: mock_db
    test_client = TestClient(app)
    yield test_client
    # Clean up after test
    app.dependency_overrides.clear()


class TestGetStatistics:
    """Tests for GET /api/stats endpoint."""

    def test_get_statistics_success(self, client, mock_db):
        """Test successful retrieval of user statistics."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Mock wallet data
        mock_wallets = [
            {"_id": ObjectId("507f1f77bcf86cd799439021")},
            {"_id": ObjectId("507f1f77bcf86cd799439022")}
        ]
        
        # Mock transaction aggregation result
        mock_transaction_types = [
            {"_id": "buy", "count": 10},
            {"_id": "sell", "count": 5}
        ]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.assets.count_documents.return_value = 25
            mock_db.transactions.count_documents.return_value = 15
            mock_db.transactions.aggregate.return_value = mock_transaction_types
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_wallets"] == 2
            assert data["total_assets"] == 25
            assert data["total_transactions"] == 15
            assert data["transactions_by_type"]["buy"] == 10
            assert data["transactions_by_type"]["sell"] == 5

    def test_get_statistics_no_wallets(self, client, mock_db):
        """Test statistics when user has no wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = []
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_wallets"] == 0
            assert data["total_assets"] == 10
            assert data["total_transactions"] == 0
            assert data["transactions_by_type"] == {}

    def test_get_statistics_no_transactions(self, client, mock_db):
        """Test statistics when user has no transactions."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": ObjectId()}]
            mock_db.assets.count_documents.return_value = 5
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_wallets"] == 1
            assert data["total_assets"] == 5
            assert data["total_transactions"] == 0
            assert data["transactions_by_type"] == {}

    def test_get_statistics_string_user_id(self, client, mock_db):
        """Test statistics with string user_id in wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Mock wallets with string user_id
        mock_wallets = [
            {"_id": ObjectId("507f1f77bcf86cd799439021"), "user_id": str(user_id)},
            {"_id": ObjectId("507f1f77bcf86cd799439022"), "user_id": str(user_id)}
        ]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 5
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_wallets"] == 2

    def test_get_statistics_objectid_user_id(self, client, mock_db):
        """Test statistics with ObjectId user_id in wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Mock wallets with ObjectId user_id
        mock_wallets = [
            {"_id": ObjectId("507f1f77bcf86cd799439021"), "user_id": user_id},
            {"_id": ObjectId("507f1f77bcf86cd799439022"), "user_id": user_id}
        ]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 5
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_wallets"] == 2

    def test_get_statistics_transaction_types_with_enum(self, client, mock_db):
        """Test statistics with transaction types that have value attribute."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        # Mock enum-like transaction type
        class MockTransactionType:
            def __init__(self, value):
                self.value = value
        
        mock_transaction_types = [
            {"_id": MockTransactionType("buy"), "count": 10},
            {"_id": MockTransactionType("sell"), "count": 5}
        ]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": ObjectId()}]
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 15
            mock_db.transactions.aggregate.return_value = mock_transaction_types
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["transactions_by_type"]["buy"] == 10
            assert data["transactions_by_type"]["sell"] == 5

    def test_get_statistics_transaction_types_without_enum(self, client, mock_db):
        """Test statistics with transaction types without value attribute."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        mock_transaction_types = [
            {"_id": "buy", "count": 10},
            {"_id": "sell", "count": 5}
        ]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": ObjectId()}]
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 15
            mock_db.transactions.aggregate.return_value = mock_transaction_types
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["transactions_by_type"]["buy"] == 10
            assert data["transactions_by_type"]["sell"] == 5

    def test_get_statistics_database_error(self, client, mock_db):
        """Test statistics handles database errors gracefully."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.side_effect = Exception("Database connection failed")
            
            # The endpoint doesn't have explicit error handling, so it will raise 500
            with pytest.raises(Exception, match="Database connection failed"):
                client.get("/api/stats")

    def test_get_statistics_aggregation_error(self, client, mock_db):
        """Test statistics handles aggregation errors gracefully."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": ObjectId()}]
            mock_db.assets.count_documents.return_value = 10
            mock_db.transactions.count_documents.return_value = 5
            mock_db.transactions.aggregate.side_effect = Exception("Aggregation failed")
            
            # The endpoint doesn't have explicit error handling, so it will raise 500
            with pytest.raises(Exception, match="Aggregation failed"):
                client.get("/api/stats")

    def test_get_statistics_verifies_query_structure(self, client, mock_db):
        """Test that the correct query structure is used for wallet lookup."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = []
            mock_db.assets.count_documents.return_value = 0
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            
            # Verify the correct query was used for wallet lookup
            expected_query = {
                "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]
            }
            mock_db.wallets.find.assert_called_with(expected_query, {"_id": 1})

    def test_get_statistics_verifies_transaction_query(self, client, mock_db):
        """Test that the correct query structure is used for transaction counting."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_ids = [ObjectId("507f1f77bcf86cd799439021"), ObjectId("507f1f77bcf86cd799439022")]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": wid} for wid in wallet_ids]
            mock_db.assets.count_documents.return_value = 0
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            
            # Verify the correct query was used for transaction counting
            expected_query = {"wallet_id": {"$in": wallet_ids}}
            mock_db.transactions.count_documents.assert_called_with(expected_query)

    def test_get_statistics_verifies_aggregation_pipeline(self, client, mock_db):
        """Test that the correct aggregation pipeline is used."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_ids = [ObjectId("507f1f77bcf86cd799439021")]
        
        with patch('api.routers.stats.get_current_user_from_token', return_value=user_id):
            mock_db.wallets.find.return_value = [{"_id": wid} for wid in wallet_ids]
            mock_db.assets.count_documents.return_value = 0
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []
            
            response = client.get("/api/stats")
            
            assert response.status_code == 200
            
            # Verify the correct aggregation pipeline was used
            expected_pipeline = [
                {"$match": {"wallet_id": {"$in": wallet_ids}}},
                {"$group": {"_id": "$transaction_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            mock_db.transactions.aggregate.assert_called_with(expected_pipeline)