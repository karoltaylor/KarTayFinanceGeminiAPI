"""Application settings and configuration."""

import os
from dotenv import load_dotenv
from pathlib import Path


def _get_active_env_file():
    """Get the active environment file, checking for .active_env marker file first."""
    # Check for .active_env marker file (created by start_api.py)
    marker_file = Path(".active_env")
    if marker_file.exists():
        try:
            env_file = marker_file.read_text().strip()
            if env_file and Path(env_file).exists():
                return env_file
        except Exception:
            pass

    # Fallback to ENV_FILE environment variable or .env
    return os.getenv("ENV_FILE", ".env")


def _load_env_once():
    """Load environment variables once."""
    # Only try to load .env files if not running in Lambda
    # In Lambda, environment variables are already set by AWS
    if not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        env_file = _get_active_env_file()
        load_dotenv(env_file, override=False)  # Don't override existing env vars


# Load environment on module import
_load_env_once()


class Settings:
    """Application settings loaded from environment variables."""

    # Google API settings
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    GENAI_MODEL: str = os.getenv("GENAI_MODEL")

    # Security settings
    ENFORCE_HTTPS: bool = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "*").split(",")

    # CORS settings
    @classmethod
    def get_cors_origins(cls) -> list:
        """Get CORS origins from environment variable."""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if not cors_origins:
            # Default to local development origins if not specified
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        # Split by comma and strip whitespace
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    # Table detection settings
    MAX_ROWS_TO_SCAN: int = 50
    MIN_COLUMNS_FOR_TABLE: int = 2
    HEADER_DETECTION_THRESHOLD: float = 0.7

    # Target columns for the TransactionRecord model
    TARGET_COLUMNS = [
        "asset_name",
        "date",
        "asset_price",
        "volume",
        "transaction_amount",
        "fee",
        "currency",
        "transaction_type",
    ]

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        if not cls.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY must be set in environment variables. "
                "Copy .env.example to .env and add your API key."
            )
        if not cls.GENAI_MODEL:
            raise ValueError(
                "GENAI_MODEL must be set in environment variables. "
                "Copy .env.example to .env and add your model name."
            )
