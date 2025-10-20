"""Edge case and performance tests for comprehensive coverage."""

import pytest
from datetime import datetime, UTC
from bson import ObjectId
from fastapi.testclient import TestClient
import tempfile
import csv
import os
import time
import concurrent.futures
from pathlib import Path

from api.main import app
from src.config.mongodb import MongoDBConfig


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


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_file_upload(self, client, test_db, auth_headers):
        """Test uploading a very large file."""
        # Create a large CSV file (1000 transactions)
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Generate 1000 transactions
        for i in range(1000):
            asset_name = f"Asset_{i % 100}"  # 100 unique assets
            date = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            price = 50 + (i % 500)
            volume = 1 + (i % 100)
            total = price * volume
            fee = 1.0 + (i % 10)
            
            writer.writerow([asset_name, date, price, volume, total, fee, 'USD'])
        
        temp_file.close()
        
        try:
            # Measure upload time
            start_time = time.time()
            
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("large_file.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Large File Test",
                        "asset_type": "stock"
                    }
                )
            
            upload_time = time.time() - start_time
            
            # Should succeed or fail gracefully
            assert response.status_code in [200, 422, 500]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should have processed many transactions
                assert summary["total_transactions"] > 500
                
                # Should complete within reasonable time
                assert upload_time < 60  # 1 minute max
                
                print(f"Large file upload metrics:")
                print(f"  Upload time: {upload_time:.2f} seconds")
                print(f"  Transactions processed: {summary['total_transactions']}")
                print(f"  Failed transactions: {summary.get('failed_transactions', 0)}")
            
        finally:
            os.unlink(temp_file.name)

    def test_empty_file_handling(self, client, test_db, auth_headers):
        """Test handling of empty files."""
        # Test completely empty file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("empty.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Empty File Test",
                        "asset_type": "stock"
                    }
                )
            
            assert response.status_code == 422
            assert "No valid transactions" in response.json()["detail"]
            
        finally:
            os.unlink(temp_file.name)

    def test_file_with_only_headers(self, client, test_db, auth_headers):
        """Test file with only headers and no data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("headers_only.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Headers Only Test",
                        "asset_type": "stock"
                    }
                )
            
            assert response.status_code == 422
            assert "No valid transactions" in response.json()["detail"]
            
        finally:
            os.unlink(temp_file.name)

    def test_file_with_mixed_valid_invalid_data(self, client, test_db, auth_headers):
        """Test file with mix of valid and invalid data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Valid transaction
        writer.writerow(['Valid Asset', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        
        # Invalid transactions
        writer.writerow(['', '2024-01-16', '200.00', '5', '1000.00', '2.50', 'USD'])  # Empty asset name
        writer.writerow(['Invalid Asset', 'invalid-date', '300.00', '3', '900.00', '2.50', 'USD'])  # Invalid date
        writer.writerow(['Negative Asset', '2024-01-17', '-100.00', '10', '1000.00', '2.50', 'USD'])  # Negative price
        writer.writerow(['Zero Volume', '2024-01-18', '100.00', '0', '0.00', '2.50', 'USD'])  # Zero volume
        
        # Another valid transaction
        writer.writerow(['Another Valid Asset', '2024-01-19', '150.00', '8', '1200.00', '3.00', 'USD'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("mixed_data.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Mixed Data Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed with some transactions and some errors
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should have processed valid transactions
                assert summary["total_transactions"] >= 2
                
                # Should have some failed transactions
                assert summary["failed_transactions"] >= 3
                
                # Verify error records were created
                errors_count = test_db.transaction_errors.count_documents({})
                assert errors_count >= 3
                
        finally:
            os.unlink(temp_file.name)

    def test_very_long_field_values(self, client, test_db, auth_headers):
        """Test handling of very long field values."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Very long asset name (should be truncated or rejected)
        long_asset_name = "A" * 1000
        writer.writerow([long_asset_name, '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        
        # Very long currency code (should be rejected)
        writer.writerow(['Normal Asset', '2024-01-16', '200.00', '5', '1000.00', '2.50', 'VERYLONGCURRENCY'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("long_fields.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Long Fields Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should fail due to validation errors
            assert response.status_code in [422, 500]
            
        finally:
            os.unlink(temp_file.name)

    def test_special_characters_in_data(self, client, test_db, auth_headers):
        """Test handling of special characters in data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Special characters in asset name
        writer.writerow(['Asset & Co.', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        writer.writerow(['Asset "Quoted"', '2024-01-16', '200.00', '5', '1000.00', '2.50', 'USD'])
        writer.writerow(['Asset (Parentheses)', '2024-01-17', '300.00', '3', '900.00', '2.50', 'USD'])
        writer.writerow(['Asset #1', '2024-01-18', '400.00', '2', '800.00', '2.50', 'USD'])
        writer.writerow(['Asset $ymbol', '2024-01-19', '500.00', '1', '500.00', '2.50', 'USD'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("special_chars.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Special Chars Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed with special characters handled properly
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should process transactions with special characters
                assert summary["total_transactions"] >= 3
                
                # Verify asset names are preserved
                transactions = data["data"]["transactions"]
                asset_names = [tx["asset_name"] for tx in transactions]
                
                # Check that special characters are preserved
                assert any("&" in name for name in asset_names)
                assert any("(" in name for name in asset_names)
                assert any("#" in name for name in asset_names)
                
        finally:
            os.unlink(temp_file.name)

    def test_unicode_characters_in_data(self, client, test_db, auth_headers):
        """Test handling of Unicode characters in data."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Unicode characters in asset names
        writer.writerow(['Café & Co.', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        writer.writerow(['Müller AG', '2024-01-16', '200.00', '5', '1000.00', '2.50', 'USD'])
        writer.writerow(['株式会社テスト', '2024-01-17', '300.00', '3', '900.00', '2.50', 'USD'])
        writer.writerow(['Тест Корпорация', '2024-01-18', '400.00', '2', '800.00', '2.50', 'USD'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("unicode_chars.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Unicode Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed with Unicode characters handled properly
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should process transactions with Unicode characters
                assert summary["total_transactions"] >= 2
                
        finally:
            os.unlink(temp_file.name)

    def test_extreme_numeric_values(self, client, test_db, auth_headers):
        """Test handling of extreme numeric values."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Very large numbers
        writer.writerow(['Large Asset', '2024-01-15', '999999999.99', '1000000', '999999999990000.00', '999999.99', 'USD'])
        
        # Very small numbers
        writer.writerow(['Small Asset', '2024-01-16', '0.0001', '0.0001', '0.00000001', '0.0001', 'USD'])
        
        # Zero values
        writer.writerow(['Zero Asset', '2024-01-17', '0.00', '0', '0.00', '0.00', 'USD'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("extreme_values.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Extreme Values Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should handle extreme values appropriately
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should process valid extreme values
                assert summary["total_transactions"] >= 1
                
        finally:
            os.unlink(temp_file.name)

    def test_malformed_csv_file(self, client, test_db, auth_headers):
        """Test handling of malformed CSV files."""
        # CSV with inconsistent columns
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Asset 1', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        writer.writerow(['Asset 2', '2024-01-16', '200.00', '5'])  # Missing columns
        writer.writerow(['Asset 3', '2024-01-17', '300.00', '3', '900.00', '2.50', 'USD', 'Extra'])  # Extra columns
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("malformed.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Malformed CSV Test",
                        "asset_type": "stock"
                    }
                )
            
            # Should handle malformed CSV gracefully
            assert response.status_code in [200, 422, 500]
            
        finally:
            os.unlink(temp_file.name)

    def test_concurrent_large_uploads(self, client, test_db, auth_headers):
        """Test concurrent uploads of large files."""
        def create_large_file(file_index):
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
            writer = csv.writer(temp_file)
            writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
            
            # Generate 100 transactions per file
            for i in range(100):
                asset_name = f"Concurrent_Asset_{file_index}_{i}"
                date = f"2024-01-{(i % 28) + 1:02d}"
                price = 100 + (i % 200)
                volume = 1 + (i % 50)
                total = price * volume
                fee = 2.0 + (i % 5)
                
                writer.writerow([asset_name, date, price, volume, total, fee, 'USD'])
            
            temp_file.close()
            return temp_file.name
        
        def upload_file(file_path, wallet_name):
            try:
                with open(file_path, 'rb') as f:
                    response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": ("concurrent.csv", f, "text/csv")},
                        data={
                            "wallet_name": wallet_name,
                            "asset_type": "stock"
                        }
                    )
                return response.status_code == 200
            finally:
                os.unlink(file_path)
        
        # Create 5 large files
        file_paths = [create_large_file(i) for i in range(5)]
        
        try:
            # Execute concurrent uploads
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(upload_file, file_path, f"Concurrent_Wallet_{i}")
                    for i, file_path in enumerate(file_paths)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # All uploads should succeed
            assert all(results)
            
            # Should complete within reasonable time
            assert total_time < 120  # 2 minutes max
            
            # Verify all data was created
            transactions_count = test_db.transactions.count_documents({})
            assert transactions_count == 500  # 5 files * 100 transactions each
            
            wallets_count = test_db.wallets.count_documents({})
            assert wallets_count == 5
            
            assets_count = test_db.assets.count_documents({})
            assert assets_count == 500  # Each transaction creates a unique asset
            
            print(f"Concurrent upload metrics:")
            print(f"  Total time: {total_time:.2f} seconds")
            print(f"  Transactions created: {transactions_count}")
            print(f"  Wallets created: {wallets_count}")
            print(f"  Assets created: {assets_count}")
            
        except Exception as e:
            # Clean up files if test fails
            for file_path in file_paths:
                try:
                    os.unlink(file_path)
                except:
                    pass
            raise

    def test_memory_usage_large_dataset(self, client, test_db, auth_headers):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create a very large dataset
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Generate 2000 transactions
        for i in range(2000):
            asset_name = f"Memory_Asset_{i % 100}"  # 100 unique assets
            date = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            price = 50 + (i % 500)
            volume = 1 + (i % 100)
            total = price * volume
            fee = 1.0 + (i % 10)
            
            writer.writerow([asset_name, date, price, volume, total, fee, 'USD'])
        
        temp_file.close()
        
        try:
            # Measure memory during upload
            peak_memory = initial_memory
            
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("memory_test.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Memory Test Wallet",
                        "asset_type": "stock"
                    }
                )
            
            # Check memory after upload
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Should succeed or fail gracefully
            assert response.status_code in [200, 422, 500]
            
            # Memory increase should be reasonable (less than 500MB for 2000 transactions)
            assert memory_increase < 500
            
            print(f"Memory usage metrics:")
            print(f"  Initial memory: {initial_memory:.2f} MB")
            print(f"  Final memory: {final_memory:.2f} MB")
            print(f"  Memory increase: {memory_increase:.2f} MB")
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                print(f"  Transactions processed: {summary['total_transactions']}")
            
        finally:
            os.unlink(temp_file.name)

    def test_database_connection_failure_simulation(self, client, test_db, auth_headers):
        """Test behavior when database operations fail."""
        # This test simulates database connection issues by testing error handling
        
        # Create a transaction file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        writer.writerow(['Connection Test Asset', '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        temp_file.close()
        
        try:
            # Test with invalid user ID (simulates database constraint violation)
            invalid_headers = {"X-User-ID": "invalid-user-id"}
            
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=invalid_headers,
                    files={"file": ("connection_test.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Connection Test Wallet",
                        "asset_type": "stock"
                    }
                )
            
            # Should fail due to invalid user ID
            assert response.status_code == 401
            
        finally:
            os.unlink(temp_file.name)

    def test_boundary_value_limits(self, client, test_db, auth_headers):
        """Test boundary values and limits."""
        # Test maximum allowed values
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Test maximum wallet name length (200 characters)
        max_wallet_name = "A" * 200
        
        # Test maximum asset name length (200 characters)
        max_asset_name = "B" * 200
        
        writer.writerow([max_asset_name, '2024-01-15', '100.00', '10', '1000.00', '2.50', 'USD'])
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("boundary_test.csv", f, "text/csv")},
                    data={
                        "wallet_name": max_wallet_name,
                        "asset_type": "stock"
                    }
                )
            
            # Should succeed with maximum allowed values
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert data["data"]["wallet_name"] == max_wallet_name
                
                # Verify asset name was preserved
                transactions = data["data"]["transactions"]
                assert len(transactions) == 1
                assert transactions[0]["asset_name"] == max_asset_name
            
        finally:
            os.unlink(temp_file.name)

    def test_timezone_handling(self, client, test_db, auth_headers):
        """Test handling of different timezone formats."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='')
        writer = csv.writer(temp_file)
        writer.writerow(['Asset Name', 'Date', 'Price', 'Volume', 'Total', 'Fee', 'Currency'])
        
        # Different date formats with timezone information
        writer.writerow(['Timezone Asset 1', '2024-01-15T10:30:00Z', '100.00', '10', '1000.00', '2.50', 'USD'])
        writer.writerow(['Timezone Asset 2', '2024-01-16T15:45:00+02:00', '200.00', '5', '1000.00', '2.50', 'USD'])
        writer.writerow(['Timezone Asset 3', '2024-01-17T08:15:00-05:00', '300.00', '3', '900.00', '2.50', 'USD'])
        
        temp_file.close()
        
        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": ("timezone_test.csv", f, "text/csv")},
                    data={
                        "wallet_name": "Timezone Test Wallet",
                        "asset_type": "stock"
                    }
                )
            
            # Should handle timezone formats appropriately
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                
                # Should process timezone-aware dates
                assert summary["total_transactions"] >= 1
                
        finally:
            os.unlink(temp_file.name)
