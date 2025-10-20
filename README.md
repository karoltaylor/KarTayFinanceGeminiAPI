# Financial Transaction API

A FastAPI application for processing financial transaction files with AI-powered column mapping, smart caching, and secure authentication.

## Features

- 📊 **AI-Powered Column Mapping**: Uses Google Gemini to intelligently map file columns to transaction schema
- ⚡ **Smart Caching**: Per-user column mapping cache (99% faster for repeated file formats)
- 🔐 **Secure Authentication**: Firebase JWT tokens with backward-compatible X-User-ID
- 💾 **MongoDB Storage**: User-isolated data storage with optimized queries
- 🎯 **Modular API**: Clean router-based architecture for easy maintenance
- 🧪 **Comprehensive Testing**: 60+ tests with 79% coverage, fast mocked AI mode
- 🚀 **Production Ready**: AWS Lambda deployment, HTTPS enforcement, comprehensive logging

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp config/config.local.env .env
# Edit .env with your MongoDB URL and Google API key

# 3. Start the API
python start_api.py --env local

# 4. Access interactive docs
# Open http://localhost:8000/docs
```

## API Endpoints

### Authentication
```
POST /api/users/register    # Register/login with OAuth
GET  /api/users/me          # Get current user info
```

### Wallets
```
GET    /api/wallets           # List user's wallets
POST   /api/wallets           # Create new wallet
DELETE /api/wallets/{id}      # Delete wallet
```

### Transactions
```
POST   /api/transactions/upload        # Upload file (CSV/Excel)
GET    /api/transactions?wallet_id=... # List transactions
GET    /api/transactions/errors        # List upload errors
DELETE /api/transactions/wallet/{id}   # Delete all transactions
```

### Other
```
GET /health                 # Health check
GET /api/assets             # List all assets
GET /api/stats              # User statistics
GET /docs                   # API documentation (Swagger)
```

## Configuration

### Environment Files

Choose based on deployment:
- `config/config.local.env` - Local development (MongoDB localhost)
- `config/config.dev.env` - Development server
- `config/config.production.env` - Production deployment

### Required Environment Variables

```bash
# MongoDB
MONGODB_URL=mongodb://localhost:27017  # or mongodb+srv://...
MONGODB_DATABASE=financial_tracker

# Google Gemini AI
GOOGLE_API_KEY=your_api_key_here
GENAI_MODEL=gemini-1.5-flash

# Firebase (optional, for JWT auth)
FIREBASE_SERVICE_ACCOUNT_PATH=config/firebase-service-account.json

# Security
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000
ENFORCE_HTTPS=false  # Set to true in production
```

### Switch Environments

```bash
# Local development
python start_api.py --env local

# Development server
python start_api.py --env dev

# Production
python start_api.py --env production
```

## Testing

```bash
# Fast tests (mocked AI - recommended for development)
pytest tests/ -v

# Full integration tests with real AI
USE_REAL_AI=true pytest tests/ -v        # Linux/Mac
$env:USE_REAL_AI="true"; pytest tests/   # Windows

# With coverage report
pytest tests/ -v --cov=src --cov-report=html

# Specific test files
pytest tests/test_column_mapping_cache.py -v
```

**Performance:**
- Mocked AI: ~2-3 seconds per test ⚡
- Real AI: ~25-30 seconds per test

## Key Features Explained

### 1. Smart Column Mapping Cache

**Problem:** Every file upload called Google Gemini AI (~5-15 seconds, costs money)

**Solution:** Cache mappings per user based on file structure

**Performance Impact:**
- First upload of a format: 5-15 seconds (AI call)
- Subsequent uploads: ~instant (cache hit)
- **99% reduction** for repeated formats!

**How it works:**
1. Generate cache key from: column names + file type + column count
2. Check MongoDB cache for existing mapping
3. If found: use cached mapping (instant)
4. If not found: call AI, then cache the result

**Cache invalidation:**
```python
# In src/services/column_mapper.py
self.cache_version = 1  # Increment to invalidate all cache
```

### 2. Modular API Architecture

**Before:** 1,232-line `main.py` (monolith)
**After:** Organized routers (~170 lines each)

```
api/
├── main.py (169 lines)          # App initialization only
├── dependencies.py              # Shared dependencies
└── routers/
    ├── system.py               # Health checks
    ├── auth.py                 # Authentication
    ├── wallets.py              # Wallet management
    ├── assets.py               # Asset listing
    ├── transactions.py         # Transaction operations
    └── stats.py                # Statistics
```

**Benefits:**
- 86% reduction in main.py size
- Easier to find and maintain code
- Better for team collaboration
- Clearer code reviews

### 3. Optimized Database Queries

**N+1 Query Fix:**
- Before: 200 DB queries for 100 transactions
- After: 2 DB queries (batch fetching)
- **100x faster** response times

### 4. API Changes (Breaking)

⚠️ **Important:** Transaction APIs now use `wallet_id` instead of `wallet_name`

**Before:**
```python
# Auto-created wallet
POST /api/transactions/upload
{
  "wallet_name": "My Wallet"
}
```

**After:**
```python
# Step 1: Create wallet first
POST /api/wallets
{"name": "My Wallet"}
→ {"data": {"_id": "507f..."}}

# Step 2: Use wallet ID
POST /api/transactions/upload
{
  "wallet_id": "507f..."
}
```

**Migration:** Update client code to create wallets via `/api/wallets` before uploading transactions.

## Project Structure

```
├── api/                    # API layer
│   ├── main.py            # App initialization & routing
│   ├── dependencies.py    # Shared dependencies
│   └── routers/           # Modular endpoint routers
├── src/
│   ├── auth/              # Firebase authentication
│   ├── config/            # MongoDB & settings
│   ├── loaders/           # File loaders (CSV, Excel)
│   ├── middleware/        # Logging middleware
│   ├── models/            # Pydantic & MongoDB models
│   ├── pipeline/          # Data processing pipeline
│   ├── services/          # Business logic (mapping, validation)
│   └── utils/             # Logger utilities
├── tests/                 # Test suite (60+ tests)
├── config/                # Environment configurations
└── test_data/             # Sample transaction files
```

## Deployment

### Local Development
```bash
python start_api.py --env local
```

### Docker (Optional)
```bash
docker build -t finance-api .
docker run -p 8000:8000 finance-api
```

### AWS Lambda
```bash
# Configure SAM
cp config/samconfig.example.toml samconfig.toml
# Edit with your AWS settings

# Deploy
sam build
sam deploy --guided
```

## Logging

**Structured logging** to multiple files:

- `logs/combined.log` - All logs
- `logs/backend.log` - API and database logs
- `logs/frontend.log` - Request/response logs
- `logs/errors.log` - Errors only

**Log formats:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "event": "transaction_upload",
  "message": "Transaction upload started",
  "user_id": "507f...",
  "context": {
    "wallet_id": "507f...",
    "filename": "transactions.csv"
  }
}
```

## Troubleshooting

### MongoDB Connection Issues
```bash
# Check MongoDB is running
mongosh --eval "db.runCommand({ ping: 1 })"

# Verify connection string in .env
MONGODB_URL=mongodb://localhost:27017
```

### Google AI API Errors
```bash
# Verify API key is set
echo $GOOGLE_API_KEY  # Linux/Mac
echo $env:GOOGLE_API_KEY  # Windows

# Test with mocked AI instead
pytest tests/ -v  # Uses mock by default
```

### Import Errors After Refactoring
```bash
# Old import
from api.main import app, get_current_user

# New import
from api.main import app
from api.dependencies import get_current_user
```

## Performance Metrics

- **API Response Time**: < 100ms (cached queries)
- **File Upload**: 2-3s (cached) vs 5-15s (first time)
- **Test Suite**: ~30s (mocked AI) vs 10+ minutes (real AI)
- **Database Queries**: Batch fetching (2 queries vs 200+)

## Development

### Adding New Endpoints

1. Create or update router in `api/routers/`
2. Define endpoint with proper tags
3. Register in `api/main.py`

```python
# api/routers/my_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-feature", tags=["MyFeature"])

@router.get("")
async def my_endpoint():
    return {"message": "Hello"}

# api/main.py
from api.routers import my_feature
app.include_router(my_feature.router)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_wallets.py -v

# With coverage
pytest --cov=src --cov-report=html

# Coverage threshold
pytest --cov-fail-under=79
```

### Code Quality

```bash
# Linting
pylint src/

# Type checking
mypy src/

# Format code
black src/
```

## Security

- ✅ HTTPS enforcement in production
- ✅ CORS configuration per environment
- ✅ Firebase JWT token validation
- ✅ User isolation (MongoDB queries)
- ✅ Input validation (Pydantic models)
- ✅ Security headers (X-Frame-Options, etc.)
- ✅ Trusted host middleware

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/ -v`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Support

- 📖 **API Docs**: http://localhost:8000/docs (when running)
- 🐛 **Issues**: Create a GitHub issue
- 💬 **Questions**: Check the interactive API documentation

---

**Version**: 1.0.0 | **Python**: 3.8+ | **FastAPI**: Latest
