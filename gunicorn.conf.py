"""
gunicorn.conf.py — Production Gunicorn configuration for Railway.
"""
import os

# Bind to Railway's injected PORT
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# 2 workers is right for Railway's free tier (512MB RAM).
# Increase to 4 on a paid plan.
workers    = 2
threads    = 2
worker_class = 'sync'

# Allow long-running CSV import requests
timeout = 120

# Load app before forking — prevents duplicate bot threads
preload_app = True

# Log to stdout (Railway captures it)
accesslog = '-'
errorlog  = '-'
loglevel  = 'info'

# Graceful shutdown
graceful_timeout = 30
