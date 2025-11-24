from services import TavilyClient, CloudflareAIClient
from utils import contains_technical_specifications
from constants import CLOUDFLARE_LLAMA_3_2

async def _tavily_part_search(client: TavilyClient, query: str, max_results: int = 10) -> dict:
	return await client.search(query=query, max_results=max_results)

async def _cloudflare_ai_analyze_search_results(client: CloudflareAIClient, model: str, query: str, has_query_specs: bool, search_results: list):
	return await client.analyze_search_results(model=model, query=query, has_query_specs=has_query_specs, search_results=search_results)

async def search_parts(client: TavilyClient, ai_client: CloudflareAIClient, query: str, location_filter: str = "global suppliers") -> dict:
	
	has_specs = contains_technical_specifications(query)
	travily_response = await _tavily_part_search(client=client, query=f"{query} | {location_filter}", max_results=5)
	
	ai_analysis = await _cloudflare_ai_analyze_search_results(
		client=ai_client,
		model=CLOUDFLARE_LLAMA_3_2,
		query=query,
		has_query_specs=has_specs,
		search_results=travily_response.get("results", [])
	)
	return {
		"part_search_results": travily_response,
		"ai_analysis": ai_analysis
	}

