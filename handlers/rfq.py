"""RFQ drafting and sending — LLM for drafting, Python for execution."""
import threading
from datetime import date
from services import llm, email_client, csv_store, sheets
from config import EMAIL_ADDRESS, EMAIL_DISPLAY_NAME, CATEGORIES, CUSTOMER_NAME, CUSTOMER_FULL_NAME, CUSTOMER_TITLE, CUSTOMER_COMPANY


def handle_draft(supplier, part, qty="", notes=""):
    """Draft an RFQ email. Returns email text."""
    supplier_name = supplier.get("name", "Unknown")
    supplier_email = supplier.get("email", "")
    website = supplier.get("website", "")

    system = f"""You are {CUSTOMER_NAME}, {CUSTOMER_TITLE} at {CUSTOMER_COMPANY}, writing a quick RFQ email to a supplier.

YOUR GOAL: Get the supplier to reply. These tactics increase response rates:
- Mention your company name so they know you're a real buyer.
- Hint at ongoing or larger business ("first order", "upcoming project", "regular demand") so they see long-term value.
- Add a soft deadline or reason for urgency ("finalizing vendors this week", "project kicks off next month") so they prioritize you.
- Make it dead easy to reply — ask for a ballpark or "whatever you have on hand" rather than a formal quote package.

STRICT FORMATTING RULES — violating any of these means failure:
1. PLAIN TEXT ONLY. Absolutely NO markdown, NO asterisks, NO bullet points, NO numbered lists, NO dashes, NO "Please include:" lists. Zero formatting.
2. Maximum 4-5 sentences total. One or two short paragraphs.
3. Start with "Hi [Company]," — NEVER "Dear", NEVER "To Whom It May Concern", NEVER "Team".
4. End with just "{CUSTOMER_NAME}" on its own line, then "{CUSTOMER_COMPANY}" on the next line. NEVER "Sincerely", NEVER "Best regards". No other signature lines.
5. Mention what you need and ask for pricing, lead time, and availability naturally. Do NOT break these into separate lines or a checklist.
6. If quantity is given, weave it into a sentence naturally. NEVER list it as a field.
7. Sound like a real buyer who sends these daily — casual, direct, confident.

GOOD example:
Hi Schaeffler,

I'm sourcing crossed roller bearings for an upcoming automation build at {CUSTOMER_COMPANY}. We'd need around 50 units to start, with likely repeat orders down the line. Could you send over ballpark pricing and lead time when you get a chance? We're finalizing our vendor list this week.

{CUSTOMER_NAME}
{CUSTOMER_COMPANY}

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
    }
    csv_store.append_quote(quote)

    # Sync sheets in background
    threading.Thread(target=sheets.sync, daemon=True).start()

    return {"success": True, "message": f"RFQ sent to {supplier_name} at {to_addr}"}


def _guess_category(part):
    """Guess the best category for a part description."""
    part_lower = part.lower()
    keywords = {
        "Flow Measurement & Control": ["flow", "meter", "sensor", "gauge", "instrument"],
        "Valves & Nozzles": ["valve", "nozzle", "spray", "ball valve", "gate valve"],
        "Metals & Alloys": ["inconel", "titanium", "alloy", "steel", "bronze", "aluminum", "metal", "nickel"],
        "Power Transmission": ["gear", "belt", "coupling", "clutch", "drive", "motor", "bearing"],
        "Pneumatics": ["pneumatic", "cylinder", "air", "actuator"],
        "Fasteners": ["fastener", "bolt", "screw", "nut", "rivet"],
    }
    for cat, words in keywords.items():
        if any(w in part_lower for w in words):
            return cat
    return ""
