"""
automation/trip_report/builder.py
──────────────────────────────────
TripReportBuilder

Transforms a flat list of raw trip records (from AmazonTrip ORM objects or
parsed CSV dicts) into per-driver DriverReport objects ready for PDF
generation and email delivery.

Driver grouping logic
─────────────────────
Trips are grouped by the driver name field (case-insensitive, whitespace
normalised).  If a DspDriver table record exists with a matching name, its
driver_type and other metadata are pulled in; otherwise the driver is treated
as a company driver.

The set of drivers to report on is determined as follows (in priority order):
  1. REPORT_DRIVER_NAMES env var — comma-separated explicit allow-list
  2. All active DspDriver records in the database
  3. All unique driver names appearing in the trip data for the window

If the allow-list / DB produce driver names that have NO trips for the window
those drivers are still included in the output with trip_count=0 and
total_revenue=0.0 so the operator can see the gap.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class TripRecord:
    trip_id:     str
    trip_date:   str   # YYYY-MM-DD
    driver:      str
    driver_type: str   # company | owner_op
    revenue:     float
    route:       str
    stops:       int
    status:      str


@dataclass
class DriverReport:
    driver_name:   str
    driver_type:   str   # company | owner_op
    trips:         list[TripRecord] = field(default_factory=list)
    trip_count:    int   = 0
    total_revenue: float = 0.0
    report_date:   str   = ''   # YYYY-MM-DD the job ran
    window_start:  str   = ''   # YYYY-MM-DD first day of window
    window_end:    str   = ''   # YYYY-MM-DD last day of window


# ── Builder ───────────────────────────────────────────────────────────────────

class TripReportBuilder:
    """Groups raw trip data into per-driver DriverReport objects."""

    def __init__(self, app=None):
        """
        Args:
            app: Flask app instance (optional).  When provided the builder
                 queries DspDriver from the database.  When None it falls back
                 to the REPORT_DRIVER_NAMES env var or the raw trip data alone.
        """
        self._app = app

    # ── Public API ────────────────────────────────────────────────────────────

    def build(
        self,
        raw_trips: list[Any],
        report_date: str,
        window_start: str,
        window_end: str,
    ) -> list[DriverReport]:
        """Return one DriverReport per relevant driver, sorted by name.

        Args:
            raw_trips:    List of AmazonTrip ORM objects *or* dicts with the
                          same field names (trip_id, trip_date, driver,
                          driver_type, trip_revenue / bcat_revenue, route,
                          stops, status).
            report_date:  The calendar date the job runs (YYYY-MM-DD).
            window_start: First day of the trip reporting window (YYYY-MM-DD).
            window_end:   Last  day of the trip reporting window (YYYY-MM-DD).
        """
        trips = [self._normalise(t) for t in raw_trips]

        # Build a lookup of all driver names that appear in the trip data
        trip_map: dict[str, list[TripRecord]] = {}
        for t in trips:
            key = t.driver.strip().lower()
            trip_map.setdefault(key, []).append(t)

        # Determine the canonical driver list
        driver_meta = self._resolve_driver_meta(list(trip_map.keys()))

        reports: list[DriverReport] = []
        for display_name, driver_type in driver_meta.items():
            key    = display_name.strip().lower()
            bucket = trip_map.get(key, [])
            bucket.sort(key=lambda r: r.trip_date)
            revenue = sum(r.revenue for r in bucket)

            reports.append(DriverReport(
                driver_name   = display_name,
                driver_type   = driver_type,
                trips         = bucket,
                trip_count    = len(bucket),
                total_revenue = round(revenue, 2),
                report_date   = report_date,
                window_start  = window_start,
                window_end    = window_end,
            ))

        reports.sort(key=lambda r: r.driver_name.lower())
        log.info(
            "Built %d driver reports (window %s – %s, %d total trips)",
            len(reports), window_start, window_end, len(trips),
        )
        return reports

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _normalise(self, raw: Any) -> TripRecord:
        """Convert an ORM object or dict into a TripRecord."""
        if hasattr(raw, '__dict__'):
            # SQLAlchemy ORM object
            return TripRecord(
                trip_id     = str(raw.trip_id    or ''),
                trip_date   = str(raw.trip_date  or ''),
                driver      = str(raw.driver     or '').strip(),
                driver_type = str(raw.driver_type or 'company'),
                revenue     = float(raw.trip_revenue or raw.bcat_revenue or 0.0),
                route       = str(raw.route  or ''),
                stops       = int(raw.stops  or 0),
                status      = str(raw.status or ''),
            )
        # Dict (from parse_amazon_relay_csv or mock data)
        return TripRecord(
            trip_id     = str(raw.get('trip_id', '')),
            trip_date   = str(raw.get('trip_date', '')),
            driver      = str(raw.get('driver', '')).strip(),
            driver_type = str(raw.get('driver_type', 'company')),
            revenue     = float(raw.get('trip_revenue') or raw.get('bcat_revenue') or 0.0),
            route       = str(raw.get('route', '')),
            stops       = int(raw.get('stops') or 0),
            status      = str(raw.get('status', '')),
        )

    def _resolve_driver_meta(self, trip_driver_keys: list[str]) -> dict[str, str]:
        """Return {display_name: driver_type} for all drivers to report on.

        Resolution order:
          1. REPORT_DRIVER_NAMES env var (comma-separated)
          2. Active DspDriver DB records
          3. All unique drivers from trip data
        """
        env_names = [
            n.strip() for n in os.getenv('REPORT_DRIVER_NAMES', '').split(',')
            if n.strip()
        ]

        if env_names:
            # Use explicit allow-list; type defaults to 'company' unless DB tells us otherwise
            db_meta = self._fetch_db_driver_meta()
            result: dict[str, str] = {}
            for name in env_names:
                lk = name.lower()
                result[name] = db_meta.get(lk, 'company')
            return result

        db_meta = self._fetch_db_driver_meta()
        if db_meta:
            # Merge: DB drivers take precedence; add any trip drivers not in DB
            result = {display: dtype for display, dtype in db_meta.items()}  # type: ignore[assignment]
            # db_meta keys are lowercased display names; values are driver_type
            # We need {display_name: driver_type} where keys are display names
            # Rebuild from DB with proper casing
            db_display = self._fetch_db_driver_display()
            result_display: dict[str, str] = {dn: db_meta[dn.lower()] for dn in db_display}
            # Add any trip driver not matched in DB
            existing_lc = {k.lower() for k in result_display}
            for key in trip_driver_keys:
                if key not in existing_lc and key:
                    # Reconstruct a display name by title-casing
                    display = key.title()
                    result_display[display] = 'company'
            return result_display

        # Fallback: use trip data only
        result_final: dict[str, str] = {}
        for key in trip_driver_keys:
            if key:
                result_final[key.title()] = 'company'
        return result_final

    def _fetch_db_driver_meta(self) -> dict[str, str]:
        """Return {lowercase_name: driver_type} from DspDriver table."""
        if not self._app:
            return {}
        try:
            from models import DspDriver
            with self._app.app_context():
                drivers = DspDriver.query.filter_by(active=True).all()
                return {d.name.strip().lower(): d.driver_type for d in drivers}
        except Exception as e:
            log.warning("Could not query DspDriver table: %s", e)
            return {}

    def _fetch_db_driver_display(self) -> list[str]:
        """Return list of display names (original casing) from DspDriver table."""
        if not self._app:
            return []
        try:
            from models import DspDriver
            with self._app.app_context():
                return [d.name.strip() for d in DspDriver.query.filter_by(active=True).all()]
        except Exception as e:
            log.warning("Could not query DspDriver display names: %s", e)
            return []
