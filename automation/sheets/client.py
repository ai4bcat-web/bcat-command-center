"""
automation/sheets/client.py

Google Sheets client backed by a service account.

A service account is used (not user OAuth) because:
  - No browser / user interaction needed for production/Railway
  - Sheets are "owned" by the service account; share them with
    SHEETS_SHARE_EMAIL so they appear in the right Google Drive.

Configuration (env vars):
  SHEETS_SERVICE_ACCOUNT_JSON   — base64-encoded service account JSON (required)
  SHEETS_SHARE_EMAIL            — email to share all created sheets with
  SHEETS_FOLDER_ID              — Google Drive folder ID to create sheets in (optional)

Public API:
  get_client()                                -> gspread.Client
  get_or_create_spreadsheet(title)            -> gspread.Spreadsheet
  ensure_worksheet(spreadsheet, title, cols)  -> gspread.Worksheet
"""

import base64
import json
import logging
import os
from pathlib import Path

log = logging.getLogger("sheets.client")

_SA_JSON_ENV  = "SHEETS_SERVICE_ACCOUNT_JSON"
_SA_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "sheets_service_account.json"


def _load_service_account_info() -> dict:
    """Load service account credentials from env var or local file."""
    raw = os.getenv(_SA_JSON_ENV, "").strip()
    if raw:
        decoded = base64.b64decode(raw + "==").decode()
        return json.loads(decoded)

    if _SA_FILE_PATH.exists():
        return json.loads(_SA_FILE_PATH.read_text())

    raise RuntimeError(
        f"{_SA_JSON_ENV} env var not set and {_SA_FILE_PATH} not found. "
        "Download a service account JSON from Google Cloud Console → IAM → Service Accounts."
    )


def get_client():
    """Return an authenticated gspread client using the service account."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    sa_info = _load_service_account_info()
    creds   = Credentials.from_service_account_info(sa_info, scopes=scopes)
    client  = gspread.authorize(creds)
    log.debug("gspread client authenticated as %s", sa_info.get("client_email", "?"))
    return client


def get_or_create_spreadsheet(title: str) -> "gspread.Spreadsheet":
    """
    Open an existing spreadsheet by title or create a new one.

    If SHEETS_FOLDER_ID is set, the new sheet is moved into that Drive folder.
    If SHEETS_SHARE_EMAIL is set, the sheet is shared (writer access) with that email.
    """
    import gspread

    client    = get_client()
    folder_id = os.getenv("SHEETS_FOLDER_ID", "").strip() or None
    share_to  = os.getenv("SHEETS_SHARE_EMAIL", "").strip() or None

    # Try to open existing spreadsheet
    try:
        ss = client.open(title)
        log.info("Opened existing spreadsheet: %r (id=%s)", title, ss.id)
        return ss
    except gspread.SpreadsheetNotFound:
        pass

    # Create new spreadsheet
    ss = client.create(title)
    log.info("Created new spreadsheet: %r (id=%s)", title, ss.id)

    # Move to folder if configured
    if folder_id:
        _move_to_folder(client, ss.id, folder_id)

    # Share with human user
    if share_to:
        ss.share(share_to, perm_type="user", role="writer", notify=False)
        log.info("Shared %r with %s", title, share_to)

    return ss


def ensure_worksheet(
    spreadsheet,
    title: str,
    headers: list[str] | None = None,
) -> "gspread.Worksheet":
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

def _move_to_folder(client, spreadsheet_id: str, folder_id: str) -> None:
    """Move a spreadsheet into a Google Drive folder via Drive API."""
    try:
        from googleapiclient.discovery import build as _build
        from google.oauth2.service_account import Credentials

        sa_info = _load_service_account_info()
        creds   = Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        drive = _build("drive", "v3", credentials=creds, cache_discovery=False)

        # Get current parents
        file_meta = drive.files().get(
            fileId=spreadsheet_id, fields="parents"
        ).execute()
        prev_parents = ",".join(file_meta.get("parents", []))

        drive.files().update(
            fileId         = spreadsheet_id,
            addParents     = folder_id,
            removeParents  = prev_parents,
            fields         = "id, parents",
        ).execute()
        log.info("Moved spreadsheet %s to folder %s", spreadsheet_id, folder_id)
    except Exception as e:
        log.warning("Could not move spreadsheet to folder: %s", e)
