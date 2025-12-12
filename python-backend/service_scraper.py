#!/usr/bin/env python3
"""
Service Page Scraper for extracting supplier capabilities and services.
"""

import os
import requests
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import anthropic
from dotenv import load_dotenv

load_dotenv()


class ServiceScraper:
    """Extract service capabilities from supplier web pages using Claude."""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize the service scraper.

        Args:
            anthropic_api_key: Anthropic API key. If not provided, will look for ANTHROPIC_API_KEY env var.
        """
        self.anthropic_api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable "
                "or pass it as an argument."
            )
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)

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

    def extract_services(self, page_text: str, supplier_name: Optional[str] = None) -> Dict:
        """
        Extract service capabilities from page text using Claude.

        Args:
            page_text: Text extracted from web page
            supplier_name: Optional supplier name for context

        Returns:
            Dictionary of extracted service information
        """
        # Limit text to avoid token limits (approx 60k chars = ~15k tokens)
        if len(page_text) > 60000:
            page_text = page_text[:60000]

        supplier_hint = f"This is the website for {supplier_name}. " if supplier_name else ""

        prompt = f"""{supplier_hint}Extract key information about this supplier's manufacturing services and capabilities.

Focus on extracting:
1. **Services Offered**: What manufacturing services do they provide? (e.g., CNC machining, injection molding, sheet metal fabrication, etc.)
2. **Capabilities**: Specific capabilities, processes, or technologies (e.g., 5-axis CNC, precision tolerances, materials worked with)
3. **Certifications**: Quality certifications (ISO 9001, AS9100, ITAR, etc.)
4. **Equipment**: Major equipment or machinery mentioned
5. **Industries Served**: Target industries or markets
6. **Location**: Geographic location, facilities
7. **Lead Times**: Typical turnaround times if mentioned
8. **MOQ**: Minimum order quantities if mentioned
9. **Company Info**: Company name, year established, size

Return the information as a JSON object with these keys:
- company_name: string
- services_offered: array of strings
- capabilities: array of strings
- certifications: array of strings
- equipment: array of strings
- industries_served: array of strings
- location: string
- lead_time: string (or null if not mentioned)
- moq: string (or null if not mentioned)
- year_established: string (or null if not mentioned)
- employees: string (or null if not mentioned)

Page text:
{page_text}

Return ONLY valid JSON, no other text."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
            else:
                return {"error": "Could not extract services", "raw_response": response_text}

        except Exception as e:
            return {"error": f"Failed to extract services: {str(e)}"}

    def scrape_page(self, url: str, supplier_name: Optional[str] = None) -> Dict:
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
            services = self.extract_services(page_text, supplier_name)
            result["services"] = services

        except Exception as e:
            result["error"] = str(e)

        return result

    def scrape_multiple(self, urls: List[str], query_context: Optional[str] = None) -> List[Dict]:
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
            standardized_services = self.extract_standardized_services(page_texts, urls, query_context)

            for i, result in enumerate(results):
                if result["error"] is None and i < len(standardized_services):
                    result["services"] = standardized_services[i]

        return results

    def extract_standardized_services(self, page_texts: List[Optional[str]], urls: List[str], query_context: Optional[str] = None) -> List[Dict]:
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
                # Limit each page to 40k chars to fit multiple in context
                truncated = text[:40000] if len(text) > 40000 else text
                pages_text += f"\n\n=== SUPPLIER PAGE {i+1} (URL: {urls[i]}) ===\n{truncated}\n"

        prompt = f"""{context_hint}I need to extract supplier service information from multiple web pages for side-by-side comparison.

CRITICAL: Use IDENTICAL keys across all suppliers so they can be compared. Be consistent with:
- Array formatting (always use arrays for lists, even if single item)
- Null values (use null if information not found, don't omit the key)
- Standardized naming (use same service names across suppliers)

Extract these pages and return a JSON array where each element corresponds to one supplier's info.

Focus on:
1. **Services Offered**: Manufacturing services (CNC machining, injection molding, 3D printing, etc.)
2. **Capabilities**: Specific processes, technologies, materials, tolerances
3. **Certifications**: ISO 9001, AS9100, ITAR, ISO 13485, etc.
4. **Equipment**: Major machinery or technology platforms
5. **Industries**: Aerospace, medical, automotive, etc.
6. **Location**: City/state/country
7. **Lead Times & MOQ**: If mentioned
8. **Company Info**: Name, size, year established

{pages_text}

Return ONLY a JSON array with one object per supplier. Use IDENTICAL keys across all objects.
Example format:
[
  {{
    "company_name": "ABC Manufacturing",
    "services_offered": ["CNC machining", "Sheet metal"],
    "capabilities": ["5-axis CNC", "±0.001\" tolerance"],
    "certifications": ["ISO 9001", "AS9100"],
    "equipment": ["Haas VF-4", "DMG Mori NLX"],
    "industries_served": ["Aerospace", "Medical"],
    "location": "Los Angeles, CA",
    "lead_time": "2-3 weeks",
    "moq": "No minimum",
    "year_established": "1995",
    "employees": "50-100"
  }},
  {{
    "company_name": "XYZ Services",
    "services_offered": ["CNC machining", "Injection molding"],
    ...
  }}
]

Return ONLY valid JSON array, no other text."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

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
