# Debugging AWS Lambda Deployment

## Enhanced Logging Added

I've added comprehensive debug logging to help diagnose the MongoDB connection issue in Lambda.

### Files Modified with Logging

1. **`lambda_handler.py`** - Entry point logging
   - Shows Lambda environment detection
   - Lists all MongoDB and Google API environment variables
   - Shows if they're SET or NOT SET (with lengths for sensitive data)

2. **`src/config/mongodb.py`** - Database connection logging
   - Environment detection (Lambda vs local)
   - Environment variable loading process
   - MongoDB URL detection and masking
   - Client creation steps
   - Database selection
   - Index creation progress
   - Connection ping test
   - Detailed error messages

3. **`api/main.py`** - FastAPI startup logging
   - Lifespan event tracking
   - MongoDB initialization steps
   - Full exception tracebacks

## What the Logs Will Show

When you deploy and check CloudWatch logs, you'll now see:

```
[DEBUG] ========== Lambda Handler Initialization ==========
[DEBUG] AWS_LAMBDA_FUNCTION_NAME: kartay-finance-api-production
[DEBUG] AWS_REGION: eu-central-1
[DEBUG] Environment variables related to MongoDB and Google:
[DEBUG]   MONGODB_URL = SET (length: 87)  <-- Or NOT SET
[DEBUG]   MONGODB_DATABASE = financial_tracker
[DEBUG]   GOOGLE_API_KEY = SET (length: 39)  <-- Or NOT SET
[DEBUG]   GENAI_MODEL = models/gemini-2.5-flash
[DEBUG] ===================================================
[DEBUG] Creating Mangum handler...
[DEBUG] Environment detection - Is Lambda: True
[DEBUG] AWS_LAMBDA_FUNCTION_NAME: kartay-finance-api-production
[DEBUG] Running in Lambda - skipping .env file loading
[DEBUG] Mangum handler created successfully
[DEBUG] ========== FastAPI Lifespan Startup ==========
[DEBUG] Retrieving MongoDB configuration...
[DEBUG] get_mongodb_url() called - URL is SET
[DEBUG] get_mongodb_database() called - Database: financial_tracker
[INFO] Connecting to: mongodb+srv://user:***@cluster.mongodb.net/
[INFO] Database: financial_tracker
[DEBUG] Calling MongoDBConfig.initialize_collections()...
[DEBUG] Initializing MongoDB collections and indexes...
[DEBUG] Getting MongoDB database...
[DEBUG] Creating new MongoDB client...
[DEBUG] MONGODB_URL environment variable: SET
[DEBUG] MongoDB URL (masked): mongodb+srv://***:***@cluster.mongodb.net/
[DEBUG] Creating MongoClient with timeout=10000ms...
[DEBUG] MongoClient created successfully
[DEBUG] Database name: financial_tracker
[DEBUG] Selecting database: financial_tracker
[DEBUG] Database selected successfully
[DEBUG] Database object obtained: <class 'pymongo.database.Database'>
[DEBUG] Testing connection with ping...
[DEBUG] Ping successful!
[DEBUG] Creating indexes for users collection...
[DEBUG] Users indexes created
... [more index creation logs] ...
[OK] MongoDB connected and initialized
[DEBUG] ===============================================
```

## Critical Issues Fixed

1. ✅ **Runtime**: Changed to Python 3.12 (3.13 not supported by Lambda)
2. ✅ **Enhanced Logging**: Added debug statements throughout connection flow
3. ✅ **Error Handling**: Added try-catch with full tracebacks

## IMPORTANT: Missing Parameters Issue

Your `samconfig.toml` still has this line (line 24):
```toml
parameter_overrides = "MongoDBDatabase=\"financial_tracker\" Environment=\"production\" AllowedOrigins=\"*\""
```

**This is MISSING `MongoDBUrl` and `GoogleApiKey`!**

## How to Deploy Correctly

### Option 1: Command Line (Recommended - Most Secure)

```bash
# Build
sam build

# Deploy with parameters
sam deploy --parameter-overrides \
  MongoDBUrl="mongodb+srv://user:password@cluster.mongodb.net/" \
  GoogleApiKey="your-google-api-key-here"
```

### Option 2: Edit samconfig.toml (Less Secure)

Edit line 24 in `samconfig.toml`:

```toml
parameter_overrides = "MongoDBUrl=\"mongodb+srv://user:pass@cluster.mongodb.net/\" GoogleApiKey=\"your-google-api-key\" MongoDBDatabase=\"financial_tracker\" Environment=\"production\" AllowedOrigins=\"*\""
```

⚠️ **Don't commit this file with real credentials!**

## Viewing Logs

After deployment:

```bash
# Real-time tail
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail

# Or via AWS Console
# CloudWatch → Log groups → /aws/lambda/kartay-finance-api-production
```

## What to Look For in Logs

### If Parameters Are NOT Set:
```
[DEBUG]   MONGODB_URL = NOT SET
[ERROR] MONGODB_URL is None or empty!
[ERROR] MONGODB_URL environment variable is not set.
```

### If Parameters ARE Set:
```
[DEBUG]   MONGODB_URL = SET (length: 87)
[DEBUG] MongoDB URL (masked): mongodb+srv://***:***@cluster.mongodb.net/
[DEBUG] Ping successful!
```

## Next Steps

1. **Deploy with correct parameters:**
   ```bash
   sam build
   sam deploy --parameter-overrides MongoDBUrl="YOUR_URL" GoogleApiKey="YOUR_KEY"
   ```

2. **Check logs immediately:**
   ```bash
   sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail
   ```

3. **Look for these key indicators:**
   - ✅ `MONGODB_URL = SET (length: XX)` - Good!
   - ❌ `MONGODB_URL = NOT SET` - Parameters not passed correctly
   - ✅ `Ping successful!` - Connection works!
   - ❌ `Connection refused` - Wrong URL or network issue
   - ❌ `Authentication failed` - Wrong credentials in URL

## Common Issues and Solutions

### Issue: `MONGODB_URL = NOT SET`
**Solution:** You didn't pass the parameters. Use:
```bash
sam deploy --parameter-overrides MongoDBUrl="..." GoogleApiKey="..."
```

### Issue: `Connection refused` to localhost
**Solution:** Parameters not reaching Lambda. Check CloudFormation stack parameters in AWS Console.

### Issue: `Authentication failed`
**Solution:** Check your MongoDB Atlas username/password in the connection string.

### Issue: `Network timeout`
**Solution:** Check MongoDB Atlas Network Access settings - add `0.0.0.0/0` or AWS IP ranges.

## Verify Parameters Were Set

After deployment, check AWS Console:
1. Go to CloudFormation
2. Find stack: `kartay-finance-api`
3. Click "Parameters" tab
4. Verify `MongoDBUrl` and `GoogleApiKey` show values (not empty)

## Clean Up Old Deployments

If you've deployed multiple times with wrong config:

```bash
# Delete and redeploy fresh
sam delete --stack-name kartay-finance-api
sam build
sam deploy --guided
```

Then provide correct parameters when prompted.

---

With all this logging, we'll be able to see exactly where the connection is failing! 🔍

