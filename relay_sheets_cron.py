"""
relay_sheets_cron.py — Railway cron entry point for Relay → Sheets sync.

Runs once and exits. Railway's cron service calls this 3× per day.

What it does:
  1. Loads Amazon Relay trips from the DB (current week, via relay_current_week table)
  2. Groups trips by driver and week
  3. For each driver/week:
     a. Opens (or creates) the driver's Google Spreadsheet
     b. Opens (or creates) the weekly tab (e.g. "Apr 5 – Apr 10")
     c. Writes all trips for that driver/week
     d. Looks up estimated payout from the Master Sheet by Trip ID
     e. Logs any unmatched Trip IDs
  4. Writes an audit record to RelaySheetSyncRun DB table

Railway cron schedule:  0 14,19,1 * * *
Timezone (UTC):         14:00 = 8:00 AM CST  (after relay fetch at 13:30)
                        19:00 = 1:00 PM CST
                        01:00 = 7:00 PM CST
Adjust RELAY_SHEETS_SCHEDULE in Railway if you want different times.

Start command (Railway cron service):
    bash start_relay_sheets_cron.sh

Required environment variables:
    DATABASE_URL                    — PostgreSQL connection string
    SHEETS_SERVICE_ACCOUNT_JSON     — base64-encoded Google service account JSON

Optional:
    SHEETS_SHARE_EMAIL              — share created sheets with this email (human owner)
    SHEETS_FOLDER_ID                — Google Drive folder for all driver sheets
    DRIVER_SHEET_PREFIX             — prefix for spreadsheet titles (default: "BCAT")
    MASTER_SHEET_TITLE              — master sheet title (default: "BCAT Master Trip Payouts")
    MASTER_SHEET_ID                 — open master sheet by ID (skip title search)
    RELAY_SHEETS_DRY_RUN            — "true" to log without writing
    RELAY_SHEETS_WINDOW_START       — override window start YYYY-MM-DD
    RELAY_SHEETS_WINDOW_END         — override window end YYYY-MM-DD

Exit codes:
    0 — completed (even with partial errors — those are logged + recorded in DB)
    1 — fatal startup failure
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
log = logging.getLogger("relay_sheets_cron")


def _init_app():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        log.warning("DATABASE_URL not set — running without DB (CSV fallback, no audit records).")
        return None
    try:
        from dashboard import app
        return app
    except Exception as e:
        log.error("Flask app init failed: %s", e, exc_info=True)
        return None


def main() -> int:
    dry_run      = os.getenv("RELAY_SHEETS_DRY_RUN", "false").strip().lower() in ("true", "1", "yes")
    window_start = os.getenv("RELAY_SHEETS_WINDOW_START", "").strip() or None
    window_end   = os.getenv("RELAY_SHEETS_WINDOW_END",   "").strip() or None

    log.info("relay_sheets_cron starting...")
    log.info("DRY_RUN        : %s", dry_run)
    log.info("WINDOW         : %s – %s", window_start or "(auto)", window_end or "(auto)")
    log.info("DB set         : %s", bool(os.getenv("DATABASE_URL")))
    log.info("Sheets enabled : %s", bool(os.getenv("SHEETS_SERVICE_ACCOUNT_JSON")))

    if not os.getenv("SHEETS_SERVICE_ACCOUNT_JSON"):
        log.error("SHEETS_SERVICE_ACCOUNT_JSON not set — cannot write to Google Sheets. Exiting.")
        return 1

    app = _init_app()

    try:
        from automation.relay_sheets_sync.syncer import RelaySheetsSyncer
        syncer = RelaySheetsSyncer(app=app)
        result = syncer.run(
            window_start = window_start,
            window_end   = window_end,
            dry_run      = dry_run,
        )
    except Exception as e:
        log.error("Relay sheets sync failed: %s", e, exc_info=True)
        return 1

    log.info("relay_sheets_cron complete | %s", result.summary())
    return 0 if result.status in ("completed", "completed_with_errors") else 1


if __name__ == "__main__":
    sys.exit(main())
