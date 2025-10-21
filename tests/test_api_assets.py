"""Unit tests for assets API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from bson import ObjectId

from api.main import app
from src.models import AssetType
from src.config.mongodb import get_db

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database for testing."""
    mock_db = MagicMock()
    mock_db.assets = MagicMock()
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


class TestListAssets:
    """Tests for GET /api/assets endpoint."""

    def test_list_assets_success(self, client, mock_db):
        """Test successful listing of assets."""
        mock_assets = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Apple Inc.",
                "symbol": "AAPL",
                "asset_type": "stock",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "name": "Microsoft Corp.",
                "symbol": "MSFT",
                "asset_type": "stock",
            },
        ]

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets")

        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert "count" in data
        assert "filter" in data
        assert data["count"] == 2
        assert len(data["assets"]) == 2

        # Verify ObjectIds are converted to strings
        for asset in data["assets"]:
            assert isinstance(asset["_id"], str)

    def test_list_assets_with_asset_type_filter(self, client, mock_db):
        """Test listing assets with asset type filter."""
        mock_assets = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Apple Inc.",
                "symbol": "AAPL",
                "asset_type": "stock",
            }
        ]

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets?asset_type=stock")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["filter"] == {"asset_type": "stock"}

        # Verify query was called with correct filter
        mock_db.assets.find.assert_called_with({"asset_type": "stock"})

    def test_list_assets_with_pagination(self, client, mock_db):
        """Test listing assets with pagination parameters."""
        mock_assets = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Apple Inc.",
                "symbol": "AAPL",
                "asset_type": "stock",
            }
        ]

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets?limit=10&skip=5")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

        # Verify pagination parameters were applied
        mock_cursor.skip.assert_called_with(5)
        mock_cursor.skip.return_value.limit.assert_called_with(10)

    def test_list_assets_empty_result(self, client, mock_db):
        """Test listing assets when no assets exist."""
        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = []
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["assets"] == []
        assert data["filter"] == {}

    def test_list_assets_invalid_asset_type(self, client):
        """Test listing assets with invalid asset type."""
        response = client.get("/api/assets?asset_type=invalid_type")
        assert response.status_code == 422

    def test_list_assets_limit_too_low(self, client):
        """Test listing assets with limit below minimum."""
        response = client.get("/api/assets?limit=0")
        assert response.status_code == 422

    def test_list_assets_limit_too_high(self, client):
        """Test listing assets with limit above maximum."""
        response = client.get("/api/assets?limit=1001")
        assert response.status_code == 422

    def test_list_assets_skip_negative(self, client):
        """Test listing assets with negative skip value."""
        response = client.get("/api/assets?skip=-1")
        assert response.status_code == 422

    def test_list_assets_default_parameters(self, client, mock_db):
        """Test listing assets with default parameters."""
        mock_assets = []

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets")

        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == {}

        # Verify default pagination parameters
        mock_cursor.skip.assert_called_with(0)
        mock_cursor.skip.return_value.limit.assert_called_with(100)

    def test_list_assets_maximum_limit(self, client, mock_db):
        """Test listing assets with maximum allowed limit."""
        mock_assets = []

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets?limit=1000")

        assert response.status_code == 200
        mock_cursor.skip.return_value.limit.assert_called_with(1000)

    def test_list_assets_multiple_filters(self, client, mock_db):
        """Test listing assets with multiple query parameters."""
        mock_assets = []

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets?asset_type=stock&limit=50&skip=10")

        assert response.status_code == 200
        data = response.json()
        assert data["filter"] == {"asset_type": "stock"}

        # Verify all parameters were applied
        mock_db.assets.find.assert_called_with({"asset_type": "stock"})
        mock_cursor.skip.assert_called_with(10)
        mock_cursor.skip.return_value.limit.assert_called_with(50)

    def test_list_assets_database_error(self, client, mock_db):
        """Test listing assets handles database errors gracefully."""
        mock_db.assets.find.side_effect = Exception("Database connection failed")

        # The endpoint doesn't have explicit error handling, so it will raise 500
        # We need to catch the exception that bubbles up
        with pytest.raises(Exception, match="Database connection failed"):
            client.get("/api/assets")

    def test_list_assets_all_asset_types(self, client, mock_db):
        """Test listing assets with different asset types."""
        asset_types = ["stock", "bond", "cryptocurrency", "commodity", "other"]

        for asset_type in asset_types:
            # Set up mock cursor
            mock_cursor = MagicMock()
            mock_cursor.skip.return_value.limit.return_value = []
            mock_db.assets.find.return_value = mock_cursor

            response = client.get(f"/api/assets?asset_type={asset_type}")

            assert response.status_code == 200
            data = response.json()
            assert data["filter"] == {"asset_type": asset_type}

    def test_list_assets_objectid_conversion(self, client, mock_db):
        """Test that ObjectIds are properly converted to strings."""
        mock_assets = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "Test Asset",
                "symbol": "TEST",
                "asset_type": "stock",
            }
        ]

        # Set up mock cursor
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value.limit.return_value = mock_assets
        mock_db.assets.find.return_value = mock_cursor

        response = client.get("/api/assets")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["assets"][0]["_id"], str)
        assert data["assets"][0]["_id"] == "507f1f77bcf86cd799439011"
