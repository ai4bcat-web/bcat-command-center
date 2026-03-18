/**
 * aiden.ts — /api/aiden/* routes
 *
 * Mirrors the Flask aiden routes using the Anthropic API directly.
 * Requires ANTHROPIC_API_KEY in Replit Secrets.
 *
 * POST /api/aiden/optimize-post    { content, content_type, tone }
 * POST /api/aiden/generate-post    { topic, tone, category }
 * POST /api/aiden/generate-hooks   { topic, style_mode, category }
 */

import { Router, Request, Response } from "express";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) { res.status(401).json({ error: "Unauthorized" }); return false; }
  return true;
}

async function callAnthropic(prompt: string): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set");

  const body = {
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    messages: [{ role: "user", content: prompt }],
  };

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Anthropic API error ${res.status}: ${text}`);
  }

  const data = await res.json() as any;
  return data.content?.[0]?.text ?? "";
}

// ── POST /api/aiden/optimize-post ─────────────────────────────────────────────
router.post("/aiden/optimize-post", async (req: Request, res: Response) => {
  if (!requireAuth(req, res)) return;

  const { content, content_type = "linkedin", tone = "professional" } = req.body as {
    content?: string; content_type?: string; tone?: string;
  };

  if (!content) { res.status(400).json({ error: "content is required" }); return; }

  try {
    const prompt = `You are an expert ${content_type} content optimizer for BCAT Corp, a freight brokerage and trucking company.

Optimize the following post for maximum engagement. Keep the core message intact.
Tone: ${tone}
Content type: ${content_type}

Original post:
${content}

Return ONLY the optimized post text, no commentary or labels.`;

    const optimized = await callAnthropic(prompt);
    res.json({ original: content, optimized, content_type, tone });
  } catch (err: any) {
    console.error("[aiden/optimize-post]", err);
    res.status(500).json({ error: err?.message ?? "Failed to optimize post" });
  }
});

// ── POST /api/aiden/generate-post ─────────────────────────────────────────────
router.post("/aiden/generate-post", async (req: Request, res: Response) => {
  if (!requireAuth(req, res)) return;

  const { topic, tone = "professional", category = "industry" } = req.body as {
    topic?: string; tone?: string; category?: string;
  };

  if (!topic) { res.status(400).json({ error: "topic is required" }); return; }

  try {
    const prompt = `You are an expert ${category} content writer for BCAT Corp, a freight brokerage and trucking company.

Write a compelling LinkedIn post about: ${topic}
Tone: ${tone}
Category: ${category}

The post should:
- Open with a strong hook
- Share a genuine insight or story related to freight/logistics
- End with an engaging question or call to action
- Be 150-250 words
- Feel authentic, not corporate

Return ONLY the post text, no labels or commentary.`;

    const post = await callAnthropic(prompt);
    res.json({ topic, post, tone, category });
  } catch (err: any) {
    console.error("[aiden/generate-post]", err);
    res.status(500).json({ error: err?.message ?? "Failed to generate post" });
  }
});

// ── POST /api/aiden/generate-hooks ───────────────────────────────────────────
router.post("/aiden/generate-hooks", async (req: Request, res: Response) => {
  if (!requireAuth(req, res)) return;

  const { topic, style_mode = "contrarian", category = "industry" } = req.body as {
    topic?: string; style_mode?: string; category?: string;
  };

  if (!topic) { res.status(400).json({ error: "topic is required" }); return; }

  try {
    const prompt = `You are an expert LinkedIn hook writer for BCAT Corp, a freight brokerage and trucking company.

Generate 5 compelling opening hooks for a post about: ${topic}
Style: ${style_mode}
Category: ${category}

Hook styles to use:
- contrarian: "The advice everyone gives about {topic}? It's wrong."
- painful truth: "Nobody tells you {topic} gets harder before it gets easier."
- curiosity gap: "There's one pattern in {topic} most people never see."
- proof/authority: Build credibility with a specific result
- myth vs reality: Challenge a common misconception

Return exactly 5 hooks, one per line, numbered 1-5. No other commentary.`;

    const raw = await callAnthropic(prompt);
    const hooks = raw.split("\n")
      .map(l => l.replace(/^\d+\.\s*/, "").trim())
      .filter(l => l.length > 0)
      .slice(0, 5);
    res.json({ topic, style_mode, category, hooks });
  } catch (err: any) {
    console.error("[aiden/generate-hooks]", err);
    res.status(500).json({ error: err?.message ?? "Failed to generate hooks" });
  }
});

export default router;
