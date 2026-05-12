"""Customer-editable account settings."""
import json
import os
import tempfile

from config import (
    RFQ_DEFAULT_DEADLINE,
    RFQ_EXTRA_INSTRUCTIONS,
    RFQ_SIGNATURE,
    RFQ_TONE,
    SETTINGS_JSON,
)

RFQ_SETTING_FIELDS = {
    "rfq_tone": 160,
    "rfq_signature": 500,
    "rfq_default_deadline": 240,
    "rfq_extra_instructions": 1200,
}


def default_rfq_settings():
    return {
        "rfq_tone": RFQ_TONE,
        "rfq_signature": RFQ_SIGNATURE,
        "rfq_default_deadline": RFQ_DEFAULT_DEADLINE,
        "rfq_extra_instructions": RFQ_EXTRA_INSTRUCTIONS,
    }


def _clean_value(key, value):
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    return text[:RFQ_SETTING_FIELDS[key]]


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


def get_rfq_settings():
    settings = default_rfq_settings()
    data = _read_settings_file()
    rfq = data.get("rfq", data)
    if not isinstance(rfq, dict):
        return settings
    for key in RFQ_SETTING_FIELDS:
        if key in rfq:
            settings[key] = _clean_value(key, rfq.get(key))
    if not settings["rfq_signature"]:
        settings["rfq_signature"] = RFQ_SIGNATURE
    return settings


def update_rfq_settings(updates):
    settings = get_rfq_settings()
    updates = updates or {}
    for key in RFQ_SETTING_FIELDS:
        if key in updates:
            settings[key] = _clean_value(key, updates.get(key))
    if not settings["rfq_signature"]:
        settings["rfq_signature"] = RFQ_SIGNATURE

    data = _read_settings_file()
    data["rfq"] = settings
    _write_settings_file(data)
    return settings
