#!/bin/bash
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_TOKEN_JSON" ] && echo "$GMAIL_TOKEN_JSON" | base64 -d > token.json
[ -n "$GMAIL_CREDS_JSON" ] && echo "$GMAIL_CREDS_JSON" | base64 -d > credentials.json

echo "Running database migrations..."
flask db upgrade || echo "No migrations folder — skipping (schema managed by auto-migrate in dashboard.py)"

echo "Seeding admin user..."
flask create-admin || true

echo "Fixing DSP driver type classifications..."
flask fix-driver-types || true

echo "Starting gunicorn..."
exec gunicorn wsgi:app -c gunicorn.conf.py
