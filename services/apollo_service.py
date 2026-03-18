"""
Apollo.io Service Adapter
Pulls contacts, sequences, and analytics from Apollo.

Required env vars:
  APOLLO_API_KEY   — from Apollo Settings > Integrations > API Keys

Apollo API docs: https://apolloio.github.io/apollo-api-docs/
"""

import json, logging, os, urllib.request, urllib.parse
from datetime import datetime
log = logging.getLogger(__name__)

_BASE = 'https://api.apollo.io/v1'
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')

def _api_key(): return os.getenv('APOLLO_API_KEY', '')
def _is_configured(): return bool(_api_key())

def _headers():
    return {'X-Api-Key': _api_key(), 'Content-Type': 'application/json', 'Cache-Control': 'no-cache'}

def _post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(f'{_BASE}{path}', data=data, headers=_headers(), method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# ── Public API ────────────────────────────────────────────────────────────────

def search_contacts(
    workspace_id: str,
    titles: list[str] = None,
    industries: list[str] = None,
    locations: list[str] = None,
    company_sizes: list[str] = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """Search Apollo for contacts matching ICP criteria."""
    if not _is_configured():
        return {'ok': False, 'error': 'APOLLO_API_KEY not set', 'contacts': []}
    try:
        body = {
            'q_organization_industry_tag_ids': industries or [],
            'person_titles': titles or [],
            'person_locations': locations or [],
            'organization_num_employees_ranges': company_sizes or [],
            'page': page,
            'per_page': per_page,
        }
        result = _post('/mixed_people/search', body)
        contacts = result.get('people', [])
        _append_leads_cache(workspace_id, contacts)
        return {'ok': True, 'count': len(contacts), 'contacts': contacts,
                'pagination': result.get('pagination', {})}
    except Exception as e:
        log.exception('Apollo search failed')
        return {'ok': False, 'error': str(e), 'contacts': []}

def sync_sequences(workspace_id: str) -> dict:
    """Pull email sequence analytics from Apollo."""
    if not _is_configured():
        return {'ok': False, 'error': 'APOLLO_API_KEY not set', 'synced_at': None}
    try:
        result = _post('/email_accounts/search', {'page': 1, 'per_page': 50})
        payload = {
            'synced_at': datetime.utcnow().isoformat() + 'Z',
            'workspace_id': workspace_id,
            'accounts': result.get('email_accounts', []),
        }
        _write_cache(workspace_id, 'apollo_sequences', payload)
        return {'ok': True, 'accounts': len(payload['accounts']), 'synced_at': payload['synced_at']}
    except Exception as e:
        log.exception('Apollo sequence sync failed')
        return {'ok': False, 'error': str(e), 'synced_at': None}

def enrich_contact(email: str) -> dict:
    """Enrich a single contact with Apollo data."""
    if not _is_configured():
        return {'ok': False, 'error': 'Not configured'}
    try:
        result = _post('/people/match', {'email': email, 'reveal_personal_emails': True})
        return {'ok': True, 'person': result.get('person', {})}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def get_sync_status(workspace_id: str) -> dict:
    data = _read_cache(workspace_id, 'apollo_leads')
    return {'configured': _is_configured(), 'synced_at': data.get('synced_at'),
            'leads_cached': len(data.get('contacts', []))}

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
def _append_leads_cache(ws, contacts):
    data = _read_cache(ws, 'apollo_leads')
    existing = data.get('contacts', [])
    existing.extend(contacts)
    _write_cache(ws, 'apollo_leads', {
        'synced_at': datetime.utcnow().isoformat() + 'Z',
        'workspace_id': ws, 'contacts': existing,
    })
