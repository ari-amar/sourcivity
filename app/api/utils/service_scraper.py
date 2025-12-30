#!/usr/bin/env python3
"""
Service Page Scraper for extracting supplier capabilities and services.
"""

import os
import requests
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import anthropic

from services.interfaces import AiClientBase

from prompts.service_extraction_prompts import SERVICE_EXTRACTION_PROMPT, STANDARDIZED_SERVICE_PROMPT

# Import contact URL utilities from pdf_scraper
from utils.pdf_scraper import derive_contact_url, find_contact_url


class ServiceScraper:
	"""Extract service capabilities from supplier web pages using Claude."""

	def __init__(self, api_client: AiClientBase):
		"""
		Initialize the service scraper.

		Args:
			api_client: An instance of AiClientBase to use for API calls.
		"""
		self.api_client = api_client

	def fetch_page(self, url: str) -> str:
		"""
		Fetch HTML content from URL.

		Args:
			url: URL of the web page

		Returns:
			HTML content as string
		"""
		try:
			response = requests.get(url, timeout=30, headers={
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
			})
			response.raise_for_status()
			return response.text
		except Exception as e:
			raise Exception(f"Failed to fetch page from {url}: {str(e)}")

	def extract_text_from_html(self, html_content: str) -> str:
		"""
		Extract clean text from HTML content.

		Args:
			html_content: Raw HTML content

		Returns:
			Cleaned text extracted from HTML
		"""
		try:
			soup = BeautifulSoup(html_content, 'html.parser')

			# Remove script and style elements
			for script in soup(["script", "style", "nav", "footer", "header"]):
				script.decompose()

			# Get text
			text = soup.get_text()

			# Clean up whitespace
			lines = (line.strip() for line in text.splitlines())
			chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
			text = '\n'.join(chunk for chunk in chunks if chunk)

			return text
		except Exception as e:
			raise Exception(f"Failed to extract text from HTML: {str(e)}")

	async def extract_services(self, page_text: str, supplier_name: Optional[str] = None) -> Dict:
		"""
		Extract service capabilities from page text using Claude.

		Args:
			page_text: Text extracted from web page
			supplier_name: Optional supplier name for context

		Returns:
			Dictionary of extracted service information
		"""
		# Limit text to avoid token limits (approx 30k chars = ~7.5k tokens)
		if len(page_text) > 30000:
			page_text = page_text[:30000]

		supplier_hint = f"This is the website for {supplier_name}. " if supplier_name else ""

		prompt = SERVICE_EXTRACTION_PROMPT.format(supplier_hint=supplier_hint, page_text=page_text)

		try:
			# note false enforce json only because schema is manually included in prompt
			response_text = await self.api_client.generate(
				system_prompt="You are an expert at extracting structured information from web pages about manufacturing suppliers.",
				user_prompt=prompt,
				max_tokens=2000,
				enforce_json=False
			)

			# Extract JSON from response (in case there's extra text)
			json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
			if json_match:
				import json
				return json.loads(json_match.group())
			else:
				return {"error": "Could not extract services", "raw_response": response_text}

		except Exception as e:
			return {"error": f"Failed to extract services: {str(e)}"}

	async def scrape_page(self, url: str, supplier_name: Optional[str] = None) -> Dict:
		"""
		Fetch web page and extract service information.

		Args:
			url: URL of the supplier's service/capability page
			supplier_name: Optional supplier name for context

		Returns:
			Dictionary containing URL, services, and any errors
		"""
		result = {
			"url": url,
			"services": {},
			"error": None
		}

		try:
			# Fetch page
			html_content = self.fetch_page(url)

			# Extract text
			page_text = self.extract_text_from_html(html_content)

			if not page_text.strip():
				result["error"] = "No text could be extracted from page"
				return result

			# Extract services using Claude
			services = await self.extract_services(page_text, supplier_name)
			result["services"] = services

		except Exception as e:
			result["error"] = str(e)

		return result

	async def scrape_multiple(self, urls: List[str], query_context: Optional[str] = None) -> List[Dict]:
		"""
		Scrape multiple supplier pages and extract service info with standardized keys.

		Args:
			urls: List of web page URLs
			query_context: Optional context about what user is searching for

		Returns:
			List of dictionaries with service info for each page
		"""
		# First pass: Fetch all pages and extract text
		page_texts = []
		results = []

		for url in urls:
			print(f"Scraping: {url}")
			result = {
				"url": url,
				"services": {},
				"error": None
			}

			try:
				html_content = self.fetch_page(url)
				page_text = self.extract_text_from_html(html_content)

				if not page_text.strip():
					result["error"] = "No text could be extracted from page"
				else:
					page_texts.append(page_text)

			except Exception as e:
				result["error"] = str(e)
				page_texts.append(None)

			results.append(result)

		# Second pass: Extract services with standardized keys across all pages
		if any(text for text in page_texts):
			standardized_services = await self.extract_standardized_services(page_texts, urls, query_context)

			for i, result in enumerate(results):
				if result["error"] is None and i < len(standardized_services):
					result["services"] = standardized_services[i]

		# Third pass: Verify/find contact URLs (hybrid approach like parts search)
		print(f"\n{'='*60}")
		print(f"VERIFYING CONTACT URLS FOR {len(results)} SUPPLIERS")
		print(f"{'='*60}")

		for i, result in enumerate(results):
			if result["error"] is not None:
				continue

			extracted_services = result.get("services", {})
			company_name = extracted_services.get("company_name", "Unknown")
			ai_contact_url = extracted_services.get("contact_url", "")

			print(f"\n[{i+1}/{len(results)}] Processing: {company_name}")
			print(f"  Page URL: {result['url']}")

			# If AI found a contact URL and it looks valid, use it
			if ai_contact_url and ai_contact_url.startswith("http"):
				print(f"  ✅ AI extracted contact URL: {ai_contact_url}")
				continue

			# Otherwise, use hybrid approach: derive + verify
			print(f"  ⚠️  No contact URL from AI extraction")

			# Get supplier homepage as ultimate fallback
			parsed = urlparse(result["url"])
			homepage_url = f"{parsed.scheme}://{parsed.netloc}"

			# Step 1: Try to find actual contact page by crawling homepage
			try:
				domain = parsed.netloc
				print(f"  🔍 Crawling {domain} homepage for contact link...")
				actual_contact = await find_contact_url(domain, timeout=8)
				if actual_contact:
					extracted_services["contact_url"] = actual_contact
					print(f"  ✅ Found verified contact URL: {actual_contact}")
				else:
					# Step 2: Verify derived URL exists
					derived_url = derive_contact_url(result["url"])
					print(f"  ⚡ Testing derived URL: {derived_url}")
					try:
						head_response = requests.head(derived_url, timeout=5, allow_redirects=True)
						if head_response.status_code == 200:
							extracted_services["contact_url"] = derived_url
							print(f"  ✅ Derived URL verified: {derived_url}")
						else:
							extracted_services["contact_url"] = homepage_url
							print(f"  ⚠️  Derived URL failed (status {head_response.status_code}), using homepage: {homepage_url}")
					except:
						extracted_services["contact_url"] = homepage_url
						print(f"  ⚠️  Derived URL unreachable, using homepage: {homepage_url}")
			except Exception as e:
				print(f"  ❌ Error during contact URL discovery: {e}")
				extracted_services["contact_url"] = homepage_url
				print(f"  📌 Using supplier homepage as fallback: {homepage_url}")

		print(f"\n{'='*60}")
		print(f"CONTACT URL VERIFICATION COMPLETE")
		print(f"{'='*60}\n")

		return results

	async def extract_standardized_services(self, page_texts: List[Optional[str]], urls: List[str], query_context: Optional[str] = None) -> List[Dict]:
		"""
		Extract service info from multiple pages with standardized keys for comparison.

		Args:
			page_texts: List of extracted page texts (can contain None for failed extractions)
			urls: List of URLs for reference
			query_context: Optional context about what user is searching for

		Returns:
			List of service dictionaries with standardized keys
		"""
		# Build combined prompt with all pages
		context_hint = f"The user is searching for: {query_context}. " if query_context else ""

		pages_text = ""
		for i, text in enumerate(page_texts):
			if text:
				# Limit each page to 20k chars to fit multiple in context
				truncated = text[:20000] if len(text) > 20000 else text
				pages_text += f"\n\n=== SUPPLIER PAGE {i+1} (URL: {urls[i]}) ===\n{truncated}\n"

		prompt = STANDARDIZED_SERVICE_PROMPT.format(
			context_hint=context_hint,
			pages_text=pages_text
		)

		try:
			response_text = await self.api_client.generate(
				system_prompt="You are an expert at extracting structured information from web pages about manufacturing suppliers.",
				user_prompt=prompt,
				max_tokens=4000,
				enforce_json=False
			)

			# Extract JSON array from response
			json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
			if json_match:
				import json
				services_array = json.loads(json_match.group())

				# Ensure we return the right number of results
				while len(services_array) < len(page_texts):
					services_array.append({})

				return services_array[:len(page_texts)]
			else:
				# Fallback: return empty services for all
				return [{}] * len(page_texts)

		except Exception as e:
			print(f"Error in standardized extraction: {str(e)}")
			# Fallback: return error in services
			return [{"error": f"Failed to extract: {str(e)}"} for _ in page_texts]