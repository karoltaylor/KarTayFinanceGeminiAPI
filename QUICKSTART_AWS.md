# Quick Start: Deploy to AWS Lambda in 5 Minutes

This is a condensed guide to get your API running on AWS Lambda quickly.

## Prerequisites Checklist

- [ ] AWS Account created
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] SAM CLI installed (`sam --version`)
- [ ] MongoDB Atlas account with connection string ready
- [ ] Google API Key ready

## Step-by-Step Deployment

### 1. Install AWS SAM CLI (if not installed)

**Windows:**
```powershell
# Download and run the installer
# https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi
```

**Mac:**
```bash
brew install aws-sam-cli
```

**Linux:**
```bash
# Download and install
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region (e.g., us-east-1)
# Enter output format (json)
```

### 3. Get MongoDB Connection String

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster (if you don't have one)
3. Click "Connect" → "Connect your application"
4. Copy connection string (looks like: `mongodb+srv://user:password@cluster.mongodb.net/`)
5. **Important**: Go to "Network Access" and add `0.0.0.0/0` (for testing) or specific AWS IP ranges

### 4. Build Your Application

```bash
# Navigate to your project directory
cd path/to/KarTayFinanceGoogleAPI

# Build
sam build
```

### 5. Deploy to AWS

```bash
sam deploy --guided
```

Answer the prompts:
```
Stack Name: kartay-finance-api
AWS Region: us-east-1 (or your preferred region)
Parameter MongoDBUrl: mongodb+srv://user:password@cluster.mongodb.net/
Parameter MongoDBDatabase: financial_tracker
Parameter GoogleApiKey: your-google-api-key
Parameter Environment: production
Parameter AllowedOrigins: *
Confirm changes before deploy [Y/n]: Y
Allow SAM CLI IAM role creation [Y/n]: Y
Disable rollback [y/N]: N
FinanceAPIFunction has no authentication [y/N]: Y
Save arguments to configuration file [Y/n]: Y
SAM configuration file [samconfig.toml]: (press Enter)
SAM configuration environment [default]: (press Enter)
```

Wait 2-3 minutes for deployment...

### 6. Get Your API URL

After deployment, you'll see:
```
CloudFormation outputs:
ApiEndpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/production/
ApiDocsUrl: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/production/docs
```

### 7. Test Your API

```bash
# Test health endpoint
curl https://your-api-url/production/health

# Or open in browser:
# https://your-api-url/production/docs
```

## That's It! 🎉

Your API is now running on AWS Lambda!

## What Next?

### Update Your Code
```bash
# Make code changes
# Then rebuild and redeploy
sam build && sam deploy
```

### View Logs
```bash
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail
```

### Delete Everything
```bash
sam delete --stack-name kartay-finance-api
```

## Common Issues

**"Unable to connect to MongoDB"**
- Check MongoDB Network Access settings
- Verify connection string is correct
- Ensure password doesn't contain special characters (or URL-encode them)

**"Timeout error"**
- Your file is too large or processing is slow
- Increase timeout in template.yaml: `Timeout: 60`
- Then redeploy: `sam build && sam deploy`

**"CORS error"**
- Add your frontend domain to AllowedOrigins in template.yaml
- Redeploy: `sam build && sam deploy`

## Cost Estimate

With AWS Free Tier:
- **Lambda**: First 1M requests/month FREE
- **API Gateway**: First 1M requests/month FREE
- **CloudWatch Logs**: 5GB/month FREE

For most personal projects, you'll stay within free tier! 🎉

## Need Help?

See the full [DEPLOYMENT.md](./DEPLOYMENT.md) guide for detailed instructions.

