"""
relay_cron.py — Railway cron entry point for nightly Amazon Relay fetch.

Runs once and exits. Railway's cron service calls this on schedule.

Railway cron schedule:  0 4 * * *
Timezone note:          Railway cron runs in UTC.
                        10:00 PM CST (UTC-6) = 04:00 UTC
                        10:00 PM CDT (UTC-5) = 03:00 UTC
                        Use 0 4 * * * year-round (acceptable 1h drift in summer).

Start command (Railway cron service):
    python relay_cron.py

Required Railway environment variables:
    DATABASE_URL            — set automatically by Railway Postgres add-on
    AMAZON_RELAY_EMAIL      — Amazon Relay login email
    AMAZON_RELAY_PASSWORD   — Amazon Relay login password
    DISCORD_WEBHOOK_URL     — (optional) webhook for success/failure alerts

Optional:
    RELAY_HEADLESS          — "false" to show browser (local debug only)

Exit codes:
    0 — success
    1 — fetch or ingest failed (CAPTCHA, login error, network, etc.)

CAPTCHA / MFA handling:
    If Amazon shows a CAPTCHA or MFA challenge the job exits with code 1,
    sends a Discord alert with instructions, and marks the session status
    as "captcha" in the relay_sessions table.
    To recover: run locally with RELAY_HEADLESS=false, solve the challenge,
    then the fresh session cookies are saved to the DB and Railway resumes.

Manual test run:
    DATABASE_URL=<your_railway_db_url> python relay_cron.py
"""

import asyncio
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.amazon_relay.fetcher  import fetch_relay_csv
from automation.amazon_relay.ingestor import ingest_relay_csv

# ── logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("relay_cron")

# ── config ────────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()


# ── discord notifications ─────────────────────────────────────────────────

def _notify(msg: str, is_error: bool = False) -> None:
    """Post a message to Discord via webhook. No-op if DISCORD_WEBHOOK_URL is unset."""
    if not DISCORD_WEBHOOK_URL:
        return
    prefix = "⚠️ **Amazon Relay nightly fetch FAILED**" if is_error else "✅ **Amazon Relay nightly fetch OK**"
    try:
        body = json.dumps({"content": f"{prefix}\n{msg}"}).encode()
        req  = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        log.info("Discord notification sent.")
    except Exception as e:
        log.warning(f"Discord notify failed: {e}")


# ── main job ──────────────────────────────────────────────────────────────

def main() -> int:
    log.info("=" * 60)
    log.info(f"Amazon Relay cron — {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC")
    log.info(f"EMAIL set: {bool(os.getenv('AMAZON_RELAY_EMAIL'))}")
    log.info(f"DB set:    {bool(os.getenv('DATABASE_URL'))}")
    log.info("=" * 60)

    # ── 1. Fetch ──────────────────────────────────────────────────────────
    try:
        csv_path = asyncio.run(fetch_relay_csv())
        log.info(f"Fetch OK: {csv_path}")
    except RuntimeError as e:
        err = str(e)
        log.error(f"Fetch FAILED: {err}")
        is_captcha = any(w in err for w in ("CAPTCHA", "MFA", "challenge", "human"))
        if is_captcha:
            _notify(
                f"**CAPTCHA or MFA detected — manual re-auth required.**\n"
                f"```\n{err[:800]}\n```\n\n"
                f"Fix: run locally with headed browser to solve it:\n"
                f"```\nRELAY_HEADLESS=false python automation/amazon_relay/run_once.py\n```\n"
                f"The fresh session will be saved to the DB and nightly runs will resume.",
                is_error=True,
            )
        else:
            _notify(f"```\n{err[:1200]}\n```", is_error=True)
        return 1
    except Exception as e:
        log.error(f"Fetch FAILED (unexpected): {e}", exc_info=True)
        _notify(f"Unexpected error:\n```\n{str(e)[:1200]}\n```", is_error=True)
        return 1

    # ── 2. Ingest (CSV file + PostgreSQL) ─────────────────────────────────
    try:
        result = ingest_relay_csv(csv_path)
    except Exception as e:
        log.error(f"Ingest raised an exception: {e}", exc_info=True)
        _notify(f"Ingest exception:\n```\n{str(e)[:1200]}\n```", is_error=True)
        return 1

    if not result.success:
        log.error(f"Ingest FAILED: {result.error}")
        _notify(f"Ingest failed:\n```\n{result.error[:1200]}\n```", is_error=True)
        return 1

    log.info(str(result))

    # ── 3. Success notification ───────────────────────────────────────────
    _notify(
        f"Date: {datetime.utcnow():%Y-%m-%d}\n"
        f"New rows:  **{result.rows_new}**\n"
        f"Preserved: **{result.rows_kept}**\n"
        f"Total:     **{result.rows_total}**\n"
        + (f"DB rows:   **{result.db_count}**\n" if result.db_count else "")
    )

    log.info("=" * 60)
    log.info("Cron job complete — exiting 0.")
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
