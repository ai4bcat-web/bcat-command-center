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
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


def _webhook_url() -> str:
    return (
        os.getenv('REPORT_DISCORD_WEBHOOK_URL', '').strip()
        or os.getenv('DISCORD_WEBHOOK_URL', '').strip()
    )


def _fmt_week(window_start: str, window_end: str) -> tuple[str, bool]:
    """Return ("Sun Apr 5 – Sat Apr 11, 2026", is_wtd) tuple."""
    try:
        s        = datetime.strptime(window_start, '%Y-%m-%d')
        e        = datetime.strptime(window_end,   '%Y-%m-%d')
        saturday = s + timedelta(days=6)
        is_wtd   = e < saturday
        label = f"{s.strftime('%a %b %-d')} – {saturday.strftime('%a %b %-d, %Y')}"
        return label, is_wtd
    except ValueError:
        return f"{window_start} – {window_end}", False


class DiscordReportNotifier:
    """Posts per-driver report status to a Discord webhook."""

    def notify_success(self, report, dry_run: bool = False) -> None:
        """Post a success message after a driver report email is sent."""
        week, is_wtd = _fmt_week(report.window_start, report.window_end)
        dtype = 'Owner Operator' if report.driver_type == 'owner_op' else 'Company Driver'

        try:
            e = datetime.strptime(report.window_end, '%Y-%m-%d')
            through_line = f"\n**Week-to-Date Through:** {e.strftime('%b %-d, %Y')}" if is_wtd else ''
        except ValueError:
            through_line = ''

        msg = (
            f"✅ **Driver Report Sent**\n"
            f"**Driver:** {report.driver_name}  ·  {dtype}\n"
            f"**Reporting Week:** {week}{through_line}\n"
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
        """Post a failure message when a step errors out."""
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
        window_start:  str,
        window_end:    str,
        driver_count:  int,
        total_trips:   int,
        total_revenue: float,
        failed_count:  int,
        dry_run:       bool = False,
    ) -> None:
        """Post a job-level summary after all driver reports are processed."""
        status  = '✅' if failed_count == 0 else '⚠️'
        dry_tag = '  *(DRY RUN)*' if dry_run else ''
        week, is_wtd = _fmt_week(window_start, window_end)

        try:
            e = datetime.strptime(window_end, '%Y-%m-%d')
            through_line = f"\n**Week-to-Date Through:** {e.strftime('%b %-d, %Y')}" if is_wtd else ''
        except ValueError:
            through_line = ''

        msg = (
            f"{status} **Weekly Trip Report Complete**{dry_tag}\n"
            f"**Reporting Week:** {week}{through_line}\n"
            f"**Drivers reported:** {driver_count}  |  "
            f"**Trips:** {total_trips}  |  "
            f"**Total revenue:** ${total_revenue:,.2f}\n"
            + (f"⚠️ {failed_count} driver report(s) failed — check logs." if failed_count else '')
        )
        self._post(msg, dry_run)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _post(self, content: str, dry_run: bool, is_error: bool = False) -> None:
        """Post to Discord. Always fires — dry_run adds a label but does NOT suppress."""
        url = _webhook_url()
        if not url:
            log.warning(
                "DISCORD_WEBHOOK_URL / REPORT_DISCORD_WEBHOOK_URL not set — "
                "notification skipped. Set one of these env vars to enable Discord alerts."
            )
            return

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
            log.error("Discord POST failed: %s", exc)
