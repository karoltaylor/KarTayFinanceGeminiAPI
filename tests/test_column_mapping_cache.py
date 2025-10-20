"""Tests for column mapping cache functionality."""

import pytest
import pandas as pd
from bson import ObjectId
from datetime import datetime

from src.services.column_mapper import ColumnMapper
from src.config.mongodb import MongoDBConfig


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return ObjectId("507f1f77bcf86cd799439011")


@pytest.fixture
def test_db(test_user_id):
    """Get test database and clean up cache collection."""
    db = MongoDBConfig.get_database()
    
    # Clean up before test
    db.column_mapping_cache.delete_many({"user_id": test_user_id})
    
    yield db
    
    # Clean up after test
    db.column_mapping_cache.delete_many({"user_id": test_user_id})


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame({
        "Account": ["Wallet1", "Wallet2"],
        "Stock Name": ["AAPL", "GOOGL"],
        "Trade Date": ["2024-01-10", "2024-01-11"],
        "Price": [150.50, 2800.00],
        "Shares": [10, 5],
        "Total": [1505.00, 14000.00],
        "Curr": ["USD", "USD"],
    })


class TestColumnMappingCache:
    """Test column mapping cache functionality."""

    def test_cache_key_generation(self, test_db, test_user_id, sample_dataframe):
        """Test that cache keys are generated consistently."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        key1 = mapper._generate_cache_key(sample_dataframe, "csv")
        key2 = mapper._generate_cache_key(sample_dataframe, "csv")
        
        # Same DataFrame and file type should produce same key
        assert key1 == key2
        
        # Different file type should produce different key
        key3 = mapper._generate_cache_key(sample_dataframe, "xlsx")
        assert key1 != key3

    def test_cache_key_different_columns(self, test_db, test_user_id):
        """Test that different columns produce different cache keys."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        df1 = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        df2 = pd.DataFrame({"col1": [1, 2], "col3": [3, 4]})
        
        key1 = mapper._generate_cache_key(df1, "csv")
        key2 = mapper._generate_cache_key(df2, "csv")
        
        assert key1 != key2

    def test_cache_storage_and_retrieval(self, test_db, test_user_id, sample_dataframe):
        """Test storing and retrieving mappings from cache."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        
        test_mapping = {
            "asset_name": "Stock Name",
            "date": "Trade Date",
            "asset_price": "Price",
            "volume": "Shares",
        }
        
        # Store mapping
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", test_mapping)
        
        # Retrieve mapping
        retrieved_mapping = mapper._get_cached_mapping(cache_key)
        
        assert retrieved_mapping == test_mapping

    def test_cache_miss(self, test_db, test_user_id):
        """Test cache miss returns None."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        # Non-existent cache key
        retrieved_mapping = mapper._get_cached_mapping("non_existent_key")
        
        assert retrieved_mapping is None

    def test_cache_hit_count_increment(self, test_db, test_user_id, sample_dataframe):
        """Test that cache hit count increments on each retrieval."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        
        test_mapping = {"asset_name": "Stock Name"}
        
        # Store mapping
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", test_mapping)
        
        # Retrieve multiple times
        mapper._get_cached_mapping(cache_key)
        mapper._get_cached_mapping(cache_key)
        mapper._get_cached_mapping(cache_key)
        
        # Check hit count in database
        cache_entry = test_db.column_mapping_cache.find_one({
            "user_id": test_user_id,
            "cache_key": cache_key
        })
        
        assert cache_entry["hit_count"] == 3

    def test_cache_per_user_isolation(self, test_db, sample_dataframe):
        """Test that cache is isolated per user."""
        user1_id = ObjectId()
        user2_id = ObjectId()
        
        mapper1 = ColumnMapper(db=test_db, user_id=user1_id)
        mapper2 = ColumnMapper(db=test_db, user_id=user2_id)
        
        cache_key = mapper1._generate_cache_key(sample_dataframe, "csv")
        
        mapping1 = {"asset_name": "Stock Name"}
        mapping2 = {"asset_name": "Different Column"}
        
        # Store different mappings for each user
        mapper1._store_mapping_cache(cache_key, sample_dataframe, "csv", mapping1)
        mapper2._store_mapping_cache(cache_key, sample_dataframe, "csv", mapping2)
        
        # Retrieve and verify isolation
        retrieved1 = mapper1._get_cached_mapping(cache_key)
        retrieved2 = mapper2._get_cached_mapping(cache_key)
        
        assert retrieved1 == mapping1
        assert retrieved2 == mapping2
        assert retrieved1 != retrieved2
        
        # Clean up
        test_db.column_mapping_cache.delete_many({
            "user_id": {"$in": [user1_id, user2_id]}
        })

    def test_cache_version_isolation(self, test_db, test_user_id, sample_dataframe):
        """Test that different cache versions are isolated."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        mapping_v1 = {"asset_name": "Stock Name"}
        
        # Store with version 1
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", mapping_v1)
        
        # Change version
        mapper.cache_version = 2
        
        # Should not find version 1 mapping
        retrieved = mapper._get_cached_mapping(cache_key)
        assert retrieved is None

    def test_cache_without_db(self, test_user_id, sample_dataframe):
        """Test that cache operations gracefully handle missing database."""
        mapper = ColumnMapper(db=None, user_id=test_user_id)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        
        # Should not raise error, just return None
        retrieved = mapper._get_cached_mapping(cache_key)
        assert retrieved is None
        
        # Should not raise error when storing
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", {})

    def test_cache_without_user_id(self, test_db, sample_dataframe):
        """Test that cache operations gracefully handle missing user_id."""
        mapper = ColumnMapper(db=test_db, user_id=None)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        
        # Should not raise error, just return None
        retrieved = mapper._get_cached_mapping(cache_key)
        assert retrieved is None
        
        # Should not raise error when storing
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", {})

    def test_cache_stores_metadata(self, test_db, test_user_id, sample_dataframe):
        """Test that cache stores all metadata correctly."""
        mapper = ColumnMapper(db=test_db, user_id=test_user_id)
        
        cache_key = mapper._generate_cache_key(sample_dataframe, "csv")
        test_mapping = {"asset_name": "Stock Name"}
        
        mapper._store_mapping_cache(cache_key, sample_dataframe, "csv", test_mapping)
        
        # Retrieve from database directly
        cache_entry = test_db.column_mapping_cache.find_one({
            "user_id": test_user_id,
            "cache_key": cache_key
        })
        
        assert cache_entry is not None
        assert cache_entry["user_id"] == test_user_id
        assert cache_entry["cache_key"] == cache_key
        assert cache_entry["column_names"] == sample_dataframe.columns.tolist()
        assert cache_entry["file_type"] == "csv"
        assert cache_entry["column_count"] == len(sample_dataframe.columns)
        assert cache_entry["mapping"] == test_mapping
        assert cache_entry["version"] == 1
        assert cache_entry["hit_count"] == 0
        assert "created_at" in cache_entry
        assert "last_used_at" in cache_entry

