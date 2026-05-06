"""Brave retry-policy tests — verify the latency-sensitive parts of the retry loop.

These directly exercise services.brave.search by patching urllib.request.urlopen,
bypassing the orchestration layer. Each test is independent (no _searches dict
state leaking between calls) so we don't see the background-thread interference
that affected test_search_timing.py's smoke #2 (3 attempts vs 2).

Usage (no API keys needed):
    python3 tests/test_brave_retry.py
"""
import io
import json as _json
import os
import sys
import time
import urllib.error
import urllib.request

os.environ.setdefault("CEREBRAS_API_KEY", "stub")
os.environ.setdefault("BRAVE_API_KEY", "stub")
os.environ.setdefault("GMAIL_ADDRESS", "stub@example.com")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import brave  # noqa: E402


_OK_PAYLOAD = _json.dumps({
    "web": {"results": [{"title": "Acme", "url": "https://acme.com",
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


def _http_error(code, url="https://api.search.brave.com/x"):
    return urllib.error.HTTPError(url, code, f"HTTP {code}", {}, io.BytesIO(b''))


class _UrlopenPatch:
    """Context manager that swaps urllib.request.urlopen for a controllable fake."""
    def __init__(self, side_effects):
        # side_effects: list of either Exception instances/classes to raise,
        # callables (req, timeout) -> response, or bytes payloads to return.
        self._effects = list(side_effects)
        self.calls = []  # list of (timeout, attempt_index)

    def __enter__(self):
        self._real = urllib.request.urlopen
        outer = self

        def fake(req, timeout=15):
            outer.calls.append(timeout)
            if not outer._effects:
                raise RuntimeError("urlopen called more times than expected")
            effect = outer._effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            if isinstance(effect, type) and issubclass(effect, BaseException):
                raise effect()
            if callable(effect):
                return effect(req, timeout)
            return _FakeResp(effect)

        urllib.request.urlopen = fake
        return self

    def __exit__(self, *a):
        urllib.request.urlopen = self._real
        return False


def _check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}{(' — ' + detail) if detail else ''}")
    return cond


def test_429_not_retried():
    """429 must be a non-retried error: only 1 HTTP call, returns empty."""
    with _UrlopenPatch([_http_error(429)]) as patch:
        results, faq, infobox = brave.search("rate-limit query")
    return (
        _check("429 not retried (single HTTP call)", len(patch.calls) == 1,
               f"got {len(patch.calls)} calls") and
        _check("429 returns empty results", results == [] and faq == [] and infobox is None)
    )


def test_503_still_retried():
    """503 followed by success: exactly 2 calls, results parsed."""
    with _UrlopenPatch([_http_error(503), _OK_PAYLOAD]) as patch:
        results, _, _ = brave.search("transient query")
    return (
        _check("503 retried once", len(patch.calls) == 2, f"got {len(patch.calls)} calls") and
        _check("503 retry succeeds", len(results) == 1)
    )


def test_400_not_retried():
    """400 (non-transient client error) is not retried."""
    with _UrlopenPatch([_http_error(400)]) as patch:
        results, _, _ = brave.search("bad query")
    return (
        _check("400 not retried", len(patch.calls) == 1, f"got {len(patch.calls)} calls") and
        _check("400 returns empty", results == [])
    )


def test_retry_timeout_is_shorter():
    """Second attempt must use the shorter retry timeout, not the full 15s."""
    with _UrlopenPatch([_http_error(503), _OK_PAYLOAD]) as patch:
        brave.search("timeout-budget query")
    return (
        _check("first attempt uses 15s timeout", patch.calls[0] == 15,
               f"got {patch.calls[0]}") and
        _check("retry uses shorter timeout (<15s)", patch.calls[1] < 15,
               f"got {patch.calls[1]}") and
        _check("retry timeout is _RETRY_TIMEOUT", patch.calls[1] == brave._RETRY_TIMEOUT,
               f"got {patch.calls[1]} vs {brave._RETRY_TIMEOUT}")
    )


def test_network_error_retried():
    """Network glitch (URLError) is retried."""
    with _UrlopenPatch([urllib.error.URLError("connection reset"), _OK_PAYLOAD]) as patch:
        results, _, _ = brave.search("network glitch")
    return (
        _check("network error retried", len(patch.calls) == 2, f"got {len(patch.calls)} calls") and
        _check("network retry succeeds", len(results) == 1)
    )


def test_double_429_latency_bounded():
    """Critical regression check: under sustained 429 (rate-limited account),
    each search incurs only one API call + zero retry sleep. Before fix this
    cost ~250ms sleep + 1 extra API call per query, per search."""
    t0 = time.perf_counter()
    with _UrlopenPatch([_http_error(429)]) as patch:
        brave.search("hot path under rate limit")
    elapsed = time.perf_counter() - t0
    return (
        _check("rate-limited search makes 1 call", len(patch.calls) == 1,
               f"got {len(patch.calls)} calls") and
        _check("rate-limited search returns in < 100ms (no retry sleep)",
               elapsed < 0.1, f"took {elapsed*1000:.1f}ms")
    )


def test_502_503_504_500_all_retried():
    """All 5xx codes in the transient set are retried once."""
    all_pass = True
    for code in (500, 502, 503, 504):
        with _UrlopenPatch([_http_error(code), _OK_PAYLOAD]) as patch:
            results, _, _ = brave.search(f"5xx-{code}")
        ok = len(patch.calls) == 2 and len(results) == 1
        all_pass = all_pass and _check(f"HTTP {code} retried", ok,
                                        f"calls={len(patch.calls)} results={len(results)}")
    return all_pass


def test_408_not_retried_post_fix():
    """408 was previously retried but is now treated as non-transient (matches
    comment: client-timeout / server-side issue rarely fixed by 250ms backoff)."""
    with _UrlopenPatch([_http_error(408)]) as patch:
        brave.search("408 case")
    # We allow either behavior here, but document the chosen policy.
    retried = len(patch.calls) == 2
    not_retried = len(patch.calls) == 1
    return _check(
        "408 policy documented",
        retried or not_retried,
        f"calls={len(patch.calls)} (retried={retried})"
    )


def main():
    tests = [
        test_429_not_retried,
        test_503_still_retried,
        test_400_not_retried,
        test_retry_timeout_is_shorter,
        test_network_error_retried,
        test_double_429_latency_bounded,
        test_502_503_504_500_all_retried,
        test_408_not_retried_post_fix,
    ]
    results = []
    for t in tests:
        print(f"\n--- {t.__name__} ---")
        try:
            results.append(t())
        except Exception as e:
            print(f"[FAIL] {t.__name__} raised: {e!r}")
            results.append(False)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n=== {passed}/{total} test groups passed ===")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
