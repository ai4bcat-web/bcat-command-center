"""
automation/gmail_ingestor/reader.py

Gmail API reader — authenticates with gmail.readonly scope and searches the
ai4bcat@gmail.com inbox for Amazon Relay trip booking emails.

Uses a separate token file (gmail_reader_token.json / GMAIL_READER_TOKEN_JSON)
from the send-only EmailService so the two credential flows are independent.

Public API:
  build_gmail_reader_service() -> Resource
  search_trip_booking_emails(service, max_results, after_date) -> list[dict]
  fetch_message_content(service, message_id) -> dict
"""

import base64
import logging
import os
import sys
from datetime import datetime, timedelta
from email import message_from_bytes
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

log = logging.getLogger("gmail_ingestor.reader")

# gmail.readonly + gmail.send so one re-auth covers both use-cases.
# The send scope is already authorised for the main EmailService token, but
# the reader token is independent and carries both so it can be used standalone.
READER_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

_HERE = Path(__file__).resolve().parent.parent.parent   # project root
_READER_TOKEN_PATH = _HERE / "gmail_reader_token.json"
_CREDS_PATH        = _HERE / "credentials.json"

# Gmail search query — matches subject lines like:
#   "Load Board - Trip 114MKFP5V booked"
#   "Load Board Trip booked"
#   "Trip booked"
TRIP_BOOKING_QUERY = (
    'subject:"Load Board" OR subject:"Trip booked" OR '
    'subject:"trip booked" OR subject:"booked"'
)


def _write_env_credentials() -> None:
    """Write gmail_reader_token.json / credentials.json from env if files are missing."""
    reader_token_env = os.getenv("GMAIL_READER_TOKEN_JSON", "").strip()
    creds_env        = os.getenv("GMAIL_CREDS_JSON", "").strip()

    if reader_token_env and not _READER_TOKEN_PATH.exists():
        _READER_TOKEN_PATH.write_text(
            base64.b64decode(reader_token_env).decode()
        )
        log.info("gmail_reader_token.json written from GMAIL_READER_TOKEN_JSON env var.")

    if creds_env and not _CREDS_PATH.exists():
        _CREDS_PATH.write_text(
            base64.b64decode(creds_env).decode()
        )
        log.info("credentials.json written from GMAIL_CREDS_JSON env var.")


def build_gmail_reader_service():
    """
    Build and return an authenticated Gmail API service (v1) with readonly scope.

    Token is loaded from:
      1. GMAIL_READER_TOKEN_JSON env var (base64-encoded JSON, used on Railway)
      2. gmail_reader_token.json file in the project root (used locally)

    On first run locally (no token), opens a browser for OAuth consent.
    """
    _write_env_credentials()

    creds = None
    if _READER_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_READER_TOKEN_PATH), READER_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing Gmail reader credentials...")
            creds.refresh(Request())
        else:
            if not _CREDS_PATH.exists():
                raise RuntimeError(
                    "credentials.json not found and GMAIL_CREDS_JSON env var not set. "
                    "Download OAuth2 credentials from Google Cloud Console."
                )
            log.info("No Gmail reader token found — opening browser for OAuth consent...")
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), READER_SCOPES)
            creds = flow.run_local_server(port=0)

        _READER_TOKEN_PATH.write_text(creds.to_json())
        log.info("Gmail reader token saved to %s", _READER_TOKEN_PATH)

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def search_trip_booking_emails(
    service,
    max_results: int = 2000,
    after_date: datetime | None = None,
) -> list[dict]:
    """
    Search the inbox for trip booking emails.

    Args:
        service:     Gmail API resource (from build_gmail_reader_service).
        max_results: Maximum number of messages to return.
        after_date:  Only return messages received after this datetime.
                     Defaults to 30 days ago if not specified.

    Returns:
        List of message stubs: [{"id": "...", "threadId": "..."}, ...]
    """
    if after_date is not None:
        # Gmail uses epoch seconds for the 'after:' operator
        after_epoch = int(after_date.timestamp())
        query = f"{TRIP_BOOKING_QUERY} after:{after_epoch}"
    else:
        query = TRIP_BOOKING_QUERY  # no date filter — search all history

    log.info("Searching Gmail with query: %s", query)

    messages = []
    page_token = None

    while True:
        kwargs: dict = dict(userId="me", q=query, maxResults=min(max_results, 500))
        if page_token:
            kwargs["pageToken"] = page_token

        response = service.users().messages().list(**kwargs).execute()
        batch = response.get("messages", [])
        messages.extend(batch)
        log.debug("  Page returned %d messages (total so far: %d)", len(batch), len(messages))

        page_token = response.get("nextPageToken")
        if not page_token or len(messages) >= max_results:
            break

    log.info("Found %d trip booking email candidates.", len(messages))
    return messages[:max_results]


def fetch_message_content(service, message_id: str) -> dict:
    """
    Fetch full content of a Gmail message.

    Returns dict with:
      message_id, thread_id, subject, received_at (datetime),
      body_text (plain text), snippet
    """
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers   = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject   = headers.get("subject", "")
    date_str  = headers.get("date", "")
    thread_id = msg.get("threadId", "")
    snippet   = msg.get("snippet", "")

    # Parse received date
    received_at = _parse_date_header(date_str)

    # Decode body
    body_text = _decode_body(msg.get("payload", {}))

    return {
        "message_id":  message_id,
        "thread_id":   thread_id,
        "subject":     subject,
        "received_at": received_at,
        "body_text":   body_text,
        "snippet":     snippet,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_date_header(date_str: str) -> datetime | None:
    """Parse RFC 2822 date header to datetime (UTC)."""
    if not date_str:
        return None
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        # Normalize to UTC naive
        if dt.tzinfo:
            import datetime as dt_mod
            dt = dt.astimezone(dt_mod.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        log.warning("Could not parse date header: %r", date_str)
        return None


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    # Multipart — recurse into parts, prefer text/plain
    parts = payload.get("parts", [])
    plain = ""
    html  = ""
    for part in parts:
        sub_type = part.get("mimeType", "")
        sub_text = _decode_body(part)
        if sub_type == "text/plain":
            plain = sub_text
        elif sub_type == "text/html":
            html = sub_text
        elif sub_type.startswith("multipart/") and sub_text:
            plain = sub_text  # use nested result

    return plain or _strip_html(html)


def _strip_html(html: str) -> str:
    """Very light HTML stripper — removes tags, decodes common entities."""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text).strip()
    return text
