"""MongoDB connection configuration."""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv


def _load_env_once():
    """Load environment variables once."""
    env_file = os.getenv("ENV_FILE", ".env")
    load_dotenv(env_file, override=True)


# Load environment on module import
_load_env_once()


class MongoDBConfig:
    """MongoDB configuration and connection management."""

    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    @classmethod
    def get_client(cls) -> MongoClient:
        """Get MongoDB client (singleton)."""
        if cls._client is None:
            url = os.getenv("MONGODB_URL")
            cls._client = MongoClient(url)
        return cls._client

    @classmethod
    def get_database(cls) -> Database:
        """Get MongoDB database (singleton)."""
        if cls._db is None:
            client = cls.get_client()
            db_name = os.getenv("MONGODB_DATABASE")
            cls._db = client[db_name]
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
        return os.getenv("MONGODB_URL")
    
    @classmethod
    def get_mongodb_database(cls) -> str:
        """Get MongoDB database name from environment."""
        return os.getenv("MONGODB_DATABASE")

    @classmethod
    def initialize_collections(cls):
        """Initialize MongoDB collections with indexes."""
        db = cls.get_database()

        # Create indexes for users
        db.users.create_index("email", unique=True)
        db.users.create_index("username", unique=True)
        db.users.create_index([("oauth_provider", 1), ("oauth_id", 1)])
        db.users.create_index("created_at")

        # Create indexes for wallets
        db.wallets.create_index("user_id")
        db.wallets.create_index([("user_id", 1), ("name", 1)], unique=True)
        db.wallets.create_index("created_at")

        # Create indexes for assets
        db.assets.create_index("asset_name")
        db.assets.create_index("asset_type")
        db.assets.create_index("symbol")

        # Create indexes for asset_current_values
        db.asset_current_values.create_index("asset_id")
        db.asset_current_values.create_index("date")
        db.asset_current_values.create_index([("asset_id", 1), ("date", -1)])

        # Create indexes for transactions
        db.transactions.create_index("wallet_id")
        db.transactions.create_index("asset_id")
        db.transactions.create_index("date")
        db.transactions.create_index("transaction_type")
        db.transactions.create_index([("wallet_id", 1), ("date", -1)])


# Convenience functions
def get_db() -> Database:
    """Get database instance for dependency injection."""
    return MongoDBConfig.get_database()