"""Brave Search API wrapper — extracts web results, FAQ, infobox, and extra snippets."""
import re
import urllib.request
import urllib.parse
import urllib.error
import json
from config import BRAVE_API_KEY


def _strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text) if text else ''


def search(query, count=10, region='north_america'):
    """Search Brave and return (results, faq, infobox).

    results: list of {title, url, description, extra_snippets, page_age, profile_name}
    faq: list of {question, answer, url} — company facts (founded, employees, revenue)
    infobox: dict with {title, description, long_desc, attributes} or None
    """
    country = 'us' if region == 'north_america' else 'all'
    params = urllib.parse.urlencode({"q": query[:500], "count": count, "country": country, "search_lang": "en"})
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        print(f"[brave] HTTP {e.code} from Brave API")
        raise RuntimeError(f"Brave API HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"[brave] Network error: {e}")
        raise RuntimeError(f"Brave API network error: {e}") from e

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print("[brave] Malformed JSON response from Brave API")
        raise RuntimeError("Brave API malformed JSON response")

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
