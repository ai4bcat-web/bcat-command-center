"""
automation/trip_report/job.py
──────────────────────────────
WeeklyTripHistoryReportJob

Orchestrates the weekly Amazon trip-report workflow:

  1. Compute the Amazon reporting window (most recently completed Sunday–Saturday)
  2. Load trip data from AmazonTrip DB table (fallback: CSV)
  3. Build per-driver reports via TripReportBuilder
  4. For each driver report:
       a. Check idempotency — skip if already successfully sent for this week
       b. Generate PDF
       c. Send email with PDF attached
       d. Post Discord notification
       e. Update DriverReportRun status in DB
  5. Finalize ReportJobRun record (completed or failed)

Reporting window
────────────────
Amazon's weekly reporting window is Sunday through Saturday.

When the job runs on Sunday at 8 AM it reports on the week that just ended:
  - window_start = the Sunday that began the previous week
  - window_end   = the Saturday that ended the previous week

Example: job runs Sunday Apr 12 → reports on Apr 5 (Sun) – Apr 11 (Sat).

If run manually on any other day of the week it still resolves to the most
recently COMPLETED Saturday and the Sunday 6 days before it.

Idempotency
───────────
Before creating a new DriverReportRun the job queries for any existing
DriverReportRun with the same window_start AND driver_name AND
email_status='sent'.  If found, that driver is skipped for the current run
unless REPORT_FORCE_RESEND=true.

This means re-running the job on the same Sunday — or triggering it manually
for the same week — will not double-send reports.

Configuration (env vars)
────────────────────────
  REPORT_RECIPIENT_EMAIL     — destination address (required for real sends)
  REPORT_OUTPUT_DIR          — directory for generated PDFs (default: /tmp/trip_reports)
  REPORT_DRY_RUN             — "true" to skip actual email/Discord sends
  REPORT_FORCE_RESEND        — "true" to ignore already-sent status
  REPORT_DRIVER_NAMES        — comma-separated driver allow-list (default: DspDriver table)
  REPORT_WEEK_ENDING         — override the window: set to a Saturday YYYY-MM-DD
                               (computes window_start automatically as Sun 6 days prior)
  REPORT_DISCORD_WEBHOOK_URL / DISCORD_WEBHOOK_URL — Discord webhook

Manual trigger examples
───────────────────────
  # Run for the auto-resolved current week:
  DATABASE_URL=<url> REPORT_RECIPIENT_EMAIL=you@example.com python report_cron.py

  # Dry run (generates PDFs, no email, no Discord):
  DATABASE_URL=<url> REPORT_RECIPIENT_EMAIL=x REPORT_DRY_RUN=true python report_cron.py

  # Report on a specific completed week (supply the Saturday end date):
  DATABASE_URL=<url> REPORT_WEEK_ENDING=2026-04-11 python report_cron.py

  # Force resend even if already sent this week:
  DATABASE_URL=<url> REPORT_FORCE_RESEND=true python report_cron.py
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)


# ── Window calculation ────────────────────────────────────────────────────────

def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('true', '1', 'yes')


def _amazon_weekly_window(run_date: str | None = None) -> tuple[str, str]:
    """Return (window_start, window_end) for the CURRENT Amazon week-to-date.

    Amazon week = Sunday through Saturday.
    Returns (most recent Sunday, today) so the report always reflects the
    current week in progress, not the prior completed week.

    Uses isoweekday(): Mon=1 … Sat=6, Sun=7.
    days_since_sunday = isoweekday % 7  →  Sun=0, Mon=1, Tue=2 … Sat=6

    Examples (run on Wednesday Apr 8):
      isoweekday=3, days_since_sunday=3
      window_start = Apr 8 - 3 = Apr 5 (Sun)  ✓
      window_end   = Apr 8         (today)     ✓

    Run on Sunday Apr 5:
      isoweekday=7, days_since_sunday=0
      window_start = Apr 5 (today, Sunday — new week starts)  ✓
      window_end   = Apr 5                                     ✓
    """
    env_ending = os.getenv('REPORT_WEEK_ENDING', '').strip()
    if env_ending:
        # Explicit override: treat as a full completed week ending on this Saturday
        try:
            window_end   = date.fromisoformat(env_ending)
            window_start = window_end - timedelta(days=6)
            return window_start.isoformat(), window_end.isoformat()
        except ValueError:
            log.warning("REPORT_WEEK_ENDING='%s' is not a valid YYYY-MM-DD date — ignoring.", env_ending)

    today = date.fromisoformat(run_date) if run_date else date.today()
    dow   = today.isoweekday()          # Mon=1 … Sat=6, Sun=7
    # Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6
    days_since_sunday = dow % 7
    window_start = today - timedelta(days=days_since_sunday)
    window_end   = today   # week-to-date through today
    return window_start.isoformat(), window_end.isoformat()


def _window_from_params(
    week_ending: str | None = None,
    week_start:  str | None = None,
    week_end:    str | None = None,
) -> tuple[str, str]:
    """Resolve a manual window override from explicit date params.

    Priority:
      1. week_start + week_end pair (used as-is)
      2. week_ending alone (Saturday date → compute Sunday 6 days prior)
      3. Auto-resolve from today via _amazon_weekly_window()
    """
    if week_start and week_end:
        return week_start, week_end
    if week_ending:
        try:
            end   = date.fromisoformat(week_ending)
            start = end - timedelta(days=6)
            return start.isoformat(), end.isoformat()
        except ValueError:
            log.warning("week_ending='%s' is not a valid YYYY-MM-DD — auto-resolving.", week_ending)
    return _amazon_weekly_window()


# ── Job ───────────────────────────────────────────────────────────────────────

class WeeklyTripHistoryReportJob:
    """Weekly Amazon trip-report workflow — runs once and exits."""

    def __init__(self, app=None):
        """
        Args:
            app: Flask app instance.  Required for DB access.  When None the
                 job falls back to CSV-only mode and no DB records are written.
        """
        self._app = app

    # ── Public entry point ────────────────────────────────────────────────────

    def run(
        self,
        dry_run:      bool | None = None,
        week_ending:  str  | None = None,   # Saturday YYYY-MM-DD
        week_start:   str  | None = None,   # Sunday YYYY-MM-DD  (overrides week_ending)
        week_end:     str  | None = None,   # Saturday YYYY-MM-DD (overrides week_ending)
        force_resend: bool | None = None,   # override REPORT_FORCE_RESEND env var
    ) -> bool:
        """Execute the full weekly workflow.

        Args:
            dry_run:     Override REPORT_DRY_RUN env var.
            week_ending: Report on the week ending this Saturday.
            week_start:  Explicit Sunday start date (use with week_end).
            week_end:    Explicit Saturday end date (use with week_start).

        Returns:
            True if all driver reports succeeded, False if any failed.
        """
        from automation.trip_report.builder          import TripReportBuilder
        from automation.trip_report.pdf_generator    import PDFReportGenerator
        from automation.trip_report.email_sender     import ReportEmailSender
        from automation.trip_report.discord_notifier import DiscordReportNotifier

        effective_dry_run = dry_run if dry_run is not None else _bool_env('REPORT_DRY_RUN')
        force_resend      = force_resend if force_resend is not None else _bool_env('REPORT_FORCE_RESEND')
        report_date       = date.today().isoformat()

        window_start, window_end = _window_from_params(week_ending, week_start, week_end)

        log.info("=" * 60)
        log.info("Weekly Trip Report job — %s UTC", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
        log.info("Report date  : %s", report_date)
        log.info("Window       : %s (Sun) – %s (Sat)", window_start, window_end)
        log.info("Dry run      : %s", effective_dry_run)
        log.info("Force resend : %s", force_resend)
        log.info("=" * 60)

        # ── 1. Create job-run audit record ────────────────────────────────────
        job_run_id = self._create_job_run(
            report_date  = report_date,
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
            self._fail_job(job_run_id, err)
            DiscordReportNotifier().notify_failure(
                'ALL', 'data_load', err, dry_run=effective_dry_run
            )
            return False

        # ── 3. Build per-driver reports ───────────────────────────────────────
        builder = TripReportBuilder(app=self._app)
        driver_reports = builder.build(
            raw_trips    = raw_trips,
            report_date  = report_date,
            window_start = window_start,
            window_end   = window_end,
        )

        if not driver_reports:
            msg = (
                f"No driver reports to send for week "
                f"{window_start} (Sun) – {window_end} (Sat)."
            )
            log.warning(msg)
            self._complete_job(job_run_id, 0, 0.0, 0, summary=msg)
            return True

        # ── 4. Initialise email sender (validates env var early) ──────────────
        try:
            sender = ReportEmailSender() if not effective_dry_run else None
        except RuntimeError as exc:
            if effective_dry_run:
                sender = None
                log.warning("Email sender init skipped in dry-run: %s", exc)
            else:
                err = str(exc)
                log.error(err)
                self._fail_job(job_run_id, err)
                return False

        # ── 5. Process each driver ────────────────────────────────────────────
        pdf_gen    = PDFReportGenerator()
        notifier   = DiscordReportNotifier()
        failed     = 0
        sent_count = 0

        for report in driver_reports:
            # ── idempotency: check if this driver's week was already sent ──
            if not force_resend and self._already_sent(window_start, report.driver_name):
                log.info(
                    "Skipping %s — week %s already sent. Use REPORT_FORCE_RESEND=true to override.",
                    report.driver_name, window_start,
                )
                continue

            drv_run_id = self._create_driver_run(job_run_id, report)

            log.info(
                "Processing driver: %s (%d trips, $%.2f)",
                report.driver_name, report.trip_count, report.total_revenue,
            )

            # ── a. Generate PDF ────────────────────────────────────────────
            try:
                pdf_path = pdf_gen.generate(report)
                self._update_driver_run(drv_run_id, pdf_path=pdf_path)
            except Exception as exc:
                err = f"PDF generation failed: {exc}"
                log.error(err, exc_info=True)
                self._update_driver_run(drv_run_id, email_status='failed', email_error=err)
                notifier.notify_failure(report.driver_name, 'pdf', err, dry_run=effective_dry_run)
                self._update_driver_run(
                    drv_run_id,
                    discord_status  = 'sent' if not effective_dry_run else 'skipped',
                    discord_sent_at = datetime.utcnow(),
                )
                failed += 1
                continue

            # ── b. Send email ──────────────────────────────────────────────
            try:
                if sender:
                    sender.send(report, pdf_path)
                else:
                    log.info("[DRY RUN] Would send email for %s", report.driver_name)
                self._update_driver_run(
                    drv_run_id,
                    email_status  = 'sent' if not effective_dry_run else 'skipped',
                    email_sent_at = datetime.utcnow(),
                )
            except Exception as exc:
                err = f"Email send failed: {exc}"
                log.error(err, exc_info=True)
                self._update_driver_run(drv_run_id, email_status='failed', email_error=err)
                notifier.notify_failure(report.driver_name, 'email', err, dry_run=effective_dry_run)
                self._update_driver_run(
                    drv_run_id,
                    discord_status  = 'sent' if not effective_dry_run else 'skipped',
                    discord_sent_at = datetime.utcnow(),
                )
                failed += 1
                continue

            # ── c. Discord notification ────────────────────────────────────
            try:
                notifier.notify_success(report, dry_run=effective_dry_run)
                self._update_driver_run(
                    drv_run_id,
                    discord_status  = 'sent' if not effective_dry_run else 'skipped',
                    discord_sent_at = datetime.utcnow(),
                )
            except Exception as exc:
                warn = f"Discord notify failed: {exc}"
                log.warning(warn)
                self._update_driver_run(drv_run_id, discord_status='failed', discord_error=warn)

            sent_count += 1

        # ── 6. Finalize ───────────────────────────────────────────────────────
        total_trips   = sum(r.trip_count    for r in driver_reports)
        total_revenue = sum(r.total_revenue for r in driver_reports)
        summary = (
            f"Sent {sent_count}/{len(driver_reports)} driver reports. "
            f"Week: {window_start} – {window_end}. "
            f"Total trips: {total_trips}. Total revenue: ${total_revenue:,.2f}."
            + (f" {failed} failed." if failed else '')
        )
        self._complete_job(job_run_id, total_trips, total_revenue, len(driver_reports), summary=summary)

        notifier.notify_job_complete(
            window_start  = window_start,
            window_end    = window_end,
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

    # ── Idempotency ───────────────────────────────────────────────────────────

    def _already_sent(self, window_start: str, driver_name: str) -> bool:
        """Return True if this driver's report for this week was already emailed."""
        if not self._app:
            return False
        try:
            from models import DriverReportRun
            with self._app.app_context():
                return DriverReportRun.query.filter_by(
                    window_start = window_start,
                    driver_name  = driver_name,
                    email_status = 'sent',
                ).first() is not None
        except Exception as exc:
            log.warning("Idempotency check failed: %s", exc)
            return False

    # ── DB record helpers ─────────────────────────────────────────────────────

    def _create_job_run(self, report_date, window_start, window_end, dry_run):
        if not self._app:
            return None
        try:
            from models import ReportJobRun
            from extensions import db
            with self._app.app_context():
                jr = ReportJobRun(
                    job_type     = 'weekly_trip_report',
                    report_date  = report_date,
                    window_start = window_start,
                    window_end   = window_end,
                    status       = 'running',
                    dry_run      = dry_run,
                )
                db.session.add(jr)
                db.session.commit()
                log.info("ReportJobRun created: id=%d", jr.id)
                return jr.id
        except Exception as exc:
            log.warning("Could not create ReportJobRun: %s", exc)
            return None

    def _fail_job(self, job_run_id, error: str):
        self._finalize_job(job_run_id, 'failed', 0, 0.0, 0, error=error)

    def _complete_job(self, job_run_id, total_trips, total_revenue, driver_count, summary=''):
        self._finalize_job(
            job_run_id, 'completed', total_trips, total_revenue, driver_count, summary=summary
        )

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
                    job_run_id    = job_run_id,
                    driver_name   = report.driver_name,
                    driver_type   = report.driver_type,
                    report_date   = report.report_date,
                    window_start  = report.window_start,
                    window_end    = report.window_end,
                    trip_count    = report.trip_count,
                    total_revenue = report.total_revenue,
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


# ── Backwards-compatible alias ────────────────────────────────────────────────
DailyTripHistoryReportJob = WeeklyTripHistoryReportJob
