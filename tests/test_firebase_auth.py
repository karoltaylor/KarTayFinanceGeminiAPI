"""Tests for Firebase authentication."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from src.auth.firebase_auth import (
    verify_firebase_token,
    get_current_user_from_token,
    _initialize_firebase,
)
from bson import ObjectId

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestVerifyFirebaseToken:
    """Tests for verify_firebase_token function."""

    @pytest.mark.asyncio
    async def test_no_authorization_header_raises_error(self):
        """Test that missing authorization header raises 401 error."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_bearer_format_raises_error(self):
        """Test that invalid Bearer format raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("InvalidFormat token123")
        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_token_raises_error(self):
        """Test that empty token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer ")
        assert exc_info.value.status_code == 401
        assert "Authorization token is empty" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_valid_token_returns_user_data(self, mock_verify):
        """Test that valid token returns decoded user data."""
        # Mock Firebase token verification
        mock_verify.return_value = {
            "uid": "firebase123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

        result = await verify_firebase_token("Bearer valid_token_123")

        assert result is not None
        assert result["uid"] == "firebase123"
        assert result["email"] == "test@example.com"
        assert result["email_verified"] is True
        assert result["name"] == "Test User"
        assert result["picture"] == "https://example.com/photo.jpg"
        assert "firebase_token" in result

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_invalid_token_raises_error(self, mock_verify):
        """Test that invalid Firebase token raises 401."""
        from firebase_admin import auth

        mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer invalid_token")
        assert exc_info.value.status_code == 401
        assert "Invalid or expired Firebase token" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_expired_token_raises_error(self, mock_verify):
        """Test that expired Firebase token raises 401."""
        from firebase_admin import auth

        mock_verify.side_effect = auth.ExpiredIdTokenError(
            "Token expired", cause=Exception("Expired")
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer expired_token")
        assert exc_info.value.status_code == 401
        assert "Firebase token has expired" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_revoked_token_raises_error(self, mock_verify):
        """Test that revoked Firebase token raises 401."""
        from firebase_admin import auth

        mock_verify.side_effect = auth.RevokedIdTokenError("Token revoked")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer revoked_token")
        assert exc_info.value.status_code == 401
        assert "Firebase token has been revoked" in exc_info.value.detail


class TestGetCurrentUserFromToken:
    """Tests for get_current_user_from_token function."""

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_firebase_user_existing_user_returns_id(self, mock_get_db):
        """Test that existing Firebase user returns user ID."""
        # Mock database
        mock_db = MagicMock()
        user_id = ObjectId()
        mock_db.users.find_one.return_value = {"_id": user_id}
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "test@example.com",
            "name": "Test User",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == user_id
        mock_db.users.find_one.assert_called_once_with({"oauth_id": "firebase123"})

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_firebase_user_new_user_auto_registers(self, mock_get_db):
        """Test that new Firebase user is auto-registered."""
        # Mock database
        mock_db = MagicMock()
        new_user_id = ObjectId()
        mock_db.users.find_one.side_effect = [
            None,
            None,
        ]  # User doesn't exist, username not taken
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "newuser@example.com",
            "name": "New User",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == new_user_id
        assert mock_db.users.insert_one.called

    # Legacy X-User-ID tests removed - Firebase tokens only now

    @pytest.mark.asyncio
    async def test_no_authentication_raises_error(self):
        """Test that missing Firebase token raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(None)
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_username_collision_handled(self, mock_get_db):
        """Test that username collision is handled with counter."""
        # Mock database
        mock_db = MagicMock()
        new_user_id = ObjectId()
        # First call: user doesn't exist
        # Second/third call: username exists (collision)
        # Fourth call: username_1 doesn't exist (success)
        mock_db.users.find_one.side_effect = [None, {"username": "test"}, None]
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "test@example.com",
            "name": "Test User",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == new_user_id
        # Should create user with username "test_1" due to collision
        assert mock_db.users.insert_one.called


class TestFirebaseInitialization:
    """Tests for Firebase initialization."""

    @patch("src.auth.firebase_auth.initialize_app")
    @patch("src.auth.firebase_auth.credentials")
    @patch("os.path.exists")
    @patch("os.getenv")
    def test_initialize_with_service_account(
        self, mock_getenv, mock_exists, mock_creds, mock_init
    ):
        """Test Firebase initialization with service account JSON."""
        # Reset global state
        import src.auth.firebase_auth

        src.auth.firebase_auth._firebase_initialized = False

        mock_getenv.return_value = "/path/to/service-account.json"
        mock_exists.return_value = True
        mock_creds.Certificate.return_value = Mock()

        from src.auth.firebase_auth import _initialize_firebase

        _initialize_firebase()

        assert mock_init.called

    @patch("src.auth.firebase_auth.initialize_app")
    @patch("os.getenv")
    def test_initialize_without_service_account(self, mock_getenv, mock_init):
        """Test Firebase initialization without service account (default credentials)."""
        # Reset global state
        import src.auth.firebase_auth

        src.auth.firebase_auth._firebase_initialized = False

        mock_getenv.return_value = None

        from src.auth.firebase_auth import _initialize_firebase

        _initialize_firebase()

        assert mock_init.called

    @patch("src.auth.firebase_auth.initialize_app")
    def test_initialize_already_initialized_safe(self, mock_init):
        """Test that re-initialization is safe (doesn't crash)."""
        from src.auth.firebase_auth import _initialize_firebase

        mock_init.side_effect = ValueError("The default Firebase app already exists")

        # Should not raise exception
        _initialize_firebase()

    @patch("src.auth.firebase_auth.initialize_app")
    @patch("src.auth.firebase_auth.credentials")
    @patch("os.path.exists")
    @patch("os.getenv")
    def test_initialize_with_invalid_service_account_path(
        self, mock_getenv, mock_exists, mock_creds, mock_init
    ):
        """Test Firebase initialization with invalid service account path."""
        # Reset global state
        import src.auth.firebase_auth

        src.auth.firebase_auth._firebase_initialized = False

        mock_getenv.return_value = "/invalid/path/service-account.json"
        mock_exists.return_value = False  # File doesn't exist

        from src.auth.firebase_auth import _initialize_firebase

        _initialize_firebase()

        # Should fall back to default credentials
        assert mock_init.called

    @patch("src.auth.firebase_auth.initialize_app")
    @patch("src.auth.firebase_auth.credentials")
    @patch("os.path.exists")
    @patch("os.getenv")
    def test_initialize_with_service_account_error(
        self, mock_getenv, mock_exists, mock_creds, mock_init
    ):
        """Test Firebase initialization with service account error."""
        # Reset global state
        import src.auth.firebase_auth

        src.auth.firebase_auth._firebase_initialized = False

        mock_getenv.return_value = "/path/to/service-account.json"
        mock_exists.return_value = True
        mock_creds.Certificate.side_effect = Exception("Invalid certificate")

        from src.auth.firebase_auth import _initialize_firebase

        _initialize_firebase()

        # Should not initialize Firebase when service account fails
        assert not mock_init.called

    @patch("src.auth.firebase_auth.initialize_app")
    def test_initialize_with_general_error(self, mock_init):
        """Test Firebase initialization with general error."""
        from src.auth.firebase_auth import _initialize_firebase

        mock_init.side_effect = Exception("General Firebase error")

        # Should not raise exception
        _initialize_firebase()

    @patch("src.auth.firebase_auth.initialize_app")
    def test_initialize_multiple_calls_safe(self, mock_init):
        """Test that multiple initialization calls are safe."""
        from src.auth.firebase_auth import _initialize_firebase

        # First call
        _initialize_firebase()

        # Second call should not cause issues
        _initialize_firebase()

        # Should only initialize once due to global flag
        assert mock_init.call_count <= 1


class TestFirebaseTokenEdgeCases:
    """Tests for Firebase token edge cases."""

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_with_minimal_data(self, mock_verify):
        """Test token with minimal required data."""
        mock_verify.return_value = {"uid": "firebase123", "email": "test@example.com"}

        result = await verify_firebase_token("Bearer minimal_token")

        assert result is not None
        assert result["uid"] == "firebase123"
        assert result["email"] == "test@example.com"
        assert "firebase_token" in result

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_with_extra_fields(self, mock_verify):
        """Test token with extra fields."""
        mock_verify.return_value = {
            "uid": "firebase123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
            "custom_claim": "custom_value",
            "phone_number": "+1234567890",
        }

        result = await verify_firebase_token("Bearer extra_fields_token")

        assert result is not None
        assert result["uid"] == "firebase123"
        assert result["email"] == "test@example.com"
        # Extra fields are not preserved in the result
        assert "custom_claim" not in result
        assert "phone_number" not in result
        # But the original token is preserved
        assert "custom_claim" in result["firebase_token"]
        assert "phone_number" in result["firebase_token"]

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_with_unverified_email(self, mock_verify):
        """Test token with unverified email."""
        mock_verify.return_value = {
            "uid": "firebase123",
            "email": "test@example.com",
            "email_verified": False,
        }

        result = await verify_firebase_token("Bearer unverified_token")

        assert result is not None
        assert result["email_verified"] is False

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_without_email(self, mock_verify):
        """Test token without email field."""
        mock_verify.return_value = {"uid": "firebase123"}

        result = await verify_firebase_token("Bearer no_email_token")

        assert result is not None
        assert result["uid"] == "firebase123"
        # Email field is always included, even if None
        assert "email" in result
        assert result["email"] is None


class TestGetCurrentUserEdgeCases:
    """Tests for get_current_user_from_token edge cases."""

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_user_with_complex_email(self, mock_get_db):
        """Test user with complex email address."""
        mock_db = MagicMock()
        user_id = ObjectId()
        mock_db.users.find_one.return_value = {"_id": user_id}
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "user+tag@example.co.uk",
            "name": "Test User",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == user_id
        mock_db.users.find_one.assert_called_once_with({"oauth_id": "firebase123"})

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_user_with_special_characters_in_name(self, mock_get_db):
        """Test user with special characters in name."""
        mock_db = MagicMock()
        new_user_id = ObjectId()
        mock_db.users.find_one.side_effect = [None, None]  # User doesn't exist
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "test@example.com",
            "name": "José María O'Connor-Smith",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == new_user_id
        assert mock_db.users.insert_one.called

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_user_without_name(self, mock_get_db):
        """Test user without name field."""
        mock_db = MagicMock()
        new_user_id = ObjectId()
        mock_db.users.find_one.side_effect = [None, None]  # User doesn't exist
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {"uid": "firebase123", "email": "test@example.com"}

        result = await get_current_user_from_token(firebase_user)

        assert result == new_user_id
        assert mock_db.users.insert_one.called

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_user_with_long_username(self, mock_get_db):
        """Test user with very long username."""
        mock_db = MagicMock()
        new_user_id = ObjectId()
        mock_db.users.find_one.side_effect = [None, None]  # User doesn't exist
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "verylongusername@example.com",
            "name": "Very Long Username That Should Be Truncated",
        }

        result = await get_current_user_from_token(firebase_user)

        assert result == new_user_id
        assert mock_db.users.insert_one.called

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_database_error_handling(self, mock_get_db):
        """Test database error handling."""
        mock_db = MagicMock()
        mock_db.users.find_one.side_effect = Exception("Database connection failed")
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "test@example.com",
            "name": "Test User",
        }

        with pytest.raises(Exception):
            await get_current_user_from_token(firebase_user)

    @pytest.mark.asyncio
    @patch("src.config.mongodb.MongoDBConfig.get_database")
    async def test_insert_error_handling(self, mock_get_db):
        """Test insert error handling."""
        mock_db = MagicMock()
        mock_db.users.find_one.side_effect = [None, None]  # User doesn't exist
        mock_db.users.insert_one.side_effect = Exception("Insert failed")
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "test@example.com",
            "name": "Test User",
        }

        with pytest.raises(Exception):
            await get_current_user_from_token(firebase_user)


class TestFirebaseTokenValidation:
    """Tests for Firebase token validation."""

    @pytest.mark.asyncio
    async def test_token_with_whitespace(self):
        """Test token with leading/trailing whitespace."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer   token_with_spaces   ")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_newlines(self):
        """Test token with newlines."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer token\nwith\nnewlines")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_with_tabs(self):
        """Test token with tabs."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer token\twith\ttabs")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_verification_timeout(self, mock_verify):
        """Test token verification timeout."""
        import asyncio

        mock_verify.side_effect = asyncio.TimeoutError("Request timeout")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer timeout_token")
        assert exc_info.value.status_code == 401
        assert "timeout" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("src.auth.firebase_auth.auth.verify_id_token")
    async def test_token_verification_network_error(self, mock_verify):
        """Test token verification network error."""
        mock_verify.side_effect = ConnectionError("Network error")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer network_error_token")
        assert exc_info.value.status_code == 401
