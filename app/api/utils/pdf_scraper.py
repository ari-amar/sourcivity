#!/usr/bin/env python3
"""
PDF Scraper for extracting specifications from datasheets using Docling and Claude.
"""

import asyncio
import re
import json
import time
import tempfile
import os
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

import requests
import fitz  # PyMuPDF - used only for page count validation
from bs4 import BeautifulSoup
from pdf2markdown4llm import PDF2Markdown4LLM

from prompts import SINGLE_PDF_SPEC_EXTRACTION_PROMPT, BATCHED_SPEC_EXTRACTION_PROMPT
from services.interfaces import AiClientBase


def repair_json(text: str) -> str:
    """Attempt to fix common JSON formatting issues from LLM output."""
    # Remove any text before first { and after last }
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return text
    text = text[start:end + 1]

    # Fix trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Fix missing commas between objects/arrays
    text = re.sub(r'}\s*{', '},{', text)
    text = re.sub(r']\s*\[', '],[', text)

    # Fix unescaped newlines in strings (common LLM issue)
    # This is tricky - try to handle simple cases
    lines = text.split('\n')
    result_lines = []
    for line in lines:
        result_lines.append(line)
    text = '\n'.join(result_lines)

    return text


def safe_parse_json(text: str) -> Optional[dict]:
    """Try to parse JSON with repair attempts."""
    # First try direct parse
    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass

    # Try with repair
    try:
        repaired = repair_json(text)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Try to extract just the products array if full parse fails
    try:
        # Look for products array
        products_match = re.search(r'"products"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if products_match:
            products_str = '[' + products_match.group(1) + ']'
            products_str = repair_json('{"products":' + products_str + '}')
            return json.loads(products_str)
    except json.JSONDecodeError:
        pass

    return None


def derive_contact_url(datasheet_url: str) -> str:
    """
    Derive likely contact page URL from datasheet URL.
    Quick fallback that assumes /contact is available.
    """
    try:
        parsed = urlparse(datasheet_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        return f"{base_url}/contact"
    except Exception as e:
        print(f"Error deriving contact URL from {datasheet_url}: {e}")
        return datasheet_url


async def find_contact_url(supplier_domain: str, timeout: int = 10) -> Optional[str]:
    """
    Crawl supplier homepage to find actual contact page URL.
    """
    try:
        homepage_url = f"https://{supplier_domain}"
        print(f"    → Fetching homepage: {homepage_url}")
        response = requests.get(homepage_url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"    → Scanning for contact links in HTML...")

        contact_keywords = ['contact', 'inquiry', 'quote', 'request', 'get-quote', 'reach-us']

        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()

            if any(keyword in href or keyword in text for keyword in contact_keywords):
                full_url = urljoin(homepage_url, link['href'])
                print(f"    → Found via HTML scan: {full_url}")
                return full_url

        print(f"    → No links found in HTML, testing common paths...")
        common_paths = ['/contact', '/contact-us', '/inquiry', '/request-quote', '/get-quote']
        for path in common_paths:
            test_url = f"{homepage_url}{path}"
            try:
                head_response = requests.head(test_url, timeout=5, allow_redirects=True)
                if head_response.status_code == 200:
                    print(f"    → Found via path test: {test_url}")
                    return test_url
            except:
                continue

        print(f"    → No contact page found")

    except Exception as e:
        print(f"    → Failed to crawl: {str(e)[:60]}")

    return None


class PDFScraper:

    def __init__(self, ai_client: AiClientBase, debug: bool = False):
        self.ai_client = ai_client
        self.debug = debug
        self.converter = PDF2Markdown4LLM(skip_empty_tables=True)

        if self.debug:
            self.debug_dir = "debug_extraction"
            os.makedirs(self.debug_dir, exist_ok=True)
            print(f"DEBUG MODE ENABLED - outputs will be saved to {self.debug_dir}/")

    def _sync_download_pdf(self, url: str) -> bytes:
        """Synchronous PDF download (runs in thread pool)."""
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            content = response.content

            # Check for %PDF magic bytes
            if content.startswith(b'%PDF'):
                if len(content) < 1024:
                    raise ValueError(f"PDF file too small ({len(content)} bytes) - likely corrupted")
                return content

            # HTML fallback: scan for PDF links and follow up to 3
            print(f"    Not a PDF, scanning HTML for PDF links: {url[:80]}")
            try:
                html_text = content.decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html_text, 'html.parser')
                pdf_links = []

                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.lower().endswith('.pdf') or '.pdf?' in href.lower():
                        full_url = urljoin(url, href)
                        if full_url not in pdf_links:
                            pdf_links.append(full_url)
                        if len(pdf_links) >= 3:
                            break

                for pdf_url in pdf_links:
                    try:
                        print(f"    Following PDF link: {pdf_url[:80]}")
                        pdf_response = requests.get(pdf_url, timeout=30, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        })
                        pdf_response.raise_for_status()
                        pdf_content = pdf_response.content

                        if pdf_content.startswith(b'%PDF') and len(pdf_content) >= 1024:
                            return pdf_content
                    except Exception as e:
                        print(f"    Failed to follow PDF link {pdf_url[:60]}: {e}")
                        continue

            except Exception as e:
                print(f"    HTML parsing failed: {e}")

            raise ValueError(f"URL does not point to a valid PDF file and no PDF links found in HTML")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download from {url}: {str(e)}")

    async def download_pdf(self, url: str) -> bytes:
        """Download PDF from URL (runs in thread pool for parallelism)."""
        return await asyncio.to_thread(self._sync_download_pdf, url)

    def validate_page_count(self, pdf_content: bytes) -> int:
        """Check page count using PyMuPDF. Reject PDFs with more than 20 pages."""
        with fitz.open(stream=pdf_content) as doc:
            page_count = len(doc)
            if page_count == 0:
                raise ValueError("PDF has no pages")
            if page_count > 20:
                raise ValueError(f"PDF has {page_count} pages (max 20)")
            return page_count

    def _sync_extract_markdown(self, pdf_content: bytes) -> str:
        """Synchronous PDF to markdown conversion (runs in thread pool)."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            md_text = self.converter.convert(tmp_path)
            if not md_text or len(md_text.strip()) < 100:
                raise ValueError(f"PDF extraction produced no meaningful content (only {len(md_text or '')} chars)")
            return md_text
        finally:
            os.unlink(tmp_path)

    async def extract_markdown_from_pdf(self, pdf_content: bytes) -> str:
        """
        Convert PDF to markdown using Docling (runs in thread pool for parallelism).
        """
        return await asyncio.to_thread(self._sync_extract_markdown, pdf_content)

    async def extract_specs(self, pdf_md: str, product_type: Optional[str] = None) -> Dict:
        """
        Extract specifications from PDF markdown using AI.
        """
        # Limit to avoid token limits
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
                        "manufacturer": {"type": "string"},
                        "product_name": {"type": "string"},
                        "specifications": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["manufacturer", "product_name", "specifications"]
                },
                max_tokens=4096
            )

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not extract specs", "raw_response": response_text}

        except Exception as e:
            return {"error": f"Failed to extract specs: {str(e)}"}

    async def scrape_pdf(self, url: str, product_type: Optional[str] = None) -> Dict:
        """
        Download PDF, validate, convert to markdown, and extract specs.
        """
        result = {
            "url": url,
            "md": None,
            "specs": {},
            "manufacturer": None,
            "product_name": None,
            "error": None
        }

        try:
            # Download (with HTML fallback) - async for parallelism
            pdf_content = await self.download_pdf(url)

            # Validate page count
            page_count = self.validate_page_count(pdf_content)
            print(f"    PDF has {page_count} pages")

            # Convert to markdown via docling (async for parallelism)
            pdf_md = await self.extract_markdown_from_pdf(pdf_content)

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

        except Exception as e:
            result["error"] = str(e)

        return result

    async def scrape_multiple(self, urls: List[str], scores: List[float], product_type: Optional[str] = "") -> List[Dict]:
        """
        Scrape multiple PDFs and return their specs with standardized keys.
        Downloads all URLs in parallel, extracts specs with AI from all valid PDFs,
        normalizes keys, and finds common specs across all products.
        """
        print(f"\n=== STARTING PARALLEL PDF SCRAPING FOR {len(urls)} URLS ===")
        parallel_start = time.time()

        # STEP 1: Download all PDFs and extract markdown IN PARALLEL
        failed_results = []
        successful_results = []

        tasks = []
        for url, score in zip(urls, scores):
            task = self.scrape_pdf(url=url, product_type=product_type)
            tasks.append((task, url, score))

        print(f"Processing {len(tasks)} URLs in parallel...")
        results = await asyncio.gather(*[task for task, _, _ in tasks], return_exceptions=True)

        for i, (result, (_, url, score)) in enumerate(zip(results, tasks), 1):
            if isinstance(result, Exception):
                error_result = {
                    "url": url, "score": score, "md": None,
                    "specs": {}, "error": str(result)
                }
                print(f"  {i}. FAIL [Score: {score:.3f}]: {str(result)[:80]}")
                failed_results.append(error_result)
            elif result.get("error"):
                result["score"] = score
                print(f"  {i}. FAIL [Score: {score:.3f}]: {result['error'][:80]}")
                failed_results.append(result)
            else:
                result["score"] = score
                md_length = len(result.get("md", ""))
                print(f"  {i}. OK   [Score: {score:.3f}]: {md_length} chars")
                successful_results.append(result)

        parallel_time = time.time() - parallel_start
        print(f"\nParallel download completed in {parallel_time:.2f}s")
        print(f"Successfully extracted: {len(successful_results)}/{len(urls)} PDFs")
        print(f"Failed: {len(failed_results)}/{len(urls)} PDFs")

        if len(successful_results) == 0:
            print("ERROR: No valid PDFs could be extracted!")
            return failed_results

        if len(successful_results) < 3:
            print(f"WARNING: Only {len(successful_results)} valid PDFs - need at least 3 for comparison")
            print("Returning results without spec extraction")
            return successful_results + failed_results

        # STEP 2: Batched AI call for extraction + normalization
        # Try full batch first, fall back to smaller batches if JSON parsing fails
        print(f"\n=== BATCHED AI EXTRACTION FOR {len(successful_results)} PDFs ===")
        extraction_start = time.time()

        async def extract_batch(batch_results: List[Dict], batch_offset: int = 0) -> bool:
            """Extract specs from a batch of PDFs. Returns True if successful."""
            # Calculate chars per PDF to stay under 100K total context
            MAX_TOTAL_CHARS = 100000
            chars_per_pdf = min(8000, MAX_TOTAL_CHARS // len(batch_results))
            print(f"  Processing batch of {len(batch_results)} PDFs ({chars_per_pdf} chars each)")

            # Build combined prompt
            pdf_contents = ""
            for i, result in enumerate(batch_results, 1):
                md = result.get("md", "")[:chars_per_pdf]
                pdf_contents += f"\n--- PDF {i} ---\n{md}\n"

            product_hint = f"These are datasheets for {product_type}." if product_type else ""
            prompt = BATCHED_SPEC_EXTRACTION_PROMPT.format(
                product_hint=product_hint,
                num_pdfs=len(batch_results),
                pdf_contents=pdf_contents
            )

            try:
                response_text = await self.ai_client.generate(
                    system_prompt="You extract and normalize specs from multiple datasheets.",
                    user_prompt=prompt,
                    enforce_json=True,
                    max_tokens=4096
                )

                # Parse response with repair attempts
                parsed = safe_parse_json(response_text)
                if parsed:
                    for product in parsed.get("products", []):
                        idx = product.get("pdf_index", 0) - 1
                        if 0 <= idx < len(batch_results):
                            batch_results[idx]["manufacturer"] = product.get("manufacturer", "Unknown")
                            batch_results[idx]["product_name"] = product.get("product_name", "Unknown")
                            batch_results[idx]["specs"] = product.get("specs", {})
                            specs_count = len(batch_results[idx]["specs"])
                            global_idx = batch_offset + idx + 1
                            print(f"  {global_idx}. OK: {batch_results[idx]['manufacturer']} {batch_results[idx]['product_name']} ({specs_count} specs)")
                    return True
                else:
                    print(f"  ERROR: Failed to parse JSON response")
                    return False

            except Exception as e:
                print(f"  ERROR: Batch extraction failed: {e}")
                return False

        # Try full batch first
        success = await extract_batch(successful_results)

        # If full batch failed, try smaller batches
        if not success and len(successful_results) > 3:
            print(f"\n  Retrying with smaller batches...")
            BATCH_SIZE = 5
            all_success = True
            for i in range(0, len(successful_results), BATCH_SIZE):
                batch = successful_results[i:i + BATCH_SIZE]
                batch_success = await extract_batch(batch, batch_offset=i)
                if not batch_success:
                    all_success = False
                    # Mark failed batch items
                    for result in batch:
                        if not result.get("specs"):
                            result["specs"] = {}
                            result["manufacturer"] = "Unknown"
                            result["product_name"] = "Unknown"

        # Mark any remaining items without specs
        for result in successful_results:
            if "specs" not in result:
                result["specs"] = {}
                result["manufacturer"] = "Unknown"
                result["product_name"] = "Unknown"

        extraction_time = time.time() - extraction_start
        print(f"Batched extraction completed in {extraction_time:.2f}s")

        # Filter to results that have specs
        results_with_specs = [r for r in successful_results if r.get("specs") and len(r["specs"]) > 0]
        if len(results_with_specs) < 3:
            print(f"WARNING: Only {len(results_with_specs)} PDFs have extracted specs")
            return successful_results

        # STEP 3: Find common specs across all PDFs
        # Goal: Keep all PDFs, find specs that appear in most/all of them
        print(f"\n=== FINDING COMMON SPECS ===")

        TARGET_SPECS = 5  # Number of spec columns to target
        num_pdfs = len(results_with_specs)

        # Count frequency of each spec across all PDFs
        spec_frequency = {}
        for result in results_with_specs:
            for key in result.get("specs", {}).keys():
                spec_frequency[key] = spec_frequency.get(key, 0) + 1

        # Group specs by how many PDFs have them
        specs_by_coverage = {}  # coverage_count -> list of specs
        for spec, count in spec_frequency.items():
            if count not in specs_by_coverage:
                specs_by_coverage[count] = []
            specs_by_coverage[count].append(spec)

        # Build column list: start with specs in all PDFs, work down
        common_keys = []
        for coverage in range(num_pdfs, 0, -1):
            if coverage in specs_by_coverage:
                specs_at_level = specs_by_coverage[coverage]
                print(f"  Specs in {coverage}/{num_pdfs} PDFs: {specs_at_level}")
                for spec in specs_at_level:
                    if len(common_keys) < TARGET_SPECS:
                        common_keys.append(spec)
            if len(common_keys) >= TARGET_SPECS:
                break

        print(f"\n  Selected {len(common_keys)} spec columns: {common_keys}")

        # All PDFs are included (we built specs around them)
        filtered_results = results_with_specs

        # Calculate fill rate for logging
        total_cells = len(filtered_results) * len(common_keys)
        filled_cells = 0
        for result in filtered_results:
            pdf_specs = result.get("specs", {})
            filled_cells += sum(1 for key in common_keys if key in pdf_specs)
        fill_rate = (filled_cells / total_cells * 100) if total_cells > 0 else 0
        print(f"  Fill rate: {filled_cells}/{total_cells} cells ({fill_rate:.0f}%)")

        # STEP 5: Build final results with only common specs
        print(f"\n=== BUILDING FINAL RESULTS ===")

        final_results = []
        for result in filtered_results:
            pdf_specs = result.get("specs", {})
            standardized_specs = {}

            for key in common_keys:
                standardized_specs[key] = pdf_specs.get(key, "N/A")

            result["specs"] = standardized_specs
            result.pop("md", None)
            result.pop("score", None)
            final_results.append(result)
            print(f"  {result.get('product_name', 'Unknown')}: {len([v for v in standardized_specs.values() if v != 'N/A'])}/{len(standardized_specs)} specs filled")

        # STEP 5: Contact URL extraction (fast derived URLs only, skip crawling)
        print(f"\n=== EXTRACTING CONTACT URLS ===")
        for result in final_results:
            result["contact_url"] = derive_contact_url(result["url"])

        print(f"\n=== PIPELINE COMPLETE: {len(final_results)} results ===")
        return final_results
