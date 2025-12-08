import os
from fastapi import Request, FastAPI, Response, UploadFile, File, Header, HTTPException
from models import *
from services import *
from search import search_parts, search_datasheets


app = FastAPI()

tavily_api_key = os.getenv("TAVILY_API_KEY")
cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
cloudflare_workers_key = os.getenv("CLOUDFLARE_WORKERS_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")


tavily_client = TavilyClient(api_key=tavily_api_key)
cloudflare_ai_client = CloudflareAIClient(account_id=cloudflare_account_id, workers_key=cloudflare_workers_key)
anthropic_ai_client = AnthropicClient(api_key=anthropic_api_key)
duckduckgo_client = DuckDuckGoClient()

@app.get("/api/health")
async def health_check():
	return Response(content="OK", media_type="text/plain")

@app.post('/api/search/parts')
async def api_search_parts(payload: PartsSearchRequest):

	search_response =  await search_parts(
		client=tavily_client,
		ai_client=cloudflare_ai_client,
		query=payload.query,
		location_filter=payload.location_filter
	)
	with open(os.path.join(os.path.dirname(__file__), "part_search_sample_out.json"), "w") as f:
		import json
		json.dump(search_response, f, indent=4)
	return search_response

@app.post('/api/search/datasheets')
async def api_search_datasheets(payload: DatasheetSearchRequest):
	search_response = await search_datasheets(
		anthropic_client=anthropic_ai_client,
		duckduck_client=duckduckgo_client,
		component_description=payload.component_description,
		max_results=payload.max_results
	)

	return search_response

@app.post('/api/search/services')
async def api_search_services(payload: ServicesSearchRequest):
	return {"message": "Service search is not yet implemented."}