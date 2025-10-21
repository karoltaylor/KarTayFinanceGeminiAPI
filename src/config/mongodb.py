"""MongoDB connection configuration."""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
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
    """Load environment variables once and return them as a dictionary."""
    # Only try to load .env files if not running in Lambda
    # In Lambda, environment variables are already set by AWS
    is_lambda = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

    print(f"[DEBUG] Environment detection - Is Lambda: {is_lambda}")
    print(
        f"[DEBUG] AWS_LAMBDA_FUNCTION_NAME: {os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'Not set')}"
    )

    env_vars = {}

    if not is_lambda:
        env_file = _get_active_env_file()
        print(f"[DEBUG] Loading env file: {env_file}")

        if env_file and Path(env_file).exists():
            try:
                # Parse the .env file manually to return the variables
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if not line or line.startswith("#"):
                            continue

                        # Parse KEY=VALUE format
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()

                            # Remove quotes if present
                            if (value.startswith('"') and value.endswith('"')) or (
                                value.startswith("'") and value.endswith("'")
                            ):
                                value = value[1:-1]

                            env_vars[key] = value

                # Also load into environment using load_dotenv
                load_dotenv(
                    env_file, override=False
                )  # Don't override existing env vars
            except Exception as e:
                print(f"[DEBUG] Error loading env file {env_file}: {e}")
                return {}
        else:
            print(f"[DEBUG] Env file {env_file} does not exist")
            return {}
    else:
        print("[DEBUG] Running in Lambda - skipping .env file loading")

    return env_vars


# Load environment on module import
_env_vars = _load_env_once()


class MongoDBConfig:
    """MongoDB configuration and connection management."""

    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    @classmethod
    def get_client(cls) -> MongoClient:
        """Get MongoDB client (singleton)."""
        if cls._client is None:
            print("[DEBUG] Creating new MongoDB client...")

            # Get URL from environment
            url = os.getenv("MONGODB_URL")

            # Log environment variable status (mask sensitive data)
            print(
                f"[DEBUG] MONGODB_URL environment variable: {'SET' if url else 'NOT SET'}"
            )
            if url:
                # Mask the URL for logging
                if "@" in url:
                    parts = url.split("@")
                    protocol = parts[0].split("://")[0]
                    masked_url = f"{protocol}://***:***@{parts[1]}"
                else:
                    masked_url = url[:20] + "..." if len(url) > 20 else url
                print(f"[DEBUG] MongoDB URL (masked): {masked_url}")
            else:
                print("[ERROR] MONGODB_URL is None or empty!")
                print("[DEBUG] All environment variables starting with MONGODB:")
                for key, value in os.environ.items():
                    if key.startswith("MONGODB"):
                        print(f"[DEBUG]   {key} = {'SET' if value else 'NOT SET'}")

            if not url:
                raise ValueError(
                    "MONGODB_URL environment variable is not set. "
                    "For local development, set it in config.local.env. "
                    "For Lambda, ensure it's set in template.yaml parameters."
                )

            # PyMongo 4.x handles SSL/TLS automatically for mongodb+srv://
            # Just set a reasonable timeout
            print("[DEBUG] Creating MongoClient with timeout=10000ms...")
            try:
                cls._client = MongoClient(url, serverSelectionTimeoutMS=10000)
                print("[DEBUG] MongoClient created successfully")
            except Exception as e:
                print(f"[ERROR] Failed to create MongoClient: {e}")
                raise
        return cls._client

    @classmethod
    def get_database(cls) -> Database:
        """Get MongoDB database (singleton)."""
        if cls._db is None:
            print("[DEBUG] Getting MongoDB database...")

            client = cls.get_client()
            db_name = os.getenv("MONGODB_DATABASE", "financial_tracker")

            print(f"[DEBUG] Database name: {db_name}")

            if not db_name:
                print("[ERROR] MONGODB_DATABASE is None or empty!")
                raise ValueError(
                    "MONGODB_DATABASE environment variable is not set. "
                    "For local development, set it in config.local.env. "
                    "For Lambda, ensure it's set in template.yaml parameters."
                )

            print(f"[DEBUG] Selecting database: {db_name}")
            cls._db = client[db_name]
            print("[DEBUG] Database selected successfully")
        return cls._db

    @classmethod
    def close_connection(cls):
        """Close MongoDB connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None

    @classmethod
    def get_mongodb_url(cls) -> str:
        """Get MongoDB URL from environment."""
        url = os.getenv("MONGODB_URL")
        print(
            f"[DEBUG] get_mongodb_url() called - URL is {'SET' if url else 'NOT SET'}"
        )
        return url

    @classmethod
    def get_mongodb_database(cls) -> str:
        """Get MongoDB database name from environment."""
        db_name = os.getenv("MONGODB_DATABASE", "financial_tracker")
        print(f"[DEBUG] get_mongodb_database() called - Database: {db_name}")
        return db_name

    @classmethod
    def initialize_collections(cls):
        """Initialize MongoDB collections with indexes."""
        print("[DEBUG] Initializing MongoDB collections and indexes...")

        try:
            db = cls.get_database()
            print(f"[DEBUG] Database object obtained: {type(db)}")

            # Test connection by pinging
            print("[DEBUG] Testing connection with ping...")
            db.command("ping")
            print("[DEBUG] Ping successful!")
        except Exception as e:
            print(f"[ERROR] Failed to connect or ping database: {e}")
            raise

        # Create indexes for users
        print("[DEBUG] Creating indexes for users collection...")
        db.users.create_index("email", unique=True)
        db.users.create_index("username", unique=True)
        db.users.create_index([("oauth_provider", 1), ("oauth_id", 1)])
        db.users.create_index("created_at")
        print("[DEBUG] Users indexes created")

        # Create indexes for wallets
        print("[DEBUG] Creating indexes for wallets collection...")
        db.wallets.create_index("user_id")
        db.wallets.create_index([("user_id", 1), ("name", 1)], unique=True)
        db.wallets.create_index("created_at")
        print("[DEBUG] Wallets indexes created")

        # Create indexes for assets
        print("[DEBUG] Creating indexes for assets collection...")
        db.assets.create_index("asset_name")
        db.assets.create_index("asset_type")
        db.assets.create_index("symbol")
        print("[DEBUG] Assets indexes created")

        # Create indexes for asset_current_values
        print("[DEBUG] Creating indexes for asset_current_values collection...")
        db.asset_current_values.create_index("asset_id")
        db.asset_current_values.create_index("date")
        db.asset_current_values.create_index([("asset_id", 1), ("date", -1)])
        print("[DEBUG] Asset_current_values indexes created")

        # Create indexes for transactions
        print("[DEBUG] Creating indexes for transactions collection...")
        db.transactions.create_index("wallet_id")
        db.transactions.create_index("asset_id")
        db.transactions.create_index("date")
        db.transactions.create_index("transaction_type")
        db.transactions.create_index([("wallet_id", 1), ("date", -1)])
        print("[DEBUG] Transactions indexes created")

        # Create indexes for column_mapping_cache
        print("[DEBUG] Creating indexes for column_mapping_cache collection...")
        db.column_mapping_cache.create_index(
            [("user_id", 1), ("cache_key", 1), ("version", 1)],
            unique=True,
            name="user_cache_key_version_idx",
        )
        db.column_mapping_cache.create_index("last_used_at")
        db.column_mapping_cache.create_index("hit_count")
        print("[DEBUG] Column_mapping_cache indexes created")

        print("[DEBUG] All indexes created successfully!")


# Convenience functions
def get_db() -> Database:
    """Get database instance for dependency injection."""
    return MongoDBConfig.get_database()
