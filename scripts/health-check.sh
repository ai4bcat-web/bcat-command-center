#!/bin/bash
# health-check.sh — ping the live app health endpoint and pretty-print the result
# Usage: ./scripts/health-check.sh [optional-url]

URL="${1:-https://app.tryaiden.ai/api/health}"

echo "Checking: $URL"
echo "---"

if command -v curl &>/dev/null; then
  curl -s "$URL" | python3 -m json.tool 2>/dev/null || curl -s "$URL"
else
  echo "curl not found. Install curl and try again."
  exit 1
fi
