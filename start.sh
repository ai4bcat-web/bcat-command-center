#!/bin/bash
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_TOKEN_JSON" ] && echo "$GMAIL_TOKEN_JSON" > token.json
[ -n "$GMAIL_CREDS_JSON" ] && echo "$GMAIL_CREDS_JSON" > credentials.json

echo "Running database migrations..."
flask db upgrade || echo "No migrations folder — skipping (schema managed by auto-migrate in dashboard.py)"

echo "Seeding admin user..."
flask create-admin || true

echo "Installing Playwright browser (Chromium)..."
playwright install chromium --with-deps || true

echo "Starting gunicorn..."
exec gunicorn wsgi:app -c gunicorn.conf.py
