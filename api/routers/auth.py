"""Authentication endpoints for user registration and login."""

from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import MongoDBConfig, get_db
from src.models.mongodb_models import User
from src.auth.firebase_auth import get_current_user_from_token

router = APIRouter(prefix="/api/users", tags=["Authentication"])


# ==============================================================================
# REQUEST/RESPONSE MODELS
# ==============================================================================


class UserRegister(BaseModel):
    """User registration request for OAuth providers (Google, Meta, etc.)."""

    email: str = Field(..., description="User email from OAuth provider", min_length=3, max_length=255)
    username: str = Field(
        ...,
        description="Username (can be derived from email)",
        min_length=3,
        max_length=50,
    )
    full_name: Optional[str] = Field(None, description="User's full name", max_length=200)
    oauth_provider: Optional[str] = Field(None, description="OAuth provider (google, meta, etc.)", max_length=50)
    oauth_id: Optional[str] = Field(None, description="Unique ID from OAuth provider", max_length=255)


# ==============================================================================
# ENDPOINTS
# ==============================================================================


@router.post("/register", summary="Register/Login with OAuth")
async def register_user(user_data: UserRegister, db: Database = Depends(get_db)):
    """
    Register or login a user after OAuth authentication (Google, Meta, etc.).

    **OAuth Flow:**
    1. User authenticates with OAuth provider on your frontend
    2. Frontend receives OAuth token and user information
    3. Frontend calls this endpoint with user data
    4. Backend creates new user or returns existing user's ID

    **Authentication:** This endpoint does NOT require Firebase token (it generates the user_id).

    **Request Body:**
    - `email` (required): User email from OAuth provider
    - `username` (required): Username (can be derived from email)
    - `full_name` (optional): Full name from OAuth profile
    - `oauth_provider` (optional): OAuth provider name (e.g., "google", "meta")
    - `oauth_id` (optional): User ID from OAuth provider

    **Returns:**
    - `user_id`: Use this in Firebase token for subsequent requests
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
            existing_user = db.users.find_one(
                {
                    "oauth_provider": user_data.oauth_provider,
                    "oauth_id": user_data.oauth_id,
                }
            )

        if not existing_user:
            existing_user = db.users.find_one({"email": normalized_email})

        if existing_user:
            # User exists - update OAuth info if provided
            if user_data.oauth_id and user_data.oauth_provider:
                db.users.update_one(
                    {"_id": existing_user["_id"]},
                    {
                        "$set": {
                            "oauth_provider": user_data.oauth_provider,
                            "oauth_id": user_data.oauth_id,
                            "updated_at": datetime.now(UTC),
                        }
                    },
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
        sanitized_username = "".join(c if (c.isalnum() or c in "_-") else "_" for c in sanitized_username)

        # If username is still invalid, generate from email
        if not sanitized_username or len(sanitized_username) < 3:
            sanitized_username = user_data.email.split("@")[0].lower()
            sanitized_username = "".join(c if (c.isalnum() or c in "_-") else "_" for c in sanitized_username)

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

        user_dict = user.model_dump(by_alias=True, exclude={"id"}, mode="python")
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


@router.get("/me", summary="Get current user info", response_model=None)
async def get_current_user_info(
    user_id: ObjectId = Depends(get_current_user_from_token),
    db: Database = Depends(get_db),
):
    """
    Get information about the currently authenticated user.

    **Authentication Required:** Include Firebase ID token in Authorization header:
    `Authorization: Bearer <firebase_token>`

    **Returns:**
    - User information including which database they're stored in
    - Helpful for debugging which environment you're connected to

    **Errors:**
    - 401: Invalid or missing Firebase token
    - 404: User not found in current database
    """
    user = db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found in database '{MongoDBConfig.get_mongodb_database()}'",
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
            "connection": masked_url,
        },
    }
