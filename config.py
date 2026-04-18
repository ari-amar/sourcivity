"""Central configuration for Sourcivity — all customer-specific values from .env"""
import os
from dotenv import load_dotenv

# Load customer-specific .env if ENV_FILE is set, otherwise default .env in sourcivity/
env_file = os.environ.get("ENV_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
load_dotenv(env_file, override=True)

# --- LLM (Cerebras — OpenAI-compatible) ---
CEREBRAS_API_KEY = os.environ["CEREBRAS_API_KEY"]
CEREBRAS_BASE_URL = os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-3-235b-a22b-instruct-2507")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/home/ubuntu/openclaw-workspace")
QUOTES_CSV = os.path.join(WORKSPACE_DIR, "quotes", "quote-tracker.csv")
COMMS_DIR = os.path.join(WORKSPACE_DIR, "comms")
CREDENTIALS_DIR = os.path.join(WORKSPACE_DIR, "credentials")
SYNC_SCRIPT = os.path.join(WORKSPACE_DIR, "sync_to_sheets.py")

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

# --- Brave Search ---
BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]

# --- Server ---
SERVE_PORT = int(os.environ.get("SERVE_PORT", "3001"))
DEMO_MODE = os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")

# --- CSV Schema ---
CSV_COLUMNS = [
    "Category", "Date", "Supplier", "Part/Service", "Quoted Price", "Unit",
    "Lead Time", "MOQ", "Payment Terms", "Valid Until", "Status", "Latest"
]
CSV_KEYS = [
    "category", "date", "supplier", "partService", "quotedPrice", "unit",
    "leadTime", "moq", "paymentTerms", "validUntil", "status", "notes"
]
CATEGORIES = [
    "Flow Measurement & Control",
    "Valves & Nozzles",
    "Metals & Alloys",
    "Power Transmission",
    "Pneumatics",
    "Fasteners",
]
