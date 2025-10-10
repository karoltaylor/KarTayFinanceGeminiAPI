# AWS Lambda Deployment - Summary

This document summarizes the AWS SAM deployment setup for the KarTay Finance API.

## 📦 Files Created

### Core Deployment Files
1. **`lambda_handler.py`** - AWS Lambda entry point using Mangum adapter
2. **`template.yaml`** - AWS SAM CloudFormation template (main deployment configuration)
3. **`.samignore`** - Excludes unnecessary files from Lambda package

### Configuration Files
4. **`samconfig.example.toml`** - Example SAM CLI configuration (copy to `samconfig.toml`)
5. **`env.example.json`** - Example environment variables for local testing (copy to `env.json`)

### Documentation Files
6. **`DEPLOYMENT.md`** - Complete deployment guide with all details
7. **`QUICKSTART_AWS.md`** - 5-minute quick start guide
8. **`.aws-sam-commands.md`** - Quick reference for SAM CLI commands
9. **`AWS_DEPLOYMENT_SUMMARY.md`** - This file

### Modified Files
10. **`requirements.txt`** - Added `mangum>=0.17.0` dependency
11. **`.gitignore`** - Added AWS SAM build artifacts

## 🎯 What Was Added

### Mangum Adapter
Mangum is an ASGI adapter that wraps FastAPI to work with AWS Lambda and API Gateway.

**In `lambda_handler.py`:**
```python
from mangum import Mangum
from api.main import app

handler = Mangum(app, lifespan="auto")
```

### AWS SAM Template
The `template.yaml` defines:
- **Lambda Function** with 1024MB memory, 30s timeout, Python 3.11
- **API Gateway** with CORS, throttling, and binary media type support
- **CloudWatch Logs** with 30-day retention
- **Environment Variables** for MongoDB, Google API Key, etc.
- **Parameters** for secure credential passing
- **Outputs** for API URLs and resource ARNs

### Build Exclusions
The `.samignore` file excludes:
- Test files and test data
- Virtual environments
- IDE configurations
- Local environment files
- Documentation
- Git files
- Cache and temporary files

This keeps the Lambda package size small (faster deployments, lower costs).

## 🚀 Deployment Process

### Quick Steps
```bash
# 1. Build
sam build

# 2. Deploy (first time)
sam deploy --guided

# 3. Test
curl https://your-api-url/production/health
```

### What Happens During Deployment

1. **Build Phase** (`sam build`)
   - Creates `.aws-sam/build/` directory
   - Installs all Python dependencies from `requirements.txt`
   - Copies source code
   - Packages everything for Lambda

2. **Package Phase** (automatic during deploy)
   - Uploads code to S3
   - Creates CloudFormation changeset

3. **Deploy Phase** (`sam deploy`)
   - Creates/updates CloudFormation stack
   - Provisions Lambda function
   - Creates API Gateway
   - Configures CloudWatch Logs
   - Sets up IAM roles and permissions

4. **Output Phase**
   - Displays API Gateway URL
   - Shows CloudFormation outputs

## 📊 Architecture

```
Internet
    ↓
API Gateway (with CORS, throttling)
    ↓
AWS Lambda (Python 3.11, FastAPI + Mangum)
    ↓
MongoDB Atlas (cloud database)
    ↓
Google Generative AI API
```

### Key Components

- **API Gateway**: REST API endpoint, handles HTTP→Lambda event conversion
- **Lambda Function**: Runs FastAPI application via Mangum adapter
- **MongoDB**: Stores users, wallets, transactions, assets (must be cloud-hosted)
- **CloudWatch**: Logs and metrics for monitoring
- **X-Ray**: Distributed tracing (enabled by default)

## 🔧 Configuration Options

### Lambda Settings (in `template.yaml`)

| Setting | Default | Max | Notes |
|---------|---------|-----|-------|
| Timeout | 30s | 900s | Increase for large file uploads |
| Memory | 1024MB | 10240MB | More memory = faster CPU |
| Runtime | Python 3.11 | - | Latest stable Python |

### API Gateway Settings

| Setting | Default | Notes |
|---------|---------|-------|
| Throttling | 500 req/s | Burst: 1000 |
| CORS | Configured | Add your domains |
| Binary Media | Enabled | For file uploads |

### Environment Variables

Set via Parameters or directly in template:
- `MONGODB_URL` - MongoDB connection string (required)
- `MONGODB_DATABASE` - Database name (default: financial_tracker)
- `GOOGLE_API_KEY` - Google Generative AI key (required)
- `GENAI_MODEL` - AI model (default: models/gemini-2.5-flash)
- `ALLOWED_HOSTS` - Allowed hosts (default: *)
- `ENFORCE_HTTPS` - HTTPS enforcement (default: false)

## 💰 Cost Breakdown

### AWS Free Tier (First 12 Months)
- **Lambda**: 1M requests/month + 400,000 GB-seconds compute FREE
- **API Gateway**: 1M API calls/month FREE
- **CloudWatch Logs**: 5GB ingestion, 5GB storage FREE

### Estimated Monthly Cost (After Free Tier)

**Low Traffic** (10,000 requests/month):
- Lambda: $0.20
- API Gateway: $0.035
- CloudWatch Logs: $0.50
- **Total: ~$0.75/month**

**Medium Traffic** (100,000 requests/month):
- Lambda: $2.00
- API Gateway: $0.35
- CloudWatch Logs: $2.00
- **Total: ~$4.35/month**

**High Traffic** (1M requests/month):
- Lambda: $18.00
- API Gateway: $3.50
- CloudWatch Logs: $10.00
- **Total: ~$31.50/month**

**Note**: MongoDB Atlas has a FREE tier (512MB storage, shared cluster).

## 🔒 Security Considerations

### Current Setup
- ✅ HTTPS via API Gateway
- ✅ CloudWatch Logs enabled
- ✅ X-Ray tracing enabled
- ✅ CORS configured
- ✅ IAM roles with minimal permissions

### Recommended Enhancements
- [ ] Use AWS Secrets Manager for credentials
- [ ] Enable API Gateway API Keys
- [ ] Set up WAF (Web Application Firewall)
- [ ] Configure Lambda in VPC (if MongoDB is in VPC)
- [ ] Add authentication (JWT tokens instead of X-User-ID header)
- [ ] Restrict CORS to specific domains
- [ ] Enable CloudTrail for audit logs

## 📈 Monitoring

### CloudWatch Logs
- **Lambda logs**: `/aws/lambda/kartay-finance-api-{environment}`
- **API Gateway logs**: `/aws/apigateway/kartay-finance-api-{environment}`
- Retention: 30 days

### Metrics to Watch
- **Invocations**: Total Lambda executions
- **Errors**: Failed invocations
- **Duration**: Execution time (optimize if consistently high)
- **Throttles**: Rate limiting hits (increase if needed)
- **4XX Errors**: Client errors (bad requests)
- **5XX Errors**: Server errors (bugs in code)

### View Logs
```bash
# Real-time tail
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --tail

# Recent logs
sam logs --name FinanceAPIFunction --stack-name kartay-finance-api --start-time '30min ago'
```

## 🧪 Testing

### Local Testing
```bash
# Start local API
sam local start-api --env-vars env.json

# Test locally
curl http://localhost:3000/health
```

### Remote Testing
```bash
# After deployment
curl https://your-api-url/production/health

# Test with authentication
curl -H "X-User-ID: your-user-id" \
     https://your-api-url/production/api/wallets
```

## 🔄 CI/CD Integration

### GitHub Actions
See `DEPLOYMENT.md` for a complete GitHub Actions workflow example.

**Key steps:**
1. Checkout code
2. Setup Python 3.11
3. Setup SAM CLI
4. Configure AWS credentials
5. Run `sam build`
6. Run `sam deploy`

**Store secrets in GitHub:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `MONGODB_URL`
- `GOOGLE_API_KEY`

## 🆘 Troubleshooting

### Build Fails
```bash
# Clean build
rm -rf .aws-sam/
sam build --debug
```

### Deployment Fails
```bash
# Validate template first
sam validate --lint

# Deploy with debug
sam deploy --debug
```

### MongoDB Connection Fails
1. Check MongoDB Atlas Network Access (whitelist `0.0.0.0/0` or AWS IP ranges)
2. Verify connection string (check for special characters in password)
3. Test connection from another client (MongoDB Compass)
4. Check Lambda CloudWatch logs for exact error

### Lambda Timeout
1. Increase timeout in `template.yaml`: `Timeout: 60`
2. Increase memory (more memory = faster CPU): `MemorySize: 2048`
3. Optimize code (reduce unnecessary database queries)
4. Use Lambda Provisioned Concurrency for faster cold starts

### CORS Errors
1. Add your frontend domain to `AllowedOrigins` in `template.yaml`
2. Ensure API Gateway CORS is configured correctly
3. Check browser console for exact error
4. Test with `curl` to isolate issue

## 📚 Additional Resources

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Mangum Documentation](https://mangum.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)

## 🎓 Next Steps

1. **Deploy to Development** - Test everything works
   ```bash
   sam build
   sam deploy --guided
   ```

2. **Configure MongoDB Atlas** - Whitelist AWS IPs

3. **Test All Endpoints** - Use Postman or API docs

4. **Set Up Monitoring** - Configure CloudWatch alarms

5. **Configure Production** - Use Secrets Manager, restrict CORS

6. **Set Up CI/CD** - Automate deployments

7. **Add Custom Domain** - Use Route 53 + API Gateway custom domain

8. **Scale as Needed** - Adjust Lambda memory/timeout based on metrics

## 🎉 Success Checklist

- [x] Mangum adapter added
- [x] SAM template created
- [x] Build exclusions configured
- [x] Documentation provided
- [x] Example configurations included
- [ ] MongoDB Atlas configured
- [ ] First deployment successful
- [ ] API endpoints tested
- [ ] Monitoring configured
- [ ] Production secrets secured

## 📞 Support

For issues:
1. Check CloudWatch logs: `sam logs --tail`
2. Validate template: `sam validate --lint`
3. Review this documentation
4. Check AWS SAM documentation
5. Search AWS Lambda troubleshooting guides

---

**Ready to deploy?** Start with [QUICKSTART_AWS.md](./QUICKSTART_AWS.md) for a 5-minute guide!

