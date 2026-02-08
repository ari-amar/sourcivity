# Search Process: End-to-End Flow

## Overview

When a user searches for an industrial part, Sourcivity executes a multi-stage pipeline:

1. The frontend sends the query to the backend via POST request
2. The backend optionally generates an AI-optimized search query
3. Exa neural search finds up to 20 relevant URLs
4. PDFs are downloaded in parallel and converted to markdown
5. AI extracts specs from each PDF (throttled to 5 concurrent)
6. Results are filtered programmatically and by AI
7. AI normalizes spec key names across all PDFs
8. Code verifies AI output, selects top 5 specs by coverage
9. Final results (top 5 products) are built with contact URLs
10. The frontend converts the response into a markdown comparison table

---

## 1. Frontend (`lib/searchApi.ts`)

**Entry point:** `fetchColumnDeterminationAndSearch(params: TextSearchParams)`

The frontend fires a POST request to `/api/search/parts` with:

```json
{
  "query": "user's search text",
  "generate_ai_search_prompt": false,
  "search_engine_client_name": "exa",
  "ai_client_name": "anthropic"
}
```

React Query configuration:

| Setting | Value |
|---------|-------|
| Timeout | 45 seconds |
| Retry attempts | 3 |
| Stale time (results) | 5 minutes |
| Cache time | 10 minutes |

When results return, `convertBackendResponseToMarkdown()` transforms the JSON into a markdown table. Each row is formatted as:

```
[Manufacturer ProductName](datasheet_url)<!--contact:contactUrl--><!--error:extractionError--><br/>OEM
```

The contact URL and extraction error are embedded as HTML comments for the UI to parse.

---

## 2. Backend Endpoint (`app/api/app.py` + `app/api/search/parts.py`)

### Lazy client initialization

Clients are initialized on first request (serverless cold-start optimization):

- **AI client:** `AnthropicAiClient` with model `claude-sonnet-4-20250514`
- **Search client:** `ExaClient` with `search_type="neural"`

Both are cached after first init and reused across requests.

### Endpoint: `POST /api/search/parts`

**Request model:** `PartSearchRequest`
```python
class PartSearchRequest(BaseModel):
    query: str
    generate_ai_search_prompt: Optional[bool] = False
    search_engine_client_name: Optional[str] = "exa"
    ai_client_name: Optional[str] = "anthropic"
    debug: Optional[bool] = False
```

**Response model:** `PartSearchResponse`
```python
class PartSearchResponse(BaseModel):
    query: str
    spec_column_names: List[str]   # Top 5 standardized spec names
    parts: List[PartResponse]      # Products with extracted specs
    timing: Optional[dict]         # Timing breakdown
```

Each `PartResponse` contains:
```python
class PartResponse(BaseModel):
    url: str
    contact_url: Optional[str]
    specs: Optional[dict]          # {spec_key: value}
    manufacturer: Optional[str]
    product_name: Optional[str]
    error: Optional[str]           # Extraction error message
```

The endpoint delegates to `search_parts()` which orchestrates the full pipeline.

---

## 3. Search Query Generation (Optional)

**Condition:** Only runs if `generate_ai_search_prompt=True` (default is `False`).

When enabled, an AI call generates an optimized search query. When disabled (the default), the query is constructed as:

```
"{user_query} datasheet filetype:pdf"
```

**AI call details (when enabled):**

| Field | Value |
|-------|-------|
| Prompt | `SEARCH_QUERY_GENERATION_PROMPT` |
| System prompt | "You are an expert at crafting search queries to find technical datasheets." |
| Max tokens | 150 |
| JSON enforced | Yes |

Output schema: `{ "search_query": "optimized query string" }`

---

## 4. Exa Neural Search (`app/api/services/search_engine_clients/exa_client.py`)

The Exa client runs a neural search (not keyword -- keyword doesn't return relevance scores).

**Configuration:**

| Parameter | Value |
|-----------|-------|
| `max_results` | 20 |
| `type` | `"neural"` |
| `contents` | `False` (PDFs downloaded directly, not via Exa text extraction) |

**Design decisions:**
- No URL filtering (e.g. `.pdf` extension check) is applied -- testing showed this reduces discovery by ~80%. PDF validation happens during download instead.
- The `category="pdf"` parameter has no measurable effect on result quality.
- Results are sorted by neural relevance score (descending).

Returns a list of `SearchEngineResult` objects with `title`, `url`, and `score`.

---

## 5. PDF Pipeline -- Step 1: Download & Markdown Conversion (`app/api/utils/pdf_scraper.py`)

**Function:** `scrape_pdf()` per URL, called via `scrape_multiple()`.

All 20 URLs are downloaded in parallel (full `asyncio.gather`, no concurrency limit).

For each URL:

1. **Download** the content via HTTP
2. **Validate** -- check for `%PDF` magic bytes in the header
3. **HTML fallback** -- if an HTML page is returned instead of a PDF, scan for PDF links and follow up to 3 of them
4. **Size check** -- reject files smaller than 1,024 bytes
5. **Page count check** -- reject PDFs with more than 10 pages
6. **Convert** to markdown using the `MarkItDown` library
7. **Empty check** -- reject if markdown conversion produces no text

Output: list of `{url, markdown_text, error}` dicts.

---

## 6. AI Spec Extraction -- Step 2 (`app/api/utils/pdf_scraper.py`)

For each successfully converted markdown, AI extracts structured specs.

**Concurrency:** `asyncio.Semaphore(5)` -- max 5 concurrent AI calls to avoid rate limits.

**AI call details:**

| Field | Value |
|-------|-------|
| Prompt | `SINGLE_PDF_SPEC_EXTRACTION_PROMPT` + markdown content |
| System prompt | "You are an expert at extracting technical specifications from product datasheets." |
| Max tokens | 8,000 |
| JSON enforced | Yes |

Output schema:
```json
{
  "manufacturer": "Company Name",
  "product_name": "Model/Product Name",
  "specifications": {
    "spec_name": "value with units"
  }
}
```

After extraction, results with fewer than 5 specs are discarded. Remaining results are sorted by neural search score.

---

## 7. Filtering -- Step 2b (`app/api/utils/pdf_scraper.py`)

### Layer A: Programmatic filters

Remove results where:
- Manufacturer is "Unknown" or empty
- Product name contains file extensions (`.pdf`, `.html`, etc.)
- Product name is purely numeric
- Fewer than 5 specs were extracted

### Layer B: AI product-type filter

**Condition:** Only runs if a `product_type` is provided AND at least 2 results remain.

| Field | Value |
|-------|-------|
| Prompt | `FILTER_COMPARABLE_PRODUCTS_PROMPT` + product list |
| System prompt | "You are an expert at identifying and categorizing industrial products." |
| Max tokens | 500 |
| JSON enforced | Yes |

Output: `{ "matching_indices": [0, 2, 4] }` -- indices of products that match the queried product type.

---

## 8. Spec Normalization -- Step 3a (`app/api/utils/pdf_scraper.py`)

**Condition:** Requires at least 3 PDFs after filtering.

Groups synonymous spec keys across all PDFs (e.g., "Operating Temp", "Temperature Range", "Working Temp" are the same spec).

| Field | Value |
|-------|-------|
| Prompt | `NORMALIZE_SPEC_KEYS_PROMPT` + all PDF key names (max 50 keys per PDF) |
| System prompt | "You are an expert at analyzing and comparing product datasheets. You normalize specification names across different datasheets." |
| Max tokens | 8,000 |
| JSON enforced | Yes |

Output:
```json
{
  "standardized_key": {
    "display_name": "Human Readable Name (unit)",
    "pdf_matches": {
      "1": "Original Key In PDF 1",
      "3": "Original Key In PDF 3"
    }
  }
}
```

---

## 9. Verification & Top 5 Selection -- Step 3b (`app/api/utils/pdf_scraper.py`)

This is a code-only step (no AI). It guards against hallucinated key mappings:

1. For each standardized key, verify the mapped original key actually exists in that PDF's extracted specs
2. Try exact match first, then case-insensitive fallback
3. Track hallucination stats (exact matches vs. case-insensitive vs. missing)
4. Drop spec groups with zero verified matches
5. Sort remaining specs by **coverage** (number of PDFs that have the spec)
6. Select the **top 5** specs

---

## 10. Build Final Results -- Step 3c (`app/api/utils/pdf_scraper.py`)

For each PDF result:
1. Pull `manufacturer` and `product_name` from extraction output
2. For each of the 5 selected specs, look up the original key via `pdf_matches` and retrieve the original value
3. If a spec isn't found for a given PDF, set to `"N/A"`

Output: list of result dicts with `url`, `specs`, `manufacturer`, `product_name`, `contact_url`.

---

## 11. Contact URL Extraction (`app/api/utils/pdf_scraper.py`)

Runs in parallel for all result domains.

**Function:** `find_contact_url(supplier_domain, timeout=10)`

1. Fetch the supplier's homepage
2. Scan HTML for links containing keywords: `contact`, `inquiry`, `quote`, `request`, `get-quote`, `reach-us`
3. If no links found, test common paths: `/contact`, `/contact-us`, `/inquiry`, `/request-quote`, `/get-quote`
4. **Fallback:** `derive_contact_url()` extracts the base domain and appends `/contact`

| Parameter | Value |
|-----------|-------|
| Homepage fetch timeout | 10 seconds |
| Contact crawl timeout | 8 seconds |

---

## 12. Response to Frontend

The backend returns a `PartSearchResponse` containing:
- `query` -- the original search query
- `spec_column_names` -- the top 5 standardized spec display names
- `parts` -- up to 5 `PartResponse` objects (top 5 by neural score after all filtering)
- `timing` -- breakdown of time spent in each stage

The frontend's `convertBackendResponseToMarkdown()` transforms this into a markdown table where columns are the spec names and rows are products.

---

## Flow Diagram

```
User enters search query
         |
         v
┌─────────────────────────────────────────────────┐
│  FRONTEND  (lib/searchApi.ts)                   │
│  POST /api/search/parts                         │
│  {query, ai_client_name, search_engine_client}  │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  BACKEND  (app/api/search/parts.py)             │
│                                                  │
│  [Optional] AI query generation ──── AI Call 1  │
│       |                                          │
│       v                                          │
│  Exa neural search (20 results)                 │
│       |                                          │
│       v                                          │
│  PDFScraper.scrape_multiple()                   │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 1: Parallel PDF Download & Conversion     │
│  • Download up to 20 PDFs (asyncio.gather)      │
│  • Validate %PDF header, size >= 1KB            │
│  • HTML fallback: follow up to 3 PDF links      │
│  • Page limit: 10 pages max                     │
│  • Convert via MarkItDown                       │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 2: AI Spec Extraction ──────── AI Call 2  │
│  • Per-PDF, Semaphore(5) concurrency            │
│  • 8,000 max tokens per call                    │
│  • Extract: manufacturer, product_name, specs   │
│  • Filter: require >= 5 specs                   │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 2b: Filtering                             │
│  A) Programmatic: bad names, low specs          │
│  B) AI product-type filter ──────── AI Call 3   │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 3a: AI Spec Normalization ──── AI Call 4  │
│  • Group synonymous keys across PDFs            │
│  • Max 50 keys per PDF                          │
│  • 8,000 max tokens                             │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 3b: Verification & Top 5 Selection        │
│  • Verify AI mappings against real data          │
│  • Catch hallucinated keys                      │
│  • Rank by coverage, pick top 5                 │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 3c: Build Final Results                   │
│  • Map standardized keys to original values     │
│  • Fill N/A for missing specs                   │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  STEP 4: Contact URL Extraction (parallel)      │
│  • Crawl supplier homepages                     │
│  • Search for contact/quote links               │
│  • Fallback: domain.com/contact                 │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  RESPONSE: Top 5 PartResponse objects           │
│  + spec_column_names + timing                   │
└────────────────────┬────────────────────────────┘
                     |
                     v
┌─────────────────────────────────────────────────┐
│  FRONTEND: convertBackendResponseToMarkdown()   │
│  • JSON -> markdown comparison table            │
│  • Contact URLs as HTML comments                │
│  • Render in UI                                 │
└─────────────────────────────────────────────────┘
```

---

## AI Calls Summary

| # | Call | Prompt Constant | System Prompt (abbreviated) | Max Tokens | When | Concurrency |
|---|------|-----------------|-----------------------------|------------|------|-------------|
| 1 | Search query generation | `SEARCH_QUERY_GENERATION_PROMPT` | "...expert at crafting search queries..." | 150 | If `generate_ai_search_prompt=True` | 1 |
| 2 | Spec extraction | `SINGLE_PDF_SPEC_EXTRACTION_PROMPT` | "...expert at extracting technical specifications..." | 8,000 | Per downloaded PDF | Semaphore(5) |
| 3 | Product-type filter | `FILTER_COMPARABLE_PRODUCTS_PROMPT` | "...expert at identifying and categorizing industrial products." | 500 | If product_type set and >= 2 results | 1 |
| 4 | Spec key normalization | `NORMALIZE_SPEC_KEYS_PROMPT` | "...expert at analyzing and comparing product datasheets..." | 8,000 | If >= 3 PDFs pass filtering | 1 |

All AI calls use `claude-sonnet-4-20250514` with `enforce_json=True`.

---

## Key Constants & Thresholds

| Parameter | Value | File | Purpose |
|-----------|-------|------|---------|
| Exa max results | 20 | `parts.py` | Maximize PDF discovery |
| PDF min file size | 1,024 bytes | `pdf_scraper.py` | Skip corrupted/empty files |
| PDF max pages | 10 | `pdf_scraper.py` | Skip overly long documents |
| Max PDF links to follow | 3 | `pdf_scraper.py` | When HTML page returned instead of PDF |
| AI concurrency (extraction) | 5 | `pdf_scraper.py` | Semaphore to avoid rate limits |
| Min specs per PDF | 5 | `pdf_scraper.py` | Filter low-quality extractions |
| Min PDFs for normalization | 3 | `pdf_scraper.py` | Skip normalization if too few results |
| Max keys per PDF (normalization) | 50 | `pdf_scraper.py` | Keep normalization prompt manageable |
| Top specs selected | 5 | `pdf_scraper.py` | Max columns in output table |
| Top results returned | 5 | `pdf_scraper.py` | Max products in response |
| Contact homepage timeout | 10 seconds | `pdf_scraper.py` | Initial homepage fetch |
| Contact crawl timeout | 8 seconds | `pdf_scraper.py` | Per-domain contact discovery |
| Frontend request timeout | 45 seconds | `searchApi.ts` | Axios timeout |
| Frontend retry attempts | 3 | `searchApi.ts` | React Query retries |
| Claude model | `claude-sonnet-4-20250514` | `app.py` | Supports native PDF input |
