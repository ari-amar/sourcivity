"""
Vercel serverless function handler for FastAPI application.
Uses Mangum to adapt FastAPI (ASGI) to work with Vercel's serverless runtime.
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

# Create the Mangum handler for Vercel's serverless runtime
# The handler converts AWS Lambda-style events to ASGI format
handler = Mangum(app, lifespan="off")

