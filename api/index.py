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

# Create the base Mangum handler
mangum_handler = Mangum(app, lifespan="off")

def handler(event, context):
    """
    Wrapper to handle path routing correctly.
    Vercel routes /api/(.*) to this function, capturing the path after /api/.
    We need to ensure the path is formatted correctly for FastAPI.
    """
    # Get the path from the event
    # Vercel passes the path in different formats depending on the event structure
    path = event.get('path', '')
    raw_path = event.get('rawPath', path)
    
    # Ensure path starts with / for FastAPI routing
    # If Vercel stripped /api/, the path will be like "search/parts" or "/search/parts"
    # FastAPI routes are defined as "/search/parts" (with leading slash)
    if raw_path and not raw_path.startswith('/'):
        raw_path = '/' + raw_path
    
    # Update the event with the corrected path
    event['rawPath'] = raw_path
    event['path'] = raw_path
    
    # Also update requestContext if it exists (API Gateway format)
    if 'requestContext' in event:
        if 'http' in event['requestContext']:
            event['requestContext']['http']['path'] = raw_path
        elif 'path' in event['requestContext']:
            event['requestContext']['path'] = raw_path
    
    # Call Mangum handler with corrected event
    return mangum_handler(event, context)

