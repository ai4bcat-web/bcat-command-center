"""
Messaging Service
Generates personalized outreach messages using style profiles and variable substitution.

Style profiles:
  carnegie    — warm, relationship-first, curiosity-driven (How to Win Friends)
  hormozi     — direct, value-stack, ROI-focused, no fluff
  concise     — short, punchy, 3 sentences max
  recruiter   — opportunity framing, lifestyle/income appeal, peer-to-peer
  executive   — boardroom tone, strategic, peer-level

Channels: email, linkedin
Goals: cold_intro, followup_1, followup_2, breakup, objection_cost,
       objection_timing, objection_competitor, meeting_confirm, meeting_remind
"""

import logging, os, re
from datetime import datetime
log = logging.getLogger(__name__)

# ── Template library ──────────────────────────────────────────────────────────

_TEMPLATES = {

    # ── BCAT LOGISTICS SALES (freight brokerage) ──────────────────────────────

    'bcat_sales': {
        'carnegie': {
            'email': {
                'cold_intro': {
                    'subject': "Quick question about {{company}}'s freight",
                    'body': """Hi {{first_name}},

I came across {{company}} and was impressed by {{company_insight}}.

I'm curious — how are you currently handling your freight when lanes get tight or your usual carriers fall through? A lot of {{industry}} companies I talk to are finding that having a reliable backup broker saves them real money in Q4.

We move {{load_type}} freight daily and specialize in last-minute coverage. Would it make sense to have a 15-minute conversation to see if there's any fit?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "Re: Quick question about {{company}}'s freight",
                    'body': """Hi {{first_name}},

Wanted to follow up on my note from last week.

I know you're busy — I just wanted to share that we recently helped a {{industry}} company in {{state}} save about ${{savings_example}} on a tight lane by covering same-day. That kind of situation tends to come up more than people expect.

No pressure at all. If it's not the right time, just let me know and I'll check back in a few months.

{{signature}}"""
                },
                'followup_2': {
                    'subject': "One more thought on {{company}}",
                    'body': """Hi {{first_name}},

Last note from me — I don't want to be a pest.

I genuinely think we could add value to {{company}}'s freight network, but I also respect your time. If you're not moving {{load_type}} loads frequently enough to need a backup broker, that's totally fine.

If things change or you hit a tough lane situation, feel free to reach out anytime.

{{signature}}"""
                },
                'breakup': {
                    'subject': "Closing the loop, {{first_name}}",
                    'body': """Hi {{first_name}},

I'm going to stop reaching out — I don't want to keep showing up in your inbox if the timing isn't right.

If your freight situation ever changes or you need emergency coverage on a lane, I'm just an email away.

Wishing {{company}} a great rest of the year.

{{signature}}"""
                },
                'objection_cost': {
                    'subject': "Re: Cost concerns",
                    'body': """Hi {{first_name}},

That's a fair point — freight brokerage adds a layer of cost, no question.

The way most of our customers think about it: they're not paying for every load, they're buying coverage for the loads that would otherwise sit on a dock. A single missed pickup at the wrong time can cost more than months of broker fees.

Would you be open to a quick call just to understand your volume? I can tell you honestly within 5 minutes if we'd be worth it for {{company}}.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """Hi {{first_name}}, I noticed {{company}} operates in {{industry}} — I work with several similar companies handling freight coverage when their primary carriers can't deliver. Not pitching anything, just curious: how do you handle last-minute lane failures? Happy to share what's been working for others if it's useful."""
                },
                'followup_1': {
                    'body': """Hi {{first_name}}, following up on my message from last week. I helped a {{industry}} company in {{state}} avoid a ${{savings_example}} detention charge last month by covering same-day. If that kind of situation comes up for {{company}}, I'd love to be on your radar."""
                },
            },
        },

        'hormozi': {
            'email': {
                'cold_intro': {
                    'subject': "{{company}} — freight coverage gap",
                    'body': """{{first_name}},

Here's the problem most {{industry}} shippers have: their broker works great until it doesn't — and when a lane fails, they're scrambling.

What we do: same-day and next-day coverage on {{load_type}} lanes, guaranteed pickup or we eat the cost difference.

Results our clients get:
→ Zero missed pickups in 60 days or money back
→ Average 8% freight cost reduction on covered lanes
→ 24/7 dispatch, not a ticketing system

If {{company}} moves more than {{load_threshold}} loads/month, this will pay for itself.

Worth 15 minutes?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "{{company}} — still relevant?",
                    'body': """{{first_name}},

Sent you a note last week. Either my email landed wrong or it's not a fit — both are fine.

If {{company}} is still moving freight and you've ever had a carrier fall through at the worst possible time, I have a specific solution for that.

If not, no worries. Just reply "not interested" and I'll never email you again.

{{signature}}"""
                },
                'breakup': {
                    'subject': "Last email, {{first_name}}",
                    'body': """{{first_name}},

This is my last email. I'm not going to keep bugging you.

If you ever need emergency freight coverage — same-day, guaranteed pickup — you know where to find me.

{{signature}}"""
                },
                'objection_cost': {
                    'subject': "Re: The cost question",
                    'body': """{{first_name}},

Fair. Let me make this simple:

If your freight runs perfectly 100% of the time, you don't need us.

If you've ever had a carrier no-show, a lane disappear, or a customer miss their delivery window — and it cost you money or a relationship — then the cost of not having a backup is higher than our fee.

I'll give you our exact pricing on a 5-minute call. You'll know immediately if the math works.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """{{first_name}} — quick question: when your primary carrier fails on a lane, what's your backup plan? I help {{industry}} companies avoid detention charges and missed pickups with guaranteed same-day coverage. If that's ever been a problem at {{company}}, worth a quick call."""
                },
            },
        },

        'concise': {
            'email': {
                'cold_intro': {
                    'subject': "Freight backup for {{company}}",
                    'body': """Hi {{first_name}},

We provide same-day freight coverage for {{industry}} shippers when primary carriers fail.

Can I send over a one-pager on how it works for {{company}}?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "Re: Freight backup for {{company}}",
                    'body': """Hi {{first_name}},

Still the right person for freight decisions at {{company}}?

If yes — 15 minutes this week?

{{signature}}"""
                },
                'breakup': {
                    'subject': "Closing out, {{first_name}}",
                    'body': """Hi {{first_name}},

Sounds like the timing isn't right. I'll stop following up.

Feel free to reach out if {{company}}'s freight situation changes.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """Hi {{first_name}}, do you handle freight at {{company}}? We do same-day carrier coverage for {{industry}} shippers. Happy to share details if it's relevant."""
                },
            },
        },
    },

    # ── BCAT RECRUITMENT ──────────────────────────────────────────────────────

    'bcat_recruitment': {
        'recruiter': {
            'email': {
                'cold_intro': {
                    'subject': "Owner-operator opportunity — {{route}} lanes",
                    'body': """Hi {{first_name}},

I found your profile and wanted to reach out directly — we have consistent {{load_type}} freight on {{route}} lanes and we're looking for reliable owner-ops to run them.

What we offer:
→ {{rate_per_mile}} average on these lanes
→ Weekly pay, no factoring needed
→ Fuel advances available
→ You choose your schedule — we don't dispatch you

We work with {{driver_count}}+ carriers right now. A lot of them came from exactly where you are — leased on somewhere that wasn't delivering consistent miles.

Are you currently running {{route}} lanes? If so, I'd love to have a quick call.

{{signature}}"""
                },
                'followup_1': {
                    'subject': "Re: Owner-op lanes — {{route}}",
                    'body': """Hi {{first_name}},

Just wanted to follow up. The {{route}} lanes I mentioned are still open — we have {{available_loads}} loads per week that need a reliable carrier.

I know switching brokers or finding new freight relationships takes time. I'm not asking for a commitment — just a 10-minute call to see if the lanes fit your current routes.

{{signature}}"""
                },
                'breakup': {
                    'subject': "Closing out — freight lanes for {{first_name}}",
                    'body': """Hi {{first_name}},

I'll stop following up. If your situation changes or you're looking for more consistent freight on {{route}}, feel free to reach out anytime.

Good luck out there.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """Hi {{first_name}}, I work with owner-ops running {{route}} lanes — we have consistent {{load_type}} freight at {{rate_per_mile}}/mile, weekly pay, no forced dispatch. Are you currently running that corridor? Happy to share lane details."""
                },
                'followup_1': {
                    'body': """{{first_name}}, following up on my last message. The {{route}} lanes are still open. If you're looking for more consistent miles with no BS, I'd love to connect for 10 minutes."""
                },
            },
        },

        'concise': {
            'email': {
                'cold_intro': {
                    'subject': "{{load_type}} lanes on {{route}} — owner-ops",
                    'body': """Hi {{first_name}},

We have consistent {{load_type}} freight on {{route}} at {{rate_per_mile}}/mile, weekly pay.

Are you running {{route}} right now?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "Re: {{route}} lanes still open",
                    'body': """Hi {{first_name}},

Lanes are still open. Worth a 10-minute call?

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """Hi {{first_name}}, we have {{load_type}} freight on {{route}} at {{rate_per_mile}}/mile, weekly pay. Running that corridor?"""
                },
            },
        },
    },

    # ── BEST CARE AUTO TRANSPORT SALES ────────────────────────────────────────

    'best_care_sales': {
        'carnegie': {
            'email': {
                'cold_intro': {
                    'subject': "Vehicle transport for {{company}} — quick question",
                    'body': """Hi {{first_name}},

I noticed {{company}} and wanted to reach out personally.

I'm curious — when your customers purchase a vehicle that needs to be transported, how are you currently handling that logistics piece? A lot of {{industry}} businesses I speak with are surprised at how much of a difference the transport partner makes in terms of the customer experience.

We specialize in vehicle transport for dealerships and remarketers, with GPS tracking and white-glove handling. We'd love to understand your current setup.

Would a 15-minute call make sense?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "Re: Vehicle transport for {{company}}",
                    'body': """Hi {{first_name}},

Following up on my note from last week.

I wanted to mention — we recently moved a batch of {{vehicle_type}} vehicles for a {{industry}} company in {{state}} and the GM told us it was the smoothest transport experience they'd had. I thought that might resonate with what {{company}} looks for in a transport partner.

Happy to share more details if it's relevant.

{{signature}}"""
                },
                'breakup': {
                    'subject': "Closing the loop, {{first_name}}",
                    'body': """Hi {{first_name}},

I'm going to stop following up — I don't want to clutter your inbox.

If {{company}} ever needs a reliable vehicle transport partner — especially for time-sensitive or high-value vehicles — I'd love to hear from you.

{{signature}}"""
                },
                'objection_cost': {
                    'subject': "Re: Pricing question",
                    'body': """Hi {{first_name}},

That's a totally fair concern. Here's how our customers typically think about it:

The cost of a scratched vehicle, a delayed delivery, or a damaged high-value car far exceeds the difference in transport pricing. Our customers tend to stay with us not because we're cheapest, but because we've never damaged a car and never missed a delivery window.

Would you be open to a quick rate comparison? I can pull exact quotes for your typical routes in about 10 minutes.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """Hi {{first_name}}, I work with auto dealerships and remarketing companies on vehicle transport — we specialize in GPS-tracked, white-glove shipping for high-value vehicles. Curious how {{company}} handles transport today. Would it be worth a brief conversation?"""
                },
            },
        },

        'hormozi': {
            'email': {
                'cold_intro': {
                    'subject': "{{company}} — vehicle transport upgrade",
                    'body': """{{first_name}},

If you transport vehicles and you've ever had a carrier damage a car, miss a pickup, or go dark mid-shipment — I have something specific for you.

What we offer dealerships:
→ GPS tracking on every load (you see it live)
→ $0 damage guarantee or we cover repair costs
→ 48-hour pickup on most routes
→ Dedicated account rep — not a call center

We moved {{vehicles_moved}}+ vehicles last year with a 0.3% damage rate (industry average is 2.1%).

If {{company}} ships more than {{volume_threshold}} vehicles/month, I can build you a custom rate sheet today.

Interested?

{{signature}}"""
                },
                'followup_1': {
                    'subject': "{{company}} — still moving vehicles?",
                    'body': """{{first_name}},

Sent you a note last week. Either bad timing or not relevant — both fine.

If {{company}} is still transporting vehicles and you've ever had a carrier issue, I have a specific fix for that.

Reply "not interested" and I'll leave you alone.

{{signature}}"""
                },
                'objection_competitor': {
                    'subject': "Re: Already have a carrier",
                    'body': """{{first_name}},

That's great — a reliable carrier relationship is worth a lot.

I'm not asking you to switch. I'm asking for one shipment.

Send us your next {{vehicle_type}} move. Compare the experience. If ours isn't better, I'll send you a $100 gift card for wasting your time.

That's how confident we are.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """{{first_name}} — does {{company}} transport vehicles? We move {{vehicle_type}} with GPS tracking, $0 damage guarantee, and 48-hour pickup. If you've ever had a carrier go dark on a high-value shipment, worth 15 minutes."""
                },
            },
        },

        'executive': {
            'email': {
                'cold_intro': {
                    'subject': "Vehicle logistics — a conversation worth having",
                    'body': """{{first_name}},

I'll be brief. We're the vehicle transport partner for several of the top {{industry}} companies in {{region}}, and I wanted to reach out directly to you.

The reason I'm contacting you specifically: {{company}}'s scale and the type of vehicles you handle are exactly the profile where our service model creates the most value — particularly around damage prevention and delivery reliability.

If you have 20 minutes for a peer conversation, I'd welcome it.

{{signature}}"""
                },
            },
            'linkedin': {
                'cold_intro': {
                    'body': """{{first_name}}, I lead partnerships at Best Care Auto Transport. We're the transport partner for several leading {{industry}} companies in {{region}}. Given {{company}}'s profile, I thought a brief conversation might be worthwhile. Open to connecting?"""
                },
            },
        },
    },
}

# ── Variable substitution ─────────────────────────────────────────────────────

def _substitute(template: str, variables: dict) -> str:
    """Replace {{variable}} placeholders with provided values."""
    def replace(m):
        key = m.group(1).strip()
        return str(variables.get(key, m.group(0)))  # leave unreplaced if missing
    return re.sub(r'\{\{(\w+)\}\}', replace, template)

# ── Public API ─────────────────────────────────────────────────────────────────

def generate_message(
    workspace_id: str,
    style: str,
    channel: str,
    goal: str,
    variables: dict,
) -> dict:
    """
    Generate a personalized message.

    Args:
        workspace_id: 'bcat_sales' | 'bcat_recruitment' | 'best_care_sales'
        style: 'carnegie' | 'hormozi' | 'concise' | 'recruiter' | 'executive'
        channel: 'email' | 'linkedin'
        goal: 'cold_intro' | 'followup_1' | 'followup_2' | 'breakup' |
              'objection_cost' | 'objection_timing' | 'objection_competitor' |
              'meeting_confirm' | 'meeting_remind'
        variables: dict of substitution values

    Returns:
        dict with subject (email only), body, style, channel, goal, missing_vars
    """
    ws_templates = _TEMPLATES.get(workspace_id, {})
    style_templates = ws_templates.get(style) or ws_templates.get(_fallback_style(workspace_id))
    if not style_templates:
        return {'ok': False, 'error': f'No templates for workspace {workspace_id}'}

    channel_templates = style_templates.get(channel, {})
    if not channel_templates:
        # Fall back to email if linkedin not defined
        channel_templates = style_templates.get('email', {})
        channel = 'email'

    template = channel_templates.get(goal)
    if not template:
        # Fall back to cold_intro if goal not found
        template = channel_templates.get('cold_intro', {})

    if not template:
        return {'ok': False, 'error': f'No template for {workspace_id}/{style}/{channel}/{goal}'}

    body = _substitute(template.get('body', ''), variables)
    result = {
        'ok':      True,
        'style':   style,
        'channel': channel,
        'goal':    goal,
        'body':    body,
    }
    if 'subject' in template:
        result['subject'] = _substitute(template['subject'], variables)

    # Report unfilled placeholders
    missing = re.findall(r'\{\{(\w+)\}\}', body)
    if result.get('subject'):
        missing += re.findall(r'\{\{(\w+)\}\}', result['subject'])
    result['missing_vars'] = list(set(missing))

    return result


def get_styles(workspace_id: str) -> list:
    """Return available style names for a workspace."""
    return list(_TEMPLATES.get(workspace_id, {}).keys())


def get_goals(workspace_id: str, style: str, channel: str) -> list:
    """Return available goal names for workspace/style/channel."""
    return list(_TEMPLATES.get(workspace_id, {})
                           .get(style, {})
                           .get(channel, {}).keys())


def get_template_variables(workspace_id: str, style: str, channel: str, goal: str) -> list:
    """Return list of variable names used in a template."""
    ws = _TEMPLATES.get(workspace_id, {})
    style_t = ws.get(style, {})
    ch_t = style_t.get(channel, {})
    tmpl = ch_t.get(goal, {})
    text = tmpl.get('body', '') + tmpl.get('subject', '')
    return list(set(re.findall(r'\{\{(\w+)\}\}', text)))


def get_all_templates(workspace_id: str) -> dict:
    """Return the full template tree for a workspace (for the UI template browser)."""
    ws = _TEMPLATES.get(workspace_id, {})
    result = {}
    for style, channels in ws.items():
        result[style] = {}
        for channel, goals in channels.items():
            result[style][channel] = list(goals.keys())
    return result


def bulk_generate(
    workspace_id: str,
    style: str,
    channel: str,
    goal: str,
    leads: list[dict],
    common_vars: dict = None,
) -> list[dict]:
    """
    Generate personalized messages for a list of leads.

    Each lead dict should contain field names matching template variables.
    common_vars are merged under leads (lead values take precedence).
    """
    common = common_vars or {}
    results = []
    for lead in leads:
        variables = {**common, **lead}
        msg = generate_message(workspace_id, style, channel, goal, variables)
        msg['lead_email'] = lead.get('email', '')
        msg['lead_name'] = lead.get('first_name', '') + ' ' + lead.get('last_name', '')
        results.append(msg)
    return results


def _fallback_style(workspace_id: str) -> str:
    defaults = {
        'bcat_sales':       'concise',
        'bcat_recruitment': 'recruiter',
        'best_care_sales':  'carnegie',
    }
    return defaults.get(workspace_id, 'concise')
