#!/bin/bash
set -e

echo "Running relay_cron..."
exec python relay_cron.py
