import sys
import os
sys.path.append(os.getcwd())

import time
from typing import List
from urllib.parse import urlparse

from models import PartSearchRequest, PartSearchResponse, PartResponse, SearchEngineResult
from services.interfaces import AiClientBase, SearchEngineClientBase
from utils.pdf_scraper import PDFScraper


async def search_parts(request: PartSearchRequest, ai_client: AiClientBase, search_engine_client: SearchEngineClientBase):
	# Track timing for performance monitoring
	timing = {
		"total": 0,
		"search_engine": 0,
		"pdf_processing": 0,
	}
	start_time = time.time()

	# Build search query with "datasheet" to find product datasheets
	search_query = f'{request.query} datasheet'

	search_engine_start = time.time()
	pdf_search_results: List[SearchEngineResult] = []

	# Request 10 results from Exa (reduced from 20 for faster processing)
	prompt_results = await search_engine_client.search(
		query=search_query,
		max_results=10
	)
	pdf_search_results.extend(prompt_results.results)

	print(f"Exa returned {len(prompt_results.results)} results")

	# Deduplicate by URL path/filename (removes regional duplicates like /us/en/ vs /gb/en/)
	seen_paths = set()
	unique_results = []
	for result in pdf_search_results:
		path = urlparse(result.url).path.split('/')[-1]
		if path and path not in seen_paths:
			seen_paths.add(path)
			unique_results.append(result)
	pdf_search_results = unique_results
	print(f"After deduplication: {len(pdf_search_results)} unique results")

	if not pdf_search_results:
		raise Exception(f"No results found for search query: {search_query}")

	# Sort by score, keep all 20
	pdf_search_results.sort(key=lambda x: x.score if x.score else 0.0, reverse=True)
	timing["search_engine"] = time.time() - search_engine_start

	print(f"Processing all {len(pdf_search_results)} results by score")

	if len(pdf_search_results) < 5:
		print(f"WARNING: Only found {len(pdf_search_results)} results - need at least 5 for best results")

	pdf_processing_start = time.time()
	pdf_scraper = PDFScraper(ai_client=ai_client, debug=request.debug)

	urls = [res.url for res in pdf_search_results]
	scores = [res.score if res.score is not None else 0.0 for res in pdf_search_results]
	print(f"\nFound {len(urls)} URLs from search:")
	for i, (url, score) in enumerate(zip(urls, scores)):
		print(f"  {i+1}. [Score: {score:.3f}] {url}")

	product_type = request.query
	scrape_results = await pdf_scraper.scrape_multiple(urls=urls, scores=scores, product_type=product_type)
	timing["pdf_processing"] = time.time() - pdf_processing_start

	print(f"Scrape results: {len(scrape_results)} items")
	for i, result in enumerate(scrape_results):
		specs_count = len(result.get('specs', {})) if result.get('specs') else 0
		error_msg = result.get('error')
		print(f"  {i+1}. URL: {result.get('url', 'N/A')[:50]}... Specs: {specs_count}, Error: {error_msg or 'None'}")

	# Convert dict results to PartResponse models
	part_responses: List[PartResponse] = [PartResponse(**result) for result in scrape_results]

	# Collect all unique spec keys from all products
	all_spec_keys = {}
	for part in part_responses:
		if part.specs:
			for key in part.specs.keys():
				if key != "error":
					all_spec_keys[key] = True

	ordered_columns = list(all_spec_keys.keys())

	timing["total"] = time.time() - start_time

	print(f"\nFINAL RESULTS:")
	print(f"  Total spec columns: {len(ordered_columns)}")
	print(f"  Columns: {ordered_columns}")
	print(f"  Total parts: {len(part_responses)}")
	print(f"\n  PERFORMANCE TIMING:")
	print(f"  Total: {timing['total']:.2f}s")
	print(f"  - Search Engine: {timing['search_engine']:.2f}s")
	print(f"  - PDF Processing: {timing['pdf_processing']:.2f}s")

	return PartSearchResponse(query=request.query, spec_column_names=ordered_columns, parts=part_responses, timing=timing)
