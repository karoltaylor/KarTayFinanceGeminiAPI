"""Tests for configuration."""

import pytest

from src.config.settings import Settings


class TestSettings:
    """Tests for Settings class."""

    def test_settings_with_env_vars(self, monkeypatch):
        """Test that settings load from environment variables."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test_api_key")
        monkeypatch.setenv("GENAI_MODEL", "test-model")

        # Reload Settings to pick up new env vars
        from importlib import reload
        from src.config import settings

        reload(settings)

        assert settings.Settings.GOOGLE_API_KEY == "test_api_key"
        assert settings.Settings.GENAI_MODEL == "test-model"

    def test_settings_defaults(self, monkeypatch):
        """Test default settings values."""
        monkeypatch.delenv("GENAI_MODEL", raising=False)

        from importlib import reload
        from src.config import settings

        reload(settings)

        assert settings.Settings.GENAI_MODEL == "gemini-1.5-flash"
        assert settings.Settings.MAX_ROWS_TO_SCAN == 50
        assert settings.Settings.MIN_COLUMNS_FOR_TABLE == 2

    def test_validate_missing_api_key(self, monkeypatch):
        """Test validation fails when API key is missing."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        from importlib import reload
        from src.config import settings

        reload(settings)

        with pytest.raises(ValueError, match="GOOGLE_API_KEY must be set"):
            settings.Settings.validate()

    def test_target_columns_defined(self):
        """Test that target columns are properly defined."""
        assert len(Settings.TARGET_COLUMNS) == 7
        assert "asset_name" in Settings.TARGET_COLUMNS
        assert "asset_price" in Settings.TARGET_COLUMNS
        assert "transaction_amount" in Settings.TARGET_COLUMNS
        assert "fee" in Settings.TARGET_COLUMNS
        assert "currency" in Settings.TARGET_COLUMNS
