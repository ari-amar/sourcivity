"""Search timing benchmark — mocks network/LLM and times the orchestration pipeline.

Use this to verify that reliability changes don't add measurable latency to the
happy path. Network calls (Brave, LLM, scraper) are stubbed with instant returns,
so this isolates pure CPU/parsing/threading cost.

Usage (no API keys needed):
    python3 tests/test_search_timing.py
    python3 tests/test_search_timing.py --iters 50
"""
import argparse
import os
import statistics
import sys
import time

# Stub env vars so config.py imports without real keys
os.environ.setdefault("CEREBRAS_API_KEY", "stub")
os.environ.setdefault("BRAVE_API_KEY", "stub")
os.environ.setdefault("GMAIL_ADDRESS", "stub@example.com")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import brave, llm, scraper  # noqa: E402
from handlers import search as search_handler  # noqa: E402


_LLM_FIRST_PASS_RESPONSE = """```json
[
  {"name": "Acme Aerospace", "state": "CA", "products": "Titanium Fasteners",
   "certifications": "AS9100, ISO 9001", "website": "https://acme-aero.com",
   "email": "", "yearsInBusiness": "37 yrs (est. 1988)", "employees": "250", "revenue": "$45M"},
  {"name": "Beta Components", "state": "OH", "products": "Aerospace Bolts",
   "certifications": "AS9100", "website": "https://beta-comp.com",
   "email": "sales@beta-comp.com", "yearsInBusiness": "", "employees": "", "revenue": ""},
  {"name": "Gamma Manufacturing", "state": "TX", "products": "Custom Fasteners",
   "certifications": "ISO 9001, ITAR", "website": "https://gamma-mfg.com",
   "email": "", "yearsInBusiness": "20 yrs (est. 2005)", "employees": "80", "revenue": "$15M"},
  {"name": "Delta Industrial", "state": "PA", "products": "Precision Hardware",
   "certifications": "ISO 9001", "website": "https://delta-ind.com",
   "email": "", "yearsInBusiness": "", "employees": "120", "revenue": ""},
  {"name": "Epsilon Specialty", "state": "MI", "products": "Specialty Fasteners",
   "certifications": "AS9100, NADCAP", "website": "https://epsilon-spec.com",
   "email": "", "yearsInBusiness": "45 yrs (est. 1980)", "employees": "300", "revenue": "$60M"}
]
```"""

_LLM_MATCH_REASONS_RESPONSE = """```json
[
  {"name": "Acme Aerospace", "matchReason": "AS9100-certified, 250 employees, 37 yrs in aerospace fastener manufacturing."},
  {"name": "Beta Components", "matchReason": "AS9100-certified specialist in aerospace bolts."},
  {"name": "Gamma Manufacturing", "matchReason": "ISO 9001 + ITAR registered, 80 employees, defense-capable."},
  {"name": "Delta Industrial", "matchReason": "ISO 9001 with 120 employees; no aerospace-specific cert listed."},
  {"name": "Epsilon Specialty", "matchReason": "AS9100 + NADCAP, 300 employees, 45 yrs in specialty fasteners."}
]
```"""


def _stub_brave_search(query, count=10, region='north_america'):
    results = [
        {"title": f"Acme Aerospace - Titanium Fasteners", "url": "https://acme-aero.com",
         "description": "Acme Aerospace makes AS9100-certified titanium fasteners since 1988.",
         "extra_snippets": ["Founded 1988", "250 employees", "ISO 9001 + AS9100 certified"],
         "page_age": "", "profile_name": ""},
        {"title": f"Beta Components Inc", "url": "https://beta-comp.com",
         "description": "Beta Components - aerospace bolts and fasteners, AS9100.",
         "extra_snippets": ["Aerospace certified", "Ohio HQ"], "page_age": "", "profile_name": ""},
        {"title": f"Gamma Manufacturing", "url": "https://gamma-mfg.com",
         "description": "Custom fasteners for defense — ITAR registered.",
         "extra_snippets": ["Texas-based", "Founded 2005", "80 employees"],
         "page_age": "", "profile_name": ""},
    ]
    faq = [
        {"question": "When was Acme Aerospace founded?", "answer": "Acme was founded in 1988.",
         "url": "https://acme-aero.com"},
        {"question": "How many employees does Acme have?", "answer": "Acme has 250 employees.",
         "url": "https://acme-aero.com"},
    ]
    infobox = None
    return results, faq, infobox


_llm_call_count = {"n": 0}


def _stub_call_llm(system, message, model=None, max_tokens=4096):
    _llm_call_count["n"] += 1
    if "matchReason" in system or "blunt" in system.lower():
        return _LLM_MATCH_REASONS_RESPONSE
    return _LLM_FIRST_PASS_RESPONSE


def _stub_enrich_suppliers(suppliers, on_each=None, skip_email=False):
    for i, s in enumerate(suppliers):
        if on_each:
            try:
                on_each(i, s)
            except Exception:
                pass
    return suppliers


def install_stubs():
    brave.search = _stub_brave_search
    llm.call_llm = _stub_call_llm
    scraper.enrich_suppliers = _stub_enrich_suppliers
    scraper.get_blocked_sites = lambda: []
    scraper._blocked_sites = []


def _wait_for_done(search_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = search_handler.get_status(search_id)
        if st.get("status") == "done":
            return st
        time.sleep(0.005)
    return search_handler.get_status(search_id)


def time_one_search(query="titanium fasteners", region="north_america"):
    _llm_call_count["n"] = 0
    t0 = time.perf_counter()
    res = search_handler.handle(query, skip_enrichment=False, region=region)
    sync_elapsed = time.perf_counter() - t0
    sid = res.get("searchId")
    if sid:
        _wait_for_done(sid, timeout=10)
    total_elapsed = time.perf_counter() - t0
    return sync_elapsed, total_elapsed, len(res.get("suppliers", []))


def run_benchmark(iters=20):
    install_stubs()

    # NA-only so all iterations exercise the full pipeline (global with US-only
    # stub suppliers would fast-fail and skew timings).
    queries = [
        ("titanium fasteners", "north_america"),
        ("ceramic bearings", "north_america"),
        ("hydraulic seals polyurethane", "north_america"),
        ("Hastelloy C276 round bar", "north_america"),
    ]

    # Warm-up — first call has Python import/JIT-ish overhead
    time_one_search(*queries[0])

    sync_times = []
    total_times = []
    supplier_counts = []
    for i in range(iters):
        q, r = queries[i % len(queries)]
        sync, total, n = time_one_search(q, r)
        sync_times.append(sync * 1000)
        total_times.append(total * 1000)
        supplier_counts.append(n)

    def stats(samples):
        return {
            "mean": statistics.mean(samples),
            "median": statistics.median(samples),
            "p95": sorted(samples)[int(len(samples) * 0.95) - 1] if len(samples) > 1 else samples[0],
            "min": min(samples),
            "max": max(samples),
        }

    print(f"\n=== Search timing benchmark ({iters} iterations, network mocked) ===")
    print(f"Suppliers per call (mean): {statistics.mean(supplier_counts):.1f}")
    s_sync = stats(sync_times)
    s_total = stats(total_times)
    print(f"\nSync portion (handle() return):")
    print(f"  mean={s_sync['mean']:.2f}ms  median={s_sync['median']:.2f}ms  "
          f"p95={s_sync['p95']:.2f}ms  min={s_sync['min']:.2f}ms  max={s_sync['max']:.2f}ms")
    print(f"\nTotal (incl. background enrichment):")
    print(f"  mean={s_total['mean']:.2f}ms  median={s_total['median']:.2f}ms  "
          f"p95={s_total['p95']:.2f}ms  min={s_total['min']:.2f}ms  max={s_total['max']:.2f}ms")
    return {"sync": s_sync, "total": s_total}


def smoke_test_failure_paths():
    """Failure-path smoke checks: each prints PASS/FAIL based on whether
    reliability improvements have shipped."""
    install_stubs()

    # 1) Transient brave failure on a single parallel query — should still succeed
    #    (this works in the baseline because 2 of 3 queries return data).
    call_count = {"n": 0}
    original = brave.search

    def flaky_single(q, count=10, region='north_america'):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return [], [], None
        return original(q, count, region)

    brave.search = flaky_single
    res = search_handler.handle("titanium fasteners", region="north_america")
    print(f"[smoke] 1-of-3 brave failure: {len(res.get('suppliers', []))} suppliers "
          f"({'PASS' if res.get('suppliers') else 'FAIL'})")
    brave.search = original

    # 2) HTTP-layer transient failure inside brave.search — retry inside brave.py
    #    should resolve a single 503/timeout. Bypasses the stubs and patches urlopen.
    import io
    import json as _json
    import urllib.request as _ureq
    fake_response_payload = _json.dumps({
        "web": {"results": [{"title": "Acme", "url": "https://acme-aero.com",
                              "description": "Acme aerospace", "extra_snippets": [],
                              "page_age": "", "profile": {}}]},
        "faq": {"results": []},
        "infobox": {"results": []},
    }).encode()

    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload
        def read(self):
            return self._payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    urlopen_calls = {"n": 0}
    real_urlopen = _ureq.urlopen

    def flaky_urlopen(req, timeout=15):
        urlopen_calls["n"] += 1
        if urlopen_calls["n"] == 1:
            import urllib.error
            raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, io.BytesIO(b''))
        return _FakeResp(fake_response_payload)

    # Reset brave.search to the real implementation so retry runs
    import importlib
    importlib.reload(brave)
    _ureq.urlopen = flaky_urlopen
    try:
        results, _, _ = brave.search("test query")
    finally:
        _ureq.urlopen = real_urlopen

    print(f"[smoke] brave HTTP 503 retry: {len(results)} results, "
          f"{urlopen_calls['n']} HTTP attempts "
          f"({'PASS' if results and urlopen_calls['n'] == 2 else 'FAIL — needs HTTP retry'})")

    # Re-install stubs after reload
    install_stubs()

    # 3) BOTH LLM calls return truncated JSON — only truncation recovery in
    #    _parse_suppliers can salvage the 2 complete supplier objects.
    truncated = ('```json\n[\n'
                 '  {"name": "Acme", "state": "CA", "products": "Bolts",'
                 ' "certifications": "ISO 9001", "website": "https://acme.com",'
                 ' "email": "", "yearsInBusiness": "", "employees": "", "revenue": ""},\n'
                 '  {"name": "Beta", "state": "OH", "products": "Nuts",'
                 ' "certifications": "AS9100", "website": "https://beta.com",'
                 ' "email": "", "yearsInBusiness": "", "employees": "", "revenue": ""},\n'
                 '  {"name": "Gamma", "state": "TX",')

    def all_truncated(system, message, model=None, max_tokens=4096):
        if "matchReason" in system or "blunt" in system.lower():
            return _LLM_MATCH_REASONS_RESPONSE
        return truncated

    llm.call_llm = all_truncated
    res = search_handler.handle("hydraulic seals", region="north_america")
    n = len(res.get("suppliers", []))
    print(f"[smoke] both LLM calls truncated: {n} suppliers "
          f"({'PASS' if n >= 2 else 'FAIL — needs truncation recovery'})")
    llm.call_llm = _stub_call_llm

    # 4) LLM returns a single supplier as a bare object (not array)
    def single_dict_llm(system, message, model=None, max_tokens=4096):
        if "matchReason" in system or "blunt" in system.lower():
            return _LLM_MATCH_REASONS_RESPONSE
        return ('```json\n{"name": "Solo", "state": "CA", "products": "Things",'
                ' "certifications": "ISO 9001", "website": "https://solo.com",'
                ' "email": "", "yearsInBusiness": "", "employees": "", "revenue": ""}\n```')

    llm.call_llm = single_dict_llm
    res = search_handler.handle("widgets", region="north_america")
    n = len(res.get("suppliers", []))
    print(f"[smoke] LLM returns dict not array: {n} suppliers "
          f"({'PASS' if n == 1 else 'FAIL — needs dict-coercion in _parse_suppliers'})")
    llm.call_llm = _stub_call_llm

    # 5) LLM returns duplicate suppliers — dedup must collapse them
    def dup_llm(system, message, model=None, max_tokens=4096):
        if "matchReason" in system or "blunt" in system.lower():
            return _LLM_MATCH_REASONS_RESPONSE
        return ('```json\n[\n'
                '  {"name": "Acme", "state": "CA", "products": "Bolts",'
                ' "certifications": "ISO 9001", "website": "https://acme.com",'
                ' "email": "", "yearsInBusiness": "", "employees": "", "revenue": ""},\n'
                '  {"name": "ACME", "state": "CA", "products": "Bolts",'
                ' "certifications": "ISO 9001", "website": "https://acme.com",'
                ' "email": "", "yearsInBusiness": "", "employees": "", "revenue": ""}\n'
                ']\n```')

    llm.call_llm = dup_llm
    res = search_handler.handle("widgets", region="north_america")
    n = len(res.get("suppliers", []))
    print(f"[smoke] duplicate suppliers: {n} suppliers "
          f"({'PASS' if n == 1 else 'FAIL — needs dedup-by-name'})")
    llm.call_llm = _stub_call_llm

    # 6) _country_from_tld — URL with a path
    country = search_handler._country_from_tld("https://example.co.in/about-us")
    print(f"[smoke] tld lookup w/ path: {country!r} "
          f"({'PASS' if country == 'India' else 'FAIL — needs domain-only parse'})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--smoke", action="store_true", help="Run failure-path smoke checks")
    args = parser.parse_args()

    if args.smoke:
        smoke_test_failure_paths()
        return

    run_benchmark(args.iters)


if __name__ == "__main__":
    main()
