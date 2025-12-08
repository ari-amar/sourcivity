#!/usr/bin/env python3
"""
PDF Scraper for extracting specifications from datasheets using PyMuPDF4LLM and Claude for robustness.
"""

import os
import requests
import re
from typing import Dict, List, Optional
from io import BytesIO
import pymupdf4llm  # Requires pip install pymupdf4llm

from prompts import SINGLE_PDF_SPEC_EXTRACTION_PROMPT, MULTPLE_PDF_SPEC_EXTRACTION_PROMPT
from services.interfaces import AiClientBase


class PDFScraper:

    def __init__(self, ai_client: AiClientBase):
        self.ai_client = ai_client

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

    def extract_markdown_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract structured markdown from PDF content using PyMuPDF4LLM.

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Extracted markdown from PDF (first 10 pages)
        """
        try:
            # PyMuPDF4LLM returns a list of markdown strings per page
            md_pages = pymupdf4llm.to_markdown(BytesIO(pdf_content), pages=range(10))
            md_text = "\n\n".join(md_pages)
            return md_text
        except Exception as e:
            raise Exception(f"Failed to extract markdown from PDF: {str(e)}")

    def extract_specs(self, pdf_md: str, product_type: Optional[str] = None) -> Dict:
        """
        Extract specifications from PDF markdown using Claude.

        Args:
            pdf_md: Markdown extracted from PDF
            product_type: Optional product type hint to help extraction

        Returns:
            Dictionary of extracted specifications
        """
        # Limit to avoid token limits (approx 20k chars ~5k tokens, but markdown is denser)
        if len(pdf_md) > 20000:
            pdf_md = pdf_md[:20000]

        product_hint = f"This is a datasheet for a {product_type}. " if product_type else ""

        prompt = SINGLE_PDF_SPEC_EXTRACTION_PROMPT.format(product_hint, pdf_md)

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Updated to a more recent model as of 2025
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

    def scrape_pdf(self, url: str, product_type: Optional[str] = None, extract_specs: bool=True) -> Dict:
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
            "md": None,
            "specs": {},
            "error": None
        }

        try:
            # Download PDF
            pdf_content = self.download_pdf(url)

            # Extract markdown
            pdf_md = self.extract_markdown_from_pdf(pdf_content)

            if not pdf_md.strip():
                raise ValueError("fNo markdown could be extracted from pdf at {url}")

            result["md"] = pdf_md

            if extract_specs:
                specs = self.extract_specs(pdf_md, product_type)
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
        # First pass: Download all PDFs and extract markdown
        
        results = []

        for url in urls:
            results = self.scrape_pdf(url=url, product_type=product_type)

        for result in results:
            if not result
        return results

    def extract_standardized_specs(self, pdf_mds: List[Optional[str]], urls: List[str], product_type: Optional[str] = None) -> List[Dict]:
        """
        Extract specs from multiple datasheets with standardized keys for comparison.

        Args:
            pdf_mds: List of extracted PDF markdowns (can contain None for failed extractions)
            urls: List of PDF URLs for reference
            product_type: Optional product type hint

        Returns:
            List of spec dictionaries with standardized keys
        """
        # Build combined prompt with all datasheets
        product_hint = f"These are datasheets for {product_type}s. " if product_type else "These are product datasheets. "

        datasheets_md = ""
        for i, md in enumerate(pdf_mds):
            if md:
                # Limit each datasheet to 15k chars to fit multiple in context
                truncated = md[:15000] if len(md) > 15000 else md
                datasheets_md += f"\n\n=== DATASHEET {i+1} (URL: {urls[i]}) ===\n{truncated}\n"

        prompt = f""""""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
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
                while len(specs_array) < len(pdf_mds):
                    specs_array.append({})

                return specs_array[:len(pdf_mds)]
            else:
                # Fallback: return empty specs for all
                return [{}] * len(pdf_mds)

        except Exception as e:
            print(f"Error in standardized extraction: {str(e)}")
            # Fallback: return error in specs
            return [{"error": f"Failed to extract: {str(e)}"} for _ in pdf_mds]