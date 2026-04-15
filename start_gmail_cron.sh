#!/bin/bash
# start_gmail_cron.sh — Railway cron startup wrapper for Gmail trip email ingestion.
#
# Railway cron service settings:
#   Start command : bash start_gmail_cron.sh
#   Schedule      : 0 * * * *   (every hour, year-round)
#
# Required env vars on the gmail_cron service:
#   GMAIL_READER_TOKEN_JSON   — base64-encoded gmail_reader_token.json
#   GMAIL_CREDS_JSON          — base64-encoded credentials.json
#   DATABASE_URL              — PostgreSQL connection string
#
# Optional:
#   SHEETS_SERVICE_ACCOUNT_JSON  — enables Google Sheets write
#   GMAIL_LOOKBACK_DAYS          — days of Gmail history to search (default: 7)
#   GMAIL_DRY_RUN                — "true" to parse without writing
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_READER_TOKEN_JSON" ] && echo "$GMAIL_READER_TOKEN_JSON" | base64 -d > gmail_reader_token.json || true
[ -n "$GMAIL_CREDS_JSON" ]        && echo "$GMAIL_CREDS_JSON"        | base64 -d > credentials.json       || true

echo "Gmail trip email ingestor starting..."
exec python gmail_cron.py
