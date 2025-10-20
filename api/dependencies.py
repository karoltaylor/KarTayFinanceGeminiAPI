"""Shared dependencies for API endpoints."""

from typing import Optional
from fastapi import Depends, Header, HTTPException
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import get_db
from src.auth.firebase_auth import verify_firebase_token, get_current_user_from_token


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
    # Verify Firebase token (if provided)
    firebase_user = await verify_firebase_token(authorization)
    
    # Get user from token or X-User-ID
    return await get_current_user_from_token(firebase_user, x_user_id, db)

