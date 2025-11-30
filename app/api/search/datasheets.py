from typing import List, Tuple
import httpx

from services import AnthropicClient, DuckDuckGoClient
from constants import DATASHEET_CACHE_DIR


async def search_datasheets(anthropic_client: AnthropicClient, 
                      duckduck_client: DuckDuckGoClient, 
                      component_description,
                      max_results:int = 5):

	search_query, supplier_info = await anthropic_client.generate_search_prompt(component_description)
	pdf_urls = await duckduck_client.search_duckduckgo(search_query, max_results * 3)
    
	validated_with_scores:List[Tuple[str, int]] = []
	query_specs = await anthropic_client.extract_specifications(component_description)
    
	for url in pdf_urls:
        
		try:

			url_lower = url.lower()
			if any(word in url_lower for word in ['catalog', 'catalogue', 'manual', 'guide', 'brochure', 'series-']):
				continue
            
			headers = {
			    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
			    "Range": "bytes=0-1024",  # Request only the first 4KB (4096 bytes)
			    "Accept": "*/*",
			}

			# Synchronous version using httpx.Client (recommended for this use case)
			with httpx.Client(timeout=10.0, follow_redirects=True) as client:
				response = client.get(url, headers=headers)
			response.raise_for_status()
            
			byte_content = response.content
            
			if byte_content.startswith(b'%PDF-'):

				# Use LLM to validate URL matches query specifications
				if query_specs:
					if not await anthropic_client.validate_url_specs(url, query_specs):
						continue

				# Rank URL by supplier quality
				supplier_score = rank_url_by_supplier(url, supplier_info)

				# Skip gray market sites
				if supplier_score == 999:
					continue

				validated_with_scores.append((url, supplier_score))

		except Exception as e:
			print(e)
			continue
    
	validated_with_scores.sort(key=lambda x: x[1])  # Sort by score (ascending)
	validated = [url for url, score in validated_with_scores[:max_results]]
	return validated
    
