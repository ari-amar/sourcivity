from typing import List
from abc import ABC, abstractmethod
from models import SearchEngineClientResponse

class SearchEngineClientBase(ABC):

	async def search(self, query: str, max_results: int) -> SearchEngineClientResponse:
		# add common functionality for logging, etc here
		return await self._search(query=query, max_results=max_results)

	@abstractmethod
	async def _search(self, query: str, max_results: int) -> SearchEngineClientResponse:
		"""
		Implementation of search for specific search engine client
		"""