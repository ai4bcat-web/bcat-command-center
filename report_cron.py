"""
report_cron.py — Railway cron entry point for the weekly Amazon trip report.

Runs once and exits.  Railway's cron service calls this on schedule.

Reporting window
────────────────
Each report covers the most recently completed Amazon weekly window: Sunday–Saturday.

The job runs on Sunday morning, reporting on the week that ended the day before (Saturday).

Example: job fires Sunday Apr 12 → reports on Apr 5 (Sun) through Apr 11 (Sat).

Railway cron schedule:  0 14 * * 0
Timezone note:          Railway cron runs in UTC.
                        8:00 AM CST (UTC-6) = 14:00 UTC
                        8:00 AM CDT (UTC-5) = 13:00 UTC
                        Use 0 14 * * 0 year-round (1h drift in summer is acceptable).
                        The "0" at the end means Sunday only (not every day).

Start command (Railway cron service):
    bash start_report_cron.sh

Required Railway environment variables:
    DATABASE_URL              — set automatically by Railway Postgres add-on
    REPORT_RECIPIENT_EMAIL    — email address to receive the driver reports
    DISCORD_WEBHOOK_URL       — (optional) Discord webhook for status notifications

Optional:
    REPORT_WEEK_ENDING        — override the reporting window; set to the Saturday
                                end date (YYYY-MM-DD) to report on a specific week
                                e.g. REPORT_WEEK_ENDING=2026-04-11
    REPORT_DRY_RUN            — "true" to generate PDFs but skip email + Discord
    REPORT_FORCE_RESEND       — "true" to bypass idempotency and resend
    REPORT_DRIVER_NAMES       — comma-separated driver allow-list
    REPORT_DISCORD_WEBHOOK_URL— separate webhook for report notifications
                                (falls back to DISCORD_WEBHOOK_URL)
    REPORT_OUTPUT_DIR         — directory for generated PDFs (default: /tmp/trip_reports)

Exit codes:
    0 — all driver reports sent successfully
    1 — one or more driver reports failed

Manual test run:
    DATABASE_URL=<url> REPORT_RECIPIENT_EMAIL=you@example.com python report_cron.py

Dry run (generates PDFs, no email, no Discord POST):
    DATABASE_URL=<url> REPORT_RECIPIENT_EMAIL=x REPORT_DRY_RUN=true python report_cron.py

Run for a specific week (supply the Saturday end date):
    DATABASE_URL=<url> REPORT_RECIPIENT_EMAIL=x \\
        REPORT_WEEK_ENDING=2026-04-11 python report_cron.py
"""

import logging
import os
import sys
from pathlib import Path

# ── path + env setup ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = '%(asctime)s  %(levelname)-8s  %(name)s — %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    stream  = sys.stdout,
)
log = logging.getLogger('report_cron')


# ── Flask app + DB setup ──────────────────────────────────────────────────────

def _init_app():
    """Bootstrap the Flask app so SQLAlchemy models are available."""
    database_url = os.getenv('DATABASE_URL', '').strip()
    if not database_url:
        log.warning("DATABASE_URL not set — running in CSV-only mode (no DB records written).")
        return None

    try:
        import config
        from dashboard import app
        return app
    except Exception as exc:
        log.error("Failed to initialise Flask app: %s", exc, exc_info=True)
        return None


def _ensure_tables(app):
    """Create report_job_runs / driver_report_runs tables if they do not exist."""
    if not app:
        return
    try:
        from sqlalchemy import inspect as _si
        from extensions import db
        with app.app_context():
            inspector = _si(db.engine)
            if not inspector.has_table('report_job_runs'):
                db.create_all()
                log.info("DB tables created (report_job_runs, driver_report_runs).")
    except Exception as exc:
        log.warning("Table auto-create skipped: %s", exc)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    week_ending = os.getenv('REPORT_WEEK_ENDING', '').strip()

    log.info("report_cron starting...")
    log.info("RECIPIENT set  : %s", bool(os.getenv('REPORT_RECIPIENT_EMAIL')))
    log.info("DB set         : %s", bool(os.getenv('DATABASE_URL')))
    log.info("DRY RUN        : %s", os.getenv('REPORT_DRY_RUN', 'false'))
    log.info("WEEK ENDING    : %s", week_ending or '(auto-resolve Sun–Sat)')

    app = _init_app()
    _ensure_tables(app)

    from automation.trip_report.job import WeeklyTripHistoryReportJob

    job     = WeeklyTripHistoryReportJob(app=app)
    success = job.run(week_ending=week_ending or None)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
