"""AWS Lambda handler for FastAPI application using Mangum adapter."""

import os
from mangum import Mangum

# Log Lambda environment info
print("[DEBUG] ========== Lambda Handler Initialization ==========")
print(f"[DEBUG] AWS_LAMBDA_FUNCTION_NAME: {os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'Not set')}")
print(f"[DEBUG] AWS_REGION: {os.getenv('AWS_REGION', 'Not set')}")
print(f"[DEBUG] Environment variables related to MongoDB and Google:")
for key in ['MONGODB_URL', 'MONGODB_DATABASE', 'GOOGLE_API_KEY', 'GENAI_MODEL']:
    value = os.getenv(key)
    if value:
        # Mask sensitive values
        if 'URL' in key or 'KEY' in key:
            display_value = f"SET (length: {len(value)})"
        else:
            display_value = value
        print(f"[DEBUG]   {key} = {display_value}")
    else:
        print(f"[DEBUG]   {key} = NOT SET")
print("[DEBUG] ===================================================")

# Import app after logging environment info
from api.main import app

# Configure for Lambda environment
# Lambda expects specific handler name
print("[DEBUG] Creating Mangum handler...")
handler = Mangum(app, lifespan="auto")
print("[DEBUG] Mangum handler created successfully")

# Alternative: if you need custom configuration
# handler = Mangum(
#     app, 
#     lifespan="auto",
#     api_gateway_base_path="/prod"  # Use this if deploying behind API Gateway with a stage
# )

