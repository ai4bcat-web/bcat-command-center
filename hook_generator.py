"""
Hook Generator for Content Engine.

Generates LinkedIn hooks from a topic + style mode.
- If ANTHROPIC_API_KEY is set: calls Claude (claude-haiku) for natural AI-written hooks.
- Otherwise: uses a curated static bank of complete, natural-language hooks.

Design principles for the static bank:
- Hooks are complete sentences, NOT pattern-substitution templates
- {t} is used sparingly and only where a topic noun flows naturally
- Some hooks are universal (no topic injection) and selected by angle
- Category filtering prevents business hooks from appearing on personal topics
"""

import os
import json
import re
import hashlib
import logging

log = logging.getLogger(__name__)

# ── Style mode tone descriptions (for Claude prompt) ────────────────────────
STYLE_TONES = {
    'operator_founder':   'Direct, practical, no-nonsense. Talks like a founder who has been in the room and has the scars to prove it.',
    'contrarian':         'Challenges what most people assume. Grounded and provable, not just edgy.',
    'executive_friendly': 'Polished and measured. Credible. Respects the reader\'s intelligence.',
    'personal_story':     'Honest and specific. Shares real experience, not advice-column platitudes.',
    'authority_building': 'Proof-first. Leads with results or pattern recognition, not opinion.',
    'comment_bait':       'Takes a clear stance worth arguing about. Invites pushback from smart people.',
    'educational':        'Clear and useful. Breaks something real down without being condescending.',
    'punchy':             'Short, sharp, high-signal. Nothing wasted. Gets to the point immediately.',
}

# ── Static hook bank ─────────────────────────────────────────────────────────
# Each entry: (hook_text, emotion, categories)
# categories: list — 'business', 'personal', or 'any'
# {t} appears only where a noun phrase flows naturally in the sentence.
# Many hooks have no {t} at all — they work as universal openers.

_HOOKS = {

    'observation': [
        ("The teams that are winning at {t} aren't doing anything exotic. They just committed to a system and actually follow it.",
         'clarity', ['business']),
        ("Nobody talks about the six months before things clicked. That part of the story is usually more useful.",
         'empathy', ['any']),
        ("The businesses that look effortless from the outside usually made one decision: stop adding things.",
         'curiosity', ['business']),
        ("Good {t} isn't about doing more of it. It's about making it need less of your attention.",
         'clarity', ['business']),
        ("The most common sign of a broken process: everyone knows it's broken and nobody says it out loud.",
         'tension', ['business']),
        ("The gap between a company that scales and one that doesn't usually comes down to two or three decisions made early.",
         'curiosity', ['business']),
        ("Every {t} operation that actually works has one thing in common: someone made a decision and stopped revisiting it.",
         'clarity', ['business']),
        ("Most of the time, the thing you think is the problem is just where the real problem shows up most clearly.",
         'curiosity', ['any']),
        ("The version of parenting nobody writes about is the one where you're just trying not to repeat what was done to you.",
         'empathy', ['personal']),
        ("Being consistent is so much harder than being excellent. Consistent beats excellent almost every time.",
         'clarity', ['any']),
    ],

    'question': [
        ("When's the last time you looked at how you handle {t} and asked: does this actually make sense?",
         'curiosity', ['business']),
        ("If {t} disappeared from your operation tomorrow, what would actually break?",
         'curiosity', ['business']),
        ("What if the reason it isn't working isn't the system — it's the assumption underneath it?",
         'tension', ['any']),
        ("How much of what you're calling a problem is really just tolerance dressed up as strategy?",
         'challenge', ['any']),
        ("Is {t} the bottleneck — or is it just where the bottleneck is easiest to see?",
         'curiosity', ['business']),
        ("What would you do differently if you assumed the problem was three levels upstream from where you're looking?",
         'challenge', ['any']),
        ("Who actually owns the outcome here? If the answer takes more than two seconds, that's the problem.",
         'challenge', ['business']),
        ("What would change about how you approach this if you knew you'd have to live with the result for five years?",
         'challenge', ['any']),
    ],

    'admission': [
        ("I got {t} wrong for two years. Not because I wasn't trying. Because I was solving the wrong version of the problem.",
         'empathy', ['business']),
        ("The most expensive mistake I made wasn't a bad decision. It was a good decision made with the wrong information.",
         'tension', ['any']),
        ("I used to think it was a capacity problem. It wasn't. It was a clarity problem.",
         'empathy', ['any']),
        ("We almost missed the real issue because we were tracking the wrong metric and it was giving us the answer we wanted.",
         'story', ['business']),
        ("Three years ago I would have given completely different advice on this. I was confidently wrong.",
         'empathy', ['any']),
        ("I spent six months fixing the wrong thing before I realized we'd been optimizing for the wrong outcome.",
         'story', ['any']),
        ("The hardest part of getting better at {t} was admitting that what I was doing wasn't working — after I'd convinced everyone it was.",
         'empathy', ['business']),
        ("There was a version of myself that thought being busy was the same as making progress. It took a while to unlearn that.",
         'empathy', ['any']),
        ("The parenting moment I'm most proud of wasn't one where I had the right answer. It was one where I admitted I didn't.",
         'story', ['personal']),
    ],

    'contrarian': [
        ("More investment in {t} without fixing the underlying system just creates a more expensive version of the same problem.",
         'challenge', ['business']),
        ("The reason it isn't working probably has nothing to do with effort.",
         'challenge', ['any']),
        ("Everyone is scaling. Almost nobody is simplifying first. That order matters.",
         'challenge', ['business']),
        ("The best {t} operation I've seen wasn't sophisticated. It was boring. That was the whole point.",
         'curiosity', ['business']),
        ("Most advice on {t} is written by people who were never accountable for the actual outcome.",
         'tension', ['business']),
        ("There's a version of excellence in {t} that looks like doing less, not more.",
         'challenge', ['business']),
        ("The obsession with growth hides a deeper problem: most companies haven't figured out the basics yet.",
         'challenge', ['business']),
        ("We've confused activity for progress so consistently that hustle culture starts to feel normal.",
         'challenge', ['any']),
        ("Being a good parent has less to do with technique than with showing up when it's inconvenient.",
         'challenge', ['personal']),
        ("The hardest sales skill isn't closing. It's knowing when to stop pushing.",
         'challenge', ['business']),
    ],

    'insight': [
        ("There's usually one decision inside a complex problem that's responsible for most of the friction.",
         'utility', ['any']),
        ("Every failure I've seen share a common pattern: the problem was visible for months before anyone named it.",
         'tension', ['any']),
        ("The best operators ask 'why does this step exist' more often than 'how do we do this faster'. That shift changes everything in {t}.",
         'clarity', ['business']),
        ("Operators who are excellent at {t} didn't get there by doing more. They got there by removing the right things.",
         'clarity', ['business']),
        ("The most underrated skill: knowing when to stop executing and question the assumption instead.",
         'clarity', ['any']),
        ("Consistency compounds faster than optimization. Almost nobody acts like they believe this.",
         'clarity', ['any']),
        ("The teams quietly winning share one trait: they decide, execute, and don't relitigate the decision.",
         'proof', ['business']),
        ("In most situations, the leverage point is two levels up from where everyone is focused.",
         'curiosity', ['any']),
        ("The difference between a habit and a system: a habit depends on motivation. A system doesn't.",
         'clarity', ['any']),
    ],

    'proof': [
        ("The most impactful change we made last year cost nothing to implement and took one afternoon.",
         'curiosity', ['business']),
        ("After working through {t} with dozens of teams, the pattern is consistent: the problem is almost always the same thing.",
         'proof', ['business']),
        ("The before and after on {t} after fixing the actual root cause: the same team, a fraction of the friction.",
         'proof', ['business']),
        ("We thought {t} was the problem. Turned out it was just where the real problem showed up most visibly.",
         'story', ['business']),
        ("The teams I've seen break through on {t} all made one shift: from managing the symptom to naming the cause.",
         'proof', ['business']),
    ],

    'tension': [
        ("Most teams know the process is broken. Almost none of them have the honest conversation about why.",
         'tension', ['business']),
        ("The uncomfortable truth: the person closest to the problem usually isn't in a position to fix it.",
         'tension', ['any']),
        ("The reason {t} feels hard is usually that you've built the system around the wrong objective.",
         'tension', ['business']),
        ("Most processes are designed for the problem you had, not the one you have now.",
         'tension', ['business']),
        ("Teams that tolerate broken systems aren't lazy. They've just stopped believing things can be different.",
         'empathy', ['business']),
        ("The conversations that would actually move things forward are usually the ones nobody wants to have.",
         'tension', ['any']),
        ("Most of us are very good at being busy in ways that feel important but don't change anything.",
         'tension', ['any']),
    ],

    'warning': [
        ("If you're scaling {t} before you understand what's breaking it, you're about to have a much larger version of the same problem.",
         'urgency', ['business']),
        ("The worst time to discover your system is wrong is after you've built everything else around it.",
         'urgency', ['business']),
        ("Before you hire someone to fix {t}: make sure you know what's actually broken. Most teams don't.",
         'urgency', ['business']),
        ("Automating a broken process doesn't fix it. It just breaks it faster at higher volume.",
         'urgency', ['business']),
        ("If your operation depends on one person knowing how everything works, you don't have a system. You have a dependency.",
         'urgency', ['business']),
        ("The most dangerous point in fixing something is when you've started but haven't yet finished. That gap is where things break.",
         'urgency', ['any']),
    ],

}

# Angle preference order by style mode
_STYLE_ANGLE_ORDER = {
    'operator_founder':   ['observation', 'insight', 'admission', 'proof', 'contrarian', 'question', 'tension', 'warning'],
    'contrarian':         ['contrarian', 'tension', 'observation', 'question', 'insight', 'admission', 'warning', 'proof'],
    'executive_friendly': ['insight', 'proof', 'observation', 'question', 'contrarian', 'tension', 'admission', 'warning'],
    'personal_story':     ['admission', 'tension', 'observation', 'question', 'insight', 'contrarian', 'warning', 'proof'],
    'authority_building': ['proof', 'insight', 'observation', 'contrarian', 'tension', 'question', 'admission', 'warning'],
    'comment_bait':       ['contrarian', 'question', 'tension', 'warning', 'observation', 'insight', 'admission', 'proof'],
    'educational':        ['insight', 'observation', 'question', 'proof', 'tension', 'contrarian', 'admission', 'warning'],
    'punchy':             ['contrarian', 'observation', 'warning', 'tension', 'insight', 'question', 'proof', 'admission'],
}

# Category group mapping
_PERSONAL_CATEGORIES = {'lifestyle', 'personal', 'parenting', 'family'}
_BUSINESS_CATEGORIES = {'industry', 'aiden', 'conflicting_opinion', 'sales', 'marketing', 'operations', 'business'}


def _apply_topic(text: str, topic: str) -> str:
    """Substitute {t} with the topic as a natural noun phrase."""
    t = topic.strip().lower() if topic else 'this'
    return text.replace('{t}', t)


def _category_type(category: str) -> str:
    """Returns 'personal', 'business', or 'any'."""
    c = (category or '').lower()
    if c in _PERSONAL_CATEGORIES:
        return 'personal'
    if c in _BUSINESS_CATEGORIES:
        return 'business'
    return 'business'  # default to business


def _seed(topic: str, style_mode: str, category: str) -> int:
    raw = f"{topic}|{style_mode}|{category}"
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def _generate_hooks_static(topic: str, style_mode: str = 'operator_founder', category: str = 'industry') -> list:
    """
    Select 10 varied, natural hooks from the curated bank.
    Filters by category type (business vs personal).
    Prioritises angles aligned to style_mode.
    """
    cat_type = _category_type(category)
    angle_order = _STYLE_ANGLE_ORDER.get(style_mode, list(_HOOKS.keys()))
    for a in _HOOKS:
        if a not in angle_order:
            angle_order.append(a)

    seed = _seed(topic, style_mode, category)
    selected = []
    used_hooks: set = set()

    def try_add(pool, angle, weight):
        nonlocal seed
        for offset in range(len(pool)):
            idx = (seed + offset) % len(pool)
            h_text, emotion, cats = pool[idx]
            # Category filter: skip if hook is for wrong context
            if cat_type == 'personal' and 'business' in cats and 'any' not in cats:
                continue
            if cat_type == 'business' and 'personal' in cats and 'any' not in cats:
                continue
            hook_text = _apply_topic(h_text, topic)
            if hook_text not in used_hooks:
                used_hooks.add(hook_text)
                selected.append({
                    'hook':    hook_text,
                    'type':    angle,
                    'emotion': emotion,
                    'weight':  weight,
                })
                seed = (seed * 1103515245 + 12345) & 0x7fffffff
                return True
        return False

    # First pass: one hook per angle in priority order
    for rank, angle in enumerate(angle_order):
        if len(selected) >= 10:
            break
        pool = _HOOKS.get(angle, [])
        weight = 9 if rank < 3 else 7 if rank < 6 else 5
        try_add(pool, angle, weight)

    # Second pass: pull more from top angles if still under 10
    if len(selected) < 10:
        for angle in angle_order:
            if len(selected) >= 10:
                break
            pool = _HOOKS.get(angle, [])
            try_add(pool, angle, 5)

    return selected[:10]


def _generate_hooks_with_claude(topic: str, style_mode: str, category: str, api_key: str) -> list:
    """Call Claude Haiku to generate natural, varied hooks."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        tone_desc = STYLE_TONES.get(style_mode, 'Direct and honest.')
        cat_type = _category_type(category)
        context_hint = (
            'This is for a personal/lifestyle topic — avoid corporate language.' if cat_type == 'personal'
            else 'This is a business/operations topic.'
        )

        prompt = f"""You are a sharp, direct LinkedIn content writer. Generate 10 hooks for a post about: "{topic}"

Tone: {tone_desc}
Context: {context_hint}

Requirements:
- Maximum 2-3 short lines per hook (a blank line between them counts as a line)
- Write like a smart person thinking out loud — not a copywriter running a formula
- Each hook should feel meaningfully different from the others (vary structure, approach, length)
- Mix naturally: direct statements, honest questions, sharp observations, real admissions
- Be specific when specificity makes it stronger
- Do NOT use: "game-changer", "this changed everything", "unpopular opinion:", "you need to hear this", "let's be honest"
- No fake urgency, no bro-marketing, no cringe phrases
- Hooks should sound like something a real, thoughtful person would actually say or write
- Topic should appear naturally in the hook — not forced into an awkward grammatical position

Return ONLY a valid JSON array with exactly 10 objects. No explanation, no markdown, no other text.
[
  {{
    "hook": "hook text here — use \\n for line breaks within the hook",
    "type": "one of: observation | question | admission | contrarian | insight | proof | tension | warning",
    "emotion": "one of: curiosity | empathy | tension | challenge | urgency | clarity | proof | story | utility"
  }}
]"""

        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': prompt}],
        )

        raw = message.content[0].text.strip()
        match = re.search(r'\[[\s\S]*\]', raw)
        if match:
            hooks = json.loads(match.group())
            return [{
                'hook':    h.get('hook', ''),
                'type':    h.get('type', 'observation'),
                'emotion': h.get('emotion', 'curiosity'),
                'weight':  h.get('weight', 8),
            } for h in hooks[:10]]

    except Exception as exc:
        log.warning('Claude hook generation failed (%s) — falling back to static', exc)

    return _generate_hooks_static(topic, style_mode, category)


def generate_hooks(topic: str, style_mode: str = 'operator_founder', category: str = 'industry') -> list:
    """
    Public entry point.
    Returns a list of up to 10 hook dicts: {hook, type, emotion, weight}
    Uses Claude if ANTHROPIC_API_KEY is set, otherwise the static bank.
    """
    if not topic or not topic.strip():
        return []

    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if api_key:
        return _generate_hooks_with_claude(topic, style_mode, category, api_key)

    return _generate_hooks_static(topic, style_mode, category)


# ── Post generator ───────────────────────────────────────────────────────────

_TONE_DESC = {
    'direct':      'Direct, practical, no-nonsense operator voice. Short sentences. No fluff.',
    'story':       'Personal story — honest, specific, first-person. Shares real experience, not advice.',
    'contrarian':  'Challenges the conventional take. Grounded and provable, not just edgy.',
    'data':        'Proof-first. Leads with numbers or pattern recognition. Credible and specific.',
    'educational': 'Clear and useful. Breaks something real down simply without being condescending.',
}

_HASHTAGS = {
    'industry':            '#logistics #operations #freight #supplychain #automation',
    'lifestyle':           '#mindset #productivity #entrepreneurship #leadership #growth',
    'aiden':               '#AI #automation #b2b #operationsai #businessgrowth',
    'conflicting_opinion': '#leadership #sales #marketing #businessstrategy',
}


def generate_post(topic: str, tone: str = 'direct', category: str = 'industry') -> dict:
    """
    Generate a complete LinkedIn post (hook + body + cta + hashtags).
    Uses Claude if ANTHROPIC_API_KEY is set, otherwise builds from the static hook bank.
    """
    if not topic or not topic.strip():
        return {}

    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if api_key:
        return _generate_post_with_claude(topic, tone, category, api_key)

    return _generate_post_static(topic, tone, category)


def _generate_post_with_claude(topic: str, tone: str, category: str, api_key: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        tone_desc = _TONE_DESC.get(tone, _TONE_DESC['direct'])
        hashtags = _HASHTAGS.get(category, _HASHTAGS['industry'])
        cat_type = _category_type(category)
        context_hint = (
            'Personal/lifestyle topic — avoid corporate language, be human.'
            if cat_type == 'personal'
            else 'Business/operations topic.'
        )

        prompt = f"""Write a complete, high-engagement LinkedIn post about: "{topic}"

Tone: {tone_desc}
Context: {context_hint}

Structure the post as:
1. Hook (1-3 lines, scroll-stopping opening — no generic openers)
2. Body (the meat — insight, story, data, or framework — 4-10 short paragraphs or bullet points)
3. CTA (1-2 lines inviting a real response)

Writing rules:
- Short sentences. White space. Skimmable.
- Sound like a real person — not a template or copywriter
- No "game-changer", "this changed everything", "let's be real", "in today's world"
- No fake urgency
- Be specific when specificity makes it better
- The hook must earn the scroll — don't open with something generic

Return ONLY a JSON object, no markdown, no explanation:
{{
  "hook": "the hook text (use \\n for line breaks)",
  "body": "the body text (use \\n for line breaks)",
  "cta": "the call to action",
  "hashtags": "{hashtags}"
}}"""

        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}],
        )

        raw = message.content[0].text.strip()
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())

    except Exception as exc:
        log.warning('Claude post generation failed (%s) — falling back to static', exc)

    return _generate_post_static(topic, tone, category)


def _generate_post_static(topic: str, tone: str, category: str) -> dict:
    """Build a post from the static hook bank + PatternLibrary body blocks."""
    # Map tone → style_mode for hook selection
    tone_to_style = {
        'direct':      'operator_founder',
        'story':       'personal_story',
        'contrarian':  'contrarian',
        'data':        'authority_building',
        'educational': 'educational',
    }
    style = tone_to_style.get(tone, 'operator_founder')
    hooks = _generate_hooks_static(topic, style, category)
    hook_text = hooks[0]['hook'] if hooks else f"Here's what most people get wrong about {topic.lower()}."

    hashtags = _HASHTAGS.get(category, _HASHTAGS['industry'])

    # Simple body — use proof/lesson block based on tone
    body_map = {
        'direct':      "Here's what I've learned:\n\n→ The problem is almost never what it looks like on the surface.\n→ The fix usually requires one decision, made clearly, followed consistently.\n→ Most teams skip straight to execution before they've named the real issue.\n\nWhen you name it correctly, the path forward gets obvious.",
        'story':       "Six months ago, I was in the middle of it.\n\nNot the polished version — the real one. Where you don't know if the decision you made was right yet.\n\nWhat I noticed: the moment you stop protecting your ego and just ask what's actually true, things move.\n\nThat shift doesn't feel dramatic. It usually just feels like a quiet decision to stop pretending.",
        'contrarian':  "Everyone's optimizing the wrong thing.\n\nThe teams that look like they're winning at {t} are usually just better at appearing busy. The ones actually winning made it boring — and then stopped touching it.\n\nMore isn't the answer. Fewer, better decisions are.\n\nSimple systems compound. Complex ones collapse.".replace('{t}', topic.lower()),
        'data':        "Here's what the pattern looks like across 30+ teams:\n\n→ The problem was visible 6–12 months before anyone named it\n→ The fix was simpler than expected\n→ The barrier was always the conversation, not the solution\n\nMost situations have a $100k+ inefficiency hiding in plain sight.\n\nYou find it by measuring what you've been ignoring.",
        'educational': f"Most people approach {topic.lower()} backwards.\n\nThey start with execution before they've diagnosed the problem.\n\nThe right order:\n\n1. Name what's actually broken (not what you think is broken)\n2. Identify the one lever that moves the most\n3. Build the simplest system that addresses it\n4. Measure before and after\n5. Then — and only then — scale\n\nThe temptation to skip step one is the reason most fixes don't stick.",
    }

    body = body_map.get(tone, body_map['direct'])
    cta  = "What's the version of this that's true for your situation?\n\nDrop it in the comments — genuinely curious."

    return {'hook': hook_text, 'body': body, 'cta': cta, 'hashtags': hashtags}
