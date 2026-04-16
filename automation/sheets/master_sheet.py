"""
automation/sheets/master_sheet.py

Writes Amazon Relay trip booking email data into the "BCAT Master Trip Payouts"
Google Spreadsheet.

This sheet is the source of truth for estimated payout by Trip ID.

Structure:
  - One worksheet per calendar week, named identically to driver sheets: "Apr 5 – 10"
  - Legacy "Trips" tab preserved for backwards compatibility
  - Weeks start Sunday, end Friday (Amazon DSP convention)

Column layout (see MASTER_HEADERS below):
  A  Trip ID
  B  Estimated Payout
  C  Received At
  D  Subject
  E  Origin
  F  Destination
  G  Pickup Date/Time
  H  Dropoff Date/Time
  I  Driver (from email if available)
  J  Rate
  K  Miles
  L  Gmail Message ID     ← idempotency key
  M  Parse Confidence
  N  Import Status
  O  Notes / Raw Snippet

Configuration (env var):
  MASTER_SHEET_TITLE   — spreadsheet title (default: "BCAT Master Trip Payouts")
  MASTER_SHEET_ID      — if set, open by ID instead of title (skip create)

Public API:
  MasterSheetWriter
    .ensure_sheet()                                -> str (spreadsheet_id)
    .find_row_by_message_id(message_id)            -> (worksheet, int) | (None, None)
    .find_payout_by_trip_id(trip_id)               -> float | None
    .append_or_update(parsed_email)                -> int (1-based row number, legacy Trips tab)
    .append_or_update_to_week_tab(parsed_email)    -> int (1-based row number, weekly tab)
    .get_all_payouts()                             -> dict[str, float]
    .list_week_tabs()                              -> list[str]
"""

import logging
import os
from datetime import date, datetime, timedelta

log = logging.getLogger("sheets.master_sheet")

MASTER_HEADERS = [
    "Trip ID",
    "Estimated Payout",
    "Received At",
    "Subject",
    "Origin",
    "Destination",
    "Pickup Date/Time",
    "Dropoff Date/Time",
    "Driver",
    "Rate",
    "Miles",
    "Gmail Message ID",
    "Parse Confidence",
    "Import Status",
    "Notes / Raw Snippet",
]

# Column index (1-based) for key lookup columns
COL_TRIP_ID    = 1
COL_PAYOUT     = 2
COL_MESSAGE_ID = 12
COL_STATUS     = 14

LEGACY_TAB = "Trips"


# ── Week helpers (mirrors driver_sheet.py) ────────────────────────────────────

def week_tab_title(week_start: str) -> str:
    """
    Return tab title for a YYYY-MM-DD Sunday.

    Format: "Apr 5 – 10"  (same as driver sheets)
    Week runs Sunday → Friday (Amazon DSP convention).
    """
    try:
        start = date.fromisoformat(week_start)
        end   = start + timedelta(days=5)
        if start.year == end.year:
            if start.month == end.month:
                return f"{start.strftime('%b %-d')} – {end.strftime('%-d')}"
            return f"{start.strftime('%b %-d')} – {end.strftime('%b %-d')}"
        return f"{start.strftime('%b %-d, %Y')} – {end.strftime('%b %-d, %Y')}"
    except ValueError:
        return week_start


def sunday_of(dt: datetime | date | None) -> str:
    """Return YYYY-MM-DD of the Sunday starting the week that contains dt."""
    if dt is None:
        return date.today().isoformat()
    if isinstance(dt, datetime):
        dt = dt.date()
    dow = dt.isoweekday() % 7   # Sun=0, Mon=1 … Sat=6
    return (dt - timedelta(days=dow)).isoformat()


class MasterSheetWriter:
    """Manages the BCAT Master Trip Payouts spreadsheet."""

    def __init__(self):
        from automation.sheets.client import get_or_create_spreadsheet, ensure_worksheet
        self._get_or_create = get_or_create_spreadsheet
        self._ensure_ws     = ensure_worksheet
        self._title         = os.getenv("MASTER_SHEET_TITLE", "BCAT Master Trip Payouts")
        self._sheet_id      = os.getenv("MASTER_SHEET_ID", "").strip() or None
        self._ss            = None    # cached gspread Spreadsheet
        self._ws            = None    # cached legacy "Trips" worksheet

    # ── Sheet bootstrap ───────────────────────────────────────────────────────

    def ensure_sheet(self) -> str:
        """Open or create the master spreadsheet. Returns spreadsheet ID."""
        if self._ss is not None:
            return self._ss.id

        if self._sheet_id:
            client = __import__("automation.sheets.client", fromlist=["get_client"]).get_client()
            self._ss = client.open_by_key(self._sheet_id)
            log.info("Opened master sheet by ID: %s", self._sheet_id)
        else:
            self._ss = self._get_or_create(self._title)

        self._ws = self._ensure_ws(self._ss, LEGACY_TAB, MASTER_HEADERS)
        return self._ss.id

    def ensure_week_tab(self, week_start: str):
        """Open or create a weekly tab. Returns the gspread Worksheet."""
        if self._ss is None:
            self.ensure_sheet()
        title = week_tab_title(week_start)
        return self._ensure_ws(self._ss, title, MASTER_HEADERS)

    def list_week_tabs(self) -> list[str]:
        """Return titles of all weekly tabs (excludes legacy 'Trips' tab)."""
        if self._ss is None:
            self.ensure_sheet()
        return [ws.title for ws in self._ss.worksheets() if ws.title != LEGACY_TAB]

    def all_worksheets(self):
        """Yield all worksheets (including legacy tab)."""
        if self._ss is None:
            self.ensure_sheet()
        return self._ss.worksheets()

    # ── Lookup helpers ────────────────────────────────────────────────────────

    def find_row_by_message_id(self, message_id: str):
        """
        Search all tabs for an already-imported Gmail message ID.

        Returns (worksheet, 1-based row number) or (None, None) if not found.
        """
        if self._ss is None:
            self.ensure_sheet()
        for ws in self._ss.worksheets():
            rows = ws.get_all_values()
            for i, row in enumerate(rows[1:], start=2):
                if len(row) >= COL_MESSAGE_ID and row[COL_MESSAGE_ID - 1] == message_id:
                    return ws, i
        return None, None

    def find_payout_by_trip_id(self, trip_id: str) -> float | None:
        """Look up estimated payout for a Trip ID across all tabs."""
        if not trip_id:
            return None
        tid_norm = trip_id.strip().upper()
        if self._ss is None:
            self.ensure_sheet()
        for ws in self._ss.worksheets():
            for row in ws.get_all_values()[1:]:
                if not row:
                    continue
                if (row[0] if row else "").strip().upper() == tid_norm:
                    raw = row[COL_PAYOUT - 1] if len(row) >= COL_PAYOUT else ""
                    raw = str(raw).replace("$", "").replace(",", "").strip()
                    try:
                        return float(raw)
                    except ValueError:
                        return None
        return None

    def get_all_payouts(self) -> dict[str, float]:
        """Return {trip_id.upper(): estimated_payout} scanning all tabs."""
        result: dict[str, float] = {}
        if self._ss is None:
            self.ensure_sheet()
        for ws in self._ss.worksheets():
            for row in ws.get_all_values()[1:]:
                if not row:
                    continue
                trip_id = (row[0] if row else "").strip().upper()
                raw     = row[COL_PAYOUT - 1] if len(row) >= COL_PAYOUT else ""
                raw     = str(raw).replace("$", "").replace(",", "").strip()
                if trip_id:
                    try:
                        result[trip_id] = float(raw)
                    except ValueError:
                        pass
        return result

    # ── Write ─────────────────────────────────────────────────────────────────

    def append_or_update_to_week_tab(self, parsed) -> int:
        """
        Write or update a row in the weekly tab determined by parsed.received_at.

        Idempotent: if the Gmail message ID is already in any tab, updates that row.
        Otherwise appends to the correct weekly tab.

        Returns 1-based row number where the data was written.
        """
        row_data = self._build_row(parsed)

        existing_ws, existing_row = self.find_row_by_message_id(parsed.message_id)
        if existing_ws and existing_row:
            existing_ws.update(
                f"A{existing_row}:{_col_letter(len(MASTER_HEADERS))}{existing_row}",
                [row_data],
                value_input_option="USER_ENTERED",
            )
            log.debug("Updated master week tab row %d for trip %s", existing_row, parsed.trip_id)
            return existing_row

        # Route to correct weekly tab
        week_start = sunday_of(parsed.received_at)
        ws = self.ensure_week_tab(week_start)
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        all_data = ws.get_all_values()
        row_num  = len(all_data)
        log.debug("Appended master week tab row %d for trip %s payout=%s week=%s",
                  row_num, parsed.trip_id, parsed.estimated_payout, week_tab_title(week_start))
        return row_num

    def append_or_update(self, parsed) -> int:
        """
        Legacy single-tab write (to 'Trips' worksheet).
        Kept for backwards compatibility with existing ingestor.run() flow.
        """
        row_data = self._build_row(parsed)

        _, existing_row = self.find_row_by_message_id(parsed.message_id)
        if existing_row:
            self._ws.update(
                f"A{existing_row}:{_col_letter(len(MASTER_HEADERS))}{existing_row}",
                [row_data],
                value_input_option="USER_ENTERED",
            )
            log.info("Updated master sheet row %d for trip %s", existing_row, parsed.trip_id)
            return existing_row
        else:
            self._ws.append_row(row_data, value_input_option="USER_ENTERED")
            all_data = self._ws.get_all_values()
            row_num  = len(all_data)
            log.info("Appended master sheet row %d for trip %s payout=%s",
                     row_num, parsed.trip_id, parsed.estimated_payout)
            return row_num

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_row(self, parsed) -> list:
        """Convert TripEmailData to a flat list matching MASTER_HEADERS."""
        payout_str = f"${parsed.estimated_payout:.2f}" if parsed.estimated_payout is not None else ""
        received   = (
            parsed.received_at.strftime("%Y-%m-%d %H:%M UTC")
            if parsed.received_at else ""
        )
        return [
            parsed.trip_id,
            payout_str,
            received,
            parsed.subject,
            parsed.origin,
            parsed.destination,
            parsed.pickup_dt,
            parsed.dropoff_dt,
            parsed.driver,
            parsed.rate,
            parsed.miles,
            parsed.message_id,
            parsed.parse_confidence,
            "imported",
            parsed.raw_snippet[:200],
        ]


def _col_letter(n: int) -> str:
    """Convert 1-based column index to letter (1→A, 26→Z, 27→AA)."""
    result = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result
