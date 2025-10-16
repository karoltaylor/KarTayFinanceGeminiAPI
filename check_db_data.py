#!/usr/bin/env python3
"""Check database data for transactions and errors."""

from src.config.mongodb import MongoDBConfig

db = MongoDBConfig.get_database()

print("="*60)
print("Database Statistics")
print("="*60)

# Count documents
trans_count = db.transactions.count_documents({})
errors_count = db.transaction_errors.count_documents({})
wallets_count = db.wallets.count_documents({})
assets_count = db.assets.count_documents({})

print(f"\nTransactions: {trans_count}")
print(f"Transaction Errors: {errors_count}")
print(f"Wallets: {wallets_count}")
print(f"Assets: {assets_count}")

# Show sample errors
if errors_count > 0:
    print(f"\n{'='*60}")
    print("Sample Transaction Errors")
    print('='*60)
    
    errors = list(db.transaction_errors.find().limit(5))
    for i, error in enumerate(errors, 1):
        print(f"\n{i}. File: {error['filename']}")
        print(f"   Row: {error['row_index']}")
        print(f"   Error Type: {error['error_type']}")
        print(f"   Message: {error['error_message'][:150]}")
        if len(error['error_message']) > 150:
            print(f"   ...")

# Show sample transactions
if trans_count > 0:
    print(f"\n{'='*60}")
    print("Sample Transactions")
    print('='*60)
    
    transactions = list(db.transactions.find().limit(3))
    for i, trans in enumerate(transactions, 1):
        wallet = db.wallets.find_one({"_id": trans['wallet_id']})
        asset = db.assets.find_one({"_id": trans['asset_id']})
        
        print(f"\n{i}. Wallet: {wallet['name'] if wallet else 'Unknown'}")
        print(f"   Asset: {asset['asset_name'] if asset else 'Unknown'}")
        print(f"   Date: {trans['date']}")
        print(f"   Type: {trans['transaction_type']}")
        print(f"   Volume: {trans['volume']}")
        print(f"   Price: {trans['item_price']}")
        print(f"   Amount: {trans['transaction_amount']}")
        print(f"   Currency: {trans['currency']}")

print(f"\n{'='*60}")
print("Check Complete!")
print('='*60)

