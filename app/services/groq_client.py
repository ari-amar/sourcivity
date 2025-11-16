import os
from groq import Groq

QUERY_TIMEOUT = int(os.getenv("GROQ_QUERY_TIMEOUT", "60"))
QUERY_MAX_RETRIES = 3
class GroqClient:
	def __init__(self, api_key: str):
		self.client = Groq(api_key=api_key)

	def query(self, 
		   model: str, 
		   system_prompt_content: str, 
		   user_prompt_content: str, 
		   temp: float, 
		   max_tokens: int, 
		   top_p: float=None, 
		   response_format: dict=None,
		   stream: bool=None) -> dict:
		retries = 0
		while retries < QUERY_MAX_RETRIES:
			try:
				return self._query(
					model=model,
					system_prompt_content=system_prompt_content,
					user_prompt_content=user_prompt_content,
					temp=temp,
					max_tokens=max_tokens,
					top_p=top_p,
					response_format=response_format,
					stream=stream
				)
			except Exception as e:
				retries += 1
				if retries >= QUERY_MAX_RETRIES:
					raise e
				
	def _query(self, 
		   model: str, 
		   system_prompt_content: str, 
		   user_prompt_content: str, 
		   temp: float, 
		   max_tokens: int, 
		   top_p: float=None, 
		   response_format: dict=None,
		   stream: bool=None) -> dict:
		
		chat_completion = self.client.chat.completions.create(
			messages=[
			{"role": "system", "content": system_prompt_content},
			{"role": "user", "content": user_prompt_content}
			],
			model=model,
			temperature=temp,
			max_tokens=max_tokens,
			top_p=top_p,
			response_format=response_format,
			stream=stream,
			timeout=QUERY_TIMEOUT
		) 
		return chat_completion.response
		