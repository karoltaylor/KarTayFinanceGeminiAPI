"""Unit tests for system API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app
from src.config.mongodb import get_db

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_db():
    """Mock database for testing."""
    mock_db = MagicMock()
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


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_endpoint_success(self, client):
        """Test successful root endpoint response."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Financial Transaction API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert data["authentication"] == "OAuth2 (Google, Meta, etc.)"
        assert "endpoints" in data

        # Verify all expected endpoints are present
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert "user_register" in endpoints
        assert "list_wallets" in endpoints
        assert "create_wallet" in endpoints
        assert "delete_wallet" in endpoints
        assert "list_assets" in endpoints
        assert "list_transactions" in endpoints
        assert "upload_transactions" in endpoints
        assert "delete_wallet_transactions" in endpoints
        assert "stats" in endpoints

    def test_root_endpoint_response_structure(self, client):
        """Test that root endpoint response has correct structure."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        required_fields = ["name", "version", "status", "authentication", "endpoints"]
        for field in required_fields:
            assert field in data

        # Verify endpoints structure
        assert isinstance(data["endpoints"], dict)
        assert len(data["endpoints"]) > 0

    def test_root_endpoint_no_dependencies(self, client):
        """Test that root endpoint doesn't require any dependencies."""
        # This endpoint should work without any database or auth dependencies
        response = client.get("/")
        assert response.status_code == 200


class TestHealthCheckEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check_success(self, client, mock_db):
        """Test successful health check when database is connected."""
        with patch(
            "api.routers.system.MongoDBConfig.get_mongodb_database",
            return_value="test_db",
        ):
            # Mock successful ping
            mock_db.command.return_value = {"ok": 1}

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["mongodb"] == "connected"
            assert data["database"] == "test_db"

            # Verify ping command was called
            mock_db.command.assert_called_with("ping")

    def test_health_check_database_disconnected(self, client, mock_db):
        """Test health check when database is disconnected."""
        # Mock database connection failure
        mock_db.command.side_effect = Exception("Connection refused")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["mongodb"] == "disconnected"
        assert "error" in data
        assert "Connection refused" in data["error"]

    def test_health_check_database_timeout(self, client, mock_db):
        """Test health check when database times out."""
        # Mock database timeout
        mock_db.command.side_effect = Exception("Operation timed out")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["mongodb"] == "disconnected"
        assert "Operation timed out" in data["error"]

    def test_health_check_database_auth_error(self, client, mock_db):
        """Test health check when database authentication fails."""
        # Mock authentication failure
        mock_db.command.side_effect = Exception("Authentication failed")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["mongodb"] == "disconnected"
        assert "Authentication failed" in data["error"]

    def test_health_check_database_not_found(self, client, mock_db):
        """Test health check when database is not found."""
        # Mock database not found
        mock_db.command.side_effect = Exception("Database not found")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["mongodb"] == "disconnected"
        assert "Database not found" in data["error"]

    def test_health_check_verifies_ping_command(self, client, mock_db):
        """Test that health check uses the correct ping command."""
        with patch(
            "api.routers.system.MongoDBConfig.get_mongodb_database",
            return_value="test_db",
        ):
            mock_db.command.return_value = {"ok": 1}

            response = client.get("/health")

            assert response.status_code == 200
            # Verify ping command was called exactly once
            mock_db.command.assert_called_once_with("ping")

    def test_health_check_database_name_retrieval(self, client, mock_db):
        """Test that health check retrieves database name correctly."""
        with patch(
            "api.routers.system.MongoDBConfig.get_mongodb_database",
            return_value="production_db",
        ) as mock_get_db_name:
            mock_db.command.return_value = {"ok": 1}

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["database"] == "production_db"

            # Verify database name retrieval was called
            mock_get_db_name.assert_called_once()

    def test_health_check_response_format(self, client, mock_db):
        """Test that health check response has correct format."""
        with patch(
            "api.routers.system.MongoDBConfig.get_mongodb_database",
            return_value="test_db",
        ):
            mock_db.command.return_value = {"ok": 1}

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert isinstance(data, dict)
            assert "status" in data
            assert "mongodb" in data
            assert "database" in data

            # Verify status values
            assert data["status"] in ["healthy", "unhealthy"]
            assert data["mongodb"] in ["connected", "disconnected"]

    def test_health_check_error_response_format(self, client, mock_db):
        """Test that health check error response has correct format."""
        mock_db.command.side_effect = Exception("Test error")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()

        # Verify error response structure
        assert isinstance(data, dict)
        assert "status" in data
        assert "mongodb" in data
        assert "error" in data

        # Verify error values
        assert data["status"] == "unhealthy"
        assert data["mongodb"] == "disconnected"
        assert isinstance(data["error"], str)
        assert len(data["error"]) > 0
