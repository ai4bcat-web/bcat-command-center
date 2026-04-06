#!/bin/bash
set -e

echo "Running database migrations..."
flask db upgrade || echo "No migrations folder — skipping (schema managed by auto-migrate in dashboard.py)"

echo "Seeding admin user..."
flask create-admin || true

echo "Starting gunicorn..."
exec gunicorn wsgi:app -c gunicorn.conf.py
