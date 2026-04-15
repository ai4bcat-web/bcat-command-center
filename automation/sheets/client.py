"""
automation/sheets/client.py

Google Sheets client using user OAuth2 credentials — the same OAuth app
already configured for Gmail. No service account or service account key needed.

Auth flow:
  - Uses credentials.json (OAuth client secrets, same file as Gmail)
  - Stores Sheets token in sheets_token.json / SHEETS_TOKEN_JSON env var
  - On first local run, opens browser for OAuth consent (Sheets + Drive scopes)
  - On Railway, token is read from SHEETS_TOKEN_JSON env var (base64-encoded)

Sheets created this way are owned by ai4bcat@gmail.com and appear directly
in Google Drive — no sharing step required.

Configuration (env vars):
  SHEETS_TOKEN_JSON   — base64-encoded sheets_token.json (required on Railway)
  GMAIL_CREDS_JSON    — base64-encoded credentials.json (shared with Gmail OAuth)

Public API:
  get_client()                                -> gspread.Client
  get_or_create_spreadsheet(title)            -> gspread.Spreadsheet
  ensure_worksheet(spreadsheet, title, cols)  -> gspread.Worksheet

First-run setup (local):
  1. Ensure credentials.json is in the project root (or set GMAIL_CREDS_JSON)
  2. Run: python -c "from automation.sheets.client import get_client; get_client()"
     → Opens browser for Sheets + Drive OAuth consent
     → Saves sheets_token.json
  3. Base64-encode: base64 -i sheets_token.json | tr -d '\\n'
  4. Set SHEETS_TOKEN_JSON in Railway environment variables
"""

import base64
import logging
import os
from pathlib import Path

log = logging.getLogger("sheets.client")

_HERE             = Path(__file__).resolve().parent.parent.parent   # project root
_SHEETS_TOKEN     = _HERE / "sheets_token.json"
_CREDS_PATH       = _HERE / "credentials.json"

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _write_env_credentials() -> None:
    """Write sheets_token.json / credentials.json from env vars if files are missing."""
    token_env = os.getenv("SHEETS_TOKEN_JSON", "").strip()
    creds_env = os.getenv("GMAIL_CREDS_JSON",  "").strip()

    if token_env and not _SHEETS_TOKEN.exists():
        _SHEETS_TOKEN.write_text(base64.b64decode(token_env + "==").decode())
        log.info("sheets_token.json written from SHEETS_TOKEN_JSON env var.")

    if creds_env and not _CREDS_PATH.exists():
        _CREDS_PATH.write_text(base64.b64decode(creds_env + "==").decode())
        log.info("credentials.json written from GMAIL_CREDS_JSON env var.")


def _build_credentials():
    """Load, refresh, or create user OAuth credentials for Sheets + Drive."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    _write_env_credentials()

    creds = None
    if _SHEETS_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_SHEETS_TOKEN), SHEETS_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Sheets OAuth token...")
            creds.refresh(Request())
        else:
            if not _CREDS_PATH.exists():
                raise RuntimeError(
                    "credentials.json not found and GMAIL_CREDS_JSON env var not set.\n"
                    "Download OAuth2 credentials from Google Cloud Console and place in project root.\n"
                    "Then run locally to authorize: "
                    "python -c \"from automation.sheets.client import get_client; get_client()\""
                )
            log.info("No Sheets token found — opening browser for OAuth consent...")
            flow  = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), SHEETS_SCOPES)
            creds = flow.run_local_server(port=0)

        _SHEETS_TOKEN.write_text(creds.to_json())
        log.info("Sheets token saved to %s", _SHEETS_TOKEN)

    return creds


def get_client():
    """Return an authenticated gspread client using user OAuth credentials."""
    import gspread
    creds  = _build_credentials()
    client = gspread.authorize(creds)
    log.debug("gspread client authenticated via user OAuth.")
    return client


def get_or_create_spreadsheet(title: str):
    """
    Open an existing spreadsheet by title or create a new one.

    The spreadsheet is owned by the authenticated user (ai4bcat@gmail.com)
    and appears directly in their Google Drive.

    If SHEETS_FOLDER_ID is set, new sheets are moved into that Drive folder.
    """
    import gspread

    client    = get_client()
    folder_id = os.getenv("SHEETS_FOLDER_ID", "").strip() or None

    try:
        ss = client.open(title)
        log.info("Opened existing spreadsheet: %r (id=%s)", title, ss.id)
        return ss
    except gspread.SpreadsheetNotFound:
        pass

    ss = client.create(title)
    log.info("Created new spreadsheet: %r (id=%s)", title, ss.id)

    if folder_id:
        _move_to_folder(ss.id, folder_id, _build_credentials())

    return ss


def ensure_worksheet(
    spreadsheet,
    title:   str,
    headers: list[str] | None = None,
):
    """
    Return a worksheet by title, creating it if it does not exist.
    If created and headers are provided, writes them as the first row.
    """
    try:
        ws = spreadsheet.worksheet(title)
        log.debug("Opened worksheet %r in %r", title, spreadsheet.title)
        return ws
    except Exception:
        pass

    ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=30)
    log.info("Created worksheet %r in %r", title, spreadsheet.title)

    if headers:
        ws.append_row(headers, value_input_option="USER_ENTERED")

    return ws


# ── Internal helpers ──────────────────────────────────────────────────────────

def _move_to_folder(spreadsheet_id: str, folder_id: str, creds) -> None:
    """Move a spreadsheet into a Google Drive folder via Drive API."""
    try:
        from googleapiclient.discovery import build as _build
        drive = _build("drive", "v3", credentials=creds, cache_discovery=False)

        file_meta    = drive.files().get(fileId=spreadsheet_id, fields="parents").execute()
        prev_parents = ",".join(file_meta.get("parents", []))

        drive.files().update(
            fileId        = spreadsheet_id,
            addParents    = folder_id,
            removeParents = prev_parents,
            fields        = "id, parents",
        ).execute()
        log.info("Moved spreadsheet %s to folder %s", spreadsheet_id, folder_id)
    except Exception as e:
        log.warning("Could not move spreadsheet to folder: %s", e)
