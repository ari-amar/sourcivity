#!/usr/bin/env python3
"""Sourcivity hybrid backend — direct Python + LLM for known workflows, agent fallback for the rest."""
import csv
import json
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from urllib.parse import urlparse, parse_qs

from config import SERVE_PORT, EMAIL_ADDRESS, CUSTOMER_NAME, CUSTOMER_COMPANY, WORKSPACE_DIR, DEMO_MODE
from services import csv_store, scraper
from handlers import search, rfq, inbox, compare

if DEMO_MODE:
    FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend-demo")
else:
    FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

# --- Demo rate limiting (IP-based, 5 searches/hour) ---
_demo_rate = {}  # { ip: [timestamps] }
DEMO_RATE_LIMIT = 5
DEMO_RATE_WINDOW = 3600
DEMO_RATE_WHITELIST = ("2607:fb91:", "2607:fb90:e917:83c3:", "2607:fb90:62b7:8869:", "172.56.")  # IP prefixes exempt from rate limiting
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",")  # comma-separated allowed origins

# --- Activity logging ---
ACTIVITY_CSV = os.path.join(WORKSPACE_DIR, "activity.csv")
_activity_lock = threading.Lock()


def log_activity(action, detail="", ip="", referrer="", device="", extra=""):
    """Append one row to activity.csv (thread-safe)."""
    with _activity_lock:
        write_header = not os.path.exists(ACTIVITY_CSV)
        with open(ACTIVITY_CSV, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["timestamp", "action", "detail", "ip", "referrer", "device", "extra"])
            w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        action, detail, ip, referrer, device, extra])


def _get_real_ip(handler):
    """Get real client IP — only trust CF-Connecting-IP (set by Cloudflare, not spoofable by clients)."""
    return (handler.headers.get("CF-Connecting-IP")
            or handler.client_address[0])


def _get_referrer(handler):
    """Return cleaned referrer domain, or 'direct'."""
    ref = handler.headers.get("Referer", "").strip()
    if not ref:
        return "direct"
    try:
        parsed = urlparse(ref)
        return parsed.netloc or ref[:100]
    except Exception:
        return ref[:100]


def _get_device(handler):
    """Return 'mobile', 'tablet', or 'desktop' from User-Agent."""
    ua = handler.headers.get("User-Agent", "").lower()
    if "tablet" in ua or "ipad" in ua:
        return "tablet"
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    return "desktop"


def _read_body(handler):
    """Read and parse JSON request body."""
    length = int(handler.headers.get("Content-Length", 0))
    raw = handler.rfile.read(length)
    return json.loads(raw) if raw else {}


def _check_origin(handler):
    """Return the origin if allowed, else empty string."""
    origin = handler.headers.get("Origin", "")
    if not origin:
        return ""  # same-origin requests have no Origin header
    if any(o.strip() for o in ALLOWED_ORIGINS if o.strip() and origin.startswith(o.strip())):
        return origin
    return ""


def _send_json(handler, data, status=200):
    """Send a JSON response with CORS headers."""
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    origin = _check_origin(handler)
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
    handler.end_headers()
    handler.wfile.write(body)


class AppHandler(SimpleHTTPRequestHandler):
    """Serves static files + API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/health":
            _send_json(self, {"ok": True, "demo": DEMO_MODE})
            return
        elif self.path == "/api/config":
            email_configured = bool(EMAIL_ADDRESS and not EMAIL_ADDRESS.startswith("__"))
            _send_json(self, {
                "customer_name": CUSTOMER_NAME,
                "customer_company": CUSTOMER_COMPANY,
                "email_configured": email_configured
            })
        elif self.path == "/api/quotes":
            try:
                quotes, warnings = csv_store.read_quotes()
                resp = {"quotes": quotes}
                if warnings:
                    resp["warnings"] = warnings
                _send_json(self, resp)
            except Exception as e:
                print(f"[quotes] Error: {e}")
                _send_json(self, {"error": "Failed to load quotes"}, 500)
        elif self.path.startswith("/api/search/status"):
            parsed = parse_qs(urlparse(self.path).query)
            search_id = parsed.get("id", [""])[0]
            if not search_id:
                _send_json(self, {"error": "Missing id"}, 400)
                return
            result = search.get_status(search_id)
            _send_json(self, result)
        else:
            super().do_GET()

    def do_POST(self):
        try:
            data = _read_body(self)
        except (json.JSONDecodeError, ValueError):
            _send_json(self, {"error": "Invalid JSON"}, 400)
            return

        # --- Demo mode: block restricted endpoints ---
        if DEMO_MODE and self.path in ("/api/rfq/draft", "/api/rfq/send",
                                        "/api/rfq/batch-draft", "/api/rfq/batch-send",
                                        "/api/enrich",
                                        "/api/inbox/check", "/api/browser/detect-forms",
                                        "/api/browser/autofill", "/api/browser/fill-form",
                                        "/api/quotes/compare"):
            _send_json(self, {"error": "This feature is not available in demo mode. Contact ari@sourcivity.io for full access."}, 403)
            return

        if self.path == "/api/search":
            query = data.get("query", "").strip()[:500]
            if not query:
                _send_json(self, {"error": "Missing query"}, 400)
                return

            # Demo rate limiting
            if DEMO_MODE:
                import time as _time
                ip = _get_real_ip(self)
                whitelisted = any(ip.startswith(prefix) for prefix in DEMO_RATE_WHITELIST)
                now = _time.time()
                hits = _demo_rate.get(ip, [])
                hits = [t for t in hits if now - t < DEMO_RATE_WINDOW]
                if not whitelisted and len(hits) >= DEMO_RATE_LIMIT:
                    _send_json(self, {"error": "Rate limit reached — 5 searches per hour on demo. Contact ari@sourcivity.io for full access."}, 429)
                    return
                hits.append(now)
                _demo_rate[ip] = hits

            ip = _get_real_ip(self)
            result = search.handle(query, skip_enrichment=DEMO_MODE)
            count = len(result.get("suppliers", [])) if isinstance(result, dict) else 0
            log_activity("search", query, ip, _get_referrer(self), _get_device(self), f"results:{count}")
            _send_json(self, result)

        elif self.path == "/api/enrich":
            suppliers = data.get("suppliers", [])
            scraper._blocked_sites.clear()
            enriched = scraper.enrich_suppliers(suppliers)
            blocked = scraper.get_blocked_sites()
            _send_json(self, {"suppliers": enriched, "blocked": blocked})

        elif self.path == "/api/rfq/draft":
            supplier = data.get("supplier", {})
            part = data.get("part", "")
            qty = data.get("qty", "")
            notes = data.get("notes", "")
            if not part:
                _send_json(self, {"error": "Missing part"}, 400)
                return
            log_activity("rfq_draft", f"{supplier.get('name', '?')} - {part}", _get_real_ip(self), _get_referrer(self), _get_device(self))
            result = rfq.handle_draft(supplier, part, qty, notes)
            _send_json(self, result)

        elif self.path == "/api/rfq/batch-draft":
            suppliers = data.get("suppliers", [])
            part = data.get("part", "")
            qty = data.get("qty", "")
            notes = data.get("notes", "")
            if not part or not suppliers:
                _send_json(self, {"error": "Missing part or suppliers"}, 400)
                return
            log_activity("rfq_batch_draft", f"{len(suppliers)} suppliers - {part}", _get_real_ip(self), _get_referrer(self), _get_device(self))
            result = rfq.handle_batch_draft(suppliers, part, qty, notes)
            _send_json(self, result)

        elif self.path == "/api/rfq/batch-send":
            items = data.get("items", [])
            if not items:
                _send_json(self, {"error": "Missing items"}, 400)
                return
            log_activity("rfq_batch_send", f"{len(items)} emails", _get_real_ip(self), _get_referrer(self), _get_device(self))
            result = rfq.handle_batch_send(items)
            _send_json(self, result)

        elif self.path == "/api/rfq/send":
            supplier = data.get("supplier", {})
            email_text = data.get("email_text", "")
            part = data.get("part", "")
            category = data.get("category", "")
            if not email_text:
                _send_json(self, {"error": "Missing email_text"}, 400)
                return
            try:
                log_activity("rfq_send", f"{supplier.get('name', '?')} - {part}", _get_real_ip(self), _get_referrer(self), _get_device(self))
                result = rfq.handle_send(supplier, email_text, part, category)
                _send_json(self, result)
            except Exception as e:
                print(f"[rfq] Send error: {e}")
                _send_json(self, {"success": False, "error": "Failed to send RFQ. Please try again."}, 500)

        elif self.path == "/api/inbox/check":
            result = inbox.handle()
            _send_json(self, result)

        elif self.path == "/api/browser/detect-forms":
            url = data.get("url", "")
            if not url:
                _send_json(self, {"error": "Missing url"}, 400)
                return
            forms = scraper.detect_forms(url)
            _send_json(self, {"forms": forms})

        elif self.path == "/api/browser/autofill":
            fields = data.get("fields", [])
            supplier = data.get("supplier", {})
            part = data.get("part", "")
            qty = data.get("qty", "")
            notes = data.get("notes", "")
            from services import llm
            import json as _json
            field_desc = _json.dumps(fields, indent=2)
            from config import CUSTOMER_FULL_NAME, CUSTOMER_COMPANY, CUSTOMER_TITLE, CUSTOMER_STATE
            from config import EMAIL_ADDRESS as _CUST_EMAIL
            system = f"""You are filling out a supplier contact form on behalf of {CUSTOMER_FULL_NAME}, a procurement professional.

Details:
- Name: {CUSTOMER_FULL_NAME}
- Email: {_CUST_EMAIL}
- Company: {CUSTOMER_COMPANY}
- Phone: (leave blank if not required)
- Job Title: {CUSTOMER_TITLE}
- Country: United States
- State: {CUSTOMER_STATE}

Generate a value for EVERY field. For message/inquiry/comment fields, write a short professional RFQ message based on the part and quantity context provided. Keep the message natural and concise — 2-3 sentences, plain text, no markdown.

For dropdown/select fields, pick the most appropriate option from the field's context (e.g. "General Inquiry" or "Request a Quote" for inquiry type).

For any field you truly cannot determine, use a reasonable default rather than leaving it blank.

Return ONLY valid JSON: {"field_name": "value", ...} where field_name matches the name property of each field."""

            message = f"""Form fields:
{field_desc}

Supplier: {supplier.get('name', 'Unknown')}
Part/Service needed: {part}
Quantity: {qty or 'please advise'}
Additional notes: {notes or 'none'}"""

            try:
                result = llm.extract_json(message, system)
                _send_json(self, {"values": result})
            except Exception as e:
                print(f"[autofill] Error: {e}")
                _send_json(self, {"values": {}, "error": "Failed to generate form values"})

        elif self.path == "/api/browser/fill-form":
            url = data.get("url", "")
            form_index = data.get("form_index", 0)
            fields = data.get("fields", {})
            if not url:
                _send_json(self, {"error": "Missing url"}, 400)
                return
            result = scraper.fill_form(url, form_index, fields)
            _send_json(self, result)

        elif self.path == "/api/quotes/compare":
            category = data.get("category")
            part = data.get("part")
            recommend = data.get("recommend", False)
            log_activity("compare", f"{category} - {part}", _get_real_ip(self), _get_referrer(self), _get_device(self))
            result = compare.handle(category, part, recommend)
            _send_json(self, result)

        else:
            _send_json(self, {"error": "Not found"}, 404)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        origin = _check_origin(self)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Only log API calls and errors
        if "/api/" in self.path or (len(args) > 1 and str(args[1]) != "200"):
            super().log_message(format, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in threads so long-running requests don't block others."""
    daemon_threads = True


INBOX_POLL_INTERVAL = 15 * 60  # 15 minutes


def _inbox_poller():
    """Background thread: periodically check inbox for quote replies (non-demo only)."""
    import time
    while True:
        time.sleep(INBOX_POLL_INTERVAL)
        try:
            result = inbox.handle()
            if result.get("processed", 0) > 0:
                print(f"[inbox-poll] Processed {result['processed']} reply(s): "
                      + ", ".join(r['supplier'] for r in result.get('results', [])))
        except Exception as e:
            print(f"[inbox-poll] Error: {e}")


if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", SERVE_PORT), AppHandler)
    print(f"Sourcivity running at http://localhost:{SERVE_PORT}")
    print(f"Handlers: search, rfq, inbox, compare")
    print(f"Complex tasks: Telegram → OpenClaw agent")

    if not DEMO_MODE:
        t = threading.Thread(target=_inbox_poller, daemon=True, name="inbox-poller")
        t.start()
        print(f"Inbox auto-poll: every {INBOX_POLL_INTERVAL // 60} minutes")

    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
