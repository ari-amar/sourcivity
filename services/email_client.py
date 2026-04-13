"""Email send/receive via Himalaya CLI."""
import json
import subprocess
import sys
import os
import tempfile

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


def get_attachment_text(email_id):
    """Download attachments for an email and extract text from PDFs/spreadsheets.
    Returns combined text string, or empty string if none found."""
    texts = []
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            _run(["attachment", "download", str(email_id), "--output-dir", tmpdir])
        except Exception as e:
            print(f"Attachment download failed for {email_id}: {e}")
            return ""

        for fname in os.listdir(tmpdir):
            fpath = os.path.join(tmpdir, fname)
            ext = fname.lower().rsplit(".", 1)[-1] if "." in fname else ""
            try:
                if ext == "pdf":
                    import pdfplumber
                    with pdfplumber.open(fpath) as pdf:
                        for page in pdf.pages:
                            t = page.extract_text()
                            if t:
                                texts.append(t)
                elif ext in ("xlsx", "xls"):
                    import openpyxl
                    wb = openpyxl.load_workbook(fpath, data_only=True)
                    for ws in wb.worksheets:
                        for row in ws.iter_rows(values_only=True):
                            line = "\t".join(str(c) for c in row if c is not None)
                            if line.strip():
                                texts.append(line)
                elif ext == "csv":
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        texts.append(f.read())
            except Exception as e:
                print(f"Attachment parse failed ({fname}): {e}")

    return "\n".join(texts)


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
