#!/usr/bin/env python3
"""
PDF Scraper for extracting specifications from datasheets using PyMuPDF4LLM and Claude for robustness.
"""

import requests
import re
import json
from typing import Dict, List, Optional
import fitz  # PyMuPDF
import pymupdf4llm  # Requires pip install pymupdf4llm

from prompts import (
    SINGLE_PDF_SPEC_EXTRACTION_PROMPT,
    MULTPLE_PDF_SPEC_EXTRACTION_PROMPT,
    PASS1_EXTRACT_ALL_SPECS_PROMPT,
    PASS2_SELECT_BEST_SPECS_PROMPT,
    PASS3_EXTRACT_SELECTED_SPECS_PROMPT
)
from services.interfaces import AiClientBase


class PDFScraper:

    def __init__(self, ai_client: AiClientBase):
        self.ai_client = ai_client

    def download_pdf(self, url: str) -> bytes:
        """
        Download PDF from URL and validate it's actually a PDF.

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

            content = response.content

            # Validate it's actually a PDF file
            if not content.startswith(b'%PDF'):
                raise ValueError(f"URL does not point to a valid PDF file (missing PDF header)")

            # Check minimum size (valid PDFs should be at least a few KB)
            if len(content) < 1024:
                raise ValueError(f"PDF file too small ({len(content)} bytes) - likely corrupted")

            return content
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
            with fitz.open(stream=pdf_content) as doc:
                # Check if PDF has pages
                if len(doc) == 0:
                    raise ValueError("PDF has no pages")

                # PyMuPDF4LLM returns markdown text
                # Limit to first 10 pages by slicing the document
                limited_doc = doc if len(doc) <= 10 else fitz.open()
                if len(doc) > 10:
                    for page_num in range(10):
                        limited_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

                md_text = pymupdf4llm.to_markdown(limited_doc)

                if limited_doc != doc:
                    limited_doc.close()

                # Validate we got actual content
                if not md_text or len(md_text.strip()) < 100:
                    raise ValueError(f"PDF extraction produced no meaningful content (only {len(md_text)} chars)")

            return md_text
        except Exception as e:
            raise Exception(f"Failed to extract markdown from PDF: {str(e)}")

    async def extract_specs(self, pdf_md: str, product_type: Optional[str] = None) -> Dict:
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

        prompt = SINGLE_PDF_SPEC_EXTRACTION_PROMPT.format(product_hint=product_hint, pdf_md=pdf_md)

        try:
            response_text = await self.ai_client.generate(
                system_prompt="You are an expert at extracting technical specifications from product datasheets.",
                user_prompt=prompt,
                enforce_json=True,
                json_schema={
                    "type": "object",
                    "properties": {
                        "specifications": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["specifications"]
                },
                max_tokens=2000
            )

            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not extract specs", "raw_response": response_text}

        except Exception as e:
            return {"error": f"Failed to extract specs: {str(e)}"}

    async def scrape_pdf(self, url: str, product_type: Optional[str] = None, extract_specs: bool=True) -> Dict:
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
                raise ValueError(f"No markdown could be extracted from pdf at {url}")

            result["md"] = pdf_md

            if extract_specs:
                specs = await self.extract_specs(pdf_md, product_type)
                result["specs"] = specs

        except Exception as e:
            result["error"] = str(e)

        return result

    async def scrape_multiple(self, urls: List[str], product_type: Optional[str] = "") -> List[Dict]:
        """
        Scrape multiple PDFs and return their specs with standardized keys.

        Args:
            urls: List of PDF URLs
            product_type: Optional product type hint

        Returns:
            List of dictionaries with specs for each PDF
        """
        print(f"\n=== STARTING PDF SCRAPING FOR {len(urls)} URLS ===")

        # First pass: Download all PDFs and extract markdown
        failed_results = []
        spec_extractable_results = []

        for i, url in enumerate(urls, 1):
            print(f"\nProcessing PDF {i}/{len(urls)}: {url[:80]}...")
            result = await self.scrape_pdf(url=url, product_type=product_type, extract_specs=False)

            if not result.get("error"):
                md_length = len(result.get("md", ""))
                print(f"  ✓ Successfully extracted {md_length} chars of markdown")
                spec_extractable_results.append(result)
            else:
                print(f"  ✗ Failed: {result['error']}")
                failed_results.append(result)

        print(f"\n=== PDF EXTRACTION SUMMARY ===")
        print(f"Successfully extracted: {len(spec_extractable_results)}/{len(urls)} PDFs")
        print(f"Failed: {len(failed_results)}/{len(urls)} PDFs")

        if len(spec_extractable_results) == 0:
            print("ERROR: No valid PDFs could be extracted!")
            return failed_results

        # Need at least 3 valid PDFs to do meaningful comparison
        if len(spec_extractable_results) < 3:
            print(f"WARNING: Only {len(spec_extractable_results)} valid PDFs - need at least 3 for comparison")
            print("Returning results without spec extraction")
            return spec_extractable_results + failed_results

        specs = await self.extract_standardized_specs(
                    pdf_mds=[res["md"] for res in spec_extractable_results],
                    urls=[res["url"] for res in spec_extractable_results],
                    product_type=product_type
                )

        successful_results = []
        for i, spec in enumerate(specs):
            result = spec_extractable_results[i]
            result["specs"] = spec.get("specifications", {})
            result["manufacturer"] = spec.get("manufacturer", "Unknown")
            result["product_name"] = spec.get("product_name", "Unknown Product")
            successful_results.append(result)

        # Return successful results first, failed ones at the end
        return successful_results + failed_results

    async def extract_standardized_specs(self, pdf_mds: List[Optional[str]], urls: List[str], product_type: Optional[str] = None) -> List[Dict]:
        """
        THREE-PASS extraction for better spec selection quality:
        Pass 1: Extract ALL specs from each datasheet individually
        Pass 2: Analyze all specs and select best 5 common ones
        Pass 3: Extract those 5 specs from all datasheets with standardized keys

        Args:
            pdf_mds: List of extracted PDF markdowns
            urls: List of PDF URLs for reference
            product_type: Optional product type hint (unused in new approach)

        Returns:
            List of spec dictionaries with standardized keys
        """
        if not any(pdf_mds):
            print("ERROR: No markdown content to extract specs from")
            return [{"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}} for _ in pdf_mds]

        print(f"\n{'='*60}")
        print(f"THREE-PASS SPEC EXTRACTION FOR {len(pdf_mds)} DATASHEETS")
        print(f"{'='*60}")

        # ===== PASS 1: Extract ALL specs from each datasheet =====
        print(f"\n📋 PASS 1: Extracting ALL specs from each datasheet individually...")
        pass1_results = []

        for i, md in enumerate(pdf_mds):
            if not md:
                pass1_results.append({"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}})
                continue

            print(f"\n  Processing datasheet {i+1}/{len(pdf_mds)}...")
            truncated = md[:20000] if len(md) > 20000 else md
            prompt = PASS1_EXTRACT_ALL_SPECS_PROMPT.format(pdf_md=truncated)

            try:
                response_text = await self.ai_client.generate(
                    system_prompt="You are extracting ALL specifications from a datasheet. Extract everything you can find - we'll filter later.",
                    user_prompt=prompt,
                    enforce_json=True,
                    json_schema={
                        "type": "object",
                        "properties": {
                            "manufacturer": {"type": "string"},
                            "product_name": {"type": "string"},
                            "specifications": {
                                "type": "object",
                                "additionalProperties": {"type": "string"}
                            }
                        },
                        "required": ["manufacturer", "product_name", "specifications"]
                    },
                    max_tokens=2000
                )

                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    spec_count = len(result.get("specifications", {}))
                    print(f"    ✓ Extracted {spec_count} specs from {result.get('manufacturer', 'Unknown')} {result.get('product_name', 'Unknown')}")
                    pass1_results.append(result)
                else:
                    print(f"    ✗ Failed to parse JSON response")
                    pass1_results.append({"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}})

            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                pass1_results.append({"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}})

        # ===== PASS 2: Analyze and select best 5 specs =====
        print(f"\n🎯 PASS 2: Analyzing all specs to select best 5 common ones...")

        # Format all extracted specs for analysis
        all_specs_summary = ""
        for i, result in enumerate(pass1_results):
            all_specs_summary += f"\nDATASHEET {i+1} ({result.get('manufacturer', 'Unknown')} {result.get('product_name', 'Unknown')}):\n"
            specs = result.get("specifications", {})
            for key, value in specs.items():
                all_specs_summary += f"  - {key}: {value}\n"

        min_coverage = max(3, len(pdf_mds) - 1)  # At least 3 or all-but-one datasheets
        prompt = PASS2_SELECT_BEST_SPECS_PROMPT.format(
            num_datasheets=len(pdf_mds),
            all_extracted_specs=all_specs_summary,
            min_coverage=min_coverage
        )

        try:
            response_text = await self.ai_client.generate(
                system_prompt="You are a spec selection expert. Analyze extracted specs and choose the 5 best for product comparison.",
                user_prompt=prompt,
                enforce_json=True,
                json_schema={
                    "type": "object",
                    "properties": {
                        "selected_specs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "standardized_key": {"type": "string"},
                                    "display_name": {"type": "string"},
                                    "reason": {"type": "string"},
                                    "coverage": {"type": "string"}
                                },
                                "required": ["standardized_key", "display_name", "reason", "coverage"]
                            }
                        }
                    },
                    "required": ["selected_specs"]
                },
                max_tokens=1500
            )

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                selection = json.loads(json_match.group())
                selected_specs = selection.get("selected_specs", [])

                print(f"\n  ✓ Selected {len(selected_specs)} specs:")
                for spec in selected_specs:
                    print(f"    - {spec['standardized_key']}: {spec['display_name']} [{spec['coverage']}]")
                    print(f"      Reason: {spec['reason']}")

                if len(selected_specs) != 5:
                    print(f"\n  ⚠️  WARNING: Expected 5 specs, got {len(selected_specs)}")

            else:
                print(f"  ✗ Failed to parse selection response")
                selected_specs = []

        except Exception as e:
            print(f"  ✗ Error in spec selection: {str(e)}")
            selected_specs = []

        if not selected_specs:
            print("\n  ⚠️  Falling back to first product's specs...")
            # Fallback: use all specs from first successful extraction
            for result in pass1_results:
                if result.get("specifications"):
                    selected_specs = [
                        {"standardized_key": key, "display_name": key}
                        for key in list(result["specifications"].keys())[:5]
                    ]
                    break

        # ===== PASS 3: Extract selected 5 specs from all datasheets =====
        print(f"\n📊 PASS 3: Extracting selected specs from all datasheets with standardized keys...")

        # Build datasheets info with original markdown
        datasheets_info = ""
        for i, md in enumerate(pdf_mds):
            if md:
                truncated = md[:15000] if len(md) > 15000 else md
                datasheets_info += f"\n\n=== DATASHEET {i+1} ===\n{truncated}\n=== END DATASHEET {i+1} ===\n"

        # Build selected specs info
        specs_info = "\n".join([
            f"{i+1}. {spec['standardized_key']} - {spec.get('display_name', spec['standardized_key'])}"
            for i, spec in enumerate(selected_specs)
        ])

        prompt = PASS3_EXTRACT_SELECTED_SPECS_PROMPT.format(
            selected_specs_info=specs_info,
            datasheets_with_specs=datasheets_info
        )

        try:
            response_text = await self.ai_client.generate(
                system_prompt="Extract the specified specs from each datasheet using the exact standardized keys provided.",
                user_prompt=prompt,
                enforce_json=True,
                json_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "manufacturer": {"type": "string"},
                            "product_name": {"type": "string"},
                            "specifications": {
                                "type": "object",
                                "additionalProperties": {"type": "string"}
                            }
                        },
                        "required": ["manufacturer", "product_name", "specifications"]
                    }
                },
                max_tokens=4096
            )

            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                specs_array = json.loads(json_match.group())
                print(f"\n  ✓ Successfully extracted standardized specs for {len(specs_array)} datasheets")

                for i, spec_obj in enumerate(specs_array):
                    specs_count = len(spec_obj.get("specifications", {}))
                    spec_keys = list(spec_obj.get('specifications', {}).keys())
                    print(f"    Datasheet {i+1}: {specs_count} specs - {spec_keys}")

                # Ensure we return the right number of results
                while len(specs_array) < len(pdf_mds):
                    specs_array.append({"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}})

                print(f"\n{'='*60}")
                print(f"THREE-PASS EXTRACTION COMPLETE")
                print(f"{'='*60}\n")

                return specs_array[:len(pdf_mds)]
            else:
                print(f"  ✗ Failed to parse final extraction")
                return [{"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}} for _ in pdf_mds]

        except Exception as e:
            print(f"  ✗ Error in final extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return [{"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}} for _ in pdf_mds]

            return [{"specifications": {"error": f"Failed to extract: {str(e)}"}} for _ in pdf_mds]