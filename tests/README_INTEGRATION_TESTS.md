# Integration Tests for FastAPI Wallet Endpoints

## Overview

The file `test_api_wallets.py` contains comprehensive integration tests for the FastAPI wallet endpoints.

## What's Tested

### List Wallets (`GET /api/wallets`)
- ✅ Empty wallet list
- ✅ List wallets with data
- ✅ Pagination (limit & skip)
- ✅ Authentication required
- ✅ Invalid user ID handling
- ✅ User isolation (users only see their wallets)

### Create Wallet (`POST /api/wallets`)
- ✅ Successful creation
- ✅ Creation without description
- ✅ Duplicate name prevention
- ✅ Invalid data validation
- ✅ Name length validation (max 200 chars)
- ✅ Authentication required
- ✅ Name whitespace stripping

### Delete Wallet (`DELETE /api/wallets/{wallet_id}`)
- ✅ Successful deletion
- ✅ Cascade delete transactions
- ✅ Non-existent wallet handling
- ✅ Invalid ID format
- ✅ User cannot delete other users' wallets
- ✅ Authentication required

### Integration Scenarios
- ✅ Complete workflow (create → list → delete)
- ✅ Multiple users isolation

## Running the Tests

### Run all wallet integration tests (NO COVERAGE):
```bash
# Recommended: Skip coverage checks for integration tests
pytest tests/test_api_wallets.py -v --no-cov

# Or use the integration marker
pytest -m integration --no-cov
```

### Run with coverage (will be lower - not recommended):
```bash
# This will show lower coverage since only API code is exercised
pytest tests/test_api_wallets.py -v
# Coverage will be ~37% since most src/ modules aren't used
```

### Run specific test class:
```bash
pytest tests/test_api_wallets.py::TestListWallets -v --no-cov
pytest tests/test_api_wallets.py::TestCreateWallet -v --no-cov
pytest tests/test_api_wallets.py::TestDeleteWallet -v --no-cov
```

### Run specific test:
```bash
pytest tests/test_api_wallets.py::TestListWallets::test_list_wallets_empty -v --no-cov
```

### Run ALL tests (unit + integration):
```bash
# This gives proper overall coverage (79.81%)
pytest
```

## Prerequisites

1. **MongoDB Connection**: Tests use the MongoDB instance configured in your environment
2. **Environment Variables**: Ensure `MONGODB_URL` and `MONGODB_DATABASE` are set
3. **Test Database**: Tests create and clean up test users automatically

## Test Data Management

### Test Users
- **User 1**: ObjectId(`507f1f77bcf86cd799439011`)
  - Email: `test@example.com`
  - Username: `testuser`
  
- **User 2**: ObjectId(`507f1f77bcf86cd799439012`)
  - Email: `test2@example.com`
  - Username: `testuser2`

### Cleanup
- Test users are created before each test
- All test wallets and transactions are deleted after each test
- Test users are removed after each test

## Important Notes

⚠️ **Production Database**: These tests use the configured MongoDB database. For production safety:
1. Use a separate test database
2. Set `MONGODB_DATABASE=finance_tracking_test` in your test environment
3. Never run tests against production data

## Test Structure

Each test class follows the AAA pattern:
- **Arrange**: Set up test data and fixtures
- **Act**: Make API request
- **Assert**: Verify response and side effects

Example:
```python
def test_create_wallet_success(self, client, auth_headers, test_db):
    # Arrange
    wallet_data = {
        "name": "My Investment Wallet",
        "description": "For tracking investments"
    }
    
    # Act
    response = client.post("/api/wallets", json=wallet_data, headers=auth_headers)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

## Coverage

Integration tests provide:
- **API endpoint coverage**: All wallet endpoints tested
- **Authentication coverage**: All auth scenarios tested
- **Error handling coverage**: Invalid inputs and edge cases covered
- **Data integrity coverage**: Database operations verified

## Extending Tests

To add new tests:

1. **Choose the appropriate test class** or create a new one
2. **Use existing fixtures**: `client`, `auth_headers`, `test_db`, `test_user_id`
3. **Follow naming convention**: `test_<action>_<scenario>`
4. **Clean up any additional data** in the test if needed

Example:
```python
def test_update_wallet_name(self, client, auth_headers, test_db, test_user_id):
    # Create wallet
    wallet_id = create_test_wallet(test_db, test_user_id, "Old Name")
    
    # Update wallet
    update_data = {"name": "New Name"}
    response = client.patch(f"/api/wallets/{wallet_id}", 
                           json=update_data, 
                           headers=auth_headers)
    
    # Verify
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "New Name"
```

## Troubleshooting

### Tests failing with 401 Unauthorized
- Ensure test users are being created (check fixture)
- Verify `X-User-ID` header is being sent
- Check user exists in database

### Tests failing with duplicate key errors
- Verify cleanup is working properly
- Check if previous test run left data behind
- Manually clean test data: `db.wallets.delete_many({"user_id": ObjectId("507f1f77bcf86cd799439011")})`

### Tests timing out
- Check MongoDB connection
- Ensure database is accessible
- Verify network connectivity

## Future Improvements

- [ ] Add test for wallet update endpoint (when implemented)
- [ ] Add tests for wallet sorting/filtering
- [ ] Add performance tests for large datasets
- [ ] Mock MongoDB for faster tests
- [ ] Add tests for concurrent operations
- [ ] Add tests for transaction limits

