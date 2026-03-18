import json
import os
from datetime import datetime, timezone
from threading import Lock

_registry = {}
_lock = Lock()
_PERSISTENCE_PATH = os.path.join(os.path.dirname(__file__), "agent_registry.json")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_persisted():
    if os.path.exists(_PERSISTENCE_PATH):
        try:
            with open(_PERSISTENCE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save():
    try:
        with open(_PERSISTENCE_PATH, "w") as f:
            json.dump(_registry, f, indent=2, default=str)
    except Exception:
        pass


# Restore persisted state on import
_registry = _load_persisted()


def register(name, description=""):
    """Register an agent. Safe to call multiple times — updates heartbeat, preserves history."""
    with _lock:
        existing = _registry.get(name, {})
        _registry[name] = {
            "name": name,
            "description": description,
            "status": "idle",
            "last_task": existing.get("last_task"),
            "last_heartbeat": _now(),
            "registered_at": existing.get("registered_at") or _now(),
        }
        _save()


def heartbeat(name):
    """Update last_heartbeat without changing status."""
    with _lock:
        if name in _registry:
            _registry[name]["last_heartbeat"] = _now()
            _save()


def set_status(name, status, last_task=None):
    """Update status and optionally last_task. Also bumps last_heartbeat."""
    with _lock:
        if name in _registry:
            _registry[name]["status"] = status
            _registry[name]["last_heartbeat"] = _now()
            if last_task is not None:
                _registry[name]["last_task"] = last_task
            _save()


def get_all():
    """Return all registered agents as a list of dicts."""
    with _lock:
        return list(_registry.values())
