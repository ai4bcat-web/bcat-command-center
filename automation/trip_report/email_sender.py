"""
automation/trip_report/email_sender.py
───────────────────────────────────────
ReportEmailSender

Sends a driver trip-report PDF as an email attachment via the existing
EmailService (Gmail API + OAuth2).

Configuration (env vars)
────────────────────────
  REPORT_RECIPIENT_EMAIL  — destination address (required)
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, date as date_type

log = logging.getLogger(__name__)


def _fmt_week(window_start: str, window_end: str) -> str:
    """Return a human-readable weekly range string.

    Example: "Apr 5 – Apr 11, 2026"
    """
    try:
        s = datetime.strptime(window_start, '%Y-%m-%d')
        e = datetime.strptime(window_end,   '%Y-%m-%d')
        # Only print the year once (on the end date)
        if s.year == e.year:
            return f"{s.strftime('%b %-d')} – {e.strftime('%b %-d, %Y')}"
        return f"{s.strftime('%b %-d, %Y')} – {e.strftime('%b %-d, %Y')}"
    except ValueError:
        return f"{window_start} – {window_end}"


def _fmt_week_long(window_start: str, window_end: str) -> str:
    """Return a verbose weekly range string for the email body.

    Example: "Sunday, April 5, 2026 – Saturday, April 11, 2026"
    """
    try:
        s = datetime.strptime(window_start, '%Y-%m-%d')
        e = datetime.strptime(window_end,   '%Y-%m-%d')
        return (
            f"{s.strftime('%A, %B %-d, %Y')}"
            f" – "
            f"{e.strftime('%A, %B %-d, %Y')}"
        )
    except ValueError:
        return f"{window_start} – {window_end}"


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


class ReportEmailSender:
    """Sends one email per driver report with the PDF attached."""

    def __init__(self):
        self._recipient = os.getenv('REPORT_RECIPIENT_EMAIL', '').strip()
        if not self._recipient:
            raise RuntimeError(
                'REPORT_RECIPIENT_EMAIL env var is required for email delivery. '
                'Set it to the address that should receive the driver reports.'
            )
        self._svc = None   # lazy-initialised

    # ── Public API ────────────────────────────────────────────────────────────

    def send(self, report, pdf_path: str, dry_run: bool = False) -> None:
        """Send the driver report email.

        Args:
            report:   DriverReport dataclass.
            pdf_path: Absolute path to the generated PDF.
            dry_run:  If True, log the email but do not actually send it.

        Raises:
            Exception: Any error from the Gmail API is re-raised so the caller
                       can record the failure in DriverReportRun.
        """
        week_label = _fmt_week(report.window_start, report.window_end)
        subject = f"Amazon Trip Report – {report.driver_name} – Week of {week_label}"
        body    = self._build_body(report)
        attachment_name = (
            f"trip_report_{_slug(report.driver_name)}"
            f"_{report.window_start}_to_{report.window_end}.pdf"
        )

        if dry_run:
            log.info(
                "[DRY RUN] Would send email to %s | subject: %s | pdf: %s",
                self._recipient, subject, pdf_path,
            )
            return

        svc = self._get_service()
        svc.send_email_with_attachment(
            to              = self._recipient,
            subject         = subject,
            body            = body,
            attachment_path = pdf_path,
            attachment_name = attachment_name,
        )
        log.info(
            "Email sent → %s | driver: %s | week: %s | trips: %d | revenue: $%.2f",
            self._recipient, report.driver_name, week_label,
            report.trip_count, report.total_revenue,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_body(self, report) -> str:
        week_short = _fmt_week(report.window_start, report.window_end)
        week_long  = _fmt_week_long(report.window_start, report.window_end)

        lines = [
            f"Amazon Weekly Trip Report — {report.driver_name}",
            f"Week of {week_short}",
            f"({week_long})",
            '',
            f"  Total trips  : {report.trip_count}",
            f"  Total revenue: ${report.total_revenue:,.2f}",
            '',
            'The full trip detail is attached as a PDF.',
            '',
            '—',
            'BCAT Command Center  |  Automated Weekly Finance Report',
            f'Generated {datetime.utcnow():%Y-%m-%d %H:%M} UTC',
        ]
        return '\n'.join(lines)

    def _get_service(self):
        if self._svc is None:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
            from email_service import EmailService
            self._svc = EmailService()
        return self._svc
