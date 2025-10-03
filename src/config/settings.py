"""Application settings and configuration."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_API_KEY: Optional[str] = "AIzaSyAtSmdIaDQPtEocsXmrKWTnicxooOrbs1o"
    GENAI_MODEL: str = os.getenv("GENAI_MODEL", "gemini-2.5-flash")

    # Table detection settings
    MAX_ROWS_TO_SCAN: int = 50
    MIN_COLUMNS_FOR_TABLE: int = 2
    HEADER_DETECTION_THRESHOLD: float = 0.7

    # Target columns for the data model
    TARGET_COLUMNS = [
        "wallet_name",
        "asset_name",
        "asset_type",
        "date",
        "asset_item_price",
        "volume",
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
