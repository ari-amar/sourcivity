"""Supplier search — parallel Brave queries + LLM extraction + background scraper enrichment."""
import concurrent.futures
import json
import re
import threading
import time
import uuid
from services import llm, scraper, brave

# In-memory store for background enrichment results
# { search_id: { "suppliers": [...], "status": "enriching"|"done", "blocked": [], "ts": time } }
_searches = {}
_MAX_AGE = 300  # clean up entries older than 5 minutes


def _build_queries(query):
    """Generate 3 search variations for broader coverage."""
    return [
        f"{query} supplier manufacturer USA",
        f"{query} distributor vendor United States",
        f"{query} company buy purchase USA",
    ]


def handle(query, skip_enrichment=False):
    """Search for US suppliers using parallel Brave queries. Returns enriched supplier list."""
    try:
        # Step 1: Run Brave searches in parallel
        all_results = []
        all_faq = []
        all_infobox = []
        seen_urls = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(brave.search, q, 10) for q in _build_queries(query)]
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
                except Exception:
                    pass

        # Filter out non-US domains and aggregator sites
        NON_US_TLDS = ('.cn', '.co.uk', '.uk', '.de', '.fr', '.it', '.es', '.jp', '.kr',
                       '.in', '.ca', '.au', '.br', '.mx', '.ru', '.nl', '.se', '.ch',
                       '.tw', '.hk', '.sg', '.co.in', '.com.cn', '.com.au', '.co.jp',
                       '.com.br', '.co.kr', '.com.mx', '.com.sg', '.com.tw', '.co.nz')
        AGGREGATORS = ('thomasnet.com', 'alibaba.com', 'amazon.com', 'globalspec.com',
                       'made-in-china.com', 'indiamart.com', 'ebay.com', 'grainger.com',
                       'mcmaster.com', 'aliexpress.com', 'dhgate.com', 'tradekey.com',
                       'ec21.com', 'tradeindia.com', 'kompass.com', 'europages.com',
                       'directindustry.com', 'go4worldbusiness.com', 'exportersindia.com')

        filtered_results = []
        for r in all_results:
            url_lower = r["url"].lower()
            # Skip non-US country domains
            if any(url_lower.rstrip('/').endswith(tld) or f'{tld}/' in url_lower for tld in NON_US_TLDS):
                continue
            # Skip aggregators
            if any(agg in url_lower for agg in AGGREGATORS):
                continue
            filtered_results.append(r)

        all_results = filtered_results

        if not all_results:
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

        # Sanitize query — strip anything that looks like prompt injection
        safe_query = re.sub(r'(?i)(ignore|forget|disregard|override|system|instruction|prompt)', '', query).strip()[:200]

        # Hard cap: truncate context if too long (~5500 chars ≈ ~1500 tokens, leaves room for system+output)
        user_msg = f"Query: {safe_query}\n\nSearch results:\n{search_context}{extra_context}"
        if len(user_msg) > 12000:
            user_msg = user_msg[:12000] + "\n... (truncated)"

        # Step 3: Feed to LLM with enhanced prompt
        system = """You are a US industrial supplier researcher. Given web search results (with extra snippets and FAQ data), extract real supplier companies.

Return ONLY a JSON array inside ```json fences. Each supplier object must have these fields:
- name: company name
- state: US state abbreviation ONLY (e.g. "CA", "TX", "OH"). Look for city/state in descriptions, snippets, profile info, or URL patterns. NEVER use "USA" — if you truly cannot determine the state, use "US".
- products: what they make/sell relevant to the query (use Title Case, e.g. "Ceramic Hybrid Angular Contact Bearings")
- certifications: quality certs found ANYWHERE in descriptions, extra_snippets, or FAQ. Look for: ISO 9001, ISO 13485, AS9100, ITAR, NADCAP, AMS, ASTM, QPL, Mil-Spec, FDA, CE, UL, RoHS. Also look for phrases like "certified", "accredited", "registered", "compliant". If truly none found, "N/A"
- website: company website URL (root domain only, e.g. "https://example.com")
- email: contact email if found, or ""
- yearsInBusiness: Look in FAQ for "founded" or "established". Also check extra_snippets for "est.", "since", "founded in", "established in". Format: "37 yrs (est. 1988)". If unknown, ""
- employees: Look in FAQ for "employees", "size", "staff". Also check extra_snippets. Format: "60" or "500+" or "10K+". If unknown, ""
- revenue: Look in FAQ for "revenue". Format: "$10M" or "$20.5B". If unknown, ""
STRICT RULES:
1. ONLY include companies physically located in the United States. Exclude any company headquartered in China, India, Canada, UK, Europe, or anywhere outside the US. Check the URL domain — .cn, .co.uk, .ca, .de etc. are NOT US companies.
2. Skip aggregator/marketplace sites: ThomasNet, Alibaba, Amazon, GlobalSpec, Made-in-China, IndiaMART, eBay, Grainger catalog pages, McMaster-Carr catalog pages.
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

        # Title-case products field
        _LOWERCASE_WORDS = {'and', 'or', 'the', 'a', 'an', 'of', 'for', 'in', 'on', 'with', 'to', 'by', 'at'}
        for s in suppliers:
            if s.get("products"):
                words = s["products"].split()
                s["products"] = " ".join(
                    w if i > 0 and w.lower() in _LOWERCASE_WORDS else w.capitalize() if w.islower() else w
                    for i, w in enumerate(words)
                )

        # Step 4+5: Return immediately, enrich reputation + emails in background
        _cleanup_old_searches()

        search_id = str(uuid.uuid4())[:8]

        if skip_enrichment:
            # Demo mode: strip emails, no background scraping, but still enrich reputation
            for s in suppliers:
                s.pop("email", None)
                s.pop("_enriching", None)
            _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}
            thread = threading.Thread(target=_background_reputation, args=(search_id,), daemon=True)
            thread.start()
            return {"searchId": search_id, "suppliers": suppliers, "status": "enriching"}

        # Full mode: enrich reputation + scrape emails in background
        for s in suppliers:
            if not s.get("email"):
                s["_enriching"] = True
        _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}

        thread = threading.Thread(target=_background_enrich, args=(search_id, suppliers), daemon=True)
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
        profile = {
            "name": s.get("name", ""),
            "products": s.get("products", ""),
            "certifications": s.get("certifications", "N/A"),
            "yearsInBusiness": s.get("yearsInBusiness", ""),
            "employees": s.get("employees", ""),
            "revenue": s.get("revenue", ""),
            "state": s.get("state", ""),
        }
        profiles.append(profile)

    system = """You are a critical industrial procurement analyst evaluating supplier matches.

Given the buyer's search query and enriched supplier profiles, write a BLUNT, SPECIFIC matchReason for each supplier.

A strong match has CONCRETE evidence such as:
- Certifications directly relevant to the query (e.g. AS9100 for aerospace parts, ISO 13485 for medical)
- Specific product lines that directly address what the buyer needs (not vague "industrial supplier")
- Proven scale: adequate employee count and revenue for the likely order size
- Track record: years in business in the relevant industry

A weak match has:
- No relevant certifications (or only generic ISO 9001)
- Vague product descriptions that don't clearly cover the query
- Unknown or very small scale with no track record info
- The company appears to be a general distributor rather than a specialist

RULES:
1. Be honest. If evidence is thin, say so: "Limited info — no certs or track record found"
2. Cite specific data points: "AS9100-certified with 200+ employees and 40 yrs in aerospace fasteners"
3. Flag red flags: "No certifications listed", "Very small scale", "Unclear if they actually manufacture this"
4. Do NOT pad weak matches with filler praise. Short and blunt is fine.
5. Max 1-2 sentences per supplier.

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


def _background_reputation(search_id):
    """Enrich reputation data in background (demo mode — no email scraping)."""
    try:
        entry = _searches.get(search_id)
        if not entry:
            return
        suppliers = entry["suppliers"]
        query = entry.get("query", "")
        enriched = _enrich_reputation(suppliers)
        enriched = _regenerate_match_reasons(enriched, query)
        _searches[search_id] = {"suppliers": enriched, "status": "done", "blocked": [], "query": query, "ts": time.time()}
    except Exception as e:
        print(f"[search] Background reputation error: {e}")
        if search_id in _searches:
            _searches[search_id]["status"] = "done"


def _background_enrich(search_id, suppliers):
    """Enrich reputation + scrape emails in background thread."""
    try:
        query = _searches.get(search_id, {}).get("query", "")
        # Reputation first (fast), then email scraping (slow)
        suppliers = _enrich_reputation(suppliers)
        _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}
        scraper._blocked_sites.clear()
        enriched = scraper.enrich_suppliers(suppliers)
        blocked = scraper.get_blocked_sites()
        # Remove _enriching flag from all suppliers
        for s in enriched:
            s.pop("_enriching", None)
        # Regenerate match reasons with full enriched data
        enriched = _regenerate_match_reasons(enriched, query)
        _searches[search_id] = {"suppliers": enriched, "status": "done", "blocked": blocked, "query": query, "ts": time.time()}
    except Exception as e:
        # On error, mark done with whatever we have
        for s in suppliers:
            s.pop("_enriching", None)
        _searches[search_id] = {"suppliers": suppliers, "status": "done", "blocked": [], "query": query, "ts": time.time()}
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
    needs_enrichment = [s for s in suppliers if not s.get("yearsInBusiness") or not s.get("employees") or s.get("certifications", "N/A") in ("N/A", "", None)]
    if not needs_enrichment:
        return suppliers

    # Search up to 5 companies in parallel
    def _fetch_company_facts(supplier):
        try:
            name = supplier.get("name", "")
            results, faq, infobox = brave.search(f"{name} company founded employees", 3)
            facts = {}

            # Extract from FAQ
            for f in faq:
                q = f["question"].lower()
                a = f["answer"]
                if "founded" in q or "established" in q:
                    # Extract year
                    year_match = re.search(r'(\d{4})', a)
                    if year_match:
                        year = int(year_match.group(1))
                        age = 2026 - year
                        facts["yearsInBusiness"] = f"{age} yrs (est. {year})"
                if ("employee" in q or "size" in q or "staff" in q) and "key employee" not in q:
                    emp_match = re.search(r'([\d,]+K?\+?)\s*(?:total\s+)?(?:employees|staff|people|workers)', a, re.I)
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
                        year_match = re.search(r'(\d{4})', attr_val)
                        if year_match:
                            year = int(year_match.group(1))
                            facts["yearsInBusiness"] = f"{2026 - year} yrs (est. {year})"
                    if "employee" in attr_lower and not facts.get("employees"):
                        emp_match = re.search(r'([\d,]+K?\+?)', attr_val)
                        if emp_match:
                            facts["employees"] = emp_match.group(1)
                    if "revenue" in attr_lower and not facts.get("revenue"):
                        rev_match = re.search(r'\$([\d.]+)\s*(B|M|K|billion|million)', attr_val, re.I)
                        if rev_match:
                            facts["revenue"] = f"${rev_match.group(1)}{rev_match.group(2)[0].upper()}"
                # Use infobox long_desc for location/state
                desc = infobox.get("long_desc", "")
                if desc and supplier.get("state") in ("US", "USA", ""):
                    state_match = re.search(r',\s*([A-Z]{2})\b', desc)
                    if state_match:
                        facts["state"] = state_match.group(1)

            # Extract certs from extra_snippets if current is N/A or empty
            if supplier.get("certifications", "N/A") in ("N/A", "", None):
                all_text = " ".join(r.get("description", "") + " " + " ".join(r.get("extra_snippets", [])) for r in results)
                cert_patterns = re.findall(r'(?:ISO\s*\d{4,5}(?::\d{4})?|AS\s*9100[A-Z]?|ITAR|NADCAP|AMS\s*\d+|ASTM\s*[A-Z]\d+|QPL|Mil-Spec|FDA|RoHS|CE\s+mark)', all_text, re.I)
                if cert_patterns:
                    unique_certs = list(dict.fromkeys(c.strip() for c in cert_patterns))
                    facts["certifications"] = ", ".join(unique_certs[:5])

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

    # Merge facts back
    for s in suppliers:
        facts = fact_map.get(s["name"], {})
        for key, val in facts.items():
            if val and not s.get(key):
                s[key] = val
            # Override N/A or empty certs
            if key == "certifications" and val and s.get(key) in ("N/A", "", None):
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
