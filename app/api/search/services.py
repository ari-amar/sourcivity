from typing import Optional, List
from services.interfaces import AiClientBase, SearchEngineClientBase
from models import ServiceSearchRequest, ServiceSearchResponse
from utils.service_scraper import ServiceScraper

async def search_services(request: ServiceSearchRequest, ai_client: AiClientBase, search_engine_client: SearchEngineClientBase) -> ServiceSearchResponse:
	"""
	Search for supplier service and capability pages.

	Args:
		request: ServiceSearchRequest containing query and optional supplier_name
		ai_client: AI client for extracting service information
		search_engine_client: Search engine client for finding pages

	Returns:
		ServiceSearchResponse with query and list of service results
	"""
	print(f"\n{'='*60}")
	print(f"[STEP 1] Building search query")
	print(f"  - User query: '{request.query}'")

	# Build query targeting service/capability pages
	query_parts = []

	if request.supplier_name:
		query_parts.append(request.supplier_name)
		print(f"  - Supplier name: '{request.supplier_name}'")

	query_parts.append(request.query)
	query_parts.append("capabilities services manufacturing")

	# Target pages that describe services, not product datasheets
	search_query = " ".join(query_parts)
	print(f"  - Final search query: '{search_query}'")
	print(f"{'='*60}")

	try:
		print(f"\n[STEP 2] Calling search engine (Exa)")
		print(f"  - Search engine: {type(search_engine_client).__name__}")
		print(f"  - Max results: 5")
		print(f"  - Initiating web search...")

		# Search for HTML pages about services/capabilities
		results = await search_engine_client.search(
			search_query,
			max_results=5
		)

		print(f"\n[STEP 3] Search results received from Exa")
		print(f"  - Raw results count: {len(results.results)}")

		print(f"\n[STEP 4] Filtering results")
		# Filter out PDFs and specification/standards pages
		filtered_results = []
		for i, result in enumerate(results.results, 1):
			print(f"\n  Processing result #{i}:")
			print(f"    - Title: {result.title[:60]}...")
			print(f"    - URL: {result.url}")

			# Exclude PDFs and specification documents
			url_lower = result.url.lower()
			is_pdf = url_lower.endswith('.pdf')

			# Check if it's a standards/specification page (not an actual supplier)
			spec_indicators = ['astm.org', 'iso.org', 'sae.org', 'ansi.org', 'asme.org', 'nist.gov']
			is_spec_page = any(indicator in url_lower for indicator in spec_indicators)

			score = getattr(result, 'score', None)
			if score:
				print(f"    - Relevance score: {score}")
			print(f"    - Is PDF: {is_pdf}")
			print(f"    - Is specification page: {is_spec_page}")

			if not is_pdf and not is_spec_page:
				filtered_results.append({
					'title': result.title,
					'url': result.url,
					'score': score
				})
				print(f"    ✓ Added to results")
			else:
				if is_pdf:
					print(f"    ✗ Excluded (PDF)")
				if is_spec_page:
					print(f"    ✗ Excluded (Specification page)")

		print(f"  - Filtered results count: {len(filtered_results)}")

		print(f"\n[STEP 5] Scraping and extracting service information")
		print(f"  - Pages to scrape: {len(filtered_results)}")
		print(f"  - Extracting capabilities from each page...")

		# Initialize scraper and extract service information
		scraper = ServiceScraper(api_client=ai_client)
		urls = [service['url'] for service in filtered_results]

		# Scrape pages and extract standardized service info
		scraped_results = await scraper.scrape_multiple(urls, query_context=request.query)

		print(f"\n[STEP 6] Merging extraction results with search results")
		# Merge scraped data with search results
		for i, (search_result, scraped_data) in enumerate(zip(filtered_results, scraped_results), 1):
			search_result['extracted_services'] = scraped_data.get('services', {})
			search_result['extraction_error'] = scraped_data.get('error')

			print(f"  Result #{i}:")
			print(f"    - Title: {search_result['title'][:50]}...")
			print(f"    - URL: {search_result['url']}")
			if scraped_data.get('error'):
				print(f"    ⚠ Extraction error: {scraped_data['error'][:60]}...")
			elif scraped_data.get('services'):
				extracted_info = scraped_data.get('services', {})
				company_name = extracted_info.get('company_name', 'N/A')
				contact_url = extracted_info.get('contact_url', 'N/A')
				services_offered = extracted_info.get('services_offered', 'N/A')

				print(f"    ✓ Company: {company_name}")
				print(f"    ✓ Contact URL: {contact_url}")
				print(f"    ✓ Services: {services_offered[:80]}...")

		print(f"\n[STEP 7] Preparing final response")
		print(f"  - Total services to return: {len(filtered_results)}")
		print(f"{'='*60}\n")

		# Return ServiceSearchResponse
		return ServiceSearchResponse(
			query=request.query,
			services=filtered_results
		)

	except Exception as e:
		print(f"\n[ERROR] Service search failed: {str(e)}")
		print(f"{'='*60}\n")
		raise Exception(f"Error searching for services: {str(e)}")