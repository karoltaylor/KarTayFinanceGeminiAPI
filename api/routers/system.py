"""System endpoints for API information and health checks."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo.database import Database

from src.config.mongodb import MongoDBConfig, get_db

router = APIRouter(tags=["System"])


@router.get("/", summary="API Information")
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
            "delete_wallet_transactions": "/api/transactions/wallet/{wallet_id} (DELETE)",
            "stats": "/api/stats (GET)",
        },
    }


@router.get("/health", summary="Health Check")
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
