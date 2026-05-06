"""Brave Search API wrapper — extracts web results, FAQ, infobox, and extra snippets."""
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import json
from config import BRAVE_API_KEY


def _strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text) if text else ''


# Retry transient failures only (network, timeout, 5xx). 4xx is not retried —
# auth/quota/rate-limit problems won't resolve in 250ms. 429 in particular
# almost always recurs on the second attempt, so retrying just doubles latency.
_TRANSIENT_HTTP_CODES = {500, 502, 503, 504}

# Second attempt uses a tighter timeout so a hung connection can't double
# total wall-clock time (the slowest of 3 parallel queries determines latency).
_RETRY_TIMEOUT = 5


def _fetch(url, headers, timeout, attempt):
    """Single HTTP attempt. Returns (raw_bytes, retriable_error_or_none)."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), None
    except urllib.error.HTTPError as e:
        if e.code in _TRANSIENT_HTTP_CODES:
            return None, f"HTTP {e.code}"
        print(f"[brave] HTTP {e.code} from Brave API (attempt {attempt})")
        return None, False  # non-retriable
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, f"network: {type(e).__name__}"


def search(query, count=10, region='north_america'):
    """Search Brave and return (results, faq, infobox).

    Retries once on transient errors (5xx / timeouts / network glitches) with a
    short backoff. Single-failure recovery materially improves reliability when
    one of three parallel queries hits an intermittent error.

    results: list of {title, url, description, extra_snippets, page_age, profile_name}
    faq: list of {question, answer, url} — company facts (founded, employees, revenue)
    infobox: dict with {title, description, long_desc, attributes} or None
    """
    country = 'us' if region == 'north_america' else 'all'
    params = urllib.parse.urlencode({"q": query[:500], "count": count, "country": country, "search_lang": "en"})
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }

    raw = None
    for attempt in (1, 2):
        timeout = 15 if attempt == 1 else _RETRY_TIMEOUT
        raw, err = _fetch(url, headers, timeout=timeout, attempt=attempt)
        if raw is not None:
            break
        if err is False:
            return [], [], None  # non-retriable HTTP error already logged
        if attempt == 1:
            time.sleep(0.25)
            continue
        print(f"[brave] {err} after {attempt} attempts — giving up")
        return [], [], None

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print("[brave] Malformed JSON response from Brave API")
        return [], [], None

    # Web results with extra data
    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": _strip_html(item.get("description", "")),
            "extra_snippets": [_strip_html(s) for s in item.get("extra_snippets", [])],
            "page_age": item.get("page_age", ""),
            "profile_name": item.get("profile", {}).get("name", ""),
        })

    # FAQ — structured Q&A (founded year, employee count, revenue, etc.)
    faq = []
    for item in data.get("faq", {}).get("results", []):
        faq.append({
            "question": _strip_html(item.get("question", "")),
            "answer": _strip_html(item.get("answer", "")),
            "url": item.get("url", ""),
        })

    # Infobox / knowledge panel
    infobox = None
    infobox_results = data.get("infobox", {}).get("results", [])
    if infobox_results:
        ib = infobox_results[0]
        infobox = {
            "title": ib.get("title", ""),
            "description": _strip_html(ib.get("description", "")),
            "long_desc": _strip_html(ib.get("long_desc", "")),
            "attributes": [[a[0], _strip_html(a[1])] for a in ib.get("attributes", []) if len(a) >= 2],
        }

    return results, faq, infobox
