#!/bin/bash
set -e

echo "Running database migrations..."
flask db upgrade

echo "Seeding admin user..."
flask create-admin || true

echo "Starting gunicorn..."
exec gunicorn wsgi:app -c gunicorn.conf.py
