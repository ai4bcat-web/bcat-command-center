/**
 * bestcare.ts — stub routes for /api/best-care/*
 *
 * Returns empty-but-valid JSON so the Best Care tab does not crash.
 * Replace with real implementations when the Best Care service is ported.
 */

import { Router, Request, Response } from "express";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) { res.status(401).json({ error: "Unauthorized" }); return false; }
  return true;
}

const UNAVAILABLE = { available: false, message: "Best Care service not configured on this deployment." };

router.get("/best-care/sync-status", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.status(503).json(UNAVAILABLE);
});

router.get("/best-care/dashboard", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ ...UNAVAILABLE, data: null });
});

router.get("/best-care/monthly-performance", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ months: [], ...UNAVAILABLE });
});

router.get("/best-care/google-ads/monthly", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ months: [], ...UNAVAILABLE });
});

router.get("/best-care/google-ads/campaigns", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ campaigns: [], ...UNAVAILABLE });
});

router.get("/best-care/google-ads/keywords", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ keywords: [], ...UNAVAILABLE });
});

router.get("/best-care/google-ads/search-terms", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ search_terms: [], ...UNAVAILABLE });
});

router.get("/best-care/calls/monthly", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ months: [], ...UNAVAILABLE });
});

router.get("/best-care/competitors", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ competitors: [], themes: [], offers: [], ...UNAVAILABLE });
});

router.get("/best-care/recommendations", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ recommendations: [], ...UNAVAILABLE });
});

router.get("/best-care/implementation-queue", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ queue: [], ...UNAVAILABLE });
});

router.get("/best-care/assumptions", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ assumptions: {}, ...UNAVAILABLE });
});

// POST stubs
["sync/google-ads", "sync/calls", "sync/competitors", "sync/all",
 "recommendations/generate", "recommendations/:recId/implement",
 "assumptions"].forEach(suffix => {
  router.post(`/best-care/${suffix}`, (req, res) => {
    if (!requireAuth(req, res)) return;
    res.json({ ...UNAVAILABLE });
  });
});

export default router;
