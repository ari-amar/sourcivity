import os
import sys
sys.path.append(os.getcwd())
from typing import List
import fitz
import asyncio
import httpx
from dotenv import load_dotenv

from constants import DATASHEET_CACHE_DIR
from services import AnthropicClient, DuckDuckGoClient
from search import search_datasheets

def download_pdf_files(urls: List[str]):

	out_dir = os.path.join(os.getcwd(), DATASHEET_CACHE_DIR)
	headers = {
			    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
			    "Accept": "*/*",
			}

	for i, url in enumerate(urls):
	
		with httpx.Client(timeout=10.0, follow_redirects=True) as client:
			response = client.get(url, headers=headers)
		response.raise_for_status()
            
		byte_content = response.content

		with open(os.path.join(out_dir, f"pdf_{i}.pdf"), "wb") as f:
			f.write(byte_content)

if __name__ == "__main__":

	env_file_name = os.path.join(os.getcwd(), "config", "env.config")
	if not os.path.exists(env_file_name):
		raise FileNotFoundError("env.config file is missing in the config folder.")
	
	load_dotenv(env_file_name)

	
	anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
	anthropic_ai_client = AnthropicClient(api_key=anthropic_api_key)
	duckduckgo_client = DuckDuckGoClient()

	query = "100 sccm mass flow controller"
	urls = asyncio.run(search_datasheets(anthropic_ai_client, duckduckgo_client, query))

	download_pdf_files(urls)
	print("hello")