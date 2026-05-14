"""Customer-editable account settings."""
import json
import os
import tempfile

from config import (
    CUSTOMER_COMPANY,
    CUSTOMER_NAME,
    CUSTOMER_TITLE,
    RFQ_DEFAULT_DEADLINE,
    RFQ_EXTRA_INSTRUCTIONS,
    RFQ_SIGNATURE,
    RFQ_TONE,
    SETTINGS_JSON,
)

TEXT_LIMITS = {
    "buyer_name": 160,
    "buyer_title": 160,
    "buyer_company": 180,
    "rfq_company_intro": 300,
    "rfq_signature": 500,
    "rfq_buyer_notes": 1200,
    "rfq_default_deadline": 240,
}

TONE_OPTIONS = {
    "direct": "direct and concise",
    "friendly": "friendly and professional",
    "formal": "formal and polished",
    "technical": "technical and precise",
}

LENGTH_OPTIONS = {
    "very_short": "very short, 2-3 sentences",
    "short": "short, 3-4 sentences",
    "standard": "standard, 4-5 sentences",
    "detailed": "detailed when the request needs context",
}

URGENCY_OPTIONS = {
    "low": "no urgency; avoid deadline pressure",
    "normal": RFQ_DEFAULT_DEADLINE,
    "high": "we are selecting suppliers soon and would appreciate a quick turnaround",
}

REQUIREMENT_OPTIONS = {
    "pricing": "pricing",
    "lead_time": "lead time",
    "availability": "availability",
    "moq": "MOQ",
    "payment_terms": "payment terms",
    "shipping_terms": "shipping terms",
    "datasheet": "datasheet",
    "certifications": "certifications",
    "volume_discounts": "volume discounts",
    "alternatives": "alternatives or substitutes",
}

DEFAULT_REQUIREMENTS = ["pricing", "lead_time", "availability", "moq"]

def _default_company_intro():
    if CUSTOMER_COMPANY:
        return f"I'm sourcing this for {CUSTOMER_COMPANY}."
    return "I'm sourcing this for an upcoming project."


def _default_tone():
    raw = (RFQ_TONE or "").lower()
    if "formal" in raw:
        return "formal"
    if "technical" in raw:
        return "technical"
    if "friendly" in raw:
        return "friendly"
    return "direct"


def default_rfq_settings():
    return {
        "buyer_name": CUSTOMER_NAME,
        "buyer_title": CUSTOMER_TITLE,
        "buyer_company": CUSTOMER_COMPANY,
        "rfq_company_intro": _default_company_intro(),
        "rfq_tone": _default_tone(),
        "rfq_length": "short",
        "rfq_urgency": "normal",
        "rfq_repeat_orders": False,
        "rfq_vendor_deadline": True,
        "rfq_casual": False,
        "rfq_requirements": list(DEFAULT_REQUIREMENTS),
        "rfq_buyer_notes": RFQ_EXTRA_INSTRUCTIONS,
        "rfq_signature": RFQ_SIGNATURE,
        # Kept for compatibility with older saved settings and env defaults.
        "rfq_default_deadline": RFQ_DEFAULT_DEADLINE,
        "rfq_extra_instructions": RFQ_EXTRA_INSTRUCTIONS,
    }


def _clean_text(key, value):
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text[:TEXT_LIMITS[key]]


def _clean_choice(value, allowed, default):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text in allowed:
        return text
    if allowed == TONE_OPTIONS:
        raw = str(value or "").lower()
        if "formal" in raw:
            return "formal"
        if "technical" in raw:
            return "technical"
        if "friendly" in raw:
            return "friendly"
    return default


def _clean_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _clean_requirements(value):
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        items = value
    else:
        items = []
    cleaned = []
    for item in items:
        key = str(item or "").strip()
        if key in REQUIREMENT_OPTIONS and key not in cleaned:
            cleaned.append(key)
    return cleaned or list(DEFAULT_REQUIREMENTS)


def _read_settings_file():
    try:
        with open(SETTINGS_JSON, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_settings_file(data):
    directory = os.path.dirname(os.path.abspath(SETTINGS_JSON))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, SETTINGS_JSON)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _merge_rfq_settings(base, rfq):
    settings = dict(base)
    if not isinstance(rfq, dict):
        return settings

    for key in ("buyer_name", "buyer_title", "buyer_company", "rfq_company_intro", "rfq_signature", "rfq_buyer_notes", "rfq_default_deadline"):
        if key in rfq:
            settings[key] = _clean_text(key, rfq.get(key))

    # Older installs stored this as "Extra Instructions".
    if "rfq_buyer_notes" not in rfq and "rfq_extra_instructions" in rfq:
        settings["rfq_buyer_notes"] = _clean_text("rfq_buyer_notes", rfq.get("rfq_extra_instructions"))
    settings["rfq_extra_instructions"] = settings["rfq_buyer_notes"]

    if "rfq_tone" in rfq:
        settings["rfq_tone"] = _clean_choice(rfq.get("rfq_tone"), TONE_OPTIONS, settings["rfq_tone"])
    if "rfq_length" in rfq:
        settings["rfq_length"] = _clean_choice(rfq.get("rfq_length"), LENGTH_OPTIONS, settings["rfq_length"])
    if "rfq_urgency" in rfq:
        settings["rfq_urgency"] = _clean_choice(rfq.get("rfq_urgency"), URGENCY_OPTIONS, settings["rfq_urgency"])

    for key in ("rfq_repeat_orders", "rfq_vendor_deadline", "rfq_casual"):
        if key in rfq:
            settings[key] = _clean_bool(rfq.get(key))

    if "rfq_requirements" in rfq:
        settings["rfq_requirements"] = _clean_requirements(rfq.get("rfq_requirements"))

    if not settings["buyer_name"]:
        settings["buyer_name"] = CUSTOMER_NAME
    if not settings["buyer_title"]:
        settings["buyer_title"] = CUSTOMER_TITLE
    if not settings["buyer_company"]:
        settings["buyer_company"] = CUSTOMER_COMPANY
    if not settings["rfq_company_intro"]:
        settings["rfq_company_intro"] = _default_company_intro()
    if not settings["rfq_signature"]:
        settings["rfq_signature"] = RFQ_SIGNATURE
    return settings


def get_rfq_settings():
    data = _read_settings_file()
    rfq = data.get("rfq", data)
    return _merge_rfq_settings(default_rfq_settings(), rfq)


def update_rfq_settings(updates):
    settings = _merge_rfq_settings(get_rfq_settings(), updates or {})
    data = _read_settings_file()
    data["rfq"] = settings
    _write_settings_file(data)
    return settings


def requirement_labels(settings):
    return [REQUIREMENT_OPTIONS[key] for key in settings.get("rfq_requirements", []) if key in REQUIREMENT_OPTIONS]


def tone_label(settings):
    return TONE_OPTIONS.get(settings.get("rfq_tone"), TONE_OPTIONS["direct"])


def length_label(settings):
    return LENGTH_OPTIONS.get(settings.get("rfq_length"), LENGTH_OPTIONS["short"])


def urgency_label(settings):
    if not settings.get("rfq_vendor_deadline"):
        return URGENCY_OPTIONS["low"]
    return URGENCY_OPTIONS.get(settings.get("rfq_urgency"), URGENCY_OPTIONS["normal"])
