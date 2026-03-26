"""
wsgi.py — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app -c gunicorn.conf.py
"""
from dashboard import app  # noqa: F401
import config

# Create DB tables and seed admin on startup (production only)
if config.DATABASE_URL:
    with app.app_context():
        try:
            from extensions import db
            db.create_all()
            print("[startup] DB tables created/verified.", flush=True)
        except Exception as e:
            print(f"[startup] DB setup warning: {e}", flush=True)

        try:
            from cli import create_admin
            from click.testing import CliRunner
            result = CliRunner().invoke(create_admin)
            print(f"[startup] create-admin: {result.output.strip()}", flush=True)
        except Exception as e:
            print(f"[startup] Admin seed warning: {e}", flush=True)
