"""
automation/backfill/relay_backfill.py

Historical Amazon Relay backfill into per-driver Google Spreadsheets.

Loads ALL AmazonTrip rows from the DB (not just relay_current_week),
groups them by (driver, week_start), and writes each group into the
correct weekly tab of the driver's spreadsheet.

Payout lookup: fetches {trip_id: payout} from Master Sheet and fills
the Estimated Payout column wherever a match is found.

Resumable: each processed (source='relay', week_start) per driver is
recorded in BackfillProgress. Re-running skips completed weeks unless
force=True.

Public API:
  RelayBackfill(app)
    .run(dry_run, force)                               -> RelayBackfillResult
    .run_driver(driver_name, dry_run, force)           -> dict
    .run_week(week_start, dry_run)                     -> dict
    .rerun_payout_match(week_start, driver_name)       -> dict
"""

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

log = logging.getLogger("backfill.relay")


@dataclass
class RelayBackfillResult:
    started_at:      datetime = field(default_factory=datetime.utcnow)
    completed_at:    datetime | None = None
    trips_found:     int = 0
    drivers:         list[str] = field(default_factory=list)
    weeks_processed: int = 0
    weeks_skipped:   int = 0
    rows_written:    int = 0
    rows_updated:    int = 0
    unmatched:       int = 0
    errors:          list[str] = field(default_factory=list)
    driver_summary:  list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"trips={self.trips_found} drivers={len(self.drivers)} "
            f"weeks={self.weeks_processed} written={self.rows_written} "
            f"updated={self.rows_updated} unmatched={self.unmatched}"
        )


class RelayBackfill:
    """
    Syncs all historical AmazonTrip rows into per-driver Google Spreadsheet weekly tabs.
    """

    def __init__(self, app=None):
        self._app = app

    def run(
        self,
        dry_run: bool = False,
        force:   bool = False,
    ) -> RelayBackfillResult:
        """
        Full historical Relay backfill across all drivers and all weeks.

        Args:
            dry_run: Log what would be written without making changes.
            force:   Reprocess weeks already marked completed.
        """
        result = RelayBackfillResult()
        log.info("=" * 60)
        log.info("Relay historical backfill START | dry_run=%s force=%s", dry_run, force)
        log.info("=" * 60)

        # ── 1. Load all trips from DB ──────────────────────────────────────
        try:
            trips = self._load_all_trips()
            result.trips_found = len(trips)
            log.info("Loaded %d total trips from DB.", len(trips))
        except Exception as e:
            err = f"DB load failed: {e}"
            log.error(err, exc_info=True)
            result.errors.append(err)
            result.completed_at = datetime.utcnow()
            return result

        if not trips:
            log.warning("No trips found in DB.")
            result.completed_at = datetime.utcnow()
            return result

        # ── 2. Load payout map from Master Sheet ───────────────────────────
        payout_map: dict[str, float] = {}
        try:
            from automation.sheets.master_sheet import MasterSheetWriter
            mw = MasterSheetWriter()
            mw.ensure_sheet()
            payout_map = mw.get_all_payouts()
            log.info("Loaded %d payout entries from Master Sheet.", len(payout_map))
        except Exception as e:
            log.warning("Master sheet payout load failed — payouts will be blank: %s", e)
            result.errors.append(f"Payout load: {e}")

        # ── 3. Group by driver and week ────────────────────────────────────
        driver_weeks: dict[tuple, list] = defaultdict(list)
        for trip in trips:
            driver     = (trip.get("driver") or "UNKNOWN").strip()
            trip_date  = trip.get("trip_date") or ""
            week_start = _sunday_of(trip_date)
            driver_weeks[(driver, week_start)].append(trip)

        result.drivers = sorted({k[0] for k in driver_weeks.keys()})
        log.info("Grouped into %d driver-week combinations across %d drivers.",
                 len(driver_weeks), len(result.drivers))

        # ── 4. Load completed weeks per driver ─────────────────────────────
        completed: set[tuple] = set() if force else self._load_completed_driver_weeks()

        if dry_run:
            for (driver, week_start), week_trips in sorted(driver_weeks.items()):
                key = (driver, week_start)
                if key in completed:
                    result.weeks_skipped += 1
                    continue
                unmatched = [
                    t.get("trip_id", "") for t in week_trips
                    if (t.get("trip_id") or "").upper() not in payout_map
                ]
                log.info("[DRY RUN] driver=%r week=%s trips=%d unmatched=%d",
                         driver, week_start, len(week_trips), len(unmatched))
                result.weeks_processed += 1
                result.rows_written    += len(week_trips)
                result.unmatched       += len(unmatched)
            result.completed_at = datetime.utcnow()
            log.info("Relay backfill DRY RUN done | %s", result.summary())
            return result

        # ── 5. Write driver sheets ─────────────────────────────────────────
        from automation.sheets.driver_sheet import DriverSheetWriter
        writer = DriverSheetWriter()

        for (driver, week_start), week_trips in sorted(driver_weeks.items()):
            key = (driver, week_start)
            if key in completed:
                result.weeks_skipped += 1
                log.debug("Skipping completed driver=%r week=%s", driver, week_start)
                continue

            log.info("Syncing driver=%r week=%s trips=%d", driver, week_start, len(week_trips))

            try:
                drv_result = writer.write_driver_week(
                    driver_name = driver,
                    week_start  = week_start,
                    trips       = week_trips,
                    payout_map  = payout_map,
                )
                result.weeks_processed += 1
                result.rows_written    += drv_result["rows_written"]
                result.rows_updated    += drv_result["rows_updated"]
                result.unmatched       += len(drv_result["unmatched_trip_ids"])

                result.driver_summary.append({
                    "driver":       driver,
                    "week_start":   week_start,
                    "tab":          drv_result["tab_title"],
                    "written":      drv_result["rows_written"],
                    "updated":      drv_result["rows_updated"],
                    "unmatched":    drv_result["unmatched_trip_ids"],
                    "matched":      drv_result["matched_count"],
                })

                self._record_progress(
                    source       = f"relay:{driver}",
                    week_start   = week_start,
                    status       = "completed",
                    rows_found   = len(week_trips),
                    rows_written = drv_result["rows_written"],
                    rows_skipped = drv_result["rows_updated"],
                    unmatched    = len(drv_result["unmatched_trip_ids"]),
                )

            except Exception as e:
                err = f"driver={driver} week={week_start}: {e}"
                log.error("Sync failed — %s", err, exc_info=True)
                result.errors.append(err)
                self._record_progress(
                    source=f"relay:{driver}", week_start=week_start,
                    status="failed", notes=str(e),
                )

        result.completed_at = datetime.utcnow()
        log.info("=" * 60)
        log.info("Relay backfill DONE | %s", result.summary())
        if result.errors:
            for err in result.errors:
                log.warning("  ERROR: %s", err)
        log.info("=" * 60)
        return result

    def run_driver(
        self,
        driver_name: str,
        dry_run: bool = False,
        force:   bool = False,
    ) -> dict:
        """Rebuild all weekly tabs for a single driver."""
        trips = self._load_all_trips(driver_filter=driver_name)
        if not trips:
            return {"driver": driver_name, "trips": 0, "message": "No trips found"}

        payout_map = self._load_payout_map()
        driver_weeks: dict[str, list] = defaultdict(list)
        for trip in trips:
            week_start = _sunday_of(trip.get("trip_date") or "")
            driver_weeks[week_start].append(trip)

        if dry_run:
            return {
                "driver": driver_name,
                "trips":  len(trips),
                "weeks":  sorted(driver_weeks.keys()),
                "dry_run": True,
            }

        completed = set() if force else self._load_completed_driver_weeks(driver_name)
        from automation.sheets.driver_sheet import DriverSheetWriter
        writer = DriverSheetWriter()

        results = []
        for week_start in sorted(driver_weeks.keys()):
            if (driver_name, week_start) in completed and not force:
                results.append({"week": week_start, "skipped": True})
                continue
            week_trips = driver_weeks[week_start]
            try:
                r = writer.write_driver_week(
                    driver_name=driver_name, week_start=week_start,
                    trips=week_trips, payout_map=payout_map,
                )
                results.append({"week": week_start, "written": r["rows_written"],
                                 "updated": r["rows_updated"], "tab": r["tab_title"]})
                self._record_progress(
                    source=f"relay:{driver_name}", week_start=week_start,
                    status="completed", rows_found=len(week_trips),
                    rows_written=r["rows_written"], rows_skipped=r["rows_updated"],
                    unmatched=len(r["unmatched_trip_ids"]),
                )
            except Exception as e:
                results.append({"week": week_start, "error": str(e)})

        return {"driver": driver_name, "trips": len(trips), "weeks": results}

    def run_week(self, week_start: str, dry_run: bool = False) -> dict:
        """Backfill all drivers for a single specific week."""
        trips = self._load_trips_for_week(week_start)
        payout_map = self._load_payout_map()

        driver_weeks: dict[str, list] = defaultdict(list)
        for trip in trips:
            driver = (trip.get("driver") or "UNKNOWN").strip()
            driver_weeks[driver].append(trip)

        if dry_run:
            return {"week_start": week_start, "trips": len(trips),
                    "drivers": list(driver_weeks.keys()), "dry_run": True}

        from automation.sheets.driver_sheet import DriverSheetWriter
        writer  = DriverSheetWriter()
        results = []
        for driver, week_trips in driver_weeks.items():
            try:
                r = writer.write_driver_week(
                    driver_name=driver, week_start=week_start,
                    trips=week_trips, payout_map=payout_map,
                )
                results.append({"driver": driver, "written": r["rows_written"],
                                 "updated": r["rows_updated"]})
            except Exception as e:
                results.append({"driver": driver, "error": str(e)})

        return {"week_start": week_start, "trips": len(trips), "drivers": results}

    def rerun_payout_match(
        self,
        week_start:  str | None = None,
        driver_name: str | None = None,
    ) -> dict:
        """
        Re-fetch payout map from Master Sheet and update all matching driver sheet rows.

        Args:
            week_start:  Limit to a specific week (YYYY-MM-DD). None = all weeks.
            driver_name: Limit to a specific driver. None = all drivers.
        """
        payout_map = self._load_payout_map()
        if not payout_map:
            return {"error": "No payouts found in Master Sheet"}

        trips = self._load_all_trips(driver_filter=driver_name)
        if week_start:
            ws_date = datetime.strptime(week_start, "%Y-%m-%d").date()
            we_date = ws_date + timedelta(days=6)
            trips = [
                t for t in trips
                if t.get("trip_date") and ws_date.isoformat() <= t["trip_date"] <= we_date.isoformat()
            ]

        driver_weeks: dict[tuple, list] = defaultdict(list)
        for trip in trips:
            driver = (trip.get("driver") or "UNKNOWN").strip()
            ws     = _sunday_of(trip.get("trip_date") or "")
            driver_weeks[(driver, ws)].append(trip)

        from automation.sheets.driver_sheet import DriverSheetWriter
        writer = DriverSheetWriter()
        total_updated = 0
        results = []

        for (driver, ws), week_trips in sorted(driver_weeks.items()):
            try:
                r = writer.write_driver_week(
                    driver_name=driver, week_start=ws,
                    trips=week_trips, payout_map=payout_map,
                )
                total_updated += r["rows_updated"] + r["rows_written"]
                results.append({"driver": driver, "week": ws,
                                 "written": r["rows_written"], "updated": r["rows_updated"],
                                 "matched": r["matched_count"]})
            except Exception as e:
                results.append({"driver": driver, "week": ws, "error": str(e)})

        return {
            "payout_entries": len(payout_map),
            "trips_processed": len(trips),
            "rows_touched": total_updated,
            "results": results,
        }

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _load_all_trips(self, driver_filter: str | None = None) -> list[dict]:
        if not self._app:
            return []
        try:
            from models import AmazonTrip
            with self._app.app_context():
                q = AmazonTrip.query
                if driver_filter:
                    q = q.filter(AmazonTrip.driver == driver_filter)
                rows = q.order_by(AmazonTrip.trip_date).all()
                return [r.to_dict() for r in rows]
        except Exception as e:
            log.error("DB load failed: %s", e)
            return []

    def _load_trips_for_week(self, week_start: str) -> list[dict]:
        try:
            ws_date = datetime.strptime(week_start, "%Y-%m-%d").date()
            we_date = ws_date + timedelta(days=6)
        except ValueError:
            return []
        if not self._app:
            return []
        try:
            from models import AmazonTrip
            with self._app.app_context():
                rows = (
                    AmazonTrip.query
                    .filter(AmazonTrip.trip_date >= ws_date.isoformat())
                    .filter(AmazonTrip.trip_date <= we_date.isoformat())
                    .all()
                )
                return [r.to_dict() for r in rows]
        except Exception as e:
            log.error("DB load for week %s failed: %s", week_start, e)
            return []

    def _load_payout_map(self) -> dict[str, float]:
        try:
            from automation.sheets.master_sheet import MasterSheetWriter
            mw = MasterSheetWriter()
            mw.ensure_sheet()
            return mw.get_all_payouts()
        except Exception as e:
            log.warning("Could not load payout map: %s", e)
            return {}

    def _load_completed_driver_weeks(self, driver_name: str | None = None) -> set[tuple]:
        if not self._app:
            return set()
        try:
            from models import BackfillProgress
            with self._app.app_context():
                q = BackfillProgress.query.filter(
                    BackfillProgress.source.like("relay:%"),
                    BackfillProgress.status == "completed",
                )
                rows = q.all()
                result = set()
                for r in rows:
                    drv = r.source[len("relay:"):]
                    if driver_name is None or drv == driver_name:
                        result.add((drv, r.week_start))
                return result
        except Exception as e:
            log.warning("Could not load completed driver weeks: %s", e)
            return set()

    def _record_progress(self, source, week_start, status, **kwargs):
        if not self._app:
            return
        try:
            from models import BackfillProgress
            from extensions import db
            with self._app.app_context():
                existing = BackfillProgress.query.filter_by(
                    source=source, week_start=week_start
                ).first()
                if existing:
                    existing.status       = status
                    existing.rows_found   = kwargs.get("rows_found", existing.rows_found)
                    existing.rows_written = kwargs.get("rows_written", existing.rows_written)
                    existing.rows_skipped = kwargs.get("rows_skipped", existing.rows_skipped)
                    existing.unmatched    = kwargs.get("unmatched", existing.unmatched)
                    existing.notes        = kwargs.get("notes", existing.notes or "")
                    existing.processed_at = datetime.utcnow()
                else:
                    db.session.add(BackfillProgress(
                        source       = source,
                        week_start   = week_start,
                        status       = status,
                        rows_found   = kwargs.get("rows_found", 0),
                        rows_written = kwargs.get("rows_written", 0),
                        rows_skipped = kwargs.get("rows_skipped", 0),
                        unmatched    = kwargs.get("unmatched", 0),
                        notes        = kwargs.get("notes", ""),
                    ))
                db.session.commit()
        except Exception as e:
            log.warning("Could not record backfill progress: %s", e)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sunday_of(date_str: str) -> str:
    """Return YYYY-MM-DD of the Sunday starting the week that contains date_str."""
    if not date_str:
        return date.today().isoformat()
    try:
        d   = date.fromisoformat(date_str[:10])
        dow = d.isoweekday() % 7   # Sun=0, Mon=1 … Sat=6
        return (d - timedelta(days=dow)).isoformat()
    except ValueError:
        return date.today().isoformat()
