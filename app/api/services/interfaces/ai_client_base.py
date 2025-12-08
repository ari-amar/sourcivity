from typing import List
from abc import ABC, abstractmethod

class AiClientBase(ABC):

	@abstractmethod
	async def generate_search_prompts(self, component_description: str, max_prompts: int) -> List[str]:
		"""
		Code to query API for AI generated search prompt
		"""

	@abstractmethod
	async def ex