"""Email extraction engine with 14 anti-obfuscation methods + Playwright fallback.
Copied from openclaw-workspace/frontend/server.py with Playwright addition."""
import base64
import codecs
import concurrent.futures
import html as html_mod
import re
import ssl
import urllib.parse
import urllib.request

# Reusable SSL context that doesn't verify certs (many industrial sites have bad certs)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
CONTACT_HREF_RE = re.compile(
    r'href=["\']([^"\']*(?:contact|quote|rfq|inquir|request|get-in-touch|reach-us)[^"\']*)["\']',
    re.IGNORECASE
)
JUNK_EMAILS = {'example.com', 'sentry.io', 'yourcompany.com', 'domain.com', 'email.com',
               'wixpress.com', 'w3.org', 'schema.org', 'googleapis.com', 'google.com',
               'facebook.com', 'twitter.com', 'cloudflare.com'}

_BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'identity',
    'Cache-Control': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

_blocked_sites = []


def get_blocked_sites():
    """Return list of sites that returned 403/Cloudflare blocks."""
    return list(_blocked_sites)


def _fetch_page(url, timeout=8):
    """Fetch a URL and return its HTML text. Returns '' on failure."""
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
            html = resp.read(500_000).decode('utf-8', errors='ignore')
            if 'cf-mitigated' in str(resp.headers) or 'Just a moment...' in html[:500]:
                _blocked_sites.append(url)
                return ''
            return html
    except urllib.error.HTTPError as e:
        if e.code == 403:
            _blocked_sites.append(url)
        return ''
    except Exception:
        return ''


_ZERO_WIDTH_RE = re.compile(
    '[\u200B\u200C\u200D\u200E\u200F\u2060\u2061\u2062\u2063\u2064\uFEFF\u00AD]'
)

_HIDDEN_STYLE_RE = re.compile(
    r'display\s*:\s*none|visibility\s*:\s*hidden|'
    r'opacity\s*:\s*0(?:[;\s"\'])|'
    r'position\s*:\s*absolute[^"\']*(?:left|top)\s*:\s*-\d{3,}|'
    r'height\s*:\s*0|font-size\s*:\s*0',
    re.IGNORECASE
)


def _decode_cf_email(encoded):
    try:
        key = int(encoded[:2], 16)
        return ''.join(chr(int(encoded[i:i+2], 16) ^ key) for i in range(2, len(encoded), 2))
    except (ValueError, IndexError):
        return ''


def _preprocess_html(raw):
    text = html_mod.unescape(raw)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = _ZERO_WIDTH_RE.sub('', text)
    text = re.sub(
        r'<(?:span|b|i|em|strong|small|div)[^>]*style=["\'][^"\']*display\s*:\s*none[^"\']*["\'][^>]*>.*?'
        r'</(?:span|b|i|em|strong|small|div)>',
        '', text, flags=re.DOTALL | re.IGNORECASE
    )
    return text


def _is_honeypot(tag_context):
    style = re.search(r'style=["\']([^"\']*)["\']', tag_context, re.I)
    return bool(style and _HIDDEN_STYLE_RE.search(style.group(1)))


def _extract_emails(raw_html):
    """Extract real email addresses from HTML, defeating 14 obfuscation methods."""
    found = set()

    # 1. Cloudflare email protection
    for m in re.findall(r'(?:data-cfemail|email-protection)(?:=["\'"]|#)([a-fA-F0-9]{6,})', raw_html):
        decoded = _decode_cf_email(m)
        if decoded and EMAIL_RE.fullmatch(decoded):
            found.add(decoded.lower())

    html = _preprocess_html(raw_html)

    # 6. URL-encoded mailto
    for m in re.findall(r'mailto:([^"\'>\s]+)', html):
        decoded = urllib.parse.unquote(m).split('?')[0]
        if EMAIL_RE.fullmatch(decoded):
            found.add(decoded.lower())

    # 7. String.fromCharCode()
    for m in re.findall(r'String\.fromCharCode\(([0-9,\s]+)\)', html):
        try:
            chars = [int(c.strip()) for c in m.split(',') if c.strip()]
            decoded = ''.join(chr(c) for c in chars)
            for e in EMAIL_RE.findall(decoded):
                found.add(e.lower())
        except (ValueError, OverflowError):
            pass

    # 8. Base64 / atob()
    for m in re.findall(r'(?:atob|data-email|data-encoded)\s*[\(=]\s*["\']([A-Za-z0-9+/=]{8,})["\']', html):
        try:
            decoded = base64.b64decode(m).decode('utf-8', errors='ignore')
            for e in EMAIL_RE.findall(decoded):
                found.add(e.lower())
        except Exception:
            pass

    # 9. ROT13
    rot13_encoded = set()
    for m in re.findall(r'(?:rot13|data-rot13)\s*[\(=]\s*["\']([^"\']+)["\']', html, re.I):
        decoded = codecs.decode(m, 'rot_13')
        if EMAIL_RE.fullmatch(decoded):
            found.add(decoded.lower())
            rot13_encoded.add(m.lower())

    # 10. data-user / data-domain
    for m in re.finditer(
        r'data-(?:user|name|local)\s*=\s*["\']([^"\']+)["\'][^>]*'
        r'data-(?:domain|host)\s*=\s*["\']([^"\']+)["\']', html, re.I
    ):
        addr = f"{m.group(1)}@{m.group(2)}"
        if EMAIL_RE.fullmatch(addr):
            found.add(addr.lower())
    for m in re.finditer(
        r'data-(?:domain|host)\s*=\s*["\']([^"\']+)["\'][^>]*'
        r'data-(?:user|name|local)\s*=\s*["\']([^"\']+)["\']', html, re.I
    ):
        addr = f"{m.group(2)}@{m.group(1)}"
        if EMAIL_RE.fullmatch(addr):
            found.add(addr.lower())

    # 11. CSS direction:rtl
    for m in re.findall(
        r'(?:direction\s*:\s*rtl|unicode-bidi\s*:\s*bidi-override)[^>]*>([^<]{5,60})<', html, re.I
    ):
        reversed_text = m.strip()[::-1]
        if EMAIL_RE.fullmatch(reversed_text):
            found.add(reversed_text.lower())

    # 12. JS hex-escaped strings
    for m in re.findall(r'["\']((\\x[0-9a-fA-F]{2}){4,})["\']', html):
        try:
            decoded = bytes.fromhex(m[0].replace('\\x', '')).decode('utf-8', errors='ignore')
            for e in EMAIL_RE.findall(decoded):
                found.add(e.lower())
        except Exception:
            pass

    # 14. Standard mailto + plaintext
    for m in re.findall(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', html, re.I):
        found.add(m.lower())
    for m in EMAIL_RE.findall(html):
        if m.lower() not in rot13_encoded:
            found.add(m.lower())

    # 13. Honeypot filtering
    honeypot_emails = set()
    for tag_match in re.finditer(r'<[^>]+style=["\'][^"\']*["\'][^>]*>.*?</[^>]+>', html, re.DOTALL | re.I):
        tag_html = tag_match.group(0)
        if _is_honeypot(tag_html):
            for e in EMAIL_RE.findall(tag_html):
                if html.count(e) == tag_html.count(e):
                    honeypot_emails.add(e.lower())
    found -= honeypot_emails

    return [e for e in found
            if not any(e.endswith('@' + j) or e.endswith('.' + j) for j in JUNK_EMAILS)
            and not e.endswith('.png') and not e.endswith('.jpg') and not e.endswith('.svg')]


def _extract_contact_url(html, base_url):
    matches = CONTACT_HREF_RE.findall(html)
    if not matches:
        return ''
    best = ''
    best_score = 0
    for href in matches:
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or 'privacy' in href.lower():
            continue
        score = 1
        lower = href.lower()
        if 'quote' in lower or 'rfq' in lower:
            score = 3
        elif 'request' in lower:
            score = 2
        if score > best_score:
            best = href
            best_score = score
    if not best:
        return ''
    if best.startswith('http'):
        return best
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
    return urllib.parse.urljoin(base_url, best)


def _pick_best_email(emails):
    for prefix in ('sales@', 'info@', 'contact@', 'inquiry@', 'inquiries@', 'quotes@', 'rfq@'):
        for e in emails:
            if e.startswith(prefix):
                return e
    return emails[0]


# --- Playwright fallback for Cloudflare/JS-blocked sites ---

def _playwright_fetch(url, timeout=15):
    """Use Playwright headless Chromium to fetch a page blocked by Cloudflare/JS."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return ''


US_STATES = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH',
    'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC',
    'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA',
    'rhode island': 'RI', 'south carolina': 'SC', 'south dakota': 'SD', 'tennessee': 'TN',
    'texas': 'TX', 'utah': 'UT', 'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA',
    'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
}
US_STATE_ABBRS = set(US_STATES.values())

NON_US_INDICATORS = [
    'united kingdom', 'england', 'u.k.', 'uk ', 'london', 'manchester', 'birmingham uk',
    'china', 'shanghai', 'beijing', 'shenzhen', 'guangzhou', 'dongguan',
    'india', 'mumbai', 'delhi', 'bangalore', 'chennai', 'hyderabad', 'pune',
    'canada', 'toronto', 'vancouver', 'montreal', 'ontario', 'alberta',
    'germany', 'deutschland', 'munich', 'berlin', 'stuttgart',
    'france', 'paris', 'lyon', 'japan', 'tokyo', 'osaka',
    'korea', 'seoul', 'taiwan', 'taipei', 'singapore',
    'australia', 'sydney', 'melbourne', 'brazil', 'mexico',
]


# --- Certification extraction ---

CERT_PATTERNS = re.compile(
    r'(?:'
    r'ISO\s*\d{4,5}(?::\d{4})?'         # ISO 9001, ISO 9001:2015, ISO 13485
    r'|AS\s*9100[A-Z]?(?::\d{4})?'       # AS9100, AS9100D
    r'|ITAR(?:\s+registered)?'            # ITAR
    r'|NADCAP'                            # NADCAP
    r'|AMS\s*\d+'                         # AMS specs
    r'|ASTM\s*[A-Z]?\d+'                 # ASTM standards
    r'|QPL(?:\s+\d+)?'                   # Qualified Products List
    r'|Mil-Spec'                          # Mil-Spec
    r'|FDA\s*(?:registered|cleared|approved|compliant)?'
    r'|RoHS(?:\s*compliant)?'
    r'|CE\s+mark(?:ed|ing)?'
    r'|UL\s*(?:listed|certified|\d+)?'
    r'|NIST\s*(?:800|SP)'
    r'|SOC\s*[12]'
    r'|CMMC'
    r'|Nadcap'
    r'|PED(?:\s+certified)?'
    r'|CWB'
    r'|AWS\s*D\d+'                        # AWS welding certs
    r'|ASME(?:\s+[A-Z]+)?'               # ASME stamps
    r'|API\s*\d+'                         # API specs
    r'|DFARS(?:\s+compliant)?'
    r'|JIS\s*[A-Z]?\d+'
    r'|SAE\s*(?:AS|AMS|J)\d+'
    r')',
    re.IGNORECASE
)

def _extract_certifications(html):
    """Extract quality certifications from HTML. Returns list of unique cert strings or empty list."""
    if not html:
        return []
    # Strip HTML tags for cleaner matching, but keep original for case-sensitive patterns
    text = re.sub(r'<[^>]+>', ' ', html)
    matches = CERT_PATTERNS.findall(text)
    if not matches:
        return []
    # Normalize and dedupe
    seen = set()
    unique = []
    for cert in matches:
        normalized = cert.strip().upper().replace('  ', ' ')
        if normalized not in seen:
            seen.add(normalized)
            unique.append(cert.strip())
    return unique[:8]  # Cap at 8 certs


def _extract_location(html):
    """Extract US state abbreviation from HTML. Returns 2-letter state code or None."""
    import re
    text = re.sub(r'<[^>]+>', ' ', html).lower()

    # Check for non-US indicators first
    for indicator in NON_US_INDICATORS:
        if indicator in text:
            # Could be a false positive (e.g. "ships to Canada"), so check context
            # But if it appears near "headquarters", "located", "address", it's real
            for ctx in ['headquarter', 'located in', 'based in', 'office in', 'address']:
                idx = text.find(indicator)
                if idx > 0 and ctx in text[max(0, idx-80):idx+len(indicator)+20]:
                    return 'NON-US'

    # Pattern: "City, ST ZIP" (e.g. "Houston, TX 77001")
    zip_match = re.search(r'([A-Z]{2})\s+\d{5}', html)
    if zip_match and zip_match.group(1) in US_STATE_ABBRS:
        return zip_match.group(1)

    # Pattern: "City, State" with full state name
    for state_name, abbr in US_STATES.items():
        if state_name in text:
            return abbr

    # Pattern: ", XX " where XX is a state abbreviation (in original HTML to preserve case)
    state_re = re.search(r',\s*([A-Z]{2})\b', html)
    if state_re and state_re.group(1) in US_STATE_ABBRS:
        return state_re.group(1)

    return None


def _enrich_single(supplier):
    """Enrich a single supplier with email, contactUrl, and location.

    Fast path: urllib on homepage + 4 common contact paths (stops on first email found).
    Slow path: single Playwright deep scan only if fast path finds nothing.
    """
    website = supplier.get('website', '')
    if not website:
        return supplier

    existing_email = supplier.get('email', '').strip()
    has_email = bool(EMAIL_RE.fullmatch(existing_email)) if existing_email else False
    existing_contact = supplier.get('contactUrl', '').strip()
    has_contact = bool(existing_contact.startswith('http')) if existing_contact else False

    if has_email and has_contact:
        return supplier

    base_url = website if website.startswith('http') else 'https://' + website
    needs_location = supplier.get('state', '') in ('', 'US', 'USA')

    def _has_valid_email():
        e = supplier.get('email', '').strip()
        return bool(e and EMAIL_RE.fullmatch(e))

    needs_certs = supplier.get('certifications', 'N/A') in ('N/A', '', None)
    all_certs = []

    def _check_html(html):
        """Extract email, contactUrl, location, and certs from HTML. Returns True if email found."""
        nonlocal all_certs
        if not html:
            return False
        if not _has_valid_email():
            emails = _extract_emails(html)
            if emails:
                supplier['email'] = _pick_best_email(emails)
        if not supplier.get('contactUrl', '').strip():
            contact = _extract_contact_url(html, base_url)
            if contact:
                supplier['contactUrl'] = contact
        if needs_location and supplier.get('state', '') in ('', 'US', 'USA'):
            loc = _extract_location(html)
            if loc == 'NON-US':
                supplier['_non_us'] = True
            elif loc:
                supplier['state'] = loc
        if needs_certs:
            certs = _extract_certifications(html)
            if certs:
                all_certs.extend(certs)
        return _has_valid_email()

    # --- Phase 1: Fast urllib pass (homepage + 4 common paths) ---
    homepage_html = _fetch_page(base_url, timeout=5)
    if _check_html(homepage_html) and supplier.get('contactUrl', '').strip():
        return supplier

    if not _has_valid_email():
        for path in ['/contact', '/contact-us', '/about', '/about-us']:
            page_html = _fetch_page(base_url.rstrip('/') + path, timeout=5)
            if _check_html(page_html):
                break

    # Fetch quality/certifications pages for certs (even if email already found)
    if needs_certs and not all_certs:
        for path in ['/quality', '/certifications', '/capabilities']:
            page_html = _fetch_page(base_url.rstrip('/') + path, timeout=5)
            if page_html:
                certs = _extract_certifications(page_html)
                if certs:
                    all_certs.extend(certs)
                    break  # Got certs, stop

    # Merge collected certs
    if all_certs:
        seen = set()
        unique = []
        for c in all_certs:
            n = c.strip().upper()
            if n not in seen:
                seen.add(n)
                unique.append(c.strip())
        supplier['certifications'] = ', '.join(unique[:6])

    if _has_valid_email():
        return supplier

    # --- Phase 2: Single Playwright deep scan (homepage → footer → contact link) ---
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": _BROWSER_HEADERS["User-Agent"]})
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=12000)
                page.wait_for_timeout(2000)

                # Rendered homepage — catches JS-injected emails and certs
                rendered_html = page.content()
                emails = _extract_emails(rendered_html)
                if needs_certs and not all_certs:
                    certs = _extract_certifications(rendered_html)
                    if certs:
                        all_certs.extend(certs)

                # Footer specifically
                footer_text = page.evaluate("""() => {
                    const footer = document.querySelector('footer') || document.querySelector('[class*="footer"]');
                    return footer ? footer.innerHTML : '';
                }""")
                if footer_text:
                    emails.extend(_extract_emails(footer_text))
                    if needs_certs and not all_certs:
                        certs = _extract_certifications(footer_text)
                        if certs:
                            all_certs.extend(certs)

                if emails:
                    supplier['email'] = _pick_best_email(list(set(emails)))
                else:
                    # Follow first contact/quote link on rendered page
                    contact_href = page.evaluate("""() => {
                        for (const a of document.querySelectorAll('a[href]')) {
                            const text = (a.textContent || '').toLowerCase();
                            const href = (a.href || '').toLowerCase();
                            if ((text.includes('contact') || text.includes('quote') || href.includes('contact'))
                                && a.href.startsWith('http')) {
                                return a.href;
                            }
                        }
                        return '';
                    }""")
                    if contact_href:
                        try:
                            page.goto(contact_href, wait_until="domcontentloaded", timeout=12000)
                            page.wait_for_timeout(2000)
                            contact_html = page.content()
                            emails = _extract_emails(contact_html)
                            if emails:
                                supplier['email'] = _pick_best_email(emails)
                            if not supplier.get('contactUrl', '').strip():
                                supplier['contactUrl'] = contact_href
                        except Exception:
                            pass
            except Exception:
                pass
            browser.close()
    except Exception:
        pass

    # Final cert merge (covers Playwright-found certs)
    if all_certs and needs_certs:
        seen = set()
        unique = []
        for c in all_certs:
            n = c.strip().upper()
            if n not in seen:
                seen.add(n)
                unique.append(c.strip())
        supplier['certifications'] = ', '.join(unique[:6])

    return supplier


def enrich_suppliers(suppliers):
    """Enrich a list of suppliers in parallel. Returns enriched list, non-US filtered out."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        enriched = list(pool.map(_enrich_single, suppliers))
    # Filter out suppliers identified as non-US during scraping
    return [s for s in enriched if not s.get('_non_us')]


# --- Browser form detection + fill ---

def detect_forms(url, timeout=20):
    """Use Playwright to detect contact/RFQ forms on a page.
    Tries multiple contact page paths if the given URL fails.
    Returns list of form metadata."""
    from urllib.parse import urlparse

    # Build list of URLs to try
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    urls_to_try = [url]
    # If the URL is just a base domain or /contact, also try common variants
    contact_paths = ['/contact', '/contact-us', '/request-a-quote', '/request-quote', '/get-a-quote', '/inquiry']
    current_path = parsed.path.rstrip('/')
    for path in contact_paths:
        candidate = base + path
        if candidate != url and path != current_path:
            urls_to_try.append(candidate)

    _FORM_JS = """() => {
        const results = [];
        document.querySelectorAll('form').forEach((form, idx) => {
            const fields = [];
            form.querySelectorAll('input, textarea, select').forEach(el => {
                if (el.type === 'hidden' || el.type === 'submit') return;
                const label = el.labels?.[0]?.textContent?.trim() ||
                              el.getAttribute('aria-label') ||
                              el.getAttribute('placeholder') || '';
                fields.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || 'text',
                    name: el.name || el.id || '',
                    label: label,
                    placeholder: el.placeholder || '',
                    required: el.required,
                });
            });
            if (fields.length < 2) return;
            const formText = form.textContent.toLowerCase();
            const isContact = ['contact', 'quote', 'rfq', 'inquiry', 'message', 'request'].some(
                kw => formText.includes(kw) || (form.action || '').toLowerCase().includes(kw)
            );
            results.push({
                index: idx,
                action: form.action || '',
                method: form.method || 'post',
                fields: fields,
                isContact: isContact,
            });
        });
        return results;
    }"""

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

            for try_url in urls_to_try:
                try:
                    page.goto(try_url, wait_until="domcontentloaded", timeout=timeout * 1000)
                    page.wait_for_timeout(2000)

                    # First try main page forms
                    forms = page.evaluate(_FORM_JS)
                    if forms:
                        browser.close()
                        contact_forms = [f for f in forms if f.get('isContact')]
                        result = contact_forms if contact_forms else forms
                        for f in result:
                            f['source_url'] = try_url
                        return result

                    # Try inside iframes (HubSpot, Marketo, Salesforce, etc.)
                    for frame in page.frames:
                        if frame == page.main_frame:
                            continue
                        try:
                            iframe_forms = frame.evaluate(_FORM_JS)
                            if iframe_forms:
                                browser.close()
                                contact_forms = [f for f in iframe_forms if f.get('isContact')]
                                result = contact_forms if contact_forms else iframe_forms
                                for f in result:
                                    f['source_url'] = try_url
                                    f['in_iframe'] = True
                                return result
                        except Exception:
                            continue

                    # No forms yet — follow "contact us" links on the page
                    contact_links = page.evaluate("""() => {
                        const links = [];
                        document.querySelectorAll('a[href]').forEach(a => {
                            const text = (a.textContent || '').trim().toLowerCase();
                            const href = a.href || '';
                            if ((text.includes('contact') || text.includes('quote') || text.includes('request'))
                                && href.startsWith('http') && !links.includes(href)) {
                                links.push(href);
                            }
                        });
                        return links.slice(0, 3);
                    }""")
                    for link_url in contact_links:
                        if link_url == try_url:
                            continue
                        try:
                            page.goto(link_url, wait_until="domcontentloaded", timeout=timeout * 1000)
                            page.wait_for_timeout(2000)
                            forms = page.evaluate(_FORM_JS)
                            if forms:
                                browser.close()
                                contact_forms = [f for f in forms if f.get('isContact')]
                                result = contact_forms if contact_forms else forms
                                for f in result:
                                    f['source_url'] = link_url
                                return result
                            # Also check iframes on followed page
                            for frame in page.frames:
                                if frame == page.main_frame:
                                    continue
                                try:
                                    iframe_forms = frame.evaluate(_FORM_JS)
                                    if iframe_forms:
                                        browser.close()
                                        contact_forms = [f for f in iframe_forms if f.get('isContact')]
                                        result = contact_forms if contact_forms else iframe_forms
                                        for f in result:
                                            f['source_url'] = link_url
                                            f['in_iframe'] = True
                                        return result
                                except Exception:
                                    continue
                        except Exception:
                            continue

                except Exception:
                    continue  # Try next URL

            browser.close()
            return []  # No forms found on any URL
    except Exception as e:
        return [{"error": str(e)}]


def fill_form(url, form_index, field_values, timeout=30):
    """Use Playwright to fill and submit a form. Returns success/failure + confirmation text."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(3000)

            # Get the form
            forms = page.query_selector_all("form")
            if form_index >= len(forms):
                browser.close()
                return {"success": False, "error": f"Form index {form_index} not found (only {len(forms)} forms)"}

            form = forms[form_index]

            # Fill fields
            for name, value in field_values.items():
                field = form.query_selector(f'input[name="{name}"], textarea[name="{name}"], select[name="{name}"]')
                if not field:
                    field = form.query_selector(f'input[id="{name}"], textarea[id="{name}"], select[id="{name}"]')
                if not field:
                    continue
                tag = field.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    field.select_option(value=value)
                else:
                    field.fill(value)

            # Find and click submit button
            submit = form.query_selector('button[type="submit"], input[type="submit"], button:not([type])')
            if submit:
                submit.click()
                page.wait_for_timeout(3000)  # Wait for submission

            confirmation = page.text_content("body")[:500]
            browser.close()
            return {"success": True, "confirmation": confirmation}
    except Exception as e:
        return {"success": False, "error": str(e)}
