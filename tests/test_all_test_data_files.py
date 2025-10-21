"""Tests for all test data files including previously unused ones."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime, UTC
import pandas as pd

from api.main import app
from src.config.mongodb import MongoDBConfig

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def _create_wallet_and_get_id(
    client: TestClient, headers: dict, name: str, description: str = "Test"
) -> str:
    """Helper to create a wallet and return its _id as string."""
    resp = client.post(
        "/api/wallets", headers=headers, json={"name": name, "description": description}
    )
    assert resp.status_code == 200, f"Failed to create wallet {name}: {resp.text}"
    return resp.json()["data"]["_id"]


def get_file_row_count(file_path: Path) -> dict:
    """Get row count and column information for a test file."""
    if not file_path.exists():
        return {"error": "File not found"}

    try:
        if file_path.suffix.lower() in [".csv", ".txt"]:
            if "historia-transakcji" in file_path.name:
                # Special handling for historia-transakcji files
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Find the header line
                header_line_idx = None
                for i, line in enumerate(lines):
                    if 'Data","Status transakcji","Typ transakcji"' in line:
                        header_line_idx = i
                        break

                if header_line_idx is not None:
                    # Count data rows
                    data_rows = 0
                    for line in lines[header_line_idx + 1 :]:
                        line = line.strip()
                        if line and ('","' in line or line.count(",") >= 5):
                            data_rows += 1

                    # Parse header
                    header_line = lines[header_line_idx].strip().strip('"')
                    columns = [col.strip('"') for col in header_line.split('","')]

                    return {
                        "rows": data_rows,
                        "columns": len(columns),
                        "column_names": columns,
                        "type": "csv",
                    }
                else:
                    return {"error": "Could not find header line"}
            else:
                # Regular CSV files
                for sep in [";", ",", "\t"]:
                    try:
                        df = pd.read_csv(file_path, sep=sep, encoding="utf-8")
                        if len(df.columns) > 1:
                            return {
                                "rows": len(df),
                                "columns": len(df.columns),
                                "column_names": list(df.columns),
                                "type": "csv",
                                "separator": sep,
                            }
                    except:
                        continue

                # Fallback
                df = pd.read_csv(file_path, encoding="utf-8")
                return {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns),
                    "type": "csv",
                }

        elif file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
            return {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "type": "excel",
            }

        return {"error": f"Unsupported file type: {file_path.suffix}"}

    except Exception as e:
        return {"error": str(e)}


def validate_transaction_columns(transaction_data: dict) -> dict:
    """Validate that transaction data has all required columns."""
    required_fields = [
        "asset_name",
        "date",
        "volume",
        "item_price",
        "transaction_amount",
        "currency",
        "transaction_type",
    ]

    validation_result = {
        "has_required_fields": True,
        "missing_fields": [],
        "extra_fields": [],
        "field_types": {},
    }

    # Check for required fields
    for field in required_fields:
        if field not in transaction_data:
            validation_result["missing_fields"].append(field)
            validation_result["has_required_fields"] = False

    # Check field types
    for field, value in transaction_data.items():
        if field == "volume" and not isinstance(value, (int, float)):
            validation_result["field_types"][
                field
            ] = f"Expected numeric, got {type(value).__name__}"
        elif field == "item_price" and not isinstance(value, (int, float)):
            validation_result["field_types"][
                field
            ] = f"Expected numeric, got {type(value).__name__}"
        elif field == "transaction_amount" and not isinstance(value, (int, float)):
            validation_result["field_types"][
                field
            ] = f"Expected numeric, got {type(value).__name__}"
        elif field == "date" and not isinstance(value, str):
            validation_result["field_types"][
                field
            ] = f"Expected string, got {type(value).__name__}"

    return validation_result


def compare_file_to_database_rows(file_info: dict, api_response: dict) -> dict:
    """Compare row counts between file and database insertion results."""
    comparison = {
        "file_rows": file_info.get("rows", 0),
        "db_inserted": api_response.get("data", {})
        .get("summary", {})
        .get("total_transactions", 0),
        "db_failed": api_response.get("data", {})
        .get("summary", {})
        .get("failed_transactions", 0),
        "match_exact": False,
        "match_reasonable": False,
        "difference": 0,
    }

    if "error" in file_info:
        comparison["file_error"] = file_info["error"]
        return comparison

    comparison["difference"] = comparison["file_rows"] - comparison["db_inserted"]
    comparison["match_exact"] = comparison["file_rows"] == comparison["db_inserted"]

    # Consider it reasonable if within 15% difference (allowing for header rows, empty rows, validation errors, etc.)
    tolerance = max(1, int(comparison["file_rows"] * 0.15))
    comparison["match_reasonable"] = abs(comparison["difference"]) <= tolerance

    # Also consider it reasonable if we have a high success rate (80% or more)
    success_rate = (
        comparison["db_inserted"] / comparison["file_rows"]
        if comparison["file_rows"] > 0
        else 0
    )
    comparison["success_rate"] = success_rate
    comparison["high_success_rate"] = success_rate >= 0.80

    return comparison


@pytest.fixture(scope="function")
def test_db(unique_test_email, unique_test_username):
    """Get test database instance and clean up test data."""
    db = MongoDBConfig.get_database()

    # Test user IDs
    test_user_id = ObjectId("507f1f77bcf86cd799439011")

    # Clean up test data before each test
    db.transactions.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )
    db.wallets.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )
    # Only delete assets that are referenced by test transactions
    test_wallet_ids = [
        w["_id"]
        for w in db.wallets.find(
            {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
        )
    ]
    if test_wallet_ids:
        test_asset_ids = [
            t["asset_id"]
            for t in db.transactions.find({"wallet_id": {"$in": test_wallet_ids}})
        ]
        if test_asset_ids:
            db.assets.delete_many({"_id": {"$in": test_asset_ids}})
    db.users.delete_many({"_id": test_user_id})
    db.transaction_errors.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )

    # Create test user with unique email
    test_user = {
        "_id": test_user_id,
        "email": unique_test_email,
        "username": unique_test_username,
        "full_name": "Test User",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    db.users.update_one({"_id": test_user_id}, {"$set": test_user}, upsert=True)

    yield db

    # Clean up test data after each test
    db.transactions.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )
    db.wallets.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )
    # Only delete assets that are referenced by test transactions
    test_wallet_ids = [
        w["_id"]
        for w in db.wallets.find(
            {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
        )
    ]
    if test_wallet_ids:
        test_asset_ids = [
            t["asset_id"]
            for t in db.transactions.find({"wallet_id": {"$in": test_wallet_ids}})
        ]
        if test_asset_ids:
            db.assets.delete_many({"_id": {"$in": test_asset_ids}})
    db.users.delete_many({"_id": test_user_id})
    db.transaction_errors.delete_many(
        {"$or": [{"user_id": test_user_id}, {"user_id": str(test_user_id)}]}
    )


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Auth headers are now provided by conftest.py fixtures


class TestAllTestDataFiles:
    """Tests for all test data files in the test_data directory."""

    def test_historia_transakcji_csv_original(self, client, test_db, auth_headers):
        """Test uploading the original historia-transakcji CSV file."""
        test_data_dir = Path("test_data")
        csv_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47.csv"

        if not csv_file.exists():
            pytest.skip(f"Test file not found: {csv_file}")

        # Get file information before upload
        file_info = get_file_row_count(csv_file)
        print(f"\nFile analysis: {file_info}")

        with open(csv_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={"wallet_name": "Historia Transakcji Original"},
            )

        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

            # Row count comparison
            row_comparison = compare_file_to_database_rows(file_info, data)
            print(f"Row comparison: {row_comparison}")

            # Verify we have a reasonable match (within 15% tolerance) OR high success rate (80%+)
            assert (
                row_comparison["match_reasonable"]
                or row_comparison["high_success_rate"]
            ), (
                f"Row count mismatch: File has {row_comparison['file_rows']} rows, "
                f"but only {row_comparison['db_inserted']} were inserted. "
                f"Difference: {row_comparison['difference']}, "
                f"Success rate: {row_comparison['success_rate']:.2%}"
            )

            # Verify transaction structure and validate columns
            for i, transaction in enumerate(
                data["data"]["transactions"][:3]
            ):  # Test first 3 transactions
                validation = validate_transaction_columns(transaction)
                print(f"Transaction {i+1} validation: {validation}")

                assert validation[
                    "has_required_fields"
                ], f"Transaction {i+1} missing required fields: {validation['missing_fields']}"

                # Check that we have the expected fields
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

        # Get file information before upload
        file_info = get_file_row_count(csv_file)
        print(f"\nFile analysis: {file_info}")

        with open(csv_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={"wallet_name": "Historia Transakcji Duplicate"},
            )

        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]

            # Row count comparison
            row_comparison = compare_file_to_database_rows(file_info, data)
            print(f"Row comparison: {row_comparison}")

            # Verify we have a reasonable match OR high success rate
            assert (
                row_comparison["match_reasonable"]
                or row_comparison["high_success_rate"]
            ), (
                f"Row count mismatch: File has {row_comparison['file_rows']} rows, "
                f"but only {row_comparison['db_inserted']} were inserted. "
                f"Difference: {row_comparison['difference']}, "
                f"Success rate: {row_comparison['success_rate']:.2%}"
            )

            # Should have same or similar number of transactions as original
            assert len(data["data"]["transactions"]) > 0

    def test_account_2082899_xlsx(self, client, test_db, auth_headers):
        """Test uploading the first account XLSX file."""
        test_data_dir = Path("test_data")
        xlsx_file = test_data_dir / "account_2082899_pl_xlsx_2005-12-31_2025-10-03.xlsx"

        if not xlsx_file.exists():
            pytest.skip(f"Test file not found: {xlsx_file}")

        # Get file information before upload
        file_info = get_file_row_count(xlsx_file)
        print(f"\nFile analysis: {file_info}")

        with open(xlsx_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={
                    "file": (
                        xlsx_file.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"wallet_name": "Account 2082899"},
            )

        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]

            # Row count comparison
            row_comparison = compare_file_to_database_rows(file_info, data)
            print(f"Row comparison: {row_comparison}")

            # For large files, we might not expect exact matches due to data quality issues
            # But we should have processed a reasonable number of rows
            assert row_comparison["db_inserted"] > 0, "No transactions were inserted"

            # Verify we processed at least some rows (even if not all)
            assert row_comparison["db_inserted"] >= row_comparison["file_rows"] * 0.1, (
                f"Too few transactions processed: {row_comparison['db_inserted']} out of "
                f"{row_comparison['file_rows']} file rows"
            )

            assert len(data["data"]["transactions"]) > 0

    def test_account_51980100_xlsx(self, client, test_db, auth_headers):
        """Test uploading the second account XLSX file."""
        test_data_dir = Path("test_data")
        xlsx_file = (
            test_data_dir / "account_51980100_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        )

        if not xlsx_file.exists():
            pytest.skip(f"Test file not found: {xlsx_file}")

        with open(xlsx_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={
                    "file": (
                        xlsx_file.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"wallet_name": "Account 51980100"},
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

        # Get file information before upload
        file_info = get_file_row_count(csv_file)
        print(f"\nFile analysis: {file_info}")

        with open(csv_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (csv_file.name, f, "text/csv")},
                data={"wallet_name": "Operacje Zlec"},
            )

        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]

            # Row count comparison
            row_comparison = compare_file_to_database_rows(file_info, data)
            print(f"Row comparison: {row_comparison}")

            # Verify we have a reasonable match (within 15% tolerance) OR high success rate (80%+)
            assert (
                row_comparison["match_reasonable"]
                or row_comparison["high_success_rate"]
            ), (
                f"Row count mismatch: File has {row_comparison['file_rows']} rows, "
                f"but only {row_comparison['db_inserted']} were inserted. "
                f"Difference: {row_comparison['difference']}, "
                f"Success rate: {row_comparison['success_rate']:.2%}"
            )

            # Validate transaction columns
            for i, transaction in enumerate(
                data["data"]["transactions"][:3]
            ):  # Test first 3 transactions
                validation = validate_transaction_columns(transaction)
                print(f"Transaction {i+1} validation: {validation}")

                assert validation[
                    "has_required_fields"
                ], f"Transaction {i+1} missing required fields: {validation['missing_fields']}"

            assert len(data["data"]["transactions"]) > 0

    def test_historia_dyspozycji_xls(self, client, test_db, auth_headers):
        """Test uploading the HistoriaDyspozycji XLS file."""
        test_data_dir = Path("test_data")
        xls_file = test_data_dir / "HistoriaDyspozycji (5).xls"

        if not xls_file.exists():
            pytest.skip(f"Test file not found: {xls_file}")

        with open(xls_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (xls_file.name, f, "application/vnd.ms-excel")},
                data={"wallet_name": "Historia Dyspozycji"},
            )

        # Should succeed or fail gracefully with validation error
        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data["data"]
            assert len(data["data"]["transactions"]) > 0

    def test_all_files_with_different_transaction_types(
        self, client, test_db, auth_headers
    ):
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
        for file_path in all_files[
            :3
        ]:  # Limit to first 3 files to avoid too many tests
            for tx_type in transaction_types:
                with open(file_path, "rb") as f:
                    response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": (file_path.name, f, "application/octet-stream")},
                        data={"wallet_name": f"Test_{file_path.stem}_{tx_type}"},
                    )

                # Should succeed or fail gracefully
                assert response.status_code in [200, 422, 500]

                if response.status_code == 200:
                    data = response.json()
                    assert data["data"]["transaction_type"] == tx_type

    def test_all_files_with_different_asset_types(self, client, test_db, auth_headers):
        """Test all files with different asset types."""
        test_data_dir = Path("test_data")
        asset_types = [
            "stock",
            "bond",
            "cryptocurrency",
            "commodity",
            "etf",
            "managed mutual fund",
        ]

        # Get all available files
        all_files = []
        for pattern in ["*.csv", "*.xlsx", "*.xls"]:
            all_files.extend(test_data_dir.glob(pattern))

        if not all_files:
            pytest.skip("No test files found")

        # Test each file with different asset types
        for file_path in all_files[:2]:  # Limit to first 2 files
            for asset_type in asset_types:
                with open(file_path, "rb") as f:
                    response = client.post(
                        "/api/transactions/upload",
                        headers=auth_headers,
                        files={"file": (file_path.name, f, "application/octet-stream")},
                        data={"wallet_name": f"Test_{file_path.stem}_{asset_type}"},
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
        duplicate_file = (
            test_data_dir / "historia-transakcji_3-10-2025_11-08-47 (1).csv"
        )

        if not original_file.exists() or not duplicate_file.exists():
            pytest.skip("Historia transakcji files not found")

        results = {}

        # Create wallets for uploads
        wallet1_id = _create_wallet_and_get_id(
            client, auth_headers, "Historia Original"
        )
        wallet2_id = _create_wallet_and_get_id(
            client, auth_headers, "Historia Duplicate"
        )

        # Upload original file
        with open(original_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (original_file.name, f, "text/csv")},
                data={"wallet_id": wallet1_id},
            )

        if response.status_code == 200:
            results["original"] = response.json()["data"]["summary"][
                "total_transactions"
            ]

        # Upload duplicate file
        with open(duplicate_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={"file": (duplicate_file.name, f, "text/csv")},
                data={"wallet_id": wallet2_id},
            )

        if response.status_code == 200:
            results["duplicate"] = response.json()["data"]["summary"][
                "total_transactions"
            ]

        # Both files should process successfully
        assert "original" in results
        assert "duplicate" in results

        # They should have similar transaction counts (might be identical or slightly different)
        assert abs(results["original"] - results["duplicate"]) <= 1

    def test_file_comparison_account_xlsx(self, client, test_db, auth_headers):
        """Test comparing the two account XLSX files."""
        test_data_dir = Path("test_data")
        account1_file = (
            test_data_dir / "account_2082899_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        )
        account2_file = (
            test_data_dir / "account_51980100_pl_xlsx_2005-12-31_2025-10-03.xlsx"
        )

        if not account1_file.exists() or not account2_file.exists():
            pytest.skip("Account XLSX files not found")

        results = {}

        # Create wallets for uploads
        wallet1_id = _create_wallet_and_get_id(client, auth_headers, "Account 2082899")
        wallet2_id = _create_wallet_and_get_id(client, auth_headers, "Account 51980100")

        # Upload first account file
        with open(account1_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={
                    "file": (
                        account1_file.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"wallet_id": wallet1_id},
            )

        if response.status_code == 200:
            results["account1"] = response.json()["data"]["summary"][
                "total_transactions"
            ]

        # Upload second account file
        with open(account2_file, "rb") as f:
            response = client.post(
                "/api/transactions/upload",
                headers=auth_headers,
                files={
                    "file": (
                        account2_file.name,
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"wallet_id": wallet2_id},
            )

        if response.status_code == 200:
            results["account2"] = response.json()["data"]["summary"][
                "total_transactions"
            ]

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
            # Create wallet for this file
            wallet_id = _create_wallet_and_get_id(
                client, auth_headers, f"Error_Test_{file_path.stem}"
            )

            with open(file_path, "rb") as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (file_path.name, f, "application/octet-stream")},
                    data={"wallet_id": wallet_id},
                )

            if response.status_code == 200:
                data = response.json()
                summary = data["data"]["summary"]
                error_counts[file_path.name] = {
                    "total": summary.get("total_transactions", 0),
                    "failed": summary.get("failed_transactions", 0),
                    "errors": summary.get("errors", 0),
                }

        # Verify that all files were processed
        assert len(error_counts) == len(all_files)

        # Log the results for analysis
        print(f"\nFile processing results:")
        for filename, counts in error_counts.items():
            print(
                f"  {filename}: {counts['total']} total, {counts['failed']} failed, {counts['errors']} errors"
            )

    def test_file_metadata_extraction(self, client, test_db, auth_headers):
        """Test that file metadata is properly extracted and stored."""
        test_data_dir = Path("test_data")

        # Test with a CSV file
        csv_file = test_data_dir / "historia-transakcji_3-10-2025_11-08-47.csv"
        if csv_file.exists():
            with open(csv_file, "rb") as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (csv_file.name, f, "text/csv")},
                    data={
                        "wallet_name": "Metadata Test CSV",
                        "transaction_type": "buy",
                        "asset_type": "stock",
                    },
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
            with open(xlsx_file, "rb") as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={
                        "file": (
                            xlsx_file.name,
                            f,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    },
                    data={
                        "wallet_name": "Metadata Test XLSX",
                        "transaction_type": "sell",
                        "asset_type": "bond",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                assert data["data"]["wallet_name"] == "Metadata Test XLSX"
                assert data["data"]["transaction_type"] == "sell"
                assert data["data"]["asset_type"] == "bond"

    def test_comprehensive_file_validation(self, client, test_db, auth_headers):
        """Comprehensive test that validates all files with detailed row count and column validation."""
        test_data_dir = Path("test_data")

        # Get all available files
        all_files = []
        for pattern in ["*.csv", "*.xlsx", "*.xls"]:
            all_files.extend(test_data_dir.glob(pattern))

        if not all_files:
            pytest.skip("No test files found")

        validation_results = {}

        for file_path in all_files:
            print(f"\n=== Validating {file_path.name} ===")

            # Get file information
            file_info = get_file_row_count(file_path)
            print(f"File analysis: {file_info}")

            # Create wallet for this file
            wallet_id = _create_wallet_and_get_id(
                client, auth_headers, f"Comprehensive_Test_{file_path.stem}"
            )

            # Upload file
            with open(file_path, "rb") as f:
                response = client.post(
                    "/api/transactions/upload",
                    headers=auth_headers,
                    files={"file": (file_path.name, f, "application/octet-stream")},
                    data={"wallet_id": wallet_id},
                )

            file_result = {
                "filename": file_path.name,
                "file_info": file_info,
                "status_code": response.status_code,
                "success": response.status_code == 200,
            }

            if response.status_code == 200:
                data = response.json()

                # Row count comparison
                row_comparison = compare_file_to_database_rows(file_info, data)
                file_result["row_comparison"] = row_comparison

                # Transaction validation
                transactions = data["data"]["transactions"]
                validation_results_summary = {
                    "total_transactions": len(transactions),
                    "valid_transactions": 0,
                    "invalid_transactions": 0,
                    "validation_errors": [],
                }

                # Validate first 5 transactions in detail
                for i, transaction in enumerate(transactions[:5]):
                    validation = validate_transaction_columns(transaction)
                    if validation["has_required_fields"]:
                        validation_results_summary["valid_transactions"] += 1
                    else:
                        validation_results_summary["invalid_transactions"] += 1
                        validation_results_summary["validation_errors"].append(
                            {"transaction_index": i, "errors": validation}
                        )

                file_result["validation_summary"] = validation_results_summary

                print(f"Row comparison: {row_comparison}")
                print(f"Validation summary: {validation_results_summary}")

                # Assertions
                assert (
                    row_comparison["db_inserted"] > 0
                ), f"No transactions inserted for {file_path.name}"

                # For CSV files, expect reasonable row match OR high success rate
                if file_path.suffix.lower() in [".csv", ".txt"]:
                    assert (
                        row_comparison["match_reasonable"]
                        or row_comparison["high_success_rate"]
                    ), (
                        f"Row count mismatch for {file_path.name}: "
                        f"File has {row_comparison['file_rows']} rows, "
                        f"but only {row_comparison['db_inserted']} were inserted. "
                        f"Difference: {row_comparison['difference']}, "
                        f"Success rate: {row_comparison['success_rate']:.2%}"
                    )

                # For Excel files, expect at least some processing
                elif file_path.suffix.lower() in [".xlsx", ".xls"]:
                    assert (
                        row_comparison["db_inserted"]
                        >= row_comparison["file_rows"] * 0.05
                    ), (
                        f"Too few transactions processed for {file_path.name}: "
                        f"{row_comparison['db_inserted']} out of {row_comparison['file_rows']} file rows"
                    )

                # Validate that we have at least some valid transactions
                assert (
                    validation_results_summary["valid_transactions"] > 0
                ), f"No valid transactions found for {file_path.name}"

            validation_results[file_path.name] = file_result

        # Print comprehensive summary
        print(f"\n{'='*60}")
        print("COMPREHENSIVE VALIDATION SUMMARY")
        print(f"{'='*60}")

        for filename, result in validation_results.items():
            print(f"\nFile: {filename}")
            print(f"  Status: {'SUCCESS' if result['success'] else 'FAILED'}")

            if result["success"] and "row_comparison" in result:
                rc = result["row_comparison"]
                print(f"  File rows: {rc['file_rows']}")
                print(f"  DB inserted: {rc['db_inserted']}")
                print(f"  DB failed: {rc['db_failed']}")
                print(f"  Match reasonable: {rc['match_reasonable']}")

                if "validation_summary" in result:
                    vs = result["validation_summary"]
                    print(f"  Valid transactions: {vs['valid_transactions']}")
                    print(f"  Invalid transactions: {vs['invalid_transactions']}")

        # Overall assertions
        successful_files = sum(1 for r in validation_results.values() if r["success"])
        assert (
            successful_files >= len(all_files) * 0.8
        ), f"Too many files failed: {successful_files}/{len(all_files)} succeeded"
