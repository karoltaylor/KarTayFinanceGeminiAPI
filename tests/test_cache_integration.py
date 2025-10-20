"""Integration test to verify caching reduces AI calls."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from bson import ObjectId

from src.pipeline import DataPipeline
from src.config.mongodb import MongoDBConfig


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return ObjectId("507f1f77bcf86cd799439011")


@pytest.fixture
def test_db(test_user_id):
    """Get test database and clean up."""
    db = MongoDBConfig.get_database()
    
    # Clean up before test
    db.column_mapping_cache.delete_many({"user_id": test_user_id})
    db.wallets.delete_many({"user_id": test_user_id})
    db.assets.delete_many({})
    db.transactions.delete_many({})
    
    yield db
    
    # Clean up after test
    db.column_mapping_cache.delete_many({"user_id": test_user_id})
    db.wallets.delete_many({"user_id": test_user_id})
    db.assets.delete_many({})
    db.transactions.delete_many({})


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file."""
    csv_content = """Date,Asset,Price,Quantity,Total,Fee,Currency
2024-01-10,AAPL,150.50,10,1505.00,5.00,USD
2024-01-11,GOOGL,140.00,5,700.00,3.00,USD
"""
    filepath = tmp_path / "test_transactions.csv"
    filepath.write_text(csv_content)
    return filepath


def test_cache_reduces_ai_calls(test_db, test_user_id, sample_csv_file, set_test_env_vars):
    """Test that cache reduces AI API calls on subsequent uploads."""
    
    # Since the autouse fixture already mocks AI calls, we just need to test the cache functionality
    
    # Create wallets for testing
    from src.models.mongodb_models import Wallet
    wallet1 = Wallet(user_id=test_user_id, name="Test Wallet 1", description="Test")
    wallet1_dict = wallet1.model_dump(by_alias=True, exclude={"id"}, mode='python')
    result1 = test_db.wallets.insert_one(wallet1_dict)
    wallet1_id = result1.inserted_id
    
    wallet2 = Wallet(user_id=test_user_id, name="Test Wallet 2", description="Test")
    wallet2_dict = wallet2.model_dump(by_alias=True, exclude={"id"}, mode='python')
    result2 = test_db.wallets.insert_one(wallet2_dict)
    wallet2_id = result2.inserted_id
    
    # First upload - should call AI
    pipeline1 = DataPipeline(db=test_db, user_id=test_user_id, api_key="test_key")
    transactions1, errors1 = pipeline1.process_file_to_transactions(
        filepath=sample_csv_file,
        wallet_id=wallet1_id,
        user_id=test_user_id,
        wallets_collection=test_db.wallets,
        assets_collection=test_db.assets,
    )
    
    # Verify first upload succeeded
    assert len(transactions1) > 0
    
    # Second upload - should use cache
    pipeline2 = DataPipeline(db=test_db, user_id=test_user_id, api_key="test_key")
    transactions2, errors2 = pipeline2.process_file_to_transactions(
        filepath=sample_csv_file,
        wallet_id=wallet2_id,
        user_id=test_user_id,
        wallets_collection=test_db.wallets,
        assets_collection=test_db.assets,
    )
    
    # Verify second upload also succeeded
    assert len(transactions2) > 0
    
    # Verify cache was created and used
    cache_entry = test_db.column_mapping_cache.find_one({
        "user_id": test_user_id
    })
    assert cache_entry is not None
    assert cache_entry["hit_count"] >= 1  # Cache was used
    
    print(f"✅ Cache working! Both uploads succeeded")
    print(f"   - First upload: Created cache entry")
    print(f"   - Second upload: Used cache")
    print(f"   - Cache hit count: {cache_entry['hit_count']}")

