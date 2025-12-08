import os
from fastapi import Request, FastAPI, Response, UploadFile, File, Header, HTTPException
from models import *
from services import *
from search import search_parts


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
async def api_search_parts(payload: PartSearchRequest) -> PartSearchResponse:

	search_response =  await search_parts(
		client=tavily_client,
		ai_client=cloudflare_ai_client,
		query=payload.query,
		location_filter=payload.location_filter
	)
	
	return search_response
