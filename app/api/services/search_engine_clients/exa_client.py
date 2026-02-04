from typing import List, Optional
from exa_py import Exa
from services.interfaces.search_engine_client_base import SearchEngineClientBase
from models import SearchEngineClientResponse, SearchEngineResult

class ExaClient(SearchEngineClientBase):

	def __init__(self,
			  api_key: str,
			  search_type: str = "neural"):
		"""
		Initialize Exa search client.

		Args:
			api_key: Exa API key
			search_type: Type of search - "neural", "keyword", or "auto" (default: "neural")

		Note:
			- Default is "neural" because it's the ONLY type that returns relevance scores
			- "auto" and "keyword" searches return None for scores
			- Contents are always disabled (contents=False) to save tokens
			- We download PDFs directly and extract markdown ourselves
		"""
		self.api_key = api_key
		self.exa = Exa(api_key=api_key)
		self.search_type = search_type

	async def _search(self, query: str, max_results: int = 10, include_text: Optional[List[str]] = None) -> SearchEngineClientResponse:
		"""
		Search using Exa API.

		Args:
			query: Search query
			max_results: Maximum number of results to return
			include_text: Optional list of terms that MUST appear in results (filters by product category)

		Returns:
			dict: Search results with 'results' list containing title, url, score, and optional text
		"""
		try:
			# Build search parameters
			search_params = {
				"query": query,
				"type": self.search_type,
				"num_results": max_results,
				"contents": False  # Don't fetch page contents - we extract PDFs directly
			}

			# Add include_text filter if provided (forces category consistency)
			if include_text and len(include_text) > 0:
				search_params["include_text"] = include_text
				print(f"[Exa] Using include_text filter: {include_text}")

			# Exa search is synchronous, but we're in async context
			results = self.exa.search(**search_params)

			# Log score summary for verification
			if results.results:
				scores = [r.score for r in results.results if r.score]
				if scores:
					print(f"[Exa] Found {len(results.results)} PDFs (scores: {min(scores):.3f}-{max(scores):.3f})")
				else:
					print(f"[Exa] Warning: Found {len(results.results)} PDFs but no scores returned")

			# Format results (no text content since contents=False)
			formatted_results = []
			for result in results.results:
				formatted_results.append(SearchEngineResult(
					title=result.title,
					url=result.url,
					score=getattr(result, 'score', None),
					published_date=getattr(result, 'published_date', None),
					author=getattr(result, 'author', None)
				))

			return SearchEngineClientResponse(
				prompt=query,
				results=formatted_results
			)
		except Exception as e:
			raise Exception(f"Exa search error: {str(e)}")


if __name__ == "__main__":
	import os
	import asyncio
	from dotenv import load_dotenv

	env_file_name = os.path.join(os.getcwd(), "config", "env.config")
	if not os.path.exists(env_file_name):
		raise FileNotFoundError("env.config file is missing in the config folder.")

	load_dotenv(env_file_name)

	exa_api_key = os.getenv("EXA_API_KEY")
	if not exa_api_key:
		raise ValueError("EXA_API_KEY not found in environment variables")

	exa_client = ExaClient(api_key=exa_api_key)

	# Test with industrial parts search
	sample_part_search = "industrial motor 3-phase 400V 50Hz IP55 TEFC 15 kW 1500 rpm foot-mounted IEC frame 160L flange B5"
	resp = asyncio.run(exa_client.search(query=sample_part_search, max_results=5))

	print(f"\nFound {len(resp.results)} results:")
	print(f"Query: {resp.prompt}\n")

	for i, result in enumerate(resp.results, 1):
		print(f"{i}. {result.title}")
		print(f"   URL: {result.url}")
		if result.score:
			print(f"   Score: {result.score:.4f}")
		print()

	# Save to file
	with open(os.path.join(os.path.dirname(__file__), "exa_test.json"), "w") as f:
		import json
		json.dump(resp.model_dump(), f, indent=4)