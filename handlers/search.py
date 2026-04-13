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
_US_STATE_ABBRS = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY',
}


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

        # Filter out aggregator sites
        AGGREGATORS = ('thomasnet.com', 'alibaba.com', 'amazon.com', 'globalspec.com',
                       'made-in-china.com', 'indiamart.com', 'ebay.com', 'grainger.com',
                       'mcmaster.com', 'aliexpress.com', 'dhgate.com', 'tradekey.com',
                       'ec21.com', 'tradeindia.com', 'kompass.com', 'europages.com',
                       'directindustry.com', 'go4worldbusiness.com', 'exportersindia.com')

        filtered_results = []
        for r in all_results:
            url_lower = r["url"].lower()
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
        system = """You are an industrial supplier researcher. Given web search results (with extra snippets and FAQ data), extract real supplier companies.

Return ONLY a JSON array inside ```json fences. Each supplier object must have these fields:
- name: company name
- state: For US suppliers, you MUST find the specific US state abbreviation (e.g. "CA", "TX", "OH"). Look carefully at addresses, city/state mentions, ZIP codes, "headquartered in", "located in", "based in" text in descriptions, snippets, profile info, FAQ data, and URL patterns. NEVER return just "US" — dig deeper to find the actual state. For non-US suppliers, use standard country abbreviations: "UK", "CHN", "IND", "CAN", "GER", "FRA", "JPN", "KOR", "TWN", "SGP", "AUS", "BRA", "MEX". If a company has both US and international locations, always use the US state abbreviation.
- products: what they make/sell relevant to the query (use Title Case, e.g. "Ceramic Hybrid Angular Contact Bearings")
- certifications: quality certs found ANYWHERE in descriptions, extra_snippets, or FAQ. Look for: ISO 9001, ISO 13485, AS9100, ITAR, NADCAP, AMS, ASTM, QPL, Mil-Spec, FDA, CE, UL, RoHS. Also look for phrases like "certified", "accredited", "registered", "compliant". If truly none found, "N/A"
- website: company website URL (root domain only, e.g. "https://example.com")
- email: contact email if found, or ""
- yearsInBusiness: Look in FAQ for "founded" or "established". Also check extra_snippets for "est.", "since", "founded in", "established in". Format: "37 yrs (est. 1988)". If unknown, ""
- employees: Look in FAQ for "employees", "size", "staff". Also check extra_snippets. Format: "60" or "500+" or "10K+". If unknown, ""
- revenue: Look in FAQ for "revenue". Format: "$10M" or "$20.5B". If unknown, ""
STRICT RULES:
1. Include suppliers from any country. For US suppliers, always determine the specific state — never leave it as just "US". For non-US suppliers, use standard abbreviations (UK, CHN, IND, CAN, GER, FRA, JPN, KOR, TWN, SGP, AUS, BRA, MEX).
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

        # Strip emails in demo mode; set _enriching spinner on all suppliers
        if skip_enrichment:
            for s in suppliers:
                s.pop("email", None)
        for s in suppliers:
            if not s.get("email"):
                s["_enriching"] = True
        _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}

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
        query = _searches.get(search_id, {}).get("query", "")

        # Phase 1: Reputation enrichment — fills years, employees, revenue, certs gaps (~3-5s)
        suppliers = _enrich_reputation(suppliers)
        _searches[search_id] = {"suppliers": list(suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}

        # Phase 2: Match reasons + website scraping in parallel
        if not skip_emails:
            scraper._blocked_sites.clear()
        current_suppliers = list(suppliers)

        def _on_supplier_enriched(idx, enriched_supplier):
            """Called as each supplier finishes website scraping — publish immediately."""
            enriched_supplier.pop("_enriching", None)
            current_suppliers[idx] = enriched_supplier
            _searches[search_id] = {
                "suppliers": list(current_suppliers),
                "status": "enriching",
                "blocked": [] if skip_emails else scraper.get_blocked_sites(),
                "query": query,
                "ts": time.time(),
            }

        def _do_match_reasons():
            return _regenerate_match_reasons(list(suppliers), query)

        def _do_scraping():
            return scraper.enrich_suppliers(list(suppliers), on_each=_on_supplier_enriched, skip_email=skip_emails)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            match_future = pool.submit(_do_match_reasons)
            scrape_future = pool.submit(_do_scraping)

            # Match reasons typically finish first (~2-3s LLM call)
            try:
                matched = match_future.result()
                reason_map = {s.get("name"): s.get("matchReason") for s in matched if s.get("matchReason")}
                for s in current_suppliers:
                    reason = reason_map.get(s.get("name"))
                    if reason:
                        s["matchReason"] = reason
                _searches[search_id] = {"suppliers": list(current_suppliers), "status": "enriching", "blocked": [], "query": query, "ts": time.time()}
            except Exception as e:
                print(f"[search] Match reason error: {e}")

            # Wait for website scraping to finish
            try:
                enriched = scrape_future.result()
                blocked = [] if skip_emails else scraper.get_blocked_sites()
                # Final merge: use enriched list but keep match reasons from above
                for s in enriched:
                    s.pop("_enriching", None)
                    name = s.get("name")
                    for cs in current_suppliers:
                        if cs.get("name") == name and cs.get("matchReason"):
                            s["matchReason"] = cs["matchReason"]
                            break

                # Re-run match reasons only if scraping found new certs
                has_new_certs = any(
                    s.get("certifications", "N/A") not in ("N/A", "", None)
                    and s.get("certifications") != next((orig.get("certifications") for orig in suppliers if orig.get("name") == s.get("name")), None)
                    for s in enriched
                )
                if has_new_certs:
                    enriched = _regenerate_match_reasons(enriched, query)

                _searches[search_id] = {"suppliers": enriched, "status": "done", "blocked": blocked, "query": query, "ts": time.time()}
            except Exception as e:
                print(f"[search] Website scraping error: {e}")
                for s in current_suppliers:
                    s.pop("_enriching", None)
                _searches[search_id] = {"suppliers": current_suppliers, "status": "done", "blocked": [], "query": query, "ts": time.time()}

    except Exception as e:
        for s in suppliers:
            s.pop("_enriching", None)
        query = _searches.get(search_id, {}).get("query", "")
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
                    # Try ZIP pattern first
                    zip_m = re.search(r'([A-Z]{2})\s+\d{5}', desc)
                    if zip_m and zip_m.group(1) in _US_STATE_ABBRS:
                        facts["state"] = zip_m.group(1)
                    else:
                        state_match = re.search(r',\s*([A-Z]{2})\b', desc)
                        if state_match and state_match.group(1) in _US_STATE_ABBRS:
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
