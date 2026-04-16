#!/bin/bash
set -e

echo "Writing Gmail credentials from env vars..."
[ -n "$GMAIL_TOKEN_JSON" ] && echo "$GMAIL_TOKEN_JSON" | base64 -d > token.json || true
[ -n "$GMAIL_CREDS_JSON" ] && echo "$GMAIL_CREDS_JSON" | base64 -d > credentials.json || true

echo "Running database migrations..."
flask db upgrade || echo "No migrations folder — skipping (schema managed by auto-migrate in dashboard.py)"

echo "Seeding admin user..."
flask create-admin || true

echo "Fixing DSP driver type classifications..."
flask fix-driver-types || true

echo "Starting Relay scheduler (8 AM / 8 PM Central)..."
python automation/amazon_relay/scheduler.py &

echo "Starting gunicorn..."
exec gunicorn wsgi:app -c gunicorn.conf.py
