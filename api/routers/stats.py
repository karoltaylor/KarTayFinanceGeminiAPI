"""Statistics endpoints."""

from fastapi import APIRouter, Depends
from bson import ObjectId
from pymongo.database import Database
from typing import List
from pydantic import BaseModel

from src.config.mongodb import get_db
from src.auth.firebase_auth import get_current_user_from_token

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


class AssetTypePercentage(BaseModel):
    """Asset type percentage breakdown."""

    asset_type: str
    percentage: float
    total_value: float
    transaction_count: int


class UserAssetStatistics(BaseModel):
    """User asset statistics with percentage breakdown."""

    total_portfolio_value: float
    asset_type_breakdown: List[AssetTypePercentage]
    total_transactions: int
    unique_assets: int


@router.get("", summary="Get user statistics", response_model=None)
async def get_statistics(
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Get statistics for the authenticated user.

    **Authentication Required:** Include Firebase ID token in Authorization header:
    `Authorization: Bearer <firebase_token>`

    **Returns:**
    - Total number of wallets owned by user
    - Total number of assets (shared across all users)
    - Total number of transactions from user's wallets
    - Breakdown of transactions by type

    **Errors:**
    - 401: Invalid or missing Firebase token
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


@router.get(
    "/asset-types",
    summary="Get user asset type percentages",
    response_model=UserAssetStatistics,
)
async def get_asset_type_percentages(
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Get asset type percentage breakdown for the authenticated user.

    **Authentication Required:** Include `Authorization` header with Firebase JWT token.

    **Returns:**
    - Total portfolio value across all user's wallets
    - Percentage breakdown by asset type (stocks, bonds, ETFs, etc.)
    - Total transaction count and unique asset count
    - Detailed breakdown with values and transaction counts per asset type

    **Errors:**
    - 401: Invalid or missing Authorization header
    - 404: No transactions found for user
    """
    # Get user's wallet IDs
    user_wallets = list(
        db.wallets.find(
            {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}, {"_id": 1}
        )
    )
    wallet_ids = [w["_id"] for w in user_wallets]

    if not wallet_ids:
        return UserAssetStatistics(
            total_portfolio_value=0.0,
            asset_type_breakdown=[],
            total_transactions=0,
            unique_assets=0,
        )

    # Aggregate pipeline to get asset type statistics
    pipeline = [
        # Match transactions from user's wallets
        {"$match": {"wallet_id": {"$in": wallet_ids}}},
        # Lookup asset information
        {
            "$lookup": {
                "from": "assets",
                "localField": "asset_id",
                "foreignField": "_id",
                "as": "asset",
            }
        },
        # Unwind asset array (should have exactly one element)
        {"$unwind": "$asset"},
        # Group by asset type and calculate totals
        {
            "$group": {
                "_id": "$asset.asset_type",
                "total_value": {"$sum": "$transaction_amount"},
                "transaction_count": {"$sum": 1},
                "unique_assets": {"$addToSet": "$asset_id"},
            }
        },
        # Calculate unique asset count per type
        {"$addFields": {"unique_assets": {"$size": "$unique_assets"}}},
        # Sort by total value descending
        {"$sort": {"total_value": -1}},
    ]

    asset_type_stats = list(db.transactions.aggregate(pipeline))

    if not asset_type_stats:
        return UserAssetStatistics(
            total_portfolio_value=0.0,
            asset_type_breakdown=[],
            total_transactions=0,
            unique_assets=0,
        )

    # Calculate total portfolio value
    total_portfolio_value = sum(stat["total_value"] for stat in asset_type_stats)

    # Calculate total transactions and unique assets
    total_transactions = sum(stat["transaction_count"] for stat in asset_type_stats)
    all_unique_assets = set()
    for stat in asset_type_stats:
        # Get unique assets for this type
        unique_assets_pipeline = [
            {"$match": {"wallet_id": {"$in": wallet_ids}}},
            {
                "$lookup": {
                    "from": "assets",
                    "localField": "asset_id",
                    "foreignField": "_id",
                    "as": "asset",
                }
            },
            {"$unwind": "$asset"},
            {"$match": {"asset.asset_type": stat["_id"]}},
            {"$group": {"_id": "$asset_id"}},
        ]
        unique_assets = list(db.transactions.aggregate(unique_assets_pipeline))
        all_unique_assets.update(asset["_id"] for asset in unique_assets)

    # Build asset type breakdown with percentages
    asset_type_breakdown = []
    for stat in asset_type_stats:
        asset_type = stat["_id"]
        percentage = (
            (stat["total_value"] / total_portfolio_value * 100)
            if total_portfolio_value > 0
            else 0.0
        )

        asset_type_breakdown.append(
            AssetTypePercentage(
                asset_type=asset_type,
                percentage=round(percentage, 2),
                total_value=round(stat["total_value"], 2),
                transaction_count=stat["transaction_count"],
            )
        )

    return UserAssetStatistics(
        total_portfolio_value=round(total_portfolio_value, 2),
        asset_type_breakdown=asset_type_breakdown,
        total_transactions=total_transactions,
        unique_assets=len(all_unique_assets),
    )
