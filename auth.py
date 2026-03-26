"""
auth.py — Authentication helpers and route-protection decorators.
Wraps Flask-Login so the rest of the app only needs to import from here.
"""
import functools
from flask import redirect, url_for, request, jsonify
from flask_login import current_user, login_required as _flask_login_required


def login_required(f):
    """
    Drop-in replacement for the old session-based decorator.
    Delegates to Flask-Login. API requests get 401 JSON;
    browser requests are redirected to /login.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            if _is_api_request():
                return jsonify({'error': 'Unauthorized', 'login_url': '/login'}), 401
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def require_permission(perm_name: str):
    """
    Decorator that enforces a named permission beyond just being logged in.
    Usage:  @require_permission('view_company_ivan')
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                if _is_api_request():
                    return jsonify({'error': 'Unauthorized'}), 401
                return redirect(url_for('login', next=request.path))
            if not current_user.has_permission(perm_name):
                if _is_api_request():
                    return jsonify({'error': 'Forbidden', 'required': perm_name}), 403
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """Shortcut decorator — requires the 'admin' role."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            if _is_api_request():
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login', next=request.path))
        if not current_user.is_admin:
            if _is_api_request():
                return jsonify({'error': 'Forbidden — admin only'}), 403
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def _is_api_request() -> bool:
    return request.path.startswith('/api/') or request.is_json
