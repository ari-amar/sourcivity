import os
from typing import Dict
from fastapi import FastAPI, Response

from enums import AiClientName, SearchEngineClientName
from models import *
from services.interfaces import AiClientBase, SearchEngineClientBase
from services.ai_clients import *
from services.search_engine_clients import *

from search import search_parts, search_services

app = FastAPI()

# NOTE: it might make sense to move client initialization elsewhere in the future to keep the code clean while we test options

cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
cloudflare_workers_key = os.getenv("CLOUDFLARE_WORKERS_KEY")
cloudflare_client = CloudflareAiClient(account_id=cloudflare_account_id, api_token=cloudflare_workers_key)

# Initialize Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = AnthropicAiClient(api_key=anthropic_api_key)

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

	search_response =  await search_parts(
		request=payload,
		ai_client=ai_client,
		search_engine_client=search_engine_client
	)
	
	return search_response


@app.post('/api/search/services')
async def api_search_services(payload):
	
	ai_client = AI_CLIENTS.get(payload.ai_client_name, None)
	search_engine_client = SEARCH_ENGINE_CLIENTS.get(payload.search_engine_client_name, None)

	search_response =  await search_services(
		request=payload,
		ai_client=ai_client,
		search_engine_client=search_engine_client
	)
	
	return search_response