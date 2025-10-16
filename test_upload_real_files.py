#!/usr/bin/env python3
"""Test transaction upload with real test data files."""

import requests
from pathlib import Path
import json

API_URL = "http://localhost:8000"
TEST_USER_ID = "507f1f77bcf86cd799439011"


def create_test_user():
    """Create a test user if it doesn't exist."""
    print(f"\n{'='*60}")
    print("Creating Test User")
    print('='*60)
    
    try:
        response = requests.post(
            f"{API_URL}/api/users/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"User created/found: {result.get('email')}")
            return result.get('user_id')
        else:
            print(f"Error creating user: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None


def test_file_upload(filepath: Path, user_id: str):
    """Test uploading a single file."""
    print(f"\n{'='*60}")
    print(f"Testing: {filepath.name}")
    print('='*60)
    
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filepath.name, f, 'application/octet-stream')}
            data = {
                'wallet_name': f'Test_{filepath.stem}',
                'transaction_type': 'buy',
                'asset_type': 'stock'
            }
            headers = {'X-User-ID': user_id}
            
            response = requests.post(
                f"{API_URL}/api/transactions/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=120  # 2 minutes timeout for AI processing
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                summary = result.get('data', {}).get('summary', {})
                print(f"Success: {summary.get('total_transactions', 0)} transactions")
                print(f"Errors: {summary.get('failed_transactions', 0)} failed")
                print(f"Wallets created: {summary.get('wallets_created', 0)}")
                print(f"Assets created: {summary.get('assets_created', 0)}")
                
                # Show first few transactions
                transactions = result.get('data', {}).get('transactions', [])
                if transactions:
                    print(f"\nFirst transaction sample:")
                    first_trans = transactions[0]
                    print(f"  - Asset: {first_trans.get('asset_name')}")
                    print(f"  - Date: {first_trans.get('date')}")
                    print(f"  - Volume: {first_trans.get('volume')}")
                    print(f"  - Price: {first_trans.get('item_price')}")
                    print(f"  - Amount: {first_trans.get('transaction_amount')}")
            else:
                print(f"Error: {response.text}")
                
    except requests.exceptions.Timeout:
        print("Error: Request timed out (AI processing may take longer)")
    except Exception as e:
        print(f"Error: {str(e)}")


def check_transaction_errors(user_id: str):
    """Check if there are any transaction errors."""
    print(f"\n{'='*60}")
    print("Checking Transaction Errors")
    print('='*60)
    
    try:
        headers = {'X-User-ID': user_id}
        response = requests.get(
            f"{API_URL}/api/transactions/errors",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            error_count = result.get('count', 0)
            print(f"Total errors: {error_count}")
            
            if error_count > 0:
                errors = result.get('errors', [])
                print(f"\nShowing first {min(5, error_count)} errors:")
                for i, error in enumerate(errors[:5], 1):
                    print(f"\n{i}. Error in {error.get('filename')} (row {error.get('row_index')})")
                    print(f"   Type: {error.get('error_type')}")
                    print(f"   Message: {error.get('error_message')[:100]}...")
        else:
            print(f"Error checking errors: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")


def check_database_stats(user_id: str):
    """Check database statistics."""
    print(f"\n{'='*60}")
    print("Database Statistics")
    print('='*60)
    
    try:
        headers = {'X-User-ID': user_id}
        
        # Get transactions count
        response = requests.get(
            f"{API_URL}/api/transactions?limit=1",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Transactions in database: {result.get('count', 0)}")
        
        # Get wallets count
        response = requests.get(
            f"{API_URL}/api/wallets",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Wallets in database: {result.get('count', 0)}")
            
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    print("="*60)
    print("Transaction Upload Test Script")
    print("="*60)
    print(f"API URL: {API_URL}")
    
    # Create test user first
    user_id = create_test_user()
    if user_id:
        TEST_USER_ID = user_id
    print(f"Test User ID: {TEST_USER_ID}")
    
    test_data_dir = Path("test_data")
    
    if not test_data_dir.exists():
        print(f"\nError: {test_data_dir} directory not found!")
        exit(1)
    
    # Get all test files
    test_files = []
    for file in test_data_dir.glob("*"):
        if file.suffix.lower() in ['.csv', '.txt', '.xls', '.xlsx']:
            test_files.append(file)
    
    if not test_files:
        print(f"\nNo test files found in {test_data_dir}")
        exit(1)
    
    print(f"\nFound {len(test_files)} test files")
    
    # Test each file
    for file in test_files:
        test_file_upload(file, TEST_USER_ID)
    
    # Check for errors
    check_transaction_errors(TEST_USER_ID)
    
    # Check database stats
    check_database_stats(TEST_USER_ID)
    
    print(f"\n{'='*60}")
    print("Test Complete!")
    print('='*60)
    print("\nData has been left in the database for inspection.")
    print("To view in MongoDB:")
    print("  - transactions collection: successful imports")
    print("  - transaction_errors collection: failed rows")
    print("  - wallets collection: created wallets")
    print("  - assets collection: created assets")

