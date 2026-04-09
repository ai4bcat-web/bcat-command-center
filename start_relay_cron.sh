#!/bin/bash
set -e

echo "Ensuring Playwright Chromium browser is installed..."
playwright install chromium --with-deps

echo "Running relay_cron..."
exec python relay_cron.py
