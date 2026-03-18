"""
Attribution & Monthly Channel Performance — Best Care Auto Transport

Combines Google Ads spend data with 8x8 call data to calculate:
  - Conversions (calls treated as leads; closing rate applied for conversion)
  - CAC (Customer Acquisition Cost)
  - Revenue attributed to Google Ads
  - Profit attributed to Google Ads
  - ROAS, cost-per-call, cost-per-lead, cost-per-sale

Attribution approach:
  1. If Google Ads has conversion tracking data configured → use it directly (ACTUAL)
  2. If 8x8 calls can be matched to a time window → use answered calls as leads (MODELED)
  3. If neither is available → apply configurable assumptions (ESTIMATED)

Metric quality labels used throughout:
  ACTUAL    — sourced directly from a verified integration
  MODELED   — calculated from connected data sources with an explicit formula
  ESTIMATED — derived from configurable assumptions; may not reflect exact reality

Revenue/profit assumptions are configurable via environment variables
(see .env.example) and stored in data/best_care/config.json.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'channel_performance.json'
)
_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'config.json'
)


# ── Assumptions / config ──────────────────────────────────────────────────────

_DEFAULT_CONFIG = {
    # Revenue model
    'avg_revenue_per_conversion': 2500.0,   # $/sale
    'avg_profit_per_conversion':  450.0,    # $/sale  (profit after carrier cost)

    # Conversion funnel (used when Google Ads conversion tracking is incomplete)
    'call_to_lead_rate':          0.70,     # % of answered calls that are qualified leads
    'lead_to_close_rate':         0.15,     # % of qualified leads that become customers

    # Cost structure
    'avg_carrier_cost_per_job':   2050.0,   # carrier pay (gross cost of service)

    # Attribution assumption labels
    'revenue_source':  'ESTIMATED',         # ACTUAL | MODELED | ESTIMATED
    'conv_source':     'MODELED',           # ACTUAL | MODELED | ESTIMATED
    'call_source':     'ACTUAL',            # ACTUAL | MODELED | ESTIMATED
    'spend_source':    'ACTUAL',            # ACTUAL | MODELED | ESTIMATED
}


def get_config() -> dict:
    """Load config from file, falling back to environment variables, then defaults."""
    cfg = dict(_DEFAULT_CONFIG)

    # File-based overrides
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH) as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception:
            pass

    # Environment variable overrides (highest priority)
    env_map = {
        'BEST_CARE_AVG_REVENUE_PER_CONVERSION': ('avg_revenue_per_conversion', float),
        'BEST_CARE_AVG_PROFIT_PER_CONVERSION':  ('avg_profit_per_conversion',  float),
        'BEST_CARE_CALL_TO_LEAD_RATE':          ('call_to_lead_rate',          float),
        'BEST_CARE_LEAD_TO_CLOSE_RATE':         ('lead_to_close_rate',         float),
    }
    for env_key, (cfg_key, cast) in env_map.items():
        val = os.getenv(env_key)
        if val:
            try:
                cfg[cfg_key] = cast(val)
            except (TypeError, ValueError):
                pass

    return cfg


def save_config(updates: dict) -> dict:
    """Persist assumption overrides to config.json. Returns updated config."""
    cfg = get_config()
    cfg.update(updates)
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)
    return cfg


# ── Core calculations ─────────────────────────────────────────────────────────

def _calc_month(
    month: str,
    ads: dict | None,
    calls: dict | None,
    cfg: dict,
) -> dict:
    """
    Calculate full channel performance for one month.

    ads   — monthly Google Ads row   (or None)
    calls — monthly 8x8 call row     (or None)
    cfg   — assumption config
    """
    # ── Spend ──
    spend = float((ads or {}).get('spend', 0) or 0)
    spend_quality = cfg['spend_source'] if ads else 'MISSING'

    # ── Calls ──
    total_calls    = int((calls or {}).get('total_calls', 0))
    answered_calls = int((calls or {}).get('answered_calls', 0))
    missed_calls   = int((calls or {}).get('missed_calls', 0))
    answer_rate    = float((calls or {}).get('answer_rate', 0))
    call_quality   = cfg['call_source'] if calls else 'MISSING'

    # ── Conversions ──
    # Prefer Google Ads conversion tracking if > 0
    ads_conversions = float((ads or {}).get('conversions', 0) or 0)
    if ads_conversions > 0:
        conversions     = ads_conversions
        conv_quality    = 'ACTUAL'
        leads           = round(answered_calls * cfg['call_to_lead_rate'])
    else:
        # Model from calls
        leads           = round(answered_calls * cfg['call_to_lead_rate'])
        conversions     = round(leads * cfg['lead_to_close_rate'], 1)
        conv_quality    = 'MODELED' if calls else 'ESTIMATED'

    # ── Revenue & Profit ──
    ads_conv_value = float((ads or {}).get('conversion_value', 0) or 0)
    if ads_conv_value > 0:
        revenue         = ads_conv_value
        profit          = revenue - (conversions * cfg['avg_carrier_cost_per_job'])
        rev_quality     = 'ACTUAL'
    else:
        revenue         = round(conversions * cfg['avg_revenue_per_conversion'], 2)
        profit          = round(conversions * cfg['avg_profit_per_conversion'], 2)
        rev_quality     = cfg['revenue_source']

    # ── Derived metrics ──
    cac          = round(spend / conversions, 2)       if conversions else None
    roas         = round(revenue / spend, 2)           if spend       else None
    cost_per_call= round(spend / total_calls, 2)       if total_calls else None
    cost_per_lead= round(spend / leads, 2)             if leads       else None
    conv_rate    = round(conversions / leads * 100, 1) if leads       else None

    return {
        'month':             month,

        # Spend
        'spend':             spend,
        'spend_quality':     spend_quality,

        # Calls
        'total_calls':       total_calls,
        'answered_calls':    answered_calls,
        'missed_calls':      missed_calls,
        'answer_rate':       answer_rate,
        'call_quality':      call_quality,

        # Leads & conversions
        'leads':             leads,
        'conversions':       conversions,
        'conv_quality':      conv_quality,

        # Revenue & profit
        'revenue':           revenue,
        'profit':            profit,
        'rev_quality':       rev_quality,

        # Derived
        'cac':               cac,
        'roas':              roas,
        'cost_per_call':     cost_per_call,
        'cost_per_lead':     cost_per_lead,
        'conversion_rate':   conv_rate,

        # Passthrough for charts
        'impressions':       int((ads or {}).get('impressions', 0)),
        'clicks':            int((ads or {}).get('clicks', 0)),
        'ctr':               float((ads or {}).get('ctr', 0)),
        'avg_cpc':           float((ads or {}).get('avg_cpc', 0)),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_and_cache() -> dict[str, Any]:
    """
    Read current Google Ads + 8x8 caches, calculate monthly performance,
    write results to channel_performance.json.
    Returns status dict.
    """
    from services import google_ads_service as gads
    from services import eightx8_service    as calls

    cfg       = get_config()
    ads_rows  = {r['month']: r for r in gads.get_monthly_summary()}
    call_rows = {r['month']: r for r in calls.get_monthly_summary()}

    all_months = sorted(set(list(ads_rows.keys()) + list(call_rows.keys())), reverse=True)

    if not all_months:
        return {
            'ok':     False,
            'error':  'No data available yet. Run Google Ads and 8x8 syncs first.',
            'months': 0,
        }

    results = []
    for m in all_months:
        row = _calc_month(m, ads_rows.get(m), call_rows.get(m), cfg)
        results.append(row)

    payload = {
        'calculated_at': datetime.utcnow().isoformat() + 'Z',
        'config':        cfg,
        'monthly':       results,
    }
    _write_cache(payload)
    return {'ok': True, 'months': len(results), 'calculated_at': payload['calculated_at']}


def get_monthly_performance() -> list[dict]:
    """Return cached monthly channel performance rows."""
    return _read_cache().get('monthly', [])


def get_assumptions() -> dict:
    """Return current config/assumptions alongside metric quality labels."""
    return get_config()


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
