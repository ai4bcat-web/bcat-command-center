#!/bin/bash
# start_report_cron.sh — Railway cron startup wrapper for the weekly trip report.
#
# Reporting window: most recently completed Sunday–Saturday Amazon week.
# The job runs on Sunday morning; it reports on the week that just ended (Sat).
#
# Railway cron service settings:
#   Start command : bash start_report_cron.sh
#   Schedule      : 0 14 * * 0   (14:00 UTC = 8:00 AM CST / 9:00 AM CDT, Sundays only)
#
# To test a specific week without waiting for Sunday:
#   Set env var REPORT_WEEK_ENDING=YYYY-MM-DD (the Saturday end date)
#   and trigger a manual Railway deployment of this cron service.
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_TOKEN_JSON" ] && echo "$GMAIL_TOKEN_JSON" > token.json
[ -n "$GMAIL_CREDS_JSON" ] && echo "$GMAIL_CREDS_JSON" > credentials.json

echo "Weekly trip report cron starting..."
exec python report_cron.py
