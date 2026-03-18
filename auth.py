"""
auth.py — Login verification and route-protection decorator.
Uses werkzeug.security (bundled with Flask) for bcrypt-style password hashing.
"""
import functools
import config
from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import check_password_hash


def login_required(f):
    """Decorator that redirects unauthenticated browser requests to /login
    and returns 401 JSON for unauthenticated API requests."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            if _is_api_request():
                return jsonify({'error': 'Unauthorized', 'login_url': '/login'}), 401
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def verify_credentials(email: str, password: str) -> bool:
    """Return True if the provided email+password match the configured admin credentials."""
    stored_email = (config.ADMIN_EMAIL or '').strip().lower()
    stored_hash  = (config.ADMIN_PASSWORD_HASH or '').strip()

    if not stored_email or not stored_hash:
        return False

    return (
        email.strip().lower() == stored_email
        and check_password_hash(stored_hash, password)
    )


def _is_api_request() -> bool:
    return request.path.startswith('/api/') or request.is_json
