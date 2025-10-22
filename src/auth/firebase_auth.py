"""Firebase Authentication for FastAPI."""

import os
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from firebase_admin import auth, credentials, initialize_app
from bson import ObjectId

# Firebase initialization state
_firebase_initialized = False


def _initialize_firebase():
    """Initialize Firebase Admin SDK (only once)."""
    global _firebase_initialized

    if _firebase_initialized:
        return

    try:
        # Check if Firebase service account JSON file exists
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_path and os.path.exists(service_account_path):
            # Initialize with service account JSON file
            cred = credentials.Certificate(service_account_path)
            initialize_app(cred)
            print(
                f"[INFO] Firebase initialized with service account: {service_account_path}"
            )
        else:
            # Initialize with default credentials (for GCP/Cloud Run environments)
            # or use Application Default Credentials
            initialize_app()
            print("[INFO] Firebase initialized with default credentials")

        _firebase_initialized = True

    except ValueError as e:
        # Firebase app already initialized (safe to ignore)
        if "already exists" in str(e).lower():
            _firebase_initialized = True
            print("[INFO] Firebase already initialized")
        else:
            raise
    except Exception as e:
        print(f"[WARNING] Firebase initialization failed: {str(e)}")
        print("[WARNING] Firebase authentication will not be available")
        # Don't raise - allow API to start without Firebase in dev mode


async def verify_firebase_token(
    authorization: Optional[str] = Header(
        None, description="Bearer {firebase_id_token}"
    )
) -> Dict[str, Any]:
    """
    Verify Firebase ID token from Authorization header.

    Frontend sends: Authorization: Bearer <firebase_id_token>
    Backend verifies token and returns decoded user info.

    Raises HTTPException if no authorization header or invalid token.
    """
    # Authorization header is required
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide Authorization: Bearer <firebase_token>",
        )

    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use: Authorization: Bearer <token>",
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Authorization token is empty")

    # Initialize Firebase if not already done
    _initialize_firebase()

    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(token)

        # Token is valid - contains user info
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "firebase_token": decoded_token,
        }

    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Firebase token has expired")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Firebase token has been revoked")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired Firebase token")
    except Exception as e:
        print(f"[ERROR] Firebase token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_current_user_from_token(
    firebase_user: Dict[str, Any] = Depends(verify_firebase_token),
) -> ObjectId:
    """
    Get or create user from Firebase token.

    Args:
        firebase_user: Verified Firebase user data

    Returns:
        ObjectId: MongoDB _id of the user

    Raises:
        HTTPException: If user not found or creation fails
    """
    from src.models.mongodb_models import User
    from src.config.mongodb import MongoDBConfig

    # Get database connection
    db = MongoDBConfig.get_database()

    # Find user by Firebase UID
    user = db.users.find_one({"oauth_id": firebase_user["uid"]})

    if not user:
        # Auto-register user on first API call with Firebase token
        print(
            f"[INFO] Auto-registering new user from Firebase: {firebase_user['email']}"
        )

        # Generate username from email
        email = firebase_user["email"]
        username = email.split("@")[0].lower()
        username = "".join(c if (c.isalnum() or c in "_-") else "_" for c in username)

        # Ensure unique username
        counter = 1
        base_username = username
        while db.users.find_one({"username": username}):
            username = f"{base_username}_{counter}"
            counter += 1

        # Create new user
        new_user = User(
            email=email,
            username=username,
            full_name=firebase_user.get("name"),
            oauth_provider="firebase",
            oauth_id=firebase_user["uid"],
        )

        user_dict = new_user.model_dump(by_alias=True, exclude={"id"}, mode="python")
        result = db.users.insert_one(user_dict)
        print(f"[INFO] User registered: {username} (ID: {result.inserted_id})")
        return result.inserted_id

    return user["_id"]
