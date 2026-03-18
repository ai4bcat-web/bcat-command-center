"""
8x8 Call Tracking Service — Best Care Auto Transport
Connects to the 8x8 Analytics API and pulls CDR (Call Detail Records)
for the configured sales phone number.

Required environment variables (see .env.example):
  EIGHTX8_API_KEY           — API key from 8x8 developer console
  EIGHTX8_BASE_URL          — e.g. https://api.8x8.com  (default shown)
  EIGHTX8_ACCOUNT_ID        — 8x8 account / sub-account ID
  BEST_CARE_SALES_NUMBER    — E.164 format, e.g. +17085551234

8x8 API reference:
  https://developer.8x8.com/work/reference
  CDR endpoint: GET /analytics/v2/accounts/{accountId}/cdrs
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

log = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'calls_monthly.json'
)

_DEFAULT_BASE_URL = 'https://api.8x8.com'


# ── Config ────────────────────────────────────────────────────────────────────

def _api_key() -> str:
    return os.getenv('EIGHTX8_API_KEY', '')

def _base_url() -> str:
    return os.getenv('EIGHTX8_BASE_URL', _DEFAULT_BASE_URL).rstrip('/')

def _account_id() -> str:
    return os.getenv('EIGHTX8_ACCOUNT_ID', '')

def _sales_number() -> str:
    """Configurable target phone number in E.164 format."""
    return os.getenv('BEST_CARE_SALES_NUMBER', '')

def _is_configured() -> bool:
    return bool(_api_key() and _account_id())


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'Authorization': f'Bearer {_api_key()}',
        'Content-Type':  'application/json',
        'Accept':        'application/json',
    }


def _get(path: str, params: dict = None) -> dict | list:
    """Make an authenticated GET request to the 8x8 API."""
    import urllib.request
    import urllib.parse

    url = f'{_base_url()}{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)

    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


# ── Fetch CDR ─────────────────────────────────────────────────────────────────

def _fetch_cdrs(start_date: str, end_date: str) -> list[dict]:
    """
    Fetch Call Detail Records from 8x8 Analytics API.

    8x8 CDR endpoint:
      GET /analytics/v2/accounts/{accountId}/cdrs
    Params:
      startTime  — ISO8601 datetime
      endTime    — ISO8601 datetime
      direction  — INBOUND | OUTBOUND | ALL
      pageSize   — max 1000
      pageToken  — for pagination
    """
    account = _account_id()
    path    = f'/analytics/v2/accounts/{account}/cdrs'
    target  = _sales_number()

    all_records = []
    page_token  = None

    while True:
        params: dict = {
            'startTime': f'{start_date}T00:00:00Z',
            'endTime':   f'{end_date}T23:59:59Z',
            'direction': 'INBOUND',
            'pageSize':  1000,
        }
        if page_token:
            params['pageToken'] = page_token

        data      = _get(path, params)
        records   = data.get('cdrs', data.get('records', data.get('items', [])))

        for r in records:
            # Normalize 8x8 CDR fields — field names vary by 8x8 product/version
            normalized = _normalize_cdr(r)
            # Filter to target number if configured
            if target and normalized['called_number'] != target:
                continue
            all_records.append(normalized)

        # Pagination
        page_token = data.get('nextPageToken') or data.get('nextPage')
        if not page_token:
            break

    return all_records


def _normalize_cdr(raw: dict) -> dict:
    """
    Normalize raw 8x8 CDR into a consistent format.
    8x8 field names differ between Work API and CPaaS API versions.
    We handle both variants.
    """
    # Timestamp
    ts_raw = (
        raw.get('startTime') or raw.get('startDate') or
        raw.get('callDateTime') or raw.get('timestamp') or ''
    )
    try:
        ts = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        ts = None

    # Duration
    duration_secs = (
        raw.get('duration') or raw.get('durationSeconds') or
        raw.get('callDuration') or 0
    )
    try:
        duration_secs = int(duration_secs)
    except (TypeError, ValueError):
        duration_secs = 0

    # Direction / disposition
    direction   = (raw.get('direction') or '').upper()
    disposition = (
        raw.get('disposition') or raw.get('outcome') or
        raw.get('status') or raw.get('callResult') or ''
    ).upper()
    answered = disposition in ('ANSWERED', 'CONNECTED', 'COMPLETED') or duration_secs > 10

    # Numbers
    called_number = (
        raw.get('calledNumber') or raw.get('to') or
        raw.get('destinationNumber') or raw.get('toNumber') or ''
    )
    caller_number = (
        raw.get('callerNumber') or raw.get('from') or
        raw.get('sourceNumber') or raw.get('fromNumber') or ''
    )

    return {
        'call_id':       raw.get('id') or raw.get('callId') or raw.get('uuid', ''),
        'timestamp':     ts.isoformat() if ts else ts_raw,
        'month':         ts.strftime('%Y-%m') if ts else '',
        'direction':     direction or 'INBOUND',
        'called_number': called_number,
        'caller_number': caller_number,
        'duration_secs': duration_secs,
        'answered':      answered,
        'disposition':   disposition,
        'agent':         raw.get('agent') or raw.get('user') or raw.get('agentName', ''),
        'queue':         raw.get('queue') or raw.get('queueName', ''),
        'raw':           raw,   # keep original for future processing
    }


# ── Monthly rollup ────────────────────────────────────────────────────────────

def _rollup_by_month(records: list[dict]) -> list[dict]:
    months: dict[str, dict] = defaultdict(lambda: {
        'total_calls':    0,
        'answered_calls': 0,
        'missed_calls':   0,
        'total_duration': 0,
        'unique_callers': set(),
        'calls':          [],
    })

    for r in records:
        m = r.get('month', '')
        if not m:
            continue
        months[m]['total_calls']    += 1
        months[m]['total_duration'] += r['duration_secs']
        months[m]['unique_callers'].add(r['caller_number'])
        months[m]['calls'].append(r)
        if r['answered']:
            months[m]['answered_calls'] += 1
        else:
            months[m]['missed_calls'] += 1

    result = []
    for m, data in sorted(months.items(), reverse=True):
        total  = data['total_calls']
        ans    = data['answered_calls']
        result.append({
            'month':             m,
            'total_calls':       total,
            'answered_calls':    ans,
            'missed_calls':      data['missed_calls'],
            'answer_rate':       round(ans / total * 100, 1) if total else 0.0,
            'avg_duration_secs': round(data['total_duration'] / total) if total else 0,
            'unique_callers':    len(data['unique_callers']),
            # individual records excluded from monthly summary to keep cache small
        })
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def sync(months_back: int = 13) -> dict[str, Any]:
    """
    Fetch CDRs from 8x8 for the past N months and write to cache.
    Returns status dict.
    """
    if not _is_configured():
        return {
            'ok': False,
            'error': 'Missing 8x8 credentials. '
                     'Set EIGHTX8_API_KEY, EIGHTX8_ACCOUNT_ID, '
                     'BEST_CARE_SALES_NUMBER in .env',
            'synced_at': None,
        }

    try:
        end   = date.today()
        start = (end.replace(day=1) - timedelta(days=months_back * 28)).replace(day=1)

        records = _fetch_cdrs(start.isoformat(), end.isoformat())
        monthly = _rollup_by_month(records)

        payload = {
            'synced_at':    datetime.utcnow().isoformat() + 'Z',
            'account_id':   _account_id(),
            'target_number': _sales_number(),
            'total_records': len(records),
            'monthly':      monthly,
        }
        _write_cache(payload)
        return {
            'ok':        True,
            'records':   len(records),
            'months':    len(monthly),
            'synced_at': payload['synced_at'],
        }

    except Exception as exc:
        log.exception('8x8 sync failed')
        return {'ok': False, 'error': str(exc), 'synced_at': None}


def get_monthly_summary() -> list[dict]:
    data = _read_cache()
    return data.get('monthly', [])


def get_sync_status() -> dict:
    data = _read_cache()
    return {
        'configured':    _is_configured(),
        'synced_at':     data.get('synced_at'),
        'months_cached': len(data.get('monthly', [])),
        'target_number': _sales_number() or None,
        'account_id':    _account_id() or None,
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
