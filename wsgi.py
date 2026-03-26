"""
wsgi.py — WSGI entry point for Gunicorn.
Usage: gunicorn wsgi:app -c gunicorn.conf.py
"""
from dashboard import app  # noqa: F401
