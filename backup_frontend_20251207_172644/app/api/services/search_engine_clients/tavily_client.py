import httpx
from services.interfaces.search_engine_client_base import SearchEngineClientBase

class TavilyClient(SearchEngineClientBase):

	def __init__(self, 
			  api_key: str,
			  search_depth: str = "advanced", 
			  include_answer: bool =False,
			  include_raw_content: bool =True):
		self.api_key = api_key
		self.base_url = "https://api.tavily.com"
		self.search_depth = search_depth
		self.include_answer = include_answer
		self.include_raw_content = include_raw_content

	async def _search(self, query: str, max_results: int = 10):
		payload = {
			"api_key": self.api_key,
			"query": query,
			"search_depth": self.search_depth,
			"max_results": max_results,
			"include_answer": self.include_answer,
			"include_raw_content": self.include_raw_content
		}
		async with httpx.AsyncClient(timeout=120) as client:
			response = await client.post(f"{self.base_url}/search", json=payload)
			response.raise_for_status()
			return response.json()

if __name__ == "__main__":
	import os
	import asyncio
	from dotenv import load_dotenv

	env_file_name = os.path.join(os.getcwd(), "config", "env.config")
	if not os.path.exists(env_file_name):
		raise FileNotFoundError("env.config file is missing in the config folder.")
	
	load_dotenv(env_file_name)

	travily_api_key = os.getenv("TAVILY_API_KEY")
	travily_client = TavilyClient(api_key=travily_api_key)
	
	sample_part_search = "industrial motor 3-phase 400V 50Hz IP55 TEFC 15 kW 1500 rpm foot-mounted IEC frame 160L flange B5"
	resp = asyncio.run(travily_client.search(query=sample_part_search, max_results=5))
	with open(os.path.join(os.path.dirname(__file__), "vendor_tst.json"), "w") as f:
		import json
		json.dump(resp, f, indent=4)