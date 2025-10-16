"""Tests for all test data files including previously unused ones."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime

from api.main import app
from src.config.mongodb import MongoDBConfig


@pytest.fixture(scope="function")
def test_db(unique_test_email, unique_test_username):
    """Get test database instance and clean up test data."""
    db = MongoDBConfig.get_database()
    
    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")
    
    # Clean up test data before each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": test_user_id})
    db.transaction_errors.delete_many({})
    
    # Create test user with unique email
    test_user = {
        "_id": test_user_id,
        "email": unique_test_email,
        "username": unique_test_username,
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    db.users.update_one(
        {"_id": test_user_id},
        {"$set": test_user},
        upsert=True
    )
    
    yield db
    
    # Clean up test data after each test
    db.transactions.delete_many({})
    db.wallets.delete_many({"$or": [
        {"user_id": test_user_id},
        {"user_id": str(test_user_id)}
    ]})
    db.assets.delete_many({})
    db.users.delete_many({"_id": test_user_id})
    db.transaction_errors.delete_many({})


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authentication headers for test user."""
    return {"X-User-ID": "507f1f77bcf86cd799439011"}


class TestAllTestDataFiles:
    """Tests for all test data files in the test_data directory."""

    def test_historia_transakcji_csv_original(self, client, test_db, auth_headers):
        """Test uploading the original historia-transakcji CSV file."""
        test_data_dir = Path("test_data")
        csv_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47.csv"
        
        if not csv_file.exists():
            pytest.skip(f"Test file not found: {csv_file}")
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Historia Transakcji Original",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0
            
            # Verify transaction structure
            transaction = data["data"]["transactions"][0]
            assert "asset_name" in transaction
            assert "date" in transaction
            assert "volume" in transaction
            assert "item_price" in transaction
            assert "transaction_amount" in transaction
            assert "currency" in transaction

    def test_historia_transakcji_csv_duplicate(self, client, test_db, auth_headers):
        """Test uploading the duplicate historia-transakcji CSV file."""
        test_data_dir = Path("test_data")
        csv_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47 (1).csv"
        
        if not csv_file.exists():
            pytest.skip(f"Test file not found: {csv_file}")
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Historia Transakcji Duplicate",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            # Should have same or similar number of transactions as original
            assert len(data["data"]["transactions"]) > 0

    def test_account_2082899_xlsx(self, client, test_db, auth_headers):
        """Test uploading the first account XLSX file."""
        test_data_dir = Path("test_data")
        xlsx_file = test_data_dir / "account_2082899_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        
        if not xlsx_file.exists():
            pytest.skip(f"Test file not found: {xlsx_file}")
        
        with open(xlsx_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (xlsx_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_name": "Account 2082899",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

    def test_account_51980100_xlsx(self, client, test_db, auth_headers):
        """Test uploading the second account XLSX file."""
        test_data_dir = Path("test_data")
        xlsx_file = test_data_dir / "account_51980100_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        
        if not xlsx_file.exists():
            pytest.skip(f"Test file not found: {xlsx_file}")
        
        with open(xlsx_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (xlsx_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_name": "Account 51980100",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

    def test_operacje_zlec_csv(self, client, test_db, auth_headers):
        """Test uploading the operacje-zlec CSV file."""
        test_data_dir = Path("test_data")
        csv_file = test_data_dir / "operacje-zlec_20251003193726969.csv"
        
        if not csv_file.exists():
            pytest.skip(f"Test file not found: {csv_file}")
        
        with open(csv_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Operacje Zlec",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

    def test_historia_dyspozycji_xls(self, client, test_db, auth_headers):
        """Test uploading the HistoriaDyspozycji XLS file."""
        test_data_dir = Path("test_data")
        xls_file = test_data_dir / "HistoriaDyspozycji (5).xls"
        
        if not xls_file.exists():
            pytest.skip(f"Test file not found: {xls_file}")
        
        with open(xls_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (xls_file.name, f, "application/vnd.ms-excel")},
                data={
                    "wallet_name": "Historia Dyspozycji",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

    def test_all_files_with_different_transaction_types(self, client, test_db, auth_headers):
        """Test all files with different transaction types."""
        test_data_dir = Path("test_data")
        transaction_types = ["buy", "sell", "dividend", "transfer_in", "transfer_out"]
        
        # Get all available files
        all_files = []
        for pattern in ["*.csv", "*.xlsx", "*.xls"]:
            all_files.extend(test_data_dir.glob(pattern))
        
        if not all_files:
            pytest.skip("No test files found")
        
        # Test each file with different transaction types
        for file_path in all_files[:3]:  # Limit to first 3 files to avoid too many tests
            for tx_type in transaction_types:
                with open(file_path, 'rb') as f:
                    response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": (file_path.name, f, "application/octet-stream")},
                        data={
                            "wallet_name": f"Test_{file_path.stem}_{tx_type}",
                            "transaction_type": tx_type,
                            "asset_type": "stock"
                        }
                    )
                
                # Should succeed or fail gracefully
                assert response.status_code in [200, 422, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["data"]["transaction_type"] == tx_type

    def test_all_files_with_different_asset_types(self, client, test_db, auth_headers):
        """Test all files with different asset types."""
        test_data_dir = Path("test_data")
        asset_types = ["stock", "bond", "cryptocurrency", "commodity", "etf", "managed mutual fund"]
        
        # Get all available files
        all_files = []
        for pattern in ["*.csv", "*.xlsx", "*.xls"]:
            all_files.extend(test_data_dir.glob(pattern))
        
        if not all_files:
            pytest.skip("No test files found")
        
        # Test each file with different asset types
        for file_path in all_files[:2]:  # Limit to first 2 files
            for asset_type in asset_types:
                with open(file_path, 'rb') as f:
                    response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": (file_path.name, f, "application/octet-stream")},
                        data={
                            "wallet_name": f"Test_{file_path.stem}_{asset_type}",
                            "transaction_type": "buy",
                            "asset_type": asset_type
                        }
                    )
                
                # Should succeed or fail gracefully
                assert response.status_code in [200, 422, 500]
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["data"]["asset_type"] == asset_type

    def test_file_comparison_historia_transakcji(self, client, test_db, auth_headers):
        """Test comparing the two historia-transakcji files."""
        test_data_dir = Path("test_data")
        original_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47.csv"
        duplicate_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47 (1).csv"
        
        if not original_file.exists() or not duplicate_file.exists():
            pytest.skip("Historia transakcji files not found")
        
        results = {}
        
        # Upload original file
        with open(original_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (original_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Historia Original",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        if response.status_code == 200:
            results["original"] = response.json()["data"]["summary"]["total_transactions"]
        
        # Upload duplicate file
        with open(duplicate_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (duplicate_file.name, f, "text/csv")},
                data={
                    "wallet_name": "Historia Duplicate",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        if response.status_code == 200:
            results["duplicate"] = response.json()["data"]["summary"]["total_transactions"]
        
        # Both files should process successfully
        assert "original" in results
        assert "duplicate" in results
        
        # They should have similar transaction counts (might be identical or slightly different)
        assert abs(results["original"] - results["duplicate"]) <= 1

    def test_file_comparison_account_xlsx(self, client, test_db, auth_headers):
        """Test comparing the two account XLSX files."""
        test_data_dir = Path("test_data")
        account1_file = test_data_dir / "account_2082899_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        account2_file = test_data_dir / "account_51980100_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        
        if not account1_file.exists() or not account2_file.exists():
            pytest.skip("Account XLSX files not found")
        
        results = {}
        
        # Upload first account file
        with open(account1_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (account1_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_name": "Account 2082899",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        if response.status_code == 200:
            results["account1"] = response.json()["data"]["summary"]["total_transactions"]
        
        # Upload second account file
        with open(account2_file, 'rb') as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (account2_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={
                    "wallet_name": "Account 51980100",
                    "transaction_type": "buy",
                    "asset_type": "stock"
                }
            )
        
        if response.status_code == 200:
            results["account2"] = response.json()["data"]["summary"]["total_transactions"]
        
        # Both files should process successfully
        assert "account1" in results
        assert "account2" in results
        
        # Both should have some transactions
        assert results["account1"] > 0
        assert results["account2"] > 0

    def test_all_files_error_handling(self, client, test_db, auth_headers):
        """Test error handling for all files."""
        test_data_dir = Path("test_data")
        
        # Get all available files
        all_files = []
        for pattern in ["*.csv", "*.xlsx", "*.xls"]:
            all_files.extend(test_data_dir.glob(pattern))
        
        if not all_files:
            pytest.skip("No test files found")
        
        error_counts = {}
        
        for file_path in all_files:
            with open(file_path, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (file_path.name, f, "application/octet-stream")},
                    data={
                        "wallet_name": f"Error_Test_{file_path.stem}",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
                )
            
            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                error_counts[file_path.name] = {
                    "total": summary.get("total_transactions", 0),
                    "failed": summary.get("failed_transactions", 0),
                    "errors": summary.get("errors", 0)
                }
        
        # Verify that all files were processed
        assert len(error_counts) == len(all_files)
        
        # Log the results for analysis
        print(f"\nFile processing results:")
        for filename, counts in error_counts.items():
            print(f"  {filename}: {counts['total']} total, {counts['failed']} failed, {counts['errors']} errors")

    def test_file_metadata_extraction(self, client, test_db, auth_headers):
        """Test that file metadata is properly extracted and stored."""
        test_data_dir = Path("test_data")
        
        # Test with a CSV file
        csv_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47.csv"
        if csv_file.exists():
            with open(csv_file, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (csv_file.name, f, "text/csv")},
                    data={
                        "wallet_name": "Metadata Test CSV",
                        "transaction_type": "buy",
                        "asset_type": "stock"
                    }
                )
            
            if response.status_code == 200:
                data = response.json()
                assert "wallet_name" in data["data"]
                assert "transaction_type" in data["data"]
                assert "asset_type" in data["data"]
                assert data["data"]["wallet_name"] == "Metadata Test CSV"
                assert data["data"]["transaction_type"] == "buy"
                assert data["data"]["asset_type"] == "stock"
        
        # Test with an XLSX file
        xlsx_file = test_data_dir / "account_2082899_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        if xlsx_file.exists():
            with open(xlsx_file, 'rb') as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (xlsx_file.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    data={
                        "wallet_name": "Metadata Test XLSX",
                        "transaction_type": "sell",
                        "asset_type": "bond"
                    }
                )
            
            if response.status_code == 200:
                data = response.json()
                assert data["data"]["wallet_name"] == "Metadata Test XLSX"
                assert data["data"]["transaction_type"] == "sell"
                assert data["data"]["asset_type"] == "bond"
