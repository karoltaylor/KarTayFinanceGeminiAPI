"""MongoDB connection configuration."""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()


class MongoDBConfig:
    """MongoDB configuration and connection management."""

    # MongoDB connection settings from environment
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE")

    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    @classmethod
    def get_client(cls) -> MongoClient:
        """Get MongoDB client (singleton)."""
        if cls._client is None:
            cls._client = MongoClient(cls.MONGODB_URL)
        return cls._client

    @classmethod
    def get_database(cls) -> Database:
        """Get MongoDB database (singleton)."""
        if cls._db is None:
            client = cls.get_client()
            cls._db = client[cls.MONGODB_DATABASE]
        return cls._db

    @classmethod
    def close_connection(cls):
        """Close MongoDB connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None

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
