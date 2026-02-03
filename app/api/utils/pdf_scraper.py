#!/usr/bin/env python3
"""
PDF Scraper for extracting specifications from datasheets using MarkItDown and Claude.
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
from markitdown import MarkItDown

from prompts import SINGLE_PDF_SPEC_EXTRACTION_PROMPT, NORMALIZE_SPEC_KEYS_PROMPT
from services.interfaces import AiClientBase


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
        self.markitdown = MarkItDown()

        if self.debug:
            self.debug_dir = "debug_extraction"
            os.makedirs(self.debug_dir, exist_ok=True)
            print(f"DEBUG MODE ENABLED - outputs will be saved to {self.debug_dir}/")

    def download_pdf(self, url: str) -> bytes:
        """
        Download content from URL. If it's a PDF (%PDF header), return it.
        If it's HTML, scan for up to 3 PDF links and follow them.
        """
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

    def validate_page_count(self, pdf_content: bytes) -> int:
        """Check page count using PyMuPDF. Reject PDFs with more than 10 pages."""
        with fitz.open(stream=pdf_content) as doc:
            page_count = len(doc)
            if page_count == 0:
                raise ValueError("PDF has no pages")
            if page_count > 10:
                raise ValueError(f"PDF has {page_count} pages (max 10)")
            return page_count

    def extract_markdown_from_pdf(self, pdf_content: bytes) -> str:
        """
        Convert PDF to markdown using MarkItDown.
        """
        # Write to temp file since markitdown works with file paths
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_content)
            tmp_path = tmp.name

        try:
            result = self.markitdown.convert(tmp_path)
            md_text = result.text_content

            if not md_text or len(md_text.strip()) < 100:
                raise ValueError(f"PDF extraction produced no meaningful content (only {len(md_text or '')} chars)")

            return md_text
        finally:
            os.unlink(tmp_path)

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
            # Download (with HTML fallback)
            pdf_content = self.download_pdf(url)

            # Validate page count
            page_count = self.validate_page_count(pdf_content)
            print(f"    PDF has {page_count} pages")

            # Convert to markdown via markitdown
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

        except Exception as e:
            result["error"] = str(e)

        return result

    async def scrape_multiple(self, urls: List[str], scores: List[float], product_type: Optional[str] = "") -> List[Dict]:
        """
        Scrape multiple PDFs and return their specs with standardized keys.
        Downloads all 20 URLs in parallel, selects top 5 valid PDFs by score,
        extracts specs with AI, normalizes keys, and selects top 5 specs by coverage.
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

        # Select top 5 by Exa score
        successful_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = successful_results[:5]

        print(f"\n=== SELECTING TOP 5 PDFs BY SCORE ===")
        for i, result in enumerate(top_results, 1):
            print(f"  {i}. [Score: {result['score']:.3f}] {result['url'][:80]}...")

        if len(top_results) < 3:
            print(f"WARNING: Only {len(top_results)} valid PDFs - need at least 3 for comparison")
            print("Returning results without spec extraction")
            return top_results + failed_results

        # STEP 2: AI spec extraction per PDF (semaphore-throttled)
        print(f"\n=== AI SPEC EXTRACTION (Semaphore(5)) ===")
        semaphore = asyncio.Semaphore(5)
        extraction_start = time.time()

        async def extract_with_semaphore(result):
            async with semaphore:
                md = result.get("md", "")
                if not md:
                    return {"error": "No markdown content"}
                specs = await self.extract_specs(md, product_type)
                return specs

        extraction_tasks = [extract_with_semaphore(r) for r in top_results]
        extraction_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        for i, (result, extraction) in enumerate(zip(top_results, extraction_results)):
            if isinstance(extraction, Exception):
                result["specs"] = {}
                result["manufacturer"] = "Unknown"
                result["product_name"] = "Unknown"
                result["extraction_error"] = str(extraction)
                print(f"  {i+1}. FAIL: {str(extraction)[:80]}")
            elif extraction.get("error"):
                result["specs"] = {}
                result["manufacturer"] = "Unknown"
                result["product_name"] = "Unknown"
                result["extraction_error"] = extraction["error"]
                print(f"  {i+1}. FAIL: {extraction['error'][:80]}")
            else:
                result["specs"] = extraction.get("specifications", {})
                result["manufacturer"] = extraction.get("manufacturer", "Unknown")
                result["product_name"] = extraction.get("product_name", "Unknown")
                specs_count = len(result["specs"])
                print(f"  {i+1}. OK: {result['manufacturer']} {result['product_name']} ({specs_count} specs)")

        extraction_time = time.time() - extraction_start
        print(f"AI extraction completed in {extraction_time:.2f}s")

        # Filter to results that have specs
        results_with_specs = [r for r in top_results if r.get("specs") and len(r["specs"]) > 0]
        if len(results_with_specs) < 3:
            print(f"WARNING: Only {len(results_with_specs)} PDFs have extracted specs")
            return top_results

        # STEP 3: AI normalize synonymous keys
        print(f"\n=== AI SPEC KEY NORMALIZATION ===")
        norm_start = time.time()

        pdf_keys_text = ""
        for i, result in enumerate(results_with_specs):
            keys = list(result["specs"].keys())  # Send ALL keys
            pdf_keys_text += f"\nPDF {i+1} keys: {', '.join(keys)}\n"

        prompt = NORMALIZE_SPEC_KEYS_PROMPT.format(
            num_pdfs=len(results_with_specs),
            pdf_keys=pdf_keys_text
        )

        try:
            response_text = await self.ai_client.generate(
                system_prompt="You are an expert at analyzing and comparing product datasheets. You normalize specification names across different datasheets.",
                user_prompt=prompt,
                enforce_json=True,
                max_tokens=4096
            )

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                normalization = json.loads(json_match.group())
            else:
                print("Failed to parse normalization response")
                normalization = {}
        except Exception as e:
            print(f"Error in normalization: {e}")
            normalization = {}

        norm_time = time.time() - norm_start
        print(f"Normalization completed in {norm_time:.2f}s")
        print(f"Found {len(normalization)} standardized spec groups")

        # STEP 3b: Verify AI mappings and build spec sets per PDF
        print(f"\n=== VERIFYING AI MAPPINGS ===")

        verified_specs = {}
        for std_key, spec_info in normalization.items():
            pdf_matches = spec_info.get("pdf_matches", {})
            display_name = spec_info.get("display_name", std_key)
            verified_count = 0
            verified_matches = {}

            for pdf_idx_str, original_key in pdf_matches.items():
                pdf_idx = int(pdf_idx_str) - 1  # Convert 1-indexed to 0-indexed
                if pdf_idx < 0 or pdf_idx >= len(results_with_specs):
                    continue

                pdf_specs = results_with_specs[pdf_idx].get("specs", {})

                # Exact match
                if original_key in pdf_specs:
                    verified_count += 1
                    verified_matches[pdf_idx_str] = original_key
                else:
                    # Case-insensitive fallback
                    lower_key = original_key.lower()
                    for actual_key in pdf_specs:
                        if actual_key.lower() == lower_key:
                            verified_count += 1
                            verified_matches[pdf_idx_str] = actual_key
                            break

            if verified_count > 0:
                verified_specs[std_key] = {
                    "display_name": display_name,
                    "pdf_matches": verified_matches,
                    "coverage": verified_count
                }

        print(f"Verified {len(verified_specs)} spec groups")

        # Build set of normalized spec keys for each PDF
        pdf_spec_sets = {}
        for i, result in enumerate(results_with_specs):
            pdf_idx_str = str(i + 1)
            pdf_spec_sets[pdf_idx_str] = set()
            for std_key, info in verified_specs.items():
                if pdf_idx_str in info["pdf_matches"]:
                    pdf_spec_sets[pdf_idx_str].add(std_key)

        for pdf_idx_str, spec_set in pdf_spec_sets.items():
            print(f"  PDF {pdf_idx_str}: {len(spec_set)} normalized specs")

        # STEP 3c: Filter results by spec commonality with ALL other results
        print(f"\n=== FILTERING RESULTS BY SPEC COMMONALITY (4+ with ALL others) ===")

        MIN_COMMON_SPECS = 4
        remaining_indices = list(range(len(results_with_specs)))

        # Iteratively remove results that don't share 4+ specs with ALL other remaining results
        changed = True
        while changed:
            changed = False
            indices_to_remove = []

            for i in remaining_indices:
                pdf_idx_str_i = str(i + 1)
                specs_i = pdf_spec_sets[pdf_idx_str_i]

                # Check commonality with ALL other remaining results
                meets_threshold = True
                for j in remaining_indices:
                    if i == j:
                        continue
                    pdf_idx_str_j = str(j + 1)
                    specs_j = pdf_spec_sets[pdf_idx_str_j]
                    common_specs = specs_i & specs_j
                    if len(common_specs) < MIN_COMMON_SPECS:
                        meets_threshold = False
                        break

                if not meets_threshold:
                    indices_to_remove.append(i)

            if indices_to_remove:
                changed = True
                for idx in indices_to_remove:
                    remaining_indices.remove(idx)
                    print(f"  Removed PDF {idx + 1} (insufficient commonality)")

        print(f"\n  Remaining after filtering: {len(remaining_indices)} results")
        for idx in remaining_indices:
            print(f"    - PDF {idx + 1}: {results_with_specs[idx]['url'][:60]}...")

        # Get filtered results
        filtered_results = [results_with_specs[i] for i in remaining_indices]

        if len(filtered_results) == 0:
            print("WARNING: All results filtered out! Keeping original results.")
            filtered_results = results_with_specs

        # STEP 3d: Collect ALL specs that appear across the filtered results
        print(f"\n=== COLLECTING ALL COMMON SPECS ===")

        # Get spec keys present in at least one filtered result
        filtered_pdf_indices = [str(i + 1) for i in remaining_indices] if remaining_indices else [str(i + 1) for i in range(len(results_with_specs))]

        selected_specs = []
        for std_key, info in verified_specs.items():
            # Check if this spec appears in at least one filtered result
            has_match = any(pdf_idx in info["pdf_matches"] for pdf_idx in filtered_pdf_indices)
            if has_match:
                selected_specs.append((std_key, info))

        print(f"Selected {len(selected_specs)} specs for output")

        # STEP 3e: Build final results with standardized keys
        print(f"\n=== BUILDING FINAL RESULTS ===")

        final_results = []
        for result in filtered_results:
            pdf_specs = result.get("specs", {})
            standardized_specs = {}

            # Find which PDF index this result was in the original results_with_specs
            result_idx = results_with_specs.index(result)
            pdf_idx_str = str(result_idx + 1)  # 1-indexed

            for std_key, info in selected_specs:
                original_key = info["pdf_matches"].get(pdf_idx_str)
                if original_key and original_key in pdf_specs:
                    standardized_specs[info["display_name"]] = pdf_specs[original_key]
                else:
                    # Try case-insensitive match
                    found = False
                    if original_key:
                        lower_key = original_key.lower()
                        for actual_key in pdf_specs:
                            if actual_key.lower() == lower_key:
                                standardized_specs[info["display_name"]] = pdf_specs[actual_key]
                                found = True
                                break
                    if not found:
                        standardized_specs[info["display_name"]] = "N/A"

            result["specs"] = standardized_specs
            # Remove markdown from response to save bandwidth
            result.pop("md", None)
            result.pop("score", None)
            final_results.append(result)

        # STEP 4: Contact URL extraction (parallel)
        print(f"\n=== EXTRACTING CONTACT URLS ===")

        async def get_contact_url(result):
            derived_url = derive_contact_url(result["url"])
            result["contact_url"] = derived_url
            try:
                domain = urlparse(result["url"]).netloc
                actual_contact = await find_contact_url(domain, timeout=8)
                if actual_contact:
                    result["contact_url"] = actual_contact
            except:
                pass

        contact_tasks = [get_contact_url(r) for r in final_results]
        await asyncio.gather(*contact_tasks, return_exceptions=True)

        print(f"\n=== PIPELINE COMPLETE: {len(final_results)} results ===")
        return final_results
