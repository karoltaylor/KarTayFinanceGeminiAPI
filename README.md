# Financial Transaction API

A FastAPI application for processing financial transaction files with AI-powered column mapping and secure user authentication.

## Features

- 📊 **AI-Powered Processing**: Uses Google Gemini to intelligently map transaction file columns
- 🔐 **Secure Authentication**: Firebase JWT tokens with backward compatibility
- 💾 **MongoDB Storage**: Flexible data storage with user isolation
- 📈 **Multi-Environment**: Local, development, and production configurations
- 🧪 **Comprehensive Testing**: 60+ integration tests with 77% pass rate
- 🚀 **AWS Ready**: Serverless deployment with SAM templates

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/config.local.env .env
# Edit .env with your MongoDB URL and Google API key

# Start the API
python start_api.py --env local
```

## Documentation

📖 **[Complete User Guide](USER_GUIDE.md)** - Everything you need to know  
⚙️ **[Configuration Setup](config/README.md)** - Environment and external services setup  
🧪 **[Integration Tests](tests/README_INTEGRATION_TESTS.md)** - API testing guide

## API Overview

### Authentication
- **Modern**: Firebase JWT tokens (`Authorization: Bearer <token>`)
- **Legacy**: `X-User-ID` header (backward compatibility)

### Key Endpoints
- `POST /api/transactions/upload` - Upload transaction files (CSV/Excel)
- `GET /api/transactions` - List transactions with filtering
- `GET /api/wallets` - Manage user wallets
- `GET /docs` - Interactive API documentation

## Requirements

### External Services
- **MongoDB**: Data storage (local or cloud)
- **Google Gemini API**: AI-powered file processing
- **Firebase** (optional): JWT authentication

### Python Dependencies
- FastAPI, Uvicorn
- PyMongo, Motor
- Firebase Admin SDK
- Google Generative AI
- Pydantic, Pandas

## Testing

```bash
# Run all tests
pytest tests/ -v

# Integration tests only
pytest tests/test_api_*.py -v --no-cov -m integration

# With coverage report
pytest tests/ -v --cov=src --cov-report=html
```

## Deployment

### Local Development
```bash
python start_api.py --env local
```

### AWS Lambda
```bash
sam build && sam deploy --guided
```

## Project Structure

```
├── api/                 # FastAPI application
├── src/                 # Source code modules
├── tests/               # Test suites (60+ tests)
├── config/              # Configuration samples
├── test_data/           # Sample transaction files
├── USER_GUIDE.md        # Complete user documentation
└── config/README.md     # Configuration setup guide
```

## Contributing

1. Run tests: `pytest tests/ -v`
2. Check code quality: `pylint src/`
3. Follow PEP 8 style guidelines
4. Update documentation as needed

## License

MIT License - see LICENSE file for details.

---

**Version**: 1.0.0 | **Python**: 3.8+ | **FastAPI**: Latest