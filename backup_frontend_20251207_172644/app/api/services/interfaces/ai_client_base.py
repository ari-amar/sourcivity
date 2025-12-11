from typing import List
from abc import ABC, abstractmethod

class AiClientBase(ABC):

	async def generate_search_prompts(self, component_description: str) -> List[str]:

		# common search prompt generation logic here if needed
		return await self._generate_search_prompts(component_description)

	@abstractmethod
	async def _generate_search_prompts(self, component_description: str) -> List[str]:
		"""
		Code for AI generated search prompt
		"""