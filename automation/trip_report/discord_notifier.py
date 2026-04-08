"""
automation/trip_report/discord_notifier.py
───────────────────────────────────────────
DiscordReportNotifier

Posts per-driver report status updates to a Discord webhook after each email
send attempt.  Uses stdlib urllib — no extra dependencies.

Configuration (env vars)
────────────────────────
  REPORT_DISCORD_WEBHOOK_URL — webhook URL for report notifications
                               Falls back to DISCORD_WEBHOOK_URL if not set.
                               If neither is set, notifications are silently skipped.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime

log = logging.getLogger(__name__)


def _webhook_url() -> str:
    return (
        os.getenv('REPORT_DISCORD_WEBHOOK_URL', '').strip()
        or os.getenv('DISCORD_WEBHOOK_URL', '').strip()
    )


class DiscordReportNotifier:
    """Posts per-driver report status to a Discord webhook."""

    def notify_success(self, report, dry_run: bool = False) -> None:
        """Post a success message after a driver report email is sent.

        Args:
            report:  DriverReport dataclass.
            dry_run: If True, log the message but do not POST to Discord.
        """
        window = self._window_str(report)
        dtype  = 'Owner Operator' if report.driver_type == 'owner_op' else 'Company Driver'

        msg = (
            f"✅ **Driver Report Sent**\n"
            f"**Driver:** {report.driver_name}  ·  {dtype}\n"
            f"**Period:** {window}\n"
            f"**Trips:** {report.trip_count}  |  "
            f"**Revenue:** ${report.total_revenue:,.2f}\n"
            f"📧 Email delivered to recipient."
        )
        self._post(msg, dry_run)

    def notify_failure(
        self,
        driver_name: str,
        step: str,
        error: str,
        dry_run: bool = False,
    ) -> None:
        """Post a failure message when a step errors out.

        Args:
            driver_name: Name of the driver being processed.
            step:        Which step failed (e.g. 'pdf', 'email', 'discord').
            error:       Short error summary (will be truncated to 500 chars).
            dry_run:     If True, log but do not POST.
        """
        short_err = str(error)[:500]
        msg = (
            f"⚠️ **Driver Report FAILED**\n"
            f"**Driver:** {driver_name}\n"
            f"**Failed step:** {step}\n"
            f"```\n{short_err}\n```"
        )
        self._post(msg, dry_run, is_error=True)

    def notify_job_complete(
        self,
        report_date: str,
        driver_count: int,
        total_trips: int,
        total_revenue: float,
        failed_count: int,
        dry_run: bool = False,
    ) -> None:
        """Post a job-level summary after all driver reports are processed."""
        status = '✅' if failed_count == 0 else '⚠️'
        dry_tag = '  *(DRY RUN)*' if dry_run else ''
        msg = (
            f"{status} **Daily Trip Report Complete**{dry_tag}\n"
            f"**Date:** {report_date}\n"
            f"**Drivers reported:** {driver_count}  |  "
            f"**Trips:** {total_trips}  |  "
            f"**Total revenue:** ${total_revenue:,.2f}\n"
            + (f"⚠️ {failed_count} driver report(s) failed — check logs." if failed_count else '')
        )
        self._post(msg, dry_run)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _window_str(self, report) -> str:
        if report.window_start and report.window_end:
            try:
                s = datetime.strptime(report.window_start, '%Y-%m-%d').strftime('%b %d')
                e = datetime.strptime(report.window_end,   '%Y-%m-%d').strftime('%b %d, %Y')
                return f"{s} – {e}"
            except ValueError:
                pass
        return report.report_date

    def _post(self, content: str, dry_run: bool, is_error: bool = False) -> None:
        url = _webhook_url()
        if not url:
            log.debug("No Discord webhook configured — skipping notification.")
            return

        if dry_run:
            log.info("[DRY RUN] Discord message:\n%s", content)
            return

        # Truncate to Discord's 2000-char limit with a safety margin
        if len(content) > 1950:
            content = content[:1947] + '...'

        try:
            body = json.dumps({'content': content}).encode()
            req  = urllib.request.Request(
                url,
                data    = body,
                headers = {'Content-Type': 'application/json'},
                method  = 'POST',
            )
            urllib.request.urlopen(req, timeout=10)
            log.info("Discord notification posted (%d chars).", len(content))
        except Exception as exc:
            # Non-fatal — log and continue
            log.warning("Discord POST failed: %s", exc)
