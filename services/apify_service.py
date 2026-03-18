"""
Apify Service Adapter
Runs Apify actors to scrape lead data (LinkedIn, Google Maps, company sites, etc.)
and imports results into the sales pipeline.

Required env vars:
  APIFY_API_TOKEN   — from Apify > Settings > Integrations

Apify API docs: https://docs.apify.com/api/v2
"""

import json, logging, os, urllib.request, urllib.parse
from datetime import datetime
log = logging.getLogger(__name__)

_BASE = 'https://api.apify.com/v2'
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')

# Preconfigured actor IDs for common scraping tasks
ACTORS = {
    'linkedin_search':    '2SyF0bVxmgGr8IVCZ',   # LinkedIn Profile Scraper
    'google_maps':        'nwua9Gu5YrADL7ZDj',   # Google Maps Scraper
    'apollo_export':      'oTgt7RPhHqbPDsBKa',   # Apollo.io Scraper
    'company_finder':     'apify~website-content-crawler',
}

def _token(): return os.getenv('APIFY_API_TOKEN', '')
def _is_configured(): return bool(_token())

def _headers():
    return {'Authorization': f'Bearer {_token()}', 'Content-Type': 'application/json'}

def _post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(f'{_BASE}{path}', data=data, headers=_headers(), method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def _get(path):
    req = urllib.request.Request(f'{_BASE}{path}', headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

# ── Public API ────────────────────────────────────────────────────────────────

def run_actor(actor_id: str, input_payload: dict, wait_secs: int = 60) -> dict:
    """Run an Apify actor and wait for results."""
    if not _is_configured():
        return {'ok': False, 'error': 'APIFY_API_TOKEN not set', 'items': []}
    try:
        run = _post(f'/acts/{actor_id}/runs', input_payload)
        run_id = run.get('data', {}).get('id')
        if not run_id:
            return {'ok': False, 'error': 'No run ID returned', 'items': []}
        # Poll for completion (simplified — in production use webhooks)
        import time
        for _ in range(wait_secs // 5):
            time.sleep(5)
            status = _get(f'/actor-runs/{run_id}')
            if status.get('data', {}).get('status') in ('SUCCEEDED', 'FAILED', 'ABORTED'):
                break
        dataset_id = status.get('data', {}).get('defaultDatasetId')
        if not dataset_id:
            return {'ok': False, 'error': 'No dataset ID', 'items': []}
        items_resp = _get(f'/datasets/{dataset_id}/items?limit=1000')
        return {'ok': True, 'run_id': run_id, 'items': items_resp.get('items', [])}
    except Exception as e:
        log.exception('Apify actor run failed')
        return {'ok': False, 'error': str(e), 'items': []}

def scrape_linkedin_contacts(workspace_id: str, search_url: str, max_items: int = 200) -> dict:
    """Scrape LinkedIn Sales Navigator search results."""
    result = run_actor(ACTORS['linkedin_search'], {
        'searchUrl': search_url,
        'maxItems':  max_items,
    })
    if result['ok']:
        _save_scraped_leads(workspace_id, 'linkedin', result['items'])
    return result

def scrape_google_maps(workspace_id: str, query: str, location: str, max_items: int = 100) -> dict:
    """Scrape businesses from Google Maps (e.g., car dealerships in Chicago)."""
    result = run_actor(ACTORS['google_maps'], {
        'searchStringsArray': [query],
        'locationQuery': location,
        'maxCrawledPlaces': max_items,
    })
    if result['ok']:
        normalized = [_normalize_maps_item(item) for item in result['items']]
        _save_scraped_leads(workspace_id, 'google_maps', normalized)
    return result

def _normalize_maps_item(item: dict) -> dict:
    """Normalize Google Maps result to lead format."""
    return {
        'company':    item.get('title', ''),
        'website':    item.get('website', ''),
        'phone':      item.get('phone', ''),
        'address':    item.get('address', ''),
        'category':   item.get('categoryName', ''),
        'rating':     item.get('totalScore'),
        'reviews':    item.get('reviewsCount'),
        'source':     'Apify/Google Maps',
    }

def get_scraped_leads(workspace_id: str, source: str = None) -> list:
    data = _read_cache(workspace_id, 'apify_leads')
    leads = data.get('leads', [])
    if source:
        leads = [l for l in leads if l.get('scrape_source') == source]
    return leads

def get_sync_status(workspace_id: str) -> dict:
    data = _read_cache(workspace_id, 'apify_leads')
    return {'configured': _is_configured(), 'leads_scraped': len(data.get('leads', [])),
            'last_run': data.get('last_run')}

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
def _save_scraped_leads(ws, source, items):
    data = _read_cache(ws, 'apify_leads')
    leads = data.get('leads', [])
    for item in items:
        item['scrape_source'] = source
        item['scraped_at'] = datetime.utcnow().isoformat() + 'Z'
        leads.append(item)
    _write_cache(ws, 'apify_leads', {
        'last_run': datetime.utcnow().isoformat() + 'Z',
        'workspace_id': ws, 'leads': leads,
    })
