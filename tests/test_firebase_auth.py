"""Tests for Firebase authentication."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from src.auth.firebase_auth import verify_firebase_token, get_current_user_from_token
from bson import ObjectId

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


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
    @patch('src.auth.firebase_auth.auth.verify_id_token')
    async def test_valid_token_returns_user_data(self, mock_verify):
        """Test that valid token returns decoded user data."""
        # Mock Firebase token verification
        mock_verify.return_value = {
            "uid": "firebase123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/photo.jpg"
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
    @patch('src.auth.firebase_auth.auth.verify_id_token')
    async def test_invalid_token_raises_error(self, mock_verify):
        """Test that invalid Firebase token raises 401."""
        from firebase_admin import auth
        mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token")
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer invalid_token")
        assert exc_info.value.status_code == 401
        assert "Invalid or expired Firebase token" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('src.auth.firebase_auth.auth.verify_id_token')
    async def test_expired_token_raises_error(self, mock_verify):
        """Test that expired Firebase token raises 401."""
        from firebase_admin import auth
        mock_verify.side_effect = auth.ExpiredIdTokenError("Token expired", cause=Exception("Expired"))
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token("Bearer expired_token")
        assert exc_info.value.status_code == 401
        assert "Firebase token has expired" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch('src.auth.firebase_auth.auth.verify_id_token')
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
    @patch('src.config.mongodb.MongoDBConfig.get_database')
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
            "name": "Test User"
        }

        result = await get_current_user_from_token(firebase_user)
        
        assert result == user_id
        mock_db.users.find_one.assert_called_once_with({"oauth_id": "firebase123"})

    @pytest.mark.asyncio
    @patch('src.config.mongodb.MongoDBConfig.get_database')
    async def test_firebase_user_new_user_auto_registers(self, mock_get_db):
        """Test that new Firebase user is auto-registered."""
        # Mock database
        mock_db = MagicMock()
        new_user_id = ObjectId()
        mock_db.users.find_one.side_effect = [None, None]  # User doesn't exist, username not taken
        mock_db.users.insert_one.return_value = MagicMock(inserted_id=new_user_id)
        mock_get_db.return_value = mock_db

        firebase_user = {
            "uid": "firebase123",
            "email": "newuser@example.com",
            "name": "New User"
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
    @patch('src.config.mongodb.MongoDBConfig.get_database')
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
            "name": "Test User"
        }

        result = await get_current_user_from_token(firebase_user)
        
        assert result == new_user_id
        # Should create user with username "test_1" due to collision
        assert mock_db.users.insert_one.called


class TestFirebaseInitialization:
    """Tests for Firebase initialization."""

    @patch('src.auth.firebase_auth.initialize_app')
    @patch('src.auth.firebase_auth.credentials')
    @patch('os.path.exists')
    @patch('os.getenv')
    def test_initialize_with_service_account(self, mock_getenv, mock_exists, mock_creds, mock_init):
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

    @patch('src.auth.firebase_auth.initialize_app')
    @patch('os.getenv')
    def test_initialize_without_service_account(self, mock_getenv, mock_init):
        """Test Firebase initialization without service account (default credentials)."""
        # Reset global state
        import src.auth.firebase_auth
        src.auth.firebase_auth._firebase_initialized = False
        
        mock_getenv.return_value = None
        
        from src.auth.firebase_auth import _initialize_firebase
        _initialize_firebase()
        
        assert mock_init.called

    @patch('src.auth.firebase_auth.initialize_app')
    def test_initialize_already_initialized_safe(self, mock_init):
        """Test that re-initialization is safe (doesn't crash)."""
        from src.auth.firebase_auth import _initialize_firebase
        
        mock_init.side_effect = ValueError("The default Firebase app already exists")
        
        # Should not raise exception
        _initialize_firebase()

