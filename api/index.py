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
# Note: Mangum should preserve the full path from Vercel
handler = Mangum(app, lifespan="off")

