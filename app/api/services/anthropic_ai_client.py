import os
import httpx
import sys
import json

from prompts import (
	ANTRHOPIC_SUPPLIER_QUALITY_SYSTEM_PROMPT, ANTRHOPIC_SUPPLIER_QUALITY_USER_PROMPT,
	ANTRHOPIC_SEARCH_GEN_SYSTEM_PROMPT, ANTRHOPIC_SEARCH_GEN_USER_PROMPT,
	ANTHROPIC_SPEC_EXTRACTION_SYSTEM_PROMPT, ANTHROPIC_SPEC_EXTRACTION_USER_PROMPT,
	ANTHROPIC_VALIDATE_URL_SYSTEM_PROMPT, ANTHROPIC_VALIDATE_URL_USER_PROMPT
)
from constants import ANTHROPIC_API_URL

class AnthropicClient():

	def __init__(self, api_key: str):
		self.api_key=api_key

	async def _call_claude(self, prompt, system_prompt=None):
		"""Call Claude API to get intelligent responses."""
		headers = {
		    "x-api-key": self.api_key,
		    "anthropic-version": "2023-06-01",
		    "content-type": "application/json"
		}

		messages = [
		    {
		        "role": "user",
		        "content": prompt
		    }
		]

		data = {
		    "model": "claude-3-haiku-20240307",
		    "max_tokens": 2048,
		    "messages": messages
		}

		if system_prompt:
			data["system"] = system_prompt

		try:
			async with httpx.AsyncClient(timeout=120) as client:
				response = client.post(ANTHROPIC_API_URL, headers=headers, json=data, timeout=30)
				response.raise_for_status()
				result = response.json()
				return result['content'][0]['text']
		except Exception as e:
			print(f"\nClaude API error: {e}", file=sys.stderr)
			try:
				if 'response' in locals():
					error_data = response.json()
					print(f"Error details: {error_data.get('error', {}).get('message', 'Unknown error')}", file=sys.stderr)
					if 'not_found_error' in str(error_data):
						print("\nNote: The API key may be invalid or expired.", file=sys.stderr)
						print("Please set a valid Anthropic API key using: export ANTHROPIC_API_KEY=your-key-here", file=sys.stderr)
			except:
				pass
			return None

	async def generate_search_prompt(self, component_description: str):
            
		system_prompt = ANTRHOPIC_SEARCH_GEN_SYSTEM_PROMPT
		prompt = ANTRHOPIC_SEARCH_GEN_USER_PROMPT.format(component_description=component_description) 
            
		search_query_result = await self._call_claude(prompt, system_prompt)
            
		if not search_query_result:
			return ""

		# Clean up the search query
		search_query = search_query.strip().strip('"\'')

		supplier_info = await self.assess_supplier_quality_llm(component_description)
            
		if supplier_info and 'tier1_domains' in supplier_info and len(supplier_info['tier1_domains']) > 0:
			# Add top 3 Tier 1 suppliers to search query using site: operator
			top_suppliers = supplier_info['tier1_domains'][:3]
			site_boost = " (" + " OR ".join([f"site:{domain}" for domain in top_suppliers]) + ")"
			search_query = search_query + site_boost
                  
		return search_query, supplier_info

	async def assess_supplier_quality_llm(self, component_description):
		"""Use LLM to identify the most reliable suppliers for this component category."""
		system_prompt = ANTRHOPIC_SUPPLIER_QUALITY_SYSTEM_PROMPT	
		prompt = ANTRHOPIC_SUPPLIER_QUALITY_USER_PROMPT.format(component_description=component_description)
		
		response = await self._call_claude(prompt, system_prompt)
		
		if not response:		
			return None

		try:
			response = response.strip()
			# Remove markdown code blocks if present
			if response.startswith('```'):
				lines = response.split('\n')
				response = '\n'.join([l for l in lines if not l.startswith('```')])
				response = response.strip()

			supplier_info = json.loads(response)
			return supplier_info
		
		except:
			return None

	async def extract_specifications(self, query: str):

		system_prompt = ANTHROPIC_SPEC_EXTRACTION_SYSTEM_PROMPT
		prompt = ANTHROPIC_SPEC_EXTRACTION_USER_PROMPT.format(query=query)

		response = await self._call_claude(prompt, system_prompt)

		if not response:
			return {}

		try:
			# Clean up response and parse JSON
			response = response.strip()
			specs = json.loads(response)
			return specs
		except:
			return {}
		
			
	async def validate_url_specs(self, url, query_specs):

		system_prompt = ANTHROPIC_VALIDATE_URL_SYSTEM_PROMPT
		prompt = ANTHROPIC_VALIDATE_URL_USER_PROMPT.format(url=url, query_specs=query_specs)

		response = await self._call_claude(prompt, system_prompt)

		return not response or response.strip().upper() == "YES"