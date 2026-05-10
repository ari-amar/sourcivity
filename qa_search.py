#!/usr/bin/env python3
"""
Search QA script — runs test queries, waits for full enrichment, scores results.

Usage (on the server where .env lives):
    python3 qa_search.py
    python3 qa_search.py --query "titanium fasteners" --region north_america
    python3 qa_search.py --suite all          # run all built-in test cases
"""
import argparse
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from handlers import search as search_handler

# ---------------------------------------------------------------------------
# Test suite — (query, region, notes_about_what_to_watch_for)
# ---------------------------------------------------------------------------
TEST_CASES = [
    # Commodity US searches — should have clean state, real certs
    ("titanium fasteners",              "north_america", "expect aerospace certs (AS9100), US states"),
    ("ceramic bearings",                "north_america", "precision manufacturers, likely CA/OH/CT"),
    ("hydraulic seals polyurethane",    "north_america", "industrial, possible ITAR/Mil-Spec"),
    ("stainless steel round bar",       "north_america", "metal service centers — watch for Indian suppliers slipping through"),
    ("vibrating fork level switches",   "north_america", "instrumentation, should be US companies"),
    # Global searches — should return non-US majority
    ("CW732R brass rod",                "global",        "European alloy — expect UK/GER/CZ suppliers"),
    ("precision linear bearings",       "global",        "expect JPN/GER alongside US"),
    # Niche / tricky
    ("Hastelloy C276 round bar",        "north_america", "high Indian supplier density — key test for IN filter"),
    ("Inconel 625 pipe fittings",       "north_america", "another India-dense category"),
    ("graphite die-formed packing rings","north_america","niche — watch for vague/empty certs"),
]

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
US_STATE_ABBRS = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
    'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
    'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
    'VA','WA','WV','WI','WY',
}
KNOWN_COUNTRY_NAMES = {
    'india','china','uk','germany','france','japan','korea','taiwan',
    'singapore','australia','canada','brazil','mexico','austria','czechia',
}
INDIAN_SIGNALS = {'india', 'mumbai', 'delhi', 'bangalore', 'chennai', 'hyderabad', 'pune', '.co.in'}


def _check_supplier(s, region):
    """Return list of issue strings for a single supplier, or empty list if clean."""
    issues = []
    name = s.get("name", "?")
    state = (s.get("state") or "").strip()
    website = (s.get("website") or "").lower()
    products = (s.get("products") or "").lower()
    certs = (s.get("certifications") or "")
    years = s.get("yearsInBusiness") or ""
    employees = s.get("employees") or ""
    match = s.get("matchReason") or ""

    # --- Region correctness ---
    if region == "north_america":
        # Must resolve to a US state (or blank = pending)
        if state and state.upper() not in US_STATE_ABBRS and state.upper() not in ("", "US", "USA"):
            issues.append(f"NON-US state in NA mode: '{state}'")
        # Indian supplier slipped through
        name_products = name.lower() + " " + products
        if any(tok in name_products for tok in INDIAN_SIGNALS) or ".co.in" in website:
            issues.append("INDIAN SUPPLIER slipped through NA filter")
        if state.upper() == "IN":
            issues.append("AMBIGUOUS state 'IN' (Indiana vs India) — verify manually")
    else:
        # Global: state should be a country name, not a US state abbreviation (mostly)
        if state.upper() in US_STATE_ABBRS:
            pass  # fine — 1-2 US results allowed in global
        elif state and state.lower() not in KNOWN_COUNTRY_NAMES:
            issues.append(f"UNKNOWN country/state value: '{state}'")

    # --- Data completeness ---
    if not certs or certs in ("N/A", ""):
        issues.append("MISSING certifications (enrichment may have found none)")
    if not years and not employees:
        issues.append("MISSING reputation data (years + employees both blank)")
    if not s.get("website"):
        issues.append("MISSING website")
    if not s.get("email") and not s.get("contactUrl"):
        issues.append("MISSING email and contactUrl (scraper may have been blocked)")

    # --- Match reason quality ---
    if match:
        lower_match = match.lower()
        if "no track record" in lower_match or "unknown scale" in lower_match:
            issues.append("MATCH REASON penalizes missing data (should be omitted, not flagged)")
        if "limited info" in lower_match and "no certs" in lower_match and not certs:
            issues.append("MATCH REASON says 'limited info / no certs' — correct but watch pattern")
        if len(match) < 20:
            issues.append(f"MATCH REASON suspiciously short: '{match}'")

    # --- Cert plausibility ---
    if certs and certs.lower() in ("ul", "n/a", "none"):
        issues.append(f"CERT VALUE looks wrong: '{certs}'")

    return issues


def _poll_until_done(search_id, timeout=90):
    """Poll get_status until status='done' or timeout. Returns final suppliers list."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = search_handler.get_status(search_id)
        if result.get("status") == "done":
            return result.get("suppliers", [])
        time.sleep(2)
    # Return whatever we have
    return search_handler.get_status(search_id).get("suppliers", [])


def _run_one(query, region, notes):
    print(f"\n{'='*72}")
    print(f"QUERY : {query}")
    print(f"REGION: {region}")
    print(f"NOTES : {notes}")
    print("Running search...")

    t0 = time.time()
    result = search_handler.handle(query, skip_enrichment=False, region=region)

    if "error" in result and not result.get("suppliers"):
        print(f"  ERROR: {result['error']}")
        return

    search_id = result.get("searchId", "")
    suppliers = result.get("suppliers", [])
    print(f"  Render 1: {len(suppliers)} suppliers in {time.time()-t0:.1f}s — waiting for enrichment...")

    if search_id:
        suppliers = _poll_until_done(search_id, timeout=120)

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s — {len(suppliers)} suppliers")

    total_issues = 0
    for i, s in enumerate(suppliers, 1):
        name = s.get("name", "?")
        state = s.get("state") or ""
        certs = s.get("certifications") or ""
        years = s.get("yearsInBusiness") or ""
        employees = s.get("employees") or ""
        email = s.get("email") or ""
        match = (s.get("matchReason") or "")[:80]

        flag = "🇺🇸" if state.upper() in US_STATE_ABBRS else "🌍"
        print(f"\n  [{i}] {name}  {flag} {state}")
        print(f"       certs: {certs or '—'}  |  {years or '—'}  {employees or '—'} emp  |  email: {email or '—'}")
        print(f"       match: {match}{'...' if len(s.get('matchReason',''))>80 else ''}")

        issues = _check_supplier(s, region)
        if issues:
            for issue in issues:
                print(f"       ⚠️  {issue}")
            total_issues += len(issues)

    print(f"\n  SUMMARY: {len(suppliers)} suppliers, {total_issues} issues flagged")
    return {"query": query, "region": region, "suppliers": suppliers, "issues": total_issues}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="Single query to test")
    parser.add_argument("--region", default="north_america", choices=["north_america", "global"])
    parser.add_argument("--suite", choices=["all", "na", "global", "india"], help="Run a predefined test suite")
    parser.add_argument("--json-out", help="Write full results to JSON file")
    args = parser.parse_args()

    cases_to_run = []

    if args.query:
        cases_to_run = [(args.query, args.region, "manual")]
    elif args.suite == "all":
        cases_to_run = TEST_CASES
    elif args.suite == "na":
        cases_to_run = [c for c in TEST_CASES if c[1] == "north_america"]
    elif args.suite == "global":
        cases_to_run = [c for c in TEST_CASES if c[1] == "global"]
    elif args.suite == "india":
        cases_to_run = [c for c in TEST_CASES if "india" in c[2].lower() or "IN" in c[2]]
    else:
        # Default: run first 3 cases as a quick smoke test
        cases_to_run = TEST_CASES[:3]

    all_results = []
    for query, region, notes in cases_to_run:
        r = _run_one(query, region, notes)
        if r:
            all_results.append(r)
        time.sleep(1)  # small gap between searches

    # Final tally
    total_issues = sum(r["issues"] for r in all_results)
    print(f"\n{'='*72}")
    print(f"QA COMPLETE — {len(all_results)} searches, {total_issues} total issues flagged")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"Full results written to {args.json_out}")


if __name__ == "__main__":
    main()
