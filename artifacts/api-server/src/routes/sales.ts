/**
 * sales.ts — stub routes for /api/sales/*
 *
 * Returns empty-but-valid JSON so sales.js does not crash.
 * Replace with real implementations when sales service is ported.
 */

import { Router, Request, Response } from "express";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) { res.status(401).json({ error: "Unauthorized" }); return false; }
  return true;
}

const UNAVAILABLE = { available: false, message: "Sales service not configured on this deployment." };

router.get("/sales/workspaces", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json([]);
});

router.get("/sales/:workspaceId/overview", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ workspace_id: req.params.workspaceId, ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/sync-status", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ workspace_id: req.params.workspaceId, synced: false, ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/leads", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ leads: [], total: 0, ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/lead-lists", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ lists: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/leads/scraped", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ leads: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/email/campaigns", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ campaigns: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/linkedin/campaigns", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ campaigns: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/daily", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ results: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/meetings", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ meetings: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/meetings/upcoming", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ meetings: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/messaging/templates", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ templates: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/recommendations", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ recommendations: [], ...UNAVAILABLE });
});

router.get("/sales/:workspaceId/activity", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ activity: [], ...UNAVAILABLE });
});

// POST stubs
["sync/instantly", "sync/calendar", "sync/all",
 "leads/scrape-maps", "leads/scrape-linkedin", "leads/enrich",
 "leads/sync-apollo", "email/enroll", "messaging/generate",
 "messaging/bulk-generate", "recommendations/:recId/implement",
 "recommendations/:recId/dismiss"].forEach(suffix => {
  router.post(`/sales/:workspaceId/${suffix}`, (req, res) => {
    if (!requireAuth(req, res)) return;
    res.json({ ...UNAVAILABLE });
  });
});

export default router;
