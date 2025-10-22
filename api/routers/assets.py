"""Asset management endpoints."""

from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
from pymongo.database import Database

from src.config.mongodb import get_db
from src.models import AssetType

router = APIRouter(prefix="/api/assets", tags=["Assets"])


@router.get("", summary="List assets")
async def list_assets(
    asset_type: Annotated[
        Optional[AssetType], Query(description="Filter by asset type")
    ] = None,
    limit: Annotated[
        int, Query(description="Maximum number of assets to return", ge=1, le=1000)
    ] = 100,
    skip: Annotated[int, Query(description="Number of assets to skip", ge=0)] = 0,
    db: Database = Depends(get_db),
):
    """
    List all assets, optionally filtered by type.

    **Authentication:** Not required (assets are shared across users).

    **Query Parameters:**
    - `asset_type`: Filter by asset type (bond, stock, crypto, etc.)
    - `limit`: Maximum number of assets to return (default: 100, max: 1000)
    - `skip`: Number of assets to skip for pagination (default: 0)

    **Returns:**
    - List of assets (optionally filtered)
    - Total count of assets returned
    - Applied filter
    """
    query = {}
    if asset_type:
        query["asset_type"] = asset_type.value

    assets = list(db.assets.find(query).skip(skip).limit(limit))

    # Convert ObjectId to string
    for asset in assets:
        asset["_id"] = str(asset["_id"])

    return {"assets": assets, "count": len(assets), "filter": query}
