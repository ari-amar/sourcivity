#!/usr/bin/env python3
"""
PDF Scraper for extracting specifications from datasheets.
"""

import os
import requests
import re
from typing import Dict, List, Optional
from io import BytesIO
import anthropic
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()


class PDFScraper:
    """Extract specifications from PDF datasheets using Claude."""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize the PDF scraper.

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

    def download_pdf(self, url: str) -> bytes:
        """
        Download PDF from URL.

        Args:
            url: URL of the PDF

        Returns:
            PDF content as bytes
        """
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Failed to download PDF from {url}: {str(e)}")

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted text from PDF
        """
        try:
            pdf_file = BytesIO(pdf_content)
            reader = PdfReader(pdf_file)

            text = ""
            # Extract from first 10 pages (specs usually on first few pages)
            max_pages = min(10, len(reader.pages))
            for page_num in range(max_pages):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"

            return text
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def extract_specs(self, pdf_text: str, product_type: Optional[str] = None) -> Dict:
        """
        Extract specifications from PDF text using Claude.

        Args:
            pdf_text: Text extracted from PDF
            product_type: Optional product type hint to help extraction

        Returns:
            Dictionary of extracted specifications
        """
        # Limit text to avoid token limits (approx 20k chars = ~5k tokens)
        if len(pdf_text) > 20000:
            pdf_text = pdf_text[:20000]

        product_hint = f"This is a datasheet for a {product_type}. " if product_type else ""

        prompt = f"""{product_hint}Extract the key technical specifications from this datasheet text.

Focus on the most important specs such as:
- Electrical characteristics (voltage, current, power, resistance, capacitance, etc.)
- Physical characteristics (dimensions, weight, temperature range)
- Performance metrics (speed, accuracy, bandwidth, frequency range, etc.)
- Part number and manufacturer
- Any other critical specifications

Return the specifications as a JSON object where keys are the specification names and values are the specification values with units.
Include only the most relevant specifications that would be useful for comparing similar products.

Datasheet text:
{pdf_text}

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
                return {"error": "Could not extract specs", "raw_response": response_text}

        except Exception as e:
            return {"error": f"Failed to extract specs: {str(e)}"}

    def scrape_pdf(self, url: str, product_type: Optional[str] = None) -> Dict:
        """
        Download PDF and extract specifications.

        Args:
            url: URL of the PDF datasheet
            product_type: Optional product type hint

        Returns:
            Dictionary containing URL, specs, and any errors
        """
        result = {
            "url": url,
            "specs": {},
            "error": None
        }

        try:
            # Download PDF
            pdf_content = self.download_pdf(url)

            # Extract text
            pdf_text = self.extract_text_from_pdf(pdf_content)

            if not pdf_text.strip():
                result["error"] = "No text could be extracted from PDF"
                return result

            # Extract specs using Claude
            specs = self.extract_specs(pdf_text, product_type)
            result["specs"] = specs

        except Exception as e:
            result["error"] = str(e)

        return result

    def scrape_multiple(self, urls: List[str], product_type: Optional[str] = None) -> List[Dict]:
        """
        Scrape multiple PDFs and return their specs with standardized keys.

        Args:
            urls: List of PDF URLs
            product_type: Optional product type hint

        Returns:
            List of dictionaries with specs for each PDF
        """
        # First pass: Download all PDFs and extract text
        pdf_texts = []
        results = []

        for url in urls:
            print(f"Scraping: {url}")
            result = {
                "url": url,
                "specs": {},
                "error": None
            }

            try:
                pdf_content = self.download_pdf(url)
                pdf_text = self.extract_text_from_pdf(pdf_content)

                if not pdf_text.strip():
                    result["error"] = "No text could be extracted from PDF"
                else:
                    pdf_texts.append(pdf_text)

            except Exception as e:
                result["error"] = str(e)
                pdf_texts.append(None)

            results.append(result)

        # Second pass: Extract specs with standardized keys across all datasheets
        if any(text for text in pdf_texts):
            standardized_specs = self.extract_standardized_specs(pdf_texts, urls, product_type)

            for i, result in enumerate(results):
                if result["error"] is None and i < len(standardized_specs):
                    result["specs"] = standardized_specs[i]

        return results

    def extract_standardized_specs(self, pdf_texts: List[Optional[str]], urls: List[str], product_type: Optional[str] = None) -> List[Dict]:
        """
        Extract specs from multiple datasheets with standardized keys for comparison.

        Args:
            pdf_texts: List of extracted PDF texts (can contain None for failed extractions)
            urls: List of PDF URLs for reference
            product_type: Optional product type hint

        Returns:
            List of spec dictionaries with standardized keys
        """
        # Build combined prompt with all datasheets
        product_hint = f"These are datasheets for {product_type}s. " if product_type else "These are product datasheets. "

        datasheets_text = ""
        for i, text in enumerate(pdf_texts):
            if text:
                # Limit each datasheet to 15k chars to fit multiple in context
                truncated = text[:15000] if len(text) > 15000 else text
                datasheets_text += f"\n\n=== DATASHEET {i+1} (URL: {urls[i]}) ===\n{truncated}\n"

        prompt = f"""{product_hint}I need to extract specifications from multiple datasheets for side-by-side comparison.

CRITICAL: Use IDENTICAL specification keys across all datasheets so they can be compared. For example:
- If one says "Supply Voltage" and another says "Input Voltage", use the SAME key like "supply_voltage_V"
- If one says "Operating Temperature" and another says "Temperature Range", use "temperature_range_C"
- Always include units in the key name (e.g., "_V" for volts, "_A" for amps, "_C" for celsius)

Extract these datasheets and return a JSON array where each element corresponds to one datasheet's specs.

Focus on the most important comparable specifications:
- Electrical (voltage, current, power)
- Performance (accuracy, bandwidth, flow rate, speed)
- Physical (dimensions, temperature range, weight)
- Identification (manufacturer, part_number, model)

{datasheets_text}

Return ONLY a JSON array with one object per datasheet. Use IDENTICAL keys across all objects for comparable specs.
Example format:
[
  {{"manufacturer": "Company A", "supply_voltage_V": "3-5", "max_current_A": "2"}},
  {{"manufacturer": "Company B", "supply_voltage_V": "5", "max_current_A": "1.5"}}
]

Return ONLY valid JSON array, no other text."""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                import json
                specs_array = json.loads(json_match.group())

                # Ensure we return the right number of results
                while len(specs_array) < len(pdf_texts):
                    specs_array.append({})

                return specs_array[:len(pdf_texts)]
            else:
                # Fallback: return empty specs for all
                return [{}] * len(pdf_texts)

        except Exception as e:
            print(f"Error in standardized extraction: {str(e)}")
            # Fallback: return error in specs
            return [{"error": f"Failed to extract: {str(e)}"} for _ in pdf_texts]
