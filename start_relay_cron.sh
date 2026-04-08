#!/bin/bash
set -e

echo "Installing Playwright browser (Chromium)..."
playwright install chromium --with-deps

echo "Running relay_cron..."
exec python relay_cron.py
