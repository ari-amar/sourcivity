"""Email send/receive via Himalaya CLI."""
import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import HIMALAYA_BIN, EMAIL_ADDRESS, EMAIL_DISPLAY_NAME

HIMALAYA = HIMALAYA_BIN


def _run(args, input_text=None):
    """Run a himalaya command, return stdout. Filters WARN lines from stderr."""
    cmd = [HIMALAYA, "--quiet"] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True, input=input_text, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"himalaya error: {result.stderr.strip()}")
    return result.stdout.strip()


def list_inbox(limit=20):
    """List recent inbox emails. Returns list of dicts with id, from, subject, date."""
    try:
        output = _run(["envelope", "list", "-f", "INBOX", "-s", str(limit), "-o", "json"])
        return json.loads(output) if output else []
    except Exception as e:
        print(f"Inbox list failed: {e}")
        return []


def read_email(email_id):
    """Read full email body by ID. Returns text."""
    try:
        return _run(["message", "read", str(email_id)])
    except Exception as e:
        print(f"Email read failed: {e}")
        return ""


def send_email(to, subject, body):
    """Send an email via himalaya template send. Returns True on success."""
    template = f"From: {EMAIL_DISPLAY_NAME} <{EMAIL_ADDRESS}>\nTo: {to}\nSubject: {subject}\n\n{body}"
    try:
        _run(["template", "send"], input_text=template)
        return True
    except Exception as e:
        # Himalaya sends the email but may fail saving to Sent folder via IMAP
        # If the error is about IMAP message/folder, the email was already sent
        err_str = str(e)
        if "cannot add IMAP message" in err_str or "Folder doesn't exist" in err_str:
            print(f"Email sent but Sent folder save failed (ignored): {e}")
            return True
        print(f"Email send failed: {e}")
        return False


def search_inbox(query):
    """Search inbox by query. Uses himalaya filter syntax (from/subject/body patterns).
    Returns list of dicts."""
    try:
        output = _run(["envelope", "list", "-f", "INBOX", "-o", "json",
                        "from", query, "or", "subject", query])
        return json.loads(output) if output else []
    except Exception as e:
        print(f"Inbox search failed: {e}")
        return []
