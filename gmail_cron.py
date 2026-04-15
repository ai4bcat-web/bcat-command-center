"""
gmail_cron.py — Railway cron entry point for Gmail trip booking email ingestion.

Runs once and exits. Railway's cron service calls this on schedule.

What it does:
  1. Authenticates with Gmail (readonly scope)
  2. Searches ai4bcat@gmail.com for trip booking emails (last 7 days)
  3. Skips already-imported messages (dedup by Gmail message ID)
  4. Parses each email for: Trip ID, Estimated Payout, Origin, Destination, dates
  5. Writes parsed rows to:
     a. GmailTripEmail DB table (persistent record, idempotency source)
     b. "BCAT Master Trip Payouts" Google Sheet (if SHEETS_SERVICE_ACCOUNT_JSON set)

Railway cron schedule:  0 * * * *
Timezone note:          Every hour, year-round.
                        Adjust GMAIL_LOOKBACK_DAYS if you want a wider search window.

Start command (Railway cron service):
    bash start_gmail_cron.sh

Required environment variables:
    GMAIL_READER_TOKEN_JSON     — base64-encoded gmail_reader_token.json (readonly OAuth token)
    GMAIL_CREDS_JSON            — base64-encoded credentials.json (OAuth client secrets)
    DATABASE_URL                — PostgreSQL connection string

Optional:
    SHEETS_SERVICE_ACCOUNT_JSON — base64-encoded service account JSON (enables Sheet writes)
    SHEETS_SHARE_EMAIL          — email address to share created sheets with
    SHEETS_FOLDER_ID            — Google Drive folder ID for created sheets
    MASTER_SHEET_TITLE          — spreadsheet title (default: "BCAT Master Trip Payouts")
    MASTER_SHEET_ID             — open existing sheet by ID instead of title
    GMAIL_LOOKBACK_DAYS         — days of Gmail history to search (default: 7)
    GMAIL_DRY_RUN               — "true" to parse without writing to DB or Sheets

Exit codes:
    0 — success (even if some parse failures — those are logged and recorded)
    1 — fatal error (auth failure, DB unreachable)

First-run setup (local):
    1. Set GMAIL_CREDS_JSON (or place credentials.json in project root)
    2. Run: python gmail_cron.py
       → Opens browser for Gmail readonly OAuth consent
       → Saves gmail_reader_token.json
    3. Base64-encode: base64 -i gmail_reader_token.json | tr -d '\\n'
    4. Set GMAIL_READER_TOKEN_JSON in Railway environment variables
"""

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    stream  = sys.stdout,
)
log = logging.getLogger("gmail_cron")


def _init_app():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        log.warning("DATABASE_URL not set — DB records will not be written.")
        return None
    try:
        from dashboard import app
        return app
    except Exception as e:
        log.error("Flask app init failed: %s", e, exc_info=True)
        return None


def main() -> int:
    lookback_days = int(os.getenv("GMAIL_LOOKBACK_DAYS", "7"))
    dry_run       = os.getenv("GMAIL_DRY_RUN", "false").strip().lower() in ("true", "1", "yes")

    log.info("gmail_cron starting...")
    log.info("LOOKBACK_DAYS   : %d", lookback_days)
    log.info("DRY_RUN         : %s", dry_run)
    log.info("DB set          : %s", bool(os.getenv("DATABASE_URL")))
    log.info("Sheets enabled  : %s", bool(os.getenv("SHEETS_SERVICE_ACCOUNT_JSON")))

    app = _init_app()

    try:
        from automation.gmail_ingestor.ingestor import GmailTripEmailIngestor
        ingestor = GmailTripEmailIngestor(app=app, dry_run=dry_run)
        result   = ingestor.run(lookback_days=lookback_days)
    except Exception as e:
        log.error("Gmail ingestor failed: %s", e, exc_info=True)
        return 1

    log.info("gmail_cron complete | %s", result.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
