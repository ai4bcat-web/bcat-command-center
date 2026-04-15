#!/bin/bash
# start_relay_sheets_cron.sh — Railway cron startup wrapper for Relay → Sheets sync.
#
# Railway cron service settings:
#   Start command : bash start_relay_sheets_cron.sh
#   Schedule      : 0 14,19,1 * * *   (8 AM / 1 PM / 7 PM CST)
#
# Required env vars on the relay_sheets_cron service:
#   DATABASE_URL                    — PostgreSQL connection string
#   SHEETS_SERVICE_ACCOUNT_JSON     — base64-encoded service account JSON
#
# Optional:
#   SHEETS_SHARE_EMAIL              — share created sheets with this email
#   SHEETS_FOLDER_ID                — Drive folder ID for driver sheets
#   RELAY_SHEETS_DRY_RUN            — "true" to log without writing
set -e

echo "Writing Sheets service account credentials from env vars..."
[ -n "$SHEETS_SERVICE_ACCOUNT_JSON" ] && echo "$SHEETS_SERVICE_ACCOUNT_JSON" | base64 -d > sheets_service_account.json || true

echo "Relay sheets sync starting..."
exec python relay_sheets_cron.py
