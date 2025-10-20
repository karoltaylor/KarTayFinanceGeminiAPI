"""FastAPI application for financial transaction processing."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.config.mongodb import MongoDBConfig
from src.config.settings import Settings
from src.middleware.logging_middleware import LoggingMiddleware

# Import routers
from api.routers import system, auth, wallets, assets, transactions, stats
from api import logs


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
# APP INITIALIZATION
# ==============================================================================

app = FastAPI(
    title="Financial Transaction API",
    description="API for processing financial transaction files and storing in MongoDB",
    version="1.0.0",
    lifespan=lifespan,
)


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    if Settings.ENFORCE_HTTPS:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response


# ==============================================================================
# INCLUDE ROUTERS
# ==============================================================================

# System routes (/, /health)
app.include_router(system.router)

# Authentication routes
app.include_router(auth.router)

# Wallet routes
app.include_router(wallets.router)

# Asset routes
app.include_router(assets.router)

# Transaction routes
app.include_router(transactions.router)

# Statistics routes
app.include_router(stats.router)

# Logging routes (from existing logs.py)
app.include_router(logs.router)

