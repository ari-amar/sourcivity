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
    PASS3_EXTRACT_SELECTED_SPECS_PROMPT
)
from services.interfaces import AiClientBase


class PDFScraper:

    def __init__(self, ai_client: AiClientBase, debug: bool = False):
        self.ai_client = ai_client
        self.debug = debug

        if self.debug:
            import os
            self.debug_dir = "debug_extraction"
            os.makedirs(self.debug_dir, exist_ok=True)
            print(f"DEBUG MODE ENABLED - outputs will be saved to {self.debug_dir}/")

    def extract_specs_with_regex(self, markdown_content: str) -> List[str]:
        """
        Extract potential specifications using regex patterns (no AI).
        Fast, free, and good for finding obvious spec lines.

        Returns:
            List of potential spec strings in "key: value" format
        """
        potential_specs = []

        # Pattern 1: Lines with colons (Key: Value)
        colon_pattern = re.compile(r'^[\s\-\*]*([A-Za-z][A-Za-z0-9\s\-/()]+):\s*(.+?)$', re.MULTILINE)
        for match in colon_pattern.finditer(markdown_content):
            key = match.group(1).strip()
            value = match.group(2).strip()
            # Filter out noise
            if len(key) < 50 and len(value) > 0 and len(value) < 200:
                # Skip common non-spec patterns
                key_lower = key.lower()
                if not any(skip in key_lower for skip in ['note', 'figure', 'table', 'revision', 'page', 'col']):
                    potential_specs.append(f"{key}: {value}")

        # Pattern 2: Markdown table rows
        table_pattern = re.compile(r'\|([^|]+)\|([^|]+)\|', re.MULTILINE)
        for match in table_pattern.finditer(markdown_content):
            col1 = match.group(1).strip()
            col2 = match.group(2).strip()
            # Skip separator lines and headers
            if (col1 and col2 and
                not col1.startswith('-') and
                not col2.startswith('-') and
                len(col1) < 50 and
                not col1.lower() in ['parameter', 'specification', 'description', 'value', 'unit', 'min', 'max', 'typ']):
                potential_specs.append(f"{col1}: {col2}")

        return potential_specs

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

            # Debug: Save markdown to file
            if self.debug:
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                md_file = f"{self.debug_dir}/markdown_{url_hash}.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(f"# URL: {url}\n\n")
                    f.write(pdf_md)
                print(f"  [DEBUG] Saved markdown to {md_file}")

            if extract_specs:
                specs = await self.extract_specs(pdf_md, product_type)
                result["specs"] = specs

        except Exception as e:
            result["error"] = str(e)

        return result

    async def scrape_multiple(self, urls: List[str], scores: List[float], product_type: Optional[str] = "") -> List[Dict]:
        """
        Scrape multiple PDFs and return their specs with standardized keys.
        Selects top 5 PDFs by score that have valid markdown.
        Uses parallel processing for faster PDF downloads and extraction.

        Args:
            urls: List of PDF URLs
            scores: List of Exa scores corresponding to URLs
            product_type: Optional product type hint

        Returns:
            List of dictionaries with specs for each PDF (top 5 by score)
        """
        import asyncio
        import time

        print(f"\n=== STARTING PARALLEL PDF SCRAPING FOR {len(urls)} URLS ===")
        parallel_start = time.time()

        # First pass: Download all PDFs and extract markdown IN PARALLEL
        failed_results = []
        spec_extractable_results = []

        # Create parallel tasks for all PDFs
        tasks = []
        for url, score in zip(urls, scores):
            task = self.scrape_pdf(url=url, product_type=product_type, extract_specs=False)
            tasks.append((task, url, score))

        # Execute all downloads/extractions in parallel
        print(f"🚀 Processing {len(tasks)} PDFs in parallel...")
        results = await asyncio.gather(*[task for task, _, _ in tasks], return_exceptions=True)

        # Process results
        for i, (result, (_, url, score)) in enumerate(zip(results, tasks), 1):
            # Handle exceptions from gather
            if isinstance(result, Exception):
                error_result = {
                    "url": url,
                    "score": score,
                    "md": None,
                    "specs": {},
                    "error": str(result)
                }
                print(f"  {i}. ✗ Failed [Score: {score:.3f}]: {str(result)[:80]}")
                failed_results.append(error_result)
            elif result.get("error"):
                result["score"] = score
                print(f"  {i}. ✗ Failed [Score: {score:.3f}]: {result['error'][:80]}")
                failed_results.append(result)
            else:
                result["score"] = score
                md_length = len(result.get("md", ""))
                print(f"  {i}. ✓ Success [Score: {score:.3f}]: {md_length} chars")
                spec_extractable_results.append(result)

        parallel_time = time.time() - parallel_start
        print(f"\n⚡ Parallel extraction completed in {parallel_time:.2f}s")

        print(f"\n=== PDF EXTRACTION SUMMARY ===")
        print(f"Successfully extracted: {len(spec_extractable_results)}/{len(urls)} PDFs")
        print(f"Failed: {len(failed_results)}/{len(urls)} PDFs")

        if len(spec_extractable_results) == 0:
            print("ERROR: No valid PDFs could be extracted!")
            return failed_results

        # Sort by score (highest first) and take top 5
        spec_extractable_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = spec_extractable_results[:5]

        print(f"\n=== SELECTING TOP 5 PDFs BY SCORE ===")
        for i, result in enumerate(top_results, 1):
            print(f"  {i}. [Score: {result['score']:.3f}] {result['url'][:80]}...")

        # Need at least 3 valid PDFs to do meaningful comparison
        if len(top_results) < 3:
            print(f"WARNING: Only {len(top_results)} valid PDFs - need at least 3 for comparison")
            print("Returning results without spec extraction")
            return top_results + failed_results

        specs = await self.extract_standardized_specs(
                    pdf_mds=[res["md"] for res in top_results],
                    urls=[res["url"] for res in top_results],
                    product_type=product_type
                )

        successful_results = []
        for i, spec in enumerate(specs):
            result = top_results[i]
            result["specs"] = spec.get("specifications", {})
            result["manufacturer"] = spec.get("manufacturer", "Unknown")
            result["product_name"] = spec.get("product_name", "Unknown Product")
            successful_results.append(result)

        # Return only the top 5 successful results
        return successful_results

    async def extract_standardized_specs(self, pdf_mds: List[Optional[str]], urls: List[str], product_type: Optional[str] = None) -> List[Dict]:
        """
        THREE-PASS extraction for better spec selection quality:
        Pass 1: Extract potential specs using REGEX (no AI - fast and free!)
        Pass 2: AI selects best 5 specs considering search query relevance
        Pass 3: AI extracts those 5 specs with standardized keys

        Args:
            pdf_mds: List of extracted PDF markdowns
            urls: List of PDF URLs for reference
            product_type: Search query used to find these PDFs (for relevance scoring)

        Returns:
            List of spec dictionaries with standardized keys
        """
        if not any(pdf_mds):
            print("ERROR: No markdown content to extract specs from")
            return [{"manufacturer": "Unknown", "product_name": "Unknown", "specifications": {}} for _ in pdf_mds]

        print(f"\n{'='*60}")
        print(f"THREE-PASS SPEC EXTRACTION FOR {len(pdf_mds)} DATASHEETS")
        print(f"{'='*60}")

        # ===== PASS 1: Extract potential specs with REGEX (no AI) =====
        print(f"\n📋 PASS 1: Extracting potential specs with regex (no AI)...")
        pass1_results = []

        for i, md in enumerate(pdf_mds):
            if not md:
                pass1_results.append([])
                continue

            print(f"\n  Processing datasheet {i+1}/{len(pdf_mds)}...")
            # Use regex to find potential spec lines
            potential_specs = self.extract_specs_with_regex(md)

            # Remove duplicates while preserving order
            seen = set()
            unique_specs = []
            for spec in potential_specs:
                if spec not in seen:
                    seen.add(spec)
                    unique_specs.append(spec)

            print(f"    ✓ Found {len(unique_specs)} potential spec lines via regex")
            pass1_results.append(unique_specs)

            # Debug: Save Pass 1 results
            if self.debug:
                pass1_file = f"{self.debug_dir}/pass1_regex_datasheet_{i+1}.txt"
                with open(pass1_file, 'w', encoding='utf-8') as f:
                    f.write(f"URL: {urls[i] if i < len(urls) else 'Unknown'}\n\n")
                    f.write(f"Found {len(unique_specs)} potential specs:\n\n")
                    for spec in unique_specs:
                        f.write(f"{spec}\n")
                print(f"      [DEBUG] Saved Pass 1 regex extraction to {pass1_file}")

        # ===== PASS 2: AI selects best 5 specs (considers relevance to search query) =====
        print(f"\n🎯 PASS 2: AI selecting best 5 specs (considering search query relevance)...")

        # Format regex-extracted specs for AI analysis
        all_specs_summary = ""
        for i, spec_list in enumerate(pass1_results):
            all_specs_summary += f"\nDATASHEET {i+1}:\n"
            if spec_list:
                for spec in spec_list[:100]:  # Limit to first 100 to avoid token limits
                    all_specs_summary += f"  - {spec}\n"
            else:
                all_specs_summary += "  (No specs found)\n"

        # Require specs to appear in at least 80% of datasheets
        import math
        min_coverage = max(3, math.ceil(len(pdf_mds) * 0.8))

        # New prompt that considers search query relevance
        search_query = product_type or "unknown product"
        prompt = f"""You are analyzing specifications extracted from {len(pdf_mds)} product datasheets.

SEARCH QUERY: "{search_query}"

EXTRACTED SPECS FROM ALL DATASHEETS:
{all_specs_summary}

YOUR TASK:
Select EXACTLY 5 specifications that are best for comparing these products.

SELECTION CRITERIA (in priority order):
1. **Relevance to Search Query**: Specs related to "{search_query}" are more important
2. **Common Across All**: Must appear in at least {min_coverage}/{len(pdf_mds)} datasheets
3. **Functional Relevance**: Directly related to what the product does
4. **Differentiation**: Values differ across products (helps comparison)

AVOID:
- Document/revision numbers, dates, catalog numbers
- Specs that appear in fewer than {min_coverage} datasheets
- Generic company info
- Specs unrelated to "{search_query}"

OUTPUT FORMAT:
Return JSON with "selected_specs" array containing EXACTLY 5 items:
{{
  "selected_specs": [
    {{
      "standardized_key": "voltage_v",
      "display_name": "Voltage (V)",
      "reason": "Core spec for {search_query}, appears in all datasheets",
      "coverage": "5/5"
    }},
    ...
  ]
}}

YOU MUST SELECT EXACTLY 5 SPECS - NO MORE, NO LESS.
Return ONLY valid JSON.
"""

        try:
            response_text = await self.ai_client.generate(
                system_prompt=f"You are a spec selection expert. Analyze specs from {len(pdf_mds)} datasheets and choose the 5 best for comparing products related to '{search_query}'. Prioritize specs relevant to the search query.",
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

                # Debug: Save Pass 2 results
                if self.debug:
                    pass2_file = f"{self.debug_dir}/pass2_selected_specs.json"
                    with open(pass2_file, 'w', encoding='utf-8') as f:
                        json.dump(selection, f, indent=2)
                    print(f"    [DEBUG] Saved Pass 2 selection to {pass2_file}")

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
        # Use same limit as Pass 1 (20,000 chars) to ensure consistency
        datasheets_info = ""
        for i, md in enumerate(pdf_mds):
            if md:
                truncated = md[:20000] if len(md) > 20000 else md
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
                system_prompt="Extract the specified specs from each datasheet. Be flexible with spec name variations - if looking for 'Operating Temperature', also check 'Temp Range', 'Working Temp', etc. Use the exact standardized keys in your JSON output.",
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
                    spec_values = spec_obj.get('specifications', {})
                    print(f"    Datasheet {i+1}: {specs_count} specs - {spec_keys}")

                    # Show which values are N/A
                    na_specs = [k for k, v in spec_values.items() if v == "N/A"]
                    if na_specs:
                        print(f"      ⚠️  N/A values: {na_specs}")

                # Debug: Save Pass 3 results
                if self.debug:
                    pass3_file = f"{self.debug_dir}/pass3_final_extraction.json"
                    with open(pass3_file, 'w', encoding='utf-8') as f:
                        json.dump(specs_array, f, indent=2)
                    print(f"\n  [DEBUG] Saved Pass 3 final extraction to {pass3_file}")

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