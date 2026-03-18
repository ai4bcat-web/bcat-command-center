/**
 * health.ts — GET /api/health (public — no auth required)
 *
 * Checks:
 *   - required env vars
 *   - CSV file presence
 *   - Discord / Telegram bot config
 *   - data layer (can we read brokerage totals?)
 */

import { Router, Request, Response } from "express";
import fs from "fs";
import path from "path";

const router = Router();

const REQUIRED_ENV = ["SECRET_KEY", "ADMIN_EMAIL", "ADMIN_PASSWORD_HASH", "NODE_ENV"];
const OPTIONAL_ENV = ["DISCORD_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "COOKIE_DOMAIN", "CORS_ORIGIN", "CSV_DATA_DIR"];

const CSV_FILES = ["brokerage_loads.csv", "ivan_cartage_loads.csv", "ivan_expenses.csv"];

function csvDir(): string {
  return process.env.CSV_DATA_DIR ?? process.cwd();
}

router.get("/health", (_req: Request, res: Response) => {
  // Env var checks
  const envStatus: Record<string, boolean> = {};
  let envOk = true;
  for (const key of REQUIRED_ENV) {
    const present = Boolean(process.env[key]?.trim());
    envStatus[key] = present;
    if (!present) envOk = false;
  }
  const optionalEnvStatus: Record<string, boolean> = {};
  for (const key of OPTIONAL_ENV) {
    optionalEnvStatus[key] = Boolean(process.env[key]?.trim());
  }

  // CSV file checks
  const csvStatus: Record<string, boolean> = {};
  let csvOk = true;
  for (const file of CSV_FILES) {
    const exists = fs.existsSync(path.join(csvDir(), file));
    csvStatus[file] = exists;
    if (!exists) csvOk = false;
  }

  // Data layer sanity check
  let dataLayerOk = false;
  let dataLayerDetail = "";
  try {
    // Lazy-import so health check doesn't crash if metrics module has issues
    const { getDashboardData } = require("../lib/financeMetrics") as typeof import("../lib/financeMetrics");
    const data = getDashboardData();
    dataLayerOk = true;
    dataLayerDetail = `total_company_revenue=$${data.total_company_revenue.toLocaleString()}`;
  } catch (err: any) {
    dataLayerDetail = String(err?.message ?? err);
  }

  const allOk = envOk && csvOk && dataLayerOk;

  res.status(allOk ? 200 : 503).json({
    status: allOk ? "ok" : "degraded",
    timestamp: new Date().toISOString(),
    checks: {
      env: {
        ok: envOk,
        required: envStatus,
        optional: optionalEnvStatus,
      },
      csv: {
        ok: csvOk,
        dir: csvDir(),
        files: csvStatus,
      },
      discord: {
        configured: Boolean(process.env.DISCORD_BOT_TOKEN?.trim()),
      },
      telegram: {
        configured: Boolean(process.env.TELEGRAM_BOT_TOKEN?.trim()),
      },
      data_layer: {
        ok: dataLayerOk,
        detail: dataLayerDetail,
      },
    },
  });
});

export default router;
