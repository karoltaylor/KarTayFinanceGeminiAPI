"""Transaction management endpoints."""

import tempfile
import os
from pathlib import Path
from datetime import datetime, UTC
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Path as PathParam,
)
from typing import Annotated, Optional
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import get_db
from src.pipeline import DataPipeline
from src.utils.logger import logger
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


# ==============================================================================
# UPLOAD ENDPOINT
# ==============================================================================


@router.post("/upload", summary="Upload transaction file", response_model=None)
async def upload_transactions(
    file: UploadFile = File(..., description="Transaction file (CSV, TXT, XLS, XLSX)"),
    wallet_id: str = Form(..., description="ID of the wallet to add transactions to"),
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Upload and process a transaction file with AI-powered column mapping.

    **Authentication Required:** Include `X-User-ID` header with your user ID.

    **Complete Processing Pipeline:**
    1. Load file and detect header row
    2. AI-powered column mapping to TransactionRecord schema (using Google Gemini)
    3. Detect transaction types from file content
    4. Calculate missing values (asset price, transaction amount, fees)
    5. Determine asset types automatically
    6. Validate all data
        7. Create/find wallet and assets in MongoDB
    8. Save all transactions to MongoDB

    **Supported File Formats:**
    - CSV (.csv, .txt)
    - Excel 2007+ (.xlsx)
    - Excel 97-2003 (.xls)

    **Form Data:**
    - `file`: Transaction file to upload
    - `wallet_id`: ID of the wallet to add transactions to (must exist)

    **Returns:**
    - Processing status and summary statistics
    - **Complete list of all transactions** with all columns:
        - Transaction ID, wallet name, asset name
        - Date, type (detected from file), volume, item price
        - Transaction amount, currency, fee
        - Asset type (determined automatically) and notes
    - Number of assets created
    - Processing timestamp

    **Errors:**
    - 400: Unsupported file type
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found
    - 422: No valid transactions in file
    - 500: Processing error
    """
    # Validate wallet_id and check ownership
    try:
        wallet_obj_id = ObjectId(wallet_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wallet_id format")

    wallet = db.wallets.find_one(
        {"_id": wallet_obj_id, "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
    )
    if not wallet:
        raise HTTPException(
            status_code=404, detail="Wallet not found or you don't have access to it"
        )

    # Log transaction upload start
    logger.info(
        "transaction_upload",
        "Transaction upload started",
        user_id=str(user_id),
        context={
            "wallet_id": wallet_id,
            "wallet_name": wallet["name"],
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": file.size if hasattr(file, "size") else "unknown",
        },
    )

    temp_file = None

    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in [".csv", ".txt", ".xls", ".xlsx"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. "
                f"Supported: .csv, .txt, .xls, .xlsx",
            )

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_extension
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_filepath = temp_file.name

        # Initialize pipeline with database for caching
        pipeline = DataPipeline(db=db, user_id=user_id)

        # Process file to Transaction models (returns transactions and errors)
        transactions, error_records = pipeline.process_file_to_transactions(
            filepath=temp_filepath,
            wallet_id=wallet_obj_id,
            user_id=user_id,
            wallets_collection=db.wallets,
            assets_collection=db.assets,
        )

        # Insert successful transactions into MongoDB
        inserted_count = 0
        if transactions:
            transaction_dicts = [
                t.model_dump(by_alias=True, exclude={"id"}, mode="python")
                for t in transactions
            ]
            result = db.transactions.insert_many(transaction_dicts)
            inserted_count = len(result.inserted_ids)

        # Insert error records into transaction_errors collection
        errors_count = 0
        if error_records:
            from src.models.mongodb_models import TransactionError

            error_docs = []
            for error_rec in error_records:
                error_doc = TransactionError(
                    user_id=user_id,
                    wallet_name=wallet["name"],
                    filename=file.filename,
                    row_index=error_rec["row_index"],
                    raw_data=error_rec["raw_data"],
                    error_message=error_rec["error_message"],
                    error_type=error_rec["error_type"],
                    transaction_type="unknown",  # Will be determined from file content
                    asset_type="unknown",  # Will be determined automatically
                )
                error_docs.append(error_doc.model_dump(by_alias=True, mode="python"))

            db.transaction_errors.insert_many(error_docs)
            errors_count = len(error_docs)

        # Check if we have any successful transactions
        if inserted_count == 0 and errors_count == 0:
            raise HTTPException(
                status_code=422,
                detail="No valid transactions could be created from the file. "
                "Check file format and data quality.",
            )

        # Get statistics
        asset_count = len(pipeline.transaction_mapper._asset_cache)

        # Log transaction upload results
        logger.info(
            "transaction_upload",
            "Transaction upload completed",
            user_id=str(user_id),
            context={
                "wallet_id": wallet_id,
                "wallet_name": wallet["name"],
                "filename": file.filename,
                "successful_transactions": inserted_count,
                "failed_transactions": errors_count,
                "assets_created": asset_count,
            },
        )

        # Fetch full transaction details with asset and wallet names
        transaction_details = []
        if transactions and inserted_count > 0:
            # Batch fetch all unique assets and wallets to avoid N+1 queries
            unique_asset_ids = list(set(t.asset_id for t in transactions))
            unique_wallet_ids = list(set(t.wallet_id for t in transactions))

            # Fetch all assets and wallets in one query each
            assets_cursor = db.assets.find({"_id": {"$in": unique_asset_ids}})
            wallets_cursor = db.wallets.find({"_id": {"$in": unique_wallet_ids}})

            # Build lookup dictionaries
            assets_dict = {asset["_id"]: asset for asset in assets_cursor}
            wallets_dict = {wallet["_id"]: wallet for wallet in wallets_cursor}

            for transaction, inserted_id in zip(transactions, result.inserted_ids):
                # Get asset and wallet from cached dictionaries
                asset = assets_dict.get(transaction.asset_id)
                wallet = wallets_dict.get(transaction.wallet_id)

                transaction_details.append(
                    {
                        "id": str(inserted_id),
                        "wallet_id": str(transaction.wallet_id),
                        "wallet_name": wallet["name"] if wallet else "Unknown",
                        "asset_id": str(transaction.asset_id),
                        "asset_name": asset["asset_name"] if asset else "Unknown",
                        "asset_type": asset["asset_type"] if asset else "unknown",
                        "date": transaction.date.isoformat(),
                        "transaction_type": transaction.transaction_type.value,
                        "volume": transaction.volume,
                        "item_price": transaction.item_price,
                        "transaction_amount": transaction.transaction_amount,
                        "currency": transaction.currency,
                        "fee": transaction.fee,
                        "notes": transaction.notes,
                        "created_at": transaction.created_at.isoformat(),
                    }
                )

        return {
            "status": "success" if inserted_count > 0 else "partial_failure",
            "message": f"Processed {inserted_count} transactions successfully, {errors_count} failed",
            "data": {
                "filename": file.filename,
                "wallet_id": wallet_id,
                "wallet_name": wallet["name"],
                "summary": {
                    "total_transactions": inserted_count,
                    "failed_transactions": errors_count,
                    "assets_created": asset_count,
                    "processed_at": datetime.now(UTC).isoformat(),
                },
                "transactions": transaction_details,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log transaction upload error
        logger.error(
            "transaction_upload",
            "Transaction upload failed",
            user_id=str(user_id),
            context={"wallet_id": wallet_id, "filename": file.filename},
            error=e,
        )
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_filepath):
            os.unlink(temp_filepath)


# ==============================================================================
# LIST ENDPOINT
# ==============================================================================


@router.get("", summary="List transactions", response_model=None)
async def list_transactions(
    wallet_id: Annotated[str, Query(description="Filter by wallet ID")],
    limit: Annotated[
        int,
        Query(description="Maximum number of transactions to return", ge=1, le=1000),
    ] = 100,
    skip: Annotated[int, Query(description="Number of transactions to skip", ge=0)] = 0,
    db: Database = Depends(get_db),
    user_id: ObjectId = Depends(get_current_user),
):
    """
    List transactions for a specific wallet with pagination.

    **Authentication Required:** Include `X-User-ID` header with your user ID.

    **Query Parameters:**
    - `wallet_id` (required): Filter by wallet ID
    - `limit`: Maximum number of transactions to return (default: 100, max: 1000)
    - `skip`: Number of transactions to skip for pagination (default: 0)

    **Returns:**
    - List of transactions with all details
    - Pagination information (limit, skip, has_next, has_prev)

    **Errors:**
    - 400: Invalid wallet_id format
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found
    """
    # Validate wallet_id and ownership
    try:
        wallet_obj_id = ObjectId(wallet_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wallet_id format")

    # Verify wallet exists and belongs to user - handle both ObjectId and string formats
    wallet = db.wallets.find_one(
        {"_id": wallet_obj_id, "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Query transactions - handle both ObjectId and string formats
    transactions = list(
        db.transactions.find(
            {"$or": [{"wallet_id": wallet_obj_id}, {"wallet_id": wallet_id}]}
        )
        .sort("date", -1)
        .skip(skip)
        .limit(limit + 1)  # Fetch one extra to check if there are more
    )

    # Check if there are more results
    has_next = len(transactions) > limit
    if has_next:
        transactions = transactions[:limit]

    has_prev = skip > 0

    # Enrich transactions with asset and wallet names
    for transaction in transactions:
        transaction["_id"] = str(transaction["_id"])
        transaction["wallet_id"] = str(transaction["wallet_id"])
        transaction["asset_id"] = str(transaction["asset_id"])

        # Get asset details
        asset = db.assets.find_one({"_id": ObjectId(transaction["asset_id"])})
        if asset:
            transaction["asset_name"] = asset.get("asset_name", "Unknown")
            transaction["asset_type"] = asset.get("asset_type", "unknown")
        else:
            transaction["asset_name"] = "Unknown"
            transaction["asset_type"] = "unknown"

        # Add wallet name
        transaction["wallet_name"] = wallet["name"]

        # Convert date to ISO format
        if "date" in transaction:
            transaction["date"] = transaction["date"].isoformat()
        if "created_at" in transaction:
            transaction["created_at"] = transaction["created_at"].isoformat()

    return {
        "transactions": transactions,
        "count": len(transactions),
        "limit": limit,
        "skip": skip,
        "has_next": has_next,
        "has_prev": has_prev,
    }


# ==============================================================================
# ERRORS ENDPOINT
# ==============================================================================


@router.get("/errors", summary="List transaction errors", response_model=None)
async def list_transaction_errors(
    wallet_id: Annotated[
        Optional[str], Query(description="Filter by wallet ID")
    ] = None,
    resolved: Annotated[
        Optional[bool], Query(description="Filter by resolved status")
    ] = None,
    limit: Annotated[
        int, Query(description="Maximum errors to return", ge=1, le=1000)
    ] = 100,
    skip: Annotated[int, Query(description="Number of errors to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    List transaction errors for manual correction.

    **Authentication Required:** Include `X-User-ID` header with your user ID.

    **Query Parameters:**
    - `wallet_id`: Filter by specific wallet ID (optional)
    - `resolved`: Filter by resolved status (optional)
    - `limit`: Maximum number of errors to return (default: 100, max: 1000)
    - `skip`: Number of errors to skip for pagination (default: 0)

    **Returns:**
    - List of transaction errors with details
    - Total count of errors returned
    - Each error includes: row index, raw data, error message, error type

    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found
    """
    query = {"user_id": user_id}

    if wallet_id:
        # Validate wallet exists and belongs to user
        try:
            wallet_obj_id = ObjectId(wallet_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid wallet_id format")

        wallet = db.wallets.find_one({"_id": wallet_obj_id, "user_id": user_id})
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        query["wallet_name"] = wallet[
            "name"
        ]  # Still filter by name in errors collection for now

    if resolved is not None:
        query["resolved"] = resolved

    errors = list(
        db.transaction_errors.find(query).sort("created_at", -1).skip(skip).limit(limit)
    )

    # Convert ObjectIds to strings
    for error in errors:
        error["_id"] = str(error["_id"])
        error["user_id"] = str(error["user_id"])

    return {"status": "success", "count": len(errors), "errors": errors}


# ==============================================================================
# DELETE ENDPOINT
# ==============================================================================


@router.delete(
    "/wallet/{wallet_id}", summary="Delete wallet transactions", response_model=None
)
async def delete_wallet_transactions(
    wallet_id: Annotated[str, PathParam(description="ID of the wallet")],
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Delete all transactions for a specific wallet.

    **Authentication Required:** Include `X-User-ID` header with your user ID.

    **Path Parameters:**
    - `wallet_id`: ID of the wallet whose transactions to delete

    **Returns:**
    - Status message
    - Number of transactions deleted

    **Errors:**
    - 400: Invalid wallet_id format
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found or not owned by user
    """
    # Validate wallet_id format
    try:
        wallet_obj_id = ObjectId(wallet_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid wallet_id format")

    # Find wallet (must belong to the user)
    wallet = db.wallets.find_one(
        {"_id": wallet_obj_id, "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
    )
    if not wallet:
        raise HTTPException(
            status_code=404, detail="Wallet not found or not owned by user"
        )

    # Delete transactions - handle both ObjectId and string formats
    result = db.transactions.delete_many(
        {"$or": [{"wallet_id": wallet_obj_id}, {"wallet_id": wallet_id}]}
    )

    return {
        "status": "success",
        "message": f"Deleted {result.deleted_count} transactions",
        "wallet_id": wallet_id,
        "wallet_name": wallet["name"],
        "deleted_count": result.deleted_count,
    }
