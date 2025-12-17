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
		scrape_results = await pdf_scraper.scrape_multiple(urls=urls, product_type=product_type)

		# Convert dict results to PartResponse models
		part_responses: List[PartResponse] = [PartResponse(**result) for result in scrape_results]
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