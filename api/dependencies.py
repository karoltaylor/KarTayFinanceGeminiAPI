"""Shared dependencies for API endpoints."""

from typing import Optional, Dict, Any
from fastapi import Depends, Header, HTTPException
from bson import ObjectId
from pymongo.database import Database

from src.config.mongodb import get_db
from src.auth.firebase_auth import verify_firebase_token, get_current_user_from_token


async def get_current_user(
    firebase_user: Dict[str, Any] = Depends(verify_firebase_token),
) -> ObjectId:
    """
    Get current user from Firebase token.

    **Required Authentication:**
    Send Firebase ID token in Authorization header:
    ```
    Authorization: Bearer <firebase_id_token>
    ```

    The Firebase token is verified and user is auto-registered on first use.
    """
    # Get user from Firebase token
    return await get_current_user_from_token(firebase_user)
