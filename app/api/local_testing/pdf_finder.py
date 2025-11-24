#!/usr/bin/env python3
"""
LLM-Powered Industrial Component PDF Finder
Uses Claude AI to find PDF datasheets for industrial components based on its knowledge.
"""

import argparse
import requests
import json
import sys
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, unquote, parse_qs, quote

# Anthropic API configuration
# Get from environment variable or use default
import os
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def call_claude(prompt, system_prompt=None):
    """Call Claude API to get intelligent responses."""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 2048,
        "messages": messages
    }

    if system_prompt:
        data["system"] = system_prompt

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['content'][0]['text']
    except Exception as e:
        print(f"\nClaude API error: {e}", file=sys.stderr)
        try:
            if 'response' in locals():
                error_data = response.json()
                print(f"Error details: {error_data.get('error', {}).get('message', 'Unknown error')}", file=sys.stderr)
                if 'not_found_error' in str(error_data):
                    print("\nNote: The API key may be invalid or expired.", file=sys.stderr)
                    print("Please set a valid Anthropic API key using: export ANTHROPIC_API_KEY=your-key-here", file=sys.stderr)
        except:
            pass
        return None


def find_pdfs_with_llm(component_description, max_results=5, verbose=False, interactive=False):
    """Use Claude as Industrial Search Optimizer to generate search query and find PDFs."""

    # Use stdout for interactive mode, stderr for command-line verbose mode
    output = sys.stdout if interactive else sys.stderr

    system_prompt = """You are the "Industrial Search Optimizer."
Your goal is to generate a SINGLE Google/DuckDuckGo search query that finds a SINGLE-PRODUCT DATASHEET (NOT catalogs, NOT manuals).

### CRITICAL REQUIREMENTS:
* Find DATASHEET ONLY - technical specifications for ONE specific product/part number
* EXCLUDE catalogs (multi-product documents)
* EXCLUDE user manuals, installation guides, brochures
* MUST be product-specific technical documentation

### INSTRUCTIONS:
1. **Analyze the Input:** Identify the specific part number or product model
2. **Select Technical Fingerprints:** Choose keywords that appear in DATASHEETS ONLY
3. **Apply Exclusion Filters:**
   * MUST use `filetype:pdf`
   * MUST use `datasheet` keyword
   * MUST exclude: `-catalog -brochure -manual -guide -installation -user -series`
   * MUST exclude gray market: `-rfq -quote -alibaba -ebay`
4. **Construct the Query:** Part number + "datasheet" + filetype:pdf + exclusions

### FINGERPRINT LOGIC (Datasheet-specific only):
* **Electronics:** "absolute maximum ratings" OR "electrical characteristics" OR "pin configuration"
* **Mechanical:** "technical specifications" OR "dimensions" OR "performance data"
* **Process Equipment:** "specifications" OR "performance curve" OR "technical data"
* **Raw Materials:** "material properties" OR "technical data sheet"

### OUTPUT FORMAT:
Return ONLY the search query string with exclusions. No JSON, no explanations."""

    prompt = f"""Input: "{component_description}"

Generate a search query that finds SINGLE-PRODUCT DATASHEETS ONLY (not catalogs or manuals).

Requirements:
1. Must include "datasheet" keyword
2. Must use filetype:pdf
3. Must exclude catalogs: -catalog
4. Must exclude manuals: -manual -guide -brochure
5. Focus on specific part number if available

Examples:
Input: "LM555 timer"
Output: LM555 datasheet filetype:pdf -catalog -manual -brochure

Input: "100 sccm mass flow controller"
Output: 100 sccm mass flow controller datasheet filetype:pdf -catalog -manual

Input: "SKF 6205 bearing"
Output: SKF 6205 bearing datasheet filetype:pdf -catalog -series -manual

Now generate the search query for: {component_description}

Return ONLY the search query string with exclusions. Keep it focused on SINGLE-PRODUCT datasheets."""

    if verbose and interactive:
        print("[Step 2] Optimizing search query with LLM...", file=output)

    # Get optimized search query from Claude
    search_query = call_claude(prompt, system_prompt)

    if not search_query:
        return []

    # Clean up the search query
    search_query = search_query.strip().strip('"\'')

    # Assess supplier quality BEFORE searching to boost top suppliers
    if verbose and interactive:
        print("[Step 3] Identifying top suppliers with LLM...", file=output)

    supplier_info = assess_supplier_quality_llm(component_description)

    # Add site: operators to boost top suppliers in search
    if supplier_info and 'tier1_domains' in supplier_info and len(supplier_info['tier1_domains']) > 0:
        # Add top 3 Tier 1 suppliers to search query using site: operator
        top_suppliers = supplier_info['tier1_domains'][:3]
        site_boost = " (" + " OR ".join([f"site:{domain}" for domain in top_suppliers]) + ")"
        boosted_query = search_query + site_boost

        if verbose:
            if interactive:
                print(f"  → Tier 1 suppliers: {', '.join(top_suppliers)}", file=output)
                print(f"  → Boosted query: {boosted_query}", file=output)
                print()
                print("[Step 4] Performing DuckDuckGo search with supplier boost...", file=output)
            else:
                print(f"Boosting search for: {', '.join(top_suppliers)}", file=output)
                print(f"Search query: {boosted_query}", file=output)
                print("Searching DuckDuckGo...", file=output)

        # Use boosted query
        pdf_urls = search_duckduckgo(boosted_query, max_results * 3)

        # Fallback: If boosted search returns 0 results, try without boost
        if len(pdf_urls) == 0:
            if verbose:
                if interactive:
                    print(f"  → Boosted search returned 0 results, retrying without boost...", file=output)
                else:
                    print("Boosted search returned 0 results, retrying without boost...", file=output)

            pdf_urls = search_duckduckgo(search_query, max_results * 3)
    else:
        if verbose:
            if interactive:
                print(f"  → Query: {search_query}", file=output)
                print()
                print("[Step 4] Performing DuckDuckGo search...", file=output)
            else:
                print(f"Search query: {search_query}", file=output)
                print("Searching DuckDuckGo...", file=output)

        # Use original query
        pdf_urls = search_duckduckgo(search_query, max_results * 3)

    if verbose:
        if interactive:
            print(f"  → Found {len(pdf_urls)} PDF URLs", file=output)
            print()
            print("[Step 5] Validating URLs and ranking by supplier quality...", file=output)
        else:
            print(f"Found {len(pdf_urls)} PDF URLs from search", file=output)
            print("Validating URLs...", file=output)

    # Validate URLs to ensure they're actually accessible PDFs and match specifications
    # Pass supplier_info to avoid recalculating
    validated_urls = validate_pdf_urls(pdf_urls, max_results, component_description, verbose, interactive, supplier_info)

    if verbose:
        if interactive:
            print()
            print(f"[Complete] Validated {len(validated_urls)} high-quality PDF datasheets", file=output)
        else:
            print(f"Validated {len(validated_urls)} working PDF URLs", file=output)

    return validated_urls


def extract_specifications_llm(query):
    """Use LLM to extract ALL technical specifications from query."""
    system_prompt = """You are a technical specification extractor. Your job is to identify ALL technical specifications in a user query.

Extract any numeric specifications with units, including but not limited to:
- Flow rates (SLPM, SCCM, LPM, ml/min, etc.)
- Voltages (V, kV, mV)
- Currents (A, mA, uA)
- Pressures (psi, bar, Pa, kPa)
- Temperatures (°C, °F, K)
- Dimensions (mm, cm, inches)
- Power (W, kW, mW)
- Frequencies (Hz, kHz, MHz, GHz)
- Capacitance (F, uF, nF, pF)
- Resistance (Ω, kΩ, MΩ)
- Any other numeric technical specifications

Return ONLY a JSON object with the specifications found, or an empty object {} if none found.

Example outputs:
{"flow_rate": "2500 SLPM"}
{"voltage": "24V", "current": "2A"}
{"pressure": "3000 psi", "temperature": "150°C"}
{"size": "6205", "type": "bearing"}
{}

Return ONLY the JSON object, no other text."""

    prompt = f"""Extract all technical specifications from this query: "{query}"

Return ONLY a JSON object."""

    response = call_claude(prompt, system_prompt)

    if not response:
        return {}

    try:
        # Clean up response and parse JSON
        response = response.strip()
        specs = json.loads(response)
        return specs
    except:
        return {}


def validate_url_specs_llm(url, query_specs):
    """Use LLM to check if URL/filename contains specifications that match the query."""
    if not query_specs:
        return True  # No specs to validate

    system_prompt = """You are a technical specification validator. Your job is to determine if a URL/filename matches the technical specifications requested.

You will be given:
1. Technical specifications from a user's query
2. A URL to a PDF datasheet

Your task: Determine if the URL suggests the PDF is for a product that matches the requested specifications.

Look for specifications in:
- The filename
- URL path segments
- Product codes/model numbers

Rules:
- If the URL contains numeric specifications that CONFLICT with the query, return NO
- A 10x difference is a conflict (e.g., 2500 vs 20)
- If the URL has no specifications, return YES (cannot determine conflict)
- Be strict about numeric matches but flexible about formats

Return ONLY "YES" or "NO", nothing else."""

    specs_text = json.dumps(query_specs)
    prompt = f"""Query specifications: {specs_text}

URL: {url}

Does this URL match the requested specifications?

Return ONLY "YES" or "NO"."""

    response = call_claude(prompt, system_prompt)

    if not response:
        return True  # If LLM fails, don't filter out

    return response.strip().upper() == "YES"


def assess_supplier_quality_llm(component_description):
    """Use LLM to identify the most reliable suppliers for this component category."""
    system_prompt = """You are an industrial procurement expert. Your job is to identify the MOST RELIABLE, HIGH-QUALITY suppliers for industrial components.

For any component, you should prioritize:
1. **OEM/Manufacturers** - Original equipment manufacturers (highest priority)
2. **Authorized Distributors** - Companies authorized by manufacturers
3. **Major Industrial Distributors** - Well-known, reputable distributors
4. **Technical Organizations** - Standards bodies, educational institutions

Supplier Quality Tiers:

**TIER 1 (Best - OEMs/Manufacturers):**
- Texas Instruments (TI), Analog Devices, Microchip, NXP, STMicroelectronics (electronics)
- SKF, NSK, Timken (bearings)
- Brooks Instrument, Alicat, MKS (flow controllers)
- Parker, Eaton, Bosch Rexroth (hydraulics)
- Grundfos, Xylem (pumps)
- Component-specific manufacturers

**TIER 2 (Good - Authorized Distributors):**
- Digi-Key, Mouser, Newark/Farnell, Arrow (electronics)
- McMaster-Carr, Grainger (industrial MRO)
- RS Components, Allied Electronics

**TIER 3 (Acceptable - Technical/Educational):**
- University domains (.edu)
- IEEE, ASTM standards organizations

**AVOID (Gray Market/Low Quality):**
- Alibaba, AliExpress, DHgate, eBay
- "RFQ" sites, quote aggregators
- Unknown resellers

Return a JSON object with:
{
  "category": "electronics|mechanical|process_equipment|raw_materials",
  "tier1_domains": ["domain1.com", "domain2.com", ...],
  "tier2_domains": ["domain1.com", "domain2.com", ...],
  "tier3_domains": [".edu", ".org"],
  "search_boost": "site:domain1.com OR site:domain2.com OR ..."
}

The search_boost should be a DuckDuckGo site: operator string to prioritize top suppliers."""

    prompt = f"""Component: "{component_description}"

Identify the most reliable suppliers and manufacturers for this component.

Return ONLY a JSON object with tier1_domains, tier2_domains, tier3_domains, category, and search_boost."""

    response = call_claude(prompt, system_prompt)

    if not response:
        return None

    try:
        response = response.strip()
        # Remove markdown code blocks if present
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join([l for l in lines if not l.startswith('```')])
            response = response.strip()

        supplier_info = json.loads(response)
        return supplier_info
    except:
        return None


def rank_url_by_supplier_llm(url, supplier_info):
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


def validate_pdf_urls(urls, max_results, user_query, verbose=False, interactive=False, supplier_info=None):
    """Validate that URLs actually return real PDF files and match specifications."""
    validated = []

    # Use stdout for interactive mode, stderr for command-line verbose mode
    output = sys.stdout if interactive else sys.stderr

    # Extract specifications from user query using LLM
    if verbose and interactive:
        print("  [5a] Extracting specifications with LLM...", file=output)

    query_specs = extract_specifications_llm(user_query)

    if verbose and query_specs:
        if interactive:
            print(f"       → Specs: {json.dumps(query_specs)}", file=output)
        else:
            print(f"Extracted specs from query: {json.dumps(query_specs)}", file=output)

    # If supplier_info wasn't provided, calculate it
    if not supplier_info:
        if verbose and interactive:
            print("  [5b] Assessing supplier quality with LLM...", file=output)

        supplier_info = assess_supplier_quality_llm(user_query)

        if verbose and supplier_info:
            if interactive:
                print(f"       → Tier 1 (OEMs): {', '.join(supplier_info.get('tier1_domains', [])[:3])}", file=output)
            else:
                print(f"Prioritizing suppliers: Tier 1 (OEMs): {', '.join(supplier_info.get('tier1_domains', [])[:3])}", file=output)

    if verbose and interactive:
        print("  [5c] Downloading and validating each PDF URL...", file=output)

    # Collect validated URLs with their supplier ranking
    validated_with_scores = []

    for url in urls:
        try:
            # Download first 4KB to check if it's actually a PDF
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': 'bytes=0-4095'  # Only download first 4KB
            }

            response = requests.get(url, headers=headers, stream=True, timeout=10, allow_redirects=True)

            # Check HTTP status - accept 200 (OK) and 206 (Partial Content for Range requests)
            # Some servers return 200 even with Range header, which is fine
            if response.status_code == 404:
                if verbose:
                    print(f"  ✗ 404 Not Found: {url[:60]}...", file=output)
                continue
            elif response.status_code not in [200, 206]:
                if verbose:
                    print(f"  ✗ Status {response.status_code}: {url[:60]}...", file=output)
                continue

            # Read first chunk of content
            content_start = b''
            for chunk in response.iter_content(chunk_size=1024):
                content_start = chunk
                break  # Only need first chunk

            # Check if it's actually a PDF by magic bytes
            if content_start.startswith(b'%PDF-'):
                # Additional check: filter out catalogs and manuals by URL patterns
                url_lower = url.lower()
                if any(word in url_lower for word in ['catalog', 'catalogue', 'manual', 'guide', 'brochure', 'series-']):
                    if verbose:
                        print(f"  ✗ Catalog/Manual (URL pattern): {url[:60]}...", file=output)
                    continue

                # Use LLM to validate URL matches query specifications
                if query_specs:
                    if not validate_url_specs_llm(url, query_specs):
                        if verbose:
                            print(f"  ✗ Spec mismatch: {url[:60]}...", file=output)
                        continue

                # Rank URL by supplier quality
                supplier_score = rank_url_by_supplier_llm(url, supplier_info)

                # Skip gray market sites
                if supplier_score == 999:
                    if verbose:
                        print(f"  ✗ Gray market/low quality: {url[:60]}...", file=output)
                    continue

                validated_with_scores.append((url, supplier_score))

                supplier_tier = {1: "Tier 1 (OEM)", 2: "Tier 2 (Auth Dist)", 3: "Tier 3 (Technical)", 4: "Unknown"}
                if verbose:
                    print(f"  ✓ Valid PDF [{supplier_tier.get(supplier_score, 'Unknown')}]: {url[:60]}...", file=output)
            # Check if it's an HTML error page
            elif content_start.startswith(b'<!DOCTYPE') or content_start.startswith(b'<html') or b'<HTML' in content_start[:100]:
                if verbose:
                    print(f"  ✗ HTML error page: {url[:60]}...", file=output)
            # Check if it's XML/SVG (sometimes returned instead of PDF)
            elif content_start.startswith(b'<?xml') or content_start.startswith(b'<svg'):
                if verbose:
                    print(f"  ✗ Not a PDF (XML/SVG): {url[:60]}...", file=output)
            # Check if content is too small to be a real PDF
            elif len(content_start) < 100:
                if verbose:
                    print(f"  ✗ File too small: {url[:60]}...", file=output)
            else:
                if verbose:
                    # Show first few bytes for debugging
                    preview = content_start[:50].decode('utf-8', errors='ignore')[:30]
                    print(f"  ✗ Unknown format: {url[:60]}... (starts with: {preview})", file=output)

        except requests.exceptions.Timeout:
            if verbose:
                print(f"  ✗ Timeout: {url[:60]}...", file=output)
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"  ✗ Request error: {url[:60]}... ({type(e).__name__})", file=output)
        except Exception as e:
            if verbose:
                print(f"  ✗ Error: {url[:60]}... ({type(e).__name__})", file=output)

    # Sort by supplier score (1=best, 4=worst) and return top results
    if verbose and interactive:
        print("  [5d] Sorting by supplier quality (Tier 1 first)...", file=output)

    validated_with_scores.sort(key=lambda x: x[1])  # Sort by score (ascending)
    validated = [url for url, score in validated_with_scores[:max_results]]

    if verbose and validated_with_scores:
        tier_counts = {}
        for _, score in validated_with_scores[:max_results]:
            tier = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3", 4: "Unknown"}[score]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if interactive:
            print(f"       → Supplier breakdown: {', '.join([f'{t}: {c}' for t, c in tier_counts.items()])}", file=output)
        else:
            print(f"Supplier breakdown: {', '.join([f'{t}: {c}' for t, c in tier_counts.items()])}", file=output)

    return validated


def extract_duckduckgo_url(redirect_url):
    """Extract actual URL from DuckDuckGo redirect."""
    try:
        if 'uddg=' in redirect_url:
            parsed = urlparse(redirect_url if redirect_url.startswith('http') else 'https:' + redirect_url)
            params = parse_qs(parsed.query)
            if 'uddg' in params:
                return unquote(params['uddg'][0])
    except:
        pass
    return redirect_url


def search_duckduckgo(query, num_results=10):
    """Search DuckDuckGo for PDF results using the optimized query."""
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    pdf_links = []

    try:
        # Use POST instead of GET (DuckDuckGo prefers POST for HTML interface)
        response = requests.post(
            'https://html.duckduckgo.com/html/',
            data={'q': query, 'b': '', 'kl': 'us-en'},
            headers=headers,
            timeout=15
        )

        # Check if we got a valid response
        if response.status_code == 202:
            # 202 means DuckDuckGo is processing - might be rate limiting
            # Fall back to GET method
            response = requests.get(search_url, headers=headers, timeout=15)

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try both possible result link classes
        result_links = soup.find_all('a', class_='result__url')
        if not result_links:
            result_links = soup.find_all('a', class_='result__a')

        for result in result_links:
            href = result.get('href', '')
            if '.pdf' in href.lower():
                actual_url = extract_duckduckgo_url(href)
                pdf_links.append(actual_url)
                if len(pdf_links) >= num_results:
                    break

    except Exception as e:
        if '--verbose' in sys.argv or '-v' in sys.argv:
            print(f"DuckDuckGo search error: {e}", file=sys.stderr)

    return pdf_links


def interactive_mode():
    """Run in interactive mode for multiple searches."""
    print("=" * 80)
    print("Industrial Component PDF Finder - Interactive Mode")
    print("=" * 80)
    print("Type your component search (or 'quit' to exit)")
    print("Examples: 'LM555', '100 sccm mass flow controller', 'SKF 6205 bearing'")
    print("=" * 80)
    print()

    while True:
        try:
            # Get user input
            query = input("Search> ").strip()

            # Check for exit commands
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break

            # Skip empty queries
            if not query:
                continue

            # Perform search
            print(f"\nSearching for: {query}")
            print("=" * 80)
            print()

            print("┌─────────────────────────────────────────────────────────────┐")
            print("│ STEP 1: Generating optimized search query (LLM)...         │")
            print("└─────────────────────────────────────────────────────────────┘")

            # Get search query from Claude first
            system_prompt = """You are the "Industrial Search Optimizer."
Your goal is to generate a SINGLE Google/DuckDuckGo search query that finds a Technical PDF from a Reputable Source.

### INSTRUCTIONS:
1. **Analyze the Input:** Identify the Core Part Number and the Industry Category.
2. **Select Technical Fingerprints:** Choose 2-3 keywords that ONLY appear in technical documentation for that category (see "Fingerprint Logic" below).
3. **Apply Reputation Filters:**
   * MUST use `filetype:pdf`.
   * MUST exclude "Gray Market" terms: `-rfq -quote -"request a quote" -alibaba -ebay`.
   * MUST exclude "Generic Junk": `-brochure -catalog -manual` (unless user asks for a manual).
4. **Construct the Query:** Combine these elements into a single string.

### FINGERPRINT LOGIC (Select based on Category):
* **Raw Materials:** "ASTM" OR "chemical composition" OR "mechanical properties"
* **Mechanical/Ind:** "dimensional drawing" OR "tolerance" OR "load rating"
* **Electronics:** "absolute maximum ratings" OR "pin configuration"
* **Machinery:** "installation guide" OR "wiring diagram" OR "troubleshooting"
* **Process Equip:** "flow curve" OR "pressure drop" OR "cut sheet"
* **Facilities/MRO:** "parts list" OR "exploded view" OR "service manual"

### OUTPUT FORMAT:
Return ONLY the raw search query string. No JSON, no explanations."""

            prompt = f"""Input: "{query}"

Generate an optimized search query following the Industrial Search Optimizer instructions.
Keep the query simple and effective for DuckDuckGo. Focus on:
1. Core part number/component name
2. "datasheet" or "specification" keyword
3. filetype:pdf
4. One key technical fingerprint phrase

Examples:
Input: "Datasheet for LM555 timer"
Output: LM555 datasheet filetype:pdf

Input: "316 Stainless Steel Round Bar specs"
Output: 316 stainless steel datasheet filetype:pdf

Input: "100 sccm mass flow controller"
Output: 100 sccm mass flow controller datasheet filetype:pdf

Input: "SKF 6205 bearing"
Output: SKF 6205 bearing datasheet filetype:pdf

Now generate the search query for: {query}

Return ONLY the search query string, nothing else. Keep it simple and focused."""

            search_query = call_claude(prompt, system_prompt)
            if search_query:
                search_query = search_query.strip().strip('"\'')
                print(f"  → Generated query: {search_query}")
                print()


            # Run with verbose=True and interactive=True to show all backend processing to stdout
            results = find_pdfs_with_llm(query, max_results=5, verbose=True, interactive=True)

            if results:
                print()
                print("=" * 80)
                print(f"FINAL RESULTS: Found {len(results)} PDF(s)")
                print("=" * 80)
                print()
                for i, url in enumerate(results, 1):
                    # Encode URL for browser compatibility
                    parsed = urlparse(url)
                    encoded_path = quote(parsed.path, safe='/:@!$&\'()*+,;=')
                    encoded_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
                    if parsed.query:
                        encoded_url += f"?{parsed.query}"
                    if parsed.fragment:
                        encoded_url += f"#{parsed.fragment}"

                    print(f"{i}. {encoded_url}")
            else:
                print("No PDF datasheets found")

            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='LLM-powered PDF datasheet finder for industrial components',
        epilog='Example: %(prog)s "100 sccm mass flow controller" OR run without arguments for interactive mode'
    )

    parser.add_argument(
        'query',
        nargs='?',  # Make query optional
        help='Component description or part number (omit for interactive mode)'
    )

    parser.add_argument(
        '-n', '--max-results',
        type=int,
        default=5,
        help='Maximum number of results (default: 5)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    args = parser.parse_args()

    # If no query provided or -i flag, run interactive mode
    if args.interactive or not args.query:
        interactive_mode()
        return

    # Single query mode
    if args.verbose:
        print(f"Searching for: {args.query}", file=sys.stderr)

    results = find_pdfs_with_llm(args.query, args.max_results, args.verbose)

    if results:
        for url in results:
            # Encode URL for browser compatibility (handles spaces and special chars)
            # Split URL into parts and encode only the path
            parsed = urlparse(url)
            # Quote the path, but safe characters that should remain unencoded
            encoded_path = quote(parsed.path, safe='/:@!$&\'()*+,;=')
            # Reconstruct URL with encoded path
            encoded_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
            if parsed.query:
                encoded_url += f"?{parsed.query}"
            if parsed.fragment:
                encoded_url += f"#{parsed.fragment}"

            print(encoded_url)
    else:
        if args.verbose:
            print("No PDF datasheets found", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()