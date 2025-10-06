"""FastAPI application for financial transaction processing."""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Query, Body, Path as PathParam
from fastapi.responses import JSONResponse
from typing import Optional, Annotated
from pathlib import Path
from pydantic import BaseModel, Field
import tempfile
import os
from datetime import datetime
from contextlib import asynccontextmanager
from bson import ObjectId

from src.pipeline import DataPipeline
from src.models import TransactionType, AssetType
from src.models.mongodb_models import Wallet, User
from src.config.mongodb import MongoDBConfig, get_db
from pymongo.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    try:
        MongoDBConfig.initialize_collections()
        print("[OK] MongoDB connected and initialized")
    except Exception as e:
        print(f"Warning: MongoDB initialization failed: {e}")
    
    yield
    
    # Shutdown
    MongoDBConfig.close_connection()
    print("[OK] MongoDB connection closed")


# Pydantic models for API requests
class UserRegister(BaseModel):
    """User registration request for OAuth providers (Google, Meta, etc.)."""
    email: str
    username: str
    full_name: Optional[str] = None
    oauth_provider: Optional[str] = None  # e.g., "google", "meta", "github"
    oauth_id: Optional[str] = None  # Provider's user ID


def get_current_user(
    user_id: Annotated[str, Header(
        alias="X-User-ID",
        description="User ID obtained from OAuth login/registration"
    )],
    db: Database = Depends(get_db)
) -> ObjectId:
    """
    Get current user from X-User-ID header.
    
    The user_id is obtained after OAuth authentication via /api/users/register endpoint.
    For production, replace this with JWT token authentication.
    """
    try:
        user_obj_id = ObjectId(user_id)
        user = db.users.find_one({"_id": user_obj_id, "is_active": True})
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user_obj_id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid user ID: {str(e)}")


# Initialize FastAPI app
app = FastAPI(
    title="Financial Transaction API",
    description="API for processing financial transaction files and storing in MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow frontend connections
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://localhost:4200",      # Angular default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers including X-User-ID
)


@app.get("/", summary="API Information", tags=["System"])
async def root():
    """
    Get API information and available endpoints.
    
    **Returns:**
    - API name, version, and status
    - Authentication method
    - List of available endpoints
    """
    return {
        "name": "Financial Transaction API",
        "version": "1.0.0",
        "status": "running",
        "authentication": "OAuth2 (Google, Meta, etc.)",
        "endpoints": {
            "health": "/health",
            "user_register": "/api/users/register (POST) - After OAuth login",
            "transactions_upload": "/api/transactions/upload",
            "list_wallets": "/api/wallets (GET)",
            "create_wallet": "/api/wallets (POST)",
            "delete_wallet": "/api/wallets/{wallet_id} (DELETE)",
            "list_assets": "/api/assets (GET)",
            "list_transactions": "/api/transactions (GET)",
            "delete_wallet_transactions": "/api/transactions/wallet/{wallet_name} (DELETE)",
            "stats": "/api/stats",
        },
    }


@app.get("/health", summary="Health Check", tags=["System"])
async def health_check(db: Database = Depends(get_db)):
    """
    Check API and database health status.
    
    **Returns:**
    - API status (healthy/unhealthy)
    - MongoDB connection status
    - Database name
    
    **Status Codes:**
    - 200: All systems operational
    - 503: Service unavailable (MongoDB disconnected)
    """
    try:
        # Test MongoDB connection
        db.command("ping")
        return {
            "status": "healthy",
            "mongodb": "connected",
            "database": MongoDBConfig.MONGODB_DATABASE,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "mongodb": "disconnected", "error": str(e)},
        )


@app.post("/api/users/register", summary="Register/Login with OAuth", tags=["Authentication"])
async def register_user(user_data: UserRegister, db: Database = Depends(get_db)):
    """
    Register or login a user after OAuth authentication (Google, Meta, etc.).
    
    **OAuth Flow:**
    1. User authenticates with OAuth provider on your frontend
    2. Frontend receives OAuth token and user information
    3. Frontend calls this endpoint with user data
    4. Backend creates new user or returns existing user's ID
    
    **Authentication:** This endpoint does NOT require X-User-ID header (it generates the user_id).
    
    **Request Body:**
    - `email` (required): User email from OAuth provider
    - `username` (required): Username (can be derived from email)
    - `full_name` (optional): Full name from OAuth profile
    - `oauth_provider` (optional): OAuth provider name (e.g., "google", "meta")
    - `oauth_id` (optional): User ID from OAuth provider
    
    **Returns:**
    - `user_id`: Use this in X-User-ID header for subsequent requests
    - `is_new_user`: true if user was just created, false if existing user
    
    **Errors:**
    - 409: Username already taken (for new users)
    """
    try:
        # Check if user exists by email or oauth_id
        existing_user = None
        
        if user_data.oauth_id and user_data.oauth_provider:
            # First, try to find by OAuth ID and provider
            existing_user = db.users.find_one({
                "oauth_provider": user_data.oauth_provider,
                "oauth_id": user_data.oauth_id
            })
        
        if not existing_user:
            # Then try to find by email
            existing_user = db.users.find_one({"email": user_data.email})
        
        if existing_user:
            # User exists - update OAuth info if provided and return user_id
            if user_data.oauth_id and user_data.oauth_provider:
                db.users.update_one(
                    {"_id": existing_user["_id"]},
                    {
                        "$set": {
                            "oauth_provider": user_data.oauth_provider,
                            "oauth_id": user_data.oauth_id,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            return {
                "status": "success",
                "message": "User logged in successfully",
                "user_id": str(existing_user["_id"]),
                "username": existing_user["username"],
                "email": existing_user["email"],
                "is_new_user": False,
            }
        
        # Check if username is taken (for new users)
        if db.users.find_one({"username": user_data.username}):
            raise HTTPException(status_code=409, detail="Username already taken")
        
        # Create new user
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            oauth_provider=user_data.oauth_provider,
            oauth_id=user_data.oauth_id,
        )
        
        user_dict = user.model_dump(by_alias=True, exclude={"id"})
        result = db.users.insert_one(user_dict)
        
        return {
            "status": "success",
            "message": f"User '{user_data.username}' registered successfully",
            "user_id": str(result.inserted_id),
            "username": user_data.username,
            "email": user_data.email,
            "is_new_user": True,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")


@app.post("/api/transactions/upload", summary="Upload transaction file", tags=["Transactions"])
async def upload_transactions(
    file: UploadFile = File(..., description="Transaction file (CSV, TXT, XLS, XLSX)"),
    wallet_name: str = Form(..., description="Name of the wallet (creates if doesn't exist)"),
    transaction_type: TransactionType = Form(
        TransactionType.BUY, description="Type of transactions (buy, sell, etc.)"
    ),
    asset_type: AssetType = Form(AssetType.STOCK, description="Type of assets (stock, crypto, etc.)"),
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Upload and process a transaction file with AI-powered column mapping.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Complete Processing Pipeline:**
    1. Load file and detect header row
    2. AI-powered column mapping to TransactionRecord schema (using Google Gemini)
    3. Calculate missing values (asset price, transaction amount, fees)
    4. Validate all data
    5. Create/find wallet and assets in MongoDB
    6. Save all transactions to MongoDB
    
    **Supported File Formats:**
    - CSV (.csv, .txt)
    - Excel 2007+ (.xlsx)
    - Excel 97-2003 (.xls)
    
    **Form Data:**
    - `file`: Transaction file to upload
    - `wallet_name`: Wallet name (creates new wallet if doesn't exist)
    - `transaction_type`: Type of transactions (default: buy)
    - `asset_type`: Type of assets (default: stock)
    
    **Returns:**
    - Processing status
    - Total transactions saved
    - Number of wallets/assets created
    - Sample of transaction IDs
    - Processing timestamp
    
    **Errors:**
    - 400: Unsupported file type
    - 422: No valid transactions in file
    - 500: Processing error
    """
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

        # Initialize pipeline
        pipeline = DataPipeline()

        # Process file to Transaction models
        transactions = pipeline.process_file_to_transactions(
            filepath=temp_filepath,
            wallet_name=wallet_name,
            user_id=user_id,
            transaction_type=transaction_type,
            asset_type=asset_type,
            wallets_collection=db.wallets,
            assets_collection=db.assets,
        )

        if not transactions:
            raise HTTPException(
                status_code=422,
                detail="No valid transactions could be created from the file. "
                "Check file format and data quality.",
            )

        # Insert transactions into MongoDB
        transaction_dicts = [t.model_dump(by_alias=True) for t in transactions]
        result = db.transactions.insert_many(transaction_dicts)

        # Get statistics
        inserted_count = len(result.inserted_ids)

        # Get wallet and asset info
        wallet_count = len(pipeline.transaction_mapper._wallet_cache)
        asset_count = len(pipeline.transaction_mapper._asset_cache)

        return {
            "status": "success",
            "message": f"Successfully processed {inserted_count} transactions",
            "data": {
                "filename": file.filename,
                "wallet_name": wallet_name,
                "transaction_type": transaction_type.value,
                "asset_type": asset_type.value,
                "total_transactions": inserted_count,
                "wallets_created": wallet_count,
                "assets_created": asset_count,
                "inserted_ids": [str(id) for id in result.inserted_ids[:10]],
                "more_ids": (
                    len(result.inserted_ids) - 10
                    if len(result.inserted_ids) > 10
                    else 0
                ),
                "processed_at": datetime.utcnow().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_filepath):
            os.unlink(temp_filepath)


@app.get("/api/wallets", summary="List user's wallets", tags=["Wallets"])
async def list_wallets(
    limit: Annotated[int, Query(description="Maximum number of wallets to return", ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(description="Number of wallets to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    List all wallets for the authenticated user.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Query Parameters:**
    - `limit`: Maximum number of wallets to return (default: 100, max: 1000)
    - `skip`: Number of wallets to skip for pagination (default: 0)
    
    **Returns:**
    - List of wallets belonging to the authenticated user
    - Total count of wallets returned
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    """
    wallets = list(db.wallets.find({"user_id": user_id}).skip(skip).limit(limit))

    # Convert ObjectId to string
    for wallet in wallets:
        wallet["_id"] = str(wallet["_id"])
        wallet["user_id"] = str(wallet["user_id"])

    return {"wallets": wallets, "count": len(wallets)}


class WalletCreate(BaseModel):
    """Request model for creating a wallet."""
    name: str = Field(..., min_length=1, max_length=200, description="Wallet name")
    description: Optional[str] = Field(None, max_length=1000, description="Wallet description")


@app.post("/api/wallets", summary="Create a wallet", tags=["Wallets"])
async def create_wallet(
    wallet_data: WalletCreate,
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Create a new wallet for the authenticated user.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Request Body:**
    - `name` (required): Wallet name (1-200 characters)
    - `description` (optional): Wallet description (max 1000 characters)
    
    **Returns:**
    - Created wallet information including wallet ID
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 409: Wallet with this name already exists for the user
    """
    try:
        # Check if wallet with same name already exists for this user
        existing_wallet = db.wallets.find_one({"user_id": user_id, "name": wallet_data.name})
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
        wallet_dict = wallet.model_dump(by_alias=True, exclude={"id"}, mode='python')
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


@app.delete("/api/wallets/{wallet_id}", summary="Delete a wallet", tags=["Wallets"])
async def delete_wallet(
    wallet_id: Annotated[str, PathParam(description="Wallet ID to delete")],
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Delete a wallet and optionally its associated transactions.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Path Parameters:**
    - `wallet_id`: MongoDB ObjectId of the wallet to delete
    
    **Returns:**
    - Success message with deletion details
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found or not owned by user
    - 400: Invalid wallet ID format
    """
    try:
        # Validate wallet_id format
        try:
            wallet_obj_id = ObjectId(wallet_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid wallet ID format")
        
        # Find wallet (must belong to the user)
        wallet = db.wallets.find_one({"_id": wallet_obj_id, "user_id": user_id})
        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found or not owned by user"
            )
        
        # Count transactions associated with this wallet
        transaction_count = db.transactions.count_documents({"wallet_id": wallet_obj_id})
        
        # Delete all transactions for this wallet
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


@app.get("/api/assets", summary="List assets", tags=["Assets"])
async def list_assets(
    asset_type: Annotated[Optional[AssetType], Query(description="Filter by asset type")] = None,
    limit: Annotated[int, Query(description="Maximum number of assets to return", ge=1, le=1000)] = 100,
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


@app.get("/api/transactions", summary="List transactions", tags=["Transactions"])
async def list_transactions(
    wallet_name: Annotated[Optional[str], Query(description="Filter by wallet name")] = None,
    limit: Annotated[int, Query(description="Maximum number of transactions to return", ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(description="Number of transactions to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    List transactions for the authenticated user's wallets.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Query Parameters:**
    - `wallet_name`: Filter by specific wallet name (optional)
    - `limit`: Maximum number of transactions to return (default: 100, max: 1000)
    - `skip`: Number of transactions to skip for pagination (default: 0)
    
    **Returns:**
    - List of transactions from user's wallets
    - Total count of transactions returned
    - Applied filter
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    """
    query = {}

    # If wallet_name provided, find wallet_id first (must belong to user)
    if wallet_name:
        wallet = db.wallets.find_one({"name": wallet_name, "user_id": user_id})
        if wallet:
            query["wallet_id"] = wallet["_id"]
        else:
            return {"transactions": [], "count": 0, "message": "Wallet not found or not owned by user"}
    else:
        # Get all wallet IDs for this user
        user_wallets = list(db.wallets.find({"user_id": user_id}, {"_id": 1}))
        wallet_ids = [w["_id"] for w in user_wallets]
        query["wallet_id"] = {"$in": wallet_ids}

    transactions = list(db.transactions.find(query).skip(skip).limit(limit))

    # Convert ObjectId to string and transaction_type enum
    for trans in transactions:
        trans["_id"] = str(trans["_id"])
        trans["wallet_id"] = str(trans["wallet_id"])
        trans["asset_id"] = str(trans["asset_id"])
        if "transaction_type" in trans:
            trans["transaction_type"] = trans["transaction_type"].value

    return {"transactions": transactions, "count": len(transactions), "filter": query}


@app.delete("/api/transactions/wallet/{wallet_name}", summary="Delete wallet transactions", tags=["Transactions"])
async def delete_wallet_transactions(
    wallet_name: Annotated[str, PathParam(description="Name of the wallet")],
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Delete all transactions for a specific wallet.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Path Parameters:**
    - `wallet_name`: Name of the wallet whose transactions to delete
    
    **Returns:**
    - Status message
    - Number of transactions deleted
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found or not owned by user
    """
    # Find wallet (must belong to the user)
    wallet = db.wallets.find_one({"name": wallet_name, "user_id": user_id})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found or not owned by user")

    # Delete transactions
    result = db.transactions.delete_many({"wallet_id": wallet["_id"]})

    return {
        "status": "success",
        "message": f"Deleted {result.deleted_count} transactions",
        "wallet_name": wallet_name,
        "deleted_count": result.deleted_count,
    }


@app.get("/api/stats", summary="Get user statistics", tags=["Statistics"])
async def get_statistics(
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
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
    user_wallets = list(db.wallets.find({"user_id": user_id}, {"_id": 1}))
    wallet_ids = [w["_id"] for w in user_wallets]
    
    stats = {
        "total_wallets": len(wallet_ids),
        "total_assets": db.assets.count_documents({}),
        "total_transactions": db.transactions.count_documents({"wallet_id": {"$in": wallet_ids}}),
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
