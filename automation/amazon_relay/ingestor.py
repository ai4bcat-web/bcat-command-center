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

def _audit_csv(csv_path: Path) -> None:
    """Log CSV headers, date range, drivers, revenue range, and sample rows."""
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            rows    = list(reader)

        log.info("── CSV audit: %s ──", csv_path.name)
        log.info("  Headers (%d): %s", len(headers), headers)
        log.info("  Total data rows: %d", len(rows))

        if not rows:
            log.warning("  CSV has no data rows.")
            return

        # Detect driver/date/revenue columns (case-insensitive)
        hdr_lc = {h.strip().lower(): h for h in headers}
        driver_col  = hdr_lc.get("driver name") or hdr_lc.get("driver")
        revenue_col = hdr_lc.get("estimated cost") or hdr_lc.get("trip_revenue")
        date_col    = next((hdr_lc[k] for k in [
            "stop 1 planned arrival date", "stop 1  actual arrival date",
            "stop 1 actual arrival date", "trip date", "execution date", "date",
        ] if k in hdr_lc), None)

        log.info("  Driver col  : %s", driver_col)
        log.info("  Date col    : %s", date_col)
        log.info("  Revenue col : %s", revenue_col)

        # Distinct drivers
        if driver_col:
            drivers = sorted({str(r.get(driver_col, '')).strip() for r in rows if r.get(driver_col, '').strip()})
            log.info("  Distinct drivers (%d): %s", len(drivers), drivers)
        else:
            log.warning("  No driver column found — trips will be skipped during parse.")

        # Date range
        if date_col:
            dates = sorted({str(r.get(date_col, '')).strip() for r in rows if r.get(date_col, '').strip()})
            log.info("  Date range: %s → %s  (%d distinct dates)", dates[0] if dates else 'none', dates[-1] if dates else 'none', len(dates))
        else:
            log.warning("  No date column found — trip_date will be empty for all rows.")

        # Revenue range
        if revenue_col:
            revenues = []
            for r in rows:
                raw = str(r.get(revenue_col, '') or '').replace('$', '').replace(',', '').strip()
                try:
                    revenues.append(float(raw))
                except ValueError:
                    pass
            if revenues:
                log.info("  Revenue range: $%.2f – $%.2f  (total $%.2f across %d rows)",
                         min(revenues), max(revenues), sum(revenues), len(revenues))
            else:
                log.warning("  Revenue col '%s' has no parseable values.", revenue_col)

        # Sample rows (first 3)
        log.info("  Sample rows (up to 3):")
        for i, r in enumerate(rows[:3]):
            log.info("    [%d] %s", i + 1, dict(r))

    except Exception as e:
        log.warning("CSV audit failed: %s", e)


def ingest_relay_csv(csv_path: Path) -> IngestResult:
    """
    Validate the CSV, merge with existing amazon_relay.csv (dedup by Trip ID),
    and atomically replace the destination file.

    This mirrors what bot/discord_bot.py does on a Discord upload, so the
    automated nightly fetch is functionally identical to a manual upload.
    """
    log.info("=" * 60)
    log.info("INGEST START: %s", csv_path)
    log.info("=" * 60)

    # ── validate ──────────────────────────────────────────────────────────
    error = _validate_csv(csv_path)
    if error:
        log.error("Validation failed: %s", error)
        return IngestResult(success=False, csv_path=csv_path, error=error)

    size = csv_path.stat().st_size
    log.info("File validated: %s  (%s bytes)", csv_path.name, f"{size:,}")

    # ── full CSV audit ────────────────────────────────────────────────────
    _audit_csv(csv_path)

    # ── count raw rows ────────────────────────────────────────────────────
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            raw_rows = sum(1 for _ in f) - 1
    except Exception:
        raw_rows = -1
    log.info("Raw data rows in downloaded file: %d", raw_rows)

    # ── merge into cumulative dataset ─────────────────────────────────────
    log.info("Merging into cumulative file: %s", AMAZON_RELAY_DEST)
    try:
        merged_path, preserved, new_count = merge_amazon_relay_csv(csv_path, AMAZON_RELAY_DEST)
    except Exception as e:
        log.error("Merge failed: %s", e)
        return IngestResult(success=False, csv_path=csv_path, error=f"Merge failed: {e}")

    log.info("Merge result — new rows: %d, preserved rows: %d, total: %d",
             new_count, preserved, new_count + preserved)

    # ── atomic replace ────────────────────────────────────────────────────
    try:
        replace_file_atomic(merged_path, AMAZON_RELAY_DEST)
        log.info("Cumulative file updated: %s", AMAZON_RELAY_DEST)
    except Exception as e:
        log.error("Atomic replace failed: %s", e)
        return IngestResult(success=False, csv_path=csv_path, error=f"Save failed: {e}")
    finally:
        if merged_path != csv_path and merged_path.exists():
            try:
                merged_path.unlink()
            except Exception:
                pass

    total = preserved + new_count

    # ── Write to database ─────────────────────────────────────────────────
    db_count = 0
    if os.getenv("DATABASE_URL", "").strip():
        log.info("Writing trips to database...")
        try:
            from finance_agent import parse_amazon_relay_csv, is_qualifying_trip
            from models import upsert_amazon_trips, set_current_week_trips
            from dashboard import app as _app

            # Read (trip_id, driver) pairs from the CURRENT DOWNLOAD (not cumulative).
            # These are exactly the trips Amazon exported for this week. Used by the
            # report job to filter without date arithmetic.
            with open(csv_path, newline="", encoding="utf-8-sig") as f:
                import csv as _csv
                reader = _csv.DictReader(f)
                current_week_pairs = []
                for row in reader:
                    tid    = (row.get('Trip ID') or row.get('trip_id') or '').strip()
                    driver = (row.get('Driver Name') or row.get('driver_name') or row.get('driver') or '').strip()
                    if tid:
                        current_week_pairs.append((tid, driver))
            log.info("Current week download contains %d (trip_id, driver) pairs.", len(current_week_pairs))

            all_trips = parse_amazon_relay_csv(str(AMAZON_RELAY_DEST))
            log.info("parse_amazon_relay_csv returned %d qualifying trips from cumulative file.", len(all_trips))

            # Per-driver breakdown
            by_driver: dict[str, list] = {}
            for t in all_trips:
                drv = t.get('driver') or 'UNKNOWN'
                by_driver.setdefault(drv, []).append(t)
            for drv, trips in sorted(by_driver.items()):
                dates = sorted({str(t.get('trip_date','')) for t in trips if t.get('trip_date')})
                rev   = sum(float(t.get('trip_revenue', 0) or 0) for t in trips)
                log.info("  Driver %-30s  trips=%d  date_range=%s–%s  revenue=$%.2f",
                         drv, len(trips),
                         dates[0] if dates else '?', dates[-1] if dates else '?',
                         rev)

            with _app.app_context():
                db_count = upsert_amazon_trips(all_trips)
                cw_count = set_current_week_trips(current_week_pairs)
            log.info("DB upsert complete: %d rows written, %d marked as current week.", db_count, cw_count)

        except Exception as e:
            log.error("DB write failed: %s", e, exc_info=True)
    else:
        log.info("DATABASE_URL not set — skipping DB write.")

    log.info("=" * 60)
    log.info("INGEST COMPLETE — new=%d preserved=%d total=%d db_written=%d",
             new_count, preserved, total, db_count)
    log.info("=" * 60)

    return IngestResult(
        success=True,
        csv_path=AMAZON_RELAY_DEST,
        rows_new=new_count,
        rows_kept=preserved,
        rows_total=total,
        db_count=db_count,
    )
