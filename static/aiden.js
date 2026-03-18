/* ═══════════════════════════════════════════════════════════════════════════
   aiden.js — Aiden Content Operations Command Center
   Version 2.0 — Master Asset Library + Multi-Platform Content Engine
   ═══════════════════════════════════════════════════════════════════════════ */
'use strict';

/* ═══════════════════════════════════════════════════════════════════════════
   BEST TIME RECOMMENDATION SERVICE
   INTEGRATION POINT: swap getRecommendation() body with fetch() to live
   analytics endpoint, LinkedIn API heatmap, or Expandi activity data.
   ═══════════════════════════════════════════════════════════════════════════ */
const BestTimeService = {
    _signals: {
        lifestyle: {
            primaryDay: 'Tuesday', primaryTime: '7:30 AM',
            reason: 'Lifestyle content peaks early — professionals scroll before their workday begins. Tuesday has the highest organic reach in this category.',
            alternatives: [{ day:'Thursday',time:'7:00 AM',score:'High'},{day:'Wednesday',time:'12:00 PM',score:'Medium-High'},{day:'Sunday',time:'8:00 PM',score:'Medium'}],
        },
        industry: {
            primaryDay: 'Wednesday', primaryTime: '8:00 AM',
            reason: 'Industry/professional content performs best mid-week when decision-makers are in planning mode. 8 AM captures the pre-meeting scroll window.',
            alternatives: [{day:'Tuesday',time:'8:30 AM',score:'High'},{day:'Thursday',time:'7:30 AM',score:'High'},{day:'Monday',time:'9:00 AM',score:'Medium'}],
        },
        aiden: {
            primaryDay: 'Tuesday', primaryTime: '9:00 AM',
            reason: 'Product/company content sees strongest B2B engagement Tuesday morning, when buyers are actively evaluating tools for the week.',
            alternatives: [{day:'Wednesday',time:'9:00 AM',score:'High'},{day:'Thursday',time:'8:00 AM',score:'Medium-High'},{day:'Monday',time:'10:00 AM',score:'Medium'}],
        },
        conflicting_opinion: {
            primaryDay: 'Thursday', primaryTime: '12:00 PM',
            reason: 'Opinion and debate content peaks at lunch — people share and comment when they have a moment to engage. Thursday lunch has a 2.4× higher comment rate.',
            alternatives: [{day:'Tuesday',time:'12:30 PM',score:'High'},{day:'Wednesday',time:'11:30 AM',score:'Medium-High'},{day:'Friday',time:'11:00 AM',score:'Medium'}],
        },
        default: {
            primaryDay: 'Tuesday', primaryTime: '8:00 AM',
            reason: 'Tuesday and Wednesday 8–10 AM windows consistently outperform for B2B LinkedIn content across most industries.',
            alternatives: [{day:'Wednesday',time:'8:30 AM',score:'High'},{day:'Thursday',time:'8:00 AM',score:'Medium-High'},{day:'Monday',time:'9:00 AM',score:'Medium'}],
        },
    },
    getRecommendation(category) {
        const key = (category || 'default').toLowerCase().replace(/\s+/g, '_');
        return this._signals[key] || this._signals.default;
    },
};


/* ═══════════════════════════════════════════════════════════════════════════
   PATTERN LIBRARY
   Central source of truth for all hook templates, CTA templates, post
   structures, and framing patterns. Extend this library — do not hardcode
   content directly into PostGenerator.
   All templates use {topic} as the injection slot.
   ═══════════════════════════════════════════════════════════════════════════ */
const PatternLibrary = {

    // ── 10 hook categories × 3 templates = 30 hook templates ─────────────
    // Each template has: text (with {topic} slot), engagement weight 1–10,
    // structure label, and which reading emotion it targets.
    hookTemplates: {
        contrarian: [
            { text: "The advice everyone gives about {topic}?\n\nIt's creating the problem.",                                                weight: 8, emotion: 'curiosity'  },
            { text: "You don't have a {topic} problem.\n\nYou have a decisions problem.",                                                   weight: 9, emotion: 'challenge' },
            { text: "{Topic} isn't hard.\n\nThe way most people approach it is.",                                                           weight: 7, emotion: 'challenge' },
        ],
        painful_truth: [
            { text: "Nobody tells you {topic} gets harder before it gets easier.",                                                          weight: 7, emotion: 'empathy'   },
            { text: "The reason your {topic} isn't working isn't what you think.",                                                          weight: 8, emotion: 'curiosity' },
            { text: "Most teams will never fix their {topic} problem.\n\nNot because they can't.\n\nBecause they won't face what it is.",   weight: 9, emotion: 'tension'   },
        ],
        hard_lesson: [
            { text: "3 years building around {topic}.\n\nThe lesson I wish I knew in year one:",                                           weight: 9, emotion: 'empathy'   },
            { text: "The {topic} mistake cost us 6 months and $80k.\n\nHere's exactly what we got wrong:",                                 weight:10, emotion: 'proof'     },
            { text: "I rebuilt our {topic} system from scratch last year.\n\nHere's why — and what actually changed:",                     weight: 8, emotion: 'story'     },
        ],
        mistake_callout: [
            { text: "Stop treating {topic} like a tactics problem.\n\nIt's a systems problem.",                                            weight: 9, emotion: 'challenge' },
            { text: "The biggest {topic} mistake:\n\nThinking more effort equals better results.",                                         weight: 8, emotion: 'challenge' },
            { text: "If your {topic} isn't working, check these 3 things before you do anything else:",                                    weight: 8, emotion: 'utility'   },
        ],
        pattern_interrupt: [
            { text: "The best {topic} decision I ever made wasn't a {topic} decision.",                                                    weight: 9, emotion: 'curiosity' },
            { text: "{Topic} isn't the bottleneck.\n\nYour tolerance for the wrong systems is.",                                           weight: 8, emotion: 'challenge' },
            { text: "The operator who fixes {topic} last usually wins.\n\nHere's why that's not a paradox:",                               weight: 7, emotion: 'curiosity' },
        ],
        authority_proof: [
            { text: "22 hours/week recovered. $180k saved. 6 weeks.\n\nThe {topic} system behind it:",                                    weight:10, emotion: 'proof'     },
            { text: "We've worked with 300+ {topic} operations.\n\nOne pattern separates the top 10% from everyone else:",                 weight: 9, emotion: 'proof'     },
            { text: "Before: 40% of the week lost to {topic}.\nAfter: fully systematized in 8 weeks.\n\nHere's the playbook:",             weight:10, emotion: 'proof'     },
        ],
        curiosity_gap: [
            { text: "There's one {topic} pattern most operators never see.\n\nThe ones who do are 3× more profitable.",                    weight: 9, emotion: 'curiosity' },
            { text: "I've watched 100+ teams try to fix {topic}.\n\nThe ones that succeed always do one thing first:",                     weight: 8, emotion: 'curiosity' },
            { text: "The {topic} insight that changed everything:\n\n(I wish someone had told me this in year one.)",                      weight: 8, emotion: 'curiosity' },
        ],
        myth_vs_reality: [
            { text: "Myth: {topic} is a resource problem.\n\nReality: it's a decisions problem.",                                          weight: 8, emotion: 'clarity'   },
            { text: "What everyone gets wrong about {topic}:\n\nIt's not an efficiency problem. It's a clarity problem.",                  weight: 9, emotion: 'clarity'   },
            { text: "The {topic} advice that sounds right — and consistently kills results:",                                               weight: 8, emotion: 'tension'   },
        ],
        you_think_x: [
            { text: "You think {topic} is your bottleneck.\n\nIt's not.\n\nHere's the real one:",                                          weight:10, emotion: 'challenge' },
            { text: "If {topic} isn't working, it's probably not a {topic} problem.",                                                      weight: 9, emotion: 'challenge' },
            { text: "Everyone blames {topic}.\n\nThe real issue is almost always the system behind it.",                                   weight: 8, emotion: 'challenge' },
        ],
        warning: [
            { text: "If you're scaling {topic} before fixing the fundamentals, stop.\n\nYou're amplifying the problem.",                   weight: 9, emotion: 'urgency'   },
            { text: "Warning: the way most teams handle {topic} creates a bigger problem 90 days later.",                                  weight: 8, emotion: 'urgency'   },
            { text: "Before you invest more in {topic}:\n\nAsk yourself these 3 questions first.",                                         weight: 8, emotion: 'urgency'   },
        ],
    },

    // ── 20 CTA templates organized by engagement goal ─────────────────────
    ctaTemplates: {
        comment: [
            "What's your take on this?\n\nDrop it in the comments — I read and respond to every one.",
            "Agree or disagree?\n\nTell me in the comments. I'll respond to every serious take.",
            "Where are you at with this right now?\n\nDrop it below — seriously curious.",
            "What am I missing?\n\nBest counterargument in the comments gets a full reply.",
            "Which part of this hits hardest for your operation?\n\nComment below.",
        ],
        save: [
            "Save this.\n\nYou'll want it when the problem shows up.",
            "Bookmark this before it gets buried.\n\nRun it when you're ready to fix this properly.",
            "Save this for later.\n\nStep 1 alone is worth the 30 seconds.",
        ],
        share: [
            "If this hit home, share it.\n\nSomeone on your team needs to read this today.",
            "Tag an operator you know who's dealing with this right now.",
            "Send this to one founder who's working too hard on the wrong things.",
        ],
        dm: [
            "DM me 'audit' and I'll share the full breakdown for your setup.",
            "Want to see how this applies to your operation?\n\nDM me — I'll walk through it with you.",
            "If you want the full system, reply to this or DM me directly.",
            "DM me 'framework' and I'll send you the exact template we use.",
        ],
        follow: [
            "If this was useful, follow me.\n\nI post the operator's version of this every week.",
            "Follow for the unpolished version of what's actually working in operations.",
            "If you found this valuable — I post one framework like this every week.\n\nFollow along.",
        ],
    },

    // ── 15 post structures with slot definitions ──────────────────────────
    structures: [
        { id: 'hook_insight_example_takeaway', label: 'Hook → Insight → Example → Takeaway', angle: 'lesson' },
        { id: 'hook_story_lesson',             label: 'Hook → Story → Lesson',                angle: 'story'  },
        { id: 'hook_myth_truth_application',   label: 'Hook → Myth → Truth → Application',   angle: 'contrarian' },
        { id: 'hook_problem_consequence_fix',  label: 'Hook → Problem → Consequence → Fix',  angle: 'lesson' },
        { id: 'hook_proof_principle_cta',      label: 'Hook → Proof → Principle → CTA',      angle: 'proof'  },
        { id: 'list_with_context',             label: 'Hook → Context → List → Closer',       angle: 'lesson' },
        { id: 'hot_take',                      label: 'Hot Take → Defense → Nuance → Invite', angle: 'contrarian' },
    ],

    // ── Body content blocks per angle — fill-able with {topic} ───────────
    bodyBlocks: {
        story: {
            setup: [
                "Here's the version most people don't share.\n\nWe were 4 months in. Every week felt like a firefight.\n\nThe team was good. The effort was real.\n\nBut nothing was compounding.",
                "A client came to me with a {topic} problem that had been building for 2 years.\n\nEvery fix they'd tried had made it worse.\n\nNot because they were doing it wrong.\n\nBecause they were solving the wrong problem.",
                "I spent 18 months building the wrong version of our {topic} system.\n\nGood intentions. Wrong diagnosis.",
            ],
            conflict: [
                "The tempting move was to add headcount.\n\nWe almost did.\n\nInstead, we made one decision:\n\nStop doing manually what a system can do better.",
                "Every 'solution' they tried added complexity.\n\nMore tools. More meetings. More process.\n\nThe team was working harder.\n\nThe results were getting worse.",
                "The pressure to do more was real.\n\nThe right answer was to do less — but differently.",
            ],
            resolution: [
                "Month 5: first system shipped.\nMonth 6: 12 hours/week recovered.\nMonth 9: output 3×, same team.",
                "8 weeks later: the problem was solved.\nNot by adding resources — by removing the right friction.",
                "The result wasn't instant. But it compounded.\n\nBy quarter 3, it was unrecognizable.",
            ],
            lesson: [
                "The business didn't change. The operating model did.\n\nSame people. Different decisions.",
                "The lesson: most {topic} problems are systems problems wearing the costume of people problems.",
                "What I learned: the bottleneck is almost never what it looks like from the outside.",
            ],
        },
        lesson: {
            insight: [
                "Here's what most teams get wrong:\n\nThey optimize {topic} at the task level when the problem lives at the system level.",
                "The teams quietly winning at {topic} share one trait.\n\nIt's not budget. It's not talent. It's not tools.\n\nIt's this:",
                "There's a pattern across every {topic} operation that works:\n\nSimplicity compounds. Complexity kills.",
            ],
            list_items: [
                "→ If a human does the same thing twice, a system should do it once.\n→ Start with the highest-volume task, not the most annoying one.\n→ Simple beats smart — every system should be explainable in one sentence.\n→ Measure before and after. No delta = no proof.\n→ Document before you delegate. Delegate before you scale.",
                "→ 78% of ops teams still run this process manually.\n→ Manual = 3–5× more errors, 4× longer cycle time.\n→ Payback period after fixing it: average 11 weeks.\n→ Teams that fix it in year 1 are 2.4× more profitable by year 3.",
                "→ Audit where the time actually goes. Most leaders are shocked.\n→ Target the 3 highest-volume manual tasks first.\n→ Build the simplest possible system. Start ugly.\n→ Measure the before-and-after. Document the delta.\n→ Repeat.",
            ],
            closer: [
                "None of this is complicated.\n\nAll of it requires the decision to actually start.",
                "The math isn't hard. The execution is what stops most people.",
                "This isn't advanced strategy. It's the boring fundamentals done exceptionally well.",
            ],
        },
        contrarian: {
            myth: [
                "The common belief: more {topic} investment = better {topic} results.\n\nThe data says otherwise.",
                "What gets talked about: more tools, more automation, more hires.\n\nWhat actually works: fewer decisions, simpler systems, ruthless prioritization.",
                "Everyone talks about {topic} like it's a capacity problem.\n\nIt's almost never a capacity problem.",
            ],
            truth: [
                "The teams quietly winning at {topic} aren't doing anything fancy.\n\nThey're doing the boring fundamentals better than everyone else.\n\nConsistency > Virality.\nProcess > Hustle.\nSimple > Smart.",
                "The operators I've watched build durable advantages all share this:\n\nThey removed decisions before they added resources.",
                "High-performing {topic} operations have fewer moving parts, not more.\n\nEvery added layer is a new place for things to break.",
            ],
            application: [
                "Build the thing that compounds.\n\nNot the thing that impresses.",
                "Before adding anything to your {topic} stack — ask: does this reduce decisions or add them?",
                "The 3-year outcome matters more than the 3-month spike.\n\nAct accordingly.",
            ],
        },
        proof: {
            setup: [
                "12-person team. $180k wasted per year on manual {topic} work.\n\nWe fixed it in 6 weeks.",
                "We ran this system with 30+ operations teams in the last 18 months.\n\nThe average result:",
                "Before/after for a mid-market freight operation:\n\nBefore: 14 hrs/week on {topic}.\nAfter: 90 minutes.",
            ],
            breakdown: [
                "What changed:\n→ Automated reporting: 6 hrs/week → 18 minutes.\n→ Automated qualification: 3 hrs/day → real-time.\n→ Automated follow-up: manual → zero-touch.\n\nResult: 22 hours/week recovered. $180k annualized.",
                "The 3 interventions:\n→ Eliminated the highest-volume manual task entirely.\n→ Automated the decision layer, not just the execution layer.\n→ Reduced the number of tools by 40%.\n\nTimeline: 8 weeks. ROI: 11×.",
                "The numbers at 90 days:\n→ Time saved: 22 hrs/week per person\n→ Error rate: down 76%\n→ Team morale: dramatically improved\n→ Cost to implement: 6 weeks of focused work",
            ],
            principle: [
                "The principle: you can't fix execution problems by adding execution capacity.\n\nFix the system. Then scale it.",
                "What this proves: the bottleneck was never people.\n\nIt was the number of manual decisions they had to make.",
                "The replicable insight:\n\nEvery operation has a $100k+ inefficiency hiding in plain sight.\n\nYou find it by measuring what you've been ignoring.",
            ],
        },
    },

    // ── Contrarian framing templates ──────────────────────────────────────
    contrarianFrames: [
        "The conventional wisdom on {topic}: [conventional].\n\nWhat actually works: [reality].\n\nThe difference: [difference].",
        "Everyone optimizes {topic} for the wrong metric.\n\nThe teams quietly winning optimize for [right_metric].",
        "More [resource] doesn't fix {topic}.\n\nBetter [alternative] does.\n\nHere's the distinction:",
    ],

    // ── Mistake templates ─────────────────────────────────────────────────
    mistakeTemplates: [
        "The {topic} mistake I see most often:\n\n[mistake].\n\nWhy it happens:\n[reason].\n\nThe fix:\n[fix].",
        "3 {topic} mistakes that are silently killing results:\n\n1. [mistake_1]\n2. [mistake_2]\n3. [mistake_3]\n\nThe one that matters most: [biggest].",
        "I made this {topic} mistake for 2 years.\n\nCost: [cost].\n\nWhat I'd do instead:\n[alternative].",
    ],

    // ── Painful truth templates ───────────────────────────────────────────
    painfulTruthTemplates: [
        "The painful truth about {topic}:\n\n[truth].\n\nMost people never face this because [reason].\n\nThe ones who do [outcome].",
        "Nobody wants to hear this about {topic}:\n\n[uncomfortable_fact].\n\nBut it explains why [phenomenon].",
        "If you're honest about your {topic} situation, you'll notice:\n\n[observation].\n\nThat's not a {topic} problem.\n\nThat's a [real_issue] problem.",
    ],

    // ── Proof / result templates ──────────────────────────────────────────
    proofResultTemplates: [
        "[result] in [timeframe].\n\nWhat changed:\n\n[change_1]\n[change_2]\n[change_3]\n\nThe underlying principle:\n\n[principle].",
        "Before: [before_state].\nAfter: [after_state].\nTime to get there: [duration].\n\nThe 3 decisions that made the difference:\n\n[decisions].",
        "Case study: [description].\n\nThe numbers:\n→ [metric_1]\n→ [metric_2]\n→ [metric_3]\n\nReplicable? Yes. Here's how:",
    ],

    // ── Style mode definitions ────────────────────────────────────────────
    styleModes: {
        operator_founder:    { label: 'Operator / Founder', ctaGoal: 'comment', tone: 'direct'      },
        contrarian:          { label: 'Contrarian',         ctaGoal: 'comment', tone: 'spiky'       },
        executive_friendly:  { label: 'Executive',          ctaGoal: 'dm',      tone: 'polished'    },
        personal_story:      { label: 'Personal Story',     ctaGoal: 'follow',  tone: 'vulnerable'  },
        authority_building:  { label: 'Authority',          ctaGoal: 'save',    tone: 'proof-first' },
        comment_bait:        { label: 'Comment Bait',       ctaGoal: 'comment', tone: 'divisive'    },
        educational:         { label: 'Educational',        ctaGoal: 'save',    tone: 'clear'       },
        punchy:              { label: 'Punchy',             ctaGoal: 'share',   tone: 'sharp'       },
    },
};


/* ═══════════════════════════════════════════════════════════════════════════
   POST GENERATOR  v3.0 — pattern-based originality engine
   Uses PatternLibrary as the single source of templates.
   Generates original content by combining user topics with proven structural
   patterns extracted from high-engagement LinkedIn post analysis.
   Does NOT clone any creator — extracts structure, not voice.
   INTEGRATION POINT: replace generateIdeas() / generateOptions() with
   fetch('/api/aiden/generate', { method:'POST', body: JSON.stringify({...}) })
   ═══════════════════════════════════════════════════════════════════════════ */
const PostGenerator = {

    // ── Deterministic hash ────────────────────────────────────────────────
    _hash(str) {
        let h = 0;
        for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) & 0xffffffff;
        return Math.abs(h);
    },

    _titleCase(str) {
        return (str || '').replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
    },

    // ── Async hook generation — calls backend API ─────────────────────────
    // Returns Promise<[{ hook, type, weight, emotion, score }]>
    async generateIdeasAsync(topic, styleMode, category) {
        const resp = await fetch('/api/aiden/generate-hooks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, style_mode: styleMode, category }),
        });
        if (!resp.ok) throw new Error(`API ${resp.status}`);
        const data = await resp.json();
        const hooks = data.hooks || [];
        this._lastAiPowered = data.ai_powered || false;
        return hooks.map(h => ({
            hook:    h.hook    || '',
            type:    h.type    || 'observation',
            emotion: h.emotion || 'curiosity',
            weight:  h.weight  || 7,
            score:   PostScorer.scoreHook(h.hook || '', h),
        }));
    },

    // ── Generate 10 hooks — 1 from each PatternLibrary category ──────────
    // Returns: [{ hook, type, weight, emotion, score }]
    // Sync fallback (used if API call fails)
    generateIdeas(topic, angle, category) {
        const categories = Object.keys(PatternLibrary.hookTemplates);
        const hash = this._hash((topic || '') + (angle || '') + (category || ''));
        return categories.map((cat, i) => {
            const pool = PatternLibrary.hookTemplates[cat];
            const item = pool[(hash + i) % pool.length];
            const hookText = item.text
                .replace(/\{topic\}/g, topic || 'this')
                .replace(/\{Topic\}/g, this._titleCase(topic || 'This'));
            const score = PostScorer.scoreHook(hookText, item);
            return { hook: hookText, type: cat, weight: item.weight, emotion: item.emotion, score };
        });
    },

    // ── Generate 4 content options from a selected hook ───────────────────
    // Returns: [{ hook, body, cta, hashtags, imageIdea, angle, structure, mode, score }]
    generateOptions(topic, hookObj, category, assetType, styleMode) {
        const angles = ['story', 'lesson', 'contrarian', 'proof'];
        const modes  = ['full', 'full', 'spiky', 'executive'];
        const hash   = this._hash((topic || '') + (hookObj?.hook || '') + (category || ''));
        return angles.map((ang, i) => {
            const struct   = this._pickStructure(ang, hash + i);
            const body     = this._buildBody(topic, ang, struct, hash + i * 7);
            const cta      = this._pickCta(styleMode, ang, hash + i * 3);
            const hashtags = this._pickHashtags(category);
            const imageIdea= this._imageIdea(ang);
            const post = {
                hook: hookObj?.hook || '',
                body, cta, hashtags, imageIdea,
                angle: ang,
                structure: struct?.label || ang,
                mode: modes[i],
            };
            post.score = PostScorer.score(post);
            return post;
        });
    },

    // ── Generate a single full post ───────────────────────────────────────
    generatePost(topic, angle, category, selectedHook, mode) {
        mode = mode || 'full';
        const hash     = this._hash((topic || '') + (angle || '') + (selectedHook || '') + mode);
        const hookText = selectedHook || this.generateIdeas(topic, angle, category)[0]?.hook || '';
        const struct   = this._pickStructure(angle, hash);
        const body     = this._buildBody(topic, angle, struct, hash);
        const cta      = this._pickCta(null, angle, hash);
        const hashtags = this._pickHashtags(category);
        const imageIdea= this._imageIdea(angle);

        let finalHook = hookText;
        if (mode === 'spiky' && !/Unpopular|won't|wrong/i.test(finalHook)) {
            finalHook = "Let me say what most people won't:\n\n" + finalHook;
        }
        if (mode === 'executive') {
            finalHook = finalHook
                .replace(/Stop /g, 'Consider moving past ')
                .replace(/\bwrong\b/g, 'worth revisiting')
                .replace(/Hot take:/gi, 'A perspective worth considering:');
        }

        const post = { hook: finalHook, body, cta, hashtags, imageIdea, angle, structure: struct?.label || angle, mode };
        const scored = PostScorer.score(post);
        if (scored.total < 42 && mode === 'full') return PostScorer.strengthen(post, scored);
        return { ...post, score: scored };
    },

    // ── Generate spiky variant ────────────────────────────────────────────
    generateSpiky(post) {
        const spiky = { ...post, mode: 'spiky' };
        spiky.hook  = "Let me say what most people won't:\n\n" + post.hook;
        spiky.body  = post.body + "\n\nMost won't act on this.\n\nThe ones who do will be miles ahead in 12 months.";
        spiky.cta   = "Who's going to push back on this? Tell me in the comments.";
        spiky.score = PostScorer.score(spiky);
        return spiky;
    },

    // ── Generate executive / polished variant ─────────────────────────────
    generateExecutive(post, angle) {
        const exec  = { ...post, mode: 'executive' };
        exec.hook   = post.hook
            .replace(/Stop /g, 'It may be time to move past ')
            .replace(/\bwrong\b/g, 'worth revisiting')
            .replace(/Hot take:/gi, 'A considered perspective:')
            .replace(/^Steal this/i, 'A framework worth considering');
        const pool  = PatternLibrary.ctaTemplates.dm;
        exec.cta    = pool[0];
        exec.score  = PostScorer.score(exec);
        return exec;
    },

    // ── Internal helpers ──────────────────────────────────────────────────
    _pickStructure(angle, hash) {
        const byAngle = PatternLibrary.structures.filter(s => s.angle === angle);
        const pool    = byAngle.length ? byAngle : PatternLibrary.structures;
        return pool[Math.abs(hash) % pool.length];
    },

    _buildBody(topic, angle, structure, hash) {
        const blocks = PatternLibrary.bodyBlocks[angle] || PatternLibrary.bodyBlocks.lesson;
        const t = topic || 'this';
        let h = Math.abs(hash);
        return Object.values(blocks).map(pool => {
            const tpl = pool[h % pool.length];
            h = Math.abs((h * 31 + 17) & 0xffffffff);
            return tpl.replace(/\{topic\}/g, t).replace(/\{Topic\}/g, this._titleCase(t));
        }).join('\n\n');
    },

    _pickCta(styleMode, angle, hash) {
        const mode = PatternLibrary.styleModes?.[styleMode];
        const ctaGoal = mode?.ctaGoal ||
            (angle === 'contrarian' ? 'comment' :
             angle === 'proof'      ? 'dm'      :
             angle === 'lesson'     ? 'save'    : 'follow');
        const pool = PatternLibrary.ctaTemplates[ctaGoal] || PatternLibrary.ctaTemplates.comment;
        return pool[Math.abs(hash || 0) % pool.length];
    },

    _pickHashtags(category) {
        const map = {
            industry:            '#logistics #operations #freight #supplychain #automation',
            lifestyle:           '#entrepreneurship #productivity #mindset #leadership #growth',
            aiden:               '#AI #automation #b2b #operationsai #businessgrowth',
            conflicting_opinion: '#leadership #sales #marketing #businessstrategy #hotTake',
        };
        return map[(category || 'industry').toLowerCase().replace(/\s+/g, '_')] || map.industry;
    },

    _imageIdea(angle) {
        const map = {
            story:      'Timeline graphic: 3 frames (Before / Turning Point / After). Dark bg, minimal text. Pull one specific number.',
            lesson:     'Numbered steps graphic (1–5) with step name only. High contrast, dark background. Add "save this" bottom-right.',
            contrarian: 'Bold text card — the contrarian statement in large type, no softening. Red or orange accent.',
            proof:      'Results card: outcome metrics only ($, hours, timeline). Clean before/after bar. Dark bg.',
        };
        return map[angle] || map.story;
    },

    // ────────────────────────────────────────────────────────────────────
    // LEGACY HOOKS (kept for reference — not used by v3.0 generator)
    // ────────────────────────────────────────────────────────────────────
    _hooks: {
        personal_story: [
            // narrative
            { style:'narrative',    text:"I almost shut it all down at month 4.\n\nThen one decision changed everything." },
            { style:'narrative',    text:"Year one of building this: constant chaos, no margin, team exhausted.\n\nYear two: completely different company. Here's what changed." },
            { style:'statement',    text:"The worst decision I made in operations cost us $180k.\n\nI'm sharing it so you don't make the same one." },
            { style:'statement',    text:"Nobody talks about the 18 months before the win.\n\nHere's ours — unfiltered." },
            { style:'question',     text:"What do you do when the thing you built stops working?\n\nHere's what we did." },
            { style:'command',      text:"Stop building around {topic} the way everyone else does.\n\nI did it wrong for two years. Here's what actually worked." },
            { style:'conditional',  text:"If you're running {topic} manually and wondering why growth stalled — this is the post for you." },
            { style:'provocation',  text:"Most founders are too proud to admit their {topic} is broken.\n\nWe weren't." },
            { style:'narrative',    text:"6 months ago, {topic} was our biggest liability.\n\nToday it's our biggest advantage. The shift took 11 weeks." },
            { style:'list_number',  text:"3 things I wish I knew about {topic} before we scaled:\n\n(Number 2 would have saved us $60k.)" },
        ],
        data_driven: [
            { style:'statement',    text:"Most businesses are hemorrhaging money on {topic} and don't know it.\n\nThe average waste: 14 hours per person per week." },
            { style:'list_number',  text:"3 numbers that will change how you think about {topic}:\n\n(Most operators have never run this calculation.)" },
            { style:'question',     text:"Do you know your real cost per hour of manual {topic}?\n\nMost teams guess $20. The actual number is usually 4× that." },
            { style:'statement',    text:"We analyzed 500+ {topic} operations.\n\nOne pattern separated the top 10% from everyone else. It's not what you'd expect." },
            { style:'provocation',  text:"78% of teams still run {topic} manually.\n\nThat's not a process problem. It's a decision problem." },
            { style:'conditional',  text:"If your {topic} ROI isn't compound — you're doing it wrong.\n\nHere's what the math actually looks like." },
            { style:'statement',    text:"Here's the {topic} benchmark nobody shares:\n\nTop operators: under 2 hrs/week. Average team: 14+ hrs/week.\n\nThe gap is fixable in 90 days." },
            { style:'command',      text:"Run this calculation right now.\n\nHow many hours does your team spend on {topic} per week?\n\nMultiply by your hourly cost. That's your baseline." },
            { style:'question',     text:"What if I told you your {topic} problem isn't a people problem?\n\nThe data says it's almost always a systems problem." },
            { style:'list_number',  text:"5 metrics every operator should track in {topic}.\n\nMost track none. Top performers track all 5." },
        ],
        how_to: [
            { style:'command',      text:"Stop hiring your way out of a {topic} problem.\n\nHere's the 5-step fix that costs nothing to start." },
            { style:'list_number',  text:"5 steps to cut {topic} overhead by 40% this quarter.\n\nNo new hires. No expensive software. Just execution." },
            { style:'statement',    text:"The simplest {topic} system I've ever seen works in 5 steps.\n\nMost teams overcomplicate it by step one." },
            { style:'command',      text:"Steal this {topic} framework.\n\nWe've used it to recover 20+ hours per week for 30+ clients." },
            { style:'conditional',  text:"If you're still doing {topic} the way you did 2 years ago — this framework will change your week." },
            { style:'question',     text:"What would your business look like with 20 extra hours per week?\n\nThis 5-step {topic} system gets you there." },
            { style:'command',      text:"Here's the exact {topic} playbook.\n\nSave this. Run it. Report back." },
            { style:'list_number',  text:"4 {topic} mistakes that add up to 20+ hours/week of wasted time:\n\n(And the fix for each one.)" },
            { style:'narrative',    text:"A client came to us drowning in {topic} work.\n\n8 weeks later: 22 hours recovered per week, $180k saved annually.\n\nHere's the exact system." },
            { style:'statement',    text:"Great {topic} isn't complicated.\n\nIt's five decisions, made once, executed consistently." },
        ],
        contrarian: [
            { style:'provocation',  text:"Unpopular opinion: your {topic} problem isn't a capacity problem.\n\nIt's a decisions problem. And more hires won't fix it." },
            { style:'statement',    text:"The conventional advice on {topic} is keeping you stuck.\n\nHere's what actually works (and why nobody talks about it)." },
            { style:'provocation',  text:"Every 'expert' is telling you the same thing about {topic}.\n\nThey're all wrong. Here's the proof." },
            { style:'question',     text:"What if everything you've been told about scaling {topic} is backwards?\n\nFor most operators, it is." },
            { style:'statement',    text:"More tools won't fix your {topic}.\n\nFewer decisions will.\n\nHere's the distinction that changes everything." },
            { style:'narrative',    text:"I spent 2 years doing {topic} the 'right' way.\n\nWasted $400k.\n\nHere's what I do now." },
            { style:'provocation',  text:"The reason your {topic} isn't working has nothing to do with effort.\n\nIt has everything to do with what you're measuring." },
            { style:'conditional',  text:"If you're adding headcount to solve a {topic} problem — stop reading and do this first." },
            { style:'statement',    text:"The businesses quietly winning at {topic} share one trait.\n\nIt's not budget. It's not talent.\n\nIt's this." },
            { style:'command',      text:"Challenge your {topic} assumptions.\n\nEvery framework you've inherited was built for a different era." },
        ],
        case_study: [
            { style:'statement',    text:"12-person team. $180k wasted per year on {topic}.\n\nWe fixed it in 6 weeks. Here's exactly what we did." },
            { style:'list_number',  text:"3 changes. 6 weeks. $240k saved.\n\nHere's the full breakdown of how we overhauled a {topic} operation." },
            { style:'narrative',    text:"Client called us in January.\n\n{topic} was eating 40% of their week.\n\nBy March: fully systematized. Here's the playbook." },
            { style:'statement',    text:"Best ROI we've ever delivered: 11× in 90 days.\n\nIt came from fixing one {topic} bottleneck. Full breakdown." },
            { style:'question',     text:"What does a 60% reduction in {topic} costs actually look like in practice?\n\nHere's a real case study with real numbers." },
            { style:'narrative',    text:"Before: 14 hours/week on {topic}. After: 90 minutes.\n\nSame team. Same tools. Different system. Here's what changed." },
            { style:'statement',    text:"The most impactful {topic} project we ran this year didn't involve a single new hire.\n\nIt involved three automations. Here's the breakdown." },
            { style:'command',      text:"Read this before you hire anyone to solve your {topic} problem.\n\nA client was about to add 2 FTEs. We found a better path." },
            { style:'list_number',  text:"4 weeks. 3 systems. 1 team.\n\nHere's how we turned {topic} from a cost center into a competitive advantage." },
            { style:'provocation',  text:"Nobody talks about what goes wrong during a {topic} overhaul.\n\nWe do. Here's the unfiltered case study." },
        ],
        question_hook: [
            { style:'question',     text:"How much is manual {topic} costing your business per year?\n\nMost operators have never done the math. The number is usually shocking." },
            { style:'question',     text:"When's the last time you actually looked at what {topic} costs you per week?\n\nMost leaders can't answer this." },
            { style:'conditional',  text:"If {topic} disappeared from your operations tomorrow — what would actually break?\n\nThat answer tells you everything." },
            { style:'question',     text:"What if {topic} is the bottleneck holding everything else back?\n\nFor most operators, it is — they just haven't named it yet." },
            { style:'question',     text:"Is your {topic} built to scale — or built to survive?\n\nBig difference. Here's how to tell." },
            { style:'provocation',  text:"Your team is working hard.\n\nBut is {topic} the reason the results don't match the effort?" },
            { style:'conditional',  text:"If you had 20 extra hours this week, what would you build?\n\nA better {topic} system could give you that. Here's how." },
            { style:'question',     text:"What would need to be true for {topic} to run without you?\n\nThat question is worth a full afternoon." },
            { style:'statement',    text:"The best operators I know don't work harder on {topic}.\n\nThey've made it nearly invisible. Here's the difference." },
            { style:'question',     text:"Are you solving {topic} — or just managing it?\n\nMost teams are doing the second one and calling it the first." },
        ],
    },

    // ── Body templates — 3 formats: list | steps | story ─────────────────
    _bodies: {
        personal_story: {
            story: `Here's the version most people don't share.\n\nWe were 4 months in. Every week felt like a firefight.\n\nThe team was good. The effort was real. But nothing was compounding.\n\nI almost made the expensive mistake of adding headcount.\n\nInstead, we made one decision:\n\nStop doing manually what a system can do better.\n\nMonth 5: first system shipped.\nMonth 6: 12 hours/week recovered.\nMonth 9: team morale flipped. Output 3×.\n\nSame people. Different decisions.\n\nThe business didn't change. The operating model did.`,
            list:  `What nobody tells you before you build:\n\n→ The first 90 days will feel broken even when they're working.\n→ Your biggest inefficiency is usually hiding in plain sight.\n→ The fix is almost never a new hire.\n→ Systems compound. Effort doesn't.\n→ One good decision at the right time beats 10 months of grinding.\n\nI learned all of this the expensive way.\n\nYou don't have to.`,
        },
        data_driven: {
            list:  `Here's what the data actually shows:\n\n→ 78% of operations teams still run this process manually.\n→ Manual work = 3–5× more errors, 4× longer cycle time.\n→ Average cost of that error rate: $47k/year per team.\n→ Payback period after fixing it: 11 weeks.\n→ Teams that fix it in year 1 are 2.4× more profitable by year 3.\n\nThis isn't a people problem.\n\nIt's a systems problem.\n\nAnd it has a very specific solution.`,
            steps: `Run this audit in 30 minutes:\n\nStep 1 — List every repeating task your team does weekly.\nStep 2 — Time each one. Be honest. Most people underestimate by 40%.\nStep 3 — Multiply hours × loaded hourly cost.\nStep 4 — Add error rate cost. (Every manual process has one.)\nStep 5 — That's your baseline. That's what inefficiency actually costs.\n\nFor most teams: $80k–$300k per year.\n\nFor some: over $1M.\n\nYou can't fix what you haven't measured.`,
        },
        how_to: {
            steps: `Here's the only framework you need (steal this):\n\nStep 1 — Map every manual task that happens more than twice a week.\nStep 2 — Sort by volume × time. Your top 3 are your targets.\nStep 3 — Build the simplest possible system for each. Don't over-engineer.\nStep 4 — Measure before and after. Document the delta.\nStep 5 — Once it's running, move to the next three.\n\nSetup time: 2–3 weeks per system.\nTime saved: 10–20 hrs/week per system.\n\nDon't wait for perfect. Start with messy.\n\nMessy and running beats perfect and not started every time.`,
            list:  `The rules that actually work:\n\n→ If a human does it the same way every time, a system should do it.\n→ Start with the highest-volume tasks, not the most annoying ones.\n→ Simple beats smart — every system should be explainable in one sentence.\n→ Measure before and after. No metric = no proof it worked.\n→ Once it's stable, document it. Once it's documented, delegate it.\n\nNone of this is complicated.\n\nAll of it requires the decision to actually start.`,
        },
        contrarian: {
            list:  `Here's what actually separates the teams quietly winning:\n\n→ They're not using more tools. They're using fewer.\n→ They're not adding people. They're removing decisions.\n→ They're not chasing growth. They're eliminating drag.\n→ They don't talk about their systems. They just run them.\n\nConsistency > Virality.\nProcess > Hustle.\nSimple > Smart.\n\nThe playbook isn't exciting.\n\nThat's exactly why it works.`,
            story: `I've watched the same pattern repeat across 100+ operators.\n\nThe ones who talk the most about their strategy? Usually struggling.\n\nThe ones quietly building systems and compounding? Winning by a mile.\n\nThe gap isn't vision. Everyone has that.\n\nThe gap is:\n\nDo you do the boring thing consistently?\n\nMost don't.\n\nThat's the actual competitive advantage.`,
        },
        case_study: {
            story: `Here's the full breakdown.\n\nThe situation: 12-person team, fully manual processes, 40% of every week evaporating into admin work.\n\nWhat we changed:\n→ Automated weekly reporting: 6 hrs/week → 18 minutes.\n→ Automated lead qualification: 3 hrs/day → real-time, zero touch.\n→ Automated follow-up sequences: manual → fully hands-off.\n\nThe result after 6 weeks:\n→ 22 hours/week recovered.\n→ $180k annualized savings.\n→ Team morale: dramatically different.\n\nNothing flashy. No reorg. No new hires.\n\nJust the decision to stop tolerating what a system could handle.`,
            list:  `What made the difference:\n\n→ We started with measurement, not solutions.\n→ We fixed the highest-volume task first (not the most annoying one).\n→ We kept every system simple enough to explain in one sentence.\n→ We documented before we delegated.\n→ We measured the delta at 30, 60, and 90 days.\n\nTotal investment: 6 weeks of focused implementation.\nAnnual return: $180k saved, 22 hrs/week recovered.\n\nROI: north of 11×.\n\nThe math works. The discipline is the hard part.`,
        },
        question_hook: {
            story: `Here's what most operators discover when they actually run the numbers:\n\nThe bottleneck isn't effort.\n\nIt's not talent.\n\nIt's not budget.\n\nIt's the fact that 30–40% of the team's week is going to work that a system could handle in minutes.\n\nAnd the reason it hasn't been fixed isn't complexity.\n\nIt's that nobody's made it the priority.\n\nUntil they do the math.\n\nDo the math.`,
            list:  `Most operators can't answer these questions:\n\n→ How many hours per week goes to tasks that repeat identically?\n→ What's the loaded cost of each manual error?\n→ How much of your team's week is value creation vs. administration?\n→ What would you build if you had 15 more hours per week?\n\nThe gap between where you are and where you want to be?\n\nIt usually lives inside those four questions.\n\nThe answers are uncomfortable.\n\nThat's exactly why they're worth finding.`,
        },
    },

    // ── CTAs — designed for comment pull and shareability ─────────────────
    _ctas: {
        personal_story:  "What was the decision that changed things for you?\n\nDrop it below — I read and respond to every comment.",
        data_driven:     "Want to run this calculation for your operation?\n\nDM me \"data\" — I'll walk you through it personally.",
        how_to:          "Save this.\n\nRun Step 1 this week. Come back and tell me what you found.",
        contrarian:      "Agree? Disagree? I want to hear the counterargument.\n\nDrop it in the comments — I'll respond to every serious take.",
        case_study:      "Curious what this looks like for your operation?\n\nDM me — I'll do a quick 20-min audit call. No pitch.",
        question_hook:   "If this hit close to home — follow me.\n\nI post the real version of what's working in operations, every week.",
    },

    // ── Executive / polished CTA variants (mode: executive) ───────────────
    _ctasExec: {
        personal_story:  "What inflection point have you experienced in your organization?\n\nI welcome perspectives in the comments.",
        data_driven:     "Happy to share the full analysis with operators who find this relevant. Reach out directly.",
        how_to:          "This framework is available in full to those who'd like to apply it to their context. Feel free to connect.",
        contrarian:      "I'm genuinely curious about alternative perspectives on this. The conversation in the comments is always worthwhile.",
        case_study:      "If your organization faces similar challenges, I'm glad to discuss how this approach might apply to your context.",
        question_hook:   "These are the questions I find most valuable in conversation with operators. Happy to explore further.",
    },

    // ── Hashtags ───────────────────────────────────────────────────────────
    _hashtags: {
        lifestyle:           '#entrepreneurship #productivity #mindset #leadership #growth',
        industry:            '#logistics #operations #freight #supplychain #automation',
        aiden:               '#AI #automation #b2b #operationsai #businessgrowth',
        conflicting_opinion: '#leadership #sales #marketing #businessstrategy #hotTake',
    },

    // ── Image direction per angle ──────────────────────────────────────────
    _imageIdeas: {
        personal_story: 'Timeline graphic: 3 frames (Month 1 / Month 6 / Month 9) showing before → turning point → result. Dark bg, minimal text. Pull one specific number from the post.',
        data_driven:    'Single-stat data card — lead with the most arresting number in large type. High contrast dark background, no clutter. Optional: small before/after bar beneath.',
        how_to:         'Numbered steps graphic (1–5) with the step name only — no filler text. High contrast, dark background. Add "save this" in small text bottom-right corner.',
        contrarian:     'Bold text card — the contrarian statement in large type, no softening language. Red or orange accent. Visual should feel like a mild provocation.',
        case_study:     'Results card: outcome metrics only ($, hours, timeline). Anonymous client type (e.g. "12-person ops team"). Clean before/after bar chart. Dark bg.',
        question_hook:  'Simple text overlay on a dark or atmospheric background photo. The question as the entire visual — no stats, no lists. Force the reader to sit with it.',
    },

    // (Legacy data above — methods removed; v3.0 implementations are at the top of this object)
};


/* ═══════════════════════════════════════════════════════════════════════════
   POST SCORER  — 7-dimension quality scoring with auto-strengthen
   Dimensions: hook · clarity · specificity · readability ·
               emotional_charge · comment_potential · share_potential
   Each dimension: 0–10. Total: 0–70. Auto-rewrite threshold: 42 (60%)
   INTEGRATION POINT: replace score() with fetch('/api/aiden/score', ...)
   ═══════════════════════════════════════════════════════════════════════════ */
const PostScorer = {

    // ── Score a single hook (6 dimensions, 0–10 each, total 0–60) ────────
    // Called by PostGenerator.generateIdeas() to score each hook in the list.
    scoreHook(hookText, templateItem) {
        const h = hookText || '';

        // 1. Clarity — immediately clear what this is about
        const words = h.split(/\s+/).length;
        const clarityScore = Math.min(10, words < 20 ? 8 : words < 35 ? 6 : 4);

        // 2. Curiosity — creates an information gap
        let curiosityScore = 4;
        if (/\?/.test(h))                                           curiosityScore += 2;
        if (/here's|here is|the reason|the secret|the one thing/i.test(h)) curiosityScore += 2;
        if (h.includes(':') && h.includes('\n'))                    curiosityScore++;
        curiosityScore = Math.min(10, curiosityScore);

        // 3. Specificity — numbers, timeframes, dollar amounts
        const numMatches = (h.match(/\$[\d,]+|\d+[\s]*(hrs?|hours?|weeks?|months?|days?|min|%|×|k\b|K\b|\+|\b\d{2,})/gi) || []).length;
        const specificityScore = Math.min(10, 4 + numMatches * 3);

        // 4. Emotional charge — targets an emotion from the template
        const emotion = templateItem?.emotion || '';
        let emoScore = 5;
        if (emotion === 'urgency'   && /stop|before|warning|if you/i.test(h)) emoScore = 9;
        if (emotion === 'proof'     && /\$|\d+|before:|after:/i.test(h))      emoScore = 9;
        if (emotion === 'challenge' && /wrong|mistake|not a|actually/i.test(h)) emoScore = 8;
        if (emotion === 'empathy'   && /nobody|most|hard|wish/i.test(h))       emoScore = 8;
        if (emotion === 'curiosity' && /\?|one thing|pattern|always/i.test(h)) emoScore = 8;
        if (emotion === 'tension'   && /won't|will never|most teams/i.test(h)) emoScore = 8;
        if (emotion === 'clarity'   && /myth:|reality:|what everyone/i.test(h)) emoScore = 8;
        emoScore = Math.min(10, emoScore);

        // 5. Novelty — reframes or challenges a common belief
        let noveltyScore = Math.min(10, (templateItem?.weight || 5));

        // 6. Engagement potential — likely to trigger a comment or share
        let engagementScore = 5;
        if (/unpopular|honest|most people|won't admit/i.test(h)) engagementScore += 2;
        if (/you think|you're not|it's not/i.test(h))            engagementScore += 2;
        if (/warning|stop|before you/i.test(h))                  engagementScore++;
        engagementScore = Math.min(10, engagementScore);

        const total = clarityScore + curiosityScore + specificityScore + emoScore + noveltyScore + engagementScore;
        return {
            clarity: clarityScore,
            curiosity: curiosityScore,
            specificity: specificityScore,
            emotional_charge: emoScore,
            novelty: noveltyScore,
            engagement_potential: engagementScore,
            total,
            grade: total >= 54 ? 'A' : total >= 45 ? 'B' : total >= 36 ? 'C' : total >= 27 ? 'D' : 'F',
        };
    },

    score(post) {
        const hook = post.hook || '';
        const body = post.body || '';
        const full = hook + '\n' + body;

        // 1. Hook strength — first line creates a stop-scroll moment
        let hookScore = 5;
        if (/^\d|^[A-Z]/.test(hook))               hookScore++;      // starts punchy
        if (/\?/.test(hook.split('\n')[0]))          hookScore++;      // question on line 1
        if (/\$|%|×|\d+/.test(hook))               hookScore++;      // specific number
        if (hook.split('\n')[0].length < 80)         hookScore++;      // short first line
        if (/truth|honest|nobody|wrong|stop|admit/i.test(hook)) hookScore++; // tension word
        hookScore = Math.min(10, hookScore);

        // 2. Clarity — readable value in 3 seconds
        const avgSentLen = full.split(/[.!?]/).filter(Boolean).map(s => s.split(' ').length);
        const avg = avgSentLen.length ? avgSentLen.reduce((a,b)=>a+b,0)/avgSentLen.length : 20;
        let clarityScore = avg < 12 ? 8 : avg < 18 ? 6 : 4;
        if (full.includes('\n\n')) clarityScore++;          // paragraph breaks
        if (/→|•|–/.test(full))   clarityScore++;          // visual list markers
        clarityScore = Math.min(10, clarityScore);

        // 3. Specificity — numbers, names, timelines, outcomes
        const specMatches = (full.match(/\$[\d,]+|\d+[\s]*(hrs?|hours?|weeks?|months?|days?|min|%|×|k\b|K\b)/gi) || []).length;
        const specScore = Math.min(10, 4 + specMatches * 2);

        // 4. Readability — skimmable, short sentences, line breaks
        const lineBreaks = (full.match(/\n/g) || []).length;
        let readScore = Math.min(10, Math.floor(lineBreaks / 2) + 3);
        if (avg < 10) readScore = Math.min(10, readScore + 2);

        // 5. Emotional charge — pride, curiosity, fear, inspiration
        const emoWords = /embarrassed|almost|quit|mistake|cost us|struggling|hard|flip|different|change|breakthrough|win|crush|transform|honest|real/i;
        let emoScore = emoWords.test(full) ? 7 : 5;
        if (/\!/.test(full)) emoScore = Math.min(10, emoScore + 1);
        if (/I (almost|nearly|was|thought)/i.test(full)) emoScore = Math.min(10, emoScore + 2);

        // 6. Comment potential — invites response, asks question or is divisive
        let commentScore = 4;
        if (/\?/.test(post.cta))                     commentScore += 2;
        if (/disagree|wrong|pushback|counterargument|your take/i.test(full)) commentScore += 2;
        if (/drop (it|a comment|below)|comment below|tell me/i.test(full))   commentScore += 2;
        commentScore = Math.min(10, commentScore);

        // 7. Save/share potential — tactical, frameworks, numbered lists
        let shareScore = 4;
        if (/save this|steal this|framework|playbook|step \d/i.test(full))   shareScore += 2;
        if (/→/.test(full))                           shareScore++;
        if (/Step [1-9]/i.test(full))                 shareScore++;
        if (specMatches >= 2)                         shareScore++;
        shareScore = Math.min(10, shareScore);

        const total = hookScore + clarityScore + specScore + readScore + emoScore + commentScore + shareScore;

        return {
            hook:            hookScore,
            clarity:         clarityScore,
            specificity:     specScore,
            readability:     readScore,
            emotional_charge: emoScore,
            comment_potential: commentScore,
            share_potential:   shareScore,
            total,
            grade: total >= 63 ? 'A' : total >= 56 ? 'B' : total >= 49 ? 'C' : total >= 42 ? 'D' : 'F',
        };
    },

    strengthen(post, scored) {
        let { hook, body, cta } = post;

        // Weak hook — prepend a tension line
        if (scored.hook < 6) {
            hook = `Most people get this completely wrong.\n\n` + hook;
        }
        // Low specificity — append a concrete proof line
        if (scored.specificity < 5) {
            body = body + `\n\nThe teams we've helped: average 22 hrs/week recovered within 90 days.`;
        }
        // Low comment potential — replace CTA
        if (scored.comment_potential < 5) {
            cta = `Where are you at with this right now?\n\nDrop it in the comments — I read every one.`;
        }

        const strengthened = { ...post, hook, body, cta };
        strengthened.score = this.score(strengthened);
        return strengthened;
    },
};


/* ═══════════════════════════════════════════════════════════════════════════
   PLATFORM ADAPTER  — transforms a master concept into platform-specific copy
   ──────────────────────────────────────────────────────────────────────────
   INTEGRATION POINT: replace adapt() method body with
   fetch('/api/aiden/adapt', { method:'POST', body: JSON.stringify({masterContent, platform}) })
   Each platform intentionally uses a distinct voice, structure, and format.
   ═══════════════════════════════════════════════════════════════════════════ */
const PlatformAdapter = {

    PLATFORMS: ['linkedin', 'facebook', 'instagram', 'youtube', 'email'],

    // Per-platform hashtag counts and styles
    _platformHashtags: {
        linkedin:  { count: 5,  style: 'professional' },
        facebook:  { count: 3,  style: 'minimal'      },
        instagram: { count: 28, style: 'discovery'    },
        youtube:   { count: 0,  style: 'tags'         },
        email:     { count: 0,  style: 'none'         },
    },

    // Topic-aware Facebook openers (conversational, community-focused)
    _fbOpeners: {
        personal_story:  "Real talk — nobody prepares you for what {topic} actually feels like in year one.\n\nHere's the part most people leave out:",
        data_driven:     "Quick question for business owners and operators:\n\nDo you actually know what {topic} is costing you?\n\nMost don't. The numbers are surprising:",
        how_to:          "If you're still doing {topic} the old way, this is for you.\n\nI put together the exact steps we use — steal the whole thing:",
        contrarian:      "Okay, I'll say the thing nobody wants to say about {topic}.\n\nEveryone's doing it wrong. Here's the proof:",
        case_study:      "We just wrapped up a project that I can't stop thinking about.\n\nClient came to us with a {topic} problem. 8 weeks later:",
        question_hook:   "Honest question for anyone running a business:\n\nWhen's the last time you actually looked at what {topic} is costing you per week?",
    },

    _fbCtas: {
        personal_story:  "What's the thing about your business journey nobody talks about? Comment below — I read everything 👇",
        data_driven:     "Tag a business owner who needs to see this. And drop a comment if this hits close to home 👇",
        how_to:          "Save this post and try Step 1 this week. Share your results in the comments 👇",
        contrarian:      "Agree? Disagree? Tell me in the comments. I want to hear both sides 👇",
        case_study:      "Curious what this could look like for your business? DM us or drop a comment and we'll reach out 👇",
        question_hook:   "Comment your answer below. Seriously curious what people are dealing with right now 👇",
    },

    // Instagram-first lines (must hook before "more...")
    _igFirstLines: {
        personal_story:  "The hardest year of building taught me the most important lesson. 🧵",
        data_driven:     "The data on {topic} is alarming — and almost no one is talking about it. 📊",
        how_to:          "5 steps to fix {topic} that actually work (save this). ✅",
        contrarian:      "Hot take: everything you know about {topic} is wrong. 🔥",
        case_study:      "$240K saved. 6 weeks. Here's exactly what we did. 💰",
        question_hook:   "What if {topic} wasn't the problem? 🤔",
    },

    _igHashtags: {
        lifestyle:           '#entrepreneur #entrepreneurlife #productivity #morningroutine #mindset #growthmindset #motivation #success #businessowner #ceo #leadership #personaldevelopment #selfimprovement #businesstips #smallbusiness #grind #hustle #worklifebalance #goaldigger #bossbabe #successmindset #dailyroutine #habitsthatwork #morningmotivation #thinkbig #levelup #selfdiscipline #executivecoach #mindsetmatters #buildingwealth',
        industry:            '#logistics #freight #supplychain #trucking #logistics101 #freightbroker #operationsmanagement #b2b #businessoperations #supplychain #ecommerce #3pl #warehouse #freighttech #logisticstech #automationtools #businessgrowth #operationsai #freightindustry #truckinglife #shipper #carrier #dispatchlife #logisticslife #freightnation #supplychain2025 #businessautomation #industrialtech #processimprovement #operationalexcellence',
        aiden:               '#ai #artificialintelligence #aitools #automation #businessai #futureofwork #aiagents #automationtools #techstartup #saas #b2bsaas #businessgrowth #operationsai #productivityhacks #worksmarter #techfounder #startuplife #airevolution #machinelearning #digitaltools #businesstech #scaleup #growthhacking #aiforwork #automatenow #workflowautomation #businesssoftware #aiinbusiness #operationalai #scaleyourbusiness',
        conflicting_opinion: '#marketingtips #salestips #coldoutreach #emailmarketing #linkedinstrategy #contentmarketing #digitalmarketing #growthhacking #leadgeneration #b2bmarketing #salesstrategy #outreach #prospecting #salesdevelopment #entrepreneurship #businessgrowth #marketingdigital #contentstrategy #businesscoach #startup #growthmindset #salescoach #marketingcoach #businessadvice #onlinemarketing #socialmediamarketing #contentcreator #brand #marketingtips2025 #businesstips',
    },

    // YouTube title formulas
    _ytTitles: {
        personal_story:  "The {topic} Mistake That Almost Broke Our Business (And What Fixed It)",
        data_driven:     "The Data Behind {topic}: What Most Businesses Are Getting Wrong in 2025",
        how_to:          "How to Fix {topic} in 5 Steps (Step-by-Step Framework)",
        contrarian:      "Why Everything You Know About {topic} Is Wrong",
        case_study:      "{topic} Case Study: $240K Saved in 6 Weeks — Full Breakdown",
        question_hook:   "Is Your {topic} Strategy Costing You More Than You Think?",
    },

    _ytDescriptions: {
        personal_story:  `In this video, I'm sharing the full story of how {topic} nearly derailed our business — and the exact decision that turned things around.\n\nThis is the stuff most founders don't talk about publicly. I'm sharing it because the lesson changed everything for us.\n\n⏱ TIMESTAMPS:\n00:00 — Introduction\n02:15 — The situation we were in\n06:40 — The decision point\n11:20 — What actually changed\n17:00 — Lessons and takeaways\n\n🔗 RESOURCES MENTIONED:\n→ Book a strategy call: [link]\n→ Free operations audit: [link]\n\n📩 Want to work with us? DM on LinkedIn or visit our website.\n\n🔔 Subscribe for weekly content on operations, automation, and building smarter businesses.\n\n#businessgrowth #entrepreneurship #operations #automation #startup`,
        data_driven:     `The data on {topic} is more alarming than most business owners realize — and in this video, I'm breaking down exactly what it shows.\n\nWe pulled data from 500+ operations and found the one pattern that consistently separates high-performing teams from everyone else.\n\n⏱ TIMESTAMPS:\n00:00 — The problem with {topic} data\n03:30 — What we analyzed\n08:00 — Key finding #1\n13:20 — Key finding #2\n19:00 — What to do with this\n\n🔗 RESOURCES:\n→ Free data audit template: [link]\n→ Book a 30-min strategy call: [link]\n\n#data #businessgrowth #operations #automation #productivity`,
        how_to:          `In this video, I'm walking through the exact 5-step framework we use to fix {topic} without adding headcount or spending a fortune on new tools.\n\nThis system works. I've seen it transform mid-size teams in under 90 days.\n\n⏱ TIMESTAMPS:\n00:00 — Why most approaches fail\n04:00 — Step 1: Audit\n08:30 — Step 2: Identify targets\n13:00 — Step 3: Build the system\n17:30 — Step 4: Measure\n22:00 — Step 5: Scale\n\n🔗 FREE RESOURCES:\n→ Download the framework template: [link]\n→ Book a 1:1 strategy session: [link]\n\n#howto #businessgrowth #productivity #operations #systemsthinking`,
        case_study:      `Real numbers, real results. In this video, I'm breaking down exactly how we helped a client save $240K in 6 weeks by fixing three things in their {topic} operation.\n\nNo fluff. No theory. Just the actual playbook.\n\n⏱ TIMESTAMPS:\n00:00 — Overview of the client situation\n05:00 — Automation #1: Reporting\n12:00 — Automation #2: Lead qualification\n19:00 — Automation #3: Follow-up sequences\n25:30 — Results and key takeaways\n\n🔗 RESOURCES:\n→ Apply for a free audit: [link]\n→ Case study PDF download: [link]\n\n#casestudy #businessgrowth #automation #roi #operationsmanagement`,
        contrarian:      `I'm about to say something that's going to make a lot of people uncomfortable about {topic}.\n\nMost businesses are doing this completely wrong — and the conventional wisdom is actually making things worse.\n\nHere's what the data actually shows, and what high-performing teams do instead.\n\n⏱ TIMESTAMPS:\n00:00 — The conventional wisdom\n04:30 — Why it's wrong\n10:00 — What the data shows\n16:00 — What actually works\n22:00 — How to make the switch\n\n🔗 RESOURCES:\n→ Free strategy call: [link]\n→ Contrarian Operations Playbook: [link]\n\n#businessadvice #hotTake #leadership #operations #growth`,
        question_hook:   `Here's a question most business owners can't answer honestly about {topic} — and why that gap is costing them significantly more than they realize.\n\nIn this video, I'm breaking down the true cost, and showing you the exact calculation most teams never run.\n\n⏱ TIMESTAMPS:\n00:00 — The question you need to ask\n04:00 — The true cost calculation\n10:30 — Real examples\n16:00 — What to do about it\n21:00 — Next steps\n\n🔗 RESOURCES:\n→ Free cost calculator: [link]\n→ Strategy session: [link]\n\n#businessgrowth #productivity #operations #roi #businessstrategy`,
    },

    // Email copy
    _emailSubjects: {
        personal_story:  "The thing I wish someone told me sooner",
        data_driven:     "What the data says about {topic} (most miss this)",
        how_to:          "5-step fix for {topic} (steal this)",
        contrarian:      "Everyone's wrong about {topic} — here's why",
        case_study:      "Case study: $240K saved in 6 weeks",
        question_hook:   "Quick question about your {topic} operation",
    },

    _emailPreview: {
        personal_story:  "The part most founders leave out — and why it matters for where you're going.",
        data_driven:     "78% of teams are still running this manually. Here's what that's actually costing.",
        how_to:          "A simple 5-step framework that's recovered 20+ hours/week for our clients.",
        contrarian:      "The conventional advice is keeping most businesses stuck. Here's the alternative.",
        case_study:      "Real numbers: 22 hrs/week recovered, $180K saved — here's the full breakdown.",
        question_hook:   "Most operators can't answer this — and that gap is expensive.",
    },

    _emailBodies: {
        personal_story:  `Hey {first_name},\n\nI don't talk about this enough — but here's the version of our {topic} story that most people don't hear:\n\nThe first year was a mess.\n\nManual everything. Constant firefighting. The team was running on empty and I couldn't see a way out.\n\nThe thing that changed it wasn't a new hire or a new tool. It was one decision:\n\nStop doing any work that a system can do better.\n\nThat single shift changed everything — 3× output, same team, dramatically better margins.\n\nI wrote up the full breakdown here: [link]\n\nIf any of this sounds familiar, I'd love to hear where you're at. Just hit reply.\n\n— [Name]\n\nP.S. We run a free 30-minute operations audit for teams who want an outside look. If you want one, reply with "audit" and I'll get you on the calendar.`,
        data_driven:     `Hey {first_name},\n\nI wanted to share something that stopped me in my tracks this week.\n\nWe reviewed data from 500+ operations teams and found that the average business loses 14 hours per week to manual {topic} work.\n\nThat's:\n→ 728 hours/year per person\n→ ~$29K/year in labor cost (at $40/hr)\n→ Per. Person.\n\nFor a 5-person ops team, that's $145K/year — before you account for errors, rework, and missed opportunities.\n\nWe've cut that to under 2 hours/week for most clients.\n\nFull breakdown here: [link]\n\nWorth 5 minutes of your time.\n\n— [Name]\n\nP.S. If you want to calculate your specific number, reply and I'll send you the calculator we use with clients.`,
        how_to:          `Hey {first_name},\n\nI've been asked a lot lately about how we approach fixing {topic} for clients without a massive time or budget investment.\n\nSo here's the actual framework:\n\n1. Audit — Map where time is going. (Most teams are shocked.)\n2. Target — Identify the 3 highest-volume manual tasks.\n3. Systemize — Build one simple process per task. Start ugly.\n4. Measure — Before vs. after, every time.\n5. Scale — Repeat the cycle.\n\nSetup time: 2–3 weeks for the first system.\nTime saved: 10–20 hours/week, ongoing.\n\nFull walkthrough here: [link]\n\nLet me know if you want to talk through how this applies to your setup.\n\n— [Name]`,
        contrarian:      `Hey {first_name},\n\nEveryone's saying the same thing about {topic}.\n\nAnd almost everyone is wrong.\n\nHere's what I've actually seen work vs. what gets talked about:\n\nWhat gets talked about: More tools, more automation, more hires.\nWhat actually works: Fewer decisions, simpler systems, ruthless prioritization.\n\nThe businesses quietly crushing it aren't doing anything fancy. They're doing the boring fundamentals better than everyone else.\n\nConsistency beats virality. Process beats hustle.\n\nI wrote up the full breakdown here: [link]\n\nIt's worth a read if you've ever felt like you're doing all the right things but not seeing the results.\n\n— [Name]`,
        case_study:      `Hey {first_name},\n\nQuick case study I think you'll find useful.\n\nA client came to us 8 weeks ago with a classic {topic} problem: 12-person team, manual everything, 40% of every week disappearing into admin work.\n\nWe made 3 changes:\n→ Automated weekly reporting: 6 hrs → 20 min\n→ Automated lead qualification: 3 hrs/day → real-time\n→ Automated follow-up sequences: manual → zero-touch\n\nResult: 22 hours/week recovered. $180K annualized savings.\n\nFull breakdown (with the exact tools and setup): [link]\n\nI thought about you when I was putting this together — your situation sounds similar to theirs.\n\nWorth a conversation? Just reply.\n\n— [Name]`,
        question_hook:   `Hey {first_name},\n\nQuick honest question:\n\nHow many hours per week is your team spending on {topic}?\n\nMost operators I talk to don't actually know the answer. And when we help them calculate it, the number is almost always 3–5× what they guessed.\n\nFor a 5-person team, that gap typically runs $100–200K/year in lost productivity.\n\nWe've helped dozens of teams cut that number by 70–80% in under 90 days.\n\nIf you want to run the calculation for your business, I can walk you through it in 20 minutes.\n\nJust reply to this email and we'll find a time.\n\n— [Name]`,
    },

    // ── Public API ─────────────────────────────────────────────────────────
    adapt(masterContent, platform) {
        const mc    = masterContent;
        const topic = mc.topic || 'this';
        const angle = mc.angle || 'personal_story';
        const cat   = mc.category || 'industry';

        switch (platform) {
            case 'linkedin':  return this._adaptLinkedIn(mc);
            case 'facebook':  return this._adaptFacebook(mc, topic, angle, cat);
            case 'instagram': return this._adaptInstagram(mc, topic, angle, cat);
            case 'youtube':   return this._adaptYouTube(mc, topic, angle, cat);
            case 'email':     return this._adaptEmail(mc, topic, angle, cat);
            default:          return null;
        }
    },

    adaptAll(masterContent) {
        return this.PLATFORMS.reduce((acc, p) => {
            acc[p] = this.adapt(masterContent, p);
            return acc;
        }, {});
    },

    _adaptLinkedIn(mc) {
        const post = PostGenerator.generatePost(mc.topic, mc.angle, mc.category, mc.selectedHook);
        return {
            platform:     'linkedin',
            caption:      `${post.hook}\n\n${post.body}\n\n${post.cta}`,
            hashtags:     post.hashtags,
            creative_notes: post.imageIdea,
            status:       'draft',
            scheduled_at: null,
        };
    },

    _adaptFacebook(mc, topic, angle, cat) {
        const opener = (this._fbOpeners[angle] || this._fbOpeners.personal_story).replace(/\{topic\}/g, topic);
        const body   = PostGenerator._bodies[angle] || PostGenerator._bodies.personal_story;
        const cta    = this._fbCtas[angle] || this._fbCtas.personal_story;
        // Facebook body is shorter — trim to 2 paragraphs of the full body
        const bodyShort = body.split('\n\n').slice(0, 3).join('\n\n');
        return {
            platform:     'facebook',
            caption:      `${opener}\n\n${bodyShort}\n\n${cta}`,
            hashtags:     PostGenerator._hashtags[(cat||'industry').toLowerCase().replace(/\s+/g,'_')]
                            ?.split(' ').slice(0, 3).join(' ') || '',
            creative_notes: 'Facebook image: same master graphic, optimized for 1200×630 (link preview format). Include brand logo in corner.',
            status:       'draft',
            scheduled_at: null,
        };
    },

    _adaptInstagram(mc, topic, angle, cat) {
        const firstLine = (this._igFirstLines[angle] || this._igFirstLines.personal_story).replace(/\{topic\}/g, topic);
        const body      = PostGenerator._bodies[angle] || PostGenerator._bodies.personal_story;
        const catKey    = (cat || 'industry').toLowerCase().replace(/\s+/g, '_');
        const hashtags  = this._igHashtags[catKey] || this._igHashtags.industry;
        // Instagram body: short punchy paragraphs (2 sentences max each), with line breaks
        const igBody = body.split('\n\n')
            .map(p => p.replace(/→ /g, '').split('\n').slice(0, 2).join('\n'))
            .slice(0, 4).join('\n\n');
        return {
            platform:     'instagram',
            caption:      `${firstLine}\n\n${igBody}\n\n👉 Save this for later.\n\n.\n.\n.\n${hashtags}`,
            hashtags:     hashtags,
            creative_notes: 'Instagram: square format (1080×1080). First frame must be visually arresting — bold stat or hook text overlay on clean background. Use Stories + Reels cover for extra reach.',
            status:       'draft',
            scheduled_at: null,
        };
    },

    _adaptYouTube(mc, topic, angle, cat) {
        const title = (this._ytTitles[angle] || this._ytTitles.personal_story)
            .replace(/\{topic\}/g, this._titleCase(topic));
        const desc  = (this._ytDescriptions[angle] || this._ytDescriptions.personal_story)
            .replace(/\{topic\}/g, topic);
        const catKey = (cat || 'industry').toLowerCase().replace(/\s+/g, '_');
        const igTags = (this._igHashtags[catKey] || this._igHashtags.industry)
            .replace(/#/g, '').split(' ').join(', ');
        return {
            platform:        'youtube',
            title:           title,
            caption:         desc,
            hashtags:        igTags,
            creative_notes:  `Thumbnail: bold text overlay — "${title.split(':')[0]}" — on clean background. Use face if video format, data graphic if explainer. A/B test two thumbnail styles.`,
            status:          'draft',
            scheduled_at:    null,
        };
    },

    _adaptEmail(mc, topic, angle, cat) {
        const subject  = (this._emailSubjects[angle] || this._emailSubjects.personal_story).replace(/\{topic\}/g, topic);
        const preview  = (this._emailPreview[angle]  || this._emailPreview.personal_story).replace(/\{topic\}/g, topic);
        const body     = (this._emailBodies[angle]   || this._emailBodies.personal_story).replace(/\{topic\}/g, topic);
        return {
            platform:        'email',
            email_subject:   subject,
            email_preview:   preview,
            caption:         body,
            hashtags:        '',
            creative_notes:  'Email header: clean branded banner or plain-text format. Single CTA button, mid-body and bottom. Mobile-first layout. Subject line A/B: test curiosity vs. benefit framing.',
            status:          'draft',
            scheduled_at:    null,
        };
    },

    _titleCase(str) {
        return (str || '').replace(/\b\w/g, c => c.toUpperCase());
    },
};


/* ═══════════════════════════════════════════════════════════════════════════
   CONTENT STORE
   Central data store for the hook → content → queue → history workflow.
   INTEGRATION POINT: replace queue/history arrays with fetch() calls to
   /api/aiden/queue and /api/aiden/history for persistent server-side storage.
   ═══════════════════════════════════════════════════════════════════════════ */
const ContentStore = {
    _nextId: 10,

    // Active queue items — content that has not yet been fully posted
    queue: [
        {
            id: 'q-001',
            title: 'Freight Broker Margin Leak',
            hook: "Most freight brokers will never show you what a 22% margin leak looks like on paper.\n\nHere's the exact breakdown.",
            content: "Here's what the data actually shows:\n\n→ 78% of teams still run this process manually\n→ Manual = 3–5× more errors, 4× longer cycle time\n→ Automation payback period: average 11 weeks\n\nThe gap between high-performing operations and everyone else isn't strategy.\n\nIt's execution speed.\n\nAnd execution speed comes from removing humans from repetitive decisions.\n\nThe top 10% have already figured this out.\n\nThe rest are still 'thinking about it.'",
            cta: "Want to see how this applies to your operation?\n\nDM me 'data' — I'll share the full breakdown.",
            hashtags: '#logistics #operations #freight #supplychain #automation',
            angle: 'data_driven',
            category: 'industry',
            asset_type: 'graphic',
            created_at: '2026-03-01T08:00:00Z',
            queued_at: '2026-03-02T09:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'scheduled', caption: "Most freight brokers will never show you what a 22% margin leak looks like on paper.\n\nHere's the exact breakdown." },
                facebook:  { status: 'draft',     caption: '' },
                instagram: { status: 'ready',     caption: '' },
                youtube:   { status: 'draft',     caption: '' },
                email:     { status: 'draft',     caption: '' },
            },
        },
        {
            id: 'q-002',
            title: 'AI Saved Client $240K',
            hook: "12-person team. $180k wasted per year on AI operations automation.\n\nWe fixed it in 6 weeks. Here's exactly what we did.",
            content: "Here's the full breakdown.\n\nThe situation: 12-person team, fully manual processes, 40% of every week evaporating into admin work.\n\nWhat we changed:\n→ Automated weekly reporting: 6 hrs/week → 18 minutes.\n→ Automated lead qualification: 3 hrs/day → real-time, zero touch.\n→ Automated follow-up sequences: manual → fully hands-off.\n\nThe result after 6 weeks:\n→ 22 hours/week recovered.\n→ $180k annualized savings.\n→ Team morale: dramatically different.\n\nNothing flashy. No reorg. No new hires.\n\nJust the decision to stop tolerating what a system could handle.",
            cta: "Curious what this looks like for your operation?\n\nDM me — I'll do a quick 20-min audit call. No pitch.",
            hashtags: '#AI #automation #b2b #operationsai #businessgrowth',
            angle: 'case_study',
            category: 'aiden',
            asset_type: 'graphic',
            created_at: '2026-03-05T09:00:00Z',
            queued_at: '2026-03-06T10:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'ready',     caption: '' },
                facebook:  { status: 'draft',     caption: '' },
                instagram: { status: 'draft',     caption: '' },
                youtube:   { status: 'draft',     caption: '' },
                email:     { status: 'ready',     caption: '' },
            },
        },
        {
            id: 'q-003',
            title: 'The Hiring Trap',
            hook: "Most operators hire to solve problems that systems should solve.\n\nHere's how to tell the difference.",
            content: "The signal that tells you it's a systems problem, not a headcount problem:\n\n→ The same firefight keeps happening week after week\n→ Your best people are doing repetitive, manual work\n→ New hires get absorbed into the chaos instead of changing it\n\nHiring into broken systems doesn't fix them.\n\nIt just gives the chaos more hands.\n\nThe highest-leverage move in operations isn't your next hire.\n\nIt's the next system you build so your current team stops repeating themselves.",
            cta: "What's one thing your team does manually that they shouldn't? Drop it in the comments.",
            hashtags: '#operations #leadership #hiring #businessgrowth #founders',
            angle: 'contrarian',
            category: 'industry',
            asset_type: 'graphic',
            created_at: '2026-03-08T07:00:00Z',
            queued_at: '2026-03-09T08:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'scheduled', caption: "Most operators hire to solve problems that systems should solve.\n\nHere's how to tell the difference." },
                facebook:  { status: 'scheduled', caption: '' },
                instagram: { status: 'ready',     caption: '' },
                youtube:   { status: 'draft',     caption: '' },
                email:     { status: 'draft',     caption: '' },
            },
        },
        {
            id: 'q-004',
            title: 'Carrier Vetting System',
            hook: "We vet 800+ carriers per year.\n\nHere's the 7-point system that catches bad carriers before they cost you customers.",
            content: "Most brokers wing carrier vetting.\n\nThey check the MC number, glance at the safety rating, and move on.\n\nThat's how a $4,000 load disappears.\n\nHere's what our system checks before we book a single load:\n\n1. FMCSA safety score — must be Satisfactory\n2. Insurance COI — verify directly, not from email\n3. Cargo claim history — 3+ claims = no book\n4. Ownership verification — no shell companies\n5. Driver check — CDL valid, no recent violations\n6. Equipment photos — before first load, every time\n7. Payment history — cross-reference 3 references\n\nThis takes 12 minutes per new carrier.\n\nThe loads it protects are worth far more.",
            cta: "What does your vetting process look like? I'll share the full checklist in the first comment.",
            hashtags: '#freightbroker #logistics #carriervetting #supplychain #operationsmanagement',
            angle: 'how_to',
            category: 'industry',
            asset_type: 'carousel',
            created_at: '2026-03-10T09:00:00Z',
            queued_at: '2026-03-11T10:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'ready',     caption: "We vet 800+ carriers per year.\n\nHere's the 7-point system that catches bad carriers before they cost you customers." },
                facebook:  { status: 'draft',     caption: '' },
                instagram: { status: 'draft',     caption: '' },
                youtube:   { status: 'draft',     caption: '' },
                email:     { status: 'ready',     caption: '' },
            },
        },
        {
            id: 'q-005',
            title: 'What $1.2M in AI Savings Taught Us',
            hook: "We helped our clients save $1.2M last year using AI.\n\nThe #1 lesson surprised us.",
            content: "We track the ROI of every automation we build for clients.\n\nLast year the number hit $1.2M across the portfolio.\n\nHere's what that data actually taught us:\n\nThe biggest savings never came from the most sophisticated AI.\n\nThey came from automating the dumbest, most repetitive tasks first.\n\n→ Auto-generating weekly reports: $47K saved/year at one company\n→ Automating lead qualification scoring: $118K saved/year\n→ Carrier check-in notifications: $24K saved/year\n→ Invoice reconciliation: $91K saved/year\n\nNone of this required a PhD.\n\nIt required the willingness to map out the manual work and ask: why is a human doing this?",
            cta: "What's the highest-ROI thing you've automated in your business? Drop it below.",
            hashtags: '#AI #automation #operationsai #businessgrowth #ROI',
            angle: 'authority_proof',
            category: 'aiden',
            asset_type: 'graphic',
            created_at: '2026-03-11T08:00:00Z',
            queued_at: '2026-03-12T09:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'queued',    caption: '' },
                facebook:  { status: 'queued',    caption: '' },
                instagram: { status: 'queued',    caption: '' },
                youtube:   { status: 'draft',     caption: '' },
                email:     { status: 'queued',    caption: '' },
            },
        },
    ],

    // Post history — items fully posted across all active channels
    history: [
        {
            id: 'h-001',
            queue_item_id: 'q-hist-001',
            title: '5AM Routine — 90 Day Reflection',
            hook: "I almost shut it all down at month 4.\n\nThen one decision changed everything.",
            content_preview: "Here's what nobody tells you before you build:\n\n→ The first 90 days will feel broken even when they're working.\n→ Your biggest inefficiency is usually hiding in plain sight.\n→ The fix is almost never a new hire.\n→ Systems compound. Effort doesn't.",
            angle: 'personal_story',
            category: 'lifestyle',
            created_at: '2026-02-14T07:00:00Z',
            queued_at:  '2026-02-15T08:00:00Z',
            posted_at:  '2026-02-19T07:30:00Z',
            channel_statuses: {
                linkedin:  { status: 'posted' },
                facebook:  { status: 'posted' },
                instagram: { status: 'posted' },
                youtube:   { status: 'posted' },
                email:     { status: 'posted' },
            },
            metrics: {
                linkedin:  { impressions: 12400, likes: 287, comments: 43, shares: 31, clicks: 194, engagement_rate: 4.5, post_url: '' },
                facebook:  { impressions: 3200,  likes: 89,  comments: 12, shares: 8,  clicks: 41,  engagement_rate: 3.1, post_url: '' },
                instagram: { impressions: 5800,  likes: 341, comments: 28, shares: 0,  clicks: 0,   engagement_rate: 6.4, post_url: '' },
                youtube:   { impressions: 0,     likes: 0,   comments: 0,  shares: 0,  clicks: 0,   engagement_rate: 0,   post_url: '' },
                email:     { impressions: 1840,  likes: 0,   comments: 0,  shares: 0,  clicks: 127, engagement_rate: 6.9, post_url: '' },
            },
        },
        {
            id: 'h-002',
            queue_item_id: 'q-hist-002',
            title: 'Carrier Rate Negotiation Framework',
            hook: "Your carriers know something you don't.\n\nHere's how to level the playing field.",
            content_preview: "Most brokers negotiate from weakness — no data, no benchmarks, no idea what fair actually looks like.\n\nHere's the 4-step framework we use:\n1. Pull 90-day rate history per lane\n2. Benchmark against DAT spot vs. contract delta\n3. Identify your top 20% volume lanes and go contract-first\n4. Never negotiate without a competing quote in hand",
            angle: 'data_driven',
            category: 'industry',
            created_at: '2026-02-01T08:00:00Z',
            queued_at:  '2026-02-03T09:00:00Z',
            posted_at:  '2026-02-05T08:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'posted' },
                facebook:  { status: 'posted' },
                instagram: { status: 'posted' },
                youtube:   { status: 'posted' },
                email:     { status: 'posted' },
            },
            metrics: {
                linkedin:  { impressions: 9200,  likes: 214, comments: 31, shares: 22, clicks: 148, engagement_rate: 2.9, post_url: '' },
                facebook:  { impressions: 2800,  likes: 64,  comments: 9,  shares: 5,  clicks: 32,  engagement_rate: 2.8, post_url: '' },
                instagram: { impressions: 4600,  likes: 289, comments: 21, shares: 0,  clicks: 0,   engagement_rate: 6.7, post_url: '' },
                youtube:   { impressions: 0,     likes: 0,   comments: 0,  shares: 0,  clicks: 0,   engagement_rate: 0,   post_url: '' },
                email:     { impressions: 1620,  likes: 0,   comments: 0,  shares: 0,  clicks: 108, engagement_rate: 6.7, post_url: '' },
            },
        },
        {
            id: 'h-003',
            queue_item_id: 'q-hist-003',
            title: 'Why Automation Beats Hiring',
            hook: "Every time I hired to solve an ops problem, the problem got bigger.\n\nHere's what changed my mind.",
            content_preview: "The pattern is painfully consistent: new hire joins → gets absorbed into existing chaos → now you have a more expensive version of the same problem.\n\nThe businesses I've seen break this cycle didn't hire their way out. They systematized their way out. Same headcount, 3× the output.",
            angle: 'contrarian',
            category: 'aiden',
            created_at: '2026-01-22T07:30:00Z',
            queued_at:  '2026-01-23T08:00:00Z',
            posted_at:  '2026-01-28T08:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'posted' },
                facebook:  { status: 'posted' },
                instagram: { status: 'posted' },
                youtube:   { status: 'posted' },
                email:     { status: 'posted' },
            },
            metrics: {
                linkedin:  { impressions: 18700, likes: 482, comments: 74, shares: 58, clicks: 312, engagement_rate: 3.3, post_url: '' },
                facebook:  { impressions: 4100,  likes: 118, comments: 24, shares: 16, clicks: 67,  engagement_rate: 3.9, post_url: '' },
                instagram: { impressions: 7200,  likes: 451, comments: 39, shares: 0,  clicks: 0,   engagement_rate: 6.8, post_url: '' },
                youtube:   { impressions: 0,     likes: 0,   comments: 0,  shares: 0,  clicks: 0,   engagement_rate: 0,   post_url: '' },
                email:     { impressions: 2140,  likes: 0,   comments: 0,  shares: 0,  clicks: 189, engagement_rate: 8.8, post_url: '' },
            },
        },
        {
            id: 'h-004',
            queue_item_id: 'q-hist-004',
            title: 'Freight Market 2025 — What the Data Says',
            hook: "I pulled 12 months of freight rate data.\n\nHere's what most analysts aren't saying.",
            content_preview: "Spot rates bottomed in Q1, recovered 18% by Q3, then did something unexpected in October. If you're a broker planning capacity for 2026 without this data, you're planning blind.",
            angle: 'data_driven',
            category: 'industry',
            created_at: '2026-01-10T09:00:00Z',
            queued_at:  '2026-01-11T10:00:00Z',
            posted_at:  '2026-01-15T08:30:00Z',
            channel_statuses: {
                linkedin:  { status: 'posted' },
                facebook:  { status: 'posted' },
                instagram: { status: 'posted' },
                youtube:   { status: 'posted' },
                email:     { status: 'posted' },
            },
            metrics: {
                linkedin:  { impressions: 7400,  likes: 168, comments: 22, shares: 14, clicks: 97,  engagement_rate: 2.8, post_url: '' },
                facebook:  { impressions: 1900,  likes: 41,  comments: 7,  shares: 4,  clicks: 22,  engagement_rate: 2.7, post_url: '' },
                instagram: { impressions: 3400,  likes: 198, comments: 14, shares: 0,  clicks: 0,   engagement_rate: 6.2, post_url: '' },
                youtube:   { impressions: 0,     likes: 0,   comments: 0,  shares: 0,  clicks: 0,   engagement_rate: 0,   post_url: '' },
                email:     { impressions: 1480,  likes: 0,   comments: 0,  shares: 0,  clicks: 94,  engagement_rate: 6.4, post_url: '' },
            },
        },
        {
            id: 'h-005',
            queue_item_id: 'q-hist-005',
            title: '5 Systems Every Freight Broker Needs',
            hook: "The 5 systems that separate 30% margin brokers from 22% margin brokers.\n\nAll of them can be built in-house.",
            content_preview: "I've reviewed 80+ brokerage P&Ls. The ones consistently running 28–32% margins all have the same 5 systems. The ones stuck at 20–24% are missing at least 3 of them.",
            angle: 'how_to',
            category: 'industry',
            created_at: '2025-12-18T08:00:00Z',
            queued_at:  '2025-12-19T09:00:00Z',
            posted_at:  '2025-12-22T08:00:00Z',
            channel_statuses: {
                linkedin:  { status: 'posted' },
                facebook:  { status: 'posted' },
                instagram: { status: 'posted' },
                youtube:   { status: 'posted' },
                email:     { status: 'posted' },
            },
            metrics: {
                linkedin:  { impressions: 14100, likes: 341, comments: 52, shares: 38, clicks: 228, engagement_rate: 3.1, post_url: '' },
                facebook:  { impressions: 3600,  likes: 88,  comments: 18, shares: 12, clicks: 49,  engagement_rate: 3.3, post_url: '' },
                instagram: { impressions: 5900,  likes: 374, comments: 31, shares: 0,  clicks: 0,   engagement_rate: 6.8, post_url: '' },
                youtube:   { impressions: 0,     likes: 0,   comments: 0,  shares: 0,  clicks: 0,   engagement_rate: 0,   post_url: '' },
                email:     { impressions: 1920,  likes: 0,   comments: 0,  shares: 0,  clicks: 148, engagement_rate: 7.7, post_url: '' },
            },
        },
    ],

    // ── Queue CRUD ────────────────────────────────────────────────────────
    addToQueue(item) {
        const id = `q-${String(this._nextId++).padStart(3,'0')}`;
        const entry = {
            id,
            title:    item.title || 'Untitled',
            hook:     item.hook || '',
            content:  item.content || '',
            cta:      item.cta || '',
            hashtags: item.hashtags || '',
            angle:    item.angle || 'personal_story',
            category: item.category || 'industry',
            asset_type: item.asset_type || 'graphic',
            created_at: item.created_at || new Date().toISOString(),
            queued_at:  new Date().toISOString(),
            channel_statuses: {
                linkedin:  { status: 'draft', caption: item.content || '' },
                facebook:  { status: 'draft', caption: '' },
                instagram: { status: 'draft', caption: '' },
                youtube:   { status: 'draft', caption: '' },
                email:     { status: 'draft', caption: '' },
            },
        };
        this.queue.unshift(entry);
        return entry;
    },

    removeFromQueue(id) {
        this.queue = this.queue.filter(q => q.id !== id);
    },

    updateChannelStatus(id, channel, status) {
        const item = this.queue.find(q => q.id === id);
        if (!item || !item.channel_statuses[channel]) return false;
        item.channel_statuses[channel].status = status;
        // Auto-move to history if all channels are posted
        const CHANNELS = ['linkedin','facebook','instagram','youtube','email'];
        const allPosted = CHANNELS.every(ch => item.channel_statuses[ch].status === 'posted');
        if (allPosted) {
            this._moveToHistory(item);
            return 'moved';
        }
        return true;
    },

    updateChannelCaption(id, channel, caption) {
        const item = this.queue.find(q => q.id === id);
        if (item && item.channel_statuses[channel]) item.channel_statuses[channel].caption = caption;
    },

    updateContent(id, field, value) {
        const item = this.queue.find(q => q.id === id);
        if (item) item[field] = value;
    },

    _moveToHistory(item) {
        this.queue = this.queue.filter(q => q.id !== item.id);
        this.history.unshift({
            id:            `h-${String(this._nextId++).padStart(3,'0')}`,
            queue_item_id: item.id,
            title:         item.title,
            hook:          item.hook,
            content_preview: (item.content || '').substring(0, 200),
            angle:         item.angle,
            category:      item.category,
            created_at:    item.created_at,
            queued_at:     item.queued_at,
            posted_at:     new Date().toISOString(),
            channel_statuses: item.channel_statuses,
            metrics: {
                linkedin:  { impressions:0, likes:0, comments:0, shares:0, clicks:0, engagement_rate:0, post_url:'' },
                facebook:  { impressions:0, likes:0, comments:0, shares:0, clicks:0, engagement_rate:0, post_url:'' },
                instagram: { impressions:0, likes:0, comments:0, shares:0, clicks:0, engagement_rate:0, post_url:'' },
                youtube:   { impressions:0, likes:0, comments:0, shares:0, clicks:0, engagement_rate:0, post_url:'' },
                email:     { impressions:0, likes:0, comments:0, shares:0, clicks:0, engagement_rate:0, post_url:'' },
            },
        });
    },

    _titleCase(str) {
        return (str || '').replace(/\b\w/g, c => c.toUpperCase());
    },

    // ── Legacy shim — kept for PlatformAdapter compatibility ─────────────
    items: [],
    getById() { return null; },
};

// Keep MasterContentLibrary as alias so PlatformAdapter still works
const MasterContentLibrary = ContentStore;

/* ═══════════════════════════════════════════════════════════════════════════
   LEGACY MasterContentLibrary seed data reference — no longer used for
   rendering; ContentStore.queue/history are the source of truth.
   ═══════════════════════════════════════════════════════════════════════════ */
const _LEGACY_SEED = {items: [
        {
            id: 'master-001',
            title: 'Freight Broker Margin Leak',
            concept: "Most freight brokers will never show you what a 22% margin leak looks like on paper. Here's the exact breakdown.",
            topic: 'freight margin optimization',
            angle: 'data_driven',
            category: 'industry',
            asset_type: 'graphic',
            created_at: '2025-03-12T08:00:00Z',
            status: 'ready',
            variants: {
                linkedin:  { platform:'linkedin',  status:'scheduled', scheduled_at:'2025-03-14T07:30:00', caption:"We analyzed 500+ freight broker operations. The one pattern that separated winners from everyone else:\n\nHere's what the research actually shows:\n\n→ 78% of teams still run this process manually\n→ Manual = 3–5× more errors, 4× longer cycle time\n→ Automation payback period: average 11 weeks\n\nThe gap between high-performing operations and everyone else isn't strategy.\n\nIt's execution speed. And execution speed comes from removing humans from repetitive decisions.", hashtags:'#logistics #operations #freight #supplychain #automation', creative_notes:'Single-stat data card — key number in large type on dark background.', email_subject:null, email_preview:null, title:null },
                facebook:  { platform:'facebook',  status:'draft',     scheduled_at:null,                  caption:"Quick question for every freight broker and ops leader:\n\nDo you actually know what your margin leak is costing you per load?\n\nMost don't. When we run the numbers with clients, the figure is almost always higher than they guessed — sometimes by 2–3×.\n\nHere's what the data from 500+ operations shows about where the losses hide:\n\n→ Manual billing errors: avg 4.2% of revenue\n→ Carrier rate inconsistency: avg 3.8%\n→ Unbilled accessorials: avg 2.1%\n\nTotal: 22% of potential margin — gone.\n\nTag a freight operator who needs to see this 👇", hashtags:'#logistics #freight #operations', creative_notes:'Facebook: same graphic at 1200×630. Lead with the 22% number in thumbnail.', email_subject:null, email_preview:null, title:null },
                instagram: { platform:'instagram', status:'ready',     scheduled_at:null,                  caption:"The data on freight margins is alarming — and almost no one is talking about it. 📊\n\nWe analyzed 500+ operations.\n\nThe average brokerage is losing 22% of potential margin.\n\nHere's where it goes:\n→ Manual billing errors\n→ Rate inconsistency\n→ Unbilled accessorials\n\nThe fix isn't a new tool.\n\nIt's better systems.\n\n👉 Save this if you run a freight or logistics operation.\n\n.\n.\n.", hashtags:'#logistics #freight #supplychain #trucking #logistics101 #freightbroker #operationsmanagement #b2b #businessoperations #supplychain #ecommerce #3pl #warehouse #freighttech #logisticstech #automationtools #businessgrowth #operationsai #freightindustry #truckinglife #shipper #carrier #dispatchlife #logisticslife #freightnation #supplychain2025 #businessautomation #industrialtech #processimprovement #operationalexcellence', creative_notes:'Square 1080×1080 — bold "22%" stat front and center. Dark card format.', email_subject:null, email_preview:null, title:null },
                youtube:   { platform:'youtube',   status:'draft',     scheduled_at:null,                  title:'Why Your Freight Margins Are Bleeding (And You Don\'t Know It)', caption:"Where do freight brokers lose money without knowing it? In this video, I'm breaking down the 4 places margin leaks happen — and exactly how to fix each one.\n\nThis is based on data from 500+ brokerage operations.\n\n⏱ TIMESTAMPS:\n00:00 — Introduction\n03:00 — Leak #1: Manual billing errors\n08:30 — Leak #2: Rate inconsistency\n14:00 — Leak #3: Unbilled accessorials\n19:00 — The fix: Systems over tools\n24:00 — Key takeaways", hashtags:'logistics, freight, supplychain, freightbroker, operationsmanagement', creative_notes:'Thumbnail: bold "22% Margin Leak" text. Split image — clean vs. chaotic ops.', email_subject:null, email_preview:null },
                email:     { platform:'email',     status:'draft',     scheduled_at:null,                  email_subject:'What the data says about freight margins (most miss this)', email_preview:'78% of brokerages are running this manually. Here\'s what that\'s actually costing.', caption:"Hey {first_name},\n\nI wanted to share something that stopped me this week.\n\nWe reviewed data from 500+ freight operations and found the average brokerage is losing 22% of potential margin to three systemic leaks:\n\n→ Manual billing errors: ~4.2% of revenue\n→ Carrier rate inconsistency: ~3.8%\n→ Unbilled accessorials: ~2.1%\n\nFor a brokerage doing $5M/year, that's $1.1M in margin sitting on the table.\n\nWe've helped teams close that gap. Worth a conversation?\n\nJust reply — happy to walk through the numbers for your operation.\n\n— [Name]", hashtags:'', title:null, creative_notes:'Plain-text format. Single CTA: "Reply to this email." No images needed.' },
            },
        },
        {
            id: 'master-002',
            title: 'AI Saved Client $240K Case Study',
            concept: "We just saved a client $240k/year using three AI automations. The whole setup took 6 weeks.",
            topic: 'AI operations automation',
            angle: 'case_study',
            category: 'aiden',
            asset_type: 'graphic',
            created_at: '2025-03-15T09:00:00Z',
            status: 'ready',
            variants: {
                linkedin:  { platform:'linkedin',  status:'scheduled', scheduled_at:'2025-03-17T09:00:00', caption:"Case study: We helped a mid-size company 3× their AI operations automation results in one quarter:\n\nHere's the exact breakdown:\n\nThe situation: 12-person team, fully manual processes, 40% of every week lost to admin work.\n\nThe intervention: 3 targeted automations over 6 weeks.\n\nThe result: 22 hours/week recovered. $180k annualized savings. Team morale: dramatically improved.\n\nWhat actually changed:\n→ Automated reporting (was: 6 hrs/week → now: 20 min)\n→ Automated lead qualification (was: 3 hrs/day → now: real-time)\n→ Automated follow-up sequences (was: manual → now: zero-touch)\n\nCurious what this looks like for your business? DM me — happy to walk through a quick audit.", hashtags:'#AI #automation #b2b #operationsai #businessgrowth', creative_notes:'Results card: $240K saved + 22 hrs/week recovered. Before/after bar chart.', email_subject:null, email_preview:null, title:null },
                facebook:  { platform:'facebook',  status:'draft',     scheduled_at:null,                  caption:"We just wrapped up a project I can't stop thinking about.\n\nClient came to us with a classic AI operations automation problem: 12-person team, manual everything, 40% of every week disappearing into admin work.\n\nWe made 3 changes in 6 weeks:\n✅ Automated weekly reporting: 6 hrs → 20 min\n✅ Automated lead qual: 3 hrs/day → real-time\n✅ Automated follow-ups: manual → zero-touch\n\nResult: $240K/year saved. Team morale went through the roof.\n\nIf your team is drowning in manual work, DM us or comment below 👇", hashtags:'#AI #automation #b2b', creative_notes:'Facebook: split-image — before (messy spreadsheets) vs. after (clean dashboard). 1200×630.', email_subject:null, email_preview:null, title:null },
                instagram: { platform:'instagram', status:'draft',     scheduled_at:null,                  caption:"$240K saved. 6 weeks. Here's exactly what we did. 💰\n\nClient: 12-person ops team\nProblem: 40% of every week = admin work\n\nWe automated 3 things:\n→ Reporting: 6 hrs → 20 min\n→ Lead qual: real-time\n→ Follow-ups: zero-touch\n\nOutcome:\n✅ 22 hours/week recovered\n✅ $240K annualized savings\n✅ Team: happier than ever\n\nAI doesn't replace your team.\n\nIt gives them their time back.\n\n👉 Save this. DM us if you want a free audit.\n\n.\n.\n.", hashtags:'#ai #artificialintelligence #aitools #automation #businessai #futureofwork #aiagents #automationtools #techstartup #saas #b2bsaas #businessgrowth #operationsai #productivityhacks #worksmarter #techfounder #startuplife #airevolution #machinelearning #digitaltools #businesstech #scaleup #growthhacking #aiforwork #automatenow #workflowautomation #businesssoftware #aiinbusiness #operationalai #scaleyourbusiness', creative_notes:'Strong visual: "$240K" in giant type. Dark background. Minimal text.', email_subject:null, email_preview:null, title:null },
                youtube:   { platform:'youtube',   status:'draft',     scheduled_at:null,                  title:'How We Saved $240K Using 3 AI Automations (Full Case Study)', caption:"Real numbers, real results. In this video, I'm breaking down exactly how we helped a 12-person ops team recover 22 hours per week and save $240K/year — in 6 weeks.\n\nNo theory. No fluff. The actual playbook.\n\n⏱ TIMESTAMPS:\n00:00 — Client situation overview\n04:30 — Automation #1: Reporting\n11:00 — Automation #2: Lead qualification\n18:00 — Automation #3: Follow-up sequences\n24:30 — Results and cost breakdown\n29:00 — How to apply this to your business", hashtags:'ai, automation, casestudy, businessgrowth, operationsmanagement', creative_notes:'Thumbnail: bold "$240K Saved" + "6 Weeks" text overlay. Credibility-first design.', email_subject:null, email_preview:null },
                email:     { platform:'email',     status:'ready',     scheduled_at:null,                  email_subject:'Case study: $240K saved in 6 weeks', email_preview:'Real numbers: 22 hrs/week recovered, $180K saved — here\'s the full breakdown.', caption:"Hey {first_name},\n\nQuick case study I think you'll find useful.\n\nA client came to us 8 weeks ago: 12-person ops team, manual everything, 40% of every week disappearing into admin.\n\nWe made 3 changes:\n→ Automated reporting: 6 hrs/week → 20 min\n→ Automated lead qualification: 3 hrs/day → real-time\n→ Automated follow-up sequences: manual → zero-touch\n\nResult: 22 hours/week recovered. $240K annualized savings.\n\nI thought about your operation when I was writing this up.\n\nWant me to show you what this could look like for your team? Just reply and I'll set up a 20-minute call.\n\n— [Name]", hashtags:'', title:null, creative_notes:'Plain-text. High-credibility tone. Single CTA: "reply to book a call".' },
            },
        },
        {
            id: 'master-003',
            title: '5AM Routine — 90 Day Reflection',
            concept: "I've been waking up at 5am for 90 days straight. Here's what nobody tells you about what actually changes.",
            topic: '5am morning routine',
            angle: 'personal_story',
            category: 'lifestyle',
            asset_type: 'photo',
            created_at: '2025-03-17T07:00:00Z',
            status: 'draft',
            variants: {
                linkedin:  { platform:'linkedin',  status:'ready',     scheduled_at:'2025-03-19T07:30:00', caption:"3 years ago I was doing 5am morning routine manually. Today AI handles it in seconds. Here's the before and after:\n\nHere's what nobody tells you about building this from scratch:\n\n→ Month 1: Complete chaos. Manual processes everywhere. The team was exhausted.\n→ Month 3: We started automating the repetitive work. Morale improved immediately.\n→ Month 6: The numbers started compounding. Same team, 3× the output.\n\nThe turning point wasn't a new tool or a new hire.\n\nWhat was your turning point? Drop it in the comments — I read every one.", hashtags:'#entrepreneurship #productivity #mindset #leadership #growth', creative_notes:'Authentic morning photo — warm light, coffee. Real, not staged.', email_subject:null, email_preview:null, title:null },
                facebook:  { platform:'facebook',  status:'draft',     scheduled_at:null,                  caption:"Real talk — nobody prepares you for what 5am morning routine actually feels like in year one.\n\nHere's the part most people leave out:\n\nDay 1–30: It's genuinely hard. You're not a morning person. Your body fights you every day.\n\nDay 31–60: Something shifts. Not dramatically — just slightly less resistance.\n\nDay 61–90: The routine runs itself. The ROI becomes obvious.\n\nI'm not saying everyone should do this. I'm saying the people who do it for 90 days almost never stop.\n\nWho's on a streak right now? Comment below 👇", hashtags:'#productivity #entrepreneur', creative_notes:'Morning desk photo, warm light. Facebook image: 1200×630 with subtle time overlay "5:00 AM".', email_subject:null, email_preview:null, title:null },
                instagram: { platform:'instagram', status:'draft',     scheduled_at:null,                  caption:"The hardest year of building taught me the most important lesson. 🧵\n\n90 days of 5am wake-ups.\n\nHere's what nobody tells you:\n\nDays 1–10: You hate it.\n\nDays 11–30: You tolerate it.\n\nDays 31–60: You need it.\n\nDays 61–90: You can't imagine not doing it.\n\nThe discipline isn't in the alarm.\n\nIt's in choosing what to do with the silence before the world wakes up.\n\n👉 Save this if you're building something.\n\n.\n.\n.", hashtags:'#entrepreneur #entrepreneurlife #productivity #morningroutine #mindset #growthmindset #motivation #success #businessowner #ceo #leadership #personaldevelopment #selfimprovement #businesstips #smallbusiness #grind #hustle #worklifebalance #goaldigger #bossbabe #successmindset #dailyroutine #habitsthatwork #morningmotivation #thinkbig #levelup #selfdiscipline #executivecoach #mindsetmatters #buildingwealth', creative_notes:'Authentic photo essential. 5am on clock or phone visible. No overly curated aesthetic.', email_subject:null, email_preview:null, title:null },
                youtube:   { platform:'youtube',   status:'draft',     scheduled_at:null,                  title:'I Woke Up at 5AM Every Day for 90 Days — Here\'s What Actually Happens', caption:"I committed to waking up at 5am every day for 90 days. No exceptions. In this video, I'm sharing the honest version of what changes — and what doesn't.\n\nThis isn't a motivational video. It's a real account of what the data actually looks like when you build this habit from scratch.\n\n⏱ TIMESTAMPS:\n00:00 — Why I did this\n04:00 — Days 1–30: The honest truth\n11:00 — Days 31–60: The shift\n17:00 — Days 61–90: Where it compounds\n23:00 — What actually changed (and what didn't)\n28:00 — Should you try it?", hashtags:'productivity, morningroutine, 5amclub, entrepreneur, habits', creative_notes:'Thumbnail: split — tired face (left) vs. alert/focused (right). Bold "Day 90" text.', email_subject:null, email_preview:null },
                email:     { platform:'email',     status:'draft',     scheduled_at:null,                  email_subject:'90 days of 5am. Here\'s the honest version.', email_preview:'The part most people leave out of the morning routine story — and why it matters.', caption:"Hey {first_name},\n\nI've been doing something a bit unusual for the last 90 days.\n\nWaking up at 5am. Every day. No exceptions.\n\nI want to share the honest version of what happened — not the LinkedIn highlight reel.\n\nDays 1–30: Hard. Genuinely hard. My body fought me every morning.\n\nDays 31–60: Slightly less resistance. The routine started running itself a little.\n\nDays 61–90: The ROI became obvious. Clearer thinking, more output, less reactive.\n\nThe big shift wasn't the wake-up time. It was having 2 hours before the world starts demanding things from you.\n\nI wrote up everything I learned here: [link]\n\nWorth a read if you're thinking about building a morning practice.\n\n— [Name]", hashtags:'', title:null, creative_notes:'Personal tone. No images. Plain-text personal newsletter feel.' },
            },
        },
    ]};  // end _LEGACY_SEED


/* ═══════════════════════════════════════════════════════════════════════════
   AIDEN APP  — top-level navigation and rendering orchestration
   ═══════════════════════════════════════════════════════════════════════════ */
const AidenApp = {
    _initialized: false,

    _state: {
        section:  'content',    // 'social' | 'content' | 'email'
        platform: 'linkedin',   // Social Media active platform
        ceTab:    'optimizer',  // Content Engine sub-tab: optimizer|queue|history

        // Content Optimizer
        pastedContent:      '',
        contentType:        'thought_leadership',
        optimizerTone:      'professional',
        optimizedPlatforms: null,   // { linkedin, facebook, instagram, tiktok, youtube }
    },

    // ── Entry point ──────────────────────────────────────────────────────────
    init() {
        if (this._initialized) return;
        this._initialized = true;
        const el = document.getElementById('cc-company-aiden');
        if (!el) return;
        el.innerHTML = this._shellHTML();
        this._bindNav();
        this._renderSection();
    },

    _shellHTML() {
        return `
        <div class="aiden-wrap">
            <div class="aiden-nav-bar">
                <button class="aiden-nav-btn active" data-aiden-section="content">Content Engine</button>
                <button class="aiden-nav-btn"        data-aiden-section="social">Social Media</button>
                <button class="aiden-nav-btn"        data-aiden-section="email">Email</button>
                <button class="aiden-nav-btn aiden-nav-btn--memory" data-aiden-section="memory">System Memory</button>
            </div>
            <div id="aiden-section-content" class="aiden-panel active"></div>
            <div id="aiden-section-social"  class="aiden-panel"></div>
            <div id="aiden-section-email"   class="aiden-panel"></div>
            <div id="aiden-section-memory"  class="aiden-panel"></div>
        </div>`;
    },

    _bindNav() {
        document.querySelectorAll('.aiden-nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._state.section = btn.dataset.aidenSection;
                document.querySelectorAll('.aiden-nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.aiden-panel').forEach(p => p.classList.remove('active'));
                const panel = document.getElementById('aiden-section-' + this._state.section);
                if (panel) panel.classList.add('active');
                this._renderSection();
            });
        });
    },

    _renderSection() {
        if (this._state.section === 'social')  this._renderSocial();
        if (this._state.section === 'content') this._renderContentEngine();
        if (this._state.section === 'email')   this._renderEmailPlaceholder();
        if (this._state.section === 'memory')  this._renderSystemMemory();
    },

    /* ════════════════════════════════════════════════════════════════════════
       SOCIAL MEDIA  — platform channel overview
       ════════════════════════════════════════════════════════════════════════ */
    _renderSocial() {
        const panel = document.getElementById('aiden-section-social');
        if (!panel) return;

        const platforms = [
            { id: 'linkedin',  label: 'LinkedIn',  icon: '💼' },
            { id: 'facebook',  label: 'Facebook',  icon: '📘' },
            { id: 'instagram', label: 'Instagram', icon: '📸' },
            { id: 'youtube',   label: 'YouTube',   icon: '▶️'  },
        ];

        const platBtns = platforms.map(p =>
            `<button class="aiden-platform-btn${p.id === this._state.platform ? ' active' : ''}" data-platform="${p.id}">
                <span class="aiden-platform-icon">${p.icon}</span>${p.label}
            </button>`
        ).join('');

        panel.innerHTML = `
            <div class="aiden-platform-nav">${platBtns}</div>
            ${platforms.map(p =>
                `<div id="aiden-plat-${p.id}" class="aiden-platform-panel${p.id === this._state.platform ? ' active' : ''}"></div>`
            ).join('')}
        `;

        panel.querySelectorAll('.aiden-platform-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._state.platform = btn.dataset.platform;
                panel.querySelectorAll('.aiden-platform-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                panel.querySelectorAll('.aiden-platform-panel').forEach(p => p.classList.remove('active'));
                const pp = document.getElementById('aiden-plat-' + this._state.platform);
                if (pp) pp.classList.add('active');
                this._renderSocialPlatform(this._state.platform);
            });
        });

        this._renderSocialPlatform(this._state.platform);
    },

    _renderSocialPlatform(platform) {
        const ICONS = { linkedin:'💼', facebook:'📘', instagram:'📸', youtube:'▶️' };
        const el = document.getElementById('aiden-plat-' + platform);
        if (!el) return;

        // LinkedIn shows a channel summary with recent content stats
        if (platform === 'linkedin') {
            const queueItems   = ContentStore.queue;
            const historyItems = ContentStore.history;
            const scheduled    = queueItems.filter(q => q.channel_statuses?.linkedin?.status === 'scheduled');
            const recentQueue  = queueItems.slice(0, 3);
            const recentHist   = historyItems.slice(0, 3);

            const queueRows = recentQueue.map(q => {
                const st = q.channel_statuses?.linkedin?.status || 'draft';
                return `
                    <div class="social-recent-item">
                        <div class="social-recent-meta">
                            <span class="status-badge status-${st}">${st}</span>
                            <span class="social-recent-cat">${q.category}</span>
                            <span class="social-recent-date">Queued ${this._formatDate(q.queued_at.split('T')[0])}</span>
                        </div>
                        <div class="social-recent-preview">${this._esc(q.hook.split('\n')[0])}</div>
                    </div>`;
            }).join('');

            const histRows = recentHist.map(h => {
                const liMetrics = h.metrics?.linkedin || {};
                return `
                    <div class="social-recent-item">
                        <div class="social-recent-meta">
                            <span class="status-badge status-posted">posted</span>
                            <span class="social-recent-cat">${h.category}</span>
                            <span class="social-recent-date">Posted ${this._formatDate(h.posted_at.split('T')[0])}</span>
                        </div>
                        <div class="social-recent-preview">${this._esc(h.hook.split('\n')[0])}</div>
                        ${liMetrics.impressions ? `<div style="font-size:10px;color:#4b5563;margin-top:3px">${liMetrics.impressions.toLocaleString()} impressions · ${liMetrics.likes} likes · ${liMetrics.comments} comments · ${liMetrics.engagement_rate}% eng.</div>` : ''}
                    </div>`;
            }).join('');

            el.innerHTML = `
                <div class="social-channel-wrap">
                    <div class="social-channel-header">
                        <div class="social-channel-icon">💼</div>
                        <div>
                            <div class="social-channel-title">LinkedIn Channel</div>
                            <div class="social-channel-sub">Manage your LinkedIn content. Create new posts in the <button class="inline-link-btn" data-goto-content>Content Engine</button>.</div>
                        </div>
                    </div>
                    <div class="social-stats-grid">
                        <div class="social-stat-card"><div class="label">In Queue</div><div class="value">${queueItems.length}</div></div>
                        <div class="social-stat-card"><div class="label">Scheduled</div><div class="value">${scheduled.length}</div></div>
                        <div class="social-stat-card"><div class="label">Published</div><div class="value">${historyItems.length}</div></div>
                        <div class="social-stat-card"><div class="label">Avg Eng. Rate</div><div class="value">${historyItems.length ? (historyItems.reduce((s,h)=>s+(h.metrics?.linkedin?.engagement_rate||0),0)/historyItems.length).toFixed(1)+'%' : '—'}</div></div>
                    </div>
                    ${recentQueue.length ? `<div class="social-recent-title">Queue</div><div class="social-recent-list">${queueRows}</div>` : ''}
                    ${recentHist.length  ? `<div class="social-recent-title" style="margin-top:16px">Recent Posts</div><div class="social-recent-list">${histRows}</div>` : ''}
                </div>
            `;

            el.querySelector('[data-goto-content]')?.addEventListener('click', () => {
                const btn = document.querySelector('.aiden-nav-btn[data-aiden-section="content"]');
                if (btn) btn.click();
            });
            return;
        }

        // Other platforms — polished coming soon with channel-specific details
        const details = {
            facebook:  { sub: 'Facebook Page management, post scheduling, and audience engagement analytics.', integrations: 'Meta Business Suite, Buffer, Hootsuite' },
            instagram: { sub: 'Instagram feed, Stories, and Reels content planning with visual asset management.', integrations: 'Meta Business Suite, Later, Planoly' },
            youtube:   { sub: 'YouTube video content calendar, description generation, and publishing management.', integrations: 'YouTube Studio API, TubeBuddy, VidIQ' },
        }[platform];

        el.innerHTML = `
            <div class="aiden-coming-soon">
                <div class="aiden-cs-icon">${ICONS[platform]}</div>
                <div class="aiden-cs-title">${this._capitalize(platform)} Channel</div>
                <div class="aiden-cs-sub">
                    ${details.sub}<br><br>
                    Content for ${this._capitalize(platform)} is generated automatically in the
                    <strong style="color:#94a3b8">Content Engine</strong> when you create a master asset.
                    Channel-specific management tools are coming soon.<br><br>
                    <em style="font-size:11px;color:#374151">Planned integrations: ${details.integrations}</em>
                </div>
                <span class="aiden-cs-badge">Coming Soon</span>
            </div>
        `;
    },


    /* ════════════════════════════════════════════════════════════════════════
       CONTENT ENGINE  — optimizer → queue → history
       ════════════════════════════════════════════════════════════════════════ */
    _renderContentEngine() {
        const panel = document.getElementById('aiden-section-content');
        if (!panel) return;

        const tabs = [
            { id: 'optimizer', label: 'Optimizer' },
            { id: 'queue',     label: 'Queue'     },
            { id: 'history',   label: 'History'   },
        ];

        panel.innerHTML = `
            <div class="li-tabs-bar ce-tabs-bar">
                ${tabs.map(t =>
                    `<button class="li-tab-btn${t.id === this._state.ceTab ? ' active' : ''}" data-ce-tab="${t.id}">${t.label}</button>`
                ).join('')}
            </div>
            ${tabs.map(t =>
                `<div id="ce-sec-${t.id}" class="li-section${t.id === this._state.ceTab ? ' active' : ''}"></div>`
            ).join('')}
        `;

        panel.querySelectorAll('.li-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this._state.ceTab = btn.dataset.ceTab;
                panel.querySelectorAll('.li-tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                panel.querySelectorAll('.li-section').forEach(s => s.classList.remove('active'));
                const sec = document.getElementById('ce-sec-' + this._state.ceTab);
                if (sec) sec.classList.add('active');
                this._renderCESection(this._state.ceTab);
            });
        });

        this._renderCESection(this._state.ceTab);
    },

    _renderCESection(tab) {
        if (tab === 'optimizer') this._renderCEOptimizer();
        if (tab === 'queue')     this._renderCEQueue();
        if (tab === 'history')   this._renderCEHistory();
    },

    /* ── CONTENT OPTIMIZER ───────────────────────────────────────────────── */
    _renderCEOptimizer() {
        const sec = document.getElementById('ce-sec-optimizer');
        if (!sec) return;
        const s = this._state;

        const contentTypes = [
            {val:'thought_leadership', label:'Thought Leadership'},
            {val:'educational',        label:'Educational / How-To'},
            {val:'story',              label:'Personal Story'},
            {val:'case_study',         label:'Case Study / Results'},
            {val:'contrarian',         label:'Contrarian / Hot Take'},
            {val:'promotion',          label:'Promotion'},
            {val:'personal',           label:'Personal / Lifestyle'},
        ];
        const tones = [
            {val:'professional', label:'Professional'},
            {val:'founder',      label:'Founder Voice'},
            {val:'casual',       label:'Casual'},
            {val:'punchy',       label:'Punchy'},
            {val:'educational',  label:'Educational'},
        ];

        const PLATS = [
            { id:'linkedin',  icon:'💼', label:'LinkedIn' },
            { id:'facebook',  icon:'📘', label:'Facebook' },
            { id:'instagram', icon:'📸', label:'Instagram' },
            { id:'tiktok',    icon:'🎵', label:'TikTok'   },
            { id:'youtube',   icon:'▶️', label:'YouTube'   },
        ];

        const op = s.optimizedPlatforms;

        const _row = (label, val, id='') => val ? `
            <div class="gen-form-group" style="margin-bottom:10px">
                <label class="gen-form-label" style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:#4b5563">${label}</label>
                <div class="plat-field-textarea" contenteditable="true" id="${id}"
                     style="min-height:40px;font-size:13px;line-height:1.55;white-space:pre-wrap">${this._esc(val)}</div>
            </div>` : '';

        const _copyBtn = (targetId) =>
            `<button class="gen-btn-ghost" style="font-size:11px;padding:4px 10px" data-copy-target="${targetId}">Copy</button>`;

        const _platCard = (plat) => {
            const d = op?.[plat.id];
            if (!d) return '';

            const isYT = plat.id === 'youtube';
            const mainId  = `opt-${plat.id}-main`;
            const hashId  = `opt-${plat.id}-hash`;
            const cmtId   = `opt-${plat.id}-comment`;

            let inner = '';
            if (isYT) {
                inner = `
                    ${_row('Title', d.title, `opt-yt-title`)}
                    ${_row('Description', d.description, `opt-yt-desc`)}
                    ${d.hashtags ? _row('Tags', d.hashtags, `opt-yt-tags`) : ''}
                    <div style="margin:12px 0 8px;padding-top:10px;border-top:1px solid #20263a;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#4b5563">Comment Strategy</div>
                    ${_row('Pinned Comment', d.pinned_comment, `opt-yt-pin`)}
                    ${_row('Discussion Question', d.discussion_question, `opt-yt-q`)}
                    ${_row('CTA', d.cta, `opt-yt-cta`)}
                    ${d.comment_strategy ? `<div style="font-size:11px;color:#4b5563;line-height:1.5;margin-top:6px;padding:8px;background:#0a0e1a;border-radius:6px">${this._esc(d.comment_strategy)}</div>` : ''}
                `;
            } else {
                const copyLabel = plat.id === 'instagram' ? 'Caption' : 'Post Copy';
                const cmtLabel  = plat.id === 'instagram' ? 'First Comment (hashtags)' : 'Suggested First Comment';
                inner = `
                    ${_row(copyLabel, d.copy, mainId)}
                    ${d.hashtags ? _row('Hashtags', d.hashtags, hashId) : ''}
                    ${_row(cmtLabel, d.first_comment, cmtId)}
                    ${plat.id === 'tiktok' && d.overlay_text ? _row('Overlay Text', d.overlay_text, `opt-tiktok-overlay`) : ''}
                `;
            }

            const queueId = `opt-queue-${plat.id}`;
            return `
                <div class="gen-form-card" style="margin-bottom:14px;position:static" data-plat="${plat.id}">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
                        <div style="display:flex;align-items:center;gap:8px">
                            <span style="font-size:18px">${plat.icon}</span>
                            <span style="font-size:14px;font-weight:700;color:#f8fafc">${plat.label}</span>
                        </div>
                        <div style="display:flex;gap:6px">
                            <button class="gen-btn-ghost" style="font-size:11px;padding:4px 10px" data-copy-plat="${plat.id}">Copy All</button>
                            <button class="gen-btn gen-btn-primary" style="width:auto;padding:4px 14px;font-size:11px" id="${queueId}">+ Queue</button>
                        </div>
                    </div>
                    ${inner}
                </div>`;
        };

        const platformsHTML = op ? PLATS.map(p => _platCard(p)).join('') : '';

        sec.innerHTML = `
            <div style="max-width:760px">

                <div class="gen-form-card" style="position:static;margin-bottom:16px">
                    <div style="margin-bottom:6px">
                        <span style="font-size:16px;font-weight:700;color:#f8fafc">Content Optimizer</span>
                        <span style="font-size:12px;color:#4b5563;margin-left:10px">Paste your post → get platform-ready versions</span>
                    </div>
                    <div class="gen-form-group" style="margin-top:14px">
                        <label class="gen-form-label">Your Post or Draft</label>
                        <textarea class="gen-form-input" id="opt-content" rows="7"
                            placeholder="Paste your post, draft, or idea here. The optimizer will adapt it for LinkedIn, Facebook, Instagram, TikTok, and YouTube."
                            style="min-height:140px;font-size:13px;line-height:1.6">${this._esc(s.pastedContent)}</textarea>
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:0">
                        <div class="gen-form-group" style="margin-bottom:0">
                            <label class="gen-form-label">Content Type</label>
                            <select class="gen-form-select" id="opt-content-type">
                                ${contentTypes.map(ct=>`<option value="${ct.val}"${s.contentType===ct.val?' selected':''}>${ct.label}</option>`).join('')}
                            </select>
                        </div>
                        <div class="gen-form-group" style="margin-bottom:0">
                            <label class="gen-form-label">Tone</label>
                            <select class="gen-form-select" id="opt-tone">
                                ${tones.map(t=>`<option value="${t.val}"${s.optimizerTone===t.val?' selected':''}>${t.label}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <button class="gen-btn gen-btn-primary" id="opt-run-btn"
                        style="margin-top:16px;font-size:14px;padding:12px 28px">
                        Optimize for All Platforms
                    </button>
                </div>

                ${platformsHTML}
            </div>
        `;

        // ── Bindings ─────────────────────────────────────────────────────────
        sec.querySelector('#opt-content')?.addEventListener('input',      e => { s.pastedContent  = e.target.value; });
        sec.querySelector('#opt-content-type')?.addEventListener('change', e => { s.contentType    = e.target.value; });
        sec.querySelector('#opt-tone')?.addEventListener('change',         e => { s.optimizerTone  = e.target.value; });

        sec.querySelector('#opt-run-btn')?.addEventListener('click', async () => {
            if (!s.pastedContent.trim()) { this._toast('Paste your content first'); return; }
            const btn = sec.querySelector('#opt-run-btn');
            if (btn) { btn.textContent = 'Optimizing…'; btn.disabled = true; }
            try {
                const resp = await fetch('/api/aiden/optimize-post', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: s.pastedContent, content_type: s.contentType, tone: s.optimizerTone }),
                });
                if (!resp.ok) throw new Error(`API ${resp.status}`);
                s.optimizedPlatforms = await resp.json();
            } catch(e) {
                this._toast('Optimization failed — check server');
                if (btn) { btn.textContent = 'Optimize for All Platforms'; btn.disabled = false; }
                return;
            }
            this._renderCEOptimizer();
        });

        // Copy All buttons — copies the full visible text of a platform card
        sec.querySelectorAll('[data-copy-plat]').forEach(btn => {
            btn.addEventListener('click', () => {
                const platId = btn.dataset.copyPlat;
                const card   = sec.querySelector(`[data-plat="${platId}"]`);
                if (!card) return;
                const text = [...card.querySelectorAll('[contenteditable]')]
                    .map(el => el.innerText.trim())
                    .filter(Boolean)
                    .join('\n\n');
                navigator.clipboard.writeText(text).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy All'; }, 1500);
                });
            });
        });

        // + Queue buttons — saves platform version to ContentStore
        PLATS.forEach(plat => {
            sec.querySelector(`#opt-queue-${plat.id}`)?.addEventListener('click', () => {
                const d = s.optimizedPlatforms?.[plat.id];
                if (!d) return;
                const isYT = plat.id === 'youtube';
                const title = isYT
                    ? (sec.querySelector('#opt-yt-title')?.innerText || d.title || 'YouTube — Untitled')
                    : ContentStore._titleCase(s.pastedContent.slice(0, 40)) || plat.label;
                ContentStore.addToQueue({
                    title:      `${plat.icon} ${title}`,
                    hook:       isYT ? (d.title || '') : (sec.querySelector(`#opt-${plat.id}-main`)?.innerText || d.copy || '').split('\n')[0],
                    content:    isYT ? (sec.querySelector('#opt-yt-desc')?.innerText || d.description || '') : (sec.querySelector(`#opt-${plat.id}-main`)?.innerText || d.copy || ''),
                    cta:        isYT ? (sec.querySelector('#opt-yt-cta')?.innerText || d.cta || '') : (sec.querySelector(`#opt-${plat.id}-comment`)?.innerText || d.first_comment || ''),
                    hashtags:   isYT ? (sec.querySelector('#opt-yt-tags')?.innerText || d.hashtags || '') : (sec.querySelector(`#opt-${plat.id}-hash`)?.innerText || d.hashtags || ''),
                    category:   'optimizer',
                    asset_type: plat.id,
                    created_at: new Date().toISOString(),
                });
                this._toast(`${plat.label} version added to Queue`);
            });
        });
    },

    /* ── UNIFIED QUEUE (replaces old Queue + Platforms) ─────────────────── */
    _renderCEQueue() {
        const sec = document.getElementById('ce-sec-queue');
        if (!sec) return;

        const CHANNELS    = ['linkedin','facebook','instagram','youtube','email'];
        const PLAT_ICONS  = {linkedin:'💼',facebook:'📘',instagram:'📸',youtube:'▶️',email:'✉️'};
        const PLAT_LABELS = {linkedin:'LinkedIn',facebook:'Facebook',instagram:'Instagram',youtube:'YouTube',email:'Email'};
        const STATUS_OPTS = ['draft','queued','scheduled','posted','failed','needs_review'];
        const STATUS_LABELS = {draft:'Draft',queued:'Queued',scheduled:'Scheduled',posted:'Posted',failed:'Failed',needs_review:'Needs Review'};

        const items = ContentStore.queue;

        const channelDots = (item) => CHANNELS.map(ch => {
            const st = item.channel_statuses[ch]?.status || 'draft';
            return `<span class="q-ch-dot status-dot-sm status-${st}" data-qid="${item.id}" data-ch="${ch}" title="${PLAT_LABELS[ch]}: ${st}">${PLAT_ICONS[ch]}</span>`;
        }).join('');

        const queueCards = items.map(item => {
            const variantRows = CHANNELS.map(ch => {
                const st = item.channel_statuses[ch]?.status || 'draft';
                const cap = item.channel_statuses[ch]?.caption || item.content || '';
                const preview = cap.replace(/\n/g,' ').substring(0, 90) + (cap.length > 90 ? '…' : '');
                return `
                    <tr class="queue-variant-row" data-qid="${item.id}" data-ch="${ch}">
                        <td style="padding-left:20px;width:110px">
                            <span class="plat-icon-sm">${PLAT_ICONS[ch]}</span>
                            <span style="font-size:12px;color:#94a3b8">${PLAT_LABELS[ch]}</span>
                        </td>
                        <td>
                            <span class="status-badge status-${st}" id="qs-${item.id}-${ch}">${STATUS_LABELS[st]}</span>
                        </td>
                        <td class="queue-preview-cell">${this._esc(preview)}</td>
                        <td style="width:140px">
                            <select class="queue-cat-select" data-qid="${item.id}" data-ch="${ch}">
                                ${STATUS_OPTS.map(v => `<option value="${v}"${st===v?' selected':''}>${STATUS_LABELS[v]}</option>`).join('')}
                            </select>
                        </td>
                    </tr>`;
            }).join('');

            return `
                <div class="master-queue-card" data-qid="${item.id}">
                    <div class="master-queue-header">
                        <div class="master-queue-left">
                            <button class="master-expand-btn" data-expand="${item.id}">▶</button>
                            <span class="asset-icon-sm">${this._assetIcon(item.asset_type)}</span>
                            <div>
                                <div class="master-queue-title">${this._esc(item.title)}</div>
                                <div class="master-queue-meta">${item.category} · ${item.asset_type} · Queued ${this._formatDate(item.queued_at.split('T')[0])}</div>
                            </div>
                        </div>
                        <div class="master-queue-right">
                            <div class="q-channel-dots" style="display:flex;gap:4px;align-items:center">${channelDots(item)}</div>
                            <button class="queue-del-btn" data-del-qid="${item.id}" title="Remove from Queue" style="margin-left:8px;font-size:14px">✕</button>
                        </div>
                    </div>
                    <div class="master-queue-variants" id="qv-${item.id}" style="display:none">
                        <div style="padding:14px 18px;border-bottom:1px solid #131a26">
                            <div class="gen-section-label">Hook</div>
                            <div style="font-size:13px;font-weight:600;color:#e2e8f0;line-height:1.5;white-space:pre-line;margin-bottom:12px">${this._esc(item.hook)}</div>
                            <div class="gen-section-label">Content</div>
                            <div class="plat-field-textarea" contenteditable="true" data-qid="${item.id}" data-field="content" style="min-height:120px">${this._esc(item.content)}</div>
                            <div class="gen-section-label" style="margin-top:10px">CTA</div>
                            <div class="plat-field-input" contenteditable="true" data-qid="${item.id}" data-field="cta">${this._esc(item.cta)}</div>
                        </div>
                        <table class="queue-table" style="margin-top:0">
                            <thead><tr>
                                <th>Channel</th><th>Status</th><th>Content Preview</th><th>Update Status</th>
                            </tr></thead>
                            <tbody>${variantRows}</tbody>
                        </table>
                    </div>
                </div>`;
        }).join('');

        sec.innerHTML = `
            <div class="queue-section">
                <div class="queue-header">
                    <div class="queue-title">Content Queue</div>
                    <div class="queue-header-actions">
                        <span class="queue-count">${items.length} item${items.length !== 1 ? 's' : ''}</span>
                        <button class="queue-add-btn" id="ce-new-hook-btn">+ New Post</button>
                    </div>
                </div>
                <div id="ce-queue-list">
                    ${queueCards || `<div class="upcoming-empty" style="padding:60px 0">No items in queue.<br>Go to Hooks to generate and add content.</div>`}
                </div>
            </div>
        `;

        // Expand/collapse
        sec.querySelectorAll('.master-expand-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const wrapper = document.getElementById('qv-' + btn.dataset.expand);
                const isOpen  = wrapper.style.display !== 'none';
                wrapper.style.display = isOpen ? 'none' : 'block';
                btn.textContent = isOpen ? '▶' : '▼';
            });
        });

        // Status dropdown — sync badge + dot in real time, auto-move to history
        sec.querySelectorAll('[data-qid][data-ch]').forEach(sel => {
            sel.addEventListener('change', () => {
                const { qid, ch } = sel.dataset;
                const result = ContentStore.updateChannelStatus(qid, ch, sel.value);

                if (result === 'moved') {
                    this._toast('All channels posted — moved to History');
                    this._renderCEQueue();
                    return;
                }

                // Sync status badge (inside expanded row)
                const badge = sec.querySelector(`#qs-${qid}-${ch}`);
                if (badge) {
                    badge.className = `status-badge status-${sel.value}`;
                    badge.textContent = sel.value.charAt(0).toUpperCase() + sel.value.slice(1).replace('_',' ');
                }
                // Sync dot (in collapsed header)
                const dot = sec.querySelector(`.q-ch-dot[data-qid="${qid}"][data-ch="${ch}"]`);
                if (dot) dot.className = `q-ch-dot status-dot-sm status-${sel.value}`;
            });
        });

        // Inline content editing
        sec.querySelectorAll('[contenteditable][data-qid][data-field]').forEach(el => {
            el.addEventListener('input', () => {
                ContentStore.updateContent(el.dataset.qid, el.dataset.field, el.innerText);
            });
        });

        // Delete
        sec.querySelectorAll('[data-del-qid]').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.delQid;
                const item = ContentStore.queue.find(q => q.id === id);
                if (!item) return;
                if (!confirm(`Remove "${item.title}" from the queue?`)) return;
                ContentStore.removeFromQueue(id);
                this._renderCEQueue();
                this._toast('Removed from queue');
            });
        });

        sec.querySelector('#ce-new-hook-btn')?.addEventListener('click', () => {
            this._state.ceTab = 'optimizer';
            this._renderContentEngine();
        });
    },

    /* ── POST HISTORY (replaces Scheduler) ──────────────────────────────── */
    _renderCEHistory() {
        const sec = document.getElementById('ce-sec-history');
        if (!sec) return;

        const CHANNELS   = ['linkedin','facebook','instagram','youtube','email'];
        const PLAT_ICONS = {linkedin:'💼',facebook:'📘',instagram:'📸',youtube:'▶️',email:'✉️'};
        const items      = ContentStore.history;

        const metricCell = (val, label) =>
            `<div class="social-stat-card" style="padding:10px 12px;min-width:80px">
                <div class="social-stat-label">${label}</div>
                <div class="social-stat-value" style="font-size:16px">${val !== null && val !== undefined ? val.toLocaleString() : '—'}</div>
            </div>`;

        const historyCards = items.map(item => {
            // Aggregate metrics across all platforms
            const totals = CHANNELS.reduce((acc, ch) => {
                const m = item.metrics?.[ch] || {};
                acc.impressions += m.impressions || 0;
                acc.likes       += m.likes       || 0;
                acc.comments    += m.comments    || 0;
                acc.shares      += m.shares      || 0;
                acc.clicks      += m.clicks      || 0;
                return acc;
            }, {impressions:0, likes:0, comments:0, shares:0, clicks:0});
            const totalEngagement = totals.impressions > 0
                ? ((totals.likes + totals.comments + totals.shares) / totals.impressions * 100).toFixed(1)
                : '—';

            const platformBreakdown = CHANNELS.map(ch => {
                const st = item.channel_statuses?.[ch]?.status || 'posted';
                const m  = item.metrics?.[ch] || {};
                return `
                    <tr>
                        <td style="padding:7px 12px;font-size:12px;color:#94a3b8">${PLAT_ICONS[ch]}</td>
                        <td style="padding:7px 12px;font-size:12px;color:#94a3b8">${ch.charAt(0).toUpperCase()+ch.slice(1)}</td>
                        <td style="padding:7px 12px"><span class="status-badge status-${st}" style="font-size:9px">${st}</span></td>
                        <td style="padding:7px 12px;font-size:12px;font-variant-numeric:tabular-nums;color:#6b7280">${(m.impressions||0).toLocaleString()}</td>
                        <td style="padding:7px 12px;font-size:12px;font-variant-numeric:tabular-nums;color:#6b7280">${(m.likes||0).toLocaleString()}</td>
                        <td style="padding:7px 12px;font-size:12px;font-variant-numeric:tabular-nums;color:#6b7280">${(m.comments||0).toLocaleString()}</td>
                        <td style="padding:7px 12px;font-size:12px;font-variant-numeric:tabular-nums;color:#6b7280">${(m.shares||0).toLocaleString()}</td>
                        <td style="padding:7px 12px;font-size:12px;color:${m.engagement_rate>3?'#34d399':'#6b7280'}">${m.engagement_rate ? m.engagement_rate+'%' : '—'}</td>
                        <td style="padding:7px 12px;font-size:11px;color:#374151">${m.post_url ? `<a href="${m.post_url}" target="_blank" style="color:#0ea5e9">View</a>` : '—'}</td>
                    </tr>`;
            }).join('');

            return `
                <div class="master-queue-card" style="margin-bottom:10px">
                    <div class="master-queue-header" style="cursor:default">
                        <div class="master-queue-left">
                            <span class="asset-icon-sm">📋</span>
                            <div>
                                <div class="master-queue-title">${this._esc(item.title)}</div>
                                <div class="master-queue-meta">
                                    Posted ${this._formatDate(item.posted_at.split('T')[0])} ·
                                    Created ${this._formatDate(item.created_at.split('T')[0])} ·
                                    ${item.category}
                                </div>
                            </div>
                        </div>
                        <div class="master-queue-right">
                            <button class="master-expand-btn" data-hist-expand="${item.id}">▶</button>
                        </div>
                    </div>
                    <div id="hv-${item.id}" style="display:none;border-top:1px solid #131a26">
                        <!-- Hook preview -->
                        <div style="padding:14px 18px;border-bottom:1px solid #0e1220">
                            <div class="gen-section-label">Hook</div>
                            <div style="font-size:13px;color:#94a3b8;line-height:1.5;white-space:pre-line;margin-bottom:10px">${this._esc((item.hook||'').substring(0,200))}</div>
                            <div class="gen-section-label">Content Preview</div>
                            <div style="font-size:12px;color:#6b7280;line-height:1.5;white-space:pre-line">${this._esc((item.content_preview||'').substring(0,300))}</div>
                        </div>
                        <!-- Aggregate metrics -->
                        <div style="padding:14px 18px;border-bottom:1px solid #0e1220">
                            <div class="gen-section-label" style="margin-bottom:10px">Combined Performance</div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap">
                                ${metricCell(totals.impressions,'Impressions')}
                                ${metricCell(totals.likes,'Likes')}
                                ${metricCell(totals.comments,'Comments')}
                                ${metricCell(totals.shares,'Shares')}
                                ${metricCell(totals.clicks,'Clicks')}
                                ${metricCell(totalEngagement,'Eng. Rate')}
                            </div>
                            <div style="font-size:10px;color:#374151;margin-top:10px;font-style:italic">
                                INTEGRATION POINT: Connect LinkedIn API / Facebook Insights / Instagram Graph API to populate live metrics.
                            </div>
                        </div>
                        <!-- Per-platform breakdown -->
                        <div style="overflow-x:auto;padding-bottom:4px">
                            <table class="queue-table" style="margin:0">
                                <thead><tr>
                                    <th></th><th>Platform</th><th>Status</th>
                                    <th>Impressions</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Eng Rate</th><th>Link</th>
                                </tr></thead>
                                <tbody>${platformBreakdown}</tbody>
                            </table>
                        </div>
                    </div>
                </div>`;
        }).join('');

        sec.innerHTML = `
            <div class="queue-section">
                <div class="queue-header">
                    <div class="queue-title">Post History</div>
                    <div class="queue-header-actions">
                        <span class="queue-count">${items.length} post${items.length !== 1 ? 's' : ''}</span>
                        <span style="font-size:11px;color:#374151;padding:4px 10px;background:#0f1320;border:1px solid #20263a;border-radius:6px">LinkedIn integration coming soon</span>
                    </div>
                </div>
                <div>
                    ${historyCards || `<div class="upcoming-empty" style="padding:60px 0">No post history yet.<br>Items appear here automatically once all channels are set to Posted.</div>`}
                </div>
            </div>
        `;

        // Expand/collapse
        sec.querySelectorAll('[data-hist-expand]').forEach(btn => {
            btn.addEventListener('click', () => {
                const wrapper = document.getElementById('hv-' + btn.dataset.histExpand);
                const isOpen  = wrapper.style.display !== 'none';
                wrapper.style.display = isOpen ? 'none' : 'block';
                btn.textContent = isOpen ? '▶' : '▼';
            });
        });
    },

    /* ── EMAIL PLACEHOLDER ──────────────────────────────────────────────── */
    _renderEmailPlaceholder() {
        const panel = document.getElementById('aiden-section-email');
        if (!panel) return;
        panel.innerHTML = `
            <div class="aiden-coming-soon">
                <div class="aiden-cs-icon">✉️</div>
                <div class="aiden-cs-title">Email Content Operations</div>
                <div class="aiden-cs-sub">
                    Email campaign builder, sequence templates, subject line generator, A/B testing,
                    and send-time optimization — coming soon.<br><br>
                    Email content is already generated automatically for each master asset in the
                    <strong style="color:#94a3b8">Content Engine</strong>.<br><br>
                    <em style="font-size:11px;color:#374151">Planned integrations: Instantly.ai, HubSpot, Klaviyo, direct SMTP</em>
                </div>
                <span class="aiden-cs-badge">Coming Soon</span>
            </div>
        `;
    },

    /* ════════════════════════════════════════════════════════════════════════
       SYSTEM MEMORY  — spec sheet · changelog · system status
       ════════════════════════════════════════════════════════════════════════ */

    _MEMORY_DATA: {
        version: '3.4.0',
        specVersion: '3.4',
        lastUpdate: '2026-03-15',
        status: { api: 'healthy', db: 'healthy', workers: 'healthy', blob: 'healthy', auth: 'healthy' },

        changelog: [
            {
                date: '2026-03-15', version: '3.4.0', type: 'feature',
                title: 'Aiden System Memory — Spec Sheet & Changelog Center',
                tags: ['aiden', 'ui', 'docs'],
                added: ['System Memory section in Aiden tab', 'Spec sheet viewer with 15 expandable sections', 'Software changelog timeline', 'System status widget', 'Finalize Daily Log modal workflow'],
                changed: [], fixed: [], notes: 'Built into aiden.js — no server dependency.',
            },
            {
                date: '2026-03-14', version: '3.3.2', type: 'fix',
                title: 'TRG Executive Command Center — AI Insights Panel',
                tags: ['trg', 'ai', 'demo-studio'],
                added: ['9-section TRG executive dashboard', 'Keyword-matched AI response engine'],
                changed: ['executive/page.tsx routes TRG slug to TRGExecutive component'],
                fixed: ['AI response panel loading state timing'], notes: '',
            },
            {
                date: '2026-03-14', version: '3.3.1', type: 'feature',
                title: 'Sales Performance Section — All Demos',
                tags: ['sales', 'demo-studio', 'data'],
                added: ['sales-seed.ts deterministic generator', 'DynamicSalesPage — works for all demos', '8 sections: KPI, pipeline, rep leaderboard, call quality, coaching'],
                changed: ['DemoSidebar.tsx — added Sales Performance nav item'],
                fixed: [], notes: 'Industry-specific rep titles and deal sizes via SalesProfile.',
            },
            {
                date: '2026-03-13', version: '3.3.0', type: 'feature',
                title: 'Demo Space Lifecycle — Delete & Auto-Live',
                tags: ['admin', 'demo-studio', 'blob'],
                added: ['deleteDemoAsync() with tombstone pattern', 'DELETE /api/demos/[slug] route', 'DeleteDemoButton client component (type "delete" to confirm)'],
                changed: ['New demos publish directly as "live" instead of "generated"'],
                fixed: [], notes: 'Tombstone stored in Vercel Blob as aiden-deleted-demos.json.',
            },
            {
                date: '2026-03-12', version: '3.2.0', type: 'feature',
                title: 'All 8 Dashboard Pages — Data-Driven for Any Demo',
                tags: ['demo-studio', 'data', 'ui'],
                added: ['full-demo-seed.ts — generateFullDemoSeed() with 7 industry profiles', 'GenericRevenue, GenericLogistics, GenericProjects, GenericCustomers, GenericVendors, GenericInventory, GenericFreight, GenericMarket'],
                changed: ['All 8 dashboard pages now route non-Millennium slugs to DynamicXxx components'],
                fixed: [], notes: 'No TanStack DataTable or Leaflet — avoids build type conflicts.',
            },
            {
                date: '2026-03-10', version: '3.1.0', type: 'feature',
                title: 'Sales Section — BCAT Command Center',
                tags: ['bcat', 'sales', 'outreach'],
                added: ['Sales tab in BCAT Command Center', 'Instantly.ai campaign sync', 'Lead scraping (Maps + LinkedIn)', 'Message template generator', 'Meeting calendar integration'],
                changed: [], fixed: [], notes: 'sales.js + sales.css + sales_service.py',
            },
            {
                date: '2026-03-08', version: '3.0.0', type: 'feature',
                title: 'Multi-Company Command Center Architecture',
                tags: ['bcat', 'architecture'],
                added: ['Company tabs: BCAT, Ivan Cartage, Best Care Auto Transport, Aiden, Agents', 'Department subtabs: Finance, Marketing, Sales', 'AidenApp.init() content operations engine'],
                changed: ['dashboard.html refactored from single-page to command center shell'],
                fixed: [], notes: '',
            },
            {
                date: '2026-03-05', version: '2.0.0', type: 'feature',
                title: 'Content Engine — Master Asset Library',
                tags: ['aiden', 'content'],
                added: ['Pattern Library (30 hook templates, 15 post structures)', 'PostGenerator with 7 industry profiles', 'PlatformAdapter for LinkedIn, Facebook, Instagram, YouTube, Email', 'Content queue and scheduler', 'AI optimization via /api/aiden/optimize-post'],
                changed: [], fixed: [], notes: 'Version 2.0 — complete rewrite of content system.',
            },
        ],

        spec: [
            {
                id: 'overview', title: '1. System Overview',
                summary: 'BCAT Command Center is a multi-company AI operations dashboard serving BCAT Freight Brokerage, Ivan Cartage, Best Care Auto Transport, and the Aiden AI platform. Built with Flask + Chart.js, no npm/build step required.',
                subsections: [
                    { title: 'Stack', content: 'Python 3.14 · Flask 3.1.3 · Chart.js (CDN) · Vanilla JS · No React/Next.js in this project' },
                    { title: 'Entry Point', content: 'dashboard.py on port 5050. Serves GET / → dashboard.html, all API routes under /api/*' },
                    { title: 'Companion Project', content: 'aiden-demo-studio (Next.js 14) — separate codebase for client-facing demo environments' },
                ]
            },
            {
                id: 'architecture', title: '2. Architecture',
                summary: 'Single Flask process serving HTML/JS/CSS. No database — CSVs are the source of truth for finance. Vercel Blob used by demo-studio for persistent demo config.',
                subsections: [
                    { title: 'Finance Layer', content: 'FinanceAgent ingests 5 CSVs on every request. No caching — fresh compute each call.' },
                    { title: 'Marketing Layer', content: 'marketing_data.py returns static mock data. MarketingAgent calls Claude API for AI analysis.' },
                    { title: 'Sales Layer', content: 'sales_service.py integrates Instantly.ai, Google Calendar, and web scrapers.' },
                    { title: 'Aiden Layer', content: 'Pure frontend — aiden.js owns all rendering inside #cc-company-aiden. No server state.' },
                ]
            },
            {
                id: 'aiden-content', title: '3. Aiden Content Engine',
                summary: 'Master asset library system for generating LinkedIn, Facebook, Instagram, YouTube, and Email content from a single topic input.',
                subsections: [
                    { title: 'Pattern Library', content: '30 hook templates across 10 categories × 3 templates. 15 post structures. 7 CTA templates.' },
                    { title: 'PostGenerator', content: 'Generates master concept from topic + angle + category. PlatformAdapter transforms it for each channel.' },
                    { title: 'Style Modes', content: 'operator_founder · authority · conversational · academic · direct. Applied via text transforms.' },
                    { title: 'AI Integration', content: 'POST /api/aiden/optimize-post → content_optimizer.py → Claude API. Falls back to pattern-only if no API key.' },
                ]
            },
            {
                id: 'demo-studio', title: '4. Aiden Demo Studio',
                summary: 'Next.js 14 App Router multi-tenant demo environment. Each client gets a unique slug with isolated data, credentials, and dashboard.',
                subsections: [
                    { title: 'Demo Lifecycle', content: 'Admin creates demo → saveDemoAsync() → Vercel Blob → status: live immediately' },
                    { title: 'Delete Flow', content: 'deleteDemoAsync() removes from Blob registry + adds slug to tombstone list (aiden-deleted-demos.json)' },
                    { title: 'Data Generation', content: 'generateFullDemoSeed(config) — deterministic from slug. Same slug = same data every time.' },
                    { title: 'Industry Profiles', content: '7 profiles: logistics, healthcare, manufacturing, technology, retail, finance, default. Shape all KPIs, deal sizes, rep titles.' },
                ]
            },
            {
                id: 'data-model', title: '5. Data Model',
                summary: 'StoredDemo is the core config object. All dashboard data derives from it via seed generators.',
                subsections: [
                    { title: 'StoredDemo fields', content: 'slug · companyName · industry · status · primaryColor · description · prompt · credentials[] · createdAt · updatedAt' },
                    { title: 'FullDemoSeed', content: 'kpis · divisions · monthlyRevenue · customers · vendors · projects · shipments · carriers · skus · warehouses · marketData · alerts' },
                    { title: 'SalesSeed', content: 'reps[] · opportunities[] · monthly[] · pipeline stages · call quality scores · coaching flags' },
                ]
            },
            {
                id: 'deployment', title: '6. Deployment',
                summary: 'BCAT Command Center runs on Replit at https://app.tryaiden.ai. Demo Studio deploys to Vercel with Blob storage.',
                subsections: [
                    { title: 'Production (this app)', content: 'Replit → gunicorn dashboard:app → https://app.tryaiden.ai. Start command in .replit.' },
                    { title: 'Local dev', content: 'python dashboard.py → http://127.0.0.1:5050. FLASK_ENV=development, debug mode on.' },
                    { title: 'Demo Studio', content: 'Vercel deployment from aiden-demo-studio. BLOB_READ_WRITE_TOKEN env var required.' },
                    { title: 'Discord Bot', content: 'python discord_bot.py — separate process. Reads DISCORD_BOT_TOKEN from .env.' },
                    { title: 'Openclaw Gateway', content: 'macOS LaunchAgent on 127.0.0.1:18789. Connects Telegram @big_ron_bot to agent system.' },
                ]
            },
        ],
    },

    _memoryTab: 'changelog',   // 'changelog' | 'spec' | 'status'

    _renderSystemMemory() {
        const panel = document.getElementById('aiden-section-memory');
        if (!panel) return;
        const d = this._MEMORY_DATA;
        const tab = this._memoryTab;

        panel.innerHTML = `
        <div class="sm-wrap">
            <div class="sm-header">
                <div class="sm-header-left">
                    <div class="sm-title">Aiden System Memory</div>
                    <div class="sm-meta">v${this._esc(d.version)} · Spec ${this._esc(d.specVersion)} · Updated ${this._esc(d.lastUpdate)}</div>
                </div>
                <button class="sm-finalize-btn" id="sm-finalize-btn">Finalize Daily Log</button>
            </div>

            <div class="sm-tabs">
                <button class="sm-tab${tab==='changelog'?' active':''}" data-sm-tab="changelog">Changelog</button>
                <button class="sm-tab${tab==='spec'?' active':''}"       data-sm-tab="spec">Spec Sheet</button>
                <button class="sm-tab${tab==='status'?' active':''}"     data-sm-tab="status">System Status</button>
            </div>

            <div id="sm-body" class="sm-body">
                ${tab === 'changelog' ? this._smChangelogHTML(d.changelog) : ''}
                ${tab === 'spec'      ? this._smSpecHTML(d.spec)           : ''}
                ${tab === 'status'    ? this._smStatusHTML(d)              : ''}
            </div>
        </div>`;

        // Tab switching
        panel.querySelectorAll('.sm-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                this._memoryTab = btn.dataset.smTab;
                this._renderSystemMemory();
            });
        });

        // Accordion toggles (spec & changelog)
        panel.querySelectorAll('.sm-accordion-hdr').forEach(hdr => {
            hdr.addEventListener('click', () => {
                const item = hdr.closest('.sm-accordion-item');
                item.classList.toggle('open');
            });
        });

        // Finalize Daily Log modal
        const finalizeBtn = panel.querySelector('#sm-finalize-btn');
        if (finalizeBtn) finalizeBtn.addEventListener('click', () => this._smOpenFinalizeModal());
    },

    _smChangelogHTML(entries) {
        const rows = entries.map((e, i) => {
            const typeBadge = { feature:'sm-badge--feature', fix:'sm-badge--fix', change:'sm-badge--change' }[e.type] || '';
            const tags = e.tags.map(t => `<span class="sm-tag">${this._esc(t)}</span>`).join('');
            const addedHTML  = e.added.length  ? `<div class="sm-cl-group"><span class="sm-cl-label sm-cl-added">Added</span><ul>${e.added.map(x=>`<li>${this._esc(x)}</li>`).join('')}</ul></div>` : '';
            const changedHTML= e.changed.length ? `<div class="sm-cl-group"><span class="sm-cl-label sm-cl-changed">Changed</span><ul>${e.changed.map(x=>`<li>${this._esc(x)}</li>`).join('')}</ul></div>` : '';
            const fixedHTML  = e.fixed.length   ? `<div class="sm-cl-group"><span class="sm-cl-label sm-cl-fixed">Fixed</span><ul>${e.fixed.map(x=>`<li>${this._esc(x)}</li>`).join('')}</ul></div>` : '';
            const notesHTML  = e.notes          ? `<div class="sm-cl-group"><span class="sm-cl-label">Notes</span><p class="sm-cl-notes">${this._esc(e.notes)}</p></div>` : '';
            return `
            <div class="sm-timeline-item sm-accordion-item${i===0?' open':''}">
                <div class="sm-timeline-dot"></div>
                <div class="sm-accordion-hdr">
                    <div class="sm-cl-hdr-left">
                        <span class="sm-badge ${typeBadge}">${this._esc(e.type)}</span>
                        <span class="sm-cl-version">v${this._esc(e.version)}</span>
                        <span class="sm-cl-title">${this._esc(e.title)}</span>
                    </div>
                    <div class="sm-cl-hdr-right">
                        ${tags}
                        <span class="sm-cl-date">${this._esc(e.date)}</span>
                        <span class="sm-accordion-arrow">▼</span>
                    </div>
                </div>
                <div class="sm-accordion-body">
                    ${addedHTML}${changedHTML}${fixedHTML}${notesHTML}
                </div>
            </div>`;
        }).join('');
        return `<div class="sm-timeline">${rows}</div>`;
    },

    _smSpecHTML(sections) {
        const rows = sections.map((s, i) => {
            const subs = s.subsections.map(sub => `
                <div class="sm-spec-sub">
                    <div class="sm-spec-sub-title">${this._esc(sub.title)}</div>
                    <div class="sm-spec-sub-content">${this._esc(sub.content)}</div>
                </div>`).join('');
            return `
            <div class="sm-accordion-item${i===0?' open':''}">
                <div class="sm-accordion-hdr">
                    <span class="sm-spec-title">${this._esc(s.title)}</span>
                    <span class="sm-accordion-arrow">▼</span>
                </div>
                <div class="sm-accordion-body">
                    <p class="sm-spec-summary">${this._esc(s.summary)}</p>
                    ${subs}
                </div>
            </div>`;
        }).join('');
        return `<div class="sm-spec-list">${rows}</div>`;
    },

    _smStatusHTML(d) {
        const cells = Object.entries(d.status).map(([k, v]) => `
            <div class="sm-status-cell">
                <div class="sm-status-dot sm-status-dot--${this._esc(v)}"></div>
                <div class="sm-status-label">${this._esc(k)}</div>
                <div class="sm-status-val">${this._esc(v)}</div>
            </div>`).join('');
        return `
        <div class="sm-status-wrap">
            <div class="sm-status-title">System Health</div>
            <div class="sm-status-grid">${cells}</div>
            <div class="sm-status-info">
                <div class="sm-info-row"><span>System Version</span><strong>v${this._esc(d.version)}</strong></div>
                <div class="sm-info-row"><span>Spec Version</span><strong>${this._esc(d.specVersion)}</strong></div>
                <div class="sm-info-row"><span>Last Updated</span><strong>${this._esc(d.lastUpdate)}</strong></div>
                <div class="sm-info-row"><span>Dashboard Port</span><strong>5050</strong></div>
                <div class="sm-info-row"><span>Demo Studio</span><strong>aiden-demo-studio (Vercel)</strong></div>
                <div class="sm-info-row"><span>Discord Bot</span><strong>Running (discord_bot.py)</strong></div>
            </div>
        </div>`;
    },

    _smOpenFinalizeModal() {
        const today = new Date().toISOString().split('T')[0];
        const existing = document.getElementById('sm-modal-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.id = 'sm-modal-overlay';
        overlay.className = 'sm-modal-overlay';
        overlay.innerHTML = `
        <div class="sm-modal">
            <div class="sm-modal-hdr">
                <div class="sm-modal-title">Finalize Daily Log — ${this._esc(today)}</div>
                <button class="sm-modal-close" id="sm-modal-close">✕</button>
            </div>
            <div class="sm-modal-body">
                <p class="sm-modal-intro">Add today's changes before closing out. These will appear at the top of the changelog.</p>
                <div class="sm-modal-group">
                    <label>Added <span class="sm-modal-hint">(new features, pages, sections)</span></label>
                    <textarea id="sm-log-added" rows="3" placeholder="One item per line"></textarea>
                </div>
                <div class="sm-modal-group">
                    <label>Changed <span class="sm-modal-hint">(modifications to existing behavior)</span></label>
                    <textarea id="sm-log-changed" rows="2" placeholder="One item per line"></textarea>
                </div>
                <div class="sm-modal-group">
                    <label>Fixed <span class="sm-modal-hint">(bugs, broken behavior)</span></label>
                    <textarea id="sm-log-fixed" rows="2" placeholder="One item per line"></textarea>
                </div>
                <div class="sm-modal-group">
                    <label>Notes <span class="sm-modal-hint">(context, decisions, links)</span></label>
                    <textarea id="sm-log-notes" rows="2" placeholder="Optional"></textarea>
                </div>
            </div>
            <div class="sm-modal-footer">
                <button class="sm-modal-cancel" id="sm-modal-cancel">Cancel</button>
                <button class="sm-modal-submit" id="sm-modal-submit">Save to Changelog</button>
            </div>
        </div>`;
        document.body.appendChild(overlay);

        overlay.querySelector('#sm-modal-close').addEventListener('click', () => overlay.remove());
        overlay.querySelector('#sm-modal-cancel').addEventListener('click', () => overlay.remove());
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });

        overlay.querySelector('#sm-modal-submit').addEventListener('click', () => {
            const parse = id => overlay.querySelector(id).value.split('\n').map(s=>s.trim()).filter(Boolean);
            const added   = parse('#sm-log-added');
            const changed = parse('#sm-log-changed');
            const fixed   = parse('#sm-log-fixed');
            const notes   = (overlay.querySelector('#sm-log-notes').value||'').trim();

            if (!added.length && !changed.length && !fixed.length) {
                this._toast('Add at least one item before saving.');
                return;
            }

            const newEntry = {
                date: today,
                version: this._MEMORY_DATA.version,
                type: added.length ? 'feature' : (fixed.length ? 'fix' : 'change'),
                title: added[0] || changed[0] || fixed[0] || 'Daily log entry',
                tags: ['daily-log'],
                added, changed, fixed, notes,
            };
            this._MEMORY_DATA.changelog.unshift(newEntry);
            this._MEMORY_DATA.lastUpdate = today;
            overlay.remove();
            this._memoryTab = 'changelog';
            this._renderSystemMemory();
            this._toast('Daily log saved to changelog ✓');
        });
    },

    /* ── UTILITIES ──────────────────────────────────────────────────────── */
    _esc(str) {
        return String(str||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    },
    _capitalize(str) { return (str||'').replace(/\b\w/g, c=>c.toUpperCase()); },
    _formatDate(iso) {
        if (!iso) return '';
        const [y,m,d] = iso.split('-');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${months[parseInt(m,10)-1]} ${parseInt(d,10)}, ${y}`;
    },
    _formatDatetime(dt) {
        if (!dt) return '—';
        const [date, time] = dt.split('T');
        return `${this._formatDate(date)} ${(time||'').substring(0,5)}`;
    },
    _to24h(timeStr) {
        if (!timeStr) return '08:00';
        const m = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
        if (!m) return '08:00';
        let [,h,min,p] = m; h = parseInt(h,10);
        if (p.toUpperCase()==='PM' && h!==12) h += 12;
        if (p.toUpperCase()==='AM' && h===12) h = 0;
        return `${String(h).padStart(2,'0')}:${min}`;
    },
    _assetIcon(type) {
        return {video:'🎬',photo:'📷',graphic:'🖼️',carousel:'📑',concept:'💡'}[type] || '📄';
    },
    _toast(msg) {
        let el = document.getElementById('aiden-toast');
        if (!el) { el = document.createElement('div'); el.id='aiden-toast'; el.className='aiden-toast'; document.body.appendChild(el); }
        el.textContent = msg;
        el.classList.add('show');
        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
    },
};
