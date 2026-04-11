#!/usr/bin/env python3
"""
Sync quotes/quote-tracker.csv → Google Sheets (one-way push).

Usage:
    # Step 1 (first time only): Get auth URL
    python3 sync_to_sheets.py --auth

    # Step 2 (first time only): Paste the redirect URL to complete auth
    python3 sync_to_sheets.py --auth-redirect "http://localhost?code=..."

    # Create a new sheet and sync
    python3 sync_to_sheets.py --new "RFQ Tracker"

    # Sync to existing sheet (after first setup)
    python3 sync_to_sheets.py
"""

import argparse
import csv
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
CLIENT_SECRET = os.path.join(CREDENTIALS_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "token.json")
SHEET_ID_FILE = os.path.join(CREDENTIALS_DIR, "sheet_id.txt")
FLOW_STATE_FILE = os.path.join(CREDENTIALS_DIR, "flow_state.json")
CSV_PATH = os.path.join(BASE_DIR, "quotes", "quote-tracker.csv")

REDIRECT_URI = "http://localhost:1"


def check_client_secret():
    if not os.path.exists(CLIENT_SECRET):
        print(f"ERROR: Client secret not found at {CLIENT_SECRET}")
        sys.exit(1)


def start_auth():
    """Generate an authorization URL for the user to visit."""
    check_client_secret()
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET, SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )

    # Save PKCE code_verifier so step 2 can complete the exchange
    with open(FLOW_STATE_FILE, "w") as f:
        json.dump({
            "state": state,
            "code_verifier": flow.code_verifier,
        }, f)

    print("\n=== Step 1: Authorize with Google ===\n")
    print("Open this URL in your browser:\n")
    print(auth_url)
    print("\nAfter authorizing, your browser will try to redirect to localhost")
    print("and likely show an error page — that's normal.")
    print("\nCopy the FULL URL from the browser address bar and run:\n")
    print('  python3 sync_to_sheets.py --auth-redirect "PASTE_URL_HERE"')
    print()


def complete_auth(redirect_url):
    """Complete auth by extracting the code from the redirect URL."""
    check_client_secret()

    # Load saved PKCE code_verifier from step 1
    if not os.path.exists(FLOW_STATE_FILE):
        print("ERROR: No pending auth flow found. Run --auth first.")
        sys.exit(1)

    with open(FLOW_STATE_FILE, "r") as f:
        flow_state = json.load(f)

    # Extract code from redirect URL
    parsed = urlparse(redirect_url)
    code = parse_qs(parsed.query).get("code", [None])[0]
    if not code:
        print("ERROR: No authorization code found in URL.")
        print("Make sure you copied the full URL including ?code=...")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET, SCOPES, redirect_uri=REDIRECT_URI
    )
    # Restore the code_verifier so PKCE validation passes
    flow.code_verifier = flow_state.get("code_verifier")
    flow.fetch_token(code=code)
    creds = flow.credentials

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    # Clean up flow state
    os.remove(FLOW_STATE_FILE)

    print("Authorization successful! Token saved.")
    print('Now run: python3 sync_to_sheets.py --new "RFQ Tracker"')


def get_credentials():
    """Get valid credentials from saved token."""
    if not os.path.exists(TOKEN_FILE):
        print("Not authenticated yet. Run: python3 sync_to_sheets.py --auth")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            print("Token expired. Re-authenticate: python3 sync_to_sheets.py --auth")
            sys.exit(1)

    return creds


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    return rows


def get_sheet_id():
    if not os.path.exists(SHEET_ID_FILE):
        return None
    with open(SHEET_ID_FILE, "r") as f:
        return f.read().strip()


def save_sheet_id(sheet_id):
    with open(SHEET_ID_FILE, "w") as f:
        f.write(sheet_id)


def create_spreadsheet(service, title):
    body = {"properties": {"title": title}}
    spreadsheet = service.spreadsheets().create(body=body).execute()
    sheet_id = spreadsheet["spreadsheetId"]
    print(f"Created spreadsheet: {title}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    return sheet_id


def push_csv_to_sheet(service, spreadsheet_id, rows):
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range="Sheet1", body={}
    ).execute()

    if not rows:
        print("CSV is empty. Sheet cleared.")
        return

    result = (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A1",
            valueInputOption="RAW",
            body={"values": rows},
        )
        .execute()
    )

    updated = result.get("updatedRows", 0)
    print(f"Synced {updated} rows ({updated - 1} data rows + header) to Google Sheets.")


def format_header(service, spreadsheet_id):
    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": 0,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def main():
    parser = argparse.ArgumentParser(description="Sync quote-tracker.csv to Google Sheets")
    parser.add_argument("--auth", action="store_true", help="Start OAuth flow (prints URL)")
    parser.add_argument("--auth-redirect", metavar="URL", help="Complete OAuth with redirect URL")
    parser.add_argument("--new", metavar="TITLE", help="Create a new spreadsheet with this title")
    parser.add_argument("--sheet-id", metavar="ID", help="Use a specific spreadsheet ID")
    args = parser.parse_args()

    # Auth flow (two-step)
    if args.auth:
        start_auth()
        return

    if args.auth_redirect:
        complete_auth(args.auth_redirect)
        return

    # Normal sync
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    spreadsheet_id = args.sheet_id
    if args.new:
        spreadsheet_id = create_spreadsheet(service, args.new)
        save_sheet_id(spreadsheet_id)
    elif not spreadsheet_id:
        spreadsheet_id = get_sheet_id()

    if not spreadsheet_id:
        print("No spreadsheet configured. Run with --new to create one:")
        print('  python3 sync_to_sheets.py --new "RFQ Tracker"')
        sys.exit(1)

    save_sheet_id(spreadsheet_id)

    rows = read_csv(CSV_PATH)
    push_csv_to_sheet(service, spreadsheet_id, rows)

    if args.new:
        format_header(service, spreadsheet_id)
        print("Header formatted (bold + frozen).")

    print("Done!")


if __name__ == "__main__":
    main()
