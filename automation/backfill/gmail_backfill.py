"""
automation/backfill/gmail_backfill.py

Historical Gmail backfill into the BCAT Master Trip Payouts spreadsheet.

Searches all of ai4bcat@gmail.com for Amazon Relay booking emails, groups them
by calendar week, and writes each group into a dedicated weekly tab on the
Master Sheet ("Apr 5 – 10" format, Sunday → Friday).

Resumable: each processed (source='gmail', week_start) is recorded in
BackfillProgress. Re-running skips completed weeks unless force=True.

Public API:
  GmailBackfill(app)
    .run(dry_run, force, batch_size) -> GmailBackfillResult
    .run_week(week_start, dry_run)   -> dict
"""

import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

log = logging.getLogger("backfill.gmail")


@dataclass
class GmailBackfillResult:
    started_at:      datetime = field(default_factory=datetime.utcnow)
    completed_at:    datetime | None = None
    emails_found:    int = 0
    emails_skipped:  int = 0   # already in DB / already in sheet
    emails_parsed:   int = 0
    parse_failed:    int = 0
    weeks_processed: int = 0
    weeks_skipped:   int = 0   # already completed in BackfillProgress
    rows_written:    int = 0
    errors:          list[str] = field(default_factory=list)
    week_summary:    list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"found={self.emails_found} parsed={self.emails_parsed} "
            f"failed={self.parse_failed} weeks={self.weeks_processed} "
            f"rows_written={self.rows_written}"
        )


class GmailBackfill:
    """
    Ingests all historical Gmail booking emails into Master Sheet weekly tabs.
    """

    def __init__(self, app=None):
        self._app = app

    def run(
        self,
        dry_run:    bool = False,
        force:      bool = False,   # reprocess weeks already marked completed
        batch_size: int  = 50,      # emails to fetch per batch before writing
    ) -> GmailBackfillResult:
        """
        Full historical Gmail backfill.

        Args:
            dry_run:    Parse emails but do not write to sheets or DB.
            force:      Reprocess weeks already recorded in BackfillProgress.
            batch_size: Number of emails to fetch full content for at once.
        """
        result = GmailBackfillResult()
        log.info("=" * 60)
        log.info("Gmail historical backfill START | dry_run=%s force=%s", dry_run, force)
        log.info("=" * 60)

        # ── 1. Build Gmail service ─────────────────────────────────────────
        try:
            from automation.gmail_ingestor.reader import (
                build_gmail_reader_service,
                search_trip_booking_emails,
                fetch_message_content,
            )
            service = build_gmail_reader_service()
        except Exception as e:
            err = f"Gmail auth failed: {e}"
            log.error(err)
            result.errors.append(err)
            result.completed_at = datetime.utcnow()
            return result

        # ── 2. Load already-imported message IDs ──────────────────────────
        imported_ids: set[str] = self._load_imported_ids()
        log.info("Already-imported message IDs in DB: %d", len(imported_ids))

        # ── 3. Load completed weeks (for resumability) ────────────────────
        completed_weeks: set[str] = set() if force else self._load_completed_weeks()
        log.info("Already-completed Gmail weeks: %d", len(completed_weeks))

        # ── 4. Search all Gmail history ───────────────────────────────────
        try:
            candidates = search_trip_booking_emails(service, max_results=5000, after_date=None)
        except Exception as e:
            err = f"Gmail search failed: {e}"
            log.error(err)
            result.errors.append(err)
            result.completed_at = datetime.utcnow()
            return result

        result.emails_found = len(candidates)
        log.info("Gmail candidates found: %d", len(candidates))

        # ── 5. Fetch + parse new emails ───────────────────────────────────
        from automation.gmail_ingestor.parser import (
            is_trip_booking_email,
            parse_trip_email,
        )

        parsed_by_week: dict[str, list] = defaultdict(list)
        skipped = 0

        for i, stub in enumerate(candidates):
            msg_id = stub["id"]
            if msg_id in imported_ids:
                skipped += 1
                continue

            try:
                content = fetch_message_content(service, msg_id)
            except Exception as e:
                log.warning("Fetch failed for %s: %s", msg_id, e)
                result.errors.append(f"Fetch {msg_id}: {e}")
                continue

            if not is_trip_booking_email(content["subject"]):
                skipped += 1
                continue

            parsed = parse_trip_email(
                subject     = content["subject"],
                body        = content["body_text"],
                message_id  = msg_id,
                received_at = content["received_at"],
            )

            if parsed.parse_confidence == "failed":
                result.parse_failed += 1
                log.debug("Parse failed for %s subject=%r", msg_id, content["subject"])
                continue

            result.emails_parsed += 1

            from automation.sheets.master_sheet import sunday_of
            week_start = sunday_of(parsed.received_at)
            parsed_by_week[week_start].append(parsed)

            if (i + 1) % 50 == 0:
                log.info("  Progress: fetched %d/%d (parsed=%d skipped=%d failed=%d)",
                         i + 1, len(candidates), result.emails_parsed,
                         skipped, result.parse_failed)

        result.emails_skipped = skipped
        log.info("Fetch complete. Parsed %d emails across %d weeks.",
                 result.emails_parsed, len(parsed_by_week))

        if not parsed_by_week:
            log.info("No new emails to write.")
            result.completed_at = datetime.utcnow()
            return result

        # ── 6. Bootstrap master sheet ─────────────────────────────────────
        master_writer = None
        if not dry_run:
            try:
                from automation.sheets.master_sheet import MasterSheetWriter
                master_writer = MasterSheetWriter()
                master_writer.ensure_sheet()
                log.info("Master sheet ready: id=%s", master_writer._ss.id)
            except Exception as e:
                err = f"Master sheet init failed: {e}"
                log.error(err)
                result.errors.append(err)

        # ── 7. Write week by week ─────────────────────────────────────────
        for week_start in sorted(parsed_by_week.keys()):
            week_emails = parsed_by_week[week_start]

            if week_start in completed_weeks:
                log.info("Skipping already-completed week %s (%d emails)", week_start, len(week_emails))
                result.weeks_skipped += 1
                continue

            log.info("Processing week %s — %d emails", week_start, len(week_emails))

            if dry_run:
                log.info("[DRY RUN] Would write %d emails to week tab %s", len(week_emails), week_start)
                result.weeks_processed += 1
                result.rows_written += len(week_emails)
                result.week_summary.append({
                    "week_start": week_start,
                    "emails":     len(week_emails),
                    "written":    len(week_emails),
                    "dry_run":    True,
                })
                continue

            week_written  = 0
            week_failed   = 0
            week_errors   = []

            for parsed in week_emails:
                try:
                    if master_writer:
                        master_writer.append_or_update_to_week_tab(parsed)
                        week_written += 1
                    self._persist(parsed)
                except Exception as e:
                    week_failed += 1
                    week_errors.append(str(e))
                    log.warning("Failed to write trip %s: %s", parsed.trip_id, e)

            self._record_progress(
                source   = "gmail",
                week_start = week_start,
                status   = "completed" if not week_errors else "failed",
                rows_found   = len(week_emails),
                rows_written = week_written,
                rows_skipped = 0,
                parse_failed = 0,
                unmatched    = 0,
                notes        = "; ".join(week_errors[:3]),
            )

            result.weeks_processed += 1
            result.rows_written    += week_written
            result.week_summary.append({
                "week_start": week_start,
                "emails":     len(week_emails),
                "written":    week_written,
                "failed":     week_failed,
            })

            log.info("Week %s done: written=%d failed=%d", week_start, week_written, week_failed)

        result.completed_at = datetime.utcnow()
        log.info("=" * 60)
        log.info("Gmail backfill DONE | %s", result.summary())
        log.info("=" * 60)
        return result

    def run_week(self, week_start: str, dry_run: bool = False) -> dict:
        """
        Backfill a single specific week from Gmail.
        Fetches all emails, filters to those received in [week_start, week_start+6d].
        """
        from datetime import timedelta
        from automation.gmail_ingestor.reader import (
            build_gmail_reader_service,
            search_trip_booking_emails,
            fetch_message_content,
        )
        from automation.gmail_ingestor.parser import is_trip_booking_email, parse_trip_email
        from automation.sheets.master_sheet import sunday_of, MasterSheetWriter

        try:
            ws_date = datetime.strptime(week_start, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid week_start: {week_start}"}

        week_end = ws_date + timedelta(days=6)

        service  = build_gmail_reader_service()
        # Search only that week
        candidates = search_trip_booking_emails(service, max_results=500, after_date=ws_date)

        imported_ids = self._load_imported_ids()
        parsed_list = []

        for stub in candidates:
            msg_id = stub["id"]
            if msg_id in imported_ids:
                continue
            try:
                content = fetch_message_content(service, msg_id)
            except Exception as e:
                log.warning("Fetch failed %s: %s", msg_id, e)
                continue
            if not is_trip_booking_email(content["subject"]):
                continue
            parsed = parse_trip_email(
                subject=content["subject"], body=content["body_text"],
                message_id=msg_id, received_at=content["received_at"],
            )
            if parsed.parse_confidence == "failed":
                continue
            if parsed.received_at and not (ws_date <= parsed.received_at <= week_end):
                continue
            parsed_list.append(parsed)

        if dry_run:
            return {"week_start": week_start, "found": len(parsed_list), "dry_run": True}

        master = MasterSheetWriter()
        master.ensure_sheet()
        written = 0
        for p in parsed_list:
            try:
                master.append_or_update_to_week_tab(p)
                self._persist(p)
                written += 1
            except Exception as e:
                log.warning("Write failed for %s: %s", p.trip_id, e)

        return {"week_start": week_start, "found": len(parsed_list), "written": written}

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
            log.warning("Could not load imported IDs: %s", e)
            return set()

    def _load_completed_weeks(self) -> set[str]:
        if not self._app:
            return set()
        try:
            from models import BackfillProgress
            with self._app.app_context():
                rows = BackfillProgress.query.filter_by(
                    source="gmail", status="completed"
                ).with_entities(BackfillProgress.week_start).all()
                return {r.week_start for r in rows}
        except Exception as e:
            log.warning("Could not load completed weeks: %s", e)
            return set()

    def _persist(self, parsed):
        if not self._app:
            return
        try:
            from models import GmailTripEmail
            from extensions import db
            with self._app.app_context():
                existing = GmailTripEmail.query.filter_by(message_id=parsed.message_id).first()
                if existing:
                    return
                record = GmailTripEmail(
                    message_id      = parsed.message_id,
                    thread_id       = "",
                    subject         = parsed.subject,
                    received_at     = parsed.received_at,
                    trip_id         = parsed.trip_id,
                    estimated_payout= parsed.estimated_payout,
                    origin          = parsed.origin,
                    destination     = parsed.destination,
                    pickup_dt       = parsed.pickup_dt,
                    dropoff_dt      = parsed.dropoff_dt,
                    driver          = parsed.driver,
                    rate            = parsed.rate,
                    miles           = parsed.miles,
                    raw_body_snippet= parsed.raw_snippet,
                    parse_confidence= parsed.parse_confidence,
                    parse_notes     = "; ".join(parsed.parse_notes),
                    import_status   = "backfill",
                )
                db.session.add(record)
                db.session.commit()
        except Exception as e:
            log.warning("DB persist failed for %s: %s", parsed.message_id, e)

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
                    existing.rows_found   = kwargs.get("rows_found", 0)
                    existing.rows_written = kwargs.get("rows_written", 0)
                    existing.rows_skipped = kwargs.get("rows_skipped", 0)
                    existing.parse_failed = kwargs.get("parse_failed", 0)
                    existing.unmatched    = kwargs.get("unmatched", 0)
                    existing.notes        = kwargs.get("notes", "")
                    existing.processed_at = datetime.utcnow()
                else:
                    db.session.add(BackfillProgress(
                        source       = source,
                        week_start   = week_start,
                        status       = status,
                        rows_found   = kwargs.get("rows_found", 0),
                        rows_written = kwargs.get("rows_written", 0),
                        rows_skipped = kwargs.get("rows_skipped", 0),
                        parse_failed = kwargs.get("parse_failed", 0),
                        unmatched    = kwargs.get("unmatched", 0),
                        notes        = kwargs.get("notes", ""),
                    ))
                db.session.commit()
        except Exception as e:
            log.warning("Could not record backfill progress: %s", e)
