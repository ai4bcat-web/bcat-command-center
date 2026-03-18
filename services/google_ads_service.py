"""
Google Ads Service — Best Care Auto Transport
Connects to the Google Ads API and syncs monthly campaign/keyword/search-term
performance data into data/best_care/google_ads_monthly.json.

Required environment variables (see .env.example):
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_LOGIN_CUSTOMER_ID   (MCC / manager account ID, no hyphens)
  BEST_CARE_GOOGLE_ADS_CUSTOMER_ID  (client account ID, no hyphens)

Install dependency:
  pip install google-ads
"""

import json
import logging
import os
from datetime import datetime, date
from typing import Any

log = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'google_ads_monthly.json'
)


# ── Config ────────────────────────────────────────────────────────────────────

def _cfg() -> dict:
    return {
        'developer_token':    os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN', ''),
        'client_id':          os.getenv('GOOGLE_ADS_CLIENT_ID', ''),
        'client_secret':      os.getenv('GOOGLE_ADS_CLIENT_SECRET', ''),
        'refresh_token':      os.getenv('GOOGLE_ADS_REFRESH_TOKEN', ''),
        'login_customer_id':  os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID', ''),
        'use_proto_plus':     True,
    }

def _customer_id() -> str:
    return os.getenv('BEST_CARE_GOOGLE_ADS_CUSTOMER_ID', '')

def _is_configured() -> bool:
    c = _cfg()
    return all([
        c['developer_token'], c['client_id'], c['client_secret'],
        c['refresh_token'], _customer_id()
    ])


# ── GAQL Queries ──────────────────────────────────────────────────────────────

_CAMPAIGN_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  segments.month,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.conversions_value,
  metrics.ctr,
  metrics.average_cpc,
  metrics.average_cpm,
  metrics.all_conversions,
  metrics.cost_per_conversion
FROM campaign
WHERE segments.date DURING LAST_12_MONTHS
  AND campaign.status != 'REMOVED'
ORDER BY segments.month DESC, metrics.cost_micros DESC
"""

_KEYWORD_QUERY = """
SELECT
  campaign.name,
  ad_group.name,
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  ad_group_criterion.quality_info.quality_score,
  segments.month,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.ctr,
  metrics.average_cpc,
  metrics.cost_per_conversion
FROM keyword_view
WHERE segments.date DURING LAST_12_MONTHS
  AND ad_group_criterion.status != 'REMOVED'
  AND campaign.status != 'REMOVED'
ORDER BY segments.month DESC, metrics.cost_micros DESC
LIMIT 500
"""

_SEARCH_TERM_QUERY = """
SELECT
  campaign.name,
  ad_group.name,
  search_term_view.search_term,
  search_term_view.status,
  segments.month,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.ctr,
  metrics.average_cpc
FROM search_term_view
WHERE segments.date DURING LAST_12_MONTHS
  AND metrics.impressions > 5
ORDER BY segments.month DESC, metrics.cost_micros DESC
LIMIT 1000
"""

_GEO_QUERY = """
SELECT
  geographic_view.country_criterion_id,
  geographic_view.location_type,
  campaign.name,
  segments.month,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions
FROM geographic_view
WHERE segments.date DURING LAST_12_MONTHS
ORDER BY segments.month DESC, metrics.cost_micros DESC
LIMIT 500
"""


# ── Live fetch ────────────────────────────────────────────────────────────────

def _run_query(client, customer_id: str, query: str) -> list[dict]:
    """Execute a GAQL query and return list of plain dicts."""
    ga_service = client.get_service('GoogleAdsService')
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    rows = []
    for batch in stream:
        for row in batch.results:
            rows.append(row)
    return rows


def _micros_to_dollars(micros) -> float:
    try:
        return round(int(micros) / 1_000_000, 2)
    except (TypeError, ValueError):
        return 0.0


def _fetch_campaigns(client, customer_id: str) -> list[dict]:
    rows = _run_query(client, customer_id, _CAMPAIGN_QUERY)
    out = []
    for row in rows:
        out.append({
            'month':         row.segments.month,
            'campaign_id':   str(row.campaign.id),
            'campaign_name': row.campaign.name,
            'status':        row.campaign.status.name,
            'channel_type':  row.campaign.advertising_channel_type.name,
            'impressions':   row.metrics.impressions,
            'clicks':        row.metrics.clicks,
            'cost':          _micros_to_dollars(row.metrics.cost_micros),
            'conversions':   round(row.metrics.conversions, 2),
            'conversion_value': round(row.metrics.conversions_value, 2),
            'ctr':           round(row.metrics.ctr * 100, 2),
            'avg_cpc':       _micros_to_dollars(row.metrics.average_cpc),
            'avg_cpm':       _micros_to_dollars(row.metrics.average_cpm),
            'cost_per_conv': _micros_to_dollars(row.metrics.cost_per_conversion),
        })
    return out


def _fetch_keywords(client, customer_id: str) -> list[dict]:
    rows = _run_query(client, customer_id, _KEYWORD_QUERY)
    out = []
    for row in rows:
        out.append({
            'month':         row.segments.month,
            'campaign':      row.campaign.name,
            'ad_group':      row.ad_group.name,
            'keyword':       row.ad_group_criterion.keyword.text,
            'match_type':    row.ad_group_criterion.keyword.match_type.name,
            'quality_score': row.ad_group_criterion.quality_info.quality_score,
            'impressions':   row.metrics.impressions,
            'clicks':        row.metrics.clicks,
            'cost':          _micros_to_dollars(row.metrics.cost_micros),
            'conversions':   round(row.metrics.conversions, 2),
            'ctr':           round(row.metrics.ctr * 100, 2),
            'avg_cpc':       _micros_to_dollars(row.metrics.average_cpc),
            'cost_per_conv': _micros_to_dollars(row.metrics.cost_per_conversion),
        })
    return out


def _fetch_search_terms(client, customer_id: str) -> list[dict]:
    rows = _run_query(client, customer_id, _SEARCH_TERM_QUERY)
    out = []
    for row in rows:
        out.append({
            'month':       row.segments.month,
            'campaign':    row.campaign.name,
            'ad_group':    row.ad_group.name,
            'search_term': row.search_term_view.search_term,
            'status':      row.search_term_view.status.name,
            'impressions': row.metrics.impressions,
            'clicks':      row.metrics.clicks,
            'cost':        _micros_to_dollars(row.metrics.cost_micros),
            'conversions': round(row.metrics.conversions, 2),
            'ctr':         round(row.metrics.ctr * 100, 2),
            'avg_cpc':     _micros_to_dollars(row.metrics.average_cpc),
        })
    return out


def _aggregate_by_month(campaigns: list[dict]) -> list[dict]:
    """Roll campaign rows up to monthly totals."""
    months: dict[str, dict] = {}
    for row in campaigns:
        m = row['month']
        if m not in months:
            months[m] = {
                'month':       m,
                'spend':       0.0,
                'clicks':      0,
                'impressions': 0,
                'conversions': 0.0,
                'conversion_value': 0.0,
                'campaigns':   [],
            }
        months[m]['spend']            += row['cost']
        months[m]['clicks']           += row['clicks']
        months[m]['impressions']      += row['impressions']
        months[m]['conversions']      += row['conversions']
        months[m]['conversion_value'] += row['conversion_value']
        months[m]['campaigns'].append(row)

    result = []
    for m, data in sorted(months.items(), reverse=True):
        spend = data['spend']
        conv  = data['conversions']
        impr  = data['impressions']
        clicks = data['clicks']
        data['ctr']           = round(clicks / impr * 100, 2)  if impr  else 0.0
        data['avg_cpc']       = round(spend / clicks, 2)       if clicks else 0.0
        data['cost_per_conv'] = round(spend / conv, 2)         if conv   else 0.0
        data['roas']          = round(data['conversion_value'] / spend, 2) if spend else 0.0
        result.append(data)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def sync(force: bool = False) -> dict[str, Any]:
    """
    Fetch data from Google Ads API and write to cache.
    Returns a status dict: {ok, records, error, synced_at}
    """
    if not _is_configured():
        return {
            'ok': False,
            'error': 'Google Ads credentials not configured. '
                     'Set GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, '
                     'GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN, '
                     'BEST_CARE_GOOGLE_ADS_CUSTOMER_ID in .env',
            'synced_at': None,
        }

    try:
        from google.ads.googleads.client import GoogleAdsClient
        client = GoogleAdsClient.load_from_dict(_cfg())
        cid    = _customer_id()

        campaigns    = _fetch_campaigns(client, cid)
        keywords     = _fetch_keywords(client, cid)
        search_terms = _fetch_search_terms(client, cid)
        monthly      = _aggregate_by_month(campaigns)

        payload = {
            'synced_at':    datetime.utcnow().isoformat() + 'Z',
            'customer_id':  cid,
            'monthly':      monthly,
            'campaigns':    campaigns,
            'keywords':     keywords,
            'search_terms': search_terms,
        }
        _write_cache(payload)
        return {'ok': True, 'records': len(monthly), 'synced_at': payload['synced_at']}

    except ImportError:
        return {
            'ok': False,
            'error': 'google-ads package not installed. Run: pip install google-ads',
            'synced_at': None,
        }
    except Exception as exc:
        log.exception('Google Ads sync failed')
        return {'ok': False, 'error': str(exc), 'synced_at': None}


def get_monthly_summary() -> list[dict]:
    """Return cached monthly totals, or empty list if cache missing."""
    data = _read_cache()
    return data.get('monthly', [])


def get_campaigns() -> list[dict]:
    data = _read_cache()
    return data.get('campaigns', [])


def get_keywords() -> list[dict]:
    data = _read_cache()
    return data.get('keywords', [])


def get_search_terms() -> list[dict]:
    data = _read_cache()
    return data.get('search_terms', [])


def get_sync_status() -> dict:
    data = _read_cache()
    return {
        'configured':    _is_configured(),
        'synced_at':     data.get('synced_at'),
        'months_cached': len(data.get('monthly', [])),
        'customer_id':   _customer_id() or None,
    }


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path() -> str:
    return os.path.abspath(_CACHE_PATH)


def _read_cache() -> dict:
    path = _cache_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    path = _cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
