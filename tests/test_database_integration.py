"""Comprehensive integration tests for real database operations."""

import pytest
from datetime import datetime, UTC
from bson import ObjectId
from fastapi.testclient import TestClient
import tempfile
import csv
import concurrent.futures
import time

from api.main import app
from src.config.mongodb import MongoDBConfig
from src.models.mongodb_models import Transaction, Wallet, Asset, User


@pytest.fixture(scope="function")
def test_db(unique_test_email, unique_test_username):
    """Get test database instance and clean up test data."""
    db = MongoDBConfig.get_database()
    
    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")
    test_user_id_2 = ObjectId("507f1f77bcf86cd799439012")
    
    # Clean up test data before each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    db.transaction_errors.delete_many({})
    
    # Create test users with unique emails
    test_user_1 = {
        "_id": test_user_id,
        "email": unique_test_email,
        "username": unique_test_username,
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    test_user_2 = {
        "_id": test_user_id_2,
        "email": f"test2_{unique_test_email.split('@')[0].split('_')[1]}@example.com",
        "username": f"{unique_test_username}_2",
        "full_name": "Test User 2",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    
    db.users.update_one(
        {"_id": test_user_id},
        {"$set": test_user_1},
        upsert=True
    )
    db.users.update_one(
        {"_id": test_user_id_2},
        {"$set": test_user_2},
        upsert=True
    )
    
    yield db
    
    # Clean up test data after each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)},
        {"user_id": test_user_id_2},
        {"user_id": str(test_user_id_2)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": {"$in": [test_user_id, test_user_id_2]}})
    db.transaction_errors.delete_many({})


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers for test user."""
    return {"X-User-ID": "507f1f77bcf86cd799439011"}


@pytest.fixture
def auth_headers_user2():
    """Get authentication headers for second test user."""
    return {"X-User-ID": "507f1f77bcf86cd799439012"}


class TestRealDatabaseOperations:
    """Tests for real database operations and data integrity."""

    def test_transaction_creation_and_retrieval(self, client, test_db, auth_headers):
        """Test creating transactions and retrieving them from database."""
        # Create wallet first
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Database Test Wallet", "description": "For testing database operations"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]
        
        # Create transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Apple Inc.', '2024-01-15', '175.50', '10', '1755.00', '2.50', 'USD'])
        writer.writerow(['Microsoft Corp.', '2024-01-16', '420.25', '5', '2101.25', '2.50', 'USD'])
        temp_file.close()
        
        try:
            # Upload transactions
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Database Test Wallet",
                        "asset_type": "stock"
                    }
                )
            assert upload_response.status_code == 200
            
            # Verify transactions were created in database
            transactions_in_db = list(test_db.transactions.find({"wallet_id": ObjectId(wallet_id)}))
            assert len(transactions_in_db) == 2
            
            # Verify transaction data integrity
            for tx in transactions_in_db:
                assert tx["wallet_id"] == ObjectId(wallet_id)
                assert "asset_id" in tx
                assert tx["transaction_type"] == "buy"
                assert tx["volume"] > 0
                assert tx["item_price"] > 0
                assert tx["transaction_amount"] > 0
                assert tx["currency"] == "USD"
                assert tx["fee"] >= 0
                assert isinstance(tx["date"], datetime)
                assert isinstance(tx["created_at"], datetime)
                assert isinstance(tx["updated_at"], datetime)
            
            # Verify assets were created
            assets_in_db = list(test_db.assets.find({}))
            assert len(assets_in_db) >= 2
            
            # Verify asset data integrity
            for asset in assets_in_db:
                assert asset["asset_name"] in ["Apple Inc.", "Microsoft Corp."]
                assert asset["asset_type"] == "stock"
                assert isinstance(asset["created_at"], datetime)
                assert isinstance(asset["updated_at"], datetime)
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_transaction_consistency(self, client, test_db, auth_headers):
        """Test that database transactions maintain consistency."""
        # Create wallet
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Consistency Test Wallet", "description": "For testing consistency"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]
        
        # Create transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Tesla Inc.', '2024-01-17', '245.80', '8', '1966.40', '3.00', 'USD'])
        temp_file.close()
        
        try:
            # Upload transactions
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Consistency Test Wallet",
                        "asset_type": "stock"
                    }
                )
            assert upload_response.status_code == 200
            
            # Get transaction from API
            api_response = client.get("/api/transactions", headers=auth_headers)
            assert api_response.status_code == 200
            api_transactions = api_response.json()["transactions"]
            assert len(api_transactions) == 1
            
            api_tx = api_transactions[0]
            
            # Get transaction from database
            db_transactions = list(test_db.transactions.find({"wallet_id": ObjectId(wallet_id)}))
            assert len(db_transactions) == 1
            
            db_tx = db_transactions[0]
            
            # Verify consistency between API and database
            assert str(db_tx["_id"]) == api_tx["_id"]
            assert str(db_tx["wallet_id"]) == api_tx["wallet_id"]
            assert str(db_tx["asset_id"]) == api_tx["asset_id"]
            assert db_tx["transaction_type"] == api_tx["transaction_type"]
            assert db_tx["volume"] == api_tx["volume"]
            assert db_tx["item_price"] == api_tx["item_price"]
            assert db_tx["transaction_amount"] == api_tx["transaction_amount"]
            assert db_tx["currency"] == api_tx["currency"]
            assert db_tx["fee"] == api_tx["fee"]
            
            # Verify date consistency (within 1 second tolerance)
            api_date = datetime.fromisoformat(api_tx["date"].replace('Z', '+00:00'))
            db_date = db_tx["date"]
            assert abs((api_date - db_date).total_seconds()) < 1
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_foreign_key_integrity(self, client, test_db, auth_headers):
        """Test that foreign key relationships are maintained."""
        # Create wallet
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "FK Test Wallet", "description": "For testing foreign keys"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]
        
        # Create transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Google Inc.', '2024-01-18', '150.00', '20', '3000.00', '5.00', 'USD'])
        temp_file.close()
        
        try:
            # Upload transactions
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "FK Test Wallet",
                        "asset_type": "stock"
                    }
                )
            assert upload_response.status_code == 200
            
            # Verify foreign key relationships
            transactions = list(test_db.transactions.find({"wallet_id": ObjectId(wallet_id)}))
            assert len(transactions) == 1
            
            transaction = transactions[0]
            asset_id = transaction["asset_id"]
            
            # Verify wallet exists
            wallet = test_db.wallets.find_one({"_id": ObjectId(wallet_id)})
            assert wallet is not None
            assert wallet["name"] == "FK Test Wallet"
            
            # Verify asset exists
            asset = test_db.assets.find_one({"_id": asset_id})
            assert asset is not None
            assert asset["asset_name"] == "Google Inc."
            
            # Verify user exists
            user = test_db.users.find_one({"_id": wallet["user_id"]})
            assert user is not None
            assert user["email"] == unique_test_email
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_performance_large_dataset(self, client, test_db, auth_headers):
        """Test database performance with larger datasets."""
        # Create wallet
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Performance Test Wallet", "description": "For testing performance"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        
        # Create large transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Generate 100 transactions
        assets = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC']
        for i in range(100):
            asset = assets[i % len(assets)]
            price = 100 + (i % 500)
            volume = 1 + (i % 50)
            total = price * volume
            fee = 2.50 + (i % 10)
            date = f"2024-01-{(i % 28) + 1:02d}"
            
            writer.writerow([asset, date, price, volume, total, fee, 'USD'])
        
        temp_file.close()
        
        try:
            # Measure upload time
            start_time = time.time()
            
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("large_transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Performance Test Wallet",
                        "asset_type": "stock"
                    }
                )
            
            upload_time = time.time() - start_time
            
            assert upload_response.status_code == 200
            
            # Verify all transactions were created
            transactions_count = test_db.transactions.count_documents({})
            assert transactions_count == 100
            
            # Verify assets were created
            assets_count = test_db.assets.count_documents({})
            assert assets_count == len(assets)  # Should have unique assets
            
            # Measure query time
            start_time = time.time()
            
            api_response = client.get("/api/transactions", headers=auth_headers)
            
            query_time = time.time() - start_time
            
            assert api_response.status_code == 200
            assert api_response.json()["count"] == 100
            
            # Performance assertions (adjust thresholds as needed)
            assert upload_time < 30  # Should complete within 30 seconds
            assert query_time < 5    # Should query within 5 seconds
            
            print(f"Performance metrics:")
            print(f"  Upload time: {upload_time:.2f} seconds")
            print(f"  Query time: {query_time:.2f} seconds")
            print(f"  Transactions created: {transactions_count}")
            print(f"  Assets created: {assets_count}")
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_concurrent_operations(self, client, test_db, auth_headers):
        """Test database consistency under concurrent operations."""
        def create_wallet_and_transactions(wallet_name, asset_name):
            # Create wallet
            wallet_response = client.post(
                "/api/wallets",
                json={"name": wallet_name, "description": "Concurrent test"},
                headers=auth_headers
            )
            if wallet_response.status_code != 200:
                return None
            
            wallet_id = wallet_response.json()["data"]["_id"]
            
            # Create transaction file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
            writer = csv.writer(temp_file)
            writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
            writer.writerow([asset_name, '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
            temp_file.close()
            
            try:
                # Upload transactions
                with open(temp_file.name, 'rb') as f:
                    upload_response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": ("transactions.csv", f, "text/csv")},
                        data={
                            "wallet_name": wallet_name,
                            "asset_type": "stock"
                        }
                    )
                
                return upload_response.status_code == 200
            finally:
                import os
                os.unlink(temp_file.name)
        
        # Execute 10 concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_wallet_and_transactions, f"Concurrent_Wallet_{i}", f"Asset_{i}")
                for i in range(10)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All operations should succeed
        assert all(results)
        
        # Verify all wallets and transactions were created
        wallets_count = test_db.wallets.count_documents({})
        transactions_count = test_db.transactions.count_documents({})
        assets_count = test_db.assets.count_documents({})
        
        assert wallets_count == 10
        assert transactions_count == 10
        assert assets_count == 10  # Each asset should be unique
        
        # Verify no duplicate wallet names
        wallet_names = [w["name"] for w in test_db.wallets.find({})]
        assert len(set(wallet_names)) == 10

    def test_database_error_recovery(self, client, test_db, auth_headers):
        """Test database error recovery and transaction rollback."""
        # Create wallet
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Error Recovery Wallet", "description": "For testing error recovery"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        
        # Create transaction file with some invalid data
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Valid Asset', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        writer.writerow(['Invalid Asset', 'invalid-date', '-50.00', '-5', 'invalid', 'fee', 'INVALID'])
        writer.writerow(['Another Valid Asset', '2024-01-16', '200.00', '5', '1000.00', '2.50', 'USD'])
        temp_file.close()
        
        try:
            # Upload transactions (should handle errors gracefully)
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("mixed_transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Error Recovery Wallet",
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed with some transactions and some errors
            assert upload_response.status_code in [200, 422]
            
            if upload_response.status_code == 200:
                data = upload_response.json()
                summary = data["data"]["summary"]
                
                # Should have some successful transactions
                assert summary["total_transactions"] >= 2
                
                # Should have some failed transactions
                assert summary["failed_transactions"] >= 1
                
                # Verify valid transactions were created
                transactions_count = test_db.transactions.count_documents({})
                assert transactions_count >= 2
                
                # Verify error records were created
                errors_count = test_db.transaction_errors.count_documents({})
                assert errors_count >= 1
                
                # Verify error data integrity
                errors = list(test_db.transaction_errors.find({}))
                for error in errors:
                    assert error["user_id"] == ObjectId("507f1f77bcf86cd799439011")
                    assert error["wallet_name"] == "Error Recovery Wallet"
                    assert error["filename"] == "mixed_transactions.csv"
                    assert error["row_index"] >= 0
                    assert "error_message" in error
                    assert "error_type" in error
                    assert error["resolved"] is False
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_data_persistence(self, client, test_db, auth_headers):
        """Test that data persists correctly across operations."""
        # Create wallet
        wallet_response = client.post(
            "/api/wallets",
            json={"name": "Persistence Test Wallet", "description": "For testing persistence"},
            headers=auth_headers
        )
        assert wallet_response.status_code == 200
        wallet_id = wallet_response.json()["data"]["_id"]
        
        # Create transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Persistent Asset', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        temp_file.close()
        
        try:
            # Upload transactions
            with open(temp_file.name, 'rb') as f:
                upload_response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("transactions.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Persistence Test Wallet",
                        "asset_type": "stock"
                    }
                )
            assert upload_response.status_code == 200
            
            # Verify data exists
            transactions_count = test_db.transactions.count_documents({})
            assert transactions_count == 1
            
            # Simulate application restart by creating new client
            new_client = TestClient(app)
            
            # Verify data still exists after "restart"
            api_response = new_client.get("/api/transactions", headers=auth_headers)
            assert api_response.status_code == 200
            assert api_response.json()["count"] == 1
            
            # Verify wallet still exists
            wallets_response = new_client.get("/api/wallets", headers=auth_headers)
            assert wallets_response.status_code == 200
            assert wallets_response.json()["count"] == 1
            
            # Verify data integrity after "restart"
            transaction = api_response.json()["transactions"][0]
            assert transaction["wallet_id"] == wallet_id
            assert transaction["asset_name"] == "Persistent Asset"
            assert transaction["transaction_type"] == "buy"
            assert transaction["volume"] == 10.0
            assert transaction["item_price"] == 100.0
            assert transaction["transaction_amount"] == 1000.0
            assert transaction["currency"] == "USD"
            assert transaction["fee"] == 2.5
            
        finally:
            import os
            os.unlink(temp_file.name)

    def test_database_index_performance(self, client, test_db, auth_headers):
        """Test database index performance."""
        # Create multiple wallets and transactions
        wallet_ids = []
        for i in range(5):
            wallet_response = client.post(
                "/api/wallets",
                json={"name": f"Index Test Wallet {i}", "description": "For testing indexes"},
                headers=auth_headers
            )
            assert wallet_response.status_code == 200
            wallet_ids.append(wallet_response.json()["data"]["_id"])
        
        # Create transactions for each wallet
        for i, wallet_id in enumerate(wallet_ids):
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
            writer = csv.writer(temp_file)
            writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
            writer.writerow([f'Asset {i}', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
            temp_file.close()
            
            try:
                with open(temp_file.name, 'rb') as f:
                    upload_response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": ("transactions.csv", f, "text/csv")},
                        data={
                            "wallet_name": f"Index Test Wallet {i}",
                            "asset_type": "stock"
                        }
                    )
                assert upload_response.status_code == 200
            finally:
                import os
                os.unlink(temp_file.name)
        
        # Test query performance with different filters
        start_time = time.time()
        
        # Query all transactions
        all_transactions = client.get("/api/transactions", headers=auth_headers)
        assert all_transactions.status_code == 200
        assert all_transactions.json()["count"] == 5
        
        all_query_time = time.time() - start_time
        
        # Test filtered query performance
        start_time = time.time()
        
        filtered_transactions = client.get(
            "/api/transactions",
            headers=auth_headers,
            params={"wallet_name": "Index Test Wallet 0"}
        )
        assert filtered_transactions.status_code == 200
        assert filtered_transactions.json()["count"] == 1
        
        filtered_query_time = time.time() - start_time
        
        # Performance assertions
        assert all_query_time < 2    # Should query all within 2 seconds
        assert filtered_query_time < 1  # Should query filtered within 1 second
        
        print(f"Index performance metrics:")
        print(f"  All transactions query time: {all_query_time:.3f} seconds")
        print(f"  Filtered query time: {filtered_query_time:.3f} seconds")
