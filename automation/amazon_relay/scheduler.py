"""
automation/amazon_relay/scheduler.py

Runs the Amazon Relay fetch + ingest job every night at 10:00 PM local time.

Uses the `schedule` library (already a project dependency).

How to run:
  source .venv/bin/activate
  python automation/amazon_relay/scheduler.py

The process runs indefinitely; use a terminal multiplexer (screen/tmux) or a
LaunchAgent to keep it alive.  See setup instructions in automation/amazon_relay/README.md.

To change the run time, update SCHEDULE_TIME below.
"""

import asyncio
import json
import logging
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import schedule
import time

# ── path setup ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "automation" / "amazon_relay" / "scheduler.log"),
    ],
)
log = logging.getLogger("amazon_relay.scheduler")

# ── config ────────────────────────────────────────────────────────────────
SCHEDULE_TIME       = "22:00"   # 10:00 PM local time — change here to adjust
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()


# ── discord alert ─────────────────────────────────────────────────────────

def _notify_failure(error_msg: str) -> None:
    """
    Post a failure alert to Discord via webhook.

    Set DISCORD_WEBHOOK_URL in .env to enable.  If not set, this is a no-op.
    Create a webhook: Discord channel → Edit → Integrations → Webhooks → New Webhook.
    """
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        body = json.dumps({
            "content": (
                "⚠️ **Amazon Relay nightly fetch FAILED**\n"
                f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                f"```\n{error_msg[:1500]}\n```\n\n"
                "Run this to fix (solve CAPTCHA in the browser window that opens):\n"
                "```\nRELAY_HEADLESS=false python automation/amazon_relay/run_once.py\n```"
            )
        }).encode()
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        log.info("Discord failure alert sent.")
    except Exception as e:
        log.warning(f"Could not send Discord alert: {e}")


# ── job ───────────────────────────────────────────────────────────────────

def run_job() -> None:
    """Synchronous wrapper so schedule can call it."""
    log.info("=" * 60)
    log.info(f"Amazon Relay nightly fetch — started at {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info("=" * 60)

    # 1. Fetch
    try:
        csv_path = asyncio.run(fetch_relay_csv())
        log.info(f"Fetch OK: {csv_path}")
    except Exception as e:
        log.error(f"Fetch FAILED: {e}")
        log.error("Ingestion skipped.")
        _notify_failure(str(e))
        return

    # 2. Ingest
    try:
        result = ingest_relay_csv(csv_path)
        if result.success:
            log.info(str(result))
            log.info("Dashboard will reflect new data on the next page load.")
        else:
            log.error(f"Ingestion FAILED: {result.error}")
    except Exception as e:
        log.error(f"Ingestion raised an exception: {e}")

    log.info(f"Job finished at {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info("=" * 60)


# ── schedule + loop ───────────────────────────────────────────────────────

def main() -> None:
    log.info(f"Scheduler started — job runs daily at {SCHEDULE_TIME} local time.")
    log.info("Press Ctrl-C to stop.")

    schedule.every().day.at(SCHEDULE_TIME).do(run_job)

    # Show next run time
    next_run = schedule.next_run()
    log.info(f"Next run: {next_run:%Y-%m-%d %H:%M:%S}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)   # check every 30 seconds
    except KeyboardInterrupt:
        log.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
