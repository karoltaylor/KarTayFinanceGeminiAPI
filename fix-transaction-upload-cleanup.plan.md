# Fix Transaction Upload Cleanup and Wallet ID Issues

## Summary

This plan addresses two critical issues:
1. **Windows file locking issue** causing HTTP 500 errors during transaction upload cleanup
2. **TransactionError using wallet_name instead of wallet_id** for proper data consistency

## Issues Fixed

### 1. Transaction Upload Cleanup Error (COMPLETED ✅)

**Problem**: Windows file locking issue (`WinError 32`) when deleting temporary files after successful transaction processing caused HTTP 500 errors even when transactions were successfully saved.

**Solution Implemented**:
- Added `_cleanup_temp_file()` helper function with retry logic and exponential backoff
- Restructured upload endpoint to build response before `finally` block
- Updated cleanup logic to use safe helper without raising exceptions
- Ensured success responses are sent even if cleanup fails

### 2. TransactionError Wallet ID Issue (COMPLETED ✅)

**Problem**: TransactionError model and endpoints were using `wallet_name` instead of `wallet_id`, causing data inconsistency.

**Solution Implemented**:
- Updated `TransactionError` model to use `wallet_id: PyObjectId` instead of `wallet_name: str`
- Updated transaction upload endpoint to save `wallet_id` in error records
- Updated `list_transaction_errors` endpoint to filter by `wallet_id` instead of `wallet_name`

## Changes Made

### Files Modified

1. **`api/routers/transactions.py`**:
   - Added `_cleanup_temp_file()` helper function (lines 30-64)
   - Restructured upload endpoint to build response before finally block (lines 149-318)
   - Updated error record creation to use `wallet_id` (line 202)
   - Updated `list_transaction_errors` to filter by `wallet_id` (line 475)

2. **`src/models/mongodb_models.py`**:
   - Changed `TransactionError.wallet_name` to `TransactionError.wallet_id` (line 410)

### Files Deleted

- `htmlcov_routers/` directory (debug coverage reports)

## Testing Results

- ✅ All 25 transaction unit tests pass
- ✅ No more `PermissionError` exceptions in backend logs
- ✅ Success responses returned even when cleanup fails
- ✅ Proper wallet_id usage in error records

## Next Steps

1. Run Black formatter on code
2. Run pytest with coverage to ensure 80%+ coverage
3. Create new git branch
4. Commit changes and create pull request
