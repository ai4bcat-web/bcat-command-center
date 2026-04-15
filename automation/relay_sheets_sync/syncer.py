"""
automation/relay_sheets_sync/syncer.py

Reads Amazon Relay trips from the database (AmazonTrip table), groups them
by driver and week, and writes each group to the appropriate driver Google Sheet.

Also fetches the Master Sheet payout lookup so each driver row shows the
estimated payout from the original booking email.

Scheduling: runs 3× per day (configurable via RELAY_SHEETS_SCHEDULE env var).
Default Railway cron: 0 14,19,1 * * *  (8 AM / 1 PM / 7 PM CST)

Public API:
  RelaySheetsSyncer
    .run(window_start, window_end, dry_run) -> SyncRunResult
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

log = logging.getLogger("relay_sheets_sync.syncer")


@dataclass
class SyncRunResult:
    started_at:      datetime = field(default_factory=datetime.utcnow)
    completed_at:    datetime | None = None
    status:          str = "running"      # running | completed | failed
    window_start:    str = ""
    window_end:      str = ""
    trips_found:     int = 0
    rows_written:    int = 0
    rows_updated:    int = 0
    unmatched_count: int = 0
    drivers_synced:  int = 0
    errors:          list[str] = field(default_factory=list)
    driver_results:  list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"window={self.window_start}–{self.window_end} "
            f"trips={self.trips_found} drivers={self.drivers_synced} "
            f"written={self.rows_written} updated={self.rows_updated} "
            f"unmatched={self.unmatched_count}"
        )


class RelaySheetsSyncer:
    """
    Syncs Amazon Relay trip history from the DB into per-driver Google Sheets.
    """

    def __init__(self, app=None):
        self._app = app

    def run(
        self,
        window_start: str | None = None,
        window_end:   str | None = None,
        dry_run:      bool       = False,
    ) -> SyncRunResult:
        """
        Run the sync for the given date window.

        Args:
            window_start: YYYY-MM-DD (Sunday). Defaults to current-week Sunday.
            window_end:   YYYY-MM-DD. Defaults to today.
            dry_run:      Log what would be written, skip actual sheet writes.
        """
        ws, we = _resolve_window(window_start, window_end)
        result = SyncRunResult(window_start=ws, window_end=we)

        log.info("=" * 60)
        log.info("Relay sheets sync START | window=%s–%s dry_run=%s", ws, we, dry_run)
        log.info("=" * 60)

        # ── 1. Create DB audit record ──────────────────────────────────────────
        sync_run_id = self._create_sync_run(ws, we)

        # ── 2. Load trips from DB ──────────────────────────────────────────────
        try:
            trips = self._load_trips(ws, we)
            result.trips_found = len(trips)
            log.info("Loaded %d trips from DB.", len(trips))
        except Exception as e:
            err = f"DB load failed: {e}"
            log.error(err, exc_info=True)
            result.errors.append(err)
            result.status = "failed"
            self._finalize_sync_run(sync_run_id, result)
            return result

        if not trips:
            log.warning("No trips found for window %s–%s.", ws, we)
            result.status = "completed"
            result.completed_at = datetime.utcnow()
            self._finalize_sync_run(sync_run_id, result)
            return result

        # ── 3. Load payout map from Master Sheet ───────────────────────────────
        payout_map: dict[str, float] = {}
        sheets_enabled = bool(os.getenv("SHEETS_SERVICE_ACCOUNT_JSON", "").strip())
        if sheets_enabled:
            try:
                from automation.sheets.master_sheet import MasterSheetWriter
                mw = MasterSheetWriter()
                mw.ensure_sheet()
                payout_map = mw.get_all_payouts()
                log.info("Loaded %d payout entries from Master Sheet.", len(payout_map))
            except Exception as e:
                log.warning("Master sheet payout load failed — payouts will be blank: %s", e)
                result.errors.append(f"Payout load: {e}")
        else:
            log.info("SHEETS_SERVICE_ACCOUNT_JSON not set — payout lookup skipped.")

        # ── 4. Group trips by driver and week ──────────────────────────────────
        driver_weeks = _group_by_driver_week(trips)
        log.info("Grouped into %d driver-week combinations.", len(driver_weeks))

        # ── 5. Sync each driver/week ───────────────────────────────────────────
        if not sheets_enabled:
            log.warning("Google Sheets not configured — skipping sheet writes.")
            result.status = "completed"
            result.completed_at = datetime.utcnow()
            self._finalize_sync_run(sync_run_id, result)
            return result

        from automation.sheets.driver_sheet import DriverSheetWriter
        writer = DriverSheetWriter()

        for (driver, week_start), week_trips in driver_weeks.items():
            log.info("Syncing driver=%r week=%s trips=%d", driver, week_start, len(week_trips))

            if dry_run:
                unmatched = [
                    t.get("trip_id", "") for t in week_trips
                    if (t.get("trip_id") or "").upper() not in payout_map
                ]
                log.info("[DRY RUN] Would write %d rows | unmatched=%s", len(week_trips), unmatched)
                result.rows_written += len(week_trips)
                result.unmatched_count += len(unmatched)
                result.drivers_synced += 1
                continue

            try:
                drv_result = writer.write_driver_week(
                    driver_name = driver,
                    week_start  = week_start,
                    trips       = week_trips,
                    payout_map  = payout_map,
                )
                result.rows_written    += drv_result["rows_written"]
                result.rows_updated    += drv_result["rows_updated"]
                result.unmatched_count += len(drv_result["unmatched_trip_ids"])
                result.drivers_synced  += 1

                drv_summary = {
                    "driver":            driver,
                    "week_tab":          drv_result["tab_title"],
                    "spreadsheet_id":    drv_result["spreadsheet_id"],
                    "rows_written":      drv_result["rows_written"],
                    "rows_updated":      drv_result["rows_updated"],
                    "unmatched_trip_ids": drv_result["unmatched_trip_ids"],
                    "matched_count":     drv_result["matched_count"],
                }
                result.driver_results.append(drv_summary)
                self._save_driver_result(sync_run_id, drv_summary)

            except Exception as e:
                err = f"Sync failed for driver={driver} week={week_start}: {e}"
                log.error(err, exc_info=True)
                result.errors.append(err)

        result.status       = "completed" if not result.errors else "completed_with_errors"
        result.completed_at = datetime.utcnow()
        self._finalize_sync_run(sync_run_id, result)

        # ── 6. Reconciliation log ──────────────────────────────────────────────
        log.info("=" * 60)
        log.info("RECONCILIATION SUMMARY")
        log.info("  Window        : %s – %s", ws, we)
        log.info("  Trips found   : %d", result.trips_found)
        log.info("  Drivers synced: %d", result.drivers_synced)
        log.info("  Rows written  : %d", result.rows_written)
        log.info("  Rows updated  : %d", result.rows_updated)
        log.info("  Payout matched: %d", result.trips_found - result.unmatched_count)
        log.info("  Unmatched IDs : %d", result.unmatched_count)
        if result.errors:
            for err in result.errors:
                log.warning("  ERROR: %s", err)
        log.info("=" * 60)

        return result

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _load_trips(self, window_start: str, window_end: str) -> list[dict]:
        """Load AmazonTrip rows for the given date window from the DB."""
        if not self._app:
            # Fallback: parse from CSV
            return self._load_from_csv(window_start, window_end)

        try:
            from models import AmazonTrip, RelayCurrentWeek
            with self._app.app_context():
                # Prefer relay_current_week (exact list from last fetch)
                current_ids = [r.load_id for r in RelayCurrentWeek.query.all()]
                if current_ids:
                    rows = AmazonTrip.query.filter(
                        AmazonTrip.load_id.in_(current_ids)
                    ).all()
                    # Date guard: strip prior-week bleed
                    rows = [r for r in rows if not r.trip_date or r.trip_date >= window_start]
                    log.info("Loaded %d trips from relay_current_week.", len(rows))
                else:
                    rows = (
                        AmazonTrip.query
                        .filter(AmazonTrip.trip_date >= window_start)
                        .filter(AmazonTrip.trip_date <= window_end)
                        .all()
                    )
                    log.info("Date-range fallback: %d trips.", len(rows))
                return [r.to_dict() for r in rows]
        except Exception as e:
            log.warning("DB load failed, falling back to CSV: %s", e)
            return self._load_from_csv(window_start, window_end)

    def _load_from_csv(self, window_start: str, window_end: str) -> list[dict]:
        from finance_agent import parse_amazon_relay_csv
        csv_path = PROJECT_ROOT / "amazon_relay.csv"
        if not csv_path.exists():
            return []
        all_trips = parse_amazon_relay_csv(str(csv_path))
        return [
            t for t in all_trips
            if window_start <= str(t.get("trip_date") or "") <= window_end
        ]

    def _create_sync_run(self, window_start: str, window_end: str) -> int | None:
        if not self._app:
            return None
        try:
            from models import RelaySheetSyncRun
            from extensions import db
            with self._app.app_context():
                run = RelaySheetSyncRun(
                    window_start = window_start,
                    window_end   = window_end,
                    status       = "running",
                )
                db.session.add(run)
                db.session.commit()
                return run.id
        except Exception as e:
            log.warning("Could not create RelaySheetSyncRun: %s", e)
            return None

    def _finalize_sync_run(self, run_id: int | None, result: SyncRunResult) -> None:
        if not self._app or run_id is None:
            return
        try:
            from models import RelaySheetSyncRun
            from extensions import db
            with self._app.app_context():
                run = RelaySheetSyncRun.query.get(run_id)
                if run:
                    run.status          = result.status
                    run.completed_at    = result.completed_at
                    run.rows_found      = result.trips_found
                    run.rows_written    = result.rows_written
                    run.rows_updated    = result.rows_updated
                    run.unmatched_count = result.unmatched_count
                    run.error           = "; ".join(result.errors)
                    db.session.commit()
        except Exception as e:
            log.warning("Could not finalize RelaySheetSyncRun: %s", e)

    def _save_driver_result(self, run_id: int | None, drv: dict) -> None:
        if not self._app or run_id is None:
            return
        try:
            import json
            from models import DriverSheetSyncResult
            from extensions import db
            with self._app.app_context():
                r = DriverSheetSyncResult(
                    sync_run_id        = run_id,
                    driver             = drv["driver"],
                    week_tab           = drv["week_tab"],
                    spreadsheet_id     = drv["spreadsheet_id"],
                    rows_written       = drv["rows_written"],
                    rows_updated       = drv["rows_updated"],
                    unmatched_trip_ids = json.dumps(drv["unmatched_trip_ids"]),
                )
                db.session.add(r)
                db.session.commit()
        except Exception as e:
            log.warning("Could not save DriverSheetSyncResult: %s", e)


# ── Window helpers ────────────────────────────────────────────────────────────

def _resolve_window(window_start: str | None, window_end: str | None) -> tuple[str, str]:
    """Return (window_start, window_end) defaulting to current Amazon week-to-date."""
    if window_start and window_end:
        return window_start, window_end

    today = date.today()
    dow   = today.isoweekday()          # Mon=1 … Sun=7
    days_since_sunday = dow % 7
    start = today - timedelta(days=days_since_sunday)
    return start.isoformat(), today.isoformat()


def _group_by_driver_week(trips: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """
    Group trips by (driver, week_start) where week_start is the
    most recent Sunday on or before the trip_date.

    Returns dict keyed by (driver_name, week_start_iso).
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for trip in trips:
        driver     = (trip.get("driver") or "UNKNOWN").strip()
        trip_date  = trip.get("trip_date") or ""
        week_start = _sunday_of(trip_date)
        key        = (driver, week_start)
        groups.setdefault(key, []).append(trip)
    return groups


def _sunday_of(date_str: str) -> str:
    """Return the YYYY-MM-DD of the Sunday that starts the week containing date_str."""
    if not date_str:
        return date.today().isoformat()
    try:
        d   = date.fromisoformat(date_str[:10])
        dow = d.isoweekday() % 7   # Sun=0, Mon=1 … Sat=6
        return (d - timedelta(days=dow)).isoformat()
    except ValueError:
        return date.today().isoformat()
