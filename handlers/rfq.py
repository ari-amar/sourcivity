"""RFQ drafting and sending — LLM for drafting, Python for execution."""
import threading
from datetime import date
from services import llm, email_client, csv_store, sheets, settings as user_settings
from config import (
    EMAIL_ADDRESS,
    EMAIL_DISPLAY_NAME,
    CATEGORIES,
    CUSTOMER_NAME,
    CUSTOMER_FULL_NAME,
    CUSTOMER_TITLE,
    CUSTOMER_COMPANY,
)


def _customer_style_block(settings):
    requirements = ", ".join(user_settings.requirement_labels(settings)) or "pricing, lead time, and availability"
    buyer_notes = settings["rfq_buyer_notes"] or "none"
    repeat_orders = (
        "May mention possible repeat orders when it sounds natural."
        if settings["rfq_repeat_orders"]
        else "Do not promise repeat orders unless the RFQ notes explicitly say so."
    )
    casual = "Keep it casual and plainspoken." if settings["rfq_casual"] else "Keep it professional and buyer-like."
    return f"""CUSTOMER RFQ PREFERENCES:
- Buyer: {settings["buyer_name"]}, {settings["buyer_title"]} at {settings["buyer_company"]}
- Company intro to use naturally: {settings["rfq_company_intro"]}
- Tone: {user_settings.tone_label(settings)}
- Length: {user_settings.length_label(settings)}
- Urgency: {user_settings.urgency_label(settings)}
- Default asks: {requirements}
- Repeat-order language: {repeat_orders}
- Voice: {casual}
- Buyer notes: {buyer_notes}
- Signature must be exactly:
{settings["rfq_signature"]}"""


def handle_draft(supplier, part, qty="", notes=""):
    """Draft an RFQ email. Returns email text."""
    supplier_name = supplier.get("name", "Unknown")
    supplier_email = supplier.get("email", "")
    website = supplier.get("website", "")
    rfq_settings = user_settings.get_rfq_settings()
    signature = rfq_settings["rfq_signature"]
    buyer_name = rfq_settings["buyer_name"]
    buyer_title = rfq_settings["buyer_title"]
    buyer_company = rfq_settings["buyer_company"]

    system = f"""You are {buyer_name}, {buyer_title} at {buyer_company}, writing a quick RFQ email to a supplier.

YOUR GOAL: Get the supplier to reply. These tactics increase response rates:
- Mention your company name so they know you're a real buyer.
- Hint at ongoing or larger business ("first order", "upcoming project", "regular demand") so they see long-term value.
- Add a soft deadline or reason for urgency ("finalizing vendors this week", "project kicks off next month") so they prioritize you.
- Make it dead easy to reply — ask for a ballpark or "whatever you have on hand" rather than a formal quote package.

STRICT FORMATTING RULES — violating any of these means failure:
1. PLAIN TEXT ONLY. Absolutely NO markdown, NO asterisks, NO bullet points, NO numbered lists, NO dashes, NO "Please include:" lists. Zero formatting.
2. Follow the configured length preference, but never exceed 5 sentences total. One or two short paragraphs.
3. Start with "Hi [Company]," — NEVER "Dear", NEVER "To Whom It May Concern", NEVER "Team".
4. End with the configured signature exactly. NEVER "Sincerely", NEVER "Best regards". No other signature lines.
5. Mention what you need and ask for the selected default asks naturally. Do NOT break these into separate lines or a checklist.
6. If quantity is given, weave it into a sentence naturally. NEVER list it as a field.
7. Sound like a real buyer who sends these daily.

{_customer_style_block(rfq_settings)}

GOOD example:
Hi Schaeffler,

I'm sourcing crossed roller bearings for an upcoming automation build at {buyer_company}. We'd need around 50 units to start. Could you send over ballpark pricing, lead time, availability, and MOQ when you get a chance? We're finalizing our vendor list this week.

{signature}

BAD (do NOT do this):
Dear Schaeffler Team,
We are seeking a quote for the following:
- Crossed roller bearings
- Quantity: 50 units
Please include pricing, lead time, and MOQ.
Sincerely, {CUSTOMER_FULL_NAME}

Return ONLY in this exact format:
Subject: [Part] — quick quote request
To: {supplier_email}
From: {EMAIL_ADDRESS}

[Body]"""

    message = f"""Draft an RFQ email:
Supplier: {supplier_name}
Email: {supplier_email}
Website: {website}
Part/Service: {part}
Quantity: {qty or 'please advise on pricing tiers'}
Additional notes: {notes or 'none'}"""

    try:
        email_text = llm.call_llm(system, message, max_tokens=1024)
        # Strip any markdown the LLM may have added
        clean_lines = []
        for line in email_text.split("\n"):
            line = line.replace("**", "").replace("*", "")
            if line.strip().startswith("- ") or line.strip().startswith("• "):
                line = line.strip().lstrip("-•").strip()
            clean_lines.append(line)
        email_text = "\n".join(clean_lines)
        return {"email_text": email_text}
    except Exception as e:
        return {"error": str(e)}


def handle_send(supplier, email_text, part, category=""):
    """Send an approved RFQ email and update all tracking."""
    supplier_name = supplier.get("name", "Unknown")
    supplier_email = supplier.get("email", "")
    website = supplier.get("website", "")

    # Parse email components
    subject = "Request for Quote"
    body_lines = []
    to_addr = supplier_email

    for line in email_text.split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            subject = stripped[8:].strip()
        elif stripped.lower().startswith("to:"):
            to_addr = stripped[3:].strip()
        elif stripped.lower().startswith("from:"):
            continue  # Skip From line
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    if not to_addr:
        return {"success": False, "error": "No recipient email address"}

    # Send email
    success = email_client.send_email(to_addr, subject, body)

    if not success:
        return {"success": False, "error": "Email send failed"}

    today = date.today().isoformat()

    # Assign category if not provided
    if not category:
        category = _guess_category(part)

    # Add to CSV
    quote = {
        "category": category,
        "date": today,
        "supplier": supplier_name,
        "partService": part,
        "quotedPrice": "",
        "unit": "",
        "leadTime": "",
        "moq": "",
        "paymentTerms": "",
        "validUntil": "",
        "status": "📨 Sent",
        "notes": "Awaiting initial response",
        "email": to_addr,
    }
    csv_store.append_quote(quote)

    # Sync sheets in background
    threading.Thread(target=sheets.sync, daemon=True).start()

    return {"success": True, "message": f"RFQ sent to {supplier_name} at {to_addr}"}


def handle_followup(supplier_name):
    """Send a short follow-up email to a supplier who hasn't responded. Returns status dict."""
    if not supplier_name:
        return {"success": False, "error": "Missing supplier"}

    quotes, _ = csv_store.read_quotes()
    quote = next(
        (q for q in quotes if q.get("supplier", "").strip().lower() == supplier_name.strip().lower()),
        None,
    )
    if not quote:
        return {"success": False, "error": "Supplier not found in tracker"}

    email_addr = (quote.get("email") or "").strip()
    if not email_addr:
        return {"success": False, "error": "No email on file for this supplier — send a new RFQ instead."}

    part = quote.get("partService", "")
    sent_date = quote.get("date", "")
    rfq_settings = user_settings.get_rfq_settings()
    buyer_name = rfq_settings["buyer_name"]
    buyer_title = rfq_settings["buyer_title"]
    buyer_company = rfq_settings["buyer_company"]

    system = f"""You are {buyer_name}, {buyer_title} at {buyer_company}, sending a short, polite follow-up to a supplier who hasn't replied to an earlier RFQ.

STRICT RULES:
1. PLAIN TEXT ONLY. No markdown, no bullets, no asterisks.
2. 2-3 sentences maximum. Friendly nudge, not pushy.
3. Briefly reference the original request.
4. Ask if they can share ballpark pricing and lead time.
5. Start with "Hi {supplier_name}," — never "Dear" or "To Whom It May Concern".
6. End with the configured signature exactly.

{_customer_style_block(rfq_settings)}

Return ONLY in this exact format:
Subject: Re: [Part] — quick follow-up

[Body]"""

    message = f"""Draft the follow-up:
Supplier: {supplier_name}
Part/Service: {part}
Original RFQ sent: {sent_date or 'a few days ago'}"""

    try:
        email_text = llm.call_llm(system, message, max_tokens=400)
    except Exception as e:
        return {"success": False, "error": f"Draft failed: {e}"}

    subject = f"Re: {part} — quick follow-up" if part else "Quick follow-up on our request"
    body_lines = []
    for line in email_text.split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            subject = stripped[8:].strip()
            continue
        line = line.replace("**", "").replace("*", "")
        if line.strip().startswith("- ") or line.strip().startswith("• "):
            line = line.strip().lstrip("-•").strip()
        body_lines.append(line)
    body = "\n".join(body_lines).strip()

    if not email_client.send_email(email_addr, subject, body):
        return {"success": False, "error": "Email send failed"}

    today = date.today().isoformat()
    csv_store.update_quote(supplier_name, {
        "status": "🔔 Follow-up Sent",
        "notes": f"Follow-up sent {today}",
    })

    threading.Thread(target=sheets.sync, daemon=True).start()

    return {"success": True, "message": f"Follow-up sent to {supplier_name} at {email_addr}"}


def handle_batch_draft(suppliers, part, qty="", notes=""):
    """Draft RFQ emails for multiple suppliers in parallel. Returns list of drafts."""
    results = [None] * len(suppliers)

    def draft_one(i, supplier):
        result = handle_draft(supplier, part, qty, notes)
        results[i] = {
            "supplier_name": supplier.get("name", "Unknown"),
            "supplier_email": supplier.get("email", ""),
            "email_text": result.get("email_text", ""),
            "error": result.get("error", ""),
        }

    threads = []
    for i, supplier in enumerate(suppliers):
        t = threading.Thread(target=draft_one, args=(i, supplier))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return {"emails": results}


def handle_batch_send(items):
    """Send multiple RFQ emails sequentially. Returns list of results."""
    results = []
    for item in items:
        supplier = item.get("supplier", {})
        email_text = item.get("email_text", "")
        part = item.get("part", "")
        category = item.get("category", "")
        try:
            result = handle_send(supplier, email_text, part, category)
            results.append({
                "supplier_name": supplier.get("name", "Unknown"),
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "error": result.get("error", ""),
            })
        except Exception as e:
            results.append({
                "supplier_name": supplier.get("name", "Unknown"),
                "success": False,
                "error": str(e),
            })
    return {"results": results}


def _guess_category(part):
    """Use LLM to pick the best category for a part description."""
    # Get existing categories from the CSV so the LLM reuses them
    try:
        existing_quotes, _ = csv_store.read_quotes()
        existing_cats = sorted(set(q.get("category", "") for q in existing_quotes if q.get("category")))
    except Exception:
        existing_cats = []

    # Merge with config defaults
    all_cats = sorted(set(existing_cats + list(CATEGORIES)))
    cat_list = "\n".join(f"- {c}" for c in all_cats) if all_cats else "(none yet)"

    system = f"""You are a procurement categorization assistant. Given a part/service description, pick the BEST matching category from the existing list below. If none fit well, create a short new category name (2-4 words, Title Case, use & for conjunctions).

Existing categories:
{cat_list}

Rules:
1. Prefer an existing category if the part reasonably fits.
2. Only create a new category if the part clearly doesn't belong in any existing one.
3. Return ONLY the category name — nothing else. No quotes, no explanation."""

    try:
        result = llm.call_llm(system, f"Part/Service: {part}", max_tokens=30)
        category = result.strip().strip('"').strip("'")
        # Sanity check: if LLM returned something too long or weird, fall back
        if len(category) > 50 or "\n" in category:
            return _guess_category_fallback(part)
        return category
    except Exception:
        return _guess_category_fallback(part)


def _guess_category_fallback(part):
    """Simple keyword fallback if LLM is unavailable."""
    part_lower = part.lower()
    keywords = {
        "Flow Measurement & Control": ["flow", "meter", "sensor", "gauge", "instrument"],
        "Valves & Nozzles": ["valve", "nozzle", "spray", "ball valve", "gate valve"],
        "Metals & Alloys": ["inconel", "titanium", "alloy", "steel", "bronze", "aluminum", "metal", "nickel"],
        "Power Transmission": ["gear", "belt", "coupling", "clutch", "drive", "motor", "bearing"],
        "Pneumatics": ["pneumatic", "cylinder", "air", "actuator"],
        "Fasteners": ["fastener", "bolt", "screw", "nut", "rivet"],
        "Seals & Gaskets": ["seal", "gasket", "o-ring", "packing", "ptfe"],
        "Heat Transfer & Thermal": ["heat exchanger", "furnace", "heater", "condenser", "coil", "thermal"],
        "Pumps & Compressors": ["pump", "compressor", "blower", "vacuum"],
        "Tubing & Piping": ["tube", "tubing", "pipe", "piping", "hose", "fitting"],
        "Electrical & Controls": ["electrical", "control", "plc", "vfd", "drive", "wire", "cable"],
    }
    for cat, words in keywords.items():
        if any(w in part_lower for w in words):
            return cat
    return ""
