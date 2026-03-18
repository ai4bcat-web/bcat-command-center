/**
 * dashboard.ts — Express route for /api/dashboard
 * Returns the same JSON shape as the Flask /api/dashboard endpoint.
 *
 * Mount this in app.ts BEFORE the catch-all auth middleware:
 *
 *   import dashboardRouter from "./routes/dashboard";
 *   app.use("/api", dashboardRouter);
 *
 * The route is /api/dashboard (GET). It is protected by session auth —
 * returns 401 if req.session.authenticated is not true.
 */

import { Router, Request, Response } from "express";
import { getDashboardData } from "../lib/financeMetrics";

const router = Router();

router.get("/dashboard", (req: Request, res: Response) => {
  // Session auth guard — adjust field name to match your session setup
  if (!(req.session as any)?.authenticated) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  try {
    const data = getDashboardData();
    res.json(data);
  } catch (err: any) {
    console.error("[dashboard] Error computing metrics:", err);
    res.status(500).json({ error: "Failed to load dashboard data", detail: err?.message ?? String(err) });
  }
});

export default router;
