"""Google Sheets sync wrapper."""
import subprocess
from config import SYNC_SCRIPT


def sync():
    """Run sync_to_sheets.py. Returns True on success."""
    try:
        result = subprocess.run(
            ["python3", SYNC_SCRIPT],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Sheets sync failed: {e}")
        return False
