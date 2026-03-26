"""
automation/amazon_relay/run_once.py

Manual test runner — fetches the CSV once and ingests it immediately.

Usage:
  source .venv/bin/activate
  python automation/amazon_relay/run_once.py

  # Watch the browser (useful for debugging login / MFA):
  RELAY_HEADLESS=false python automation/amazon_relay/run_once.py

  # Dry-run validation only (skip fetch, validate an existing file):
  python automation/amazon_relay/run_once.py --validate /path/to/file.csv
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

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
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("amazon_relay.run_once")


# ── entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Amazon Relay one-shot fetch + ingest")
    parser.add_argument(
        "--validate", metavar="CSV_PATH",
        help="Skip fetch; validate and ingest an existing CSV file.",
    )
    parser.add_argument(
        "--fetch-only", action="store_true",
        help="Download the CSV but do not ingest into the dashboard.",
    )
    args = parser.parse_args()

    # ── mode: validate existing file ──────────────────────────────────────
    if args.validate:
        csv_path = Path(args.validate)
        log.info(f"Validate-only mode: {csv_path}")
        result = ingest_relay_csv(csv_path)
        if result.success:
            log.info(f"Success: {result}")
        else:
            log.error(f"Failed: {result.error}")
            sys.exit(1)
        return

    # ── mode: full fetch (+ optional ingest) ──────────────────────────────
    log.info("Starting Amazon Relay fetch …")
    try:
        csv_path = asyncio.run(fetch_relay_csv())
    except Exception as e:
        log.error(f"Fetch failed: {e}")
        log.error(
            "Tip: run with RELAY_HEADLESS=false to see the browser and diagnose the issue.\n"
            "     Check screenshots saved in automation/amazon_relay/downloads/"
        )
        sys.exit(1)

    log.info(f"Downloaded: {csv_path}")

    if args.fetch_only:
        log.info("--fetch-only: skipping ingestion.")
        return

    log.info("Ingesting into dashboard pipeline …")
    result = ingest_relay_csv(csv_path)
    if result.success:
        log.info(str(result))
        log.info("Reload the dashboard to see updated Amazon DSP data.")
    else:
        log.error(f"Ingestion failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
