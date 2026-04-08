"""
automation/trip_report/email_sender.py
───────────────────────────────────────
ReportEmailSender

Sends a driver trip-report PDF as an email attachment via the existing
EmailService (Gmail API + OAuth2).

Configuration (env vars)
────────────────────────
  REPORT_RECIPIENT_EMAIL  — destination address (required)
  GMAIL_TOKEN_PATH        — path to token.json  (default: token.json)
  GMAIL_CREDS_PATH        — path to credentials.json (default: credentials.json)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)


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
        subject = (
            f"Amazon Trip Report – {report.driver_name} – {report.report_date}"
        )
        body = self._build_body(report)
        attachment_name = f"trip_report_{report.driver_name.replace(' ', '_')}_{report.report_date}.pdf"

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
            "Email sent → %s | driver: %s | trips: %d | revenue: $%.2f",
            self._recipient, report.driver_name,
            report.trip_count, report.total_revenue,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_body(self, report) -> str:
        window = ''
        if report.window_start and report.window_end:
            window = f"{report.window_start} to {report.window_end}"
        else:
            window = report.report_date

        lines = [
            f"Driver Trip Report — {report.driver_name}",
            f"Reporting window: {window}",
            '',
            f"  Total trips  : {report.trip_count}",
            f"  Total revenue: ${report.total_revenue:,.2f}",
            '',
            'The full trip detail is attached as a PDF.',
            '',
            '—',
            'BCAT Command Center  |  Automated Finance Report',
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
