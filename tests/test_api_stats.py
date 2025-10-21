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
            {"_id": ObjectId("507f1f77bcf86cd799439022")},
        ]

        # Mock transaction aggregation result
        mock_transaction_types = [
            {"_id": "buy", "count": 10},
            {"_id": "sell", "count": 5},
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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
            {"_id": ObjectId("507f1f77bcf86cd799439022"), "user_id": str(user_id)},
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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
            {"_id": ObjectId("507f1f77bcf86cd799439022"), "user_id": user_id},
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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
            {"_id": MockTransactionType("sell"), "count": 5},
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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
            {"_id": "sell", "count": 5},
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.side_effect = Exception("Database connection failed")

            # The endpoint doesn't have explicit error handling, so it will raise 500
            with pytest.raises(Exception, match="Database connection failed"):
                client.get("/api/stats")

    def test_get_statistics_aggregation_error(self, client, mock_db):
        """Test statistics handles aggregation errors gracefully."""
        user_id = ObjectId("507f1f77bcf86cd799439011")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = []
            mock_db.assets.count_documents.return_value = 0
            mock_db.transactions.count_documents.return_value = 0
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats")

            assert response.status_code == 200

            # Verify the correct query was used for wallet lookup
            expected_query = {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
            mock_db.wallets.find.assert_called_with(expected_query, {"_id": 1})

    def test_get_statistics_verifies_transaction_query(self, client, mock_db):
        """Test that the correct query structure is used for transaction counting."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_ids = [
            ObjectId("507f1f77bcf86cd799439021"),
            ObjectId("507f1f77bcf86cd799439022"),
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
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


class TestGetAssetTypePercentages:
    """Tests for GET /api/stats/asset-types endpoint."""

    def test_get_asset_type_percentages_success(self, client, mock_db):
        """Test successful retrieval of asset type percentages."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")
        asset_id_1 = ObjectId("507f1f77bcf86cd799439031")
        asset_id_2 = ObjectId("507f1f77bcf86cd799439032")

        # Mock wallet data
        mock_wallets = [{"_id": wallet_id}]

        # Mock asset type statistics aggregation result
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 10000.0,
                "transaction_count": 5,
                "unique_assets": [asset_id_1],
            },
            {
                "_id": "bond",
                "total_value": 5000.0,
                "transaction_count": 3,
                "unique_assets": [asset_id_2],
            },
        ]

        # Mock unique assets aggregation results
        mock_unique_assets_stock = [{"_id": asset_id_1}]
        mock_unique_assets_bond = [{"_id": asset_id_2}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,  # First call for main aggregation
                mock_unique_assets_stock,  # Second call for stock unique assets
                mock_unique_assets_bond,  # Third call for bond unique assets
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 15000.0
            assert data["total_transactions"] == 8
            assert data["unique_assets"] == 2

            # Check asset type breakdown
            assert len(data["asset_type_breakdown"]) == 2

            # Stock should be first (higher value)
            stock_breakdown = data["asset_type_breakdown"][0]
            assert stock_breakdown["asset_type"] == "stock"
            assert stock_breakdown["percentage"] == 66.67  # 10000/15000 * 100
            assert stock_breakdown["total_value"] == 10000.0
            assert stock_breakdown["transaction_count"] == 5

            # Bond should be second
            bond_breakdown = data["asset_type_breakdown"][1]
            assert bond_breakdown["asset_type"] == "bond"
            assert bond_breakdown["percentage"] == 33.33  # 5000/15000 * 100
            assert bond_breakdown["total_value"] == 5000.0
            assert bond_breakdown["transaction_count"] == 3

    def test_get_asset_type_percentages_no_wallets(self, client, mock_db):
        """Test asset type percentages when user has no wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 0.0
            assert data["asset_type_breakdown"] == []
            assert data["total_transactions"] == 0
            assert data["unique_assets"] == 0

    def test_get_asset_type_percentages_no_transactions(self, client, mock_db):
        """Test asset type percentages when user has no transactions."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = [{"_id": wallet_id}]
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 0.0
            assert data["asset_type_breakdown"] == []
            assert data["total_transactions"] == 0
            assert data["unique_assets"] == 0

    def test_get_asset_type_percentages_single_asset_type(self, client, mock_db):
        """Test asset type percentages with only one asset type."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")
        asset_id = ObjectId("507f1f77bcf86cd799439031")

        mock_wallets = [{"_id": wallet_id}]
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 10000.0,
                "transaction_count": 5,
                "unique_assets": [asset_id],
            }
        ]
        mock_unique_assets = [{"_id": asset_id}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,
                mock_unique_assets,
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 10000.0
            assert data["total_transactions"] == 5
            assert data["unique_assets"] == 1

            assert len(data["asset_type_breakdown"]) == 1
            breakdown = data["asset_type_breakdown"][0]
            assert breakdown["asset_type"] == "stock"
            assert breakdown["percentage"] == 100.0
            assert breakdown["total_value"] == 10000.0
            assert breakdown["transaction_count"] == 5

    def test_get_asset_type_percentages_zero_total_value(self, client, mock_db):
        """Test asset type percentages when total value is zero."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")

        mock_wallets = [{"_id": wallet_id}]
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 0.0,
                "transaction_count": 0,
                "unique_assets": [],
            }
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,
                [],  # No unique assets
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 0.0
            assert data["total_transactions"] == 0
            assert data["unique_assets"] == 0

            assert len(data["asset_type_breakdown"]) == 1
            breakdown = data["asset_type_breakdown"][0]
            assert breakdown["percentage"] == 0.0

    def test_get_asset_type_percentages_multiple_wallets(self, client, mock_db):
        """Test asset type percentages with multiple wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id_1 = ObjectId("507f1f77bcf86cd799439021")
        wallet_id_2 = ObjectId("507f1f77bcf86cd799439022")
        asset_id = ObjectId("507f1f77bcf86cd799439031")

        mock_wallets = [{"_id": wallet_id_1}, {"_id": wallet_id_2}]
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 15000.0,
                "transaction_count": 8,
                "unique_assets": [asset_id],
            }
        ]
        mock_unique_assets = [{"_id": asset_id}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,
                mock_unique_assets,
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 15000.0
            assert data["total_transactions"] == 8
            assert data["unique_assets"] == 1

    def test_get_asset_type_percentages_string_user_id(self, client, mock_db):
        """Test asset type percentages with string user_id in wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")

        mock_wallets = [{"_id": wallet_id, "user_id": str(user_id)}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 0.0
            assert data["asset_type_breakdown"] == []

    def test_get_asset_type_percentages_objectid_user_id(self, client, mock_db):
        """Test asset type percentages with ObjectId user_id in wallets."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")

        mock_wallets = [{"_id": wallet_id, "user_id": user_id}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 0.0
            assert data["asset_type_breakdown"] == []

    def test_get_asset_type_percentages_verifies_query_structure(self, client, mock_db):
        """Test that the correct query structure is used for wallet lookup."""
        user_id = ObjectId("507f1f77bcf86cd799439011")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = []
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200

            # Verify the correct query was used for wallet lookup
            expected_query = {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
            mock_db.wallets.find.assert_called_with(expected_query, {"_id": 1})

    def test_get_asset_type_percentages_verifies_aggregation_pipeline(
        self, client, mock_db
    ):
        """Test that the correct aggregation pipeline is used."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_ids = [ObjectId("507f1f77bcf86cd799439021")]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = [{"_id": wid} for wid in wallet_ids]
            mock_db.transactions.aggregate.return_value = []

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200

            # Verify the correct aggregation pipeline was used
            expected_pipeline = [
                {"$match": {"wallet_id": {"$in": wallet_ids}}},
                {
                    "$lookup": {
                        "from": "assets",
                        "localField": "asset_id",
                        "foreignField": "_id",
                        "as": "asset",
                    }
                },
                {"$unwind": "$asset"},
                {
                    "$group": {
                        "_id": "$asset.asset_type",
                        "total_value": {"$sum": "$transaction_amount"},
                        "transaction_count": {"$sum": 1},
                        "unique_assets": {"$addToSet": "$asset_id"},
                    }
                },
                {"$addFields": {"unique_assets": {"$size": "$unique_assets"}}},
                {"$sort": {"total_value": -1}},
            ]
            mock_db.transactions.aggregate.assert_called_with(expected_pipeline)

    def test_get_asset_type_percentages_database_error(self, client, mock_db):
        """Test asset type percentages handles database errors gracefully."""
        user_id = ObjectId("507f1f77bcf86cd799439011")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.side_effect = Exception("Database connection failed")

            # The endpoint doesn't have explicit error handling, so it will raise 500
            with pytest.raises(Exception, match="Database connection failed"):
                client.get("/api/stats/asset-types")

    def test_get_asset_type_percentages_aggregation_error(self, client, mock_db):
        """Test asset type percentages handles aggregation errors gracefully."""
        user_id = ObjectId("507f1f77bcf86cd799439011")

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = [{"_id": ObjectId()}]
            mock_db.transactions.aggregate.side_effect = Exception("Aggregation failed")

            # The endpoint doesn't have explicit error handling, so it will raise 500
            with pytest.raises(Exception, match="Aggregation failed"):
                client.get("/api/stats/asset-types")

    def test_get_asset_type_percentages_precision_rounding(self, client, mock_db):
        """Test that percentages are properly rounded to 2 decimal places."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")
        asset_id = ObjectId("507f1f77bcf86cd799439031")

        mock_wallets = [{"_id": wallet_id}]
        # Use values that will result in repeating decimals
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 1000.0,
                "transaction_count": 1,
                "unique_assets": [asset_id],
            },
            {
                "_id": "bond",
                "total_value": 333.33,
                "transaction_count": 1,
                "unique_assets": [asset_id],
            },
        ]
        mock_unique_assets = [{"_id": asset_id}]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,
                mock_unique_assets,
                mock_unique_assets,
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            # Check that percentages are rounded to 2 decimal places
            stock_breakdown = data["asset_type_breakdown"][0]
            bond_breakdown = data["asset_type_breakdown"][1]

            assert (
                stock_breakdown["percentage"] == 75.0
            )  # 1000/1333.33 * 100 = 75.000...
            assert (
                bond_breakdown["percentage"] == 25.0
            )  # 333.33/1333.33 * 100 = 25.000...

    def test_get_asset_type_percentages_all_asset_types(self, client, mock_db):
        """Test asset type percentages with all supported asset types."""
        user_id = ObjectId("507f1f77bcf86cd799439011")
        wallet_id = ObjectId("507f1f77bcf86cd799439021")

        mock_wallets = [{"_id": wallet_id}]

        # Mock all asset types from the enum
        mock_asset_stats = [
            {
                "_id": "stock",
                "total_value": 1000.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "bond",
                "total_value": 800.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "etf",
                "total_value": 600.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "managed mutual fund",
                "total_value": 400.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "real_estate",
                "total_value": 200.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "cryptocurrency",
                "total_value": 100.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "commodity",
                "total_value": 50.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "cash",
                "total_value": 25.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
            {
                "_id": "other",
                "total_value": 10.0,
                "transaction_count": 1,
                "unique_assets": [],
            },
        ]

        with patch(
            "api.routers.stats.get_current_user_from_token", return_value=user_id
        ):
            mock_db.wallets.find.return_value = mock_wallets
            mock_db.transactions.aggregate.side_effect = [
                mock_asset_stats,
                *([[]] * 9),  # Empty unique assets for each type
            ]

            response = client.get("/api/stats/asset-types")

            assert response.status_code == 200
            data = response.json()

            assert data["total_portfolio_value"] == 3185.0
            assert data["total_transactions"] == 9
            assert data["unique_assets"] == 0

            # Verify all asset types are present and sorted by value
            asset_types = [
                breakdown["asset_type"] for breakdown in data["asset_type_breakdown"]
            ]
            expected_order = [
                "stock",
                "bond",
                "etf",
                "managed mutual fund",
                "real_estate",
                "cryptocurrency",
                "commodity",
                "cash",
                "other",
            ]
            assert asset_types == expected_order
