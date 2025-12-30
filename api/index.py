"""
Vercel serverless function handler for FastAPI application.
This file wraps the FastAPI app to work with Vercel's serverless function architecture.
"""
import os
import sys
from pathlib import Path

# Add the app/api directory to the Python path
api_dir = Path(__file__).parent.parent / "app" / "api"
sys.path.insert(0, str(api_dir))

# Load environment variables if env.config exists (for local development)
# In Vercel, environment variables are set automatically
env_file = api_dir / "config" / "env.config"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Import the FastAPI app after setting up the path
from app import app
from mangum import Mangum

# Create the ASGI handler for AWS Lambda/Vercel
# Using lifespan="off" because we handle initialization in app.py with lazy loading
# Note: When Vercel routes /api/(.*) to this function, the path might be the full path
# or just the captured group. We've added routes for both cases in app.py

# Debug wrapper to log incoming requests
def debug_handler(event, context):
    """Wrapper to log request details for debugging 405 errors"""
    # Log the request details
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'UNKNOWN'))
    path = event.get('path', event.get('rawPath', event.get('requestContext', {}).get('path', 'UNKNOWN')))
    query_string = event.get('queryStringParameters', {}) or {}
    
    print(f"[DEBUG] Request received:")
    print(f"  Method: {http_method}")
    print(f"  Path: {path}")
    print(f"  Query: {query_string}")
    print(f"  Event keys: {list(event.keys())}")
    
    # Call the actual handler
    return handler(event, context)

handler = Mangum(app, lifespan="off")

# Export both handlers - use debug_handler for debugging, handler for production
# Uncomment the line below to enable debugging:
# handler = debug_handler

