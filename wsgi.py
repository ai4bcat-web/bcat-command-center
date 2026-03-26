"""
wsgi.py — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app -c gunicorn.conf.py
"""
from dashboard import app  # noqa: F401
import config

# Run DB migrations and admin seed on startup (production only)
if config.DATABASE_URL:
    with app.app_context():
        try:
            from flask_migrate import upgrade
            upgrade()
            print("[startup] DB migrations applied.", flush=True)
        except Exception as e:
            print(f"[startup] Migration warning: {e}", flush=True)

        try:
            from cli import create_admin
            from click.testing import CliRunner
            result = CliRunner().invoke(create_admin)
            print(f"[startup] create-admin: {result.output.strip()}", flush=True)
        except Exception as e:
            print(f"[startup] Admin seed warning: {e}", flush=True)
