"""
config.py — Environment-aware configuration for BCAT Command Center.
Loaded once at startup. All secrets and environment-specific values live here.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Environment detection ─────────────────────────────────────────────────────
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production' or os.environ.get('IS_PRODUCTION', '').lower() in ('true', '1', 'yes')

# ── Core Flask ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            'SECRET_KEY environment variable is required in production. '
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    SECRET_KEY = 'dev-insecure-secret-do-not-use-in-production'

DEBUG = not IS_PRODUCTION
PORT  = int(os.environ.get('PORT', 5050))
HOST  = os.environ.get('HOST', '0.0.0.0')

# ── Session / Cookie ─────────────────────────────────────────────────────────
SESSION_COOKIE_NAME     = 'bcat_session'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE   = IS_PRODUCTION          # HTTPS only in production
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_DOMAIN   = os.environ.get('COOKIE_DOMAIN', None)   # e.g. 'tryaiden.ai'
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# ── Auth credentials ──────────────────────────────────────────────────────────
# Store the hashed password in the env (not plaintext).
# Generate hash: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpass'))"
ADMIN_EMAIL         = os.environ.get('ADMIN_EMAIL', 'admin@tryaiden.ai')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')

# ── URLs ──────────────────────────────────────────────────────────────────────
APP_BASE_URL = os.environ.get('APP_BASE_URL', 'https://app.tryaiden.ai')

# ── CORS / allowed origins ────────────────────────────────────────────────────
# Comma-separated list of allowed origins for API calls (if CORS is needed).
_raw_origins = os.environ.get('ALLOWED_ORIGINS', APP_BASE_URL)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(',') if o.strip()]

# ── Database ──────────────────────────────────────────────────────────────────
# Railway injects DATABASE_URL automatically.
# For local dev use: postgresql://user:pass@localhost/bcat
_raw_db_url = os.environ.get('DATABASE_URL', '')
# Render/Railway may still use legacy 'postgres://' prefix — SQLAlchemy requires 'postgresql://'
DATABASE_URL = _raw_db_url.replace('postgres://', 'postgresql://', 1) if _raw_db_url else ''

SQLALCHEMY_TRACK_MODIFICATIONS = False

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Railway Redis add-on injects REDIS_URL. Falls back to in-memory for single-instance deploys.
REDIS_URL = os.environ.get('REDIS_URL', 'memory://')

# ── CSRF ──────────────────────────────────────────────────────────────────────
WTF_CSRF_ENABLED    = IS_PRODUCTION   # disabled in dev for easier API testing
WTF_CSRF_TIME_LIMIT = 3600            # 1 hour

# ── Admin seed credentials (used only by 'flask create-admin' CLI command) ────
# After the admin user is in the database these env vars are no longer needed for login.
SEED_ADMIN_EMAIL    = os.environ.get('SEED_ADMIN_EMAIL',    ADMIN_EMAIL)
SEED_ADMIN_PASSWORD = os.environ.get('SEED_ADMIN_PASSWORD', '')
SEED_ADMIN_NAME     = os.environ.get('SEED_ADMIN_NAME',     'Admin')
