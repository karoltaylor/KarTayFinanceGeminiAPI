#!/usr/bin/env python3
"""Debug transaction data to identify serialization issues."""

from src.config.mongodb import MongoDBConfig
from bson import ObjectId

db = MongoDBConfig.get_database()
user_id = ObjectId("68e619e3848c88e19bc78202")

print("=" * 60)
print("Debug Transaction Data")
print("=" * 60)

# Get user's wallets
user_wallets = list(
    db.wallets.find(
        {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}, {"_id": 1}
    )
)

print(f"Found {len(user_wallets)} wallets for user")

if user_wallets:
    wallet_ids = [w["_id"] for w in user_wallets]
    print(f"Wallet IDs: {wallet_ids}")

    # Get transactions
    transactions = list(
        db.transactions.find({"wallet_id": {"$in": wallet_ids}}).limit(3)
    )
    print(f"\nFound {len(transactions)} transactions")

    if transactions:
        print(f"\nFirst transaction structure:")
        first_trans = transactions[0]
        for key, value in first_trans.items():
            print(f"  {key}: {value} (type: {type(value).__name__})")
            if hasattr(value, "__class__"):
                print(f"    Class: {value.__class__}")
                print(f"    Module: {value.__class__.__module__}")

        print(f"\nTrying to convert first transaction...")
        try:
            # Try the same conversion as the API
            trans = first_trans.copy()
            trans["_id"] = str(trans["_id"])
            trans["wallet_id"] = str(trans["wallet_id"])
            trans["asset_id"] = str(trans["asset_id"])

            # Handle transaction_type enum safely
            if "transaction_type" in trans:
                if hasattr(trans["transaction_type"], "value"):
                    trans["transaction_type"] = trans["transaction_type"].value
                else:
                    trans["transaction_type"] = str(trans["transaction_type"])

            # Handle asset_type enum safely
            if "asset_type" in trans:
                if hasattr(trans["asset_type"], "value"):
                    trans["asset_type"] = trans["asset_type"].value
                else:
                    trans["asset_type"] = str(trans["asset_type"])

            # Convert any remaining ObjectId fields
            for key, value in trans.items():
                if (
                    hasattr(value, "__class__")
                    and value.__class__.__name__ == "ObjectId"
                ):
                    trans[key] = str(value)

            print("Conversion successful!")

        except Exception as e:
            print(f"Conversion failed: {str(e)}")
            print(f"Error type: {type(e)}")
    else:
        print("No transactions found")
else:
    print("No wallets found for user")

print("\n" + "=" * 60)
