import sys
import os
sys.path.append(os.getcwd())

from typing import List

from models import PartSearchRequest, PartSearchResponse, PartResponse, SearchEngineClientResponse, SearchEngineResult
from services.interfaces import AiClientBase, SearchEngineClientBase
from utils.pdf_scraper import PDFScraper


async def search_parts(request: PartSearchRequest, ai_client: AiClientBase, search_engine_client: SearchEngineClientBase):

	results = []
	search_queries = []
	
	if request.generate_ai_search_prompt:
		# get search prompts from AI client
		pass
	else:
		search_queries = [f'{request.query} datasheet filetype:pdf']

	pdf_search_results: List[SearchEngineResult] = []
	for search_query in search_queries:

		prompt_results = await search_engine_client.search(query=search_query, max_results=1)

		pdf_search_results.extend(prompt_results.results)

	if pdf_search_results:
		pdf_scraper = PDFScraper(ai_client=ai_client)

		urls = [res.url for res in pdf_search_results]
		product_type = request.query  # could be improved by extracting product type more accurately
		part_responses: List[PartResponse] = await pdf_scraper.scrape_multiple(urls=urls, product_type=product_type)
	else:
		raise Exception(f"No results found for the following search queries: {search_queries}")
	
	# extract product specs from part responses
	spec_column_names = []
	for resp in part_responses:
		if resp.specs:
			for key in resp.specs.keys():
				if key not in spec_column_names:
					spec_column_names.append(key)

	return PartSearchResponse(query=request.query, spec_column_names=spec_column_names, parts=part_responses)

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






