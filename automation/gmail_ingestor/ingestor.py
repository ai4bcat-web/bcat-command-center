"""
automation/gmail_ingestor/ingestor.py

Orchestrates the Gmail trip booking email ingestion pipeline:

  1. Authenticate with Gmail (readonly scope)
  2. Search inbox for trip booking emails (last N days)
  3. Skip messages already imported (dedup by Gmail message ID)
  4. Parse each email body for trip data
  5. Persist parsed result to GmailTripEmail DB table
  6. Write each new row to the Master Sheet

Public API:
  GmailTripEmailIngestor
    .run(lookback_days, dry_run) -> IngestRunResult
"""

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.gmail_ingestor.reader import (
    build_gmail_reader_service,
    search_trip_booking_emails,
    fetch_message_content,
)
from automation.gmail_ingestor.parser import (
    is_trip_booking_email,
    parse_trip_email,
    TripEmailData,
)

log = logging.getLogger("gmail_ingestor.ingestor")


@dataclass
class IngestRunResult:
    started_at:     datetime = field(default_factory=datetime.utcnow)
    completed_at:   datetime | None = None
    emails_found:   int = 0
    emails_skipped: int = 0    # already imported
    emails_parsed:  int = 0
    parse_failed:   int = 0
    parse_partial:  int = 0
    sheet_written:  int = 0
    errors:         list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"found={self.emails_found} skipped={self.emails_skipped} "
            f"parsed={self.emails_parsed} failed={self.parse_failed} "
            f"sheet_written={self.sheet_written}"
        )


class GmailTripEmailIngestor:
    """
    Ingests Amazon Relay trip booking emails from Gmail into the DB and Master Sheet.

    Deduplication: each Gmail message ID is stored in GmailTripEmail.message_id
    (unique constraint). Already-imported messages are skipped without DB query
    by checking the in-memory set built at startup.
    """

    def __init__(self, app=None, dry_run: bool = False):
        """
        Args:
            app:     Flask app for DB access. Required for persistence.
            dry_run: If True, parse emails but do not write to DB or Sheets.
        """
        self._app     = app
        self._dry_run = dry_run

    def run(self, lookback_days: int = 7) -> IngestRunResult:
        """
        Run the full ingestion pipeline.

        Args:
            lookback_days: Search Gmail for emails received in the last N days.

        Returns:
            IngestRunResult with counts and any error messages.
        """
        result = IngestRunResult()
        log.info("=" * 60)
        log.info("Gmail ingest START | lookback=%d days dry_run=%s", lookback_days, self._dry_run)
        log.info("=" * 60)

        # ── 1. Build Gmail service ─────────────────────────────────────────────
        try:
            service = build_gmail_reader_service()
        except Exception as e:
            err = f"Gmail auth failed: {e}"
            log.error(err)
            result.errors.append(err)
            result.completed_at = datetime.utcnow()
            return result

        # ── 2. Load already-imported message IDs from DB ───────────────────────
        imported_ids: set[str] = self._load_imported_ids()
        log.info("Already-imported message IDs in DB: %d", len(imported_ids))

        # ── 3. Search Gmail ────────────────────────────────────────────────────
        after_date = datetime.utcnow() - timedelta(days=lookback_days)
        try:
            candidates = search_trip_booking_emails(service, max_results=500, after_date=after_date)
        except Exception as e:
            err = f"Gmail search failed: {e}"
            log.error(err)
            result.errors.append(err)
            result.completed_at = datetime.utcnow()
            return result

        result.emails_found = len(candidates)

        # ── 4. Bootstrap master sheet writer ──────────────────────────────────
        master_writer = None
        sheets_enabled = bool(os.getenv("SHEETS_TOKEN_JSON", "").strip()) or (PROJECT_ROOT / "sheets_token.json").exists()
        if sheets_enabled and not self._dry_run:
            try:
                from automation.sheets.master_sheet import MasterSheetWriter
                master_writer = MasterSheetWriter()
                master_writer.ensure_sheet()
                log.info("Master sheet ready: id=%s", master_writer._ss.id)
            except Exception as e:
                log.warning("Master sheet init failed — will persist to DB only: %s", e)
                result.errors.append(f"Master sheet init: {e}")

        # ── 5. Process each candidate ──────────────────────────────────────────
        for stub in candidates:
            msg_id = stub["id"]

            if msg_id in imported_ids:
                result.emails_skipped += 1
                log.debug("Skipping already-imported message: %s", msg_id)
                continue

            # Fetch full message
            try:
                content = fetch_message_content(service, msg_id)
            except Exception as e:
                err = f"Fetch failed for {msg_id}: {e}"
                log.warning(err)
                result.errors.append(err)
                continue

            # Subject filter — confirm it's really a trip booking email
            if not is_trip_booking_email(content["subject"]):
                log.debug("Skipping non-booking email: %r", content["subject"])
                result.emails_skipped += 1
                continue

            # Parse
            parsed = parse_trip_email(
                subject     = content["subject"],
                body        = content["body_text"],
                message_id  = msg_id,
                received_at = content["received_at"],
            )

            if parsed.parse_confidence == "failed":
                result.parse_failed += 1
                self._persist(parsed, import_status="parse_failed")
                continue
            elif parsed.parse_confidence == "partial":
                result.parse_partial += 1

            result.emails_parsed += 1

            if self._dry_run:
                log.info("[DRY RUN] Would write trip=%s payout=%s", parsed.trip_id, parsed.estimated_payout)
                continue

            # ── Save to DB ────────────────────────────────────────────────────
            db_record = self._persist(parsed, import_status="pending")

            # ── Write to master sheet ─────────────────────────────────────────
            if master_writer and db_record:
                try:
                    row_num = master_writer.append_or_update(parsed)
                    self._update_sheet_row(db_record.id, row_num)
                    result.sheet_written += 1
                except Exception as e:
                    err = f"Master sheet write failed for trip={parsed.trip_id}: {e}"
                    log.error(err)
                    result.errors.append(err)
                    self._mark_failed(db_record.id, str(e))
            elif db_record:
                self._update_status(db_record.id, "db_only")

        result.completed_at = datetime.utcnow()
        log.info("=" * 60)
        log.info("Gmail ingest DONE | %s", result.summary())
        log.info("=" * 60)
        return result

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _load_imported_ids(self) -> set[str]:
        if not self._app:
            return set()
        try:
            from models import GmailTripEmail
            with self._app.app_context():
                rows = GmailTripEmail.query.with_entities(GmailTripEmail.message_id).all()
                return {r.message_id for r in rows}
        except Exception as e:
            log.warning("Could not load imported message IDs: %s", e)
            return set()

    def _persist(self, parsed: TripEmailData, import_status: str = "pending"):
        """Save or update a GmailTripEmail record. Returns the ORM object or None."""
        if not self._app:
            return None
        try:
            from models import GmailTripEmail
            from extensions import db
            with self._app.app_context():
                existing = GmailTripEmail.query.filter_by(message_id=parsed.message_id).first()
                if existing:
                    record = existing
                else:
                    record = GmailTripEmail(message_id=parsed.message_id)
                    db.session.add(record)

                record.thread_id        = ""
                record.subject          = parsed.subject
                record.received_at      = parsed.received_at
                record.trip_id          = parsed.trip_id
                record.estimated_payout = parsed.estimated_payout
                record.origin           = parsed.origin
                record.destination      = parsed.destination
                record.pickup_dt        = parsed.pickup_dt
                record.dropoff_dt       = parsed.dropoff_dt
                record.driver           = parsed.driver
                record.rate             = parsed.rate
                record.miles            = parsed.miles
                record.raw_body_snippet = parsed.raw_snippet
                record.parse_confidence = parsed.parse_confidence
                record.parse_notes      = "; ".join(parsed.parse_notes)
                record.import_status    = import_status

                db.session.commit()
                log.debug("Persisted GmailTripEmail id=%d trip=%s", record.id, parsed.trip_id)
                return record
        except Exception as e:
            log.error("DB persist failed for message %s: %s", parsed.message_id, e)
            return None

    def _update_sheet_row(self, record_id: int, row_num: int) -> None:
        if not self._app or not record_id:
            return
        try:
            from models import GmailTripEmail
            from extensions import db
            with self._app.app_context():
                r = GmailTripEmail.query.get(record_id)
                if r:
                    r.sheet_row     = row_num
                    r.import_status = "written"
                    db.session.commit()
        except Exception as e:
            log.warning("Could not update sheet_row: %s", e)

    def _update_status(self, record_id: int, status: str) -> None:
        if not self._app or not record_id:
            return
        try:
            from models import GmailTripEmail
            from extensions import db
            with self._app.app_context():
                r = GmailTripEmail.query.get(record_id)
                if r:
                    r.import_status = status
                    db.session.commit()
        except Exception as e:
            log.warning("Could not update import_status: %s", e)

    def _mark_failed(self, record_id: int, error: str) -> None:
        if not self._app or not record_id:
            return
        try:
            from models import GmailTripEmail
            from extensions import db
            with self._app.app_context():
                r = GmailTripEmail.query.get(record_id)
                if r:
                    r.import_status = "sheet_failed"
                    r.parse_notes   = (r.parse_notes or "") + f" | sheet_error: {error}"
                    db.session.commit()
        except Exception as e:
            log.warning("Could not mark failed: %s", e)
