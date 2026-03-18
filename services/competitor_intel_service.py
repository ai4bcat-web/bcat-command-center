"""
Competitor Ad Intelligence Service — Best Care Auto Transport

Fetches real competitor data from DataForSEO (primary) or SerpAPI (secondary).
Falls back to cached data if APIs are unavailable or unconfigured.

Focuses on:
  - Google Ads competitor ads (Google Ads Transparency / paid SERP)
  - Competitor keyword patterns
  - Competitor messaging themes
  - Location/geo targeting signals
  - Offer and CTA patterns

Required environment variables (see .env.example):
  DATAFORSEO_LOGIN      — DataForSEO account email
  DATAFORSEO_PASSWORD   — DataForSEO API password
  SERPAPI_KEY           — SerpAPI API key (alternative/fallback)
  BEST_CARE_COMPETITOR_DOMAINS — comma-separated list of competitor domains

DataForSEO docs:
  https://docs.dataforseo.com/v3/serp/google/ads/live/
  https://docs.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live/
"""

import base64
import json
import logging
import os
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'competitor_intel.json'
)

# Default target keywords for auto transport competitor research
_DEFAULT_KEYWORDS = [
    'auto transport', 'car shipping', 'vehicle transport',
    'car transport service', 'auto shipping quotes',
    'enclosed car transport', 'open car transport',
    'door to door car shipping', 'auto transport near me',
]

_DEFAULT_COMPETITOR_DOMAINS = [
    'montway.com', 'uship.com', 'amerifreight.net',
    'sgautocarriers.com', 'nextruckaway.com',
]


# ── Config ────────────────────────────────────────────────────────────────────

def _dataforseo_creds() -> tuple[str, str]:
    login    = os.getenv('DATAFORSEO_LOGIN', '')
    password = os.getenv('DATAFORSEO_PASSWORD', '')
    return login, password

def _serpapi_key() -> str:
    return os.getenv('SERPAPI_KEY', '')

def _competitor_domains() -> list[str]:
    env = os.getenv('BEST_CARE_COMPETITOR_DOMAINS', '')
    return [d.strip() for d in env.split(',') if d.strip()] or _DEFAULT_COMPETITOR_DOMAINS

def _target_keywords() -> list[str]:
    env = os.getenv('BEST_CARE_TARGET_KEYWORDS', '')
    return [k.strip() for k in env.split(',') if k.strip()] or _DEFAULT_KEYWORDS

def _is_dataforseo_configured() -> bool:
    login, pw = _dataforseo_creds()
    return bool(login and pw)

def _is_serpapi_configured() -> bool:
    return bool(_serpapi_key())


# ── DataForSEO integration ────────────────────────────────────────────────────

def _dfs_auth_header() -> str:
    login, password = _dataforseo_creds()
    token = base64.b64encode(f'{login}:{password}'.encode()).decode()
    return f'Basic {token}'


def _dfs_post(endpoint: str, payload: list[dict]) -> dict:
    url  = f'https://api.dataforseo.com/v3/{endpoint}'
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url,
        data=body,
        headers={
            'Authorization': _dfs_auth_header(),
            'Content-Type':  'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _fetch_google_ads_serp(keyword: str, location_code: int = 2840) -> list[dict]:
    """
    Fetch Google paid ads for a keyword via DataForSEO SERP/Google/Ads.
    location_code 2840 = United States
    """
    result = _dfs_post('serp/google/ads/live/regular', [{
        'keyword':       keyword,
        'location_code': location_code,
        'language_code': 'en',
        'device':        'desktop',
        'os':            'windows',
    }])

    ads = []
    for task in result.get('tasks', []):
        for res in (task.get('result') or []):
            for item in (res.get('items') or []):
                if item.get('type') not in ('paid', 'paid_advanced'):
                    continue
                ads.append({
                    'keyword':      keyword,
                    'domain':       item.get('domain', ''),
                    'title':        item.get('title', ''),
                    'description':  item.get('description', ''),
                    'url':          item.get('url', ''),
                    'position':     item.get('rank_absolute', 0),
                    'extensions':   item.get('extra_links') or [],
                })
    return ads


def _fetch_competitor_keywords(domain: str) -> list[dict]:
    """
    Fetch top paid keywords for a competitor domain via DataForSEO Labs.
    """
    result = _dfs_post('dataforseo_labs/google/ranked_keywords/live', [{
        'target':          domain,
        'location_code':   2840,
        'language_code':   'en',
        'limit':           50,
        'filters':         [['paid_serp_info.count', '>', 0]],
        'order_by':        ['paid_serp_info.count,desc'],
    }])

    keywords = []
    for task in result.get('tasks', []):
        for res in (task.get('result') or []):
            for item in (res.get('items') or []):
                si = item.get('paid_serp_info', {})
                keywords.append({
                    'domain':         domain,
                    'keyword':        item.get('keyword', {}).get('keyword', ''),
                    'search_volume':  item.get('keyword', {}).get('search_volume', 0),
                    'cpc':            item.get('keyword', {}).get('cpc', 0),
                    'competition':    item.get('keyword', {}).get('competition', 0),
                    'avg_position':   si.get('avg_position', 0),
                    'serp_count':     si.get('count', 0),
                })
    return keywords


# ── SerpAPI fallback ──────────────────────────────────────────────────────────

def _fetch_serp_ads_via_serpapi(keyword: str) -> list[dict]:
    key = _serpapi_key()
    params = urllib.parse.urlencode({
        'q':             keyword,
        'api_key':       key,
        'engine':        'google',
        'gl':            'us',
        'hl':            'en',
        'google_domain': 'google.com',
        'num':           10,
    })
    url = f'https://serpapi.com/search?{params}'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    ads = []
    for item in data.get('ads', []):
        ads.append({
            'keyword':     keyword,
            'domain':      item.get('displayed_link', ''),
            'title':       item.get('title', ''),
            'description': item.get('description', ''),
            'url':         item.get('link', ''),
            'position':    item.get('block_position', 0),
            'extensions':  item.get('sitelinks', []),
        })
    return ads


# ── Analysis helpers ──────────────────────────────────────────────────────────

def _extract_themes(ads: list[dict]) -> list[dict]:
    """
    Identify recurring messaging themes from competitor ad copy.
    Simple frequency-based pattern detection — no ML required.
    """
    theme_signals = {
        'price/quote':     ['quote', 'price', 'free', 'instant', 'cost', 'rate', '$'],
        'speed':           ['fast', 'quick', 'same day', '24h', 'express', 'rapid'],
        'trust/safety':    ['safe', 'insured', 'bonded', 'licensed', 'trusted', 'guaranteed'],
        'enclosed':        ['enclosed', 'premium', 'white glove', 'luxury', 'exotic'],
        'door-to-door':    ['door to door', 'door-to-door', 'pickup', 'delivered'],
        'nationwide':      ['nationwide', 'national', 'all states', 'coast to coast', 'anywhere'],
        'rating/reviews':  ['rated', 'reviews', 'stars', 'trusted', 'bbb', 'accredited'],
        'no upfront':      ['no deposit', 'no upfront', 'pay on delivery', 'no hidden'],
    }

    theme_counts: dict[str, int] = {t: 0 for t in theme_signals}
    for ad in ads:
        text = (ad.get('title', '') + ' ' + ad.get('description', '')).lower()
        for theme, signals in theme_signals.items():
            if any(s in text for s in signals):
                theme_counts[theme] += 1

    total = len(ads) or 1
    return sorted([
        {'theme': t, 'count': c, 'prevalence_pct': round(c / total * 100)}
        for t, c in theme_counts.items() if c > 0
    ], key=lambda x: -x['count'])


def _extract_offers(ads: list[dict]) -> list[str]:
    """Extract distinct offer/CTA patterns from ads."""
    offers = set()
    offer_signals = [
        'free quote', 'instant quote', 'get a quote', 'free estimate',
        'book now', 'save', 'off', 'discount', 'promo', 'deal',
        'no deposit', 'pay on delivery',
    ]
    for ad in ads:
        text = (ad.get('title', '') + ' ' + ad.get('description', '')).lower()
        for sig in offer_signals:
            if sig in text:
                offers.add(sig.title())
    return sorted(offers)


def _summarize_competitors(competitor_ads: list[dict], kw_data: list[dict]) -> list[dict]:
    """Build per-competitor summary cards."""
    by_domain: dict[str, dict] = {}

    for ad in competitor_ads:
        d = ad['domain']
        if d not in by_domain:
            by_domain[d] = {
                'domain':     d,
                'ad_count':   0,
                'ads':        [],
                'keywords':   [],
                'themes':     [],
                'offers':     [],
                'avg_pos':    [],
            }
        by_domain[d]['ad_count']  += 1
        by_domain[d]['ads'].append(ad)
        by_domain[d]['avg_pos'].append(ad.get('position', 0))

    for kw in kw_data:
        d = kw['domain']
        if d in by_domain:
            by_domain[d]['keywords'].append(kw['keyword'])

    result = []
    for d, data in by_domain.items():
        data['themes']   = _extract_themes(data['ads'])
        data['offers']   = _extract_offers(data['ads'])
        data['avg_position'] = round(
            sum(data['avg_pos']) / len(data['avg_pos']), 1
        ) if data['avg_pos'] else 0
        del data['avg_pos']
        result.append(data)

    return sorted(result, key=lambda x: x['ad_count'], reverse=True)


# ── Public API ────────────────────────────────────────────────────────────────

def sync() -> dict[str, Any]:
    """
    Fetch competitor intelligence from best available source.
    Priority: DataForSEO → SerpAPI → error
    """
    keywords  = _target_keywords()
    domains   = _competitor_domains()
    all_ads   = []
    all_kws   = []
    source    = None

    if _is_dataforseo_configured():
        source = 'dataforseo'
        try:
            for kw in keywords[:5]:   # limit API calls; expand as budget allows
                all_ads.extend(_fetch_google_ads_serp(kw))
            for domain in domains:
                all_kws.extend(_fetch_competitor_keywords(domain))
        except Exception as exc:
            return {'ok': False, 'error': f'DataForSEO error: {exc}', 'synced_at': None}

    elif _is_serpapi_configured():
        source = 'serpapi'
        try:
            for kw in keywords[:5]:
                all_ads.extend(_fetch_serp_ads_via_serpapi(kw))
        except Exception as exc:
            return {'ok': False, 'error': f'SerpAPI error: {exc}', 'synced_at': None}

    else:
        return {
            'ok': False,
            'error': 'No competitor intelligence API configured. '
                     'Set DATAFORSEO_LOGIN + DATAFORSEO_PASSWORD '
                     'or SERPAPI_KEY in .env',
            'synced_at': None,
        }

    summaries = _summarize_competitors(all_ads, all_kws)
    themes    = _extract_themes(all_ads)
    offers    = _extract_offers(all_ads)

    payload = {
        'synced_at':   datetime.utcnow().isoformat() + 'Z',
        'source':      source,
        'keywords_searched': keywords[:5],
        'competitors': summaries,
        'global_themes': themes,
        'global_offers': offers,
        'raw_ads':     all_ads,
    }
    _write_cache(payload)
    return {
        'ok':         True,
        'source':     source,
        'ads_found':  len(all_ads),
        'competitors': len(summaries),
        'synced_at':  payload['synced_at'],
    }


def get_competitor_summary() -> list[dict]:
    data = _read_cache()
    return data.get('competitors', [])


def get_global_themes() -> list[dict]:
    data = _read_cache()
    return data.get('global_themes', [])


def get_global_offers() -> list[str]:
    data = _read_cache()
    return data.get('global_offers', [])


def get_sync_status() -> dict:
    data = _read_cache()
    return {
        'configured':       _is_dataforseo_configured() or _is_serpapi_configured(),
        'source':           data.get('source'),
        'synced_at':        data.get('synced_at'),
        'competitors_cached': len(data.get('competitors', [])),
        'dataforseo_ready': _is_dataforseo_configured(),
        'serpapi_ready':    _is_serpapi_configured(),
    }


def get_all() -> dict:
    return _read_cache()


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _read_cache() -> dict:
    if not os.path.exists(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, 'w') as f:
        json.dump(data, f, indent=2)
