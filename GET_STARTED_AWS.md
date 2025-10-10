# 🚀 Get Started with AWS Lambda Deployment

Your KarTay Finance API is now ready to deploy to AWS Lambda! Here's everything you need to know.

## 📋 What Was Added

### New Files Created

1. **`lambda_handler.py`** - Entry point for AWS Lambda using Mangum adapter
2. **`template.yaml`** - Complete AWS SAM deployment configuration
3. **`.samignore`** - Excludes unnecessary files from deployment package
4. **`samconfig.example.toml`** - Template for SAM configuration
5. **`env.example.json`** - Template for local testing environment variables

### Documentation Added

6. **`QUICKSTART_AWS.md`** - 5-minute quick deployment guide ⚡
7. **`DEPLOYMENT.md`** - Complete detailed deployment guide 📚
8. **`AWS_DEPLOYMENT_SUMMARY.md`** - Architecture, costs, and reference 📊
9. **`.aws-sam-commands.md`** - Quick CLI command reference 💻
10. **`GET_STARTED_AWS.md`** - This file! 👋

### Modified Files

- **`requirements.txt`** - Added `mangum>=0.17.0` for Lambda compatibility
- **`.gitignore`** - Added AWS SAM build artifacts
- **`README.md`** - Added AWS Lambda deployment section

## ⚡ Quick Start (5 Minutes)

### Prerequisites

- [ ] AWS Account (sign up at https://aws.amazon.com)
- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed
- [ ] MongoDB Atlas connection string (free tier available)
- [ ] Google API Key for AI features

### Step 1: Install AWS SAM CLI

**Windows:**
```powershell
# Download installer from:
# https://github.com/aws/aws-sam-cli/releases/latest/download/AWS_SAM_CLI_64_PY3.msi
```

**Mac:**
```bash
brew install aws-sam-cli
```

**Linux:**
```bash
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
```

### Step 2: Configure AWS Credentials

```bash
aws configure
# AWS Access Key ID: [Your Key]
# AWS Secret Access Key: [Your Secret]
# Default region name: us-east-1
# Default output format: json
```

### Step 3: Get MongoDB Atlas Ready

1. Create free account at https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Get connection string: `mongodb+srv://user:password@cluster.mongodb.net/`
4. **Important**: In Atlas, go to Network Access → Add `0.0.0.0/0` (for testing)

### Step 4: Build & Deploy

```bash
# Build the application
sam build

# Deploy (guided first time)
sam deploy --guided
```

Answer the prompts:
- **Stack Name**: `kartay-finance-api`
- **AWS Region**: `us-east-1` (or your choice)
- **MongoDBUrl**: `mongodb+srv://user:pass@cluster.mongodb.net/`
- **GoogleApiKey**: Your Google API key
- **MongoDBDatabase**: `financial_tracker`
- **Environment**: `production`
- Confirm all other defaults (press Enter)

### Step 5: Test Your API

After deployment completes, you'll see:
```
ApiEndpoint: https://abc123.execute-api.us-east-1.amazonaws.com/production/
ApiDocsUrl: https://abc123.execute-api.us-east-1.amazonaws.com/production/docs
```

Test it:
```bash
curl https://your-api-url/production/health
```

Or open the docs URL in your browser! 🎉

## 📖 Documentation Guide

Choose based on your needs:

### 🏃 I want to deploy NOW
→ Read **[QUICKSTART_AWS.md](./QUICKSTART_AWS.md)** (5 minutes)

### 📚 I want detailed instructions
→ Read **[DEPLOYMENT.md](./DEPLOYMENT.md)** (complete guide)

### 💰 I want to know costs & architecture
→ Read **[AWS_DEPLOYMENT_SUMMARY.md](./AWS_DEPLOYMENT_SUMMARY.md)**

### 💻 I need CLI command reference
→ Read **[.aws-sam-commands.md](./.aws-sam-commands.md)**

## 🎯 Common Tasks

### Update Your Code
```bash
# Make changes to your code
# Then rebuild and redeploy
sam build && sam deploy
```

### View Logs
```bash
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail
```

### Test Locally
```bash
# Copy example env file
cp env.example.json env.json
# Edit env.json with your credentials

# Start local API
sam local start-api --env-vars env.json

# Test at http://localhost:3000
curl http://localhost:3000/health
```

### Delete Everything
```bash
sam delete --stack-name kartay-finance-api
```

## 💰 Cost Breakdown

### AWS Free Tier (Forever Free)
- **1M Lambda requests/month** - FREE
- **1M API Gateway calls/month** - FREE
- **5GB CloudWatch logs** - FREE

### MongoDB Atlas
- **512MB storage** - FREE (forever)

### Typical Costs (After Free Tier)

| Usage | Cost/Month |
|-------|-----------|
| Personal project (10K req) | $0.75 |
| Small business (100K req) | $4.35 |
| Growing app (1M req) | $31.50 |

**Most projects stay FREE!** 🎉

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              AWS API Gateway (HTTPS)                        │
│  • CORS configured                                          │
│  • Throttling: 500 req/s                                    │
│  • Binary media types                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│           AWS Lambda (Python 3.11)                          │
│  • FastAPI + Mangum adapter                                 │
│  • Memory: 1024 MB                                          │
│  • Timeout: 30 seconds                                      │
│  • Auto-scaling                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌──────────────────┐            ┌──────────────────┐
│  MongoDB Atlas   │            │  Google Gemini   │
│  (Database)      │            │  (AI Mapping)    │
└──────────────────┘            └──────────────────┘
```

## 🔧 Configuration

### Environment Variables

Set via SAM parameters during deployment:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URL` | ✅ Yes | - | MongoDB connection string |
| `GOOGLE_API_KEY` | ✅ Yes | - | Google Generative AI key |
| `MONGODB_DATABASE` | No | `financial_tracker` | Database name |
| `GENAI_MODEL` | No | `models/gemini-2.5-flash` | AI model |
| `ENVIRONMENT` | No | `production` | Environment name |
| `ALLOWED_HOSTS` | No | `*` | Allowed hosts |
| `ENFORCE_HTTPS` | No | `false` | HTTPS enforcement |

### Lambda Settings

Adjust in `template.yaml`:

```yaml
Timeout: 30              # 3-900 seconds
MemorySize: 1024        # 128-10240 MB
Runtime: python3.11     # Python version
```

## 🔒 Security Checklist

- [x] HTTPS via API Gateway (automatic)
- [x] CORS configured
- [x] CloudWatch logging enabled
- [x] X-Ray tracing enabled
- [ ] Use AWS Secrets Manager for credentials (recommended)
- [ ] Restrict CORS to your domain (recommended)
- [ ] Enable API Gateway API keys (optional)
- [ ] Set up CloudWatch alarms (optional)

## 🐛 Troubleshooting

### "Unable to import module 'lambda_handler'"
```bash
# Rebuild
rm -rf .aws-sam/
sam build
sam deploy
```

### "Unable to connect to MongoDB"
1. Check MongoDB Atlas Network Access → Add `0.0.0.0/0`
2. Verify connection string (check password encoding)
3. Test with MongoDB Compass

### "Lambda timeout"
```yaml
# In template.yaml, increase:
Timeout: 60
MemorySize: 2048
# Then: sam build && sam deploy
```

### "CORS error"
```yaml
# In template.yaml, update:
AllowedOrigins: "https://your-domain.com"
# Then: sam build && sam deploy
```

## 📊 Monitoring

### View Metrics
1. Go to AWS Console → CloudWatch
2. Select "All metrics" → Lambda
3. View: Invocations, Duration, Errors, Throttles

### View Logs
```bash
# Real-time tail
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail

# Last 30 minutes
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --start-time '30min ago'
```

### Set Up Alarms
```bash
# In AWS Console → CloudWatch → Alarms
# Create alarm for:
# - Lambda errors > 10
# - Lambda duration > 25 seconds
# - API Gateway 5XX errors > 5
```

## 🚀 Next Steps

### Immediate
1. [ ] Deploy to AWS: `sam build && sam deploy --guided`
2. [ ] Test API: Visit `/docs` endpoint
3. [ ] Check logs: `sam logs --tail`

### Short Term
4. [ ] Configure custom domain (Route 53 + API Gateway)
5. [ ] Set up CI/CD (GitHub Actions, AWS CodePipeline)
6. [ ] Add CloudWatch alarms
7. [ ] Use Secrets Manager for credentials

### Long Term
8. [ ] Add caching (API Gateway caching, Lambda@Edge)
9. [ ] Set up staging environment
10. [ ] Monitor costs (AWS Cost Explorer)
11. [ ] Optimize Lambda (memory, timeout, provisioned concurrency)

## 🎓 Learning Resources

### AWS SAM
- [Official Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Workshop](https://aws.amazon.com/serverless/workshops/)

### AWS Lambda
- [Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Python Lambda Guide](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

### Mangum
- [Documentation](https://mangum.io/)
- [GitHub](https://github.com/jordaneremieff/mangum)

## 💡 Pro Tips

### Development Workflow
```bash
# Fast iteration during development
sam sync --watch
# Auto-syncs code changes to Lambda
```

### Multiple Environments
```bash
# Deploy to dev
sam deploy --config-env development

# Deploy to staging
sam deploy --config-env staging

# Deploy to production
sam deploy --config-env production
```

### Cost Optimization
1. **Adjust memory** based on actual usage (CloudWatch metrics)
2. **Reduce timeout** to minimum needed
3. **Enable request caching** in API Gateway
4. **Set CloudWatch log retention** to 7-30 days
5. **Monitor cold starts** - use Provisioned Concurrency if needed

### Testing
```bash
# Local testing (free!)
sam local start-api --env-vars env.json

# Test specific endpoint
sam local invoke FinanceAPIFunction --event test-event.json
```

## ✅ Deployment Checklist

Pre-Deployment:
- [ ] AWS CLI installed and configured
- [ ] SAM CLI installed
- [ ] MongoDB Atlas cluster created
- [ ] Google API Key ready
- [ ] Code tested locally

Deployment:
- [ ] `sam build` successful
- [ ] `sam deploy --guided` completed
- [ ] API endpoint accessible
- [ ] Health check passes
- [ ] API documentation loads

Post-Deployment:
- [ ] CloudWatch logs visible
- [ ] Test all endpoints
- [ ] Configure CloudWatch alarms
- [ ] Update frontend with new API URL
- [ ] Document API endpoint for team

## 🎉 Success!

Once deployed, your API will be:
- ✅ **Live** at a public HTTPS URL
- ✅ **Auto-scaling** to handle any traffic
- ✅ **Highly available** (99.95% uptime SLA)
- ✅ **Monitored** with CloudWatch
- ✅ **Cost-effective** (pay only for use)

**Your API URL** will look like:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/production/
```

Share this with your team! 🚀

## 📞 Need Help?

1. **Check logs**: `sam logs --tail`
2. **Validate template**: `sam validate --lint`
3. **Read docs**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
4. **AWS Support**: AWS Forums, Stack Overflow
5. **SAM Issues**: https://github.com/aws/aws-sam-cli/issues

---

**Ready?** Start with: `sam build` 🚀

