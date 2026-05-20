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

# Default SSL context with verification; fallback to unverified only on cert errors
_ssl_ctx = ssl.create_default_context()
_ssl_ctx_noverify = ssl.create_default_context()
_ssl_ctx_noverify.check_hostname = False
_ssl_ctx_noverify.verify_mode = ssl.CERT_NONE

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
CONTACT_HREF_RE = re.compile(
    r'href=["\']([^"\']*(?:contact|quote|rfq|inquir|request|get-in-touch|reach-us)[^"\']*)["\']',
    re.IGNORECASE
)
JUNK_EMAILS = {'example.com', 'sentry.io', 'yourcompany.com', 'domain.com', 'email.com',
               'wixpress.com', 'w3.org', 'schema.org', 'googleapis.com', 'google.com',
               'facebook.com', 'twitter.com', 'cloudflare.com'}
NON_EMAIL_TLDS = {
    'png', 'jpg', 'jpeg', 'svg', 'webp', 'gif', 'bmp', 'ico', 'pdf', 'css', 'js',
    'json', 'xml', 'woff', 'woff2', 'ttf', 'eot', 'map',
}

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

FAST_FETCH_TIMEOUT = 4
CERT_FETCH_TIMEOUT = 3
PLAYWRIGHT_GOTO_TIMEOUT_MS = 8000
PLAYWRIGHT_WAIT_MS = 800
FAST_ENRICH_PATHS = ('/contact', '/contact-us', '/about', '/about-us')
CERT_ENRICH_PATHS = ('/quality', '/certifications')
UNKNOWN_LOCATION_VALUES = {'', 'US', 'USA', 'UNITED STATES', 'N/A', 'NA', 'UNKNOWN'}


def get_blocked_sites():
    """Return list of sites that returned 403/Cloudflare blocks."""
    return list(_blocked_sites)


def _fetch_page(url, timeout=8, blocked_sites=None):
    """Fetch a URL and return its HTML text. Returns '' on failure."""
    blocked_sites = _blocked_sites if blocked_sites is None else blocked_sites
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
        try:
            resp_ctx = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
        except (ssl.SSLCertVerificationError, ssl.SSLError):
            resp_ctx = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx_noverify)
        with resp_ctx as resp:
            html = resp.read(500_000).decode('utf-8', errors='ignore')
            if 'cf-mitigated' in str(resp.headers) or 'Just a moment...' in html[:500]:
                blocked_sites.append(url)
                return ''
            return html
    except urllib.error.HTTPError as e:
        if e.code == 403:
            blocked_sites.append(url)
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


def _normalize_email_candidate(email):
    email = urllib.parse.unquote(email or '')
    return email.strip().strip('.,;:)]}>"\'').lower()


def _is_valid_email(email):
    email = _normalize_email_candidate(email)
    if not EMAIL_RE.fullmatch(email):
        return False
    lower = email.lower()
    local, domain = lower.rsplit('@', 1)
    if not local or not domain:
        return False
    if any(domain == junk or domain.endswith('.' + junk) for junk in JUNK_EMAILS):
        return False
    suffix = domain.rsplit('.', 1)[-1]
    if suffix in NON_EMAIL_TLDS:
        return False
    if re.search(r'\b\d{2,}x\d{2,}', domain):
        return False
    if '/' in lower or '..' in domain:
        return False
    return True


def _extract_emails(raw_html):
    """Extract real email addresses from HTML, defeating 14 obfuscation methods."""
    found = set()

    # 1. Cloudflare email protection
    for m in re.findall(r'(?:data-cfemail|email-protection)(?:=["\'"]|#)([a-fA-F0-9]{6,})', raw_html):
        decoded = _decode_cf_email(m)
        if decoded and _is_valid_email(decoded):
            found.add(_normalize_email_candidate(decoded))

    html = _preprocess_html(raw_html)

    # 6. URL-encoded mailto
    for m in re.findall(r'mailto:([^"\'>\s]+)', html):
        decoded = urllib.parse.unquote(m).split('?')[0]
        if _is_valid_email(decoded):
            found.add(_normalize_email_candidate(decoded))

    # 7. String.fromCharCode()
    for m in re.findall(r'String\.fromCharCode\(([0-9,\s]+)\)', html):
        try:
            chars = [int(c.strip()) for c in m.split(',') if c.strip()]
            decoded = ''.join(chr(c) for c in chars)
            for e in EMAIL_RE.findall(decoded):
                if _is_valid_email(e):
                    found.add(_normalize_email_candidate(e))
        except (ValueError, OverflowError):
            pass

    # 8. Base64 / atob()
    for m in re.findall(r'(?:atob|data-email|data-encoded)\s*[\(=]\s*["\']([A-Za-z0-9+/=]{8,})["\']', html):
        try:
            decoded = base64.b64decode(m).decode('utf-8', errors='ignore')
            for e in EMAIL_RE.findall(decoded):
                if _is_valid_email(e):
                    found.add(_normalize_email_candidate(e))
        except Exception:
            pass

    # 9. ROT13
    rot13_encoded = set()
    for m in re.findall(r'(?:rot13|data-rot13)\s*[\(=]\s*["\']([^"\']+)["\']', html, re.I):
        decoded = codecs.decode(m, 'rot_13')
        if _is_valid_email(decoded):
            found.add(_normalize_email_candidate(decoded))
            rot13_encoded.add(m.lower())

    # 10. data-user / data-domain
    for m in re.finditer(
        r'data-(?:user|name|local)\s*=\s*["\']([^"\']+)["\'][^>]*'
        r'data-(?:domain|host)\s*=\s*["\']([^"\']+)["\']', html, re.I
    ):
        addr = f"{m.group(1)}@{m.group(2)}"
        if _is_valid_email(addr):
            found.add(_normalize_email_candidate(addr))
    for m in re.finditer(
        r'data-(?:domain|host)\s*=\s*["\']([^"\']+)["\'][^>]*'
        r'data-(?:user|name|local)\s*=\s*["\']([^"\']+)["\']', html, re.I
    ):
        addr = f"{m.group(2)}@{m.group(1)}"
        if _is_valid_email(addr):
            found.add(_normalize_email_candidate(addr))

    # 11. CSS direction:rtl
    for m in re.findall(
        r'(?:direction\s*:\s*rtl|unicode-bidi\s*:\s*bidi-override)[^>]*>([^<]{5,60})<', html, re.I
    ):
        reversed_text = m.strip()[::-1]
        if _is_valid_email(reversed_text):
            found.add(_normalize_email_candidate(reversed_text))

    # 12. JS hex-escaped strings
    for m in re.findall(r'["\']((\\x[0-9a-fA-F]{2}){4,})["\']', html):
        try:
            decoded = bytes.fromhex(m[0].replace('\\x', '')).decode('utf-8', errors='ignore')
            for e in EMAIL_RE.findall(decoded):
                if _is_valid_email(e):
                    found.add(_normalize_email_candidate(e))
        except Exception:
            pass

    # 14. Standard mailto + plaintext
    for m in re.findall(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', html, re.I):
        if _is_valid_email(m):
            found.add(_normalize_email_candidate(m))
    for m in EMAIL_RE.findall(html):
        if m.lower() not in rot13_encoded:
            if _is_valid_email(m):
                found.add(_normalize_email_candidate(m))

    # 13. Honeypot filtering
    honeypot_emails = set()
    for tag_match in re.finditer(r'<[^>]+style=["\'][^"\']*["\'][^>]*>.*?</[^>]+>', html, re.DOTALL | re.I):
        tag_html = tag_match.group(0)
        if _is_honeypot(tag_html):
            for e in EMAIL_RE.findall(tag_html):
                if html.count(e) == tag_html.count(e):
                    honeypot_emails.add(e.lower())
    found -= honeypot_emails

    cleaned = []
    for email in found:
        normalized = _normalize_email_candidate(email)
        if _is_valid_email(normalized) and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


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


CERT_HREF_RE = re.compile(
    r'href=["\']([^"\']*(?:quality|certif|iso|as9100|nadcap|itar|compliance|standard|accredit)[^"\']*)["\']',
    re.IGNORECASE
)

def _find_cert_page_url(html, base_url):
    """Scan homepage links for a cert/quality page URL, mirroring _extract_contact_url."""
    matches = CERT_HREF_RE.findall(html)
    if not matches:
        return ''
    for href in matches:
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
            continue
        if href.startswith('http'):
            return href
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        return urllib.parse.urljoin(base_url, href)
    return ''


def _pick_best_email(emails):
    emails = [
        _normalize_email_candidate(e)
        for e in emails
        if _is_valid_email(e)
    ]
    if not emails:
        return ''
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
NON_US_COLLISION_CODES = {
    'IN': 'India',
    'CA': 'Canada',
    'DE': 'Germany',
    'IL': 'Israel',
    'CO': 'Colombia',
    'AR': 'Argentina',
    'AL': 'Albania',
    'GA': 'Gabon',
    'ID': 'Indonesia',
    'ME': 'Montenegro',
}

NON_US_INDICATORS = {
    # UK
    'united kingdom': 'UK', 'england': 'UK', 'u.k.': 'UK', 'uk ': 'UK', 'london': 'UK', 'manchester': 'UK', 'birmingham uk': 'UK', 'leeds': 'UK', 'glasgow': 'UK', 'sheffield': 'UK', 'bristol': 'UK',
    # China
    'china': 'CN', 'shanghai': 'CN', 'beijing': 'CN', 'shenzhen': 'CN', 'guangzhou': 'CN', 'dongguan': 'CN', 'chengdu': 'CN', 'wuhan': 'CN', 'tianjin': 'CN', 'ningbo': 'CN', 'suzhou': 'CN',
    # India
    'india': 'IN', 'mumbai': 'IN', 'delhi': 'IN', 'bangalore': 'IN', 'chennai': 'IN', 'hyderabad': 'IN', 'pune': 'IN', 'ahmedabad': 'IN', 'kolkata': 'IN', 'coimbatore': 'IN',
    # Canada
    'canada': 'CA', 'toronto': 'CA', 'vancouver': 'CA', 'montreal': 'CA', 'ontario': 'CA', 'alberta': 'CA', 'calgary': 'CA', 'edmonton': 'CA', 'ottawa': 'CA', 'winnipeg': 'CA',
    # Germany
    'germany': 'DE', 'deutschland': 'DE', 'munich': 'DE', 'berlin': 'DE', 'stuttgart': 'DE', 'hamburg': 'DE', 'frankfurt': 'DE', 'düsseldorf': 'DE', 'cologne': 'DE',
    # France
    'france': 'FR', 'paris': 'FR', 'lyon': 'FR', 'marseille': 'FR', 'toulouse': 'FR', 'bordeaux': 'FR',
    # Japan
    'japan': 'JP', 'tokyo': 'JP', 'osaka': 'JP', 'nagoya': 'JP', 'yokohama': 'JP', 'kyoto': 'JP', 'hiroshima': 'JP',
    # South Korea
    'korea': 'KR', 'south korea': 'KR', 'seoul': 'KR', 'busan': 'KR', 'incheon': 'KR',
    # Taiwan
    'taiwan': 'TW', 'taipei': 'TW', 'taichung': 'TW', 'kaohsiung': 'TW',
    # Singapore
    'singapore': 'SG',
    # Australia
    'australia': 'AU', 'sydney': 'AU', 'melbourne': 'AU', 'brisbane': 'AU', 'perth': 'AU', 'adelaide': 'AU',
    # Brazil
    'brazil': 'BR', 'são paulo': 'BR', 'sao paulo': 'BR', 'rio de janeiro': 'BR', 'belo horizonte': 'BR',
    # Mexico
    'mexico': 'MX', 'monterrey': 'MX', 'guadalajara': 'MX', 'ciudad juárez': 'MX',
    # Italy
    'italy': 'IT', 'milan': 'IT', 'rome': 'IT', 'turin': 'IT', 'bologna': 'IT', 'florence': 'IT',
    # Spain
    'spain': 'ES', 'madrid': 'ES', 'barcelona': 'ES', 'bilbao': 'ES', 'valencia': 'ES',
    # Netherlands
    'netherlands': 'NL', 'holland': 'NL', 'amsterdam': 'NL', 'rotterdam': 'NL', 'eindhoven': 'NL',
    # Switzerland
    'switzerland': 'CH', 'zurich': 'CH', 'geneva': 'CH', 'basel': 'CH', 'bern': 'CH',
    # Sweden
    'sweden': 'SE', 'stockholm': 'SE', 'gothenburg': 'SE', 'malmö': 'SE',
    # Poland
    'poland': 'PL', 'warsaw': 'PL', 'kraków': 'PL', 'krakow': 'PL', 'wrocław': 'PL', 'gdańsk': 'PL',
    # Czech Republic
    'czech republic': 'CZ', 'czechia': 'CZ', 'prague': 'CZ', 'brno': 'CZ',
    # Turkey
    'turkey': 'TR', 'türkiye': 'TR', 'istanbul': 'TR', 'ankara': 'TR', 'bursa': 'TR', 'izmir': 'TR',
    # Belgium
    'belgium': 'BE', 'brussels': 'BE', 'antwerp': 'BE', 'ghent': 'BE',
    # Austria
    'austria': 'AT', 'vienna': 'AT', 'graz': 'AT', 'linz': 'AT',
    # Portugal
    'portugal': 'PT', 'lisbon': 'PT', 'porto': 'PT',
    # Denmark
    'denmark': 'DK', 'copenhagen': 'DK', 'aarhus': 'DK',
    # Finland
    'finland': 'FI', 'helsinki': 'FI', 'tampere': 'FI',
    # Norway
    'norway': 'NO', 'oslo': 'NO', 'bergen': 'NO',
    # Ireland
    'ireland': 'IE', 'dublin': 'IE', 'cork': 'IE',
    # Hungary
    'hungary': 'HU', 'budapest': 'HU',
    # Romania
    'romania': 'RO', 'bucharest': 'RO', 'cluj': 'RO',
    # Greece
    'greece': 'GR', 'athens': 'GR', 'thessaloniki': 'GR',
    # Vietnam
    'vietnam': 'VN', 'ho chi minh': 'VN', 'hanoi': 'VN', 'da nang': 'VN',
    # Thailand
    'thailand': 'TH', 'bangkok': 'TH', 'chiang mai': 'TH',
    # Malaysia
    'malaysia': 'MY', 'kuala lumpur': 'MY', 'penang': 'MY', 'johor': 'MY',
    # Indonesia
    'indonesia': 'ID', 'jakarta': 'ID', 'surabaya': 'ID',
    # Philippines
    'philippines': 'PH', 'manila': 'PH', 'cebu': 'PH',
    # Israel
    'israel': 'IL', 'tel aviv': 'IL', 'haifa': 'IL',
    # UAE
    'united arab emirates': 'UAE', 'u.a.e.': 'UAE', 'dubai': 'UAE', 'abu dhabi': 'UAE', 'sharjah': 'UAE',
    # Saudi Arabia
    'saudi arabia': 'SA', 'riyadh': 'SA', 'jeddah': 'SA',
    # Hong Kong
    'hong kong': 'HK',
    # New Zealand
    'new zealand': 'NZ', 'auckland': 'NZ', 'wellington': 'NZ', 'christchurch': 'NZ',
    # South Africa
    'south africa': 'ZA', 'johannesburg': 'ZA', 'cape town': 'ZA', 'durban': 'ZA',
    # Argentina
    'argentina': 'AR', 'buenos aires': 'AR', 'córdoba': 'AR',
    # Colombia
    'colombia': 'CO', 'bogotá': 'CO', 'medellín': 'CO',
    # Chile
    'chile': 'CL', 'santiago': 'CL',
    # Egypt
    'egypt': 'EG', 'cairo': 'EG', 'alexandria': 'EG',
    # Morocco
    'morocco': 'MA', 'casablanca': 'MA', 'rabat': 'MA',
    # Ukraine
    'ukraine': 'UA', 'kyiv': 'UA', 'kharkiv': 'UA', 'lviv': 'UA',
    # Pakistan
    'pakistan': 'PK', 'karachi': 'PK', 'lahore': 'PK',
    # Bangladesh
    'bangladesh': 'BD', 'dhaka': 'BD', 'chittagong': 'BD',
}


# --- Certification extraction ---

CERT_PATTERNS = re.compile(
    r'(?:'
    r'ISO\s*\d{4,5}(?::\s*\d{4})?'       # ISO 9001, ISO 9001:2015, ISO 13485
    r'|AS\s*9100[A-Z]?(?::\s*\d{4})?'    # AS9100, AS9100D
    r'|ITAR(?:\s+registered)?'            # ITAR
    r'|NADCAP'                            # NADCAP
    r'|AMS\s*\d+'                         # AMS specs
    r'|ASTM\s*[A-Z]?\d+'                 # ASTM standards
    r'|QPL(?:\s+\d+)?'                   # Qualified Products List
    r'|Mil-Spec'                          # Mil-Spec
    r'|FDA\s*(?:registered|cleared|approved|compliant)?'
    r'|RoHS(?:\s*compliant)?'
    r'|CE\s+mark(?:ed|ing)?'
    r'|UL\s*(?:listed|certified|approved|\d{3,})'
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

_WEAK_CERT_PREFIXES = (
    'FDA', 'ROHS', 'CE ', 'UL ', 'PED', 'ASME', 'API ', 'DFARS', 'ASTM',
    'AMS', 'SAE', 'JIS', 'MIL-SPEC', 'QPL'
)
_ALWAYS_REJECT_CERTS = {
    'FDA', 'FDA APPROVED', 'FDA CLEARED', 'FDA COMPLIANT',
    'ROHS', 'ROHS COMPLIANT',
    'CE MARK', 'CE MARKED', 'CE MARKING',
    'UL LISTED', 'UL CERTIFIED', 'UL APPROVED',
    'PED', 'PED CERTIFIED',
    'ASME', 'ASME SECTION',
    'DFARS', 'DFARS COMPLIANT',
}
_CONTEXT_MARKERS = (
    'certified', 'certification', 'certificate', 'certifications', 'registered',
    'registration', 'accredited', 'accreditation', 'quality management',
    'management system', 'approved supplier'
)


def _normalize_cert(cert):
    normalized = re.sub(r'\s+', ' ', str(cert or '').strip().upper())
    normalized = normalized.replace('MIL SPEC', 'MIL-SPEC')

    iso_match = re.fullmatch(r'ISO\s*(\d{4,5})(?::\s*(\d{4}))?', normalized)
    if iso_match:
        version = f":{iso_match.group(2)}" if iso_match.group(2) else ""
        return f"ISO {iso_match.group(1)}{version}"

    as_match = re.fullmatch(r'AS\s*9100\s*([A-Z]?)(?::\s*(\d{4}))?', normalized)
    if as_match:
        suffix = as_match.group(1) or ""
        version = f":{as_match.group(2)}" if as_match.group(2) else ""
        return f"AS9100{suffix}{version}"

    return normalized


def _cert_family_key(cert):
    cert = _normalize_cert(cert)
    iso_match = re.match(r'ISO (\d{4,5})', cert)
    if iso_match:
        return f"ISO {iso_match.group(1)}"
    as_match = re.match(r'AS9100', cert)
    if as_match:
        return "AS9100"
    return cert


def _cert_specificity(cert):
    cert = _normalize_cert(cert)
    return (10 if ':' in cert else 0) + len(cert)


def _dedupe_certifications(certs):
    normalized = []
    seen = set()
    for cert in certs:
        n = _normalize_cert(cert)
        if not n or n in seen:
            continue
        seen.add(n)
        normalized.append(n)

    filtered = []
    for cert in normalized:
        key = _cert_family_key(cert)
        if any(
            other != cert
            and _cert_family_key(other) == key
            and _cert_specificity(other) > _cert_specificity(cert)
            for other in normalized
        ):
            continue
        filtered.append(cert)

    _SUBSUMABLE = {'ASME', 'ISO', 'AS', 'AMS', 'ASTM', 'SAE', 'AWS', 'API'}
    deduped = []
    for cert in filtered:
        base = cert.split()[0] if cert.split() else cert
        if base in _SUBSUMABLE and len(cert.split()) == 1:
            if not any(c != cert and c.startswith(cert) for c in filtered):
                deduped.append(cert)
        else:
            deduped.append(cert)
    return deduped


def _is_always_rejected_cert(cert):
    return _normalize_cert(cert) in _ALWAYS_REJECT_CERTS


def _is_supplier_level_cert(cert):
    normalized = _normalize_cert(cert)
    if _is_always_rejected_cert(normalized):
        return False
    if re.match(r'^ISO \d{4,5}', normalized):
        return True
    if normalized.startswith(('AS9100', 'NADCAP', 'NIST 800', 'NIST SP', 'SOC 1', 'SOC 2', 'CMMC', 'CWB', 'AWS D')):
        return True
    if normalized.startswith('ITAR REGISTERED'):
        return True
    if normalized.startswith(_WEAK_CERT_PREFIXES) or normalized == 'ITAR':
        return False
    return False


def _has_cert_context(text, start, end):
    window = text[max(0, start - 90):min(len(text), end + 90)].lower()
    return any(marker in window for marker in _CONTEXT_MARKERS)


def _filter_unverified_certifications(certs):
    """Keep certs likely to be supplier-level when there is no source context."""
    return _dedupe_certifications(c for c in certs if _is_supplier_level_cert(c))


def _extract_certifications(html, require_context=False):
    """Extract quality certifications from HTML. Returns list of unique cert strings or empty list."""
    if not html:
        return []
    # Pull alt and title attribute values before stripping tags — cert badges are
    # almost always <img> elements whose text content disappears after tag removal.
    attr_text = ' '.join(re.findall(r'(?:alt|title)=["\']([^"\']+)["\']', html, re.IGNORECASE))
    # Strip HTML tags for the main body text
    body_text = re.sub(r'<[^>]+>', ' ', html)
    text = attr_text + ' ' + body_text
    matches = []
    for match in CERT_PATTERNS.finditer(text):
        cert = _normalize_cert(match.group(0))
        if _is_always_rejected_cert(cert):
            continue
        if require_context and not _is_supplier_level_cert(cert) and not _has_cert_context(text, match.start(), match.end()):
            continue
        matches.append(cert)
    if not matches:
        return []
    deduped = _dedupe_certifications(matches)
    return deduped[:8]  # Cap at 8 certs


def _extract_location(html):
    """Extract location from HTML. Returns US state abbr, country code, or None.

    Priority order (most to least semantically specific):
      1. Schema.org addressRegion — author explicitly declared it
      2. "headquartered/located/based in ..., ST" — unambiguous company statement
      3. ", ST ZIP[-4]" — address-formatted with ZIP (contextual anchor)
      4. "ST United States/USA" — state anchored to country name
      5. Full state name in page text — lowest precision, last resort
    The bare ", XX" pattern is intentionally omitted — too many false positives
    (e.g. "Type, CA" or "Page, OR") on full-page scans.
    """
    import re
    text = re.sub(r'<[^>]+>', ' ', html).lower()

    us_state_found = None
    non_us_country = None
    for indicator, country_code in NON_US_INDICATORS.items():
        if indicator in text:
            non_us_country = NON_US_COLLISION_CODES.get(country_code, country_code)
            break

    def _is_non_us_collision(code):
        return bool(non_us_country and NON_US_COLLISION_CODES.get(code) == non_us_country)

    # Pattern 1: Schema.org / JSON-LD addressRegion — most authoritative
    region_match = re.search(r'"addressRegion"\s*:\s*"([A-Z]{2})"', html)
    if region_match:
        code = region_match.group(1)
        if code in US_STATE_ABBRS and not _is_non_us_collision(code):
            us_state_found = code

    # Pattern 2: "headquartered/located/based in ..., ST"
    if not us_state_found:
        meta_match = re.search(r'(?:headquartered|located|based)\s+in\s+[\w\s]+,\s*([A-Z]{2})\b', html)
        if meta_match:
            code = meta_match.group(1)
            if code in US_STATE_ABBRS and not _is_non_us_collision(code):
                us_state_found = code

    # Pattern 3: ", ST ZIP[-4]" — address-formatted (comma anchors the state)
    if not us_state_found:
        zip_match = re.search(r',\s*([A-Z]{2})\s+\d{5}(?:-\d{4})?(?!\d)', html)
        if zip_match:
            code = zip_match.group(1)
            if code in US_STATE_ABBRS and not _is_non_us_collision(code):
                us_state_found = code

    # Pattern 4: "ST United States" / "ST, USA" — state anchored to country name
    if not us_state_found:
        addr_match = re.search(r'([A-Z]{2})\s*,?\s*(?:United States|USA|U\.S\.A\.)', html)
        if addr_match:
            code = addr_match.group(1)
            if code in US_STATE_ABBRS and not _is_non_us_collision(code):
                us_state_found = code

    # Check non-US indicators before loose full-state matching. This prevents
    # India/Canada/etc. pages from being misclassified because they mention a US
    # state name in navigation, distributor text, examples, or customer lists.
    if non_us_country:
        return non_us_country

    # Pattern 5: Full state name anywhere in page text — last resort, low precision
    if not us_state_found:
        for state_name, abbr in US_STATES.items():
            if state_name in text:
                us_state_found = abbr
                break

    # If we found a US state, always prefer it (even if non-US indicators exist)
    if us_state_found:
        return us_state_found

    return None


def _has_strong_non_us_location(html, country_value):
    """Return True when a non-US country appears in address/headquarters context."""
    if not html or not country_value:
        return False
    text = re.sub(r'<[^>]+>', ' ', html).lower()
    country_code = None
    country_name = str(country_value).lower()
    for code, name in NON_US_COLLISION_CODES.items():
        if name.lower() == country_name:
            country_code = code
            break
    indicators = [
        indicator for indicator, code in NON_US_INDICATORS.items()
        if code == country_value or code == country_code or indicator == country_name
    ]
    if not indicators:
        indicators = [country_name]

    address_cue = (
        r'headquarter|head office|registered office|located|based|address|factory|'
        r'plant|warehouse|manufactur|unit|road|street|avenue|postal|pincode|pin code'
    )
    for indicator in indicators:
        if len(indicator.strip()) < 3:
            continue
        escaped = re.escape(indicator.strip())
        if re.search(rf'(?:{address_cue})[^.{{}}]{{0,140}}\b{escaped}\b', text):
            return True
        if re.search(rf'\b{escaped}\b[^.{{}}]{{0,140}}(?:{address_cue})', text):
            return True
    return False


def _is_unknown_location_value(value):
    return (value or '').strip().upper() in UNKNOWN_LOCATION_VALUES


def _enrich_single(supplier, skip_email=False, blocked_sites=None):
    """Enrich a single supplier with location, certs, contactUrl, and optionally email.

    skip_email=True: skips email/contact discovery for demo mode, while still
    filling missing location and certifications.
    Fast path: urllib on homepage + 4 common paths.
    Slow path: single Playwright deep scan only if still missing data after fast path.
    """
    website = supplier.get('website', '')
    if not website:
        return supplier

    existing_email = supplier.get('email', '').strip()
    if existing_email and not _is_valid_email(existing_email):
        supplier['email'] = ''
        existing_email = ''
    has_email = bool(_is_valid_email(existing_email)) if existing_email else False
    existing_contact = supplier.get('contactUrl', '').strip()
    has_contact = bool(existing_contact.startswith('http')) if existing_contact else False

    existing_certs = (supplier.get('certifications') or '').strip()
    initial_state = (supplier.get('state') or '').strip().upper()
    existing_cert_list = []
    if existing_certs and existing_certs.upper() not in UNKNOWN_LOCATION_VALUES:
        existing_cert_list = _filter_unverified_certifications(_extract_certifications(existing_certs))
        supplier['certifications'] = ', '.join(existing_cert_list) if existing_cert_list else ''

    needs_location = _is_unknown_location_value(initial_state)
    needs_certs = not bool(existing_cert_list)
    needs_contact = not skip_email
    location_verified = not needs_location

    # Early exit: nothing left to fetch
    email_done = skip_email or has_email
    if email_done and (not needs_contact or has_contact) and not needs_location and not needs_certs:
        return supplier

    base_url = website if website.startswith('http') else 'https://' + website

    def _has_valid_email():
        e = supplier.get('email', '').strip()
        return bool(e and _is_valid_email(e))

    def _has_contact_url():
        contact = supplier.get('contactUrl', '').strip()
        return bool(contact and contact.startswith('http'))

    def _contact_done():
        return not needs_contact or _has_contact_url()

    def _state_done():
        return not needs_location or location_verified or not _is_unknown_location_value(supplier.get('state', ''))

    def _fast_enough():
        return (skip_email or _has_valid_email()) and _contact_done() and _state_done() and (not needs_certs or bool(all_certs))

    all_certs = []

    def _check_html(html):
        """Extract contactUrl, location, certs, and (if not skip_email) email from HTML."""
        nonlocal all_certs, location_verified
        if not html:
            return
        if not skip_email and not _has_valid_email():
            emails = _extract_emails(html)
            if emails:
                supplier['email'] = _pick_best_email(emails)
        if needs_contact and not supplier.get('contactUrl', '').strip():
            contact = _extract_contact_url(html, base_url)
            if contact:
                supplier['contactUrl'] = contact
        if needs_location:
            loc = _extract_location(html)
            if loc:
                if loc not in US_STATE_ABBRS:
                    if initial_state in US_STATE_ABBRS and not _has_strong_non_us_location(html, loc):
                        loc = None
                if loc and loc not in US_STATE_ABBRS:
                    location_verified = True
                    supplier['state'] = loc
                    supplier['_non_us'] = True
                elif loc:
                    location_verified = True
                    supplier['state'] = loc
                    supplier.pop('_non_us', None)
        if needs_certs:
            certs = _extract_certifications(html, require_context=True)
            if certs:
                all_certs.extend(certs)

    def _publish_certs():
        if all_certs:
            certs = _dedupe_certifications(all_certs)
            supplier['certifications'] = ', '.join(certs[:6]) if certs else ''
            return bool(certs)
        if existing_cert_list:
            supplier['certifications'] = ', '.join(existing_cert_list[:6])
            return True
        return False

    # --- Phase 1: Fast urllib pass (homepage + 4 common paths) ---
    homepage_html = _fetch_page(base_url, timeout=FAST_FETCH_TIMEOUT, blocked_sites=blocked_sites)
    _check_html(homepage_html)

    # Discover cert page URL from homepage links before guessing paths
    discovered_cert_url = _find_cert_page_url(homepage_html, base_url) if homepage_html else ''

    for path in FAST_ENRICH_PATHS:
        if _fast_enough():
            break
        page_html = _fetch_page(base_url.rstrip('/') + path, timeout=FAST_FETCH_TIMEOUT, blocked_sites=blocked_sites)
        _check_html(page_html)

    # Cert pages are only fetched when the first pass still has no supplier-level certs.
    if needs_certs:
        cert_urls_to_try = []
        if discovered_cert_url:
            cert_urls_to_try.append(discovered_cert_url)
        for path in CERT_ENRICH_PATHS:
            url = base_url.rstrip('/') + path
            if url != discovered_cert_url:
                cert_urls_to_try.append(url)
        for url in cert_urls_to_try:
            if all_certs:
                break
            page_html = _fetch_page(url, timeout=CERT_FETCH_TIMEOUT, blocked_sites=blocked_sites)
            if page_html:
                certs = _extract_certifications(page_html, require_context=True)
                if certs:
                    all_certs.extend(certs)

    # Merge collected certs
    _publish_certs()

    # Playwright is expensive; use it only for missing email or missing location,
    # not for cert-only cleanup.
    email_done = skip_email or _has_valid_email()
    state_done = _state_done()
    needs_playwright = (not email_done) or (needs_location and not state_done)
    if not needs_playwright:
        supplier['_location_verified'] = bool(location_verified)
        return supplier

    # --- Phase 2: Single Playwright deep scan (homepage → footer → contact link) ---
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": _BROWSER_HEADERS["User-Agent"]})
            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS)
                page.wait_for_timeout(PLAYWRIGHT_WAIT_MS)

                # Rendered homepage — catches JS-injected content
                rendered_html = page.content()
                if not skip_email:
                    emails = _extract_emails(rendered_html)
                if needs_certs and not all_certs:
                    certs = _extract_certifications(rendered_html, require_context=True)
                    if certs:
                        all_certs.extend(certs)

                # Footer specifically
                footer_text = page.evaluate("""() => {
                    const footer = document.querySelector('footer') || document.querySelector('[class*="footer"]');
                    return footer ? footer.innerHTML : '';
                }""")
                if footer_text:
                    if not skip_email:
                        emails.extend(_extract_emails(footer_text))
                    if needs_certs and not all_certs:
                        certs = _extract_certifications(footer_text, require_context=True)
                        if certs:
                            all_certs.extend(certs)

                # Location from rendered page (catches JS-rendered addresses)
                if needs_location and not location_verified:
                    loc = _extract_location(rendered_html)
                    if loc:
                        if loc not in US_STATE_ABBRS:
                            if initial_state in US_STATE_ABBRS and not _has_strong_non_us_location(rendered_html, loc):
                                loc = None
                        if loc and loc not in US_STATE_ABBRS:
                            location_verified = True
                            supplier['state'] = loc
                            supplier['_non_us'] = True
                        elif loc:
                            location_verified = True
                            supplier['state'] = loc
                            supplier.pop('_non_us', None)

                if not skip_email:
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
                                page.goto(contact_href, wait_until="domcontentloaded", timeout=PLAYWRIGHT_GOTO_TIMEOUT_MS)
                                page.wait_for_timeout(PLAYWRIGHT_WAIT_MS)
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
        _publish_certs()
    elif existing_certs and existing_certs.upper() not in UNKNOWN_LOCATION_VALUES:
        supplier['certifications'] = ', '.join(existing_cert_list) if existing_cert_list else ''

    supplier['_location_verified'] = bool(location_verified)
    return supplier


def enrich_suppliers(suppliers, on_each=None, skip_email=False, blocked_sites=None):
    """Enrich a list of suppliers in parallel. Returns enriched list.
    skip_email=True skips email/contact discovery (demo mode).
    If on_each callback is provided, it's called after each supplier finishes."""
    blocked_sites = _blocked_sites if blocked_sites is None else blocked_sites
    results = [None] * len(suppliers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_enrich_single, s, skip_email, blocked_sites): i for i, s in enumerate(suppliers)}
        for f in concurrent.futures.as_completed(futures):
            idx = futures[f]
            try:
                results[idx] = f.result()
            except Exception:
                results[idx] = suppliers[idx]
            if on_each:
                try:
                    on_each(idx, results[idx])
                except Exception:
                    pass
    return results


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
