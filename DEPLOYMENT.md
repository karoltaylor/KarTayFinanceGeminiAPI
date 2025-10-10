# AWS Lambda Deployment Guide

This guide will help you deploy the KarTay Finance API to AWS Lambda using AWS SAM (Serverless Application Model).

## Prerequisites

1. **AWS Account** - You need an active AWS account
2. **AWS CLI** - Install from [AWS CLI Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
3. **AWS SAM CLI** - Install from [SAM CLI Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
4. **MongoDB Atlas** (or other cloud MongoDB) - Lambda cannot connect to localhost, so you need a cloud-hosted MongoDB
5. **Python 3.11** - Required for building the Lambda package

## Quick Start

### 1. Install AWS CLI and SAM CLI

```bash
# Install AWS CLI (if not already installed)
# See: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

# Install SAM CLI
# Windows (using MSI installer):
# Download from: https://github.com/aws/aws-sam-cli/releases/latest

# Mac (using Homebrew):
brew install aws-sam-cli

# Verify installation
aws --version
sam --version
```

### 2. Configure AWS Credentials

```bash
# Configure AWS credentials
aws configure

# You'll be prompted for:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region name (e.g., us-east-1)
# - Default output format (json)
```

### 3. Set Up MongoDB (Required)

Lambda functions cannot connect to `localhost`. You need a cloud-hosted MongoDB instance:

**Option A: MongoDB Atlas (Recommended - Free Tier Available)**
1. Create account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)
4. **Important**: Whitelist AWS IP ranges or use `0.0.0.0/0` for testing (configure in Atlas Network Access)

**Option B: Other Cloud MongoDB**
- Use any cloud MongoDB service (AWS DocumentDB, etc.)
- Ensure it's accessible from AWS Lambda

### 4. Build the Application

```bash
# Build the SAM application
sam build
```

This command:
- Creates a `.aws-sam` directory
- Installs all dependencies from `requirements.txt`
- Packages your code for Lambda

### 5. Deploy to AWS

**First Time Deployment (Guided):**

```bash
sam deploy --guided
```

You'll be prompted for:
- **Stack Name**: `kartay-finance-api` (or your preferred name)
- **AWS Region**: `us-east-1` (or your preferred region)
- **Parameter MongoDBUrl**: Your MongoDB connection string (e.g., `mongodb+srv://user:pass@cluster.mongodb.net/`)
- **Parameter GoogleApiKey**: Your Google Generative AI API key
- **Parameter MongoDBDatabase**: `financial_tracker` (or your preferred database name)
- **Parameter Environment**: `production` (or `development`, `staging`)
- **Confirm changes before deploy**: `Y`
- **Allow SAM CLI IAM role creation**: `Y`
- **Disable rollback**: `N`
- **Save arguments to samconfig.toml**: `Y`

**Subsequent Deployments:**

After the first deployment, you can simply run:

```bash
sam deploy
```

Or deploy with specific parameters:

```bash
sam deploy --parameter-overrides \
  MongoDBUrl="mongodb+srv://user:pass@cluster.mongodb.net/" \
  GoogleApiKey="your-google-api-key" \
  Environment="production"
```

### 6. Test Your Deployment

After deployment, SAM will output:
```
CloudFormation outputs:
ApiEndpoint: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/production/
ApiDocsUrl: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/production/docs
```

Test your API:

```bash
# Test the health endpoint
curl https://your-api-gateway-url.amazonaws.com/production/health

# Open API documentation in browser
# https://your-api-gateway-url.amazonaws.com/production/docs
```

## Deployment Environments

The template supports multiple environments. Configure them in `samconfig.toml`:

### Deploy to Production
```bash
sam deploy --config-env production
```

### Deploy to Staging
```bash
sam deploy --config-env staging
```

### Deploy to Development
```bash
sam deploy --config-env development
```

## Local Testing with SAM

Before deploying to AWS, you can test locally:

### Test API Locally

```bash
# Start local API Gateway
sam local start-api

# API will be available at http://127.0.0.1:3000
```

**Note**: For local testing, you still need to set environment variables:

```bash
# Set environment variables for local testing
export MONGODB_URL="your-mongodb-url"
export GOOGLE_API_KEY="your-google-api-key"

# Then start local API
sam local start-api --env-vars env.json
```

Create `env.json` for local testing:
```json
{
  "FinanceAPIFunction": {
    "MONGODB_URL": "mongodb+srv://user:pass@cluster.mongodb.net/",
    "MONGODB_DATABASE": "financial_tracker",
    "GOOGLE_API_KEY": "your-google-api-key",
    "GENAI_MODEL": "models/gemini-2.5-flash"
  }
}
```

### Invoke Function Directly

```bash
# Invoke Lambda function locally
sam local invoke FinanceAPIFunction --event events/test-event.json
```

## Monitoring and Logs

### View Lambda Logs

```bash
# View logs in real-time
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail

# View logs for specific time range
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api \
  --start-time '10min ago' --end-time '5min ago'
```

### CloudWatch Logs

Logs are automatically sent to CloudWatch:
- **Lambda logs**: `/aws/lambda/kartay-finance-api-production`
- **API Gateway logs**: `/aws/apigateway/kartay-finance-api-production`

Access them via AWS Console:
1. Go to CloudWatch → Log groups
2. Find your log group
3. View log streams

### Monitoring Metrics

View metrics in AWS Console:
1. CloudWatch → Metrics
2. Lambda → By Function Name
3. Key metrics:
   - Invocations
   - Errors
   - Duration
   - Throttles

## Configuration

### Environment Variables

Set in `template.yaml` or via deployment parameters:

- `MONGODB_URL` - MongoDB connection string
- `MONGODB_DATABASE` - Database name
- `GOOGLE_API_KEY` - Google Generative AI API key
- `GENAI_MODEL` - AI model to use
- `ALLOWED_HOSTS` - Comma-separated allowed hosts
- `ENFORCE_HTTPS` - Enable HTTPS enforcement

### Lambda Configuration

In `template.yaml`:
- **Timeout**: 30 seconds (can increase up to 900 seconds)
- **Memory**: 1024 MB (can adjust between 128 MB - 10,240 MB)
- **Runtime**: Python 3.11

### API Gateway Configuration

- **CORS**: Configured for common frontend origins
- **Throttling**: 500 requests/second, burst 1000
- **Binary Media Types**: Enabled for file uploads

## Cost Optimization

### Lambda Free Tier
- 1 million requests per month
- 400,000 GB-seconds compute time per month

### Tips to Reduce Costs
1. **Optimize memory**: Start with 512 MB, adjust based on performance
2. **Optimize timeout**: Use shortest timeout that works reliably
3. **Enable Lambda caching**: Code is cached between invocations
4. **Use MongoDB connection pooling**: Reuse connections (already implemented)
5. **Monitor CloudWatch logs**: Set appropriate retention period (currently 30 days)

## Security Best Practices

### 1. Use AWS Secrets Manager

Instead of passing secrets as parameters:

```bash
# Store MongoDB URL in Secrets Manager
aws secretsmanager create-secret \
  --name kartay-finance-mongodb-url \
  --secret-string "mongodb+srv://user:pass@cluster.mongodb.net/"

# Store Google API Key
aws secretsmanager create-secret \
  --name kartay-finance-google-api-key \
  --secret-string "your-google-api-key"
```

Then update `template.yaml` to retrieve secrets from Secrets Manager.

### 2. Configure CORS

Update `template.yaml` to restrict CORS origins:

```yaml
AllowOrigin: "'https://your-frontend-domain.com'"
```

### 3. Enable API Key

Add API Gateway API keys for additional security:

```yaml
Auth:
  ApiKeyRequired: true
```

### 4. Use VPC

If MongoDB is in a VPC (like AWS DocumentDB):

```yaml
VpcConfig:
  SecurityGroupIds:
    - sg-xxxxxxxxx
  SubnetIds:
    - subnet-xxxxxxxxx
    - subnet-yyyyyyyyy
```

## Troubleshooting

### Common Issues

**1. "Unable to connect to MongoDB"**
- Ensure MongoDB URL is correct
- Check MongoDB Atlas Network Access (whitelist AWS IPs or use 0.0.0.0/0)
- Verify credentials in connection string

**2. "Lambda timeout"**
- Increase timeout in `template.yaml` (Timeout: 60)
- Optimize code or increase memory

**3. "Module not found error"**
- Run `sam build` again
- Ensure all dependencies are in `requirements.txt`

**4. "CORS error"**
- Update CORS configuration in `template.yaml`
- Add your frontend domain to AllowedOrigins

**5. "File upload fails"**
- Check Lambda timeout (file processing can be slow)
- Verify BinaryMediaTypes in API Gateway config
- Consider increasing Lambda memory

### Debug Tips

```bash
# Validate SAM template
sam validate

# Build with debug output
sam build --debug

# Deploy with debug output
sam deploy --debug

# Tail logs during testing
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail
```

## Updating Your Application

### 1. Make Code Changes

Edit your Python code as needed.

### 2. Rebuild and Deploy

```bash
# Build with new changes
sam build

# Deploy
sam deploy
```

### 3. Quick Sync (Development)

For faster development iterations:

```bash
# Sync code changes without full deployment
sam sync --watch
```

This watches for file changes and syncs them to AWS.

## Deleting the Stack

To completely remove the application from AWS:

```bash
# Delete the CloudFormation stack
sam delete

# Or specify stack name
sam delete --stack-name kartay-finance-api
```

This will:
- Delete the Lambda function
- Delete the API Gateway
- Delete CloudWatch log groups
- Delete all associated resources

**Warning**: This does NOT delete your MongoDB data. That's stored separately.

## Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Mangum Documentation](https://mangum.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Support

For issues:
1. Check CloudWatch logs for error details
2. Run `sam validate` to check template syntax
3. Review AWS Lambda and API Gateway documentation
4. Check MongoDB connection from another client

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS Lambda

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - uses: aws-actions/setup-sam@v2
      
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: SAM Build
        run: sam build
      
      - name: SAM Deploy
        run: |
          sam deploy --no-confirm-changeset --no-fail-on-empty-changeset \
            --parameter-overrides \
              MongoDBUrl="${{ secrets.MONGODB_URL }}" \
              GoogleApiKey="${{ secrets.GOOGLE_API_KEY }}"
```

Store your secrets in GitHub repository settings under Settings → Secrets and variables → Actions.

