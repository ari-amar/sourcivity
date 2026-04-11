#!/usr/bin/env python3
"""Sourcivity Admin Dashboard — password-protected view of all customer activity."""
import csv
import json
import os
import urllib.request
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "sourcivity2026")
ADMIN_PORT = int(os.environ.get("ADMIN_PORT", "3099"))
CUSTOMERS_DIR = os.environ.get("CUSTOMERS_DIR", "/home/ubuntu/customers")
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))


def _send_json(handler, data, status=200):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(body)


def _check_auth(handler):
    """Check X-Admin-Password header or ?pw= query param."""
    pw = handler.headers.get("X-Admin-Password", "")
    if not pw:
        from urllib.parse import urlparse, parse_qs
        parsed = parse_qs(urlparse(handler.path).query)
        pw = parsed.get("pw", [""])[0]
    return pw == ADMIN_PASSWORD


def _get_all_customers():
    """Scan /opt/customers/ for deployed instances."""
    customers = []
    if not os.path.isdir(CUSTOMERS_DIR):
        return customers
    for slug in sorted(os.listdir(CUSTOMERS_DIR)):
        env_path = os.path.join(CUSTOMERS_DIR, slug, ".env")
        if not os.path.isfile(env_path):
            continue
        info = {"slug": slug}
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if k in ("CUSTOMER_NAME", "CUSTOMER_FULL_NAME", "CUSTOMER_COMPANY",
                             "CUSTOMER_STATE", "CUSTOMER_EMAIL", "SERVE_PORT"):
                        info[k.lower()] = v
        # Check if server is running
        pid_path = os.path.join(CUSTOMERS_DIR, slug, ".pid")
        info["running"] = False
        if os.path.isfile(pid_path):
            try:
                pid = int(open(pid_path).read().strip())
                os.kill(pid, 0)
                info["running"] = True
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        customers.append(info)
    return customers


def _get_activity(slug):
    """Read activity.csv for a customer."""
    csv_path = os.path.join(CUSTOMERS_DIR, slug, "data", "activity.csv")
    rows = []
    if os.path.isfile(csv_path):
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def _get_all_activity():
    """Aggregate activity across all customers."""
    all_activity = []
    if not os.path.isdir(CUSTOMERS_DIR):
        return all_activity
    for slug in sorted(os.listdir(CUSTOMERS_DIR)):
        rows = _get_activity(slug)
        for row in rows:
            row["customer"] = slug
            all_activity.append(row)
    # Sort by timestamp descending
    all_activity.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return all_activity


def _get_quotes_count(slug):
    """Count quotes in a customer's tracker."""
    csv_path = os.path.join(CUSTOMERS_DIR, slug, "data", "quotes", "quote-tracker.csv")
    if not os.path.isfile(csv_path):
        return 0
    with open(csv_path) as f:
        return max(0, sum(1 for _ in f) - 1)  # minus header


_geo_cache = {}  # ip -> {"city": "...", "region": "...", "country": "..."}


def _geolocate_ips(ips):
    """Batch geolocate IPs via ip-api.com. Returns dict of ip -> location string."""
    # Filter out already cached and invalid IPs
    uncached = [ip for ip in set(ips) if ip and ip not in _geo_cache and ip not in ("", "None", "127.0.0.1")]
    if uncached:
        # ip-api.com batch endpoint: POST up to 100 IPs
        for batch_start in range(0, len(uncached), 100):
            batch = uncached[batch_start:batch_start + 100]
            payload = json.dumps([{"query": ip, "fields": "query,city,regionName,country,status"} for ip in batch]).encode()
            req = urllib.request.Request(
                "http://ip-api.com/batch",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    results = json.loads(resp.read())
                for r in results:
                    ip = r.get("query", "")
                    if r.get("status") == "success":
                        parts = [p for p in [r.get("city"), r.get("regionName"), r.get("country")] if p]
                        _geo_cache[ip] = ", ".join(parts)
                    else:
                        _geo_cache[ip] = ""
            except Exception as e:
                print(f"[geo] Batch lookup failed: {e}")
                for ip in batch:
                    _geo_cache[ip] = ""

    return {ip: _geo_cache.get(ip, "") for ip in ips}


class AdminHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/auth":
            if _check_auth(self):
                _send_json(self, {"ok": True})
            else:
                _send_json(self, {"ok": False}, 401)

        elif path == "/api/customers":
            if not _check_auth(self):
                _send_json(self, {"error": "Unauthorized"}, 401)
                return
            customers = _get_all_customers()
            for c in customers:
                c["quotes"] = _get_quotes_count(c["slug"])
                activity = _get_activity(c["slug"])
                c["total_actions"] = len(activity)
                c["searches"] = sum(1 for a in activity if a.get("action") == "search")
                c["rfqs_sent"] = sum(1 for a in activity if a.get("action") == "rfq_send")
                if activity:
                    c["last_active"] = activity[-1].get("timestamp", "")
                else:
                    c["last_active"] = "never"
            _send_json(self, {"customers": customers})

        elif path == "/api/activity":
            if not _check_auth(self):
                _send_json(self, {"error": "Unauthorized"}, 401)
                return
            from urllib.parse import parse_qs, urlparse
            parsed = parse_qs(urlparse(self.path).query)
            slug = parsed.get("customer", [""])[0]
            if slug:
                activity = _get_activity(slug)
                activity.reverse()
                for a in activity:
                    a["customer"] = slug
            else:
                activity = _get_all_activity()
            # Geolocate IPs
            all_ips = [a.get("ip", "") for a in activity]
            geo = _geolocate_ips(all_ips)
            for a in activity:
                a["location"] = geo.get(a.get("ip", ""), "")
            _send_json(self, {"activity": activity})

        else:
            super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/activity/clear":
            if not _check_auth(self):
                _send_json(self, {"error": "Unauthorized"}, 401)
                return
            cleared = 0
            if os.path.isdir(CUSTOMERS_DIR):
                for slug in os.listdir(CUSTOMERS_DIR):
                    csv_path = os.path.join(CUSTOMERS_DIR, slug, "data", "activity.csv")
                    if os.path.isfile(csv_path):
                        os.remove(csv_path)
                        cleared += 1
            _send_json(self, {"ok": True, "cleared": cleared})
        else:
            _send_json(self, {"error": "Not found"}, 404)

    def log_message(self, fmt, *args):
        if "/api/" in self.path:
            super().log_message(fmt, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", ADMIN_PORT), AdminHandler)
    print(f"Admin dashboard at http://localhost:{ADMIN_PORT}")
    print(f"Password: {ADMIN_PASSWORD}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
