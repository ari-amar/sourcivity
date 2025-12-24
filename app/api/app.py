import os
from typing import Dict
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from enums import AiClientName, SearchEngineClientName
from models import *
from services.interfaces import AiClientBase, SearchEngineClientBase
from services.ai_clients import *
from services.search_engine_clients import *

from search import search_parts, search_services

app = FastAPI()

# CORS configuration - allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default development server
        "http://localhost:3001",  # Alternative Next.js port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# NOTE: it might make sense to move client initialization elsewhere in the future to keep the code clean while we test options

cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
cloudflare_workers_key = os.getenv("CLOUDFLARE_WORKERS_KEY")
cloudflare_client = CloudflareAiClient(account_id=cloudflare_account_id, api_token=cloudflare_workers_key)

# Initialize Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = AnthropicAiClient(
    api_key=anthropic_api_key,
    model="claude-3-haiku-20240307"  # Using Haiku (Sonnet not available on this API key)
)

# TODO: initialize other AI clients here

AI_CLIENTS: Dict[str, AiClientBase] = {
	AiClientName.CLOUDFLARE: cloudflare_client,
	AiClientName.ANTHROPIC: anthropic_client,
}


exa_api_key = os.getenv("EXA_API_KEY")
exa_client = ExaClient(api_key = exa_api_key)

# TODO: initialize other search engine clients here

SEARCH_ENGINE_CLIENTS: Dict[str, SearchEngineClientBase] = {
	SearchEngineClientName.EXA: exa_client,
	# TODO: register other search engine clients here
}

# NOTE: if we want to have different search prompts per AI client, we can add a similar dictionary for that as well


@app.get("/api/health")
async def health_check():
	return Response(content="OK", media_type="text/plain")

@app.get("/api/available_client_names")
async def get_available_client_names() -> AvailableClientResponse:

	# NOTE: we could potentially update this to run health checks on the available clients as well, or even get usage/cost metrics
	return AvailableClientResponse(
		ai_client_names=AI_CLIENTS.keys(),
		search_engine_client_names=SEARCH_ENGINE_CLIENTS.keys()
	)

@app.post('/api/search/parts')
async def api_search_parts(payload: PartSearchRequest) -> PartSearchResponse:

	ai_client = AI_CLIENTS.get(payload.ai_client_name, None)
	search_engine_client = SEARCH_ENGINE_CLIENTS.get(payload.search_engine_client_name, None)

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

	ai_client = AI_CLIENTS.get(payload.ai_client_name, None)
	search_engine_client = SEARCH_ENGINE_CLIENTS.get(payload.search_engine_client_name, None)

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