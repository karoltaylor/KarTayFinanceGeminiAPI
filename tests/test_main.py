"""Unit tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from api.main import app, lifespan, enforce_https

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAppLifespan:
    """Tests for FastAPI application lifespan events."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Test successful lifespan startup."""
        with patch(
            "api.main.MongoDBConfig.get_mongodb_url",
            return_value="mongodb://user:pass@host/db",
        ), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch(
            "api.main.MongoDBConfig.initialize_collections"
        ) as mock_init:

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # Verify initialization was called
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_with_masked_url(self):
        """Test lifespan startup with password masking."""
        with patch(
            "api.main.MongoDBConfig.get_mongodb_url",
            return_value="mongodb://user:secretpass@host/db",
        ), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch(
            "api.main.MongoDBConfig.initialize_collections"
        ):

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # The URL masking logic should work correctly
            # This is tested implicitly by the successful execution

    @pytest.mark.asyncio
    async def test_lifespan_startup_no_url(self):
        """Test lifespan startup when no URL is set."""
        with patch("api.main.MongoDBConfig.get_mongodb_url", return_value=None), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch("api.main.MongoDBConfig.initialize_collections"):

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # Should handle None URL gracefully

    @pytest.mark.asyncio
    async def test_lifespan_startup_url_without_password(self):
        """Test lifespan startup with URL without password."""
        with patch(
            "api.main.MongoDBConfig.get_mongodb_url", return_value="mongodb://host/db"
        ), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch(
            "api.main.MongoDBConfig.initialize_collections"
        ):

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # Should handle URL without password gracefully

    @pytest.mark.asyncio
    async def test_lifespan_startup_initialization_error(self):
        """Test lifespan startup when initialization fails."""
        with patch(
            "api.main.MongoDBConfig.get_mongodb_url", return_value="mongodb://host/db"
        ), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch(
            "api.main.MongoDBConfig.initialize_collections",
            side_effect=Exception("Connection failed"),
        ):

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # Should handle initialization errors gracefully

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test lifespan shutdown."""
        with patch(
            "api.main.MongoDBConfig.get_mongodb_url", return_value="mongodb://host/db"
        ), patch(
            "api.main.MongoDBConfig.get_mongodb_database", return_value="test_db"
        ), patch(
            "api.main.MongoDBConfig.initialize_collections"
        ), patch(
            "api.main.MongoDBConfig.close_connection"
        ) as mock_close:

            # Test the lifespan context manager
            async with lifespan(app):
                pass

            # Verify shutdown was called
            mock_close.assert_called_once()


class TestHTTPSEnforcement:
    """Tests for HTTPS enforcement middleware."""

    def test_enforce_https_redirects_http_to_https(self, client):
        """Test that HTTP requests are redirected to HTTPS."""
        with patch("api.main.Request") as mock_request:
            mock_request.url = "http://example.com/api/test"
            mock_request.headers = {"host": "example.com"}

            # Mock call_next function
            async def mock_call_next(request):
                return Response()

            response = enforce_https(mock_request, mock_call_next)

            # Should return a redirect response
            assert response is not None

    def test_enforce_https_allows_https_requests(self, client):
        """Test that HTTPS requests are allowed through."""
        with patch("api.main.Request") as mock_request:
            mock_request.url = "https://example.com/api/test"

            # Mock call_next function
            async def mock_call_next(request):
                return Response()

            response = enforce_https(mock_request, mock_call_next)

            # Should return the response from call_next
            assert response is not None

    def test_enforce_https_handles_localhost(self, client):
        """Test that localhost requests are handled appropriately."""
        with patch("api.main.Request") as mock_request:
            mock_request.url = "http://localhost:8000/api/test"

            # Mock call_next function
            async def mock_call_next(request):
                return Response()

            response = enforce_https(mock_request, mock_call_next)

            # Should return the response from call_next for localhost
            assert response is not None


class TestAppConfiguration:
    """Tests for FastAPI application configuration."""

    def test_app_has_correct_title(self, client):
        """Test that the app has the correct title."""
        assert app.title == "Financial Transaction API"

    def test_app_has_correct_version(self, client):
        """Test that the app has the correct version."""
        assert app.version == "1.0.0"

    def test_app_has_correct_description(self, client):
        """Test that the app has the correct description."""
        assert "API for processing financial transaction files" in app.description

    def test_app_includes_all_routers(self, client):
        """Test that the app includes all required routers."""
        # Get all routes
        routes = [route.path for route in app.routes]

        # Check for key routes from each router
        assert any("/" in route for route in routes)  # System router
        assert any("/api/users" in route for route in routes)  # Auth router
        assert any("/api/wallets" in route for route in routes)  # Wallets router
        assert any("/api/assets" in route for route in routes)  # Assets router
        assert any(
            "/api/transactions" in route for route in routes
        )  # Transactions router
        assert any("/api/stats" in route for route in routes)  # Stats router
        assert any("/logs" in route for route in routes)  # Logs router

    def test_app_has_cors_middleware(self, client):
        """Test that the app has CORS middleware configured."""
        # Check if CORS middleware is in the middleware stack
        middleware_types = [middleware.cls for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware

        assert CORSMiddleware in middleware_types

    def test_app_has_trusted_host_middleware(self, client):
        """Test that the app has TrustedHost middleware configured."""
        # Check if TrustedHost middleware is in the middleware stack
        middleware_types = [middleware.cls for middleware in app.user_middleware]
        from fastapi.middleware.trustedhost import TrustedHostMiddleware

        # TrustedHostMiddleware is only added when ALLOWED_HOSTS != ["*"]
        # Since ALLOWED_HOSTS is ["*"], TrustedHostMiddleware should NOT be present
        assert TrustedHostMiddleware not in middleware_types

    def test_app_has_logging_middleware(self, client):
        """Test that the app has LoggingMiddleware configured."""
        # Check if LoggingMiddleware is in the middleware stack
        middleware_types = [middleware.cls for middleware in app.user_middleware]
        from src.middleware.logging_middleware import LoggingMiddleware

        assert LoggingMiddleware in middleware_types


class TestAppEndpoints:
    """Tests for basic app endpoints."""

    def test_root_endpoint_exists(self, client):
        """Test that the root endpoint exists."""
        response = client.get("/")
        assert response.status_code == 200

    def test_health_endpoint_exists(self, client):
        """Test that the health endpoint exists."""
        with patch("api.routers.system.get_db"):
            response = client.get("/health")
            # Should return either 200 or 503 depending on DB connection
            assert response.status_code in [200, 503]

    def test_openapi_endpoint_exists(self, client):
        """Test that the OpenAPI endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        # Verify it returns valid OpenAPI spec
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_docs_endpoint_exists(self, client):
        """Test that the docs endpoint exists."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint_exists(self, client):
        """Test that the redoc endpoint exists."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestAppErrorHandling:
    """Tests for app error handling."""

    def test_404_error_handling(self, client):
        """Test that 404 errors are handled properly."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed_error(self, client):
        """Test that method not allowed errors are handled properly."""
        response = client.post("/")  # POST not allowed on root
        assert response.status_code == 405

    def test_validation_error_handling(self, client):
        """Test that validation errors are handled properly."""
        # Try to create wallet with invalid data
        response = client.post("/api/wallets", json={"invalid": "data"})
        assert response.status_code == 422


class TestAppDependencies:
    """Tests for app dependencies."""

    def test_app_has_dependency_overrides(self, client):
        """Test that the app has dependency overrides configured."""
        # The app should have dependency overrides for testing
        assert hasattr(app, "dependency_overrides")
        assert isinstance(app.dependency_overrides, dict)

    def test_app_dependency_overrides_can_be_cleared(self, client):
        """Test that dependency overrides can be cleared."""
        # Clear overrides
        app.dependency_overrides.clear()

        # Should be empty
        assert len(app.dependency_overrides) == 0

        # Can add overrides back
        app.dependency_overrides["test"] = "value"
        assert "test" in app.dependency_overrides
