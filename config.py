"""Central configuration for Sourcivity — all customer-specific values from .env"""
import os
from dotenv import load_dotenv

# Load customer-specific .env if ENV_FILE is set, otherwise default .env in sourcivity/
env_file = os.environ.get("ENV_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
load_dotenv(env_file, override=True)

# --- LLM ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "").strip().lower()
if not LLM_PROVIDER:
    if ANTHROPIC_API_KEY:
        LLM_PROVIDER = "anthropic"
    elif OPENAI_API_KEY:
        LLM_PROVIDER = "openai"
    else:
        LLM_PROVIDER = "cerebras"

_LLM_DEFAULTS = {
    "anthropic": {
        "api_key": ANTHROPIC_API_KEY,
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        "model": "claude-haiku-4-5",
        "fallback_model": "",
        "token_param": "max_tokens",
    },
    "openai": {
        "api_key": OPENAI_API_KEY,
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": "gpt-5-mini",
        "fallback_model": "gpt-5-nano",
        "token_param": "max_completion_tokens",
    },
    "cerebras": {
        "api_key": CEREBRAS_API_KEY,
        "base_url": os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
        "model": "qwen-3-235b-a22b-instruct-2507",
        "fallback_model": "llama3.1-8b",
        "token_param": "max_tokens",
    },
}
if LLM_PROVIDER not in _LLM_DEFAULTS:
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
_llm_defaults = _LLM_DEFAULTS[LLM_PROVIDER]

LLM_API_KEY = os.environ.get("LLM_API_KEY") or _llm_defaults["api_key"]
if not LLM_API_KEY:
    raise RuntimeError(
        "Missing LLM API key. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or LLM_API_KEY plus LLM_BASE_URL."
    )
LLM_BASE_URL = os.environ.get("LLM_BASE_URL") or _llm_defaults["base_url"]
LLM_MODEL = os.environ.get("LLM_MODEL") or _llm_defaults["model"]
_fallback_model = os.environ.get("LLM_FALLBACK_MODEL")
LLM_FALLBACK_MODEL = _llm_defaults["fallback_model"] if _fallback_model is None else _fallback_model.strip()
LLM_TOKEN_PARAM = os.environ.get("LLM_TOKEN_PARAM") or _llm_defaults["token_param"]
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "0"))
LLM_PRIMARY_COOLDOWN_SECONDS = int(os.environ.get("LLM_PRIMARY_COOLDOWN_SECONDS", "300"))

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/ubuntu/openclaw-workspace")
QUOTES_CSV = os.path.join(WORKSPACE_DIR, "quotes", "quote-tracker.csv")
COMMS_DIR = os.path.join(WORKSPACE_DIR, "comms")
CREDENTIALS_DIR = os.path.join(WORKSPACE_DIR, "credentials")
SYNC_SCRIPT = os.path.join(WORKSPACE_DIR, "sync_to_sheets.py")
SETTINGS_JSON = os.environ.get("SETTINGS_JSON", os.path.join(WORKSPACE_DIR, "settings.json"))

# --- Email (via Himalaya CLI — supports Gmail, Outlook/M365, any IMAP/SMTP) ---
HIMALAYA_BIN = os.environ.get("HIMALAYA_BIN", "/tmp/himalaya")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS") or os.environ["GMAIL_ADDRESS"]
EMAIL_DISPLAY_NAME = (
    os.environ.get("EMAIL_DISPLAY_NAME")
    or os.environ.get("GMAIL_DISPLAY_NAME")
    or "Procurement"
)

# --- Customer Identity ---
CUSTOMER_NAME = os.environ.get("CUSTOMER_NAME", "Buyer")
CUSTOMER_FULL_NAME = os.environ.get("CUSTOMER_FULL_NAME", CUSTOMER_NAME)
CUSTOMER_COMPANY = os.environ.get("CUSTOMER_COMPANY", "")
CUSTOMER_TITLE = os.environ.get("CUSTOMER_TITLE", "Procurement Manager")
CUSTOMER_STATE = os.environ.get("CUSTOMER_STATE", "")
RFQ_TONE = os.environ.get("RFQ_TONE", "casual, direct, confident")
RFQ_SIGNATURE = os.environ.get("RFQ_SIGNATURE", f"{CUSTOMER_NAME}\n{CUSTOMER_COMPANY}").strip()
RFQ_DEFAULT_DEADLINE = os.environ.get("RFQ_DEFAULT_DEADLINE", "We're finalizing our vendor list this week.")
RFQ_EXTRA_INSTRUCTIONS = os.environ.get("RFQ_EXTRA_INSTRUCTIONS", "").strip()

# --- Brave Search ---
BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]

# --- Server ---
SERVE_PORT = int(os.environ.get("SERVE_PORT", "3001"))
DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")

# --- CSV Schema ---
CSV_COLUMNS = [
    "Category", "Date", "Supplier", "Part/Service", "Quoted Price", "Unit",
    "Lead Time", "MOQ", "Payment Terms", "Valid Until", "Status", "Latest", "Email"
]
CSV_KEYS = [
    "category", "date", "supplier", "partService", "quotedPrice", "unit",
    "leadTime", "moq", "paymentTerms", "validUntil", "status", "notes", "email"
]
CATEGORIES = [
    "Flow Measurement & Control",
    "Valves & Nozzles",
    "Metals & Alloys",
    "Power Transmission",
    "Pneumatics",
    "Fasteners",
]
