"""
Sales Recommendation Service
Daily optimization engine for outbound sales workspaces.

Evaluates yesterday's results, email campaign performance, and lead pipeline
to generate actionable next-day recommendations with priority and effort scores.
"""

import json, logging, os
from datetime import datetime, timezone, timedelta
log = logging.getLogger(__name__)

_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales')

# ── Thresholds ────────────────────────────────────────────────────────────────

THRESHOLDS = {
    'open_rate_low':        0.25,   # below this → subject line issue
    'open_rate_good':       0.45,
    'reply_rate_low':       0.03,   # below this → body copy issue
    'reply_rate_good':      0.08,
    'bounce_rate_high':     0.05,   # above this → list quality issue
    'meeting_rate_low':     0.015,  # replies-to-meetings below this → follow-up gap
    'daily_sends_min':      30,     # below this → pipeline at risk
    'daily_sends_target':   75,
    'stale_lead_days':      14,     # leads untouched this long
    'pipeline_low_usd':     20000,  # total pipeline value below this → lead gen needed
}

# ── Public API ────────────────────────────────────────────────────────────────

def generate(workspace_id: str, use_real_data: bool = False) -> dict:
    """
    Generate daily recommendations for a workspace.
    Reads real service caches when available; falls back to mock data.
    Returns list of recommendations written to cache.
    """
    try:
        recs = []

        # Gather data
        email_data  = _get_email_data(workspace_id, use_real_data)
        lead_data   = _get_lead_data(workspace_id, use_real_data)
        daily_data  = _get_daily_data(workspace_id, use_real_data)
        meeting_data = _get_meeting_data(workspace_id, use_real_data)

        # Run rule engines
        recs.extend(_recs_from_email_performance(email_data))
        recs.extend(_recs_from_lead_pipeline(lead_data))
        recs.extend(_recs_from_daily_volume(daily_data))
        recs.extend(_recs_from_meetings(meeting_data))
        recs.extend(_recs_workspace_specific(workspace_id, email_data, lead_data))

        # Dedupe by title, sort by priority
        seen = set()
        unique_recs = []
        for r in recs:
            if r['title'] not in seen:
                seen.add(r['title'])
                unique_recs.append(r)

        unique_recs.sort(key=lambda r: (
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(r['priority'], 4),
            -r.get('impact_score', 0)
        ))

        # Assign IDs
        now = datetime.now(timezone.utc)
        for i, r in enumerate(unique_recs):
            r['id']         = f'srec_{workspace_id}_{now.strftime("%Y%m%d")}_{i:02d}'
            r['generated_at'] = now.isoformat()
            r['status']     = 'pending'

        payload = {
            'generated_at': now.isoformat(),
            'workspace_id': workspace_id,
            'recommendations': unique_recs,
        }
        _write_cache(workspace_id, 'recommendations', payload)
        return {'ok': True, 'count': len(unique_recs), 'recommendations': unique_recs}

    except Exception as e:
        log.exception('Sales recommendation generation failed')
        return {'ok': False, 'error': str(e), 'recommendations': []}


def get_recommendations(workspace_id: str) -> list:
    data = _read_cache(workspace_id, 'recommendations')
    return data.get('recommendations', [])


def mark_implemented(workspace_id: str, rec_id: str, notes: str = '') -> dict:
    data = _read_cache(workspace_id, 'recommendations')
    recs = data.get('recommendations', [])
    for r in recs:
        if r['id'] == rec_id:
            r['status'] = 'implemented'
            r['implemented_at'] = datetime.now(timezone.utc).isoformat()
            r['implementation_notes'] = notes
            _write_cache(workspace_id, 'recommendations', data)
            return {'ok': True, 'rec': r}
    return {'ok': False, 'error': 'Recommendation not found'}


def mark_dismissed(workspace_id: str, rec_id: str) -> dict:
    data = _read_cache(workspace_id, 'recommendations')
    recs = data.get('recommendations', [])
    for r in recs:
        if r['id'] == rec_id:
            r['status'] = 'dismissed'
            _write_cache(workspace_id, 'recommendations', data)
            return {'ok': True}
    return {'ok': False, 'error': 'Recommendation not found'}


# ── Rule engines ──────────────────────────────────────────────────────────────

def _recs_from_email_performance(email_data: dict) -> list:
    recs = []
    campaigns = email_data.get('campaigns', [])

    for c in campaigns:
        name     = c.get('name', 'Unknown campaign')
        opens    = c.get('open_rate', 0)
        replies  = c.get('reply_rate', 0)
        bounces  = c.get('bounce_rate', 0)
        sent     = c.get('emails_sent', 0)

        if sent < 5:
            continue  # not enough data

        if opens < THRESHOLDS['open_rate_low']:
            recs.append({
                'title':        f'Low open rate on "{name}"',
                'priority':     'high',
                'category':     'email',
                'finding':      f'Open rate is {opens:.0%} (target: {THRESHOLDS["open_rate_low"]:.0%}+). Subject line is likely the issue.',
                'action':       f'Test 2–3 new subject lines on "{name}". Try personalizing with company name or a direct question. Pause current sequence after today.',
                'impact_score': 8,
                'effort':       'low',
                'metric':       'open_rate',
                'current_value': opens,
                'target_value':  THRESHOLDS['open_rate_good'],
            })

        elif opens >= THRESHOLDS['open_rate_good'] and replies < THRESHOLDS['reply_rate_low']:
            recs.append({
                'title':        f'Good opens, low replies on "{name}"',
                'priority':     'high',
                'category':     'email',
                'finding':      f'Opens are {opens:.0%} but replies are only {replies:.0%}. People are reading but not responding — body copy issue.',
                'action':       f'Rewrite the CTA in "{name}" — make it a yes/no question. Add a specific insight or proof point. Test Hormozi-style directness vs Carnegie warm approach.',
                'impact_score': 9,
                'effort':       'medium',
                'metric':       'reply_rate',
                'current_value': replies,
                'target_value':  THRESHOLDS['reply_rate_good'],
            })

        if bounces > THRESHOLDS['bounce_rate_high']:
            recs.append({
                'title':        f'High bounce rate on "{name}" — list quality issue',
                'priority':     'critical',
                'category':     'list',
                'finding':      f'Bounce rate is {bounces:.0%} on "{name}". This will hurt sender reputation and deliverability.',
                'action':       'Pause campaign immediately. Run the lead list through NeverBounce or ZeroBounce. Re-verify all emails before resuming.',
                'impact_score': 10,
                'effort':       'medium',
                'metric':       'bounce_rate',
                'current_value': bounces,
                'target_value':  THRESHOLDS['bounce_rate_high'],
            })

    return recs


def _recs_from_lead_pipeline(lead_data: dict) -> list:
    recs = []
    leads      = lead_data.get('leads', [])
    pipeline   = lead_data.get('pipeline_value', 0)
    stale_days = THRESHOLDS['stale_lead_days']

    now = datetime.now(timezone.utc)
    stale_leads = []
    for lead in leads:
        last_contact = lead.get('last_contact_date') or lead.get('created_at', '')
        if not last_contact:
            continue
        try:
            dt = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
            if (now - dt).days >= stale_days and lead.get('stage') not in ('won', 'lost'):
                stale_leads.append(lead)
        except Exception:
            pass

    if stale_leads:
        recs.append({
            'title':        f'{len(stale_leads)} leads untouched for {stale_days}+ days',
            'priority':     'high',
            'category':     'pipeline',
            'finding':      f'{len(stale_leads)} active leads have not been contacted in over {stale_days} days.',
            'action':       f'Send a breakup email sequence to all {len(stale_leads)} stale leads today. This re-engages ~5% and cleans the pipeline. Use the "breakup" template.',
            'impact_score': 7,
            'effort':       'low',
            'metric':       'stale_leads',
            'current_value': len(stale_leads),
            'target_value':  0,
        })

    if pipeline < THRESHOLDS['pipeline_low_usd']:
        recs.append({
            'title':        'Pipeline value is low — lead generation needed',
            'priority':     'critical',
            'category':     'pipeline',
            'finding':      f'Total active pipeline is ${pipeline:,.0f}, below the ${THRESHOLDS["pipeline_low_usd"]:,.0f} threshold needed to hit monthly targets.',
            'action':       'Launch an Apollo contact search today: pull 200 new ICP contacts. Set up a new Instantly sequence and launch by EOD.',
            'impact_score': 10,
            'effort':       'high',
            'metric':       'pipeline_value',
            'current_value': pipeline,
            'target_value':  THRESHOLDS['pipeline_low_usd'],
        })

    # Check for leads stuck in demo/proposal stage
    stuck = [l for l in leads if l.get('stage') in ('demo_done', 'proposal_sent')
             and l.get('last_contact_date')]
    if len(stuck) >= 3:
        recs.append({
            'title':        f'{len(stuck)} leads stuck after demo/proposal',
            'priority':     'medium',
            'category':     'pipeline',
            'finding':      f'{len(stuck)} leads have seen a demo or received a proposal but haven\'t moved forward.',
            'action':       'Send a Hormozi-style "still interested?" email to all stuck leads. Give them a 48-hour deadline. Convert or clean the pipeline.',
            'impact_score': 8,
            'effort':       'low',
            'metric':       'stuck_leads',
            'current_value': len(stuck),
            'target_value':  0,
        })

    return recs


def _recs_from_daily_volume(daily_data: dict) -> list:
    recs = []
    days = daily_data.get('days', [])
    if not days:
        return recs

    # Look at last 3 days
    recent = days[-3:] if len(days) >= 3 else days
    avg_sends = sum(d.get('emails_sent', 0) for d in recent) / len(recent)

    if avg_sends < THRESHOLDS['daily_sends_min']:
        recs.append({
            'title':        f'Email send volume critically low ({avg_sends:.0f}/day avg)',
            'priority':     'critical',
            'category':     'volume',
            'finding':      f'Average daily sends over the last {len(recent)} days: {avg_sends:.0f}. Minimum target is {THRESHOLDS["daily_sends_min"]}.',
            'action':       'Check Instantly campaign status — campaigns may be paused or exhausted. Refill lead lists or activate dormant campaigns.',
            'impact_score': 9,
            'effort':       'medium',
            'metric':       'daily_sends',
            'current_value': avg_sends,
            'target_value':  THRESHOLDS['daily_sends_target'],
        })
    elif avg_sends < THRESHOLDS['daily_sends_target']:
        recs.append({
            'title':        f'Send volume below target ({avg_sends:.0f}/day, target: {THRESHOLDS["daily_sends_target"]})',
            'priority':     'medium',
            'category':     'volume',
            'finding':      f'Sends are running at {avg_sends:.0f}/day vs target of {THRESHOLDS["daily_sends_target"]}.',
            'action':       'Add 100+ new verified leads to your active Instantly sequence. Consider running a parallel campaign to a new segment.',
            'impact_score': 6,
            'effort':       'medium',
            'metric':       'daily_sends',
            'current_value': avg_sends,
            'target_value':  THRESHOLDS['daily_sends_target'],
        })

    # Check if sends dropped suddenly
    if len(days) >= 7:
        week_avg = sum(d.get('emails_sent', 0) for d in days[-7:-3]) / 4
        if week_avg > 0 and avg_sends < week_avg * 0.6:
            recs.append({
                'title':        'Email sends dropped 40%+ vs last week',
                'priority':     'high',
                'category':     'volume',
                'finding':      f'Last 3-day avg ({avg_sends:.0f}) is 40%+ below prior week avg ({week_avg:.0f}). Something changed.',
                'action':       'Investigate: check if Instantly campaigns ran out of leads, if sending limit was hit, or if a domain was flagged. Fix before more days pass.',
                'impact_score': 8,
                'effort':       'low',
            })

    return recs


def _recs_from_meetings(meeting_data: dict) -> list:
    recs = []
    meetings      = meeting_data.get('meetings', [])
    upcoming      = meeting_data.get('upcoming', [])
    meetings_booked = meeting_data.get('meetings_booked_this_week', 0)
    replies_this_week = meeting_data.get('replies_this_week', 1)  # avoid div/0

    # Meeting rate
    meeting_rate = meetings_booked / max(replies_this_week, 1)
    if replies_this_week >= 5 and meeting_rate < THRESHOLDS['meeting_rate_low']:
        recs.append({
            'title':        'Replies not converting to meetings',
            'priority':     'high',
            'category':     'meetings',
            'finding':      f'Only {meeting_rate:.1%} of replies convert to booked meetings (target: {THRESHOLDS["meeting_rate_low"]:.1%}+).',
            'action':       'Review your reply-to-meeting follow-up sequence. Ensure you\'re sending a Calendly link in the first reply. Try offering specific times instead of a scheduling link.',
            'impact_score': 8,
            'effort':       'low',
        })

    # Upcoming meeting prep
    if upcoming:
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        tomorrow_meetings = [m for m in upcoming if m.get('start', '').startswith(tomorrow)]
        if tomorrow_meetings:
            recs.append({
                'title':        f'{len(tomorrow_meetings)} meeting(s) tomorrow — prep now',
                'priority':     'medium',
                'category':     'meetings',
                'finding':      f'You have {len(tomorrow_meetings)} meeting(s) scheduled for tomorrow.',
                'action':       'Research each attendee on LinkedIn. Review their company\'s recent news. Prepare 2-3 discovery questions. Send a confirmation email today.',
                'impact_score': 7,
                'effort':       'medium',
            })

    return recs


def _recs_workspace_specific(workspace_id: str, email_data: dict, lead_data: dict) -> list:
    """Workspace-specific rules based on business context."""
    recs = []

    if workspace_id == 'bcat_recruitment':
        # Recruiter-specific: owner-ops respond better Mon/Tue
        now = datetime.now(timezone.utc)
        if now.weekday() == 2:  # Wednesday
            recs.append({
                'title':        'Schedule bulk outreach for Monday AM',
                'priority':     'low',
                'category':     'timing',
                'finding':      'Owner-operators check messages most actively Mon-Tue before dispatch.',
                'action':       'Queue your next batch of LinkedIn messages and emails to send Monday 7-9am local time. Avoid Wed-Fri for cold outreach.',
                'impact_score': 4,
                'effort':       'low',
            })

    if workspace_id == 'best_care_sales':
        # Car dealership-specific: fleet managers are reachable Tue-Thu
        leads = lead_data.get('leads', [])
        dealership_leads = [l for l in leads if 'dealer' in l.get('industry', '').lower()
                            or 'auto' in l.get('company', '').lower()]
        if len(dealership_leads) < 20:
            recs.append({
                'title':        'Dealership lead list is thin — scrape more',
                'priority':     'medium',
                'category':     'pipeline',
                'finding':      f'Only {len(dealership_leads)} dealership leads in pipeline. Best Care targets car dealerships and remarketers.',
                'action':       'Run an Apify Google Maps scrape: query "car dealership", target cities in your service area. Pull 150+ new contacts.',
                'impact_score': 7,
                'effort':       'medium',
            })

    if workspace_id == 'bcat_sales':
        # Freight-specific: check if we're targeting high-value verticals
        leads = lead_data.get('leads', [])
        high_value = [l for l in leads if l.get('estimated_value', 0) > 5000]
        if len(high_value) < 5:
            recs.append({
                'title':        'Few high-value leads in pipeline',
                'priority':     'medium',
                'category':     'pipeline',
                'finding':      'Less than 5 leads with estimated value >$5K/mo in pipeline.',
                'action':       'Run an Apollo search targeting VP Operations and Logistics Directors at manufacturers with 50-500 employees. These accounts have higher freight volume.',
                'impact_score': 6,
                'effort':       'medium',
            })

    return recs


# ── Data loading ──────────────────────────────────────────────────────────────

def _get_email_data(workspace_id: str, use_real: bool) -> dict:
    """Load email campaign data — real (Instantly) or mock."""
    if use_real:
        try:
            from services import instantly_service as _inst
            campaigns = _inst.get_campaigns(workspace_id)
            analytics = _inst.get_analytics(workspace_id)
            normalized = []
            for c in campaigns:
                cid = c.get('id', '')
                a   = analytics.get(cid, {})
                normalized.append({
                    'name':         c.get('name', ''),
                    'emails_sent':  a.get('total_sent', 0),
                    'open_rate':    a.get('open_rate', 0) / 100 if a.get('open_rate') else 0,
                    'reply_rate':   a.get('reply_rate', 0) / 100 if a.get('reply_rate') else 0,
                    'bounce_rate':  a.get('bounce_rate', 0) / 100 if a.get('bounce_rate') else 0,
                })
            return {'campaigns': normalized}
        except Exception:
            pass

    # Fall back to mock
    try:
        import sales_data as _sd
        campaigns = _sd.get_email_campaigns(workspace_id)
        return {'campaigns': campaigns}
    except Exception:
        return {'campaigns': []}


def _get_lead_data(workspace_id: str, use_real: bool) -> dict:
    """Load lead pipeline data."""
    try:
        import sales_data as _sd
        leads = _sd.get_leads(workspace_id)
        pipeline = sum(l.get('estimated_value', 0) for l in leads
                       if l.get('stage') not in ('won', 'lost'))
        return {'leads': leads, 'pipeline_value': pipeline}
    except Exception:
        return {'leads': [], 'pipeline_value': 0}


def _get_daily_data(workspace_id: str, use_real: bool) -> dict:
    """Load daily send/reply data."""
    try:
        import sales_data as _sd
        days = _sd.get_daily_results(workspace_id)
        return {'days': days}
    except Exception:
        return {'days': []}


def _get_meeting_data(workspace_id: str, use_real: bool) -> dict:
    """Load meeting data from GCal or mock."""
    result = {'meetings': [], 'upcoming': [], 'meetings_booked_this_week': 0, 'replies_this_week': 0}
    if use_real:
        try:
            from services import gcal_service as _gcal
            summary = _gcal.get_meetings_summary(workspace_id)
            result['meetings']                = summary.get('events', [])
            result['upcoming']                = _gcal.get_upcoming(workspace_id, days=3)
            result['meetings_booked_this_week'] = summary.get('this_week', 0)
        except Exception:
            pass
    try:
        import sales_data as _sd
        meetings = _sd.get_meetings(workspace_id)
        if not result['meetings']:
            result['meetings'] = meetings
        days = _sd.get_daily_results(workspace_id)
        if days:
            recent = days[-7:]
            result['replies_this_week'] = sum(d.get('replies', 0) for d in recent)
            if not result['meetings_booked_this_week']:
                result['meetings_booked_this_week'] = sum(d.get('meetings_booked', 0) for d in recent)
    except Exception:
        pass
    return result


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
