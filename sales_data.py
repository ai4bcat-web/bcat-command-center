"""
Sales Data Layer — BCAT Command Center
Mock data for 3 sales workspaces. Replace each section with live service
calls as integrations are connected (Instantly, Apollo, Apify, Google Calendar).

Workspaces:
  bcat_sales        — BCAT Logistics outbound sales
  bcat_recruitment  — BCAT agent/driver recruitment
  best_care_sales   — Best Care Auto Transport B2B sales
"""

from datetime import date, timedelta
import random

# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_back(n: int = 30) -> list[str]:
    """Last N calendar dates, most recent first."""
    today = date(2026, 3, 10)
    return [(today - timedelta(days=i)).isoformat() for i in range(1, n + 1)]

def _months(n: int = 12) -> list[str]:
    """Last N months as YYYY-MM strings, most recent first."""
    m = date(2026, 2, 1)
    result = []
    for _ in range(n):
        result.append(m.strftime('%Y-%m'))
        # go back one month
        m = (m.replace(day=1) - timedelta(days=1)).replace(day=1)
    return result

MONTHS = _months(12)


# ── BCAT Logistics — Sales ────────────────────────────────────────────────────

_bcat_sales_daily = []
for i, d in enumerate(_days_back(30)):
    dow = date.fromisoformat(d).weekday()  # 0=Mon, 6=Sun
    is_weekend = dow >= 5
    sent = 0 if is_weekend else [145, 132, 158, 167, 124, 141, 153, 139, 162, 148,
                                   155, 143, 170, 161, 137, 148, 156, 144, 163, 152,
                                   138, 149, 165, 142, 157, 146, 168, 135, 153, 141][i % 30]
    opens       = int(sent * (0.38 + (i % 7) * 0.01))
    replies     = int(opens * (0.11 + (i % 5) * 0.005))
    pos_replies = int(replies * 0.38)
    li_sent     = 0 if is_weekend else int(sent * 0.32)
    li_replies  = int(li_sent * 0.22)
    meetings    = 1 if (pos_replies >= 3 and not is_weekend) else 0
    _bcat_sales_daily.append({
        'date':              d,
        'emails_sent':       sent,
        'opens':             opens,
        'open_rate':         round(opens / sent * 100, 1) if sent else 0,
        'replies':           replies,
        'reply_rate':        round(replies / sent * 100, 1) if sent else 0,
        'positive_replies':  pos_replies,
        'positive_rate':     round(pos_replies / sent * 100, 1) if sent else 0,
        'linkedin_sent':     li_sent,
        'linkedin_replies':  li_replies,
        'linkedin_reply_rate': round(li_replies / li_sent * 100, 1) if li_sent else 0,
        'meetings_booked':   meetings,
        'vs_target_emails':  round(sent / 150, 2) if sent else 0,
        'vs_target_replies': round(replies / 10, 2) if sent else 0,
    })

_bcat_sales = {
    'id':   'bcat_sales',
    'name': 'BCAT Logistics — Sales',
    'type': 'sales',

    'overview': {
        'kpis': {
            'leads_added_mtd':        412,
            'active_prospects':       1847,
            'emails_sent_mtd':        3824,
            'open_rate':              41.3,
            'reply_rate':             5.8,
            'positive_reply_rate':    2.1,
            'meetings_booked_mtd':    9,
            'meetings_held_mtd':      7,
            'show_rate':              77.8,
            'opp_conversion':         44.4,
            'linkedin_sent_mtd':      1240,
            'linkedin_reply_rate':    21.8,
            'pipeline_value':         None,
            'target_emails_per_day':  150,
            'target_meetings_per_week': 3,
        },
        'monthly': [
            {
                'month':              m,
                'leads_added':        [28,32,41,38,45,52,48,55,61,58,67,74][i],
                'emails_sent':        [2100,2340,2580,2720,2890,3050,3120,3280,3410,3560,3680,3824][i],
                'open_rate':          [36.2,37.8,38.5,39.1,39.8,40.2,40.6,41.0,41.1,41.2,41.3,41.3][i],
                'reply_rate':         [4.1,4.4,4.7,4.9,5.1,5.2,5.4,5.5,5.6,5.7,5.8,5.8][i],
                'positive_rate':      [1.4,1.5,1.6,1.7,1.8,1.8,1.9,2.0,2.0,2.1,2.1,2.1][i],
                'meetings_booked':    [4,5,5,6,6,7,7,8,8,9,9,9][i],
                'linkedin_sent':      [520,590,680,730,810,880,940,1010,1080,1140,1200,1240][i],
                'linkedin_replies':   [88,102,122,134,152,168,182,200,218,234,252,270][i],
            }
            for i, m in enumerate(reversed(MONTHS))
        ],
        'funnel': {
            'leads':            1847,
            'contacted':        1240,
            'opened':           512,
            'replied':          221,
            'positive':         79,
            'meetings_booked':  9,
            'meetings_held':    7,
            'opportunities':    3,
        },
    },

    'lead_lists': [
        {
            'id': 'll_bcat_01', 'name': 'Manufacturing Shippers — IL/IN/OH',
            'count': 384, 'enrolled': 312, 'source': 'Apollo',
            'persona': 'Logistics Manager / VP Supply Chain',
            'industries': ['Manufacturing', 'Distribution'],
            'created_at': '2026-01-15', 'status': 'active', 'tags': ['high-volume', 'midwest'],
        },
        {
            'id': 'll_bcat_02', 'name': 'E-Commerce Brands — $10M+ Revenue',
            'count': 218, 'enrolled': 218, 'source': 'Apollo',
            'persona': 'Operations Director / Head of Logistics',
            'industries': ['E-Commerce', 'Retail'],
            'created_at': '2026-01-28', 'status': 'active', 'tags': ['ecomm', 'high-value'],
        },
        {
            'id': 'll_bcat_03', 'name': 'Food & Beverage Shippers',
            'count': 156, 'enrolled': 0, 'source': 'Apify',
            'persona': 'Supply Chain Manager',
            'industries': ['Food & Beverage', 'CPG'],
            'created_at': '2026-03-05', 'status': 'ready', 'tags': ['new', 'F&B'],
        },
        {
            'id': 'll_bcat_04', 'name': 'Chicago-Area 3PL Partners',
            'count': 89, 'enrolled': 89, 'source': 'Manual',
            'persona': '3PL Operations',
            'industries': ['3PL', 'Warehousing'],
            'created_at': '2025-12-10', 'status': 'completed', 'tags': ['local', 'partnership'],
        },
    ],

    'leads': [
        {
            'id': 'ld_b01', 'first_name': 'Marcus', 'last_name': 'Hendricks',
            'company': 'Apex Industrial Supply', 'title': 'VP of Logistics',
            'email': 'mhendricks@apexindustrial.com', 'phone': '312-555-0182',
            'linkedin': 'linkedin.com/in/marcushendricks', 'location': 'Chicago, IL',
            'industry': 'Manufacturing', 'company_size': '250-500',
            'source': 'Apollo', 'list': 'll_bcat_01', 'status': 'replied',
            'fit_score': 92, 'persona': 'Logistics Manager',
            'last_touch': '2026-03-08', 'touches': 4, 'notes': 'Interested in spot loads. Follow up next week.',
        },
        {
            'id': 'ld_b02', 'first_name': 'Sarah', 'last_name': 'Kowalczyk',
            'company': 'LakeShore Direct', 'title': 'Operations Director',
            'email': 's.kowalczyk@lakeshoredirect.com', 'phone': '773-555-0293',
            'linkedin': 'linkedin.com/in/sarahkowalczyk', 'location': 'Evanston, IL',
            'industry': 'E-Commerce', 'company_size': '50-200',
            'source': 'Apollo', 'list': 'll_bcat_02', 'status': 'meeting_booked',
            'fit_score': 88, 'persona': 'Operations Director',
            'last_touch': '2026-03-07', 'touches': 6, 'notes': 'Meeting 3/12 at 2pm. Ships 80 loads/month.',
        },
        {
            'id': 'ld_b03', 'first_name': 'Derek', 'last_name': 'Patton',
            'company': 'Midwest Foods Group', 'title': 'Supply Chain Manager',
            'email': 'd.patton@midwestfoods.com', 'phone': '630-555-0147',
            'linkedin': 'linkedin.com/in/derekpatton', 'location': 'Naperville, IL',
            'industry': 'Food & Beverage', 'company_size': '500-1000',
            'source': 'Apify', 'list': 'll_bcat_03', 'status': 'new',
            'fit_score': 79, 'persona': 'Supply Chain Manager',
            'last_touch': None, 'touches': 0, 'notes': '',
        },
        {
            'id': 'ld_b04', 'first_name': 'Priya', 'last_name': 'Nair',
            'company': 'TechBox Commerce', 'title': 'Head of Operations',
            'email': 'pnair@techboxcommerce.com', 'phone': None,
            'linkedin': 'linkedin.com/in/priyanair', 'location': 'Schaumburg, IL',
            'industry': 'E-Commerce', 'company_size': '50-200',
            'source': 'Apollo', 'list': 'll_bcat_02', 'status': 'positive_reply',
            'fit_score': 85, 'persona': 'Operations Director',
            'last_touch': '2026-03-09', 'touches': 3, 'notes': 'Loves the rate guarantee offer. Wants pricing call.',
        },
    ],

    'email_campaigns': [
        {
            'id': 'ec_b01', 'name': 'Manufacturing Shippers — Midwest Q1',
            'status': 'active', 'source': 'Instantly',
            'list': 'll_bcat_01', 'leads_enrolled': 312, 'leads_active': 210,
            'sequence_steps': [
                {'step': 1, 'type': 'email', 'day': 0,  'subject': 'Quick question about your shipping volume', 'opens': 156, 'replies': 22, 'style': 'carnegie'},
                {'step': 2, 'type': 'email', 'day': 3,  'subject': 'Following up — freight broker that guarantees rates', 'opens': 89,  'replies': 11, 'style': 'hormozi'},
                {'step': 3, 'type': 'email', 'day': 7,  'subject': 'One thing most shippers never know about spot rates', 'opens': 62,  'replies': 7,  'style': 'value'},
                {'step': 4, 'type': 'email', 'day': 14, 'subject': 'Last note — wanted to leave this with you', 'opens': 38,  'replies': 4,  'style': 'breakup'},
            ],
            'metrics': {
                'sent': 1248, 'opens': 516, 'replies': 72, 'positive_replies': 28,
                'open_rate': 41.3, 'reply_rate': 5.8, 'positive_rate': 2.2,
                'meetings_booked': 5, 'unsubscribes': 8, 'bounces': 3,
            },
            'started_at': '2026-01-20', 'last_send': '2026-03-09',
        },
        {
            'id': 'ec_b02', 'name': 'E-Commerce Brands — Value Stack',
            'status': 'active', 'source': 'Instantly',
            'list': 'll_bcat_02', 'leads_enrolled': 218, 'leads_active': 148,
            'sequence_steps': [
                {'step': 1, 'type': 'email', 'day': 0,  'subject': 'Saving $4,200/month on freight — is that interesting?', 'opens': 61,  'replies': 16, 'style': 'hormozi'},
                {'step': 2, 'type': 'email', 'day': 4,  'subject': 'Re: freight savings for {{company}}', 'opens': 41,  'replies': 9,  'style': 'hormozi'},
                {'step': 3, 'type': 'email', 'day': 10, 'subject': 'Quick win for your shipping ops', 'opens': 28,  'replies': 5,  'style': 'carnegie'},
            ],
            'metrics': {
                'sent': 654, 'opens': 203, 'replies': 56, 'positive_replies': 24,
                'open_rate': 31.0, 'reply_rate': 8.6, 'positive_rate': 3.7,
                'meetings_booked': 4, 'unsubscribes': 4, 'bounces': 6,
            },
            'started_at': '2026-02-03', 'last_send': '2026-03-09',
            'note': 'Low open rate — subject line issue. When they do open, reply rate is excellent.',
        },
    ],

    'linkedin_campaigns': [
        {
            'id': 'li_b01', 'name': 'Supply Chain Managers — LinkedIn',
            'status': 'active', 'tool': 'Manual / Sales Navigator',
            'persona': 'Supply Chain / Logistics Managers',
            'connection_requests_sent': 340, 'connections_accepted': 108, 'acceptance_rate': 31.8,
            'messages_sent': 108, 'replies': 47, 'positive_replies': 19, 'meetings_booked': 4,
            'reply_rate': 43.5, 'positive_rate': 17.6,
            'sequence': [
                {'step': 1, 'type': 'connection', 'message': 'Hi {{first_name}}, I work with logistics teams at manufacturers like {{company}}. Would love to connect.'},
                {'step': 2, 'type': 'message', 'day': 3, 'message': 'Thanks for connecting, {{first_name}}. Quick question — are you managing spot loads in-house or using a broker currently?'},
                {'step': 3, 'type': 'message', 'day': 8, 'message': 'One thing we hear often from ops teams at companies like {{company}} is that rates are inconsistent. We built a model that guarantees consistency. Worth a 15-minute look?'},
            ],
            'started_at': '2026-01-10',
        },
    ],

    'meetings': [
        {'id': 'mt_b01', 'prospect': 'Sarah Kowalczyk', 'company': 'LakeShore Direct', 'source': 'email',
         'campaign': 'ec_b01', 'date': '2026-03-12', 'time': '14:00', 'status': 'upcoming',
         'outcome': None, 'notes': 'Ships 80 loads/month. Decision maker.', 'cal_event_id': None},
        {'id': 'mt_b02', 'prospect': 'Marcus Hendricks', 'company': 'Apex Industrial Supply', 'source': 'email',
         'campaign': 'ec_b01', 'date': '2026-03-14', 'time': '10:00', 'status': 'upcoming',
         'outcome': None, 'notes': 'Interested in spot rate program.', 'cal_event_id': None},
        {'id': 'mt_b03', 'prospect': 'James Ortega', 'company': 'Tri-State Distribution', 'source': 'linkedin',
         'campaign': 'li_b01', 'date': '2026-03-07', 'time': '11:00', 'status': 'held',
         'outcome': 'opportunity', 'notes': 'Strong fit. Sent proposal. FU 3/14.', 'cal_event_id': None},
        {'id': 'mt_b04', 'prospect': 'Leah Zimmerman', 'company': 'Clearwater CPG', 'source': 'email',
         'campaign': 'ec_b02', 'date': '2026-03-05', 'time': '09:00', 'status': 'held',
         'outcome': 'no_decision', 'notes': 'Needs budget approval. Re-engage Q2.', 'cal_event_id': None},
        {'id': 'mt_b05', 'prospect': 'Ramon Delgado', 'company': 'UrbanShip LLC', 'source': 'linkedin',
         'campaign': 'li_b01', 'date': '2026-03-04', 'time': '15:30', 'status': 'no_show',
         'outcome': None, 'notes': 'No-show. Sent reschedule. No response.', 'cal_event_id': None},
    ],

    'daily_results': _bcat_sales_daily,

    'message_templates': [
        {
            'id': 'mt_tmpl_01', 'name': 'First Touch — Logistics Manager (Carnegie)',
            'style': 'carnegie', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'Quick question about your shipping volume, {{first_name}}',
            'body': """Hi {{first_name}},

I came across {{company}} while researching logistics teams in {{location}} — impressive operation.

Quick question: are you managing your spot freight in-house, or do you work with outside brokers currently?

I ask because we've helped a few {{industry}} companies nearby lock in more consistent rates on their regular lanes — and I wanted to see if a quick conversation would make sense for your team.

No pitch, just a 10-minute call to see if what we do could actually help.

Worth a quick chat?

Best,
[Name]""",
            'performance': {'open_rate': 43.1, 'reply_rate': 6.2, 'meetings': 5},
        },
        {
            'id': 'mt_tmpl_02', 'name': 'First Touch — Logistics Manager (Hormozi)',
            'style': 'hormozi', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'Saving $4,200/month on freight — is that interesting?',
            'body': """{{first_name}},

We work with {{industry}} companies shipping similar volume to {{company}}.

Average result: $4,200/month saved on freight — no carrier switching, no disruption to your current ops.

Here's how: we cover your lanes with guaranteed rates and consolidate spot load pricing so you're never paying peak market on lanes you run regularly.

If that's interesting, I can pull together a lane-by-lane estimate in under 20 minutes.

Worth a quick look?

[Name]""",
            'performance': {'open_rate': 31.0, 'reply_rate': 8.6, 'meetings': 4},
        },
        {
            'id': 'mt_tmpl_03', 'name': 'Follow-Up Day 3 (Carnegie)',
            'style': 'carnegie', 'goal': 'follow_up', 'channel': 'email',
            'subject': 'Following up — {{company}}',
            'body': """Hi {{first_name}},

Just following up on my note from earlier this week.

I know your inbox is full — no pressure at all. I just wanted to make sure my message didn't get lost before I stop sending.

If now isn't a good time, a simple "not now" works too. I'd rather know than keep reaching out at the wrong moment.

[Name]""",
            'performance': {'open_rate': 38.5, 'reply_rate': 5.1, 'meetings': 2},
        },
        {
            'id': 'mt_tmpl_04', 'name': 'LinkedIn Connection Request',
            'style': 'carnegie', 'goal': 'cold_outreach', 'channel': 'linkedin',
            'subject': None,
            'body': 'Hi {{first_name}}, I work with logistics teams at manufacturers in {{location}}. Would love to connect and see if there\'s a fit.',
            'performance': {'acceptance_rate': 31.8, 'reply_rate': 43.5, 'meetings': 4},
        },
        {
            'id': 'mt_tmpl_05', 'name': 'Breakup Email',
            'style': 'concise', 'goal': 'breakup', 'channel': 'email',
            'subject': 'Last note from me',
            'body': """{{first_name}},

I've reached out a few times and haven't heard back — so I'll assume the timing isn't right.

I won't reach out again, but if freight ever becomes a priority, I'm happy to pick this up then.

Take care,
[Name]""",
            'performance': {'open_rate': 48.2, 'reply_rate': 7.3, 'meetings': 1},
        },
    ],

    'recommendations': [
        {
            'id': 'rec_bs_01', 'priority': 'high', 'category': 'email',
            'title': 'Campaign ec_b02 Open Rate 31% — Test 3 New Subject Lines Today',
            'rationale': 'E-Commerce campaign reply rate (8.6%) is excellent when leads open. The bottleneck is opens (31% vs 41% benchmark). Test subject lines focused on curiosity and specificity.',
            'metric_trigger': 'open_rate < 35%', 'campaign': 'ec_b02',
            'expected_impact': 'Improving opens to 41% = ~20 more opened emails/day = ~4 more replies/week',
            'action_type': 'swap_subject', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
            'suggested_variants': [
                'One thing most e-commerce ops directors get wrong about freight',
                '{{company}} ships how many loads per month? (quick question)',
                'Real numbers: what your competitors pay vs what you pay',
            ],
        },
        {
            'id': 'rec_bs_02', 'priority': 'high', 'category': 'volume',
            'title': 'LinkedIn Volume Below Target — Increase to 60 Connections/Day',
            'rationale': 'LinkedIn positive reply rate (17.6%) and meeting rate from LinkedIn are outperforming email on a per-touch basis. Currently sending ~40/day. Increasing to 60 adds ~8 more monthly positive replies.',
            'metric_trigger': 'linkedin_volume < target', 'campaign': 'li_b01',
            'expected_impact': '+2-3 meetings/month at current conversion rate',
            'action_type': 'increase_volume', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
        },
        {
            'id': 'rec_bs_03', 'priority': 'medium', 'category': 'targeting',
            'title': 'Launch F&B Shippers List — 156 Leads Ready to Enroll',
            'rationale': 'Food & Beverage list is built and staged but not enrolled in any campaign. Based on manufacturing campaign performance, expect similar 41% open / 5.8% reply metrics.',
            'metric_trigger': 'unenrolled_list_ready', 'campaign': None,
            'expected_impact': '+3-5 meetings over 6-week campaign cycle',
            'action_type': 'enroll_list', 'confidence': 'MEDIUM', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
        },
    ],

    'activity_log': [
        {'date': '2026-03-09', 'type': 'send',   'description': '141 emails sent across 2 active campaigns'},
        {'date': '2026-03-09', 'type': 'reply',  'description': '8 email replies received (3 positive)'},
        {'date': '2026-03-09', 'type': 'book',   'description': 'Meeting booked: Sarah Kowalczyk — LakeShore Direct'},
        {'date': '2026-03-08', 'type': 'send',   'description': '148 emails sent'},
        {'date': '2026-03-07', 'type': 'meeting','description': 'Meeting held: James Ortega — Tri-State Distribution → Opportunity'},
    ],
}


# ── BCAT Logistics — Agent Recruitment ───────────────────────────────────────

_bcat_rec_daily = []
for i, d in enumerate(_days_back(30)):
    dow = date.fromisoformat(d).weekday()
    is_weekend = dow >= 5
    sent = 0 if is_weekend else [82, 76, 91, 88, 79, 84, 87, 81, 94, 86,
                                   90, 83, 96, 89, 77, 85, 92, 80, 95, 84,
                                   78, 86, 93, 82, 88, 76, 91, 85, 89, 83][i % 30]
    opens       = int(sent * (0.44 + (i % 6) * 0.01))
    replies     = int(opens * (0.22 + (i % 4) * 0.01))  # higher — operators are active searchers
    pos_replies = int(replies * 0.45)
    li_sent     = 0 if is_weekend else int(sent * 0.28)
    li_replies  = int(li_sent * 0.31)
    meetings    = 1 if pos_replies >= 2 else 0
    _bcat_rec_daily.append({
        'date': d, 'emails_sent': sent, 'opens': opens,
        'open_rate': round(opens / sent * 100, 1) if sent else 0,
        'replies': replies, 'reply_rate': round(replies / sent * 100, 1) if sent else 0,
        'positive_replies': pos_replies,
        'positive_rate': round(pos_replies / sent * 100, 1) if sent else 0,
        'linkedin_sent': li_sent, 'linkedin_replies': li_replies,
        'linkedin_reply_rate': round(li_replies / li_sent * 100, 1) if li_sent else 0,
        'meetings_booked': meetings,
    })

_bcat_recruitment = {
    'id':   'bcat_recruitment',
    'name': 'BCAT Logistics — Agent Recruitment',
    'type': 'recruitment',

    'overview': {
        'kpis': {
            'leads_added_mtd':         187,
            'active_prospects':         624,
            'emails_sent_mtd':         1820,
            'open_rate':               47.2,
            'reply_rate':              10.8,
            'positive_reply_rate':      4.9,
            'meetings_booked_mtd':      6,
            'meetings_held_mtd':        5,
            'show_rate':               83.3,
            'recruits_onboarded_mtd':   2,
            'linkedin_sent_mtd':       480,
            'linkedin_reply_rate':     28.1,
            'target_recruits_per_month': 5,
            'target_emails_per_day':   80,
        },
        'monthly': [
            {
                'month':             m,
                'leads_added':       [14,18,22,19,24,28,26,31,34,29,38,42][i],
                'emails_sent':       [980,1100,1240,1320,1450,1560,1620,1700,1760,1800,1810,1820][i],
                'open_rate':         [40.1,41.5,42.8,43.6,44.2,44.9,45.4,45.8,46.2,46.6,46.9,47.2][i],
                'reply_rate':        [7.2,7.8,8.3,8.7,9.0,9.4,9.7,10.0,10.2,10.4,10.6,10.8][i],
                'recruits_onboarded':[0,1,1,1,1,2,2,2,2,2,2,2][i],
                'meetings_booked':   [2,3,3,3,4,4,4,5,5,5,6,6][i],
            }
            for i, m in enumerate(reversed(MONTHS))
        ],
        'funnel': {
            'leads':           624,
            'contacted':       488,
            'opened':          230,
            'replied':         117,
            'positive':         53,
            'calls_booked':      6,
            'calls_held':        5,
            'onboarded':         2,
        },
    },

    'lead_lists': [
        {
            'id': 'll_rec_01', 'name': 'Owner-Operators — Midwest Dry Van',
            'count': 241, 'enrolled': 241, 'source': 'Apify + Manual',
            'persona': 'Owner-Operator / Small Fleet (1-3 trucks)',
            'equipment': ['Dry Van 53\'', 'Reefer'],
            'lanes': ['IL', 'IN', 'OH', 'MI', 'WI'],
            'created_at': '2026-01-08', 'status': 'active', 'tags': ['midwest', 'dry-van'],
        },
        {
            'id': 'll_rec_02', 'name': 'CDL Drivers — Actively Looking',
            'count': 183, 'enrolled': 183, 'source': 'Apify',
            'persona': 'CDL-A Driver — Looking for better opportunities',
            'equipment': ['Dry Van', 'Flatbed'],
            'lanes': ['Nationwide'],
            'created_at': '2026-02-01', 'status': 'active', 'tags': ['drivers', 'high-intent'],
        },
        {
            'id': 'll_rec_03', 'name': 'Amazon Relay Drivers — Tier 1',
            'count': 128, 'enrolled': 0, 'source': 'Apify',
            'persona': 'Amazon DSP / Relay Drivers — looking for more loads',
            'equipment': ['Sprinter', 'Box Truck'],
            'lanes': ['IL Metro'],
            'created_at': '2026-03-08', 'status': 'ready', 'tags': ['amazon', 'last-mile'],
        },
    ],

    'leads': [
        {
            'id': 'ld_r01', 'first_name': 'Tony', 'last_name': 'Marchetti',
            'company': 'Self / Owner-Operator', 'title': 'Owner-Operator',
            'email': 'tony.marchetti.truck@gmail.com', 'phone': '708-555-0261',
            'linkedin': None, 'location': 'Joliet, IL',
            'industry': 'Trucking', 'company_size': '1',
            'equipment': 'Dry Van 53\'', 'lanes': 'IL/IN/OH',
            'source': 'Apify', 'list': 'll_rec_01', 'status': 'call_booked',
            'fit_score': 94, 'persona': 'Owner-Operator',
            'last_touch': '2026-03-09', 'touches': 5,
            'recruitment_stage': 'qualification', 'notes': 'Runs 3 trucks, looking for consistent loads. Call 3/11.',
        },
        {
            'id': 'ld_r02', 'first_name': 'Darrell', 'last_name': 'Washington',
            'company': 'Washington Freight LLC', 'title': 'Owner-Operator / Fleet',
            'email': 'd.washington@washingtonfreight.com', 'phone': '219-555-0384',
            'linkedin': None, 'location': 'Hammond, IN',
            'industry': 'Trucking', 'company_size': '3',
            'equipment': 'Dry Van', 'lanes': 'IN/OH/PA',
            'source': 'Manual', 'list': 'll_rec_01', 'status': 'replied',
            'fit_score': 88, 'persona': 'Small Fleet Owner',
            'last_touch': '2026-03-08', 'touches': 3,
            'recruitment_stage': 'nurture', 'notes': 'Has 3 trucks. Reply: interested in learning more about rates.',
        },
    ],

    'email_campaigns': [
        {
            'id': 'ec_r01', 'name': 'Owner-Operators — Midwest Lanes',
            'status': 'active', 'source': 'Instantly',
            'list': 'll_rec_01', 'leads_enrolled': 241, 'leads_active': 180,
            'sequence_steps': [
                {'step': 1, 'type': 'email', 'day': 0,  'subject': 'More consistent loads for your route — quick question', 'opens': 118, 'replies': 38, 'style': 'carnegie'},
                {'step': 2, 'type': 'email', 'day': 4,  'subject': 'What owner-operators tell us about load boards', 'opens': 74,  'replies': 19, 'style': 'value'},
                {'step': 3, 'type': 'email', 'day': 10, 'subject': 'One specific thing we do differently', 'opens': 51,  'replies': 12, 'style': 'hormozi'},
                {'step': 4, 'type': 'email', 'day': 18, 'subject': 'Last reach out — leaving the door open', 'opens': 32,  'replies': 8,  'style': 'breakup'},
            ],
            'metrics': {
                'sent': 964, 'opens': 455, 'replies': 104, 'positive_replies': 47,
                'open_rate': 47.2, 'reply_rate': 10.8, 'positive_rate': 4.9,
                'meetings_booked': 6, 'unsubscribes': 6, 'bounces': 4,
            },
            'started_at': '2026-01-15', 'last_send': '2026-03-09',
        },
    ],

    'linkedin_campaigns': [
        {
            'id': 'li_r01', 'name': 'Owner-Ops — LinkedIn + Facebook Groups',
            'status': 'active', 'tool': 'Manual',
            'persona': 'Owner-Operators and Small Fleet Owners',
            'connection_requests_sent': 180, 'connections_accepted': 64, 'acceptance_rate': 35.6,
            'messages_sent': 64, 'replies': 36, 'positive_replies': 18, 'meetings_booked': 3,
            'reply_rate': 56.3, 'positive_rate': 28.1,
            'sequence': [
                {'step': 1, 'type': 'connection', 'message': 'Hey {{first_name}}, fellow trucking industry — would love to connect and share some load info your way.'},
                {'step': 2, 'type': 'message', 'day': 2, 'message': 'Thanks for connecting. Quick question — are you finding enough consistent loads on your preferred lanes right now?'},
            ],
            'started_at': '2026-02-01',
        },
    ],

    'meetings': [
        {'id': 'mt_r01', 'prospect': 'Tony Marchetti', 'company': 'Owner-Operator', 'source': 'email',
         'campaign': 'ec_r01', 'date': '2026-03-11', 'time': '10:00', 'status': 'upcoming',
         'outcome': None, 'notes': '3 trucks, IL/IN/OH lanes. Pre-qualified.'},
        {'id': 'mt_r02', 'prospect': 'Greg Flores', 'company': 'Flores Freight LLC', 'source': 'linkedin',
         'campaign': 'li_r01', 'date': '2026-03-06', 'time': '14:00', 'status': 'held',
         'outcome': 'onboarded', 'notes': 'Onboarded. First load assigned 3/10.'},
        {'id': 'mt_r03', 'prospect': 'Mike Szabo', 'company': 'Owner-Operator', 'source': 'email',
         'campaign': 'ec_r01', 'date': '2026-03-04', 'time': '11:00', 'status': 'held',
         'outcome': 'onboarded', 'notes': 'Onboarded. Running Chicago-Columbus lane.'},
    ],

    'daily_results': _bcat_rec_daily,

    'message_templates': [
        {
            'id': 'mt_rec_01', 'name': 'First Touch — Owner-Operator (Carnegie)',
            'style': 'carnegie', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'More consistent loads for your route — quick question',
            'body': """Hey {{first_name}},

I saw you're running {{lanes}} lanes out of {{location}} — that's exactly the corridor we're most active in right now.

Quick question: are you finding enough consistent volume on those lanes, or is it a mix of load board scrambling and gaps?

We work with owner-ops in the Midwest who want consistent loads without chasing boards every morning. If that sounds familiar, I'd love to share what a few of them told us helped most.

Worth a 10-minute call?

[Name]""",
            'performance': {'open_rate': 47.2, 'reply_rate': 10.8, 'meetings': 6},
        },
        {
            'id': 'mt_rec_02', 'name': 'First Touch — Owner-Operator (Hormozi)',
            'style': 'hormozi', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'Guaranteed loads on your preferred lanes — interested?',
            'body': """{{first_name}},

We guarantee consistent freight on {{lanes}} dry van lanes — minimum 3 loads/week, at rates 8-12% above average load board for comparable lanes.

No spot hunting. No rate surprises. You tell us your lanes, we fill them.

If you're running under capacity right now or tired of load board inconsistency, worth a 10-minute call to see if we're a fit.

[Name]""",
            'performance': {'open_rate': 42.1, 'reply_rate': 12.3, 'meetings': 4},
        },
    ],

    'recommendations': [
        {
            'id': 'rec_br_01', 'priority': 'high', 'category': 'list',
            'title': 'Enroll Amazon Relay List — 128 High-Intent Leads Ready',
            'rationale': 'Amazon Relay/DSP drivers actively seek supplemental loads. List built, not enrolled. Based on owner-op campaign, expect 45-50% opens and 10-12% replies.',
            'metric_trigger': 'unenrolled_list', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
            'expected_impact': '+2 recruits/month at current conversion rate',
        },
        {
            'id': 'rec_br_02', 'priority': 'medium', 'category': 'linkedin',
            'title': 'Increase LinkedIn Volume — Outperforming Email (56% reply rate)',
            'rationale': 'LinkedIn reply rate for owner-ops (56%) far exceeds email (10.8%). Currently sending 25/day. Increase to 40 with slight message tweak.',
            'metric_trigger': 'linkedin_outperforming', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
            'expected_impact': '+1-2 recruits/month',
        },
    ],

    'activity_log': [
        {'date': '2026-03-09', 'type': 'send',    'description': '83 emails sent — Owner-Operator campaign'},
        {'date': '2026-03-09', 'type': 'reply',   'description': '9 replies (4 positive)'},
        {'date': '2026-03-08', 'type': 'book',    'description': 'Recruiter call booked: Tony Marchetti'},
        {'date': '2026-03-06', 'type': 'meeting', 'description': 'Greg Flores — Onboarded. First load 3/10.'},
    ],
}


# ── Best Care Auto Transport — Sales ──────────────────────────────────────────

_bc_sales_daily = []
for i, d in enumerate(_days_back(30)):
    dow = date.fromisoformat(d).weekday()
    is_weekend = dow >= 5
    sent = 0 if is_weekend else [98, 112, 105, 118, 94, 108, 121, 103, 115, 126,
                                   107, 119, 113, 124, 98, 110, 122, 106, 117, 129,
                                   103, 114, 121, 108, 118, 101, 115, 109, 120, 111][i % 30]
    opens       = int(sent * (0.39 + (i % 7) * 0.008))
    replies     = int(opens * (0.09 + (i % 5) * 0.006))
    pos_replies = int(replies * 0.35)
    li_sent     = 0 if is_weekend else int(sent * 0.25)
    li_replies  = int(li_sent * 0.19)
    meetings    = 1 if pos_replies >= 2 else 0
    _bc_sales_daily.append({
        'date': d, 'emails_sent': sent, 'opens': opens,
        'open_rate': round(opens / sent * 100, 1) if sent else 0,
        'replies': replies, 'reply_rate': round(replies / sent * 100, 1) if sent else 0,
        'positive_replies': pos_replies,
        'positive_rate': round(pos_replies / sent * 100, 1) if sent else 0,
        'linkedin_sent': li_sent, 'linkedin_replies': li_replies,
        'linkedin_reply_rate': round(li_replies / li_sent * 100, 1) if li_sent else 0,
        'meetings_booked': meetings,
    })

_best_care_sales = {
    'id':   'best_care_sales',
    'name': 'Best Care Auto Transport — Sales',
    'type': 'sales',

    'overview': {
        'kpis': {
            'leads_added_mtd':        298,
            'active_prospects':       1124,
            'emails_sent_mtd':        2640,
            'open_rate':              40.8,
            'reply_rate':             4.9,
            'positive_reply_rate':    1.7,
            'meetings_booked_mtd':    7,
            'meetings_held_mtd':      5,
            'show_rate':              71.4,
            'opp_conversion':         40.0,
            'linkedin_sent_mtd':      640,
            'linkedin_reply_rate':    17.2,
            'pipeline_value':         87500,
            'target_emails_per_day':  120,
            'target_meetings_per_week': 3,
        },
        'monthly': [
            {
                'month':           m,
                'leads_added':     [18,22,28,24,32,36,33,40,44,41,48,54][i],
                'emails_sent':     [1400,1580,1740,1860,1980,2100,2180,2280,2360,2440,2540,2640][i],
                'open_rate':       [35.8,36.9,37.8,38.4,39.0,39.4,39.7,40.0,40.2,40.4,40.6,40.8][i],
                'reply_rate':      [3.4,3.7,3.9,4.1,4.2,4.4,4.5,4.6,4.7,4.8,4.8,4.9][i],
                'meetings_booked': [3,3,4,4,4,5,5,5,6,6,7,7][i],
                'pipeline_value':  [24000,28000,33000,38000,44000,51000,58000,64000,70000,76000,82000,87500][i],
            }
            for i, m in enumerate(reversed(MONTHS))
        ],
        'funnel': {
            'leads':           1124,
            'contacted':        820,
            'opened':           334,
            'replied':          129,
            'positive':          44,
            'meetings_booked':    7,
            'meetings_held':      5,
            'opportunities':      2,
        },
    },

    'lead_lists': [
        {
            'id': 'll_bc_01', 'name': 'Car Dealerships — Chicago Metro (50+ unit/mo)',
            'count': 186, 'enrolled': 186, 'source': 'Apollo + Apify',
            'persona': 'Dealer Principal / GM / Fleet Manager',
            'industries': ['Automotive Retail'],
            'created_at': '2026-01-20', 'status': 'active', 'tags': ['dealerships', 'chicago', 'high-value'],
        },
        {
            'id': 'll_bc_02', 'name': 'Corporate Fleet Relocation — HR / Benefits',
            'count': 124, 'enrolled': 124, 'source': 'Apollo',
            'persona': 'HR Director / Fleet Manager / Mobility Lead',
            'industries': ['Corporate', 'Financial Services', 'Healthcare'],
            'created_at': '2026-02-05', 'status': 'active', 'tags': ['corporate', 'relocation'],
        },
        {
            'id': 'll_bc_03', 'name': 'Auto Auction Houses — Midwest',
            'count': 67, 'enrolled': 0, 'source': 'Manual',
            'persona': 'Operations Manager / Transport Coordinator',
            'industries': ['Auto Auction'],
            'created_at': '2026-03-06', 'status': 'ready', 'tags': ['auctions', 'high-volume'],
        },
    ],

    'leads': [
        {
            'id': 'ld_bc01', 'first_name': 'Craig', 'last_name': 'Vosberg',
            'company': 'Vosberg Auto Group', 'title': 'Dealer Principal',
            'email': 'craig@vosbergauto.com', 'phone': '847-555-0291',
            'linkedin': 'linkedin.com/in/craigvosberg', 'location': 'Arlington Heights, IL',
            'industry': 'Automotive Retail', 'company_size': '50-200',
            'source': 'Apollo', 'list': 'll_bc_01', 'status': 'meeting_booked',
            'fit_score': 96, 'persona': 'Dealer Principal',
            'last_touch': '2026-03-08', 'touches': 5,
            'notes': 'Moves 80+ units/month. Meeting 3/13. Very interested in dedicated account pricing.',
        },
        {
            'id': 'ld_bc02', 'first_name': 'Tamara', 'last_name': 'Blankenship',
            'company': 'Midway Financial Group', 'title': 'Corporate Fleet Director',
            'email': 't.blankenship@midwayfinancial.com', 'phone': None,
            'linkedin': 'linkedin.com/in/tamarablankenship', 'location': 'Oak Brook, IL',
            'industry': 'Financial Services', 'company_size': '1000+',
            'source': 'Apollo', 'list': 'll_bc_02', 'status': 'positive_reply',
            'fit_score': 89, 'persona': 'Fleet Manager',
            'last_touch': '2026-03-09', 'touches': 3,
            'notes': 'Manages relocation for 200+ employees/year. Responded: "Tell me more."',
        },
    ],

    'email_campaigns': [
        {
            'id': 'ec_bc01', 'name': 'Auto Dealerships — Dedicated Account Offer',
            'status': 'active', 'source': 'Instantly',
            'list': 'll_bc_01', 'leads_enrolled': 186, 'leads_active': 130,
            'sequence_steps': [
                {'step': 1, 'type': 'email', 'day': 0,  'subject': 'Dedicated transport account for {{company}} — quick question', 'opens': 82, 'replies': 18, 'style': 'carnegie'},
                {'step': 2, 'type': 'email', 'day': 4,  'subject': 'What dealers tell us about their transport headaches', 'opens': 54, 'replies': 9,  'style': 'value'},
                {'step': 3, 'type': 'email', 'day': 9,  'subject': 'One number that changes how dealers think about transport', 'opens': 37, 'replies': 6,  'style': 'hormozi'},
                {'step': 4, 'type': 'email', 'day': 18, 'subject': 'Last note — leaving this with you', 'opens': 24, 'replies': 3,  'style': 'breakup'},
            ],
            'metrics': {
                'sent': 744, 'opens': 303, 'replies': 51, 'positive_replies': 18,
                'open_rate': 40.7, 'reply_rate': 6.9, 'positive_rate': 2.4,
                'meetings_booked': 5, 'unsubscribes': 5, 'bounces': 7,
            },
            'started_at': '2026-01-25', 'last_send': '2026-03-09',
        },
        {
            'id': 'ec_bc02', 'name': 'Corporate Fleet Relocation',
            'status': 'active', 'source': 'Instantly',
            'list': 'll_bc_02', 'leads_enrolled': 124, 'leads_active': 90,
            'sequence_steps': [
                {'step': 1, 'type': 'email', 'day': 0,  'subject': 'Vehicle relocation for {{company}} employees — do you outsource this?', 'opens': 51, 'replies': 7, 'style': 'carnegie'},
                {'step': 2, 'type': 'email', 'day': 5,  'subject': 'Most HR teams handle this 2 different ways — which are you?', 'opens': 31, 'replies': 4, 'style': 'value'},
            ],
            'metrics': {
                'sent': 372, 'opens': 143, 'replies': 27, 'positive_replies': 10,
                'open_rate': 38.4, 'reply_rate': 7.3, 'positive_rate': 2.7,
                'meetings_booked': 2, 'unsubscribes': 2, 'bounces': 5,
            },
            'started_at': '2026-02-10', 'last_send': '2026-03-09',
        },
    ],

    'linkedin_campaigns': [
        {
            'id': 'li_bc01', 'name': 'Dealer Principals — LinkedIn',
            'status': 'active', 'tool': 'Manual / Sales Navigator',
            'persona': 'Dealer Principals and GM / Sales Directors',
            'connection_requests_sent': 220, 'connections_accepted': 68, 'acceptance_rate': 30.9,
            'messages_sent': 68, 'replies': 22, 'positive_replies': 9, 'meetings_booked': 2,
            'reply_rate': 32.4, 'positive_rate': 13.2,
            'sequence': [
                {'step': 1, 'type': 'connection', 'message': 'Hi {{first_name}}, I work with auto dealers in the Chicago area on vehicle transport. Would love to connect.'},
                {'step': 2, 'type': 'message', 'day': 3, 'message': 'Thanks for connecting, {{first_name}}. Quick question — are you using one transport company for all your moves, or managing multiple carriers?'},
            ],
            'started_at': '2026-01-20',
        },
    ],

    'meetings': [
        {'id': 'mt_bc01', 'prospect': 'Craig Vosberg', 'company': 'Vosberg Auto Group', 'source': 'email',
         'campaign': 'ec_bc01', 'date': '2026-03-13', 'time': '11:00', 'status': 'upcoming',
         'outcome': None, 'notes': '80+ units/month. Wants dedicated account pricing.'},
        {'id': 'mt_bc02', 'prospect': 'Linda Park', 'company': 'Park Automotive Group', 'source': 'linkedin',
         'campaign': 'li_bc01', 'date': '2026-03-11', 'time': '09:30', 'status': 'upcoming',
         'outcome': None, 'notes': '3 rooftops. Using multiple carriers. Pain point: coordination.'},
        {'id': 'mt_bc03', 'prospect': 'Robert Simone', 'company': 'North Shore Lexus', 'source': 'email',
         'campaign': 'ec_bc01', 'date': '2026-03-06', 'time': '10:00', 'status': 'held',
         'outcome': 'opportunity', 'notes': 'Proposal sent. $4,200/mo estimated contract. FU 3/13.'},
        {'id': 'mt_bc04', 'prospect': 'Anna Kovacs', 'company': 'Lakefront Audi', 'source': 'email',
         'campaign': 'ec_bc01', 'date': '2026-03-03', 'time': '14:00', 'status': 'no_show',
         'outcome': None, 'notes': 'No-show. LinkedIn follow-up sent. No response.'},
        {'id': 'mt_bc05', 'prospect': 'Jason Morrow', 'company': 'Morrow Fleet Solutions', 'source': 'email',
         'campaign': 'ec_bc02', 'date': '2026-03-01', 'time': '11:00', 'status': 'held',
         'outcome': 'no_decision', 'notes': 'Uses internal driver. Not ready yet. Re-engage Q3.'},
    ],

    'daily_results': _bc_sales_daily,

    'message_templates': [
        {
            'id': 'mt_bc_01', 'name': 'First Touch — Dealer Principal (Carnegie)',
            'style': 'carnegie', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'Transport for {{company}} vehicles — quick question, {{first_name}}',
            'body': """Hi {{first_name}},

I was looking at {{company}} — {{location}} is one of the markets we cover most actively for auto transport.

Quick question: when you move vehicles between rooftops or to auction, are you working with one carrier or managing a mix?

I ask because a few dealers in the Chicago area told us the coordination was their biggest headache — not the cost. We built something specifically for that problem.

If it's relevant, happy to share what they told us worked. 15 minutes?

[Name]""",
            'performance': {'open_rate': 40.7, 'reply_rate': 6.9, 'meetings': 5},
        },
        {
            'id': 'mt_bc_02', 'name': 'First Touch — Fleet Director (Hormozi)',
            'style': 'hormozi', 'goal': 'cold_outreach', 'channel': 'email',
            'subject': 'Vehicle relocation for {{company}} — do you outsource this?',
            'body': """{{first_name}},

If your company relocates employees with vehicles, we can handle the transport — fully insured, door-to-door, with real-time tracking.

Average corporate client: 40-200 vehicle moves/year. We price it as a flat rate per move so HR always knows the cost upfront.

Worth a 15-minute call to see if it fits your relocation program?

[Name]""",
            'performance': {'open_rate': 38.4, 'reply_rate': 7.3, 'meetings': 2},
        },
    ],

    'recommendations': [
        {
            'id': 'rec_bc_01', 'priority': 'high', 'category': 'list',
            'title': 'Enroll Auto Auction List — 67 Leads, Zero Competition',
            'rationale': 'Auction houses move high volume with limited outreach from auto transport companies. 67-lead list ready. Expect high open rate (auction ops are email-active). No competing campaigns.',
            'metric_trigger': 'unenrolled_list', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
            'expected_impact': '+2-3 meetings in first 30 days',
        },
        {
            'id': 'rec_bc_02', 'priority': 'medium', 'category': 'show_rate',
            'title': 'Show Rate 71% — Add Calendar Confirmation Sequence',
            'rationale': '2 no-shows this month. A same-day reminder text/email from sales rep reduces no-shows by 20-30% on average. Easy automation win.',
            'metric_trigger': 'show_rate < 80%', 'confidence': 'HIGH', 'difficulty': 'EASY',
            'status': 'pending', 'generated_at': '2026-03-10',
            'expected_impact': '+1 held meeting/month at zero additional outreach cost',
        },
        {
            'id': 'rec_bc_03', 'priority': 'medium', 'category': 'messaging',
            'title': 'Test "Cost Per Move" Angle — Resonates With Fleet Buyers',
            'rationale': 'Corporate fleet campaign reply rate (7.3%) is strong for a newer campaign. The "cost per move" framing in step 2 got the highest engagement. Build a dedicated sequence around this angle.',
            'metric_trigger': 'message_variant_performance', 'confidence': 'MEDIUM', 'difficulty': 'MEDIUM',
            'status': 'pending', 'generated_at': '2026-03-10',
            'expected_impact': '+15% positive reply rate on fleet segment',
        },
    ],

    'activity_log': [
        {'date': '2026-03-09', 'type': 'send',   'description': '111 emails sent across 2 campaigns'},
        {'date': '2026-03-09', 'type': 'reply',  'description': '6 replies (2 positive)'},
        {'date': '2026-03-08', 'type': 'reply',  'description': 'Tamara Blankenship — "Tell me more" — flagged for follow-up'},
        {'date': '2026-03-06', 'type': 'meeting','description': 'Robert Simone — North Shore Lexus → Opportunity → Proposal sent'},
    ],
}


# ── Registry ──────────────────────────────────────────────────────────────────

WORKSPACES = {
    'bcat_sales':       _bcat_sales,
    'bcat_recruitment': _bcat_recruitment,
    'best_care_sales':  _best_care_sales,
}


def get_workspace(workspace_id: str) -> dict | None:
    return WORKSPACES.get(workspace_id)

def get_workspaces_summary() -> list[dict]:
    return [
        {
            'id':   ws['id'],
            'name': ws['name'],
            'type': ws['type'],
            'kpis': ws['overview']['kpis'],
        }
        for ws in WORKSPACES.values()
    ]

def get_overview(workspace_id: str)       -> dict | None: return _section(workspace_id, 'overview')
def get_lead_lists(workspace_id: str)     -> list | None: return _section(workspace_id, 'lead_lists')
def get_leads(workspace_id: str)          -> list | None: return _section(workspace_id, 'leads')
def get_email_campaigns(workspace_id: str)-> list | None: return _section(workspace_id, 'email_campaigns')
def get_linkedin_campaigns(workspace_id: str)->list|None: return _section(workspace_id, 'linkedin_campaigns')
def get_meetings(workspace_id: str)       -> list | None: return _section(workspace_id, 'meetings')
def get_daily_results(workspace_id: str)  -> list | None: return _section(workspace_id, 'daily_results')
def get_message_templates(workspace_id: str)->list|None:  return _section(workspace_id, 'message_templates')
def get_recommendations(workspace_id: str)-> list | None: return _section(workspace_id, 'recommendations')
def get_activity_log(workspace_id: str)   -> list | None: return _section(workspace_id, 'activity_log')

def _section(workspace_id: str, key: str):
    ws = get_workspace(workspace_id)
    return ws.get(key) if ws else None
