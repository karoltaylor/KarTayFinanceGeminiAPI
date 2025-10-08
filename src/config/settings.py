"""Application settings and configuration."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Google API settings
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    GENAI_MODEL: str = os.getenv("GENAI_MODEL")

    # Security settings
    ENFORCE_HTTPS: bool = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "*").split(",")

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
