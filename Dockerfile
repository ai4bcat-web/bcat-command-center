# Dockerfile — BCAT Command Center
#
# Builds a single image used by both the web dashboard service and the
# relay_cron service. Playwright + Chromium are baked in at build time
# so the relay_cron container starts in seconds, not 2+ minutes.
#
# Railway uses the start command configured per-service:
#   Web dashboard  : gunicorn wsgi:app -c gunicorn.conf.py  (via start.sh)
#   Relay cron     : bash start_relay_cron.sh

FROM python:3.11-slim-bookworm

# ── System dependencies ───────────────────────────────────────────────────────
# Install all packages that Playwright/Chromium needs. Doing this in one layer
# here means it is committed to the image and never re-downloaded at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core Chromium runtime libraries
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 \
    libxcb1 libxkbcommon0 libx11-6 libxcomposite1 libxdamage1 \
    libxext6 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    # Additional libs for headless shell
    libx11-xcb1 libxcb-dri3-0 libxcb-dri2-0 \
    libxcb-glx0 libxcb-present0 libxcb-randr0 \
    libxcb-render0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 \
    libgl1 libglapi-mesa libglvnd0 libglx0 libglx-mesa0 \
    libglib2.0-0 libharfbuzz0b libfontconfig1 libfreetype6 \
    fonts-liberation fonts-freefont-ttf \
    # Needed for flask db, process management
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Playwright Chromium browser ───────────────────────────────────────────────
# Install ONLY the browser binary (system deps already above via apt).
# This downloads ~120MB once and bakes it into the image.
RUN playwright install chromium

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

EXPOSE 8000
