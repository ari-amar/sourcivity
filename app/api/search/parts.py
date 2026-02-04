import sys
import os
sys.path.append(os.getcwd())

import re
import json
import time
from typing import List, Optional

from models import PartSearchRequest, PartSearchResponse, PartResponse, SearchEngineResult
from services.interfaces import AiClientBase, SearchEngineClientBase
from utils.pdf_scraper import PDFScraper
from prompts import CATEGORY_TERMS_PROMPT


async def get_category_phrase(product_query: str, ai_client: AiClientBase) -> Optional[str]:
	"""
	Use AI to generate a category-specific phrase for filtering search results.
	This phrase ensures search returns comparable products from the same category.

	Note: Exa only supports ONE phrase of up to 5 words for include_text.
	"""
	try:
		prompt = CATEGORY_TERMS_PROMPT.format(product_query=product_query)

		response = await ai_client.generate(
			system_prompt="You are an industrial product expert who identifies technical specification terms.",
			user_prompt=prompt,
			enforce_json=True,
			max_tokens=300
		)

		# Parse JSON response
		json_match = re.search(r'\{.*\}', response, re.DOTALL)
		if json_match:
			data = json.loads(json_match.group())
			phrase = data.get("phrase", "")
			reasoning = data.get("reasoning", "")

			if phrase and len(phrase.strip()) > 0:
				# Ensure phrase is max 5 words (Exa limit)
				words = phrase.strip().split()
				if len(words) > 5:
					phrase = " ".join(words[:5])
					print(f"[Category Phrase] Truncated to 5 words: {phrase}")

				print(f"[Category Phrase] Generated for '{product_query}': \"{phrase}\"")
				print(f"[Category Phrase] Reasoning: {reasoning}")
				return phrase

		print(f"[Category Phrase] Failed to parse response, proceeding without filter")
		return None

	except Exception as e:
		print(f"[Category Phrase] Error generating phrase: {e}, proceeding without filter")
		return None


async def search_parts(request: PartSearchRequest, ai_client: AiClientBase, search_engine_client: SearchEngineClientBase):
	# Track timing for performance monitoring
	timing = {
		"total": 0,
		"category_terms": 0,
		"search_engine": 0,
		"pdf_processing": 0,
	}
	start_time = time.time()

	# Step 1: Generate category-specific phrase for search filtering
	category_start = time.time()
	category_phrase = await get_category_phrase(request.query, ai_client)
	timing["category_terms"] = time.time() - category_start

	# Build search query directly (no AI query generation)
	search_query = f'{request.query} datasheet'

	search_engine_start = time.time()
	pdf_search_results: List[SearchEngineResult] = []

	# Request 20 results from Exa with optional category filter
	# Note: Exa include_text expects a list with a single phrase (max 5 words)
	include_text = [category_phrase] if category_phrase else None
	prompt_results = await search_engine_client.search(
		query=search_query,
		max_results=20,
		include_text=include_text  # Filter by category-specific phrase
	)
	pdf_search_results.extend(prompt_results.results)

	print(f"Exa returned {len(prompt_results.results)} results")

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
		has_error = 'error' in result
		print(f"  {i+1}. URL: {result.get('url', 'N/A')[:50]}... Specs: {specs_count}, Error: {has_error}")

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
	print(f"  - Category Terms: {timing['category_terms']:.2f}s")
	print(f"  - Search Engine: {timing['search_engine']:.2f}s")
	print(f"  - PDF Processing: {timing['pdf_processing']:.2f}s")

	return PartSearchResponse(query=request.query, spec_column_names=ordered_columns, parts=part_responses, timing=timing)
