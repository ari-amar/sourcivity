# Supplier Service Search Implementation

## Overview
This implementation adds a parallel search pipeline for discovering and comparing supplier services alongside the existing product datasheet search functionality.

## Architecture: Dual Search Mode System

### Search Modes
1. **Product Datasheets** - Original functionality for finding and comparing technical product specifications
2. **Supplier Services** - NEW functionality for discovering supplier capabilities, certifications, and service offerings

## Implementation Details

### Backend (Python)

#### 1. Service Finder (`python-backend/service_finder.py`)
- **Purpose**: Uses Exa.ai to search for supplier service/capability pages
- **Key Features**:
  - Targets HTML pages (not PDFs) about services and capabilities
  - Filters results for service-related keywords (services, capabilities, manufacturing, etc.)
  - Excludes PDF files to focus on web pages
  - Scores results based on relevance to service pages
- **Usage**:
  ```python
  finder = ServiceFinder()
  results = finder.search_services(
      query="CNC machining services",
      supplier_name="ProtoLabs",  # optional
      num_results=10
  )
  ```

#### 2. Service Scraper (`python-backend/service_scraper.py`)
- **Purpose**: Extracts service information from supplier web pages using Claude
- **Key Features**:
  - Uses BeautifulSoup for HTML parsing
  - Removes navigation, scripts, styles for clean text extraction
  - Claude extracts structured service data:
    - Company name
    - Services offered (array)
    - Capabilities (array)
    - Certifications (array)
    - Equipment (array)
    - Industries served (array)
    - Location
    - Lead times
    - MOQ
    - Company info (year established, employees)
  - Standardized extraction across multiple pages for comparison

#### 3. Service Comparator (`python-backend/service_comparator.py`)
- **Purpose**: Creates comparison tables for supplier services
- **Key Features**:
  - Structures data for easy comparison
  - Generates both text and HTML output formats
  - Intelligent field ordering (company, location, services, capabilities, etc.)
  - Handles arrays and null values gracefully

#### 4. Web Server Updates (`python-backend/web_server.py`)
- Added two new endpoints:
  - **`POST /search-services`**: Search for supplier service pages
  - **`POST /compare-services`**: Scrape and compare multiple service pages

### Frontend (Next.js)

#### 1. API Route Updates (`app/api/search/parts/route.ts`)
- Added `handleServiceSearch()` function:
  - Calls `/search-services` to find service pages
  - Calls `/compare-services` to extract and compare up to 5 suppliers
  - Uses Claude to select top 5 most important service fields
  - Generates markdown comparison table
- Added `convertServiceComparisonToMarkdown()` function:
  - Formats service data as markdown table
  - First column: Supplier name (linked to page)
  - Additional columns: Top 5 service fields selected by Claude
  - Handles arrays by joining with commas (limit 3 items for readability)
- Added `selectTopServiceFields()` function:
  - Uses Claude to intelligently pick most relevant fields
  - Prioritizes: services offered, capabilities, certifications, location, lead time
  - Fallback to first 5 fields if Claude unavailable

#### 2. Search Page UI (`app/search/page.tsx`)
- Added search mode toggle with radio buttons:
  - "Product Datasheets" (default)
  - "Supplier Services" (new)
- Updated form schema to include `searchMode` field
- Passes `searchMode` to search API
- Clean, user-friendly toggle interface

### Dependencies

#### New Python Package
Added to `python-backend/requirements.txt`:
- `beautifulsoup4>=4.12.0` - HTML parsing for service page scraping

## How It Works

### Service Search Flow
```
User Query: "CNC machining services"
  ↓
[User selects "Supplier Services" mode]
  ↓
Next.js API (/api/search/parts)
  ↓
Python Backend (/search-services)
  ↓
Exa.ai finds top 10 service/capability pages
  ↓
Python Backend (/compare-services)
  ↓
Scrape top 5 pages (BeautifulSoup)
  ↓
Extract service info (Claude with standardized keys)
  ↓
Claude selects top 5 most important fields
  ↓
Markdown comparison table
  ↓
Frontend displays results
```

### Example Output Table

| Supplier | Services Offered | Certifications | Location | Lead Time | Capabilities |
|----------|-----------------|----------------|----------|-----------|--------------|
| [ABC Manufacturing](url) | CNC machining, Sheet metal | ISO 9001, AS9100 | Los Angeles, CA | 2-3 weeks | 5-axis CNC, ±0.001" tolerance |
| [XYZ Services](url) | CNC machining, Injection molding | ISO 9001 | Chicago, IL | 1-2 weeks | Precision grinding, rapid prototyping |

## Testing

### Backend Testing
```bash
# Install new dependency
cd python-backend
pip install -r requirements.txt

# Test service search
python service_finder.py search "CNC machining services"

# Start server
python web_server.py
```

### Frontend Testing
1. Start Python backend: `cd python-backend && python web_server.py`
2. Start Next.js: `npm run dev`
3. Navigate to http://localhost:3000/search
4. Select "Supplier Services" radio button
5. Search for: "CNC machining services" or "injection molding capabilities"
6. View comparison table with supplier capabilities

### Test Queries
**Good Service Search Queries:**
- "CNC machining services"
- "injection molding capabilities"
- "sheet metal fabrication"
- "precision grinding services"
- "rapid prototyping services"
- "3D printing services aerospace"

## Key Design Decisions

### Why Approach 1 (Dual Search Mode)?
✅ **Clean separation of concerns** - Datasheet and service search remain independent
✅ **Code reuse** - 80% of infrastructure reused (Exa search, Claude extraction, comparison logic)
✅ **Easy to maintain** - Clear boundaries between product specs and supplier services
✅ **User-friendly** - Simple toggle, clear intent
✅ **Extensible** - Can add more search modes in the future

### Why HTML Scraping vs PDF?
- Service information lives on web pages, not PDFs
- Faster extraction (no PDF parsing overhead)
- BeautifulSoup efficiently handles HTML cleanup
- More dynamic content (services change more frequently than datasheets)

### Why Claude for Field Selection?
- Different queries return different service fields
- Claude intelligently prioritizes what matters for each search
- Ensures most relevant information appears in comparison table
- Adapts to user's search intent

## Future Enhancements

### Potential Improvements
1. **Geo-filtering**: Filter suppliers by location/region
2. **Service categories**: Pre-defined service type filters (machining, molding, finishing, etc.)
3. **Certification filters**: Search only ISO 9001, AS9100, ITAR certified suppliers
4. **Multi-page crawling**: Scrape multiple pages per supplier (services, about, certifications)
5. **Supplier profiles**: Save and track preferred suppliers
6. **RFQ integration**: Generate RFQs directly from service search results
7. **Capability matching**: Score suppliers based on query requirements
8. **Review/rating integration**: Pull supplier ratings from third-party sources

### Production Considerations
1. **Caching**: Cache service page extractions (pages don't change often)
2. **Rate limiting**: Respect robots.txt and add delays between scrapes
3. **Error handling**: Handle timeouts, blocked pages, malformed HTML
4. **User feedback**: Allow users to flag incorrect extractions
5. **Analytics**: Track which service fields users find most valuable

## Files Modified/Created

### Created
- `python-backend/service_finder.py`
- `python-backend/service_scraper.py`
- `python-backend/service_comparator.py`
- `SERVICE_SEARCH_IMPLEMENTATION.md`

### Modified
- `python-backend/web_server.py`
- `python-backend/requirements.txt`
- `app/api/search/parts/route.ts`
- `app/search/page.tsx`

## Environment Variables

No new environment variables required. Uses existing:
- `EXA_API_KEY` - Exa.ai API key (already required)
- `ANTHROPIC_API_KEY` - Claude API key (already required)

## Notes

- Service search uses same Exa API credits as datasheet search
- Claude calls increase for service extraction (one call per 5 suppliers)
- Field selection uses separate Claude call for intelligent prioritization
- BeautifulSoup dependency added - ensure it's installed before testing
- Search mode defaults to "Product Datasheets" for backward compatibility
