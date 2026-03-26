"""
automation/amazon_relay/ingestor.py

Validates a downloaded Amazon Relay CSV and merges it into the dashboard pipeline.

Uses the exact same merge + atomic-replace logic as bot/discord_bot.py so the
automated fetch is byte-for-byte equivalent to a manual Discord upload.

Public API:
  ingest_relay_csv(csv_path: Path) -> IngestResult
"""

import csv
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── path setup ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Re-use the exact functions from the existing Discord bot pipeline
from bot.discord_bot import merge_amazon_relay_csv, replace_file_atomic

log = logging.getLogger("amazon_relay.ingestor")

# Expected header columns (lowercase, stripped) — must be present for the file to be valid
REQUIRED_HEADERS = {"driver name", "trip id", "estimated cost", "load execution status"}

AMAZON_RELAY_DEST = PROJECT_ROOT / "amazon_relay.csv"


# ── result type ───────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    success:    bool
    csv_path:   Path
    rows_new:   int = 0
    rows_kept:  int = 0
    rows_total: int = 0
    db_count:   int = 0
    error:      str = ""

    @property
    def rows_skipped(self) -> int:
        return self.rows_new + self.rows_kept  # alias kept for logging

    def __str__(self) -> str:
        if not self.success:
            return f"IngestResult(FAILED): {self.error}"
        db_str = f", db={self.db_count}" if self.db_count else ""
        return (
            f"IngestResult(OK): "
            f"new={self.rows_new}, kept={self.rows_kept}, total={self.rows_total}{db_str}"
        )


# ── validation ────────────────────────────────────────────────────────────

def _validate_csv(path: Path) -> str | None:
    """
    Returns None if the file is valid, or an error string if not.
    Checks: exists, non-empty, parseable, contains required headers.
    """
    if not path.exists():
        return f"File does not exist: {path}"

    size = path.stat().st_size
    if size == 0:
        return f"File is empty: {path}"

    if size < 100:
        return f"File is suspiciously small ({size} bytes) — likely not a real export."

    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
    except Exception as e:
        return f"Could not parse CSV: {e}"

    if not headers:
        return "CSV has no header row."

    normalized = {h.strip().lower() for h in headers}
    missing = REQUIRED_HEADERS - normalized
    if missing:
        return (
            f"CSV is missing required columns: {missing}. "
            f"Got: {list(normalized)[:10]}"
        )

    return None  # valid


# ── ingestion ─────────────────────────────────────────────────────────────

def ingest_relay_csv(csv_path: Path) -> IngestResult:
    """
    Validate the CSV, merge with existing amazon_relay.csv (dedup by Trip ID),
    and atomically replace the destination file.

    This mirrors what bot/discord_bot.py does on a Discord upload, so the
    automated nightly fetch is functionally identical to a manual upload.
    """
    log.info(f"Ingesting: {csv_path}")

    # ── validate ──────────────────────────────────────────────────────────
    error = _validate_csv(csv_path)
    if error:
        log.error(f"Validation failed: {error}")
        return IngestResult(success=False, csv_path=csv_path, error=error)

    size = csv_path.stat().st_size
    log.info(f"File validated: {csv_path.name}  ({size:,} bytes)")

    # ── count raw rows for logging ────────────────────────────────────────
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            raw_rows = sum(1 for _ in f) - 1  # subtract header
    except Exception:
        raw_rows = -1

    log.info(f"Raw rows in new file: {raw_rows}")

    # ── merge into cumulative dataset ─────────────────────────────────────
    try:
        merged_path, preserved, new_count = merge_amazon_relay_csv(csv_path, AMAZON_RELAY_DEST)
    except Exception as e:
        log.error(f"Merge failed: {e}")
        return IngestResult(success=False, csv_path=csv_path, error=f"Merge failed: {e}")

    # ── atomic replace ────────────────────────────────────────────────────
    try:
        replace_file_atomic(merged_path, AMAZON_RELAY_DEST)
    except Exception as e:
        log.error(f"Atomic replace failed: {e}")
        return IngestResult(success=False, csv_path=csv_path, error=f"Save failed: {e}")
    finally:
        # Clean up the temp merge file
        if merged_path != csv_path and merged_path.exists():
            try:
                merged_path.unlink()
            except Exception:
                pass

    total = preserved + new_count
    log.info(
        f"Ingestion complete — "
        f"new: {new_count}, preserved from prior weeks: {preserved}, total on file: {total}"
    )

    # ── Also write to database so Railway dashboard reads persistent data ──
    db_count = 0
    if os.getenv("DATABASE_URL", "").strip():
        try:
            from finance_agent import parse_amazon_relay_csv
            from models import upsert_amazon_trips
            from dashboard import app as _app
            trips = parse_amazon_relay_csv(str(AMAZON_RELAY_DEST))
            with _app.app_context():
                db_count = upsert_amazon_trips(trips)
            log.info(f"Saved {db_count} trips to database.")
        except Exception as e:
            log.warning(f"DB save skipped: {e}")

    return IngestResult(
        success=True,
        csv_path=AMAZON_RELAY_DEST,
        rows_new=new_count,
        rows_kept=preserved,
        rows_total=total,
        db_count=db_count,
    )
