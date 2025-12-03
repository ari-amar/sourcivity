from abc import ABC, abstractmethod

class SearchEngineClientBase(ABC):

	async def search(self, query: str, max_results: int):
		# add common functionality for logging, etc here
		return await self._search(query=query, max_results=max_results)

	@abstractmethod
	async def _search(self, query: str, max_results: int):
		"""
		Implementation of search for specific search engine client
		"""