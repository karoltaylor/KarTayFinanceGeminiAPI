# Financial Transaction API - User Guide

## Overview

A FastAPI application for processing financial transaction files with AI-powered column mapping, storing data in MongoDB, and providing secure user authentication.

## Quick Start

### 1. Setup
```bash
# Clone and install
git clone <repository>
cd KarTayFinanceGoogleAPI
pip install -r requirements.txt

# Configure environment
cp config/config.local.env .env
# Edit .env with your MongoDB URL and Google API key

# Start API
python start_api.py --env local
```

### 2. Required External Services
- **MongoDB**: Local installation or cloud service (Atlas/DocumentDB)
- **Google Gemini API**: For AI-powered file processing
- **Firebase** (optional): For JWT authentication

See `config/README.md` for detailed setup instructions.

## API Endpoints

### Authentication
- **Legacy**: `X-User-ID` header (backward compatibility)
- **Modern**: Firebase JWT token in `Authorization: Bearer <token>` header

### Wallets
- `GET /api/wallets` - List user wallets
- `POST /api/wallets` - Create wallet
- `DELETE /api/wallets/{wallet_id}` - Delete wallet

### Transactions
- `POST /api/transactions/upload` - Upload transaction file
- `GET /api/transactions` - List transactions (with filtering/pagination)
- `DELETE /api/transactions/wallet/{wallet_name}` - Delete wallet transactions

### System
- `GET /` - API information
- `GET /health` - Health check
- `GET /api/stats` - User statistics

## File Upload

### Supported Formats
- **CSV**: `.csv`, `.txt`
- **Excel**: `.xlsx`, `.xls`

### Upload Process
1. **File Processing**: AI maps columns to transaction fields
2. **Data Validation**: Calculates missing values (prices, amounts, fees)
3. **Storage**: Creates wallets/assets and saves transactions
4. **Response**: Returns complete transaction list with all details

### Example Request
```bash
curl -X POST "http://localhost:8000/api/transactions/upload" \
  -H "X-User-ID: 507f1f77bcf86cd799439011" \
  -F "file=@transactions.csv" \
  -F "wallet_name=My Portfolio" \
  -F "transaction_type=buy" \
  -F "asset_type=stock"
```

## Environments

### Local Development
```bash
python start_api.py --env local
```
- Uses local MongoDB
- HTTP allowed
- Debug logging enabled

### Development/Staging
```bash
python start_api.py --env dev
```
- Uses cloud MongoDB (Atlas)
- CORS configured for staging domains
- Production-like settings

### Production
```bash
python start_api.py --env production
```
- Uses production MongoDB
- HTTPS enforced
- Security headers enabled
- CORS restricted to production domains

## Testing

### Run Tests
```bash
# Unit tests
pytest tests/ -v

# Integration tests (requires MongoDB)
pytest tests/test_api_wallets.py tests/test_api_transactions.py -v --no-cov -m integration

# All tests with coverage
pytest tests/ -v --cov=src --cov-report=html
```

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end API testing
- **Firebase Auth Tests**: Authentication flow testing

## Deployment

### Local Development
```bash
python start_api.py --env local
```

### AWS Lambda
```bash
# Build and deploy
sam build
sam deploy --guided

# Use production environment
sam deploy --config-env production
```

### Docker (Optional)
```bash
docker build -t financial-api .
docker run -p 8000:8000 --env-file .env financial-api
```

## Security

### Authentication Methods
1. **Firebase JWT** (Recommended)
   - Secure token-based authentication
   - Automatic user registration
   - Production-ready

2. **X-User-ID Header** (Legacy)
   - Simple user ID header
   - Backward compatibility
   - Development/testing only

### CORS Configuration
- Environment-specific allowed origins
- Local: `http://localhost:*`
- Production: Specific HTTPS domains only

### Security Headers
- HTTPS enforcement (production)
- XSS protection
- Content type validation
- Host header validation

## Troubleshooting

### Common Issues

**API won't start**:
- Check MongoDB connection
- Verify environment variables
- Check port availability (8000)

**File upload fails**:
- Verify Google API key
- Check file format (CSV/Excel)
- Ensure file has transaction data

**Authentication errors**:
- Verify user exists in database
- Check X-User-ID format (24-char ObjectId)
- For Firebase: verify service account JSON

**Tests fail**:
- Ensure MongoDB is running
- Check test database connection
- Verify all environment variables set

### Debug Mode
Enable debug logging:
```env
DEBUG=true
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Configuration Reference

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `MONGODB_URL` | Yes | MongoDB connection string |
| `MONGODB_DATABASE` | Yes | Database name |
| `GOOGLE_API_KEY` | Yes | Gemini API key for file processing |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | No | Path to Firebase service account JSON |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `ENFORCE_HTTPS` | No | Force HTTPS (production) |
| `DEBUG` | No | Enable debug logging |

### File Structure
```
├── api/                 # FastAPI application
├── src/                 # Source code
│   ├── auth/           # Authentication logic
│   ├── config/         # Configuration management
│   ├── loaders/        # File loaders
│   ├── models/         # Data models
│   ├── pipeline/       # Data processing pipeline
│   └── services/       # Business logic services
├── tests/              # Test suites
├── config/             # Configuration samples
├── test_data/          # Sample transaction files
└── docs/               # Documentation
```

## Support

### Documentation
- Configuration: `config/README.md`
- Integration Tests: `tests/README_*_INTEGRATION_TESTS.md`
- API Documentation: Available at `http://localhost:8000/docs` when running

### Development
- **Code Style**: Follows PEP 8
- **Testing**: pytest with coverage
- **Linting**: PyLint integration
- **CI/CD**: GitHub Actions workflows

### Contributing
1. Run tests: `pytest tests/ -v`
2. Check linting: `pylint src/`
3. Update documentation as needed
4. Submit pull request

---

**Version**: 1.0.0  
**Last Updated**: October 2025
