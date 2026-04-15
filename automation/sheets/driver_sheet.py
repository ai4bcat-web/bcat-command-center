"""
automation/sheets/driver_sheet.py

Per-driver Google Spreadsheet writer.

Each driver gets one spreadsheet named "BCAT [Driver Name] Trips".
Within each spreadsheet, weekly tabs are created following the
Sunday–Friday Amazon week structure used in BCAT Command Center.

Tab naming:  "Apr 5 – Apr 10"  (Sunday open, Friday close of that week)

Column layout (see DRIVER_HEADERS below):
  A  Trip ID
  B  Trip Date
  C  Week
  D  Status
  E  Origin
  F  Destination
  G  Route / Lane
  H  Miles
  I  Equipment
  J  Revenue (Amazon Relay — "trip_revenue")
  K  Estimated Payout (from Master Sheet lookup)
  L  Load ID
  M  Notes

Configuration (env vars):
  DRIVER_SHEET_PREFIX   — spreadsheet title prefix (default: "BCAT")
  SHEETS_SHARE_EMAIL    — share all created sheets with this email
  SHEETS_FOLDER_ID      — Drive folder to place driver sheets in

Public API:
  DriverSheetWriter
    .ensure_spreadsheet(driver_name)                       -> str (spreadsheet_id)
    .write_driver_week(driver_name, week_start, trips, payout_map) -> dict
"""

import logging
import os
from datetime import date, timedelta

log = logging.getLogger("sheets.driver_sheet")

DRIVER_HEADERS = [
    "Trip ID",
    "Trip Date",
    "Week",
    "Status",
    "Origin",
    "Destination",
    "Route / Lane",
    "Miles",
    "Equipment",
    "Revenue",
    "Estimated Payout",
    "Load ID",
    "Notes",
]

# Track spreadsheet_id per driver so we don't re-open on every write
_SHEET_CACHE: dict[str, str] = {}


def week_tab_title(week_start: str) -> str:
    """
    Return the tab title for a given week start date (YYYY-MM-DD Sunday).

    Format: "Apr 5 – Apr 10"
    The week runs Sunday → Friday (Amazon DSP week convention).
    """
    try:
        start = date.fromisoformat(week_start)
        end   = start + timedelta(days=5)   # Sunday + 5 = Friday
        if start.year == end.year:
            if start.month == end.month:
                return f"{start.strftime('%b %-d')} – {end.strftime('%-d')}"
            return f"{start.strftime('%b %-d')} – {end.strftime('%b %-d')}"
        return f"{start.strftime('%b %-d, %Y')} – {end.strftime('%b %-d, %Y')}"
    except ValueError:
        return week_start


class DriverSheetWriter:
    """Creates and maintains per-driver Google Spreadsheets with weekly tabs."""

    def __init__(self):
        from automation.sheets.client import get_or_create_spreadsheet, ensure_worksheet
        self._get_or_create = get_or_create_spreadsheet
        self._ensure_ws     = ensure_worksheet
        self._prefix        = os.getenv("DRIVER_SHEET_PREFIX", "BCAT")

    # ── Spreadsheet bootstrap ─────────────────────────────────────────────────

    def ensure_spreadsheet(self, driver_name: str) -> str:
        """Open or create a driver spreadsheet. Returns spreadsheet ID."""
        norm = _normalize_driver(driver_name)
        if norm in _SHEET_CACHE:
            return _SHEET_CACHE[norm]

        title = f"{self._prefix} {driver_name} Trips"
        ss    = self._get_or_create(title)
        _SHEET_CACHE[norm] = ss.id
        log.info("Driver sheet for %r: id=%s", driver_name, ss.id)
        return ss.id

    # ── Weekly tab write ──────────────────────────────────────────────────────

    def write_driver_week(
        self,
        driver_name: str,
        week_start:  str,
        trips:       list[dict],
        payout_map:  dict[str, float],
    ) -> dict:
        """
        Write (or refresh) all trips for one driver/week into the appropriate tab.

        Args:
            driver_name: Display name of the driver.
            week_start:  YYYY-MM-DD (Sunday that starts the Amazon week).
            trips:       List of trip dicts from AmazonTrip.to_dict().
            payout_map:  {trip_id.upper(): estimated_payout} from master sheet.

        Returns dict with:
            tab_title, spreadsheet_id, rows_written, rows_updated,
            unmatched_trip_ids, matched_count
        """
        import gspread

        ss_id     = self.ensure_spreadsheet(driver_name)
        tab_title = week_tab_title(week_start)

        client = __import__("automation.sheets.client", fromlist=["get_client"]).get_client()
        ss     = client.open_by_key(ss_id)
        ws     = self._ensure_ws(ss, tab_title, DRIVER_HEADERS)

        # Load existing rows so we can dedup by trip_id
        existing = ws.get_all_values()
        existing_trip_ids: set[str] = set()
        if len(existing) > 1:
            for row in existing[1:]:
                if row and row[0]:
                    existing_trip_ids.add(row[0].strip().upper())

        rows_to_append  = []
        rows_updated    = 0
        unmatched       = []
        matched_count   = 0

        for trip in trips:
            trip_id  = (trip.get("trip_id") or "").strip()
            trip_id_upper = trip_id.upper()

            # Payout lookup
            payout = payout_map.get(trip_id_upper)
            if payout is not None:
                matched_count += 1
            else:
                unmatched.append(trip_id)

            row = _build_driver_row(trip, week_start, tab_title, payout)

            if trip_id_upper in existing_trip_ids:
                # Update existing row
                _update_row_by_trip_id(ws, trip_id_upper, row)
                rows_updated += 1
            else:
                rows_to_append.append(row)

        # Batch append new rows
        if rows_to_append:
            ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")

        rows_written = len(rows_to_append)

        # Log unmatched trip IDs
        if unmatched:
            log.warning(
                "Payout unmatched for driver=%r week=%s trip_ids=%s",
                driver_name, week_start, unmatched,
            )

        log.info(
            "Driver sheet updated | driver=%r week=%s tab=%r "
            "new=%d updated=%d matched=%d unmatched=%d",
            driver_name, week_start, tab_title,
            rows_written, rows_updated, matched_count, len(unmatched),
        )

        return {
            "tab_title":         tab_title,
            "spreadsheet_id":    ss_id,
            "rows_written":      rows_written,
            "rows_updated":      rows_updated,
            "unmatched_trip_ids": unmatched,
            "matched_count":     matched_count,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_driver_row(trip: dict, week_start: str, week_label: str, payout: float | None) -> list:
    """Convert a trip dict to a flat list matching DRIVER_HEADERS."""
    payout_str = f"${payout:.2f}" if payout is not None else ""
    rev = trip.get("trip_revenue") or trip.get("gross_load_revenue") or 0
    return [
        trip.get("trip_id")   or "",
        trip.get("trip_date") or "",
        week_label,
        trip.get("status")    or "",
        "",                          # Origin  — not in AmazonTrip model; reserved
        "",                          # Destination — reserved
        trip.get("route")     or "",
        "",                          # Miles — not in model; reserved
        "",                          # Equipment — reserved
        f"${float(rev):.2f}" if rev else "",
        payout_str,
        trip.get("load_id")   or "",
        "",                          # Notes
    ]


def _update_row_by_trip_id(ws, trip_id_upper: str, new_row: list) -> None:
    """Find the row with matching trip_id and update it in place."""
    all_rows = ws.get_all_values()
    for i, row in enumerate(all_rows[1:], start=2):
        if row and row[0].strip().upper() == trip_id_upper:
            ws.update(f"A{i}:M{i}", [new_row], value_input_option="USER_ENTERED")
            return


def _normalize_driver(name: str) -> str:
    """Normalize driver name for cache key (lowercase, strip)."""
    return name.strip().lower()
