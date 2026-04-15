#!/bin/bash
# start_relay_sheets_cron.sh — Railway cron startup wrapper for Relay → Sheets sync.
#
# Railway cron service settings:
#   Start command : bash start_relay_sheets_cron.sh
#   Schedule      : 0 14,19,1 * * *   (8 AM / 1 PM / 7 PM CST)
#
# Required env vars on the relay_sheets_cron service:
#   DATABASE_URL          — PostgreSQL connection string
#   SHEETS_TOKEN_JSON     — base64-encoded sheets_token.json (user OAuth, Sheets+Drive scopes)
#   GMAIL_CREDS_JSON      — base64-encoded credentials.json (OAuth client secrets)
#
# Optional:
#   SHEETS_FOLDER_ID      — Drive folder ID for driver sheets
#   RELAY_SHEETS_DRY_RUN  — "true" to log without writing
set -e

echo "Writing Sheets OAuth credentials from env vars..."
[ -n "$SHEETS_TOKEN_JSON" ] && echo "$SHEETS_TOKEN_JSON" | base64 -d > sheets_token.json || true
[ -n "$GMAIL_CREDS_JSON"  ] && echo "$GMAIL_CREDS_JSON"  | base64 -d > credentials.json  || true

echo "Relay sheets sync starting..."
exec python relay_sheets_cron.py
