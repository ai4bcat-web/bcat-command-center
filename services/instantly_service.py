"""
Instantly.ai Service Adapter
Syncs campaign metrics, sequence performance, and lead status from Instantly.

Required env vars:
  INSTANTLY_API_KEY   — from Instantly Settings > API
  INSTANTLY_ORG_ID    — optional; needed if multi-org

Instantly API docs: https://developer.instantly.ai/
"""

import json, logging, os, urllib.request, urllib.parse
from datetime import datetime
log = logging.getLogger(__name__)

_BASE = 'https://api.instantly.ai/api/v2'
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')

def _api_key(): return os.getenv('INSTANTLY_API_KEY', '')
def _is_configured(): return bool(_api_key())

def _headers():
    return {'Authorization': f'Bearer {_api_key()}', 'Content-Type': 'application/json'}

def _get(path, params=None):
    url = f'{_BASE}{path}'
    if params: url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def _post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(f'{_BASE}{path}', data=data, headers=_headers(), method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# ── Public API ────────────────────────────────────────────────────────────────

def sync(workspace_id: str) -> dict:
    if not _is_configured():
        return {'ok': False, 'error': 'INSTANTLY_API_KEY not set in .env', 'synced_at': None}
    try:
        campaigns = _get('/campaigns', {'limit': 100})
        analytics = {}
        for c in (campaigns.get('items') or []):
            try:
                analytics[c['id']] = _get(f'/campaigns/{c["id"]}/analytics/overview')
            except Exception: pass

        payload = {
            'synced_at': datetime.utcnow().isoformat() + 'Z',
            'workspace_id': workspace_id,
            'campaigns': campaigns.get('items', []),
            'analytics': analytics,
        }
        _write_cache(workspace_id, 'instantly', payload)
        return {'ok': True, 'campaigns': len(payload['campaigns']), 'synced_at': payload['synced_at']}
    except Exception as e:
        log.exception('Instantly sync failed')
        return {'ok': False, 'error': str(e), 'synced_at': None}

def get_campaigns(workspace_id: str) -> list:
    return _read_cache(workspace_id, 'instantly').get('campaigns', [])

def get_analytics(workspace_id: str) -> dict:
    return _read_cache(workspace_id, 'instantly').get('analytics', {})

def get_sync_status(workspace_id: str) -> dict:
    data = _read_cache(workspace_id, 'instantly')
    return {'configured': _is_configured(), 'synced_at': data.get('synced_at'),
            'campaigns_cached': len(data.get('campaigns', []))}

# Instantly write-back: enroll leads into a campaign
def enroll_leads(campaign_id: str, emails: list[str]) -> dict:
    if not _is_configured():
        return {'ok': False, 'error': 'Not configured', 'mode': 'staged'}
    try:
        result = _post(f'/campaigns/{campaign_id}/leads', {'leads': [{'email': e} for e in emails]})
        return {'ok': True, 'enrolled': len(emails), 'result': result}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

# ── Cache ─────────────────────────────────────────────────────────────────────
def _cache_path(ws, name): return os.path.abspath(os.path.join(_CACHE_DIR, ws, f'{name}.json'))
def _read_cache(ws, name):
    p = _cache_path(ws, name)
    if not os.path.exists(p): return {}
    try:
        with open(p) as f: return json.load(f)
    except Exception: return {}
def _write_cache(ws, name, data):
    p = _cache_path(ws, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f: json.dump(data, f, indent=2)
