"""Statistics endpoints."""

from fastapi import APIRouter, Depends
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import get_db
from src.auth.firebase_auth import get_current_user_from_token

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get("", summary="Get user statistics", response_model=None)
async def get_statistics(
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Get statistics for the authenticated user.

    **Authentication Required:** Include `X-User-ID` header with your user ID.

    **Returns:**
    - Total number of wallets owned by user
    - Total number of assets (shared across all users)
    - Total number of transactions from user's wallets
    - Breakdown of transactions by type

    **Errors:**
    - 401: Invalid or missing X-User-ID header
    """
    # Get user's wallet IDs
    user_wallets = list(
        db.wallets.find(
            {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}, {"_id": 1}
        )
    )
    wallet_ids = [w["_id"] for w in user_wallets]

    stats = {
        "total_wallets": len(wallet_ids),
        "total_assets": db.assets.count_documents({}),
        "total_transactions": db.transactions.count_documents(
            {"wallet_id": {"$in": wallet_ids}}
        ),
        "transactions_by_type": {},
    }

    # Get transaction type breakdown for user's wallets only
    pipeline = [
        {"$match": {"wallet_id": {"$in": wallet_ids}}},
        {"$group": {"_id": "$transaction_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    type_counts = list(db.transactions.aggregate(pipeline))
    for item in type_counts:
        trans_type = item["_id"]
        if hasattr(trans_type, "value"):
            stats["transactions_by_type"][trans_type.value] = item["count"]
        else:
            stats["transactions_by_type"][str(trans_type)] = item["count"]

    return stats
