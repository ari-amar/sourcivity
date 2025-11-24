from typing import List, Tuple
import httpx

from services import AnthropicClient, DuckDuckGoClient
from constants import DATASHEET_CACHE_DIR

def rank_url_by_supplier_llm(url, supplier_info) -> List[str]:
    """Assign a quality score to URL based on supplier tier (1=best, 4=worst, 999=avoid)."""
    if not supplier_info:
        return 2  # Neutral score if no supplier info

    url_lower = url.lower()

    # Check tier 1 (manufacturers/OEMs)
    if 'tier1_domains' in supplier_info:
        for domain in supplier_info['tier1_domains']:
            if domain.lower() in url_lower:
                return 1

    # Check tier 2 (authorized distributors)
    if 'tier2_domains' in supplier_info:
        for domain in supplier_info['tier2_domains']:
            if domain.lower() in url_lower:
                return 2

    # Check tier 3 (technical/educational)
    if 'tier3_domains' in supplier_info:
        for domain in supplier_info['tier3_domains']:
            if domain in url_lower:  # .edu, .org
                return 3

    # Check for gray market/low quality sites to avoid
    gray_market = ['alibaba', 'aliexpress', 'dhgate', 'ebay', 'rfq', 'quote']
    for term in gray_market:
        if term in url_lower:
            return 999  # Avoid these

    return 4  # Unknown supplier

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
					if not await anthropic_client.validate_url_specs_llm(url, query_specs):
						continue

				# Rank URL by supplier quality
				supplier_score = rank_url_by_supplier_llm(url, supplier_info)

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
    
