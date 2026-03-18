"""
Content Optimizer — adapts a pasted post/draft for 5 platforms.

Each platform version is meaningfully different:
  LinkedIn    — thought-leadership, professional, long-form friendly
  Facebook    — conversational, community-oriented, shorter
  Instagram   — hook-first caption, hashtags in first comment
  TikTok      — ultra-short, punchy, overlay text suggestion
  YouTube     — title + description + full comment strategy

Uses Claude (claude-haiku) when ANTHROPIC_API_KEY is set.
Falls back to a deterministic static adapter that still produces
meaningfully different output per platform.
"""

import os
import json
import re
import logging

log = logging.getLogger(__name__)

# ── Content type descriptions ────────────────────────────────────────────────
_CONTENT_TYPE_DESC = {
    'thought_leadership': 'thought leadership / industry insight',
    'educational':        'educational / how-to / framework',
    'story':              'personal story / experience',
    'promotion':          'product or service promotion',
    'case_study':         'case study / results / proof',
    'personal':           'personal / lifestyle / mindset',
    'contrarian':         'contrarian / hot take / challenge',
}

# ── Tone descriptions ────────────────────────────────────────────────────────
_TONE_DESC = {
    'professional': 'polished, professional, credible',
    'casual':       'relaxed, conversational, approachable',
    'punchy':       'short, sharp, high-signal, nothing wasted',
    'founder':      'direct founder/operator voice — real, no-fluff',
    'educational':  'clear, helpful, structured, easy to follow',
}


def optimize_post(content: str, content_type: str = 'thought_leadership', tone: str = 'professional') -> dict:
    """
    Public entry point. Returns a dict with keys: linkedin, facebook, instagram, tiktok, youtube.
    Each value is a platform-specific output dict.
    """
    if not content or not content.strip():
        return {}

    api_key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if api_key:
        return _optimize_with_claude(content, content_type, tone, api_key)

    return _optimize_static(content, content_type, tone)


# ── Claude-powered optimizer ─────────────────────────────────────────────────

def _optimize_with_claude(content: str, content_type: str, tone: str, api_key: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        ct_desc   = _CONTENT_TYPE_DESC.get(content_type, content_type)
        tone_desc = _TONE_DESC.get(tone, tone)

        prompt = f"""You are a social media content strategist. Adapt the following post/draft for 5 platforms.

ORIGINAL CONTENT:
{content}

Content type: {ct_desc}
Tone: {tone_desc}

IMPORTANT: Each platform version must be meaningfully different — not just the same text reformatted.
Adapt for each platform's audience, norms, pacing, and format.

Platform requirements:

LINKEDIN:
- Professional, thought-leadership voice
- Long-form is fine (300–1500 chars). Use short paragraphs and line breaks for readability.
- 3–5 relevant industry hashtags
- First comment: adds depth, context, or a resource link — not a generic CTA

FACEBOOK:
- More conversational and community-oriented than LinkedIn
- Shorter (150–400 chars). More personal, warmer tone.
- Hashtags optional (0–3 max, skip if unnatural)
- First comment: sparks discussion, asks a question of the community

INSTAGRAM:
- Strong hook in the first 1–2 lines (visible before "more")
- Emoji where it feels natural (not forced)
- Caption: 100–300 chars. End with a soft CTA or question.
- Hashtags: put 10–20 hashtags in the first_comment field (NOT in copy)
- First comment: the hashtag block for reach

TIKTOK:
- Caption: 1–3 lines max. Ultra-short. Fast-reading. Hook-first.
- 5–8 relevant hashtags (mix of trending + niche)
- overlay_text: 3–8 words that would work as on-screen text overlay (punch of the idea)
- First comment: engagement hook — asks a polarizing question or dares people to respond

YOUTUBE:
- title: compelling video title, 50–70 chars, specific and clickable
- description: 3–5 paragraphs. Cover: what the video is about, key points, value the viewer gets, CTA.
- hashtags: 5–8 searchable tags (no # symbol, comma separated)
- pinned_comment: the exact comment to pin. Should include a question + CTA to reply. This drives replies directly.
- discussion_question: a standalone question to drive debate in the comments
- cta: the CTA text to say at end of video or include in description
- comment_strategy: 1–2 sentences on what to do in the comments section to maximize engagement

Return ONLY valid JSON with no markdown, no explanation:
{{
  "linkedin": {{
    "copy": "...",
    "hashtags": "...",
    "first_comment": "..."
  }},
  "facebook": {{
    "copy": "...",
    "hashtags": "...",
    "first_comment": "..."
  }},
  "instagram": {{
    "copy": "...",
    "hashtags": "...",
    "first_comment": "..."
  }},
  "tiktok": {{
    "copy": "...",
    "hashtags": "...",
    "overlay_text": "...",
    "first_comment": "..."
  }},
  "youtube": {{
    "title": "...",
    "description": "...",
    "hashtags": "...",
    "pinned_comment": "...",
    "discussion_question": "...",
    "cta": "...",
    "comment_strategy": "..."
  }}
}}"""

        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=3000,
            messages=[{'role': 'user', 'content': prompt}],
        )

        raw = message.content[0].text.strip()
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            result = json.loads(match.group())
            return _normalize_output(result)

    except Exception as exc:
        log.warning('Claude content optimization failed (%s) — falling back to static', exc)

    return _optimize_static(content, content_type, tone)


def _normalize_output(result: dict) -> dict:
    """Ensure all expected keys exist with string values."""
    platforms = {
        'linkedin':  ['copy', 'hashtags', 'first_comment'],
        'facebook':  ['copy', 'hashtags', 'first_comment'],
        'instagram': ['copy', 'hashtags', 'first_comment'],
        'tiktok':    ['copy', 'hashtags', 'overlay_text', 'first_comment'],
        'youtube':   ['title', 'description', 'hashtags', 'pinned_comment',
                      'discussion_question', 'cta', 'comment_strategy'],
    }
    out = {}
    for platform, keys in platforms.items():
        src = result.get(platform, {})
        out[platform] = {k: src.get(k, '') for k in keys}
    return out


# ── Static fallback optimizer ────────────────────────────────────────────────

def _optimize_static(content: str, content_type: str, tone: str) -> dict:
    """
    Deterministic static adapter. Takes the original content and builds
    meaningfully different versions for each platform without an API call.
    """
    lines   = [l.strip() for l in content.strip().split('\n') if l.strip()]
    first   = lines[0] if lines else content[:100]
    rest    = '\n'.join(lines[1:]) if len(lines) > 1 else ''
    preview = content[:200].strip()

    # ── LinkedIn ─────────────────────────────────────────────────────────────
    li_copy = content.strip()
    li_hash = '#leadership #operations #businessgrowth #strategy #founders'
    li_comment = (
        "I'd love to hear from others in the comments — "
        "what's your experience been with this? Happy to discuss."
    )

    # ── Facebook ─────────────────────────────────────────────────────────────
    fb_copy = (
        f"{first}\n\n"
        f"{rest[:300] + '...' if len(rest) > 300 else rest}\n\n"
        "What do you think? Drop a comment below — genuinely curious what others are seeing."
    ).strip()
    fb_hash = ''
    fb_comment = "Anyone else dealing with this? Share your experience — let's compare notes."

    # ── Instagram ────────────────────────────────────────────────────────────
    # Hook = first line, keep caption short, hashtags go in first_comment
    ig_copy = (
        f"{first}\n\n"
        f"{lines[1] if len(lines) > 1 else ''}\n\n"
        "Save this if it's useful. 👇"
    ).strip()
    ig_hashtags = (
        '#businessmindset #entrepreneurship #leadership #founders #growthmindset '
        '#operations #startups #buildinpublic #success #mindset '
        '#productivity #businessowner #smallbusiness #marketing #b2b'
    )
    ig_comment = ig_hashtags  # hashtags go in first comment on Instagram

    # ── TikTok ───────────────────────────────────────────────────────────────
    tk_copy = first[:150] if len(first) > 150 else first
    tk_hash = '#businesstok #learnontiktok #entrepreneur #founderlife #growthtips'
    # Extract a punchy 3–7 word overlay from the first line
    words = first.split()
    tk_overlay = ' '.join(words[:6]) if len(words) >= 6 else first[:40]
    tk_comment = "Do you agree or disagree? 👇 Tell me in 3 words"

    # ── YouTube ──────────────────────────────────────────────────────────────
    # Title: first line, trimmed to 65 chars
    yt_title = first[:65] if len(first) > 65 else first
    yt_description = (
        f"{content.strip()}\n\n"
        "─────────────────────────\n"
        "If this was useful, hit subscribe — I post one framework like this every week.\n\n"
        "Leave a comment below: what's your experience with this? "
        "I read and reply to every comment.\n\n"
        "─────────────────────────\n"
        "Chapters:\n"
        "0:00 — Introduction\n"
        "0:30 — The core idea\n"
        "2:00 — Why this matters\n"
        "4:00 — What to do next"
    )
    yt_hash = 'business, entrepreneurship, operations, leadership, founders'
    yt_pinned = (
        f"📌 Quick question for you: {first[:80]}...\n\n"
        "Have you dealt with this before? Reply with YES or NO — "
        "and if YES, drop what happened. I'll reply to every comment this week."
    )
    yt_question = "What's the one thing about this topic that nobody talks about honestly?"
    yt_cta = (
        "If this helped you, subscribe and hit the bell — "
        "I break down one real framework every week. No fluff."
    )
    yt_strategy = (
        "Pin your first comment immediately after publishing. "
        "Reply to every comment in the first 2 hours — this signals to the algorithm that the video drives engagement."
    )

    return {
        'linkedin':  {'copy': li_copy,    'hashtags': li_hash,    'first_comment': li_comment},
        'facebook':  {'copy': fb_copy,    'hashtags': fb_hash,    'first_comment': fb_comment},
        'instagram': {'copy': ig_copy,    'hashtags': ig_hashtags,'first_comment': ig_comment},
        'tiktok':    {'copy': tk_copy,    'hashtags': tk_hash,    'overlay_text': tk_overlay, 'first_comment': tk_comment},
        'youtube':   {
            'title':               yt_title,
            'description':         yt_description,
            'hashtags':            yt_hash,
            'pinned_comment':      yt_pinned,
            'discussion_question': yt_question,
            'cta':                 yt_cta,
            'comment_strategy':    yt_strategy,
        },
    }
