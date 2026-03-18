"""
Best Care Auto Transport — Service Orchestrator

Top-level service that coordinates all Best Care integrations:
  - Google Ads sync
  - 8x8 call sync
  - Attribution / channel performance calculation
  - Competitor intelligence sync
  - Recommendation generation

This is the single import surface for the Flask routes.
Pattern is reusable: clone for BCAT Logistics and Ivan Amazon Drivers.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

_SYNC_LOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'sync_log.json'
)


# ── Sync orchestration ────────────────────────────────────────────────────────

def sync_google_ads() -> dict:
    from services import google_ads_service as svc
    result = svc.sync()
    _log_sync('google_ads', result)
    # Recalculate channel performance after new data
    if result.get('ok'):
        from services import attribution_service
        attribution_service.calculate_and_cache()
    return result


def sync_calls() -> dict:
    from services import eightx8_service as svc
    result = svc.sync()
    _log_sync('calls', result)
    if result.get('ok'):
        from services import attribution_service
        attribution_service.calculate_and_cache()
    return result


def sync_competitors() -> dict:
    from services import competitor_intel_service as svc
    result = svc.sync()
    _log_sync('competitors', result)
    return result


def sync_all() -> dict[str, Any]:
    """Run all syncs in sequence. Returns a summary of each result."""
    results = {}
    results['google_ads']  = sync_google_ads()
    results['calls']       = sync_calls()
    results['competitors'] = sync_competitors()

    # Recalculate performance after all syncs
    from services import attribution_service
    perf_result = attribution_service.calculate_and_cache()
    results['performance_calc'] = perf_result

    # Regenerate recommendations with fresh data
    from services import recommendation_service
    rec_result = recommendation_service.generate()
    results['recommendations'] = rec_result

    return results


def generate_recommendations() -> dict:
    from services import recommendation_service
    result = recommendation_service.generate()
    _log_sync('recommendations', result)
    return result


# ── Dashboard data ────────────────────────────────────────────────────────────

def get_dashboard_data() -> dict:
    """
    Return the full data payload for the Best Care real-data dashboard view.
    Aggregates from all caches. Falls back gracefully if any cache is missing.
    """
    from services import (
        google_ads_service,
        eightx8_service,
        attribution_service,
        competitor_intel_service,
        recommendation_service,
    )

    monthly_perf = attribution_service.get_monthly_performance()
    assumptions  = attribution_service.get_assumptions()
    gads_monthly = google_ads_service.get_monthly_summary()
    calls_monthly = eightx8_service.get_monthly_summary()
    competitors  = competitor_intel_service.get_competitor_summary()
    themes       = competitor_intel_service.get_global_themes()
    offers       = competitor_intel_service.get_global_offers()
    recs         = recommendation_service.get_recommendations()
    queue        = recommendation_service.get_queue()

    has_real_data = bool(monthly_perf)

    return {
        'group_id':      'best_care_auto',
        'has_real_data': has_real_data,
        'data_quality':  _data_quality_summary(monthly_perf, assumptions),
        'monthly_performance': monthly_perf,
        'google_ads':    {'monthly': gads_monthly},
        'calls':         {'monthly': calls_monthly},
        'competitors': {
            'list':           competitors,
            'global_themes':  themes,
            'global_offers':  offers,
        },
        'recommendations':      recs,
        'implementation_queue': queue,
        'assumptions':    assumptions,
        'sync_status':    get_sync_status(),
    }


def get_sync_status() -> dict:
    from services import (
        google_ads_service,
        eightx8_service,
        competitor_intel_service,
    )
    from services import attribution_service

    perf_cache = attribution_service._read_cache()

    return {
        'google_ads':   google_ads_service.get_sync_status(),
        'calls':        eightx8_service.get_sync_status(),
        'competitors':  competitor_intel_service.get_sync_status(),
        'performance_calculated_at': perf_cache.get('calculated_at'),
        'recent_syncs': _get_recent_logs(10),
    }


def _data_quality_summary(monthly: list[dict], cfg: dict) -> dict:
    """Summarize which metrics are actual vs modeled vs estimated."""
    if not monthly:
        return {'spend': 'MISSING', 'calls': 'MISSING', 'conversions': 'MISSING', 'revenue': 'MISSING'}
    latest = monthly[0]
    return {
        'spend':       latest.get('spend_quality', cfg.get('spend_source', 'UNKNOWN')),
        'calls':       latest.get('call_quality',  cfg.get('call_source', 'UNKNOWN')),
        'conversions': latest.get('conv_quality',  cfg.get('conv_source', 'UNKNOWN')),
        'revenue':     latest.get('rev_quality',   cfg.get('revenue_source', 'UNKNOWN')),
    }


# ── Sync log ──────────────────────────────────────────────────────────────────

def _log_sync(sync_type: str, result: dict) -> None:
    data = _read_log()
    logs = data.get('logs', [])
    logs.insert(0, {
        'sync_type':  sync_type,
        'timestamp':  datetime.utcnow().isoformat() + 'Z',
        'ok':         result.get('ok', False),
        'records':    result.get('records') or result.get('count') or result.get('months'),
        'error':      result.get('error'),
    })
    logs = logs[:200]   # keep last 200 entries
    _write_log({'logs': logs})


def _get_recent_logs(n: int = 20) -> list[dict]:
    return _read_log().get('logs', [])[:n]


def _read_log() -> dict:
    if not os.path.exists(_SYNC_LOG_PATH):
        return {'logs': []}
    try:
        with open(_SYNC_LOG_PATH) as f:
            return json.load(f)
    except Exception:
        return {'logs': []}


def _write_log(data: dict) -> None:
    os.makedirs(os.path.dirname(_SYNC_LOG_PATH), exist_ok=True)
    with open(_SYNC_LOG_PATH, 'w') as f:
        json.dump(data, f, indent=2)
