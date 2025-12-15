from typing import List
from exa_py import Exa
from services.interfaces.search_engine_client_base import SearchEngineClientBase
from models import SearchEngineClientResponse, SearchEngineResult

class ExaClient(SearchEngineClientBase):

	def __init__(self,
			  api_key: str,
			  search_type: str = "auto",
			  include_text: bool = False,
			  text_length_limit: int = 1000):
		"""
		Initialize Exa search client.

		Args:
			api_key: Exa API key
			search_type: Type of search - "auto", "neural", or "keyword" (default: "auto")
			include_text: Whether to include page text content (default: False, saves credits)
			text_length_limit: Max characters of text to return if include_text=True
		"""
		self.api_key = api_key
		self.exa = Exa(api_key=api_key)
		self.search_type = search_type
		self.include_text = include_text
		self.text_length_limit = text_length_limit

	async def _search(self, query: str, max_results: int = 10) -> SearchEngineClientResponse:
		"""
		Search using Exa API.

		Args:
			query: Search query
			max_results: Maximum number of results to return

		Returns:
			dict: Search results with 'results' list containing title, url, score, and optional text
		"""
		try:
			# Exa search is synchronous, but we're in async context
			# Note: If Exa adds async support, we can use that instead
			results = self.exa.search(
				query,
				type=self.search_type,
				num_results=max_results,
			)

			# Get text content if requested
			if self.include_text and results.results:
				# Get IDs of results
				result_ids = [r.id for r in results.results]
				contents = self.exa.get_contents(
					result_ids,
					text={"max_characters": self.text_length_limit}
				)

				# Merge text into results
				formatted_results = []
				for i, result in enumerate(results.results):
					formatted_results.append(
						SearchEngineResult(
							title=result.title,
							url=result.url,
							score=getattr(result, 'score', None),
							text=contents.results[i].text if i < len(contents.results) else None,
							published_date=getattr(result, 'published_date', None),
							author=getattr(result, 'author', None)
						))
			else:
				# Format results without text
				formatted_results = []
				for result in results.results:
					formatted_results.append(SearchEngineResult(
							title=result.title,
							url=result.url,
							score=getattr(result, 'score', None),
							published_date=getattr(result, 'published_date', None),
							author=getattr(result, 'author', None)
						)
					)

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

	exa_client = ExaClient(api_key=exa_api_key, include_text=True)

	# Test with industrial parts search
	sample_part_search = "industrial motor 3-phase 400V 50Hz IP55 TEFC 15 kW 1500 rpm foot-mounted IEC frame 160L flange B5"
	resp = asyncio.run(exa_client.search(query=sample_part_search, max_results=5))

	print(f"\nFound {len(resp['results'])} results:")
	print(f"Optimized query: {resp['autoprompt_string']}\n")

	for i, result in enumerate(resp['results'], 1):
		print(f"{i}. {result['title']}")
		print(f"   URL: {result['url']}")
		if result.get('score'):
			print(f"   Score: {result['score']:.4f}")
		if result.get('text'):
			print(f"   Preview: {result['text'][:200]}...")
		print()

	# Save to file
	with open(os.path.join(os.path.dirname(__file__), "exa_test.json"), "w") as f:
		import json
		json.dump(resp, f, indent=4)