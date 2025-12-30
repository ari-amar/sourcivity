import os
from typing import Dict, Optional
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from enums import AiClientName, SearchEngineClientName
from models import *
from services.interfaces import AiClientBase, SearchEngineClientBase
from services.ai_clients import *
from services.search_engine_clients import *

from search import search_parts, search_services

app = FastAPI()

# Get Vercel deployment URL from environment (set automatically by Vercel)
# For local development, use localhost origins
vercel_url = os.getenv("VERCEL_URL")
is_vercel = os.getenv("VERCEL") == "1"

cors_origins = [
    "http://localhost:3000",  # Next.js default development server
    "http://localhost:3001",  # Alternative Next.js port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add Vercel deployment URLs if available
if vercel_url:
    # Add both https and http versions
    cors_origins.extend([
        f"https://{vercel_url}",
        f"http://{vercel_url}",
    ])

# In Vercel production, we need to allow the deployment URL
# The frontend and backend share the same domain, so CORS should work naturally
# But we still need to explicitly allow the origin
if is_vercel and vercel_url:
    # Ensure the deployment URL is in the allowed origins
    if f"https://{vercel_url}" not in cors_origins:
        cors_origins.append(f"https://{vercel_url}")

# CORS configuration - allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# NOTE: Client initialization is now lazy-loaded for better serverless performance
# This avoids initializing clients at module load time, which improves cold start times

# Global dictionaries to cache initialized clients
_AI_CLIENTS: Optional[Dict[str, AiClientBase]] = None
_SEARCH_ENGINE_CLIENTS: Optional[Dict[str, SearchEngineClientBase]] = None


def get_ai_clients() -> Dict[str, AiClientBase]:
    """Lazy initialization of AI clients for serverless compatibility."""
    global _AI_CLIENTS
    if _AI_CLIENTS is None:
        _AI_CLIENTS = {}
        
        # Initialize Cloudflare client if credentials are available
        cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cloudflare_workers_key = os.getenv("CLOUDFLARE_WORKERS_KEY")
        if cloudflare_account_id and cloudflare_workers_key:
            _AI_CLIENTS[AiClientName.CLOUDFLARE] = CloudflareAiClient(
                account_id=cloudflare_account_id,
                api_token=cloudflare_workers_key
            )
        
        # Initialize Anthropic client if API key is available
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            _AI_CLIENTS[AiClientName.ANTHROPIC] = AnthropicAiClient(
                api_key=anthropic_api_key,
                model="claude-3-haiku-20240307"  # Using Haiku (Sonnet not available on this API key)
            )
        
        # TODO: initialize other AI clients here
    
    return _AI_CLIENTS


def get_search_engine_clients() -> Dict[str, SearchEngineClientBase]:
    """Lazy initialization of search engine clients for serverless compatibility."""
    global _SEARCH_ENGINE_CLIENTS
    if _SEARCH_ENGINE_CLIENTS is None:
        _SEARCH_ENGINE_CLIENTS = {}
        
        # Initialize Exa client if API key is available
        exa_api_key = os.getenv("EXA_API_KEY")
        if exa_api_key:
            _SEARCH_ENGINE_CLIENTS[SearchEngineClientName.EXA] = ExaClient(api_key=exa_api_key)
        
        # TODO: initialize other search engine clients here
    
    return _SEARCH_ENGINE_CLIENTS


@app.get("/api/health")
async def health_check():
	return Response(content="OK", media_type="text/plain")

# Add explicit OPTIONS handler for CORS preflight (though CORS middleware should handle this)
@app.options("/api/{full_path:path}")
async def options_handler(full_path: str):
	return Response(status_code=200)

@app.get("/api/available_client_names")
async def get_available_client_names() -> AvailableClientResponse:

	# NOTE: we could potentially update this to run health checks on the available clients as well, or even get usage/cost metrics
	ai_clients = get_ai_clients()
	search_engine_clients = get_search_engine_clients()
	return AvailableClientResponse(
		ai_client_names=ai_clients.keys(),
		search_engine_client_names=search_engine_clients.keys()
	)

@app.post('/api/search/parts')
async def api_search_parts(payload: PartSearchRequest) -> PartSearchResponse:

	ai_clients = get_ai_clients()
	search_engine_clients = get_search_engine_clients()
	ai_client = ai_clients.get(payload.ai_client_name, None)
	search_engine_client = search_engine_clients.get(payload.search_engine_client_name, None)

	print(f"\n=== NEW SEARCH REQUEST ===")
	print(f"Query: {payload.query}")
	print(f"AI Client: {payload.ai_client_name}")
	print(f"Search Engine: {payload.search_engine_client_name}")
	print(f"Generate AI Prompt: {payload.generate_ai_search_prompt}")

	search_response =  await search_parts(
		request=payload,
		ai_client=ai_client,
		search_engine_client=search_engine_client
	)

	print(f"\n=== RESPONSE TO FRONTEND ===")
	print(f"Query: {search_response.query}")
	print(f"Spec Columns: {search_response.spec_column_names}")
	print(f"Parts Count: {len(search_response.parts)}")
	for i, part in enumerate(search_response.parts):
		print(f"  Part {i+1}: URL={part.url[:60]}...")
		print(f"    Specs: {part.specs}")

	return search_response


@app.post('/api/search/services')
async def api_search_services(payload: ServiceSearchRequest) -> ServiceSearchResponse:

	ai_clients = get_ai_clients()
	search_engine_clients = get_search_engine_clients()
	ai_client = ai_clients.get(payload.ai_client_name, None)
	search_engine_client = search_engine_clients.get(payload.search_engine_client_name, None)

	print(f"\n=== SERVICE SEARCH REQUEST ===")
	print(f"Query: {payload.query}")
	print(f"Supplier Name: {payload.supplier_name or 'None'}")
	print(f"AI Client: {payload.ai_client_name}")
	print(f"Search Engine: {payload.search_engine_client_name}")

	search_response = await search_services(
		request=payload,
		ai_client=ai_client,
		search_engine_client=search_engine_client
	)

	print(f"\n=== RESPONSE TO FRONTEND ===")
	print(f"Query: {search_response.query}")
	print(f"Services Count: {len(search_response.services)}")
	for i, service in enumerate(search_response.services):
		print(f"  Service {i+1}: {service['title'][:50]}...")
		print(f"    URL: {service['url']}")
		if service.get('extraction_error'):
			print(f"    ⚠ Extraction Error: {service['extraction_error']}")
		elif service.get('extracted_services'):
			extracted = service['extracted_services']
			if extracted:
				print(f"    ✓ Extracted {len(extracted)} capabilities")

	return search_response