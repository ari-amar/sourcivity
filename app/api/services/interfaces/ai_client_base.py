from typing import Dict, Any
from abc import ABC, abstractmethod

class AiClientBase(ABC):

	async def generate(self,
					 prompt: str, 
					 enforce_json: bool = False, 
					 json_schema: Dict[str, Any]=None,
					 max_tokens: int = 500):
		"""
		Docstring for generate
		
		:param self: Description
		:param prompt: Description
		:type prompt: str
		:param enforce_json: Description
		:type enforce_json: bool
		:param json_schema: Description
		:type json_schema: Dict[str, Any]
		:param max_tokens: Description
		:type max_tokens: int
		"""
		# add common functionality for logging, etc here
		return await self._generate(prompt=prompt, 
									enforce_json=enforce_json,
									json_schema=json_schema,
									max_tokens=max_tokens)

	@abstractmethod
	async def _generate(self, 
						prompt: str, 
						enforce_json: bool = False,
						json_schema: Dict[str, Any]=None,
						max_tokens: int = 500):
		"""
		Implementation of text generation for specific AI client
		"""