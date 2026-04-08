"""
automation/trip_report/job.py
──────────────────────────────
DailyTripHistoryReportJob

Orchestrates the full daily Amazon trip-report workflow:

  1. Compute reporting window (last N days, configurable)
  2. Load trip data from AmazonTrip DB table (fallback: CSV)
  3. Build per-driver reports via TripReportBuilder
  4. For each driver report:
       a. Check idempotency — skip if already successfully sent today
       b. Generate PDF
       c. Send email with PDF attached
       d. Post Discord notification
       e. Update DriverReportRun status in DB
  5. Finalize ReportJobRun record (completed or failed)

Idempotency
───────────
A DriverReportRun row is created for each (job_run_id, driver_name) pair.
If the job is re-run for the same date (e.g. manual retry), existing
DriverReportRun rows with email_status='sent' are skipped unless
REPORT_FORCE_RESEND=true is set.

Configuration (env vars)
────────────────────────
  REPORT_WINDOW_DAYS       — how many days back to include (default: 7)
  REPORT_RECIPIENT_EMAIL   — destination email address (required for real sends)
  REPORT_OUTPUT_DIR        — directory for generated PDFs (default: /tmp/trip_reports)
  REPORT_DRY_RUN           — "true" to skip actual email/Discord sends (default: false)
  REPORT_FORCE_RESEND      — "true" to ignore already-sent status (default: false)
  REPORT_DRIVER_NAMES      — comma-separated driver allow-list (default: from DspDriver table)
  REPORT_DISCORD_WEBHOOK_URL / DISCORD_WEBHOOK_URL — Discord webhook

Manual trigger
──────────────
  DATABASE_URL=<url> python report_cron.py
  DATABASE_URL=<url> REPORT_DRY_RUN=true python report_cron.py
  DATABASE_URL=<url> REPORT_WINDOW_DAYS=30 python report_cron.py
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('true', '1', 'yes')


def _window_dates() -> tuple[str, str]:
    """Return (window_start, window_end) as YYYY-MM-DD strings."""
    days   = int(os.getenv('REPORT_WINDOW_DAYS', '7'))
    today  = date.today()
    end    = today - timedelta(days=1)           # yesterday
    start  = today - timedelta(days=days)
    return start.isoformat(), end.isoformat()


class DailyTripHistoryReportJob:
    """Full daily trip-report workflow — runs once and exits."""

    def __init__(self, app=None):
        """
        Args:
            app: Flask app instance.  Required for DB access.  When None the
                 job falls back to CSV-only mode and no DB records are written.
        """
        self._app = app

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, report_date: str | None = None, dry_run: bool | None = None) -> bool:
        """Execute the full workflow.

        Args:
            report_date: Override the report date (YYYY-MM-DD).  Defaults to today.
            dry_run:     Override REPORT_DRY_RUN env var.

        Returns:
            True if all driver reports succeeded, False if any failed.
        """
        from automation.trip_report.builder          import TripReportBuilder
        from automation.trip_report.pdf_generator    import PDFReportGenerator
        from automation.trip_report.email_sender     import ReportEmailSender
        from automation.trip_report.discord_notifier import DiscordReportNotifier

        effective_dry_run  = dry_run if dry_run is not None else _bool_env('REPORT_DRY_RUN')
        effective_date     = report_date or date.today().isoformat()
        window_start, window_end = _window_dates()
        force_resend       = _bool_env('REPORT_FORCE_RESEND')

        log.info("=" * 60)
        log.info("Daily Trip Report job  — %s UTC", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        log.info("Report date  : %s", effective_date)
        log.info("Window       : %s – %s", window_start, window_end)
        log.info("Dry run      : %s", effective_dry_run)
        log.info("Force resend : %s", force_resend)
        log.info("=" * 60)

        # ── 1. Create job-run audit record ────────────────────────────────────
        job_run = self._create_job_run(
            report_date  = effective_date,
            window_start = window_start,
            window_end   = window_end,
            dry_run      = effective_dry_run,
        )

        # ── 2. Load trip data ─────────────────────────────────────────────────
        try:
            raw_trips = self._load_trips(window_start, window_end)
            log.info("Loaded %d trips for window.", len(raw_trips))
        except Exception as exc:
            err = f"Failed to load trip data: {exc}"
            log.error(err, exc_info=True)
            self._fail_job(job_run, err)
            DiscordReportNotifier().notify_failure('ALL', 'data_load', err, dry_run=effective_dry_run)
            return False

        # ── 3. Build per-driver reports ───────────────────────────────────────
        builder = TripReportBuilder(app=self._app)
        driver_reports = builder.build(
            raw_trips    = raw_trips,
            report_date  = effective_date,
            window_start = window_start,
            window_end   = window_end,
        )

        if not driver_reports:
            msg = f"No driver reports to send for window {window_start} – {window_end}."
            log.warning(msg)
            self._complete_job(job_run, 0, 0.0, 0, summary=msg)
            return True

        # ── 4. Process each driver ────────────────────────────────────────────
        pdf_gen    = PDFReportGenerator()
        notifier   = DiscordReportNotifier()
        failed     = 0
        sent_count = 0

        # Initialise email sender once (validates env var early)
        try:
            sender = ReportEmailSender() if not effective_dry_run else None
        except RuntimeError as exc:
            if effective_dry_run:
                sender = None
                log.warning("Email sender init skipped in dry-run: %s", exc)
            else:
                err = str(exc)
                log.error(err)
                self._fail_job(job_run, err)
                return False

        for report in driver_reports:
            drv_run = self._create_driver_run(job_run, report)

            # ── idempotency check ──────────────────────────────────────────
            if not force_resend and drv_run and getattr(drv_run, 'email_status', '') == 'sent':
                log.info(
                    "Skipping %s — already sent (use REPORT_FORCE_RESEND=true to override).",
                    report.driver_name,
                )
                continue

            log.info("Processing driver: %s (%d trips, $%.2f)",
                     report.driver_name, report.trip_count, report.total_revenue)

            # ── a. Generate PDF ────────────────────────────────────────────
            try:
                pdf_path = pdf_gen.generate(report)
                self._update_driver_run(drv_run, pdf_path=pdf_path)
            except Exception as exc:
                err = f"PDF generation failed: {exc}"
                log.error(err, exc_info=True)
                self._update_driver_run(drv_run, email_status='failed', email_error=err)
                notifier.notify_failure(report.driver_name, 'pdf', err, dry_run=effective_dry_run)
                failed += 1
                continue

            # ── b. Send email ──────────────────────────────────────────────
            try:
                if sender:
                    sender.send(report, pdf_path)
                else:
                    log.info("[DRY RUN] Would send email for %s", report.driver_name)
                self._update_driver_run(drv_run,
                                        email_status='sent' if not effective_dry_run else 'skipped',
                                        email_sent_at=datetime.utcnow())
            except Exception as exc:
                err = f"Email send failed: {exc}"
                log.error(err, exc_info=True)
                self._update_driver_run(drv_run, email_status='failed', email_error=err)
                notifier.notify_failure(report.driver_name, 'email', err, dry_run=effective_dry_run)
                failed += 1
                continue

            # ── c. Discord notification ────────────────────────────────────
            try:
                notifier.notify_success(report, dry_run=effective_dry_run)
                self._update_driver_run(drv_run,
                                        discord_status='sent' if not effective_dry_run else 'skipped',
                                        discord_sent_at=datetime.utcnow())
            except Exception as exc:
                # Discord failure is non-fatal — email already sent
                warn = f"Discord notify failed: {exc}"
                log.warning(warn)
                self._update_driver_run(drv_run, discord_status='failed', discord_error=warn)

            sent_count += 1

        # ── 5. Finalize job run ───────────────────────────────────────────────
        total_trips   = sum(r.trip_count    for r in driver_reports)
        total_revenue = sum(r.total_revenue for r in driver_reports)
        summary = (
            f"Sent {sent_count}/{len(driver_reports)} driver reports. "
            f"Total trips: {total_trips}. Total revenue: ${total_revenue:,.2f}."
            + (f" {failed} failed." if failed else '')
        )
        self._complete_job(job_run, total_trips, total_revenue, len(driver_reports), summary=summary)

        notifier.notify_job_complete(
            report_date   = effective_date,
            driver_count  = len(driver_reports),
            total_trips   = total_trips,
            total_revenue = total_revenue,
            failed_count  = failed,
            dry_run       = effective_dry_run,
        )

        log.info(summary)
        log.info("=" * 60)
        log.info("Job complete — exiting. Success=%s", failed == 0)
        log.info("=" * 60)
        return failed == 0

    # ── Trip data loading ─────────────────────────────────────────────────────

    def _load_trips(self, window_start: str, window_end: str) -> list:
        """Load AmazonTrip records from DB (preferred) or CSV (fallback)."""
        if self._app:
            try:
                return self._load_from_db(window_start, window_end)
            except Exception as exc:
                log.warning("DB load failed (%s) — falling back to CSV.", exc)

        return self._load_from_csv(window_start, window_end)

    def _load_from_db(self, window_start: str, window_end: str) -> list:
        from models import AmazonTrip
        with self._app.app_context():
            rows = (
                AmazonTrip.query
                .filter(AmazonTrip.trip_date >= window_start)
                .filter(AmazonTrip.trip_date <= window_end)
                .all()
            )
            log.info("DB query returned %d rows.", len(rows))
            # Detach from session by converting to dicts before leaving context
            return [r.to_dict() for r in rows]

    def _load_from_csv(self, window_start: str, window_end: str) -> list:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from finance_agent import parse_amazon_relay_csv

        csv_path = Path(__file__).resolve().parents[2] / 'amazon_relay.csv'
        if not csv_path.exists():
            log.warning("amazon_relay.csv not found — no trip data available.")
            return []

        all_trips = parse_amazon_relay_csv(str(csv_path))
        filtered  = [
            t for t in all_trips
            if window_start <= str(t.get('trip_date', '')) <= window_end
        ]
        log.info("CSV returned %d trips (%d in window).", len(all_trips), len(filtered))
        return filtered

    # ── DB record helpers ─────────────────────────────────────────────────────

    def _create_job_run(self, report_date, window_start, window_end, dry_run):
        if not self._app:
            return None
        try:
            from models import ReportJobRun
            from extensions import db
            with self._app.app_context():
                jr = ReportJobRun(
                    job_type     = 'daily_trip_report',
                    report_date  = report_date,
                    window_start = window_start,
                    window_end   = window_end,
                    status       = 'running',
                    dry_run      = dry_run,
                )
                db.session.add(jr)
                db.session.commit()
                log.info("ReportJobRun created: id=%d", jr.id)
                return jr.id   # return ID, not ORM obj (avoids detached-instance issues)
        except Exception as exc:
            log.warning("Could not create ReportJobRun: %s", exc)
            return None

    def _fail_job(self, job_run_id, error: str):
        self._finalize_job(job_run_id, 'failed', 0, 0.0, 0, error=error)

    def _complete_job(self, job_run_id, total_trips, total_revenue, driver_count, summary=''):
        self._finalize_job(job_run_id, 'completed', total_trips, total_revenue,
                           driver_count, summary=summary)

    def _finalize_job(self, job_run_id, status, total_trips, total_revenue,
                      driver_count, error='', summary=''):
        if not self._app or job_run_id is None:
            return
        try:
            from models import ReportJobRun
            from extensions import db
            with self._app.app_context():
                jr = ReportJobRun.query.get(job_run_id)
                if jr:
                    jr.status        = status
                    jr.completed_at  = datetime.utcnow()
                    jr.total_trips   = total_trips
                    jr.total_revenue = total_revenue
                    jr.driver_count  = driver_count
                    jr.error         = error
                    jr.summary       = summary
                    db.session.commit()
        except Exception as exc:
            log.warning("Could not finalize ReportJobRun: %s", exc)

    def _create_driver_run(self, job_run_id, report):
        """Create or retrieve existing DriverReportRun for idempotency check."""
        if not self._app or job_run_id is None:
            return None
        try:
            from models import DriverReportRun
            from extensions import db
            with self._app.app_context():
                existing = DriverReportRun.query.filter_by(
                    job_run_id  = job_run_id,
                    driver_name = report.driver_name,
                ).first()
                if existing:
                    return existing.id
                drv = DriverReportRun(
                    job_run_id   = job_run_id,
                    driver_name  = report.driver_name,
                    driver_type  = report.driver_type,
                    report_date  = report.report_date,
                    window_start = report.window_start,
                    window_end   = report.window_end,
                    trip_count   = report.trip_count,
                    total_revenue= report.total_revenue,
                )
                db.session.add(drv)
                db.session.commit()
                return drv.id
        except Exception as exc:
            log.warning("Could not create DriverReportRun: %s", exc)
            return None

    def _update_driver_run(self, drv_run_id, **kwargs):
        if not self._app or drv_run_id is None:
            return
        try:
            from models import DriverReportRun
            from extensions import db
            with self._app.app_context():
                drv = DriverReportRun.query.get(drv_run_id)
                if drv:
                    for k, v in kwargs.items():
                        setattr(drv, k, v)
                    db.session.commit()
        except Exception as exc:
            log.warning("Could not update DriverReportRun: %s", exc)
