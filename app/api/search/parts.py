import sys
import os
sys.path.append(os.getcwd())

from services.interfaces import AiClientBase, SearchEngineClientBase
from constants import GRAY_MARKET_SITES

async def search_parts(ai_client: AiClientBase, search_client: SearchEngineClientBase, query: str):

	results = []
	#search_queries = await ai_client.generate_search_prompts(component_description=query)
	#print(search_queries)
	gray_market_removal_str = " ".join(f'-{site}' for site in GRAY_MARKET_SITES)
	search_queries = [f'{query} "datasheet"  OR "specifications" OR "product page" {gray_market_removal_str}']

	for search_query in search_queries:

		sq_results = await search_client.search(query=search_query, max_results=5)

		results.extend(sq_results.get("results"))

	print(results)


if __name__ == "__main__":

	import asyncio
	from dotenv import load_dotenv
	from services.ai_clients import AnthropicClient
	from services.search_engine_clients import TavilyClient

	env_file_name = os.path.join(os.getcwd(), "config", "env.config")
	if not os.path.exists(env_file_name):
		raise FileNotFoundError("env.config file is missing in the config folder.")
	
	load_dotenv(env_file_name)

	ai_client = AnthropicClient(os.getenv("ANTHROPIC_API_KEY"))
	search_client = TavilyClient(os.getenv("TAVILY_API_KEY"))
	query = "100 sccm mass flow controller"

	asyncio.run(search_parts(ai_client=ai_client, search_client=search_client, query=query))






