"""Pytest configuration and shared fixtures."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import uuid
import os
from unittest.mock import MagicMock, patch
import jwt
import time


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def unique_test_email():
    """Generate a unique test email address."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test_{unique_id}@example.com"


@pytest.fixture
def unique_test_username():
    """Generate a unique test username."""
    unique_id = str(uuid.uuid4())[:8]
    return f"testuser_{unique_id}"


@pytest.fixture
def mock_firebase_token():
    """Create a mock Firebase ID token for testing."""
    now = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    email = f"test_{unique_id}@example.com"

    payload = {
        "iss": "https://securetoken.google.com/test-project",
        "aud": "test-project",
        "auth_time": now - 3600,
        "user_id": f"test-user-{unique_id}",
        "sub": f"test-user-{unique_id}",
        "iat": now - 3600,
        "exp": now + 3600,
        "email": email,
        "email_verified": True,
        "firebase": {"identities": {"email": [email]}, "sign_in_provider": "password"},
    }

    # Create a mock token (we'll mock the verification in tests)
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def auth_headers(mock_firebase_token):
    """Get authentication headers with Firebase token."""
    return {"Authorization": f"Bearer {mock_firebase_token}"}


@pytest.fixture
def auth_headers_user2():
    """Get authentication headers for second test user."""
    # Create a different mock token for user 2
    now = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    email = f"test2_{unique_id}@example.com"

    payload = {
        "iss": "https://securetoken.google.com/test-project",
        "aud": "test-project",
        "auth_time": now - 3600,
        "user_id": f"test-user-{unique_id}",
        "sub": f"test-user-{unique_id}",
        "iat": now - 3600,
        "exp": now + 3600,
        "email": email,
        "email_verified": True,
        "firebase": {"identities": {"email": [email]}, "sign_in_provider": "password"},
    }

    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_csv_content():
    """Sample CSV content with header not at top."""
    return """Financial Data Export
Report Generated: 2024-01-15

Account,Stock Name,Type,Trade Date,Price,Shares,Curr,Transaction Type
MyWallet,AAPL,Stock,2024-01-10,150.50,10,USD,buy
MyWallet,BTC,Crypto,2024-01-11,45000.00,0.5,USD,sell
Savings,MSFT,Stock,2024-01-12,380.25,5,USD,buy
"""


@pytest.fixture
def sample_csv_file(temp_dir, sample_csv_content):
    """Create a sample CSV file."""
    filepath = temp_dir / "test_data.csv"
    filepath.write_text(sample_csv_content)
    return filepath


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "asset_name": ["AAPL", "BTC"],
            "date": ["2024-01-10", "2024-01-11"],
            "asset_price": [150.50, 45000.00],
            "volume": [10, 0.5],
            "transaction_amount": [1505.00, 22500.00],
            "fee": [5.0, 10.0],
            "currency": ["USD", "USD"],
            "transaction_type": ["buy", "sell"],
        }
    )


@pytest.fixture
def valid_financial_record_data():
    """Valid data for creating TransactionRecord."""
    return {
        "asset_name": "AAPL",
        "date": "2024-01-10",
        "asset_price": 150.50,
        "volume": 10,
        "transaction_amount": 1505.00,
        "fee": 5.0,
        "currency": "USD",
        "transaction_type": "buy",
    }


@pytest.fixture
def mock_genai_response():
    """Mock response from Google GenAI."""
    return {
        "wallet_name": "Account",
        "asset_name": "Stock Name",
        "asset_type": "Type",
        "date": "Trade Date",
        "asset_item_price": "Price",
        "volume": "Shares",
        "currency": "Curr",
    }


@pytest.fixture
def set_test_env_vars(monkeypatch):
    """Set test environment variables."""
    # Delete existing env vars first to ensure clean test state
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GENAI_MODEL", raising=False)
    # Set test values
    monkeypatch.setenv("GOOGLE_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("GENAI_MODEL", "gemini-1.5-flash")


@pytest.fixture(autouse=True)
def mock_ai_calls_if_needed(request, monkeypatch):
    """
    Automatically mock AI calls unless USE_REAL_AI=true is set AND test is marked with gemini_api.

    This speeds up tests significantly by avoiding network calls to Google Gemini API.
    To test with real AI, set environment variable: USE_REAL_AI=true
    Only tests marked with @pytest.mark.gemini_api will use real AI when USE_REAL_AI=true.
    """
    # Check if test is marked with gemini_api
    has_gemini_marker = request.node.get_closest_marker("gemini_api") is not None
    use_real_ai = os.getenv("USE_REAL_AI", "false").lower() == "true"

    # Only use real AI if both marker exists AND USE_REAL_AI=true
    should_mock = not (has_gemini_marker and use_real_ai)

    if should_mock:
        # Mock the ColumnMapper.map_columns method
        def mock_map_columns(
            self, source_df, target_columns, sample_rows=5, file_type="csv"
        ):
            """
            Mock column mapping with intelligent fallback logic.

            Tries to match columns by name similarity and common patterns.
            """
            if source_df.empty:
                raise ValueError("Cannot map columns from empty DataFrame")

            source_columns = [str(col).lower() for col in source_df.columns]
            mapping = {}

            # Common column name patterns for different target columns
            column_patterns = {
                "wallet_name": ["account", "wallet", "portfel", "konto"],
                "asset_name": [
                    "stock",
                    "asset",
                    "symbol",
                    "ticker",
                    "nazwa",
                    "instrument",
                    "papier",
                ],
                "asset_type": ["type", "asset_type", "typ", "rodzaj"],
                "date": ["date", "data", "trade_date", "transaction_date", "dt"],
                "transaction_type": [
                    "transaction_type",
                    "typ_transakcji",
                    "typ",
                    "type",
                ],
                "asset_item_price": [
                    "price",
                    "cena",
                    "kurs",
                    "item_price",
                    "unit_price",
                    "asset_price",
                ],
                "volume": ["volume", "quantity", "shares", "amount", "ilosc", "liczba"],
                "transaction_amount": [
                    "total",
                    "amount",
                    "transaction_amount",
                    "wartosc",
                    "kwota",
                ],
                "fee": ["fee", "commission", "prowizja", "oplata"],
                "currency": ["currency", "curr", "waluta", "ccy"],
                "notes": ["notes", "description", "uwagi", "opis", "comment"],
            }

            # Try to match each target column
            for target_col in target_columns:
                target_lower = target_col.lower()
                patterns = column_patterns.get(target_col, [target_lower])

                # Try exact match first
                for i, src_col in enumerate(source_columns):
                    if src_col == target_lower:
                        mapping[target_col] = source_df.columns[i]
                        break

                # Try partial match for common patterns
                if target_col not in mapping:
                    for i, src_col in enumerate(source_columns):
                        if target_lower in src_col or src_col in target_lower:
                            mapping[target_col] = source_df.columns[i]
                            break

                # If no exact match, try pattern matching
                if target_col not in mapping:
                    for pattern in patterns:
                        for i, src_col in enumerate(source_columns):
                            if pattern in src_col or src_col in pattern:
                                mapping[target_col] = source_df.columns[i]
                                break
                        if target_col in mapping:
                            break

            return mapping

        # Patch the ColumnMapper class
        from src.services.column_mapper import ColumnMapper

        monkeypatch.setattr(ColumnMapper, "map_columns", mock_map_columns)

        # Also mock the __init__ to avoid requiring API key
        def mock_init(self, api_key=None, model_name=None, db=None, user_id=None):
            self.api_key = api_key or "mock_key"
            self.model_name = model_name or "mock_model"
            self.db = db
            self.user_id = user_id
            self.cache_version = 1
            self.model = MagicMock()

        monkeypatch.setattr(ColumnMapper, "__init__", mock_init)


@pytest.fixture(autouse=True, scope="function")
def mock_firebase_auth():
    """
    Automatically mock Firebase authentication for all tests.

    This fixture runs for every test and mocks Firebase token verification
    to allow tests to run without requiring real Firebase setup.
    """
    with patch("src.auth.firebase_auth.auth.verify_id_token") as mock_verify:
        # Mock Firebase token verification
        def mock_verify_token(token):
            """Mock Firebase token verification that returns test user data."""
            # Reject clearly invalid tokens (for negative testing)
            if token in ["invalid-token", "expired-token", "", None]:
                from firebase_admin import auth as firebase_auth_module

                raise firebase_auth_module.InvalidIdTokenError("Invalid token")

            # Parse the mock token to extract user info
            try:
                payload = jwt.decode(
                    token,
                    "test-secret",
                    algorithms=["HS256"],
                    options={"verify_signature": False},
                )
                # Use unique email from token or generate one
                email = payload.get("email")
                if not email or email == "test@example.com":
                    # Generate unique email for fallback
                    unique_id = str(uuid.uuid4())[:8]
                    email = f"test_{unique_id}@example.com"

                return {
                    "uid": payload.get("user_id", f"test-user-{unique_id}"),
                    "email": email,
                    "email_verified": payload.get("email_verified", True),
                    "name": payload.get("name", "Test User"),
                    "picture": payload.get("picture"),
                }
            except jwt.DecodeError:
                # Token is not a valid JWT - treat as invalid
                from firebase_admin import auth as firebase_auth_module

                raise firebase_auth_module.InvalidIdTokenError("Invalid token format")
            except Exception:
                # Other errors - treat as invalid
                from firebase_admin import auth as firebase_auth_module

                raise firebase_auth_module.InvalidIdTokenError(
                    "Token verification failed"
                )

        mock_verify.side_effect = mock_verify_token
        yield mock_verify


@pytest.fixture(autouse=True)
def override_auth_dependencies():
    """
    Override authentication dependencies for testing.

    This ensures all authenticated endpoints return the test user ID directly,
    bypassing Firebase authentication and user auto-creation logic.
    This fixes 404 errors caused by tests creating wallets for one user ID
    but authentication returning a different auto-created user ID.
    """
    from api.main import app
    from api.dependencies import get_current_user
    from src.auth.firebase_auth import get_current_user_from_token
    from bson import ObjectId

    # Fixed test user ID that matches test_db fixtures
    test_user_id = ObjectId("507f1f77bcf86cd799439011")

    async def mock_get_current_user():
        """Return test user ID for all authenticated requests."""
        return test_user_id

    # Override both auth dependency functions
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_from_token] = mock_get_current_user

    yield

    # Clean up overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def override_auth_user2():
    """
    Override auth to return second test user.

    Use this fixture in tests that need to test multi-user scenarios.
    Call this fixture and use its return value to temporarily switch to user2.

    Example usage:
        def test_two_users(client, auth_headers, auth_headers_user2, override_auth_user2):
            # First request uses user1 (default)
            response1 = client.get("/api/wallets", headers=auth_headers)

            # Switch to user2 for next request
            from api.main import app
            from api.dependencies import get_current_user
            from src.auth.firebase_auth import get_current_user_from_token
            app.dependency_overrides[get_current_user] = override_auth_user2
            app.dependency_overrides[get_current_user_from_token] = override_auth_user2

            # Now this uses user2
            response2 = client.get("/api/wallets", headers=auth_headers_user2)
    """
    from bson import ObjectId

    test_user_id_2 = ObjectId("507f1f77bcf86cd799439012")

    async def mock_get_current_user_2():
        """Return second test user ID."""
        return test_user_id_2

    return mock_get_current_user_2
