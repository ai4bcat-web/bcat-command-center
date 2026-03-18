#!/bin/bash
# check-env.sh — verify required environment variables are set
# Run in Replit Shell: bash scripts/check-env.sh

REQUIRED=(SECRET_KEY ADMIN_EMAIL ADMIN_PASSWORD_HASH NODE_ENV)
OPTIONAL=(DISCORD_BOT_TOKEN TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY APP_BASE_URL COOKIE_DOMAIN)

echo "=== Required ==="
ALL_OK=true
for key in "${REQUIRED[@]}"; do
  if [ -n "${!key}" ]; then
    echo "  ✅  $key"
  else
    echo "  ❌  $key — MISSING"
    ALL_OK=false
  fi
done

echo ""
echo "=== Optional ==="
for key in "${OPTIONAL[@]}"; do
  if [ -n "${!key}" ]; then
    echo "  ✅  $key"
  else
    echo "  --  $key (not set)"
  fi
done

echo ""
if $ALL_OK; then
  echo "All required env vars are set."
else
  echo "⚠️  Some required env vars are missing. Set them in Replit Secrets."
  exit 1
fi
