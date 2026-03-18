/**
 * marketing.ts — stub routes for /api/marketing/*
 *
 * Mirrors the Flask marketing routes so marketing.js does not crash when
 * the tab is opened. Returns empty-but-valid JSON structures.
 * Replace with real implementations when marketing service is ported.
 */

import { Router, Request, Response } from "express";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) { res.status(401).json({ error: "Unauthorized" }); return false; }
  return true;
}

const UNAVAILABLE = { available: false, message: "Marketing service not configured on this deployment." };

// GET /api/marketing/status
router.get("/marketing/status", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ status: "unavailable", agents: [] });
});

// GET /api/marketing/groups
router.get("/marketing/groups", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json([]);
});

// GET /api/marketing/:groupId/overview
router.get("/marketing/:groupId/overview", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, overview: null, competitors: [], ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/seo
router.get("/marketing/:groupId/seo", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, seo: null, ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/google-ads
router.get("/marketing/:groupId/google-ads", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, google_ads: null, ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/facebook-ads
router.get("/marketing/:groupId/facebook-ads", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, facebook_ads: null, ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/competitors
router.get("/marketing/:groupId/competitors", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, competitors: [], ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/knowledge-graph
router.get("/marketing/:groupId/knowledge-graph", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, knowledge_graph: null, ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/recommendations
router.get("/marketing/:groupId/recommendations", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, recommendations: [], ...UNAVAILABLE });
});

// GET /api/marketing/:groupId/implementation-history
router.get("/marketing/:groupId/implementation-history", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ group_id: req.params.groupId, history: [], ...UNAVAILABLE });
});

// POST stubs
router.post("/marketing/:groupId/analyze/:channel", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ ...UNAVAILABLE, group_id: req.params.groupId, channel: req.params.channel });
});

router.post("/marketing/:groupId/implement/:recId", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ ...UNAVAILABLE });
});

router.post("/marketing/:groupId/generate-plan/:channel", (req, res) => {
  if (!requireAuth(req, res)) return;
  res.json({ ...UNAVAILABLE });
});

export default router;
