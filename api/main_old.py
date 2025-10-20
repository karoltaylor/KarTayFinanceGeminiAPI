"""FastAPI application for financial transaction processing."""

# ==============================================================================
# IMPORTS
# ==============================================================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Query, Body, Path as PathParam, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import Optional, Annotated
from pathlib import Path
from pydantic import BaseModel, Field
import tempfile
import os
from datetime import datetime, UTC
from contextlib import asynccontextmanager
from bson import ObjectId

from src.pipeline import DataPipeline
from src.models import TransactionType, AssetType
from src.models.mongodb_models import Wallet, User
from src.config.mongodb import MongoDBConfig, get_db
from src.config.settings import Settings
from src.utils.logger import logger
from src.middleware.logging_middleware import LoggingMiddleware
from pymongo.database import Database
from src.auth.firebase_auth import get_current_user_from_token

# Import logging router
from api import logs


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================

class UserRegister(BaseModel):
    """User registration request for OAuth providers (Google, Meta, etc.)."""
    email: str = Field(..., description="User email from OAuth provider", min_length=3, max_length=255)
    username: str = Field(..., description="Username (can be derived from email)", min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, description="User's full name", max_length=200)
    oauth_provider: Optional[str] = Field(None, description="OAuth provider (google, meta, etc.)", max_length=50)
    oauth_id: Optional[str] = Field(None, description="Unique ID from OAuth provider", max_length=255)


class WalletCreate(BaseModel):
    """Request model for creating a wallet."""
    name: str = Field(..., min_length=1, max_length=200, description="Wallet name")
    description: Optional[str] = Field(None, max_length=1000, description="Wallet description")


# ==============================================================================
# LIFESPAN & STARTUP
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup
    print("[DEBUG] ========== FastAPI Lifespan Startup ==========")
    try:
        # Show connection info (mask credentials)
        print("[DEBUG] Retrieving MongoDB configuration...")
        db_url = MongoDBConfig.get_mongodb_url() or "Not set"
        
        if db_url and db_url != "Not set":
            if "@" in db_url:
                # Mask the password in the URL
                parts = db_url.split("@")
                creds = parts[0].split("://")[1].split(":")
                masked_url = f"mongodb+srv://{creds[0]}:***@{parts[1]}"
            else:
                masked_url = db_url[:30] + "..." if len(db_url) > 30 else db_url
        else:
            masked_url = "NOT SET (will fail)"
        
        print(f"[INFO] Connecting to: {masked_url}")
        print(f"[INFO] Database: {MongoDBConfig.get_mongodb_database()}")
        
        print("[DEBUG] Calling MongoDBConfig.initialize_collections()...")
        MongoDBConfig.initialize_collections()
        print("[OK] MongoDB connected and initialized")
    except Exception as e:
        print(f"[ERROR] MongoDB initialization failed!")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
        print("[WARNING] Continuing without MongoDB connection...")
    
    print("[DEBUG] ===============================================")
    
    yield
    
    # Shutdown
    print("[DEBUG] ========== FastAPI Lifespan Shutdown ==========")
    MongoDBConfig.close_connection()
    print("[OK] MongoDB connection closed")
    print("[DEBUG] ================================================")


# ==============================================================================
# DEPENDENCIES
# ==============================================================================

async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Database = Depends(get_db)
) -> ObjectId:
    """
    Get current user from Firebase token OR X-User-ID header (backward compatible).
    
    **Preferred Method (Secure):**
    Send Firebase ID token in Authorization header:
    ```
    Authorization: Bearer <firebase_id_token>
    ```
    
    **Legacy Method (Backward Compatible):**
    Send X-User-ID header:
    ```
    X-User-ID: <user_id>
    ```
    
    The Firebase token is verified and user is auto-registered on first use.
    X-User-ID is supported for backward compatibility during migration.
    """
    from src.auth.firebase_auth import verify_firebase_token, get_current_user_from_token
    
    # Verify Firebase token (if provided)
    firebase_user = await verify_firebase_token(authorization)
    
    # Get user from token or X-User-ID
    return await get_current_user_from_token(firebase_user, x_user_id, db)


# ==============================================================================
# APP INITIALIZATION
# ==============================================================================

app = FastAPI(
    title="Financial Transaction API",
    description="API for processing financial transaction files and storing in MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - environment-specific allowed origins
cors_origins = Settings.get_cors_origins()
print(f"[INFO] CORS allowed origins: {', '.join(cors_origins)}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",               # For JSON request bodies
        "Accept",                     # For response content negotiation
        "X-User-ID",                  # Custom auth header
        "Authorization",              # For future OAuth token support
    ],
)

# Trusted Host middleware - prevent host header attacks
if Settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=Settings.ALLOWED_HOSTS
    )

# Logging middleware - log all requests and responses
app.add_middleware(
    LoggingMiddleware,
    log_requests=True,
    log_responses=True
)


# HTTPS Enforcement Middleware
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    """
    Enforce HTTPS in production.
    
    - In development (ENFORCE_HTTPS=false): Allows HTTP
    - In production (ENFORCE_HTTPS=true): Redirects HTTP to HTTPS
    """
    if Settings.ENFORCE_HTTPS:
        # Check if request is using HTTPS
        if request.url.scheme != "https":
            # Redirect to HTTPS version
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(https_url, status_code=301)
    
    response = await call_next(request)
    
    # Add security headers to all responses
    if Settings.ENFORCE_HTTPS:
        # Strict Transport Security - force HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Security headers (always applied)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response


# ==============================================================================
# ROUTERS
# ==============================================================================

# Include logging router
app.include_router(logs.router)


# ==============================================================================
# SYSTEM ENDPOINTS
# ==============================================================================

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
            "user_register": "/api/users/register (POST)",
            "list_wallets": "/api/wallets (GET)",
            "create_wallet": "/api/wallets (POST)",
            "delete_wallet": "/api/wallets/{wallet_id} (DELETE)",
            "list_assets": "/api/assets (GET)",
            "list_transactions": "/api/transactions (GET)",
            "upload_transactions": "/api/transactions/upload (POST)",
            "delete_wallet_transactions": "/api/transactions/wallet/{wallet_name} (DELETE)",
            "stats": "/api/stats (GET)",
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
        db.command("ping")
        return {
            "status": "healthy",
            "mongodb": "connected",
            "database": MongoDBConfig.get_mongodb_database(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "mongodb": "disconnected", "error": str(e)},
        )


# ==============================================================================
# AUTHENTICATION ENDPOINTS
# ==============================================================================

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
        # Normalize email for consistent lookups
        normalized_email = user_data.email.strip().lower()
        
        # Check if user exists by email or oauth_id
        existing_user = None
        
        if user_data.oauth_id and user_data.oauth_provider:
            existing_user = db.users.find_one({
                "oauth_provider": user_data.oauth_provider,
                "oauth_id": user_data.oauth_id
            })
        
        if not existing_user:
            existing_user = db.users.find_one({"email": normalized_email})
        
        if existing_user:
            # User exists - update OAuth info if provided
            if user_data.oauth_id and user_data.oauth_provider:
                db.users.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": {
                        "oauth_provider": user_data.oauth_provider,
                        "oauth_id": user_data.oauth_id,
                        "updated_at": datetime.now(UTC)
                    }}
                )
            
            return {
                "status": "success",
                "message": "User logged in successfully",
                "user_id": str(existing_user["_id"]),
                "username": existing_user["username"],
                "email": existing_user["email"],
                "is_new_user": False,
            }
        
        # Sanitize username - replace spaces and invalid chars with underscores
        sanitized_username = user_data.username.strip().lower()
        sanitized_username = "".join(
            c if (c.isalnum() or c in "_-") else "_" 
            for c in sanitized_username
        )
        
        # If username is still invalid, generate from email
        if not sanitized_username or len(sanitized_username) < 3:
            sanitized_username = user_data.email.split("@")[0].lower()
            sanitized_username = "".join(
                c if (c.isalnum() or c in "_-") else "_" 
                for c in sanitized_username
            )
        
        # Check if username is taken, add suffix if needed
        base_username = sanitized_username
        counter = 1
        while db.users.find_one({"username": sanitized_username}):
            sanitized_username = f"{base_username}_{counter}"
            counter += 1
        
        # Create new user
        user = User(
            email=normalized_email,
            username=sanitized_username,
            full_name=user_data.full_name,
            oauth_provider=user_data.oauth_provider,
            oauth_id=user_data.oauth_id,
        )
        
        user_dict = user.model_dump(by_alias=True, exclude={"id"})
        result = db.users.insert_one(user_dict)
        
        return {
            "status": "success",
            "message": f"User '{sanitized_username}' registered successfully",
            "user_id": str(result.inserted_id),
            "username": sanitized_username,
            "email": normalized_email,
            "is_new_user": True,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering user: {str(e)}")


@app.get("/api/users/me", summary="Get current user info", tags=["Authentication"], response_model=None)
async def get_current_user_info(
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Get information about the currently authenticated user.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Returns:**
    - User information including which database they're stored in
    - Helpful for debugging which environment you're connected to
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 404: User not found in current database
    """
    user = db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found in database '{MongoDBConfig.get_mongodb_database()}'"
        )
    
    # Mask sensitive connection info
    db_url = MongoDBConfig.get_mongodb_url() or "Not set"
    if "@" in db_url:
        parts = db_url.split("@")
        creds = parts[0].split("://")[1].split(":")
        masked_url = f"mongodb+srv://{creds[0]}:***@{parts[1]}"
    else:
        masked_url = db_url
    
    return {
        "user_id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "database": {
            "name": MongoDBConfig.get_mongodb_database(),
            "connection": masked_url
        }
    }


# ==============================================================================
# WALLET ENDPOINTS
# ==============================================================================

@app.get("/api/wallets", summary="List user's wallets", tags=["Wallets"], response_model=None)
async def list_wallets(
    limit: Annotated[int, Query(description="Maximum number of wallets to return", ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(description="Number of wallets to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user_from_token),
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
    # Query for wallets - support both ObjectId and string formats for backwards compatibility
    wallets = list(db.wallets.find({
        "$or": [
            {"user_id": user_id},
            {"user_id": str(user_id)}
        ]
    }).skip(skip).limit(limit))

    # Convert ObjectId to string for JSON serialization
    for wallet in wallets:
        wallet["_id"] = str(wallet["_id"])
        if isinstance(wallet.get("user_id"), ObjectId):
            wallet["user_id"] = str(wallet["user_id"])

    return {"wallets": wallets, "count": len(wallets)}


@app.post("/api/wallets", summary="Create a wallet", tags=["Wallets"], response_model=None)
async def create_wallet(
    wallet_data: WalletCreate,
    user_id: ObjectId = Depends(get_current_user_from_token),
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
        existing_wallet = db.wallets.find_one({
            "$or": [{"user_id": user_id}, {"user_id": str(user_id)}],
            "name": wallet_data.name
        })
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


@app.delete("/api/wallets/{wallet_id}", summary="Delete a wallet", tags=["Wallets"], response_model=None)
async def delete_wallet(
    wallet_id: Annotated[str, PathParam(description="Wallet ID to delete")],
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
):
    """
    Delete a wallet and all its associated transactions.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Path Parameters:**
    - `wallet_id`: MongoDB ObjectId of the wallet to delete
    
    **Returns:**
    - Success message with deletion details
    - Number of transactions deleted
    
    **Errors:**
    - 400: Invalid wallet ID format
    - 401: Invalid or missing X-User-ID header
    - 404: Wallet not found or not owned by user
    """
    try:
        # Validate wallet_id format
        try:
            wallet_obj_id = ObjectId(wallet_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid wallet ID format")
        
        # Find wallet (must belong to the user)
        wallet = db.wallets.find_one({
            "_id": wallet_obj_id,
            "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]
        })
        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found or not owned by user"
            )
        
        # Count and delete transactions associated with this wallet
        transaction_count = db.transactions.count_documents({"wallet_id": wallet_obj_id})
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


# ==============================================================================
# ASSET ENDPOINTS
# ==============================================================================

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


# ==============================================================================
# TRANSACTION ENDPOINTS
# ==============================================================================

@app.post("/api/transactions/upload", summary="Upload transaction file", tags=["Transactions"], response_model=None)
async def upload_transactions(
    file: UploadFile = File(..., description="Transaction file (CSV, TXT, XLS, XLSX)"),
    wallet_id: str = Form(..., description="ID of the wallet to add transactions to"),
    user_id: ObjectId = Depends(get_current_user_from_token),
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
    
    wallet = db.wallets.find_one({"_id": wallet_obj_id, "user_id": user_id})
    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"Wallet not found or you don't have access to it"
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
            "file_size": file.size if hasattr(file, 'size') else 'unknown'
        }
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
            transaction_dicts = [t.model_dump(by_alias=True) for t in transactions]
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
                    asset_type="unknown"  # Will be determined automatically
                )
                error_docs.append(error_doc.model_dump(by_alias=True))
            
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
                "assets_created": asset_count
            }
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
                
                transaction_details.append({
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
                })

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
            context={
                "wallet_id": wallet_id,
                "filename": file.filename
            },
            error=e
        )
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_filepath):
            os.unlink(temp_filepath)


@app.get("/api/transactions", summary="List transactions", tags=["Transactions"], response_model=None)
async def list_transactions(
    wallet_id: Annotated[str, Query(description="Filter by wallet ID")],
    limit: Annotated[int, Query(description="Maximum number of transactions to return", ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(description="Number of transactions to skip", ge=0)] = 0,
    db: Database = Depends(get_db),
    user_id: ObjectId = Depends(get_current_user_from_token),
):
    """
    List transactions for a specific wallet with pagination support.
    
    **Authentication Required:** Include `X-User-ID` header with your user ID.
    
    **Query Parameters:**
    - `wallet_id`: Wallet ID to filter transactions (required)
    - `limit`: Maximum number of transactions to return (default: 100, max: 1000)
    - `skip`: Number of transactions to skip for pagination (default: 0)
    
    **Returns:**
    - `transactions`: List of transactions from the specified wallet
    - `count`: Number of transactions in current page
    - `total_count`: Total number of transactions in the wallet
    - `total_pages`: Total number of pages available
    - `page`: Current page number (1-based)
    - `limit`: Number of transactions per page
    - `skip`: Number of transactions skipped
    - `has_next`: Whether there are more pages after current page
    - `has_prev`: Whether there are pages before current page
    
    **Errors:**
    - 401: Invalid or missing X-User-ID header
    - 422: Missing required wallet_id parameter
    """
    # Verify wallet belongs to user
    try:
        wallet_object_id = ObjectId(wallet_id)
    except Exception:
        return {"transactions": [], "count": 0, "message": "Invalid wallet ID format"}
    
    wallet = db.wallets.find_one({
        "_id": wallet_object_id,
        "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]
    })
    if wallet:
        # Include both ObjectId and string versions to handle data type mismatches
        query = {"wallet_id": {"$in": [wallet_object_id, wallet_id]}}
    else:
        return {"transactions": [], "count": 0, "message": "Wallet not found or not owned by user"}

    # Get total count for pagination
    total_count = db.transactions.count_documents(query)
    
    # Get transactions with pagination
    transactions = list(db.transactions.find(query).skip(skip).limit(limit))

    # Fetch asset and wallet details for all transactions
    asset_ids = set()
    wallet_ids = set()
    for trans in transactions:
        asset_ids.add(trans["asset_id"])
        wallet_ids.add(trans["wallet_id"])
    
    # Fetch all assets and wallets in bulk
    assets = {}
    if asset_ids:
        # Convert asset IDs to ObjectIds for lookup
        asset_object_ids = []
        asset_string_ids = []
        for asset_id in asset_ids:
            try:
                asset_object_ids.append(ObjectId(asset_id))
                asset_string_ids.append(str(asset_id))
            except:
                asset_string_ids.append(str(asset_id))
        
        # Query with both ObjectId and string versions
        asset_cursor = db.assets.find({
            "$or": [
                {"_id": {"$in": asset_object_ids}},
                {"_id": {"$in": asset_string_ids}}
            ]
        })
        for asset in asset_cursor:
            assets[str(asset["_id"])] = {
                "name": asset["asset_name"],
                "type": asset["asset_type"] if hasattr(asset["asset_type"], 'value') else str(asset["asset_type"]),
                "symbol": asset.get("symbol", "")
            }
    
    wallets = {}
    if wallet_ids:
        # Convert wallet IDs to ObjectIds for lookup
        wallet_object_ids = []
        wallet_string_ids = []
        for wallet_id in wallet_ids:
            try:
                wallet_object_ids.append(ObjectId(wallet_id))
                wallet_string_ids.append(str(wallet_id))
            except:
                wallet_string_ids.append(str(wallet_id))
        
        # Query with both ObjectId and string versions
        wallet_cursor = db.wallets.find({
            "$or": [
                {"_id": {"$in": wallet_object_ids}},
                {"_id": {"$in": wallet_string_ids}}
            ]
        })
        for wallet in wallet_cursor:
            wallets[str(wallet["_id"])] = {
                "name": wallet["name"]
            }

    # Enhance transactions with asset and wallet details
    enhanced_transactions = []
    for trans in transactions:
        asset_id = str(trans["asset_id"])
        wallet_id = str(trans["wallet_id"])
        
        # Get asset and wallet details
        asset_details = assets.get(asset_id, {"name": "Unknown", "type": "unknown", "symbol": ""})
        wallet_details = wallets.get(wallet_id, {"name": "Unknown"})
        
        # Create enhanced transaction record
        enhanced_trans = {
            "_id": str(trans["_id"]),
            "wallet_id": wallet_id,
            "wallet_name": wallet_details["name"],
            "asset_id": asset_id,
            "asset_name": asset_details["name"],
            "asset_type": asset_details["type"],
            "asset_symbol": asset_details["symbol"],
            "date": trans["date"].isoformat() if hasattr(trans["date"], 'isoformat') else str(trans["date"]),
            "transaction_type": trans["transaction_type"].value if hasattr(trans["transaction_type"], 'value') else str(trans["transaction_type"]),
            "volume": trans["volume"],
            "item_price": trans["item_price"],
            "transaction_amount": trans["transaction_amount"],
            "currency": trans["currency"],
            "fee": trans["fee"],
            "notes": trans.get("notes"),
            "created_at": trans["created_at"].isoformat() if hasattr(trans["created_at"], 'isoformat') else str(trans["created_at"]),
            "updated_at": trans["updated_at"].isoformat() if hasattr(trans["updated_at"], 'isoformat') else str(trans["updated_at"])
        }
        enhanced_transactions.append(enhanced_trans)

    # Convert ObjectIds in filter to strings for JSON serialization
    serializable_filter = {}
    for key, value in query.items():
        if key == "wallet_id" and isinstance(value, dict) and "$in" in value:
            # Convert ObjectId list to string list
            serializable_filter[key] = {"$in": [str(oid) for oid in value["$in"]]}
        elif hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
            serializable_filter[key] = str(value)
        else:
            serializable_filter[key] = value
    
    # Calculate pagination metadata
    current_page = (skip // limit) + 1
    total_pages = (total_count + limit - 1) // limit  # Ceiling division
    has_next = skip + limit < total_count
    has_prev = skip > 0
    
    return {
        "transactions": enhanced_transactions,
        "count": len(enhanced_transactions),
        "total_count": total_count,
        "total_pages": total_pages,
        "page": current_page,
        "limit": limit,
        "skip": skip,
        "has_next": has_next,
        "has_prev": has_prev
    }


@app.get("/api/transactions/errors", summary="List transaction errors", tags=["Transactions"], response_model=None)
async def list_transaction_errors(
    wallet_id: Annotated[Optional[str], Query(description="Filter by wallet ID")] = None,
    resolved: Annotated[Optional[bool], Query(description="Filter by resolved status")] = None,
    limit: Annotated[int, Query(description="Maximum errors to return", ge=1, le=1000)] = 100,
    skip: Annotated[int, Query(description="Number of errors to skip", ge=0)] = 0,
    user_id: ObjectId = Depends(get_current_user_from_token),
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
        
        query["wallet_name"] = wallet["name"]  # Still filter by name in errors collection for now
    
    if resolved is not None:
        query["resolved"] = resolved
    
    errors = list(db.transaction_errors.find(query).sort("created_at", -1).skip(skip).limit(limit))
    
    # Convert ObjectIds to strings
    for error in errors:
        error["_id"] = str(error["_id"])
        error["user_id"] = str(error["user_id"])
    
    return {
        "status": "success",
        "count": len(errors),
        "errors": errors
    }


@app.delete("/api/transactions/wallet/{wallet_id}", summary="Delete wallet transactions", tags=["Transactions"], response_model=None)
async def delete_wallet_transactions(
    wallet_id: Annotated[str, PathParam(description="ID of the wallet")],
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db)
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
    wallet = db.wallets.find_one({
        "_id": wallet_obj_id,
        "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]
    })
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found or not owned by user")

    # Delete transactions
    result = db.transactions.delete_many({"wallet_id": wallet_obj_id})

    return {
        "status": "success",
        "message": f"Deleted {result.deleted_count} transactions",
        "wallet_id": wallet_id,
        "wallet_name": wallet["name"],
        "deleted_count": result.deleted_count,
    }


# ==============================================================================
# STATISTICS ENDPOINTS
# ==============================================================================

@app.get("/api/stats", summary="Get user statistics", tags=["Statistics"], response_model=None)
async def get_statistics(
    user_id: ObjectId = Depends(get_current_user_from_token),
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
    user_wallets = list(db.wallets.find({
        "$or": [{"user_id": user_id}, {"user_id": str(user_id)}]
    }, {"_id": 1}))
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
