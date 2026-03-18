"""
Recommendation Engine — Best Care Auto Transport

Generates data-driven optimization recommendations using:
  - Real Google Ads monthly performance (spend, conversions, CPA)
  - Real 8x8 call data (call volume, answer rate, cost-per-call)
  - Attribution layer (CAC, revenue, profit, ROAS)
  - Competitor intelligence (themes, keywords, offers)
  - Keyword-level wasted spend analysis

Each recommendation includes:
  - title, category, rationale
  - supporting data points
  - competitor insight (if applicable)
  - expected impact (leads, conversions, spend, profit)
  - confidence level (HIGH | MEDIUM | LOW)
  - implementation difficulty (EASY | MEDIUM | HARD)
  - implementation status (pending | approved | running | completed | failed)
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'recommendations.json'
)
_QUEUE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'best_care', 'implementation_queue.json'
)


# ── Rule-based recommendation generators ─────────────────────────────────────

def _recs_from_monthly_performance(monthly: list[dict]) -> list[dict]:
    """Generate recommendations from attribution data trends."""
    if not monthly:
        return []

    recs = []
    recent = monthly[:3]   # last 3 months

    # CAC trend
    cac_vals = [m['cac'] for m in recent if m.get('cac')]
    if len(cac_vals) >= 2 and cac_vals[0] > cac_vals[-1] * 1.15:
        recs.append({
            'category':   'budget',
            'title':      'CAC Rising — Audit Wasted Spend Before Next Budget Cycle',
            'rationale':  (
                f'CAC increased from ${cac_vals[-1]:,.0f} to ${cac_vals[0]:,.0f} '
                f'over {len(cac_vals)} months (+{(cac_vals[0]/cac_vals[-1]-1)*100:.0f}%). '
                'Review and pause non-converting keywords before adding budget.'
            ),
            'data_points': {
                'cac_current': cac_vals[0],
                'cac_previous': cac_vals[-1],
                'change_pct': round((cac_vals[0] / cac_vals[-1] - 1) * 100, 1),
            },
            'expected_impact': {
                'spend_change_pct':    -10,
                'conversion_change_pct': 0,
                'cac_change_pct':     -10,
            },
            'confidence':  'HIGH',
            'difficulty':  'EASY',
        })

    # Low answer rate
    ans_vals = [m['answer_rate'] for m in recent if m.get('answer_rate') is not None]
    if ans_vals and (sum(ans_vals) / len(ans_vals)) < 70:
        avg_ans = round(sum(ans_vals) / len(ans_vals), 1)
        recs.append({
            'category':   'calls',
            'title':      f'Answer Rate {avg_ans}% — Missed Calls Are Paid Leads Going to Competitors',
            'rationale':  (
                f'Average answer rate over the past {len(ans_vals)} months is {avg_ans}%. '
                'Every missed call is a paid lead that likely books with a competitor. '
                'Improving to 85%+ could add conversions at zero additional ad spend.'
            ),
            'data_points': {'avg_answer_rate': avg_ans},
            'expected_impact': {
                'leads_change_pct':       int((85 - avg_ans) / (avg_ans or 1) * 100),
                'conversion_change_pct':  int((85 - avg_ans) / (avg_ans or 1) * 100),
            },
            'confidence':  'HIGH',
            'difficulty':  'EASY',
        })

    # ROAS below target
    roas_vals = [m['roas'] for m in recent if m.get('roas')]
    if roas_vals and (sum(roas_vals) / len(roas_vals)) < 3.0:
        avg_roas = round(sum(roas_vals) / len(roas_vals), 2)
        recs.append({
            'category':   'budget',
            'title':      f'ROAS {avg_roas}x Below 3x Target — Shift Budget to Top-Performing Campaigns',
            'rationale':  (
                f'Blended ROAS of {avg_roas}x is below the 3x breakeven threshold. '
                'Reallocating 20–30% of spend from low-ROAS campaigns to best performers '
                'can improve overall return without increasing total budget.'
            ),
            'data_points': {'avg_roas': avg_roas, 'target_roas': 3.0},
            'expected_impact': {
                'revenue_change_pct':    10,
                'profit_change_pct':     15,
                'spend_change_pct':       0,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'MEDIUM',
        })

    return recs


def _recs_from_keywords(keywords: list[dict]) -> list[dict]:
    """Identify wasted spend and keyword expansion opportunities."""
    if not keywords:
        return []

    recs = []

    # Wasted spend: high cost, zero conversions
    wasted = [
        k for k in keywords
        if k.get('cost', 0) > 100 and k.get('conversions', 0) == 0
    ]
    if wasted:
        total_wasted = sum(k['cost'] for k in wasted)
        recs.append({
            'category':   'keywords',
            'title':      f'Pause {len(wasted)} Zero-Conversion Keywords (${total_wasted:,.0f} wasted)',
            'rationale':  (
                f'{len(wasted)} keywords spent ${total_wasted:,.0f} with 0 conversions. '
                'Pausing these and reallocating to converting keywords directly reduces CPA.'
            ),
            'data_points': {
                'keyword_count':    len(wasted),
                'total_wasted_spend': total_wasted,
                'top_wasted':       sorted(wasted, key=lambda k: -k.get('cost', 0))[:5],
            },
            'expected_impact': {
                'spend_change_pct':       round(-total_wasted / max(sum(k.get('cost', 0) for k in keywords), 1) * 100),
                'cac_change_pct':        -15,
                'conversion_change_pct':   0,
            },
            'confidence':  'HIGH',
            'difficulty':  'EASY',
        })

    # Low quality score keywords
    low_qs = [
        k for k in keywords
        if k.get('quality_score') and k['quality_score'] < 5 and k.get('cost', 0) > 50
    ]
    if low_qs:
        recs.append({
            'category':   'quality',
            'title':      f'{len(low_qs)} Keywords With Quality Score < 5 — Fix Ad Relevance',
            'rationale':  (
                f'{len(low_qs)} active keywords have quality scores below 5, '
                'increasing CPCs by an estimated 20–50%. Improving ad copy relevance '
                'and landing page alignment for these keywords can reduce CPC.'
            ),
            'data_points': {
                'low_qs_count':  len(low_qs),
                'avg_qs':        round(sum(k['quality_score'] for k in low_qs) / len(low_qs), 1),
                'keywords':      [k['keyword'] for k in low_qs[:5]],
            },
            'expected_impact': {
                'cpc_change_pct':  -20,
                'spend_change_pct': -10,
                'ctr_change_pct':   15,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'MEDIUM',
        })

    return recs


def _recs_from_search_terms(search_terms: list[dict]) -> list[dict]:
    """Find negative keyword opportunities and expansion terms."""
    if not search_terms:
        return []

    recs = []

    # High spend, zero conv search terms → negative keyword candidates
    negatives = [
        st for st in search_terms
        if st.get('cost', 0) > 75 and st.get('conversions', 0) == 0
    ]
    if negatives:
        total = sum(st['cost'] for st in negatives)
        recs.append({
            'category':   'negatives',
            'title':      f'Add {len(negatives)} Negative Keywords From Wasted Search Terms (${total:,.0f})',
            'rationale':  (
                f'{len(negatives)} search terms triggered ads and spent ${total:,.0f} '
                'with no conversions. Adding these as negative keywords prevents '
                'future wasted impressions on unqualified searches.'
            ),
            'data_points': {
                'negative_count': len(negatives),
                'total_wasted':   total,
                'top_terms':      sorted(negatives, key=lambda x: -x.get('cost', 0))[:10],
            },
            'expected_impact': {
                'spend_change_pct':  round(-total / max(sum(st.get('cost', 0) for st in search_terms), 1) * 100),
                'ctr_change_pct':    10,
                'cac_change_pct':   -12,
            },
            'confidence':  'HIGH',
            'difficulty':  'EASY',
        })

    # High-converting search terms not yet in keyword list → expansion
    converters = [
        st for st in search_terms
        if st.get('conversions', 0) >= 1 and st.get('status', '') == 'NONE'
    ]
    if converters:
        recs.append({
            'category':   'expansion',
            'title':      f'Add {len(converters)} Converting Search Terms as Exact Match Keywords',
            'rationale':  (
                f'{len(converters)} search terms generated conversions but are not targeted '
                'as explicit keywords (matched via broad/phrase). Adding as exact match '
                'gives control over bids and budgets for these proven terms.'
            ),
            'data_points': {
                'count':    len(converters),
                'terms':    [st['search_term'] for st in converters[:10]],
            },
            'expected_impact': {
                'conversion_change_pct': 8,
                'cac_change_pct':        -8,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'EASY',
        })

    return recs


def _recs_from_competitor_intel(intel: dict) -> list[dict]:
    """Generate recommendations informed by competitor ad data."""
    if not intel:
        return []

    recs = []
    themes  = intel.get('global_themes', [])
    offers  = intel.get('global_offers', [])
    comps   = intel.get('competitors', [])

    # Dominant competitor theme not reflected in our current strategy
    dominant_themes = [t for t in themes if t.get('prevalence_pct', 0) >= 50]
    for t in dominant_themes[:2]:
        recs.append({
            'category':       'ad_copy',
            'title':          f'Test Ad Copy Angle: "{t["theme"].title()}" (Used by {t["prevalence_pct"]}% of Competitors)',
            'rationale':      (
                f'{t["prevalence_pct"]}% of competitor ads in the auto transport space '
                f'use the "{t["theme"]}" messaging angle. This frequency suggests the '
                'market responds to this message. Test a variation of this angle in '
                'one campaign to benchmark against current creative.'
            ),
            'competitor_insight': {
                'theme':          t['theme'],
                'prevalence_pct': t['prevalence_pct'],
                'ad_count':       t['count'],
            },
            'data_points': {'theme': t},
            'expected_impact': {
                'ctr_change_pct':        15,
                'conversion_change_pct':  8,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'EASY',
        })

    # Competitor offer patterns
    if offers:
        recs.append({
            'category':       'offers',
            'title':          f'Test Offer: {offers[0]} — Matches Top Competitor CTAs',
            'rationale':      (
                f'"{offers[0]}" appears repeatedly in competitor ads, suggesting it '
                'converts well in this market. Add this CTA to at least one ad group '
                'to measure response against current offer.'
            ),
            'competitor_insight': {'offers': offers[:5]},
            'data_points': {'competitor_offers': offers},
            'expected_impact': {
                'ctr_change_pct':        10,
                'conversion_change_pct':  5,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'EASY',
        })

    # Top competitor keyword expansion
    if comps:
        top_comp = comps[0]
        kws = top_comp.get('keywords', [])[:5]
        if kws:
            recs.append({
                'category':       'keywords',
                'title':          f'Target {top_comp["domain"]} Keyword Gaps',
                'rationale':      (
                    f'{top_comp["domain"]} is the most active paid advertiser in this '
                    f'analysis. They target keywords including: {", ".join(kws[:3])}. '
                    'Closing keyword gaps against this competitor captures demand '
                    'they are currently intercepting.'
                ),
                'competitor_insight': {
                    'domain':   top_comp['domain'],
                    'keywords': kws,
                    'ad_count': top_comp.get('ad_count', 0),
                },
                'data_points': {},
                'expected_impact': {
                    'impressions_change_pct': 20,
                    'leads_change_pct':       10,
                },
                'confidence':  'MEDIUM',
                'difficulty':  'MEDIUM',
            })

    return recs


def _recs_calls_vs_ads(monthly: list[dict]) -> list[dict]:
    """Surface mismatches between call volume and paid traffic."""
    if not monthly:
        return []

    recs = []
    recent = monthly[:3]
    high_cost_low_calls = [
        m for m in recent
        if m.get('spend', 0) > 2000 and m.get('total_calls', 0) < 30
    ]
    if high_cost_low_calls:
        avg_spend = round(sum(m['spend'] for m in high_cost_low_calls) / len(high_cost_low_calls))
        avg_calls = round(sum(m['total_calls'] for m in high_cost_low_calls) / len(high_cost_low_calls))
        recs.append({
            'category':   'calls',
            'title':      f'High Spend (${avg_spend:,}/mo), Low Call Volume ({avg_calls}/mo) — Audit Call Extensions',
            'rationale':  (
                f'Spending ${avg_spend:,}/month but generating only ~{avg_calls} calls. '
                'Either call extensions are missing, ads are not driving call intent, '
                'or tracking is incomplete. Audit call extension setup and '
                'verify call tracking is firing on the sales number.'
            ),
            'data_points': {
                'avg_monthly_spend': avg_spend,
                'avg_monthly_calls': avg_calls,
                'cost_per_call_est': round(avg_spend / max(avg_calls, 1)),
            },
            'expected_impact': {
                'call_change_pct': 25,
                'lead_change_pct': 25,
            },
            'confidence':  'MEDIUM',
            'difficulty':  'EASY',
        })

    return recs


# ── Assemble + persist ────────────────────────────────────────────────────────

def _build_rec(raw: dict) -> dict:
    return {
        'id':                  f'rec_{uuid.uuid4().hex[:8]}',
        'group_id':            'best_care_auto',
        'source':              'live',   # distinguishes from mock recs
        'category':            raw.get('category', 'general'),
        'channel':             raw.get('channel', 'google_ads'),
        'title':               raw.get('title', ''),
        'rationale':           raw.get('rationale', ''),
        'data_points':         raw.get('data_points', {}),
        'competitor_insight':  raw.get('competitor_insight'),
        'expected_impact':     raw.get('expected_impact', {}),
        'confidence':          raw.get('confidence', 'MEDIUM'),
        'difficulty':          raw.get('difficulty', 'MEDIUM'),
        'status':              'pending',
        'priority':            _priority(raw.get('confidence', 'MEDIUM'), raw.get('difficulty', 'MEDIUM')),
        'generated_at':        datetime.utcnow().isoformat() + 'Z',
    }


def _priority(confidence: str, difficulty: str) -> str:
    if confidence == 'HIGH' and difficulty == 'EASY':
        return 'high'
    if confidence == 'HIGH':
        return 'medium'
    return 'low'


def generate() -> dict[str, Any]:
    """Generate recommendations from all available real data sources."""
    from services import google_ads_service    as gads
    from services import attribution_service   as attr
    from services import competitor_intel_service as comp

    monthly     = attr.get_monthly_performance()
    keywords    = gads.get_keywords()
    search_terms = gads.get_search_terms()
    intel       = comp.get_all()

    raw_recs = []
    raw_recs.extend(_recs_from_monthly_performance(monthly))
    raw_recs.extend(_recs_from_keywords(keywords))
    raw_recs.extend(_recs_from_search_terms(search_terms))
    raw_recs.extend(_recs_from_competitor_intel(intel))
    raw_recs.extend(_recs_calls_vs_ads(monthly))

    built = [_build_rec(r) for r in raw_recs]

    # Sort: high priority first
    order = {'high': 0, 'medium': 1, 'low': 2}
    built.sort(key=lambda r: order.get(r['priority'], 9))

    payload = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'count':        len(built),
        'recommendations': built,
    }
    _write_cache(_CACHE_PATH, payload)
    return {'ok': True, 'count': len(built), 'generated_at': payload['generated_at']}


def get_recommendations() -> list[dict]:
    data = _read_cache(_CACHE_PATH)
    return data.get('recommendations', [])


def update_status(rec_id: str, status: str, notes: str = '') -> dict | None:
    data = _read_cache(_CACHE_PATH)
    for rec in data.get('recommendations', []):
        if rec['id'] == rec_id:
            rec['status']     = status
            rec['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            if notes:
                rec['notes'] = notes
            _write_cache(_CACHE_PATH, data)
            return rec
    return None


# ── Implementation queue ──────────────────────────────────────────────────────

def queue_action(rec_id: str, action_type: str, params: dict = None) -> dict:
    data   = _read_cache(_QUEUE_PATH)
    queue  = data.get('queue', [])

    action = {
        'id':          f'act_{uuid.uuid4().hex[:8]}',
        'rec_id':      rec_id,
        'action_type': action_type,
        'params':      params or {},
        'status':      'pending',
        'queued_at':   datetime.utcnow().isoformat() + 'Z',
        'executed_at': None,
        'result':      None,
    }
    queue.append(action)
    _write_cache(_QUEUE_PATH, {'queue': queue})
    return action


def get_queue() -> list[dict]:
    return _read_cache(_QUEUE_PATH).get('queue', [])


def execute_action(action_id: str) -> dict:
    """
    Execute a queued action. Currently runs in mock/staged mode.
    Replace the _mock_execute() calls with real API calls when ready for live execution.
    """
    data  = _read_cache(_QUEUE_PATH)
    queue = data.get('queue', [])

    for action in queue:
        if action['id'] == action_id:
            result = _mock_execute(action)
            action['status']      = 'completed' if result['ok'] else 'failed'
            action['executed_at'] = datetime.utcnow().isoformat() + 'Z'
            action['result']      = result
            _write_cache(_QUEUE_PATH, {'queue': queue})
            # Mark the linked recommendation as implemented
            if result['ok'] and action.get('rec_id'):
                update_status(action['rec_id'], 'implemented',
                              notes=f'Action {action_id} executed')
            return action

    return {'error': f'Action {action_id} not found'}


def _mock_execute(action: dict) -> dict:
    """
    Staged/mock executor. Simulates action execution without touching live accounts.
    Future: replace each action_type branch with real Google Ads mutate calls.
    """
    at = action.get('action_type', '')
    p  = action.get('params', {})

    if at == 'pause_keywords':
        return {
            'ok':     True,
            'message': f'[STAGED] Would pause {len(p.get("keyword_ids", []))} keywords',
            'mode':   'staged',
        }
    elif at == 'add_negatives':
        return {
            'ok':     True,
            'message': f'[STAGED] Would add {len(p.get("terms", []))} negative keywords',
            'mode':   'staged',
        }
    elif at == 'budget_shift':
        return {
            'ok':     True,
            'message': f'[STAGED] Would shift ${p.get("amount", 0)} from campaign {p.get("from_campaign")} to {p.get("to_campaign")}',
            'mode':   'staged',
        }
    elif at == 'ad_copy_test':
        return {
            'ok':     True,
            'message': f'[STAGED] Would create ad copy test: {p.get("headline", "")}',
            'mode':   'staged',
        }
    else:
        return {
            'ok':     True,
            'message': f'[STAGED] Action "{at}" logged for manual execution',
            'mode':   'staged',
        }


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _read_cache(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
