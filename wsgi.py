"""
wsgi.py — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app -c gunicorn.conf.py
"""
import threading
from dashboard import app, _start_discord_bot, _start_telegram_bot  # noqa: F401
import config

# Start bots once when gunicorn loads this module (production only)
threading.Thread(target=_start_discord_bot, daemon=True, name='discord-bot').start()
threading.Thread(target=_start_telegram_bot, daemon=True, name='telegram-bot').start()

# Create DB tables and seed admin on startup (production only)
if config.DATABASE_URL:
    with app.app_context():
        try:
            from extensions import db
            import models  # noqa: F401 — ensures all models are registered before create_all
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
