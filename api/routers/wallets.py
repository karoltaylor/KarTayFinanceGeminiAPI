"""Wallet management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Path as PathParam
from pydantic import BaseModel, Field
from typing import Annotated, Optional
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import get_db
from src.models.mongodb_models import Wallet
from src.auth.firebase_auth import get_current_user_from_token

router = APIRouter(prefix="/api/wallets", tags=["Wallets"])


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================


class WalletCreate(BaseModel):
    """Request model for creating a wallet."""

    name: str = Field(..., min_length=1, max_length=200, description="Wallet name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Wallet description"
    )


# ==============================================================================
# ENDPOINTS
# ==============================================================================


@router.get("", summary="List user's wallets", response_model=None)
async def list_wallets(
    limit: Annotated[
        int, Query(description="Maximum number of wallets to return", ge=1, le=1000)
    ] = 100,
    skip: Annotated[int, Query(description="Number of wallets to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    List all wallets for the authenticated user.

    **Authentication Required:** Include Firebase ID token in Authorization header:
    `Authorization: Bearer <firebase_token>`

    **Query Parameters:**
    - `limit`: Maximum number of wallets to return (default: 100, max: 1000)
    - `skip`: Number of wallets to skip for pagination (default: 0)

    **Returns:**
    - List of wallets belonging to the authenticated user
    - Total count of wallets returned

    **Errors:**
    - 401: Invalid or missing Firebase token
    """
    # Query for wallets - support both ObjectId and string formats for backwards compatibility
    wallets = list(
        db.wallets.find({"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]})
        .skip(skip)
        .limit(limit)
    )

    # Convert ObjectId to string for JSON serialization
    for wallet in wallets:
        wallet["_id"] = str(wallet["_id"])
        if isinstance(wallet.get("user_id"), ObjectId):
            wallet["user_id"] = str(wallet["user_id"])

    return {"wallets": wallets, "count": len(wallets)}


@router.post("", summary="Create a wallet", response_model=None)
async def create_wallet(
    wallet_data: WalletCreate,
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Create a new wallet for the authenticated user.

    **Authentication Required:** Include Firebase ID token in Authorization header:
    `Authorization: Bearer <firebase_token>`

    **Request Body:**
    - `name` (required): Wallet name (1-200 characters)
    - `description` (optional): Wallet description (max 1000 characters)

    **Returns:**
    - Created wallet information including wallet ID

    **Errors:**
    - 401: Invalid or missing Firebase token
    - 409: Wallet with this name already exists for the user
    """
    try:
        # Check if wallet with same name already exists for this user
        existing_wallet = db.wallets.find_one(
            {
                "$or": [{"user_id": user_id}, {"user_id": str(user_id)}],
                "name": wallet_data.name,
            }
        )
        if existing_wallet:
            raise HTTPException(
                status_code=409,
                detail=f"Wallet with name '{wallet_data.name}' already exists for this user",
            )

        # Create wallet
        wallet = Wallet(
            user_id=user_id,
            name=wallet_data.name,
            description=wallet_data.description,
        )

        # Insert wallet into MongoDB (use mode='python' to keep ObjectId type)
        wallet_dict = wallet.model_dump(by_alias=True, exclude={"id"}, mode="python")
        result = db.wallets.insert_one(wallet_dict)

        # Get the created wallet
        created_wallet = db.wallets.find_one({"_id": result.inserted_id})
        created_wallet["_id"] = str(created_wallet["_id"])
        created_wallet["user_id"] = str(created_wallet["user_id"])

        return {
            "status": "success",
            "message": f"Wallet '{wallet_data.name}' created successfully",
            "data": created_wallet,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating wallet: {str(e)}")


@router.delete("/{wallet_id}", summary="Delete a wallet", response_model=None)
async def delete_wallet(
    wallet_id: Annotated[str, PathParam(description="Wallet ID to delete")],
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Delete a wallet and all its associated transactions.

    **Authentication Required:** Include Firebase ID token in Authorization header:
    `Authorization: Bearer <firebase_token>`

    **Path Parameters:**
    - `wallet_id`: MongoDB ObjectId of the wallet to delete

    **Returns:**
    - Success message with deletion details
    - Number of transactions deleted

    **Errors:**
    - 400: Invalid wallet ID format
    - 401: Invalid or missing Firebase token
    - 404: Wallet not found or not owned by user
    """
    try:
        # Validate wallet_id format
        try:
            wallet_obj_id = ObjectId(wallet_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid wallet ID format")

        # Find wallet (must belong to the user)
        wallet = db.wallets.find_one(
            {
                "_id": wallet_obj_id,
                "$or": [{"user_id": user_id}, {"user_id": str(user_id)}],
            }
        )
        if not wallet:
            raise HTTPException(
                status_code=404, detail="Wallet not found or not owned by user"
            )

        # Count and delete transactions associated with this wallet
        transaction_count = db.transactions.count_documents(
            {"wallet_id": wallet_obj_id}
        )
        if transaction_count > 0:
            db.transactions.delete_many({"wallet_id": wallet_obj_id})

        # Delete the wallet
        db.wallets.delete_one({"_id": wallet_obj_id})

        return {
            "status": "success",
            "message": f"Wallet '{wallet['name']}' deleted successfully",
            "wallet_name": wallet["name"],
            "transactions_deleted": transaction_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting wallet: {str(e)}")
