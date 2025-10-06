# KarTayFinance Transaction API

A FastAPI application for processing financial transaction files with OAuth authentication, AI-powered column mapping, and MongoDB storage.

## Key Features

- **OAuth Authentication**: Google/Meta sign-in integration
- **Multi-Format Support**: CSV, TXT, XLS, XLSX file processing
- **AI-Powered Column Mapping**: Automatic column detection using Google Gemini
- **Smart Table Detection**: Finds headers anywhere in the file
- **MongoDB Storage**: Complete transaction tracking with user-scoped wallets
- **RESTful API**: Clean endpoints with interactive documentation
- **Type-Safe**: Full validation with Pydantic

---

## Quick Start

### 1. Setup Environment

Create `.env` file:

```env
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
GENAI_MODEL=gemini-1.5-flash
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=financial_tracker
```

Get Google API Key: https://makersuite.google.com/app/apikey

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 4. Start API Server

```bash
python start_api.py
```

Access at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Authentication

### OAuth-Based Authentication

The API uses OAuth (Google, Meta, etc.) for authentication:

1. **Frontend**: User authenticates with OAuth provider
2. **Frontend**: Calls `/api/users/register` with OAuth data
3. **Backend**: Returns `user_id`
4. **Frontend**: Includes `X-User-ID` header in all authenticated requests

### Register/Login User

```bash
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myusername",
    "full_name": "My Name",
    "oauth_provider": "google",
    "oauth_id": "google_123456789"
  }'
```

Response:
```json
{
  "status": "success",
  "user_id": "67023abc...",
  "is_new_user": true
}
```

Save the `user_id` and use it in `X-User-ID` header for all authenticated requests.

---

## API Endpoints

### Authentication (No auth required)

- `POST /api/users/register` - Register/login after OAuth

### Wallets (Requires X-User-ID header)

- `GET /api/wallets` - List user's wallets
- `POST /api/wallets` - Create wallet
- `DELETE /api/wallets/{wallet_id}` - Delete wallet

### Transactions (Requires X-User-ID header)

- `POST /api/transactions/upload` - Upload transaction file
- `GET /api/transactions` - List transactions
- `DELETE /api/transactions/wallet/{wallet_name}` - Delete wallet transactions

### Assets & Stats

- `GET /api/assets` - List all assets
- `GET /api/stats` - Get user statistics (requires X-User-ID)

### System

- `GET /` - API information
- `GET /health` - Health check

---

## Usage Examples

### Create a Wallet

```bash
curl -X POST "http://localhost:8000/api/wallets" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: YOUR_USER_ID" \
  -d '{"name": "My Portfolio", "description": "Investment portfolio"}'
```

### List Wallets

```bash
curl -H "X-User-ID: YOUR_USER_ID" \
  http://localhost:8000/api/wallets
```

### Upload Transactions

```bash
curl -X POST "http://localhost:8000/api/transactions/upload" \
  -H "X-User-ID: YOUR_USER_ID" \
  -F "file=@transactions.csv" \
  -F "wallet_name=My Portfolio" \
  -F "transaction_type=buy" \
  -F "asset_type=stock"
```

### Delete Wallet

```bash
curl -X DELETE "http://localhost:8000/api/wallets/WALLET_ID" \
  -H "X-User-ID: YOUR_USER_ID"
```

---

## Frontend Integration

### React Example with Firebase

```javascript
import { auth } from './firebase';

// 1. After Firebase OAuth login, register with backend
const registerWithBackend = async (firebaseUser) => {
  const response = await fetch('http://localhost:8000/api/users/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: firebaseUser.email,
      username: firebaseUser.email.split('@')[0],
      full_name: firebaseUser.displayName,
      oauth_provider: 'google',
      oauth_id: firebaseUser.uid,
    }),
  });
  
  const data = await response.json();
  localStorage.setItem('backend_user_id', data.user_id);
  return data.user_id;
};

// 2. Fetch wallets with authentication
const fetchWallets = async () => {
  const userId = localStorage.getItem('backend_user_id');
  
  const response = await fetch('http://localhost:8000/api/wallets', {
    headers: { 'X-User-ID': userId }
  });
  
  return response.json();
};

// 3. Create wallet
const createWallet = async (name, description) => {
  const userId = localStorage.getItem('backend_user_id');
  
  const response = await fetch('http://localhost:8000/api/wallets', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': userId
    },
    body: JSON.stringify({ name, description })
  });
  
  return response.json();
};

// 4. Delete wallet
const deleteWallet = async (walletId) => {
  const userId = localStorage.getItem('backend_user_id');
  
  const response = await fetch(`http://localhost:8000/api/wallets/${walletId}`, {
    method: 'DELETE',
    headers: { 'X-User-ID': userId }
  });
  
  return response.json();
};
```

---

## MongoDB Models

### User Model

```python
{
  "_id": ObjectId,
  "email": str (unique),
  "username": str (unique),
  "full_name": str (optional),
  "oauth_provider": str (e.g., "google", "meta"),
  "oauth_id": str (provider's user ID),
  "is_active": bool,
  "created_at": datetime,
  "updated_at": datetime
}
```

### Wallet Model

```python
{
  "_id": ObjectId,
  "user_id": ObjectId (reference to User),
  "name": str (unique per user),
  "description": str (optional),
  "created_at": datetime,
  "updated_at": datetime
}
```

### Asset Model

```python
{
  "_id": ObjectId,
  "asset_name": str,
  "asset_type": str (bond, stock, crypto, etc.),
  "symbol": str (optional),
  "url": str (optional),
  "description": str (optional),
  "created_at": datetime,
  "updated_at": datetime
}
```

### Transaction Model

```python
{
  "_id": ObjectId,
  "wallet_id": ObjectId (reference to Wallet),
  "asset_id": ObjectId (reference to Asset),
  "date": datetime,
  "transaction_type": str (buy, sell, etc.),
  "volume": float,
  "item_price": float,
  "transaction_amount": float,
  "currency": str (ISO 4217, e.g., "USD"),
  "fee": float,
  "notes": str (optional),
  "created_at": datetime,
  "updated_at": datetime
}
```

---

## Python Client

```python
from api_client_example import (
    register_or_login_user,
    create_wallet,
    get_wallets,
    delete_wallet,
    get_transactions,
    get_stats
)

# 1. Authenticate (simulates OAuth)
user_id = register_or_login_user(
    email="user@example.com",
    username="myuser",
    full_name="My Name",
    oauth_provider="google",
    oauth_id="google_123"
)

# 2. Create wallet
create_wallet(
    user_id=user_id,
    name="My Portfolio",
    description="Investment portfolio"
)

# 3. Get wallets
wallets = get_wallets(user_id=user_id)

# 4. Delete wallet
delete_wallet(user_id=user_id, wallet_id="wallet_id_here")

# 5. Get stats
stats = get_stats(user_id=user_id)
```

---

## Data Isolation

- Each user sees only their own wallets and transactions
- Wallet names are unique per user (not globally)
- Assets are shared across all users
- Statistics are calculated per user

---

## Project Structure

```
KarTayFinanceGoogleAPI/
├── api/
│   └── main.py                    # FastAPI application
├── src/
│   ├── config/
│   │   ├── settings.py            # Configuration
│   │   └── mongodb.py             # MongoDB connection
│   ├── models/
│   │   ├── data_model.py          # TransactionRecord
│   │   └── mongodb_models.py      # User, Wallet, Asset, Transaction
│   ├── loaders/                   # File loaders (CSV, Excel)
│   ├── services/                  # Business logic
│   │   ├── table_detector.py      # Header detection
│   │   ├── column_mapper.py       # AI column mapping
│   │   └── transaction_mapper.py  # Model conversion
│   └── pipeline/
│       └── data_pipeline.py       # Main orchestration
├── tests/                         # Unit tests
├── test_data/                     # Sample files
├── start_api.py                   # Start server
├── api_client_example.py          # Python client
├── requirements.txt
└── README.md
```

---

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Test Specific Module

```bash
pytest tests/test_pipeline.py -v
```

---

## Supported File Formats

- CSV (`.csv`, `.txt`)
- Excel 2007+ (`.xlsx`)
- Excel 97-2003 (`.xls`)

### Features

- Auto header detection (headers can be anywhere)
- AI column mapping (works with any column names)
- European decimal format support (comma separator)
- Multiple date formats
- Automatic encoding detection

---

## Transaction Types

- `buy` - Purchase of assets
- `sell` - Sale of assets
- `transfer_in` - Transfer into wallet
- `transfer_out` - Transfer out of wallet
- `dividend` - Dividend payment
- `interest` - Interest earned
- `fee` - Fee payment
- `deposit` - Cash deposit
- `withdrawal` - Cash withdrawal
- `other` - Other transactions

---

## Asset Types

- `stock` - Stocks/equities
- `bond` - Bonds
- `cryptocurrency` - Crypto assets
- `real_estate` - Real estate
- `commodity` - Commodities
- `cash` - Cash/currencies
- `other` - Other assets

---

## Configuration

### Environment Variables

```env
# Required
GOOGLE_API_KEY=your_google_api_key

# Optional (with defaults)
GENAI_MODEL=gemini-1.5-flash
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=financial_tracker
```

### Database Indexes

Created automatically on startup:

```python
# Users
db.users.create_index("email", unique=True)
db.users.create_index("username", unique=True)
db.users.create_index([("oauth_provider", 1), ("oauth_id", 1)])

# Wallets
db.wallets.create_index("user_id")
db.wallets.create_index([("user_id", 1), ("name", 1)], unique=True)

# Assets
db.assets.create_index("asset_name")
db.assets.create_index("asset_type")

# Transactions
db.transactions.create_index("wallet_id")
db.transactions.create_index("asset_id")
db.transactions.create_index("date")
```

---

## Troubleshooting

### Wallets not loading

1. Check user is authenticated and `user_id` is stored
2. Verify `X-User-ID` header is included in requests
3. Check browser console for errors
4. Ensure API server is running

### CORS errors

CORS is configured for:
- http://localhost:3000 (React)
- http://localhost:5173 (Vite)
- http://localhost:4200 (Angular)

Add your frontend URL to CORS middleware in `api/main.py` if different.

### MongoDB connection failed

1. Check MongoDB is running: `docker ps`
2. Verify connection URL in `.env`
3. Test connection: `curl http://localhost:8000/health`

### File upload fails

1. Check file format (CSV, XLS, XLSX supported)
2. Verify file has transaction data
3. Check `X-User-ID` header is included
4. Review error message in response

---

## Development

### Run API in Development Mode

```bash
python start_api.py
# Auto-reloads on code changes
```

### Run in Production

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Add New Endpoints

Edit `api/main.py`:

```python
@app.get("/api/custom", tags=["Custom"])
async def custom_endpoint(
    user_id: ObjectId = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    # Your logic here
    return {"result": "success"}
```

---

## Security Notes

### Current Implementation (Development)

- Simple header-based auth (`X-User-ID`)
- OAuth data stored (email, username, oauth_id)
- User data isolation enforced

### Production Recommendations

1. **Verify OAuth tokens on backend**:
   ```bash
   pip install firebase-admin
   ```
   Use Firebase Admin SDK to verify ID tokens

2. **Use JWT tokens** instead of passing `user_id` directly

3. **Enable HTTPS/TLS** for all traffic

4. **Add rate limiting** on authentication endpoints

5. **Implement token refresh** mechanism

---

## Interactive Documentation

Visit http://localhost:8000/docs for:

- Try all endpoints with "Try it out" button
- View request/response schemas
- Test authentication flow
- Explore all available operations

---

## Example Workflow

```python
# Complete workflow with Python client
from api_client_example import *

# 1. Authenticate (simulates OAuth)
user_id = register_or_login_user(
    email="user@example.com",
    username="myuser",
    oauth_provider="google",
    oauth_id="google_123"
)

# 2. Create wallet
create_wallet(user_id, "My Portfolio", "Long-term investments")

# 3. List wallets
wallets = get_wallets(user_id)

# 4. Get transactions
transactions = get_transactions(user_id, limit=50)

# 5. Get statistics
stats = get_stats(user_id)
print(f"Total wallets: {stats['total_wallets']}")
print(f"Total transactions: {stats['total_transactions']}")
```

---

## Database Schema

### Collections

- **users** - User accounts (OAuth-based)
- **wallets** - User portfolios/accounts
- **assets** - Financial assets (shared)
- **transactions** - All transactions
- **asset_current_values** - Price history

### Relationships

```
User (1) ─── (N) Wallet
               │
               └─ (N) Transaction ─── (1) Asset
```

Each user has multiple wallets, each wallet has multiple transactions, and transactions reference shared assets.

---

## Common Tasks

### Check API Health

```bash
curl http://localhost:8000/health
```

### View All Endpoints

```bash
curl http://localhost:8000/
```

### Get User Statistics

```bash
curl -H "X-User-ID: YOUR_USER_ID" \
  http://localhost:8000/api/stats
```

### Filter Transactions by Wallet

```bash
curl -H "X-User-ID: YOUR_USER_ID" \
  "http://localhost:8000/api/transactions?wallet_name=My%20Portfolio"
```

---

## Files Included

- `start_api.py` - API server startup script
- `api_client_example.py` - Python client with examples
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template
- `pytest.ini` - Test configuration

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[MongoDB](https://www.mongodb.com/)** - NoSQL database
- **[Google Gemini AI](https://ai.google.dev/)** - AI column mapping
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation
- **[Pandas](https://pandas.pydata.org/)** - Data processing

---

## License

[Your License Here]

---

## Support

- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- GitHub Issues: [Your Repo]

---

**Ready to use!** Start the API and visit http://localhost:8000/docs to explore. 🚀
