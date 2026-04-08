#!/bin/bash
# start_report_cron.sh — Railway cron startup wrapper for the daily trip report.
#
# This script does NOT install Playwright because report_cron.py reads data
# from the PostgreSQL database (populated by relay_cron at 4 AM) rather than
# from the browser.  It's kept separate so that in future it could still be
# adapted if direct Amazon access is needed.
#
# Railway cron service settings:
#   Start command : bash start_report_cron.sh
#   Schedule      : 0 14 * * *  (8 AM CST / 9 AM CDT)
set -e

echo "Daily trip report cron starting..."
exec python report_cron.py
