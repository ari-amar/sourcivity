"""Supplier search — parallel Brave queries + LLM extraction + background scraper enrichment."""
import concurrent.futures
import json
import re
import threading
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from services import llm, scraper, brave

# In-memory store for background enrichment results
# { search_id: { "suppliers": [...], "status": "enriching"|"done", "blocked": [], "ts": time } }
_searches = {}
_MAX_AGE = 300  # clean up entries older than 5 minutes
_US_STATE_ABBRS = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY',
}


_INDIAN_CITY_TOKENS = {'mumbai', 'delhi', 'bangalore', 'chennai', 'hyderabad', 'pune', 'kolkata', 'india'}

# ISO 2-letter country codes that collide with US state abbreviations.
# Used in global mode to remap to full country names before the frontend sees them,
# so the frontend US_STATES check doesn't misclassify them as US states.
_ISO_COLLISION_TO_COUNTRY = {
    'CA': 'Canada',
    'IN': 'India',
    'DE': 'Germany',
    'IL': 'Israel',
    'CO': 'Colombia',
    'AR': 'Argentina',
    'AL': 'Albania',
    'GA': 'Gabon',
    'ID': 'Indonesia',
    'ME': 'Montenegro',
}

_UNKNOWN_LOCATION_VALUES = {'', 'US', 'USA', 'UNITED STATES', 'N/A', 'NA', 'UNKNOWN'}


def _is_us_supplier(supplier):
    """Return True only when the supplier location is explicitly a US state."""
    if supplier.get('_non_us'):
        return False
    state = (supplier.get('state', '') or '').strip()
    if state.upper() in _UNKNOWN_LOCATION_VALUES:
        return False

    # Strip "US-" prefix (e.g. US-PA → PA)
    if state.upper().startswith('US-'):
        state = state[3:]

    # "IN" is ambiguous — it's Indiana but also a common abbreviation for India.
    # Use secondary signals to disambiguate before accepting it as a US state.
    if state.upper() == 'IN':
        website = (supplier.get('website', '') or '').lower()
        name_products = (supplier.get('name', '') + ' ' + supplier.get('products', '')).lower()
        if '.co.in' in website or website.rstrip('/').endswith('.in'):
            return False
        if any(tok in name_products for tok in _INDIAN_CITY_TOKENS):
            return False

    return state.upper() in _US_STATE_ABBRS


def _is_unknown_location(supplier):
    state = (supplier.get('state', '') or '').strip().upper()
    return state in _UNKNOWN_LOCATION_VALUES


def _is_known_international_supplier(supplier):
    """Return True when location is known and is not a US state."""
    state = (supplier.get('state', '') or '').strip()
    if not state or state.upper() in _UNKNOWN_LOCATION_VALUES:
        return False
    return not _is_us_supplier(supplier)


_GEO_KEYWORDS = {
    # Countries
    'austria', 'germany', 'france', 'italy', 'spain', 'netherlands', 'belgium',
    'switzerland', 'czech republic', 'czechia', 'slovakia', 'hungary', 'poland',
    'sweden', 'denmark', 'finland', 'norway', 'portugal', 'uk', 'united kingdom',
    'china', 'japan', 'korea', 'taiwan', 'india', 'singapore', 'australia',
    'canada', 'brazil', 'mexico', 'turkey', 'ukraine',
    # Regions
    'europe', 'asia', 'central europe', 'eastern europe', 'western europe',
    'scandinavia', 'balkans', 'dach',
    # Cities commonly used as proxies
    'vienna', 'munich', 'zurich', 'prague', 'budapest', 'warsaw',
}

def _extract_geo_hint(query):
    """Return the first geographic keyword found in the query, or None."""
    q = query.lower()
    # Multi-word first
    for kw in sorted(_GEO_KEYWORDS, key=len, reverse=True):
        if kw in q:
            return kw
    return None


# Maps a specific-country geo keyword → accepted state values (code + full name).
# Only populated for single countries — broad regions (europe, asia, dach) are omitted
# so we don't over-filter when the user just wants international results generally.
_GEO_TO_CODES = {
    'austria':        ('AT', 'Austria'),
    'vienna':         ('AT', 'Austria'),
    'germany':        ('DE', 'Germany'),
    'deutschland':    ('DE', 'Germany'),
    'munich':         ('DE', 'Germany'),
    'france':         ('FR', 'France'),
    'paris':          ('FR', 'France'),
    'italy':          ('IT', 'Italy'),
    'spain':          ('ES', 'Spain'),
    'netherlands':    ('NL', 'Netherlands'),
    'holland':        ('NL', 'Netherlands'),
    'switzerland':    ('CH', 'Switzerland'),
    'zurich':         ('CH', 'Switzerland'),
    'belgium':        ('BE', 'Belgium'),
    'portugal':       ('PT', 'Portugal'),
    'sweden':         ('SE', 'Sweden'),
    'denmark':        ('DK', 'Denmark'),
    'finland':        ('FI', 'Finland'),
    'norway':         ('NO', 'Norway'),
    'poland':         ('PL', 'Poland'),
    'warsaw':         ('PL', 'Poland'),
    'czech republic': ('CZ', 'Czechia'),
    'czechia':        ('CZ', 'Czechia'),
    'prague':         ('CZ', 'Czechia'),
    'hungary':        ('HU', 'Hungary'),
    'budapest':       ('HU', 'Hungary'),
    'slovakia':       ('SK', 'Slovakia'),
    'ukraine':        ('UA', 'Ukraine'),
    'turkey':         ('TR', 'Turkey'),
    'uk':             ('UK', 'United Kingdom'),
    'united kingdom': ('UK', 'United Kingdom'),
    'china':          ('CN', 'China'),
    'japan':          ('JP', 'Japan'),
    'korea':          ('KR', 'Korea'),
    'taiwan':         ('TW', 'Taiwan'),
    'india':          ('IN', 'India'),
    'singapore':      ('SG', 'Singapore'),
    'australia':      ('AU', 'Australia'),
    'canada':         ('CA', 'Canada'),
    'brazil':         ('BR', 'Brazil'),
    'mexico':         ('MX', 'Mexico'),
}


# Country-specific TLDs — reliable signals for a company's actual location.
# Multi-part TLDs must come before single-part (e.g. .co.in before .in).
_TLD_COUNTRY_MAP = [
    ('.co.in', 'India'), ('.in', 'India'),
    ('.co.uk', 'UK'), ('.uk', 'UK'),
    ('.ca', 'Canada'),
    ('.com.au', 'Australia'), ('.au', 'Australia'),
    ('.com.br', 'Brazil'), ('.br', 'Brazil'),
    ('.com.mx', 'Mexico'), ('.mx', 'Mexico'),
    ('.de', 'Germany'), ('.at', 'Austria'), ('.ch', 'Switzerland'),
    ('.fr', 'France'), ('.it', 'Italy'), ('.es', 'Spain'),
    ('.nl', 'Netherlands'), ('.be', 'Belgium'), ('.pt', 'Portugal'),
    ('.se', 'Sweden'), ('.dk', 'Denmark'), ('.fi', 'Finland'), ('.no', 'Norway'),
    ('.pl', 'Poland'), ('.cz', 'Czechia'), ('.hu', 'Hungary'),
    ('.ro', 'Romania'), ('.gr', 'Greece'), ('.ua', 'Ukraine'),
    ('.tr', 'Turkey'), ('.cn', 'China'), ('.jp', 'Japan'),
    ('.kr', 'Korea'), ('.tw', 'Taiwan'), ('.sg', 'Singapore'),
]


def _country_from_tld(website):
    """Return the country implied by the website's TLD, or None for generic TLDs (.com etc.)."""
    if not website:
        return None
    url = website.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    parsed = urllib.parse.urlparse(url)
    host = (parsed.netloc or parsed.path.split('/')[0]).lower()
    if host.startswith('www.'):
        host = host[4:]
    for tld, country in _TLD_COUNTRY_MAP:
        if host.endswith(tld):
            return country
    return None


def _normalize_supplier_location(supplier, region='north_america'):
    """Apply deterministic country signals before region filtering."""
    state = (supplier.get('state') or '').strip()

    if region == 'global' and state and not state.upper().startswith('US-'):
        country = _ISO_COLLISION_TO_COUNTRY.get(state.upper())
        if country:
            supplier['state'] = country
            state = country

    tld_country = _country_from_tld(supplier.get('website', ''))
    if tld_country and (
        _is_unknown_location(supplier)
        or (region == 'global' and not state.upper().startswith('US-'))
        or (state.upper() == 'CA' and tld_country == 'Canada')
        or (state.upper() == 'IN' and tld_country == 'India')
    ):
        supplier['state'] = tld_country

    return supplier


def _clean_query_for_prompt(query):
    """Keep buyer search terms intact while removing control characters."""
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', query or '').strip()[:200]


def _filter_suppliers_for_region(suppliers, region, query='', allow_pending=False):
    """Drop suppliers that fail deterministic regional checks."""
    filtered = []
    geo_hint = _extract_geo_hint(query or '')
    accepted = _GEO_TO_CODES.get(geo_hint) if region == 'global' and geo_hint else None
    accepted_lower = {v.lower() for v in accepted} if accepted else None

    for s in suppliers:
        _normalize_supplier_location(s, region)
        if region == 'north_america':
            if _is_us_supplier(s):
                filtered.append(s)
            elif allow_pending and _is_unknown_location(s):
                filtered.append(s)
            continue

        if accepted_lower:
            state = (s.get('state') or '').strip().lower()
            if state in accepted_lower or (allow_pending and not state):
                filtered.append(s)
            continue

        if _is_known_international_supplier(s) or (allow_pending and _is_unknown_location(s)):
            filtered.append(s)

    return filtered


def _mark_unknown_locations(suppliers):
    """Use a visible placeholder for suppliers whose location stayed unresolved."""
    for s in suppliers:
        if _is_unknown_location(s):
            s['state'] = 'N/A'
    return suppliers


_LOWERCASE_PRODUCT_WORDS = {'and', 'or', 'the', 'a', 'an', 'of', 'for', 'in', 'on', 'with', 'to', 'by', 'at'}
_PRODUCT_ACRONYMS = {
    'iso', 'asme', 'astm', 'ams', 'ansi', 'api', 'cmmc', 'cnc', 'dfars', 'fda',
    'itar', 'mil', 'nadcap', 'nist', 'ptfe', 'pvc', 'rfq', 'sae', 'ul', 'uhmw',
}


def _format_years_in_business(year, current_year=None):
    current_year = current_year or datetime.now(timezone.utc).year
    age = max(0, current_year - year)
    unit = "yr" if age == 1 else "yrs"
    return f"{age} {unit} (est. {year})"


def _normalize_years_in_business_value(value, current_year=None):
    if not value:
        return value
    current_year = current_year or datetime.now(timezone.utc).year
    match = re.search(r'\b(18[5-9]\d|19\d{2}|20\d{2})\b', str(value))
    if not match:
        return value
    year = int(match.group(1))
    if 1850 <= year <= current_year:
        return _format_years_in_business(year, current_year)
    return value


def _title_case_product(text):
    """Title-case product text without mangling acronyms or hyphenated terms."""
    if not text:
        return text

    def format_piece(piece, is_first_word):
        lower = piece.lower()
        if not is_first_word and lower in _LOWERCASE_PRODUCT_WORDS:
            return lower
        if lower in _PRODUCT_ACRONYMS:
            return lower.upper()
        if any(ch.isdigit() for ch in piece) or piece.isupper():
            return piece
        return piece[:1].upper() + piece[1:].lower()

    formatted_words = []
    for word_index, word in enumerate(text.split()):
        parts = word.split('-')
        formatted_parts = [
            format_piece(part, word_index == 0 and part_index == 0)
            for part_index, part in enumerate(parts)
        ]
        formatted_words.append('-'.join(formatted_parts))
    return ' '.join(formatted_words)


def _build_queries(query, region='north_america'):
    """Generate 3 search variations for broader coverage."""
    if region == 'global':
        geo = _extract_geo_hint(query)
        if geo:
            # User specified a geography — anchor all three queries to it
            return [
                f"{query} supplier manufacturer",
                f"{query} distributor {geo}",
                f"{query} company {geo} supplier",
            ]
        return [
            f"{query} supplier manufacturer international",
            f"{query} manufacturer supplier Europe Asia",
            f"{query} supplier China Germany Japan UK India",
        ]
    return [
        f"{query} supplier manufacturer USA",
        f"{query} distributor vendor United States",
        f"{query} company buy purchase USA",
    ]


def handle(query, skip_enrichment=False, region='north_america'):
    """Search for US suppliers using parallel Brave queries. Returns enriched supplier list."""
    try:
        # Step 1: Run Brave searches in parallel
        all_results = []
        all_faq = []
        all_infobox = []
        seen_urls = set()
        failed_searches = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(brave.search, q, 10, region) for q in _build_queries(query, region)]
            for f in concurrent.futures.as_completed(futures):
                try:
                    results, faq, infobox = f.result()
                    for r in results:
                        if r["url"] not in seen_urls:
                            seen_urls.add(r["url"])
                            all_results.append(r)
                    all_faq.extend(faq)
                    if infobox and infobox not in all_infobox:
                        all_infobox.append(infobox)
                except Exception as e:
                    failed_searches += 1
                    print(f"[search] Brave query failed: {e}")

        # Filter out aggregator sites
        AGGREGATORS_ALWAYS = ('amazon.com', 'ebay.com', 'aliexpress.com', 'dhgate.com',
                              'grainger.com', 'mcmaster.com')
        AGGREGATORS_NA_ONLY = ('thomasnet.com', 'alibaba.com', 'globalspec.com',
                               'made-in-china.com', 'indiamart.com', 'tradekey.com',
                               'ec21.com', 'tradeindia.com', 'kompass.com', 'europages.com',
                               'directindustry.com', 'go4worldbusiness.com', 'exportersindia.com')
        active_aggregators = AGGREGATORS_ALWAYS + (AGGREGATORS_NA_ONLY if region == 'north_america' else ())

        filtered_results = []
        for r in all_results:
            url_lower = r["url"].lower()
            # Skip aggregators
            if any(agg in url_lower for agg in active_aggregators):
                continue
            filtered_results.append(r)

        all_results = filtered_results

        if not all_results:
            if failed_searches == len(futures):
                return {"suppliers": [], "blocked": [], "error": "Search provider temporarily unavailable. Please try again."}
            return {"suppliers": [], "blocked": [], "error": "No search results"}

        # Step 2: Build context with all available data — trim to fit token limits
        # Strip verbose fields to reduce size
        trimmed_results = []
        for r in all_results:
            trimmed = {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "description": r.get("description", ""),
            }
            if r.get("extra_snippets"):
                trimmed["extra_snippets"] = r["extra_snippets"][:6]
            trimmed_results.append(trimmed)

        search_context = json.dumps(trimmed_results, indent=1)

        extra_context = ""
        if all_faq:
            seen_q = set()
            unique_faq = []
            for f in all_faq:
                if f["question"] not in seen_q:
                    seen_q.add(f["question"])
                    unique_faq.append(f)
            extra_context += "\n\nFAQ data (company facts):\n" + json.dumps(unique_faq[:15], indent=1)
        if all_infobox:
            extra_context += "\n\nKnowledge panel:\n" + json.dumps(all_infobox[:2], indent=1)

        # Preserve buyer terms like "hydraulic system" and "instruction label";
        # prompt-injection handling belongs in the system prompt, not token deletion.
        safe_query = _clean_query_for_prompt(query)

        # Hard cap: truncate context if too long (~5500 chars ≈ ~1500 tokens, leaves room for system+output)
        user_msg = f"Query: {safe_query}\n\nSearch results:\n{search_context}{extra_context}"
        if len(user_msg) > 12000:
            user_msg = user_msg[:12000] + "\n... (truncated)"

        # Step 3: Feed to LLM with enhanced prompt
        if region == 'global':
            state_field_desc = (
                '- state: Use the 2-letter country code. Examples: '
                '"UK" (Britain), "CN" (China), "IN" (India), "CA" (Canada), "DE" (Germany), '
                '"FR" (France), "JP" (Japan), "KR" (Korea), "TW" (Taiwan), "SG" (Singapore), '
                '"AU" (Australia), "BR" (Brazil), "MX" (Mexico), "IT" (Italy), "ES" (Spain), '
                '"NL" (Netherlands), "CH" (Switzerland), "SE" (Sweden), "PL" (Poland), '
                '"CZ" (Czechia), "TR" (Turkey), "BE" (Belgium), "AT" (Austria), "PT" (Portugal), '
                '"DK" (Denmark), "FI" (Finland), "NO" (Norway), "IE" (Ireland), "HU" (Hungary), '
                '"RO" (Romania), "GR" (Greece), "UA" (Ukraine), "VN" (Vietnam), "TH" (Thailand), '
                '"MY" (Malaysia), "ID" (Indonesia), "PH" (Philippines), "IL" (Israel), '
                '"UAE" (UAE), "SA" (Saudi Arabia), "HK" (Hong Kong), "NZ" (New Zealand), '
                '"ZA" (South Africa), "AR" (Argentina), "CO" (Colombia), "CL" (Chile), '
                '"EG" (Egypt), "MA" (Morocco), "PK" (Pakistan), "BD" (Bangladesh). '
                'For US suppliers, prefix with "US-" followed by the state abbreviation (e.g. "US-CA", "US-TX", "US-IN" for Indiana). '
                'This avoids ambiguity with country codes. If unknown, use the 2-letter country code.'
            )
            geo_hint = _extract_geo_hint(safe_query)
            if geo_hint:
                rule_1 = (
                    f'1. The buyer specified a geographic preference: "{geo_hint}". '
                    f'ONLY include suppliers whose HEADQUARTERS or primary manufacturing operations are in or near that region. '
                    f'Do NOT include a supplier just because they export to, mention, or serve that region — physical location only. '
                    f'Exclude suppliers from unrelated regions entirely (e.g. if buyer wants Europe, exclude China, India, Americas). '
                    f'For US suppliers, use "US-XX" format (e.g. "US-CA", "US-TX"). For all others, use the 2-letter ISO country code (e.g. "DE", "FR", "CN").'
                )
            else:
                rule_1 = (
                    '1. ONLY include non-US international suppliers. '
                    'Do NOT include any suppliers headquartered in the United States under any circumstances. '
                    'Seek out suppliers from Europe, Asia, and other regions exclusively. '
                    'For all suppliers, use the 2-letter country code or full country name — never a US state.'
                )
            rule_2 = (
                '2. Skip consumer e-commerce sites: Amazon, eBay, AliExpress, DHgate, '
                'Grainger catalog pages, McMaster-Carr catalog pages.'
            )
        else:
            state_field_desc = (
                '- state: For US suppliers, you MUST find the specific US state abbreviation '
                '(e.g. "CA", "TX", "OH"). Look carefully at addresses, city/state mentions, ZIP codes, '
                '"headquartered in", "located in", "based in" text in descriptions, snippets, profile info, '
                'FAQ data, and URL patterns. NEVER return just "US" — dig deeper to find the actual state. '
                'If a company has both US and international locations, always use the US state abbreviation. '
                'CRITICAL: "IN" = Indiana (US state). Companies from India, Mumbai, Delhi, Bangalore, '
                'Chennai, Pune, Hyderabad, or with .co.in / .in websites are NOT US suppliers — exclude them entirely.'
            )
            rule_1 = (
                '1. ONLY include suppliers with US headquarters or primary US operations. '
                'Any company headquartered outside the US must be excluded entirely — no exceptions. '
                'India-based companies must NEVER appear, even if state looks like "IN" (Indiana). '
                'Always determine the specific US state — never return just "US".'
            )
            rule_2 = (
                '2. Skip aggregator/marketplace sites: ThomasNet, Alibaba, Amazon, GlobalSpec, '
                'Made-in-China, IndiaMART, eBay, Grainger catalog pages, McMaster-Carr catalog pages.'
            )

        system = f"""You are an industrial supplier researcher. Given web search results (with extra snippets and FAQ data), extract real supplier companies.

Return ONLY a JSON array inside ```json fences. Each supplier object must have these fields:
- name: company name
{state_field_desc}
- products: what they make/sell relevant to the query (use Title Case, e.g. "Ceramic Hybrid Angular Contact Bearings")
- certifications: quality certifications the SUPPLIER HOLDS, found in descriptions, extra_snippets, or FAQ. Look for: ISO 9001, ISO 13485, AS9100, ITAR, NADCAP, AMS, ASTM, QPL, Mil-Spec, FDA, RoHS, CE mark, UL listed/certified. IMPORTANT: only include certs the supplier is certified to — not certs their customers require, and not product-level safety marks on components they sell. If truly none found, "N/A"
- website: company website URL (root domain only, e.g. "https://example.com")
- email: contact email if found, or ""
- yearsInBusiness: Only use years explicitly tied to when the COMPANY was founded or established — not product release years, patent dates, or customer since-dates. Look for "founded in", "established in", "est.", "since [year]" referring to the company itself. Format: "37 yrs (est. 1988)". If unknown, ""
- employees: Only use headcount that refers to THIS company's own workforce — not client sizes or "serving X employees". Format: "60" or "500+" or "10K+". If unknown, ""
- revenue: Look in FAQ for "revenue". Format: "$10M" or "$20.5B". If unknown, ""
STRICT RULES:
{rule_1}
{rule_2}
3. Only include actual manufacturers, distributors, or service providers — not news articles, blog posts, or comparison pages.
4. Extract 5-8 suppliers maximum.
5. READ ALL extra_snippets carefully — they often contain certifications, founding year, and employee data that the main description misses."""

        response = llm.call_llm(system, user_msg, max_tokens=2048)
        if not response:
            return {"suppliers": [], "error": "Search service temporarily unavailable. Please try again."}

        suppliers = _parse_suppliers(response)

        # Retry once if LLM returned unparseable response but we have search results
        if not suppliers and all_results:
            print("[search] LLM parse failed, retrying...")
            response = llm.call_llm(system, user_msg, max_tokens=2048)
            if response:
                suppliers = _parse_suppliers(response)

        if not suppliers:
            return {"suppliers": [], "error": "No suppliers found. Try a different search term."}

        # Apply deterministic location signals before any regional filtering.
        # Unknown generic-TLD suppliers stay pending so the background scraper
        # can verify them; final publish marks unresolved locations as N/A.
        suppliers = [_normalize_supplier_location(s, region) for s in suppliers]
        if region == 'north_america':
            suppliers = _filter_suppliers_for_region(suppliers, region, safe_query, allow_pending=True)
            if not suppliers:
                return {"suppliers": [], "error": "No US suppliers found. Try a different search term."}

        if region == 'global':
            suppliers = _filter_suppliers_for_region(suppliers, region, safe_query, allow_pending=False)
            if not suppliers:
                geo_hint = _extract_geo_hint(safe_query)
                if _GEO_TO_CODES.get(geo_hint):
                    return {"suppliers": [], "error": f"No {geo_hint.title()} suppliers found for this query. Try broadening your search terms."}
                return {"suppliers": [], "error": "No international suppliers found. Try a different search term."}

            # Strip ITAR from non-US suppliers — ITAR is a US-only export regulation;
            # a non-US company cannot be ITAR-registered (LLM frequently hallucinates this).
            for s in suppliers:
                if not _is_us_supplier(s) and s.get('certifications'):
                    cleaned = re.sub(r'\bITAR\b[\s,;]*', '', s['certifications'], flags=re.IGNORECASE).strip(' ,;')
                    s['certifications'] = cleaned if cleaned else ''

        # Normalize and dedup certifications from LLM output.
        # Re-runs the cert string through the scraper's extractor which normalizes
        # case and removes prefix duplicates (e.g. ISO 9001:2015 + ISO 9001 → ISO 9001:2015).
        for s in suppliers:
            certs = (s.get('certifications') or '').strip()
            if certs and certs not in ('N/A',):
                extracted = scraper._extract_certifications(certs)
                extracted = scraper._filter_unverified_certifications(extracted)
                s['certifications'] = ', '.join(extracted) if extracted else ''

        for s in suppliers:
            if s.get("products"):
                s["products"] = _title_case_product(s["products"])
            if s.get("yearsInBusiness"):
                s["yearsInBusiness"] = _normalize_years_in_business_value(s["yearsInBusiness"])

        # Step 4+5: Return immediately, enrich reputation + emails in background
        _cleanup_old_searches()

        search_id = str(uuid.uuid4())[:8]

        # Normalize fields that will be updated in background: show blank rather than
        # an ambiguous placeholder that visibly changes on the next render.
        for s in suppliers:
            if s.get('state', '') in ('', 'US', 'USA'):
                s['state'] = ''
            if s.get('certifications', '') in ('N/A', '', None):
                s['certifications'] = ''
            # Ensure revenue always has a $ prefix (LLM occasionally omits it)
            rev = s.get('revenue', '')
            if rev and not rev.startswith('$'):
                s['revenue'] = '$' + rev

        # Strip emails in demo mode; set _enriching spinner on all suppliers
        if skip_enrichment:
            for s in suppliers:
                s.pop("email", None)
        for s in suppliers:
            if not s.get("email"):
                s["_enriching"] = True
        _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "region": region, "ts": time.time()}

        thread = threading.Thread(target=_background_enrich, args=(search_id, suppliers, skip_enrichment), daemon=True)
        thread.start()

        return {"searchId": search_id, "suppliers": suppliers, "status": "enriching"}
    except Exception as e:
        print(f"[search] Error: {e}")
        return {"suppliers": [], "error": "Search failed. Please try again."}


def _regenerate_match_reasons(suppliers, query):
    """Re-score match reasons using enriched data (certs, reputation, years, employees)."""
    if not query or not suppliers:
        return suppliers

    # Build a compact profile for each supplier
    profiles = []
    for s in suppliers:
        profile = {"name": s.get("name", ""), "products": s.get("products", "")}
        for field in ("certifications", "yearsInBusiness", "employees", "revenue", "state"):
            val = s.get(field, "")
            if val and val not in ("N/A", ""):
                profile[field] = val
        profiles.append(profile)

    system = """You are a critical industrial procurement analyst evaluating supplier matches.

Given the buyer's search query and enriched supplier profiles, write a BLUNT, SPECIFIC matchReason for each supplier.

A strong match has CONCRETE evidence such as:
- Certifications directly relevant to the query (e.g. AS9100 for aerospace parts, ISO 13485 for medical)
- Specific product lines that directly address what the buyer needs (not vague "industrial supplier")
- Proven scale: employee count and revenue that fit the likely order size (only if data is present)
- Track record: years in business in the relevant industry (only if data is present)

A weak match has:
- No relevant certifications (or only generic ISO 9001)
- Vague product descriptions that don't clearly cover the query
- The company appears to be a general distributor rather than a specialist

RULES:
1. Only cite data that is explicitly present in the profile. Empty fields mean data wasn't found — treat as unknown, NOT weak.
2. NEVER use your training knowledge to add certifications, employee counts, revenue, or founding years not in the profile. If "AS9100" is not in the certifications field, do not mention it.
3. Cite specific data points when present: "ISO 9001-certified, 200+ employees, 40 yrs in this space"
4. Flag red flags based only on what IS known: "No relevant certifications listed", "Appears to be a general distributor"
5. Do NOT say "no track record found" or "unknown scale" — omit those dimensions when data is missing.
6. Do NOT pad weak matches with filler praise. Short and blunt is fine.
7. Max 1-2 sentences per supplier.

Return ONLY a JSON array of objects: [{"name": "...", "matchReason": "..."}]
Use ```json fences."""

    user_msg = f"Buyer is searching for: {query}\n\nSupplier profiles:\n{json.dumps(profiles, indent=1)}"
    if len(user_msg) > 6000:
        user_msg = user_msg[:6000] + "\n... (truncated)"

    try:
        response = llm.call_llm(system, user_msg, max_tokens=1024)
        if not response:
            return suppliers

        # Parse the response
        parsed = _parse_suppliers(response)
        if not parsed:
            return suppliers

        # Build lookup and merge back
        reason_map = {item["name"]: item["matchReason"] for item in parsed if "name" in item and "matchReason" in item}
        for s in suppliers:
            new_reason = reason_map.get(s.get("name", ""))
            if new_reason:
                s["matchReason"] = new_reason
    except Exception as e:
        print(f"[search] Match reason regeneration failed: {e}")

    return suppliers



def _background_enrich(search_id, suppliers, skip_emails=False):
    """Enrich reputation + match reasons + website scraping in parallel.

    skip_emails=True: identical pipeline but no email extraction (demo mode).

    Rendering order:
      Render 1 (instant):  name, state, products, certs*, years*, employees*, revenue* (* if in Brave)
      Render 2 (~3-5s):    reputation gaps filled (years, employees, revenue, certs)
      Render 3 (~5-7s):    match reasons (runs parallel with website scraping)
      Render 4 (~5-15s):   location/certs/emails trickle in per-supplier as each finishes
    """
    try:
        entry = _searches.get(search_id, {})
        query = entry.get("query", "")
        region = entry.get("region", "north_america")
        blocked_sites = []

        # Phase 1: Reputation enrichment — fills years, employees, revenue, certs gaps (~3-5s)
        suppliers = _enrich_reputation(suppliers)
        publish_suppliers = _filter_suppliers_for_region(suppliers, region, query, allow_pending=True)
        _searches[search_id] = {
            "suppliers": list(publish_suppliers),
            "status": "enriching",
            "blocked": [],
            "query": query,
            "region": region,
            "ts": time.time(),
        }

        # Phase 2: Match reasons + website scraping in parallel
        current_suppliers = list(suppliers)

        def _on_supplier_enriched(idx, enriched_supplier):
            """Called as each supplier finishes website scraping — publish immediately."""
            enriched_supplier.pop("_enriching", None)
            current_suppliers[idx] = enriched_supplier
            publish_suppliers = _filter_suppliers_for_region(list(current_suppliers), region, query, allow_pending=True)
            _searches[search_id] = {
                "suppliers": publish_suppliers,
                "status": "enriching",
                "blocked": [] if skip_emails else list(blocked_sites),
                "query": query,
                "region": region,
                "ts": time.time(),
            }

        def _do_match_reasons():
            return _regenerate_match_reasons(list(suppliers), query)

        def _do_scraping():
            return scraper.enrich_suppliers(
                list(suppliers),
                on_each=_on_supplier_enriched,
                skip_email=skip_emails,
                blocked_sites=blocked_sites,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            match_future = pool.submit(_do_match_reasons)
            scrape_future = pool.submit(_do_scraping)

            # Collect match reasons but do NOT publish yet — they will only be
            # applied in the final publish so matchReason never visibly changes.
            reason_map = {}
            try:
                matched = match_future.result()
                reason_map = {s.get("name"): s.get("matchReason") for s in matched if s.get("matchReason")}
            except Exception as e:
                print(f"[search] Match reason error: {e}")

            # Wait for website scraping to finish
            try:
                enriched = scrape_future.result()
                blocked = [] if skip_emails else list(blocked_sites)
                for s in enriched:
                    s.pop("_enriching", None)
                enriched = _filter_suppliers_for_region(enriched, region, query, allow_pending=True)
                enriched = _mark_unknown_locations(enriched)

                # Apply match reasons from the parallel LLM call
                for s in enriched:
                    reason = reason_map.get(s.get("name"))
                    if reason:
                        s["matchReason"] = reason

                # Re-run match reasons if scraping surfaced new certs (matchReason
                # hasn't been shown yet so this is still a first-time render)
                has_new_certs = any(
                    s.get("certifications", "") not in ("", None)
                    and s.get("certifications") != next((orig.get("certifications") for orig in suppliers if orig.get("name") == s.get("name")), None)
                    for s in enriched
                )
                if has_new_certs:
                    enriched = _regenerate_match_reasons(enriched, query)

                _searches[search_id] = {
                    "suppliers": enriched,
                    "status": "done",
                    "blocked": blocked,
                    "query": query,
                    "region": region,
                    "ts": time.time(),
                }
            except Exception as e:
                print(f"[search] Website scraping error: {e}")
                for s in current_suppliers:
                    s.pop("_enriching", None)
                    reason = reason_map.get(s.get("name"))
                    if reason:
                        s["matchReason"] = reason
                publish_suppliers = _filter_suppliers_for_region(current_suppliers, region, query, allow_pending=True)
                publish_suppliers = _mark_unknown_locations(publish_suppliers)
                _searches[search_id] = {
                    "suppliers": publish_suppliers,
                    "status": "done",
                    "blocked": [],
                    "query": query,
                    "region": region,
                    "ts": time.time(),
                }

    except Exception as e:
        for s in suppliers:
            s.pop("_enriching", None)
        entry = _searches.get(search_id, {})
        query = entry.get("query", "")
        region = entry.get("region", "north_america")
        publish_suppliers = _filter_suppliers_for_region(suppliers, region, query, allow_pending=True)
        publish_suppliers = _mark_unknown_locations(publish_suppliers)
        _searches[search_id] = {
            "suppliers": publish_suppliers,
            "status": "done",
            "blocked": [],
            "query": query,
            "region": region,
            "ts": time.time(),
        }
        print(f"[search] Background enrichment error: {e}")


def get_status(search_id):
    """Get current status of a background search enrichment."""
    entry = _searches.get(search_id)
    if not entry:
        return {"error": "Search not found", "status": "done", "suppliers": []}
    return {"suppliers": entry["suppliers"], "status": entry["status"], "blocked": entry.get("blocked", [])}


def _cleanup_old_searches():
    """Remove search entries older than 5 minutes."""
    now = time.time()
    expired = [sid for sid, data in _searches.items() if now - data.get("ts", 0) > _MAX_AGE]
    for sid in expired:
        del _searches[sid]


def _enrich_reputation(suppliers):
    """Second-pass: search Brave for each supplier's company facts (founded, employees, revenue, certs)."""
    needs_enrichment = [s for s in suppliers if not s.get("yearsInBusiness") or not s.get("employees")]
    if not needs_enrichment:
        return suppliers
    current_year = datetime.now(timezone.utc).year

    # Search up to 5 companies in parallel
    def _fetch_company_facts(supplier):
        try:
            name = supplier.get("name", "")
            website = supplier.get("website", "")
            if website and not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            domain = urllib.parse.urlparse(website).netloc.lower().removeprefix('www.')
            facts_query = f"{name} site:{domain} founded employees revenue" if domain else f"{name} company founded employees"
            results, faq, infobox = brave.search(facts_query, 3)
            facts = {}

            def _parse_year(text):
                """Extract a plausible founding year."""
                for m in re.finditer(r'\b(\d{4})\b', text):
                    y = int(m.group(1))
                    if 1850 <= y <= current_year:
                        return y
                return None

            # Extract from FAQ
            for f in faq:
                q = f["question"].lower()
                a = f["answer"]
                if "founded" in q or "established" in q:
                    year = _parse_year(a)
                    if year:
                        facts["yearsInBusiness"] = _format_years_in_business(year, current_year)
                if ("employee" in q or "size" in q or "staff" in q) and "key employee" not in q:
                    # Require the number to precede "employees" — avoids matching client headcounts
                    emp_match = re.search(r'\b([\d,]+K?\+?)\s*(?:total\s+)?(?:employees|staff|workers)\b', a, re.I)
                    if emp_match:
                        facts["employees"] = emp_match.group(1).replace(",", "")
                if "revenue" in q and "key employee" not in q:
                    rev_match = re.search(r'\$([\d.]+)\s*(B|M|K|billion|million)', a, re.I)
                    if rev_match:
                        amt = rev_match.group(1)
                        unit = rev_match.group(2)[0].upper()
                        facts["revenue"] = f"${amt}{unit}"

            # Extract from infobox
            if infobox:
                for attr_name, attr_val in infobox.get("attributes", []):
                    attr_lower = attr_name.lower()
                    if "founded" in attr_lower and not facts.get("yearsInBusiness"):
                        year = _parse_year(attr_val)
                        if year:
                            facts["yearsInBusiness"] = _format_years_in_business(year, current_year)
                    if "employee" in attr_lower and not facts.get("employees"):
                        emp_match = re.search(r'([\d,]+K?\+?)', attr_val)
                        if emp_match:
                            facts["employees"] = emp_match.group(1)
                    if "revenue" in attr_lower and not facts.get("revenue"):
                        rev_match = re.search(r'\$([\d.]+)\s*(B|M|K|billion|million)', attr_val, re.I)
                        if rev_match:
                            facts["revenue"] = f"${rev_match.group(1)}{rev_match.group(2)[0].upper()}"

            return supplier["name"], facts
        except Exception:
            return supplier["name"], {}

    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_fetch_company_facts, s): s for s in needs_enrichment[:5]}
        fact_map = {}
        for f in concurrent.futures.as_completed(futures):
            name, facts = f.result()
            fact_map[name] = facts

    # Merge facts back — only fills yearsInBusiness, employees, revenue.
    # state and certifications are intentionally excluded here: the website
    # scraper (Render 4) is the ground truth for both and they must not change
    # after that render.
    _SKIP_IN_REPUTATION = {'state', 'certifications'}
    for s in suppliers:
        facts = fact_map.get(s["name"], {})
        for key, val in facts.items():
            if key in _SKIP_IN_REPUTATION:
                continue
            if val and not s.get(key):
                if key == 'revenue' and not val.startswith('$'):
                    val = '$' + val
                s[key] = val

    return suppliers


def _parse_suppliers(text):
    """Parse supplier JSON from LLM response."""
    if not text:
        return []

    # Try ```json fences first
    fence = re.search(r'```json\s*([\s\S]*?)```', text)
    if fence:
        try:
            result = json.loads(fence.group(1).strip())
            if isinstance(result, list) and result:
                return result
        except json.JSONDecodeError:
            pass

    # Try to find the outermost JSON array by bracket matching
    start = text.find('[')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(text[start:i+1])
                        if isinstance(result, list) and result:
                            return result
                    except json.JSONDecodeError:
                        pass
                    break

    return []
