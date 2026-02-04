from typing import List, Optional
from abc import ABC, abstractmethod
from models import SearchEngineClientResponse

class SearchEngineClientBase(ABC):

	async def search(self, query: str, max_results: int, include_text: Optional[List[str]] = None) -> SearchEngineClientResponse:
		"""
		Search for results matching the query.

		Args:
			query: Search query string
			max_results: Maximum number of results to return
			include_text: Optional list of terms that MUST appear in results (for filtering by product category)
		"""
		return await self._search(query=query, max_results=max_results, include_text=include_text)

	@abstractmethod
	async def _search(self, query: str, max_results: int, include_text: Optional[List[str]] = None) -> SearchEngineClientResponse:
		"""
		Implementation of search for specific search engine client
		"""