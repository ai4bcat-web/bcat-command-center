/**
 * dashboard.ts — GET /api/dashboard (protected)
 *
 * Returns the same JSON shape as the original Flask /api/dashboard endpoint.
 * All data is computed live from CSV files on every request (no caching).
 *
 * Shape:
 * {
 *   report_start_date: string,        // "YYYY-MM"
 *   report_end_date: string,          // "YYYY-MM"
 *   total_company_revenue: number,
 *   brokerage: {
 *     gross_revenue, carrier_pay, gross_profit, brokerage_margin,
 *     monthly_brokerage_summary: [...],
 *     brokerage_top_customers_by_month: [...]
 *   },
 *   ivan: {
 *     ivan_cartage_revenue, ivan_expenses, ivan_true_profit,
 *     ivan_total_miles, ivan_revenue_per_mile, ivan_cost_per_mile, ivan_profit_per_mile,
 *     ivan_monthly_true_profit: [...],
 *     ivan_expenses_category_monthly: [...],
 *     ivan_top_customers_by_month: [...]
 *   }
 * }
 */

import { Router, Request, Response } from "express";
import { getDashboardData } from "../lib/financeMetrics";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) {
    res.status(401).json({ error: "Unauthorized" });
    return false;
  }
  return true;
}

router.get("/dashboard", (req: Request, res: Response) => {
  if (!requireAuth(req, res)) return;

  try {
    const data = getDashboardData();
    res.json(data);
  } catch (err: any) {
    console.error("[dashboard] Failed to compute metrics:", err);
    res.status(500).json({
      error: "Failed to load dashboard data",
      detail: err?.message ?? String(err),
    });
  }
});

export default router;
