#!/bin/bash
# start_report_cron.sh — Railway cron startup wrapper for the daily trip report.
#
# Reporting window: Sunday of the current week through today (week-to-date).
# The job runs every morning after the nightly relay fetch (which runs at 04:00 UTC).
#
# Railway cron service settings:
#   Start command : bash start_report_cron.sh
#   Schedule      : 0 14 * * *   (14:00 UTC = 8:00 AM CST / 9:00 AM CDT, every day)
#
# Required env vars on the report_cron service:
#   REPORT_FORCE_RESEND=true   — resend even if already sent today (daily updates)
#
# To report on a specific week:
#   Set env var REPORT_WEEK_ENDING=YYYY-MM-DD (the Saturday end date)
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_TOKEN_JSON" ] && echo "$GMAIL_TOKEN_JSON" | base64 -d > token.json || true
[ -n "$GMAIL_CREDS_JSON" ] && echo "$GMAIL_CREDS_JSON" | base64 -d > credentials.json || true

echo "Weekly trip report cron starting..."
exec python report_cron.py
