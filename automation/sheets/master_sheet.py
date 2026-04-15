"""
automation/sheets/master_sheet.py

Writes Amazon Relay trip booking email data into the "BCAT Master Trip Payouts"
Google Spreadsheet.

This sheet is the source of truth for estimated payout by Trip ID.

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
    .ensure_sheet()                          -> str (spreadsheet_id)
    .find_row_by_message_id(message_id)      -> int | None
    .find_payout_by_trip_id(trip_id)         -> float | None
    .append_or_update(parsed_email)          -> int (1-based row number)
"""

import logging
import os
from datetime import datetime

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


class MasterSheetWriter:
    """Manages the BCAT Master Trip Payouts spreadsheet."""

    def __init__(self):
        from automation.sheets.client import get_or_create_spreadsheet, ensure_worksheet
        self._get_or_create = get_or_create_spreadsheet
        self._ensure_ws     = ensure_worksheet
        self._title         = os.getenv("MASTER_SHEET_TITLE", "BCAT Master Trip Payouts")
        self._sheet_id      = os.getenv("MASTER_SHEET_ID", "").strip() or None
        self._ss            = None    # cached gspread Spreadsheet
        self._ws            = None    # cached main worksheet

    # ── Sheet bootstrap ───────────────────────────────────────────────────────

    def ensure_sheet(self) -> str:
        """Open or create the master spreadsheet. Returns spreadsheet ID."""
        if self._ss is not None:
            return self._ss.id

        import gspread
        if self._sheet_id:
            client = __import__("automation.sheets.client", fromlist=["get_client"]).get_client()
            self._ss = client.open_by_key(self._sheet_id)
            log.info("Opened master sheet by ID: %s", self._sheet_id)
        else:
            self._ss = self._get_or_create(self._title)

        self._ws = self._ensure_ws(self._ss, "Trips", MASTER_HEADERS)
        return self._ss.id

    def _ws_data(self) -> list[list]:
        """Return all sheet values (cached lazily; caller should call ensure_sheet first)."""
        return self._ws.get_all_values()

    # ── Lookup helpers ────────────────────────────────────────────────────────

    def find_row_by_message_id(self, message_id: str) -> int | None:
        """
        Return 1-based row number for an already-imported Gmail message ID.
        Row 1 = header. Returns None if not found.
        """
        rows = self._ws_data()
        for i, row in enumerate(rows[1:], start=2):   # skip header
            if len(row) >= COL_MESSAGE_ID and row[COL_MESSAGE_ID - 1] == message_id:
                return i
        return None

    def find_payout_by_trip_id(self, trip_id: str) -> float | None:
        """
        Look up estimated payout for a Trip ID.
        Returns the float value if found, None otherwise.
        """
        if not trip_id:
            return None
        tid_norm = trip_id.strip().upper()
        rows = self._ws_data()
        for row in rows[1:]:
            if not row:
                continue
            row_trip = (row[0] if row else "").strip().upper()
            if row_trip == tid_norm:
                raw = row[COL_PAYOUT - 1] if len(row) >= COL_PAYOUT else ""
                raw = str(raw).replace("$", "").replace(",", "").strip()
                try:
                    return float(raw)
                except ValueError:
                    return None
        return None

    def get_all_payouts(self) -> dict[str, float]:
        """Return {trip_id: estimated_payout} for all rows with a valid payout."""
        result: dict[str, float] = {}
        rows = self._ws_data()
        for row in rows[1:]:
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

    def append_or_update(self, parsed) -> int:
        """
        Write or update a row for the given TripEmailData.

        If the Gmail message ID is already in the sheet, updates that row.
        Otherwise appends a new row at the bottom.

        Returns 1-based row number where the data was written.
        """
        row_data = self._build_row(parsed)

        existing_row = self.find_row_by_message_id(parsed.message_id)
        if existing_row:
            # Update existing row
            self._ws.update(
                f"A{existing_row}:{_col_letter(len(MASTER_HEADERS))}{existing_row}",
                [row_data],
                value_input_option="USER_ENTERED",
            )
            log.info("Updated master sheet row %d for trip %s", existing_row, parsed.trip_id)
            return existing_row
        else:
            # Append new row
            self._ws.append_row(row_data, value_input_option="USER_ENTERED")
            # Row number = current row count (after append)
            all_data = self._ws_data()
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
