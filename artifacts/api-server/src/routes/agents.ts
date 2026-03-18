/**
 * agents.ts — GET /api/agents (protected)
 *
 * Returns the agent registry. Reads agent_registry.json from the project root
 * (same directory as the CSV files — set via CSV_DATA_DIR or process.cwd()).
 *
 * Falls back to a static list if the file is missing.
 */

import { Router, Request, Response } from "express";
import fs from "fs";
import path from "path";

const router = Router();

function requireAuth(req: Request, res: Response): boolean {
  if (!req.session?.authenticated) {
    res.status(401).json({ error: "Unauthorized" });
    return false;
  }
  return true;
}

function dataDir(): string {
  return process.env.CSV_DATA_DIR ?? process.cwd();
}

const FALLBACK_AGENTS = [
  { name: "FinanceAgent", description: "CSV-driven financial metrics (brokerage, Ivan Cartage)", status: "idle" },
  { name: "CoordinatorAgent", description: "Message routing and agent orchestration", status: "idle" },
  { name: "Dashboard", description: "BCAT Command Center API", status: "idle" },
];

router.get("/agents", (req: Request, res: Response) => {
  if (!requireAuth(req, res)) return;

  const registryPath = path.join(dataDir(), "agent_registry.json");

  if (fs.existsSync(registryPath)) {
    try {
      const raw = fs.readFileSync(registryPath, "utf-8");
      const registry = JSON.parse(raw);
      // Convert object-of-agents to array if needed
      if (Array.isArray(registry)) {
        res.json(registry);
      } else if (registry && typeof registry === "object") {
        const agents = Object.entries(registry).map(([name, info]: [string, any]) => ({
          name,
          description: info?.description ?? "",
          status: info?.status ?? "idle",
          last_task: info?.last_task ?? "",
          updated_at: info?.updated_at ?? "",
        }));
        res.json(agents);
      } else {
        res.json(FALLBACK_AGENTS);
      }
      return;
    } catch {
      // JSON parse error — fall through to fallback
    }
  }

  res.json(FALLBACK_AGENTS);
});

export default router;
