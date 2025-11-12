import os
from groq import Groq

class GroqClient:
	def __init__(self, api_key: str):
		self.client = Groq(api_key=api_key)

	def query(self, 
		   model: str, 
		   system_prompt: str | dict, 
		   user_prompt: str | dict, 
		   temp: float, 
		   max_tokens: int, 
		   top_p: float=None, 
		   response_format: dict=None,
		   stream: bool=None) -> dict:
		
		chat_completion = self.client.chat.completions.create(
			messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt}
			],
			model=model,
			temperature=temp,
			max_tokens=max_tokens,
			top_p=top_p,
			response_format=response_format,
			stream=stream
		) 
		