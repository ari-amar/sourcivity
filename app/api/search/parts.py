import sys
import os
sys.path.append(os.getcwd())

import re
import json
import time
from typing import List

from models import PartSearchRequest, PartSearchResponse, PartResponse, SearchEngineResult
from services.interfaces import AiClientBase, SearchEngineClientBase
from utils.pdf_scraper import PDFScraper
from prompts import SEARCH_QUERY_GENERATION_PROMPT


async def search_parts(request: PartSearchRequest, ai_client: AiClientBase, search_engine_client: SearchEngineClientBase):
	# Track timing for performance monitoring
	timing = {
		"total": 0,
		"search_query_generation": 0,
		"search_engine": 0,
		"pdf_processing": 0,
		"spec_extraction": 0
	}
	start_time = time.time()

	search_queries = []

	if request.generate_ai_search_prompt:
		# Generate optimized search query using AI
		query_gen_start = time.time()
		prompt = SEARCH_QUERY_GENERATION_PROMPT.format(user_query=request.query)

		try:
			response_text = await ai_client.generate(
				system_prompt="You are an expert at crafting search queries to find technical datasheets.",
				user_prompt=prompt,
				enforce_json=True,
				json_schema={
					"type": "object",
					"properties": {
						"search_query": {"type": "string"}
					},
					"required": ["search_query"]
				},
				max_tokens=150
			)

			# Extract JSON from response
			json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
			if json_match:
				query_result = json.loads(json_match.group())
				search_queries = [query_result.get("search_query", f'{request.query} datasheet filetype:pdf')]
			else:
				# Fallback to default query if AI fails
				search_queries = [f'{request.query} datasheet filetype:pdf']
			timing["search_query_generation"] = time.time() - query_gen_start
		except Exception as e:
			print(f"Error generating AI search query: {str(e)}")
			# Fallback to default query
			search_queries = [f'{request.query} datasheet filetype:pdf']
			timing["search_query_generation"] = time.time() - query_gen_start
	else:
		search_queries = [f'{request.query} datasheet filetype:pdf']

	search_engine_start = time.time()
	pdf_search_results: List[SearchEngineResult] = []
	for search_query in search_queries:

		# Request extra results since some may not be valid PDFs after filtering
		# We want at least 10 valid PDFs, so request 20
		prompt_results = await search_engine_client.search(query=search_query, max_results=20)

		# Filter to only include URLs that look like PDFs
		valid_pdf_results = []
		for result in prompt_results.results:
			url_lower = result.url.lower()
			# Check if URL ends with .pdf or contains .pdf in query params
			if url_lower.endswith('.pdf') or '.pdf?' in url_lower or '.pdf#' in url_lower:
				valid_pdf_results.append(result)
			else:
				print(f"Skipping non-PDF URL: {result.url[:100]}")

		print(f"Exa returned {len(prompt_results.results)} results, {len(valid_pdf_results)} are valid PDF URLs")
		pdf_search_results.extend(valid_pdf_results)

	if not pdf_search_results:
		raise Exception(f"No PDF URLs found for search queries: {search_queries}")

	# Take top 10 PDFs by score (we requested 20 to account for filtering)
	pdf_search_results.sort(key=lambda x: x.score if x.score else 0.0, reverse=True)
	pdf_search_results = pdf_search_results[:10]
	timing["search_engine"] = time.time() - search_engine_start

	print(f"Selected top {len(pdf_search_results)} PDFs by score")

	if len(pdf_search_results) < 5:
		print(f"WARNING: Only found {len(pdf_search_results)} valid PDF URLs - need at least 5 for best results")

	pdf_processing_start = time.time()
	pdf_scraper = PDFScraper(ai_client=ai_client, debug=request.debug)

	urls = [res.url for res in pdf_search_results]
	scores = [res.score if res.score is not None else 0.0 for res in pdf_search_results]
	print(f"\nFound {len(urls)} valid PDF URLs from search:")
	for i, (url, score) in enumerate(zip(urls, scores)):
		print(f"  {i+1}. [Score: {score:.3f}] {url}")

	product_type = request.query  # could be improved by extracting product type more accurately
	scrape_results = await pdf_scraper.scrape_multiple(urls=urls, scores=scores, product_type=product_type)
	timing["pdf_processing"] = time.time() - pdf_processing_start

	print(f"Scrape results: {len(scrape_results)} items")
	for i, result in enumerate(scrape_results):
		specs_count = len(result.get('specs', {})) if result.get('specs') else 0
		has_error = 'error' in result
		print(f"  {i+1}. URL: {result.get('url', 'N/A')[:50]}... Specs: {specs_count}, Error: {has_error}")

	# Convert dict results to PartResponse models
	part_responses: List[PartResponse] = [PartResponse(**result) for result in scrape_results]

	# Collect all unique spec keys from all products (AI should have standardized them)
	# Use a dict to preserve order while collecting unique keys
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
	print(f"\n⏱️  PERFORMANCE TIMING:")
	print(f"  Total: {timing['total']:.2f}s")
	print(f"  - Query Generation: {timing['search_query_generation']:.2f}s")
	print(f"  - Search Engine: {timing['search_engine']:.2f}s")
	print(f"  - PDF Processing: {timing['pdf_processing']:.2f}s")

	return PartSearchResponse(query=request.query, spec_column_names=ordered_columns, parts=part_responses, timing=timing)