# Configuration Setup

## Required External Configuration

### 1. Google Gemini API Key
**Purpose**: AI-powered transaction column mapping  
**Required for**: File upload processing  
**Setup**:
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add to your environment file: `GOOGLE_API_KEY=your_key_here`

### 2. MongoDB Database
**Purpose**: Data storage  
**Required for**: All operations  
**Setup**:
- **Local**: Install MongoDB locally (default: `mongodb://localhost:27017`)
- **Cloud**: Use MongoDB Atlas or AWS DocumentDB
- Add connection string to environment file: `MONGODB_URL=your_connection_string`

### 3. Firebase Authentication (Optional)
**Purpose**: Secure user authentication  
**Setup**:
1. Create Firebase project at [Firebase Console](https://console.firebase.google.com)
2. Download service account JSON
3. Set path in environment: `FIREBASE_SERVICE_ACCOUNT_PATH=path/to/service-account.json`

## Environment Files

Copy the appropriate template and configure:

- `config.local.env` - Local development
- `config.dev.env` - Development/staging  
- `config.production.env` - Production

### Required Variables
```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=financial_tracker
GOOGLE_API_KEY=your_gemini_api_key
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/firebase-service-account.json
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Optional Variables
```env
ENFORCE_HTTPS=false
ALLOWED_HOSTS=*
DEBUG=true
```

## Quick Start

1. **Copy environment file**:
   ```bash
   cp config/config.local.env .env
   ```

2. **Set required variables**:
   - Edit `.env` with your MongoDB URL and Google API key

3. **Start the API**:
   ```bash
   python start_api.py --env local
   ```

## AWS Deployment

For AWS deployment, also copy and configure:
```bash
cp config/samconfig.example.toml samconfig.toml
cp config/env.example.json .env
```

Configure AWS-specific settings in `samconfig.toml`.
