/**
 * app.ts — Express application setup
 *
 * Env vars (set in Replit Secrets):
 *   SECRET_KEY          — session secret (required)
 *   ADMIN_EMAIL         — login email (required)
 *   ADMIN_PASSWORD_HASH — bcrypt hash of login password (required)
 *   NODE_ENV            — "production" | "development"
 *   COOKIE_DOMAIN       — e.g. "tryaiden.ai" (optional)
 *   CORS_ORIGIN         — allowed origin for CORS, e.g. "https://app.tryaiden.ai" (optional)
 *   CSV_DATA_DIR        — absolute path to project root (contains CSVs, templates/, static/)
 *   PORT                — injected by Replit automatically
 */

import path from "path";
import express from "express";
import cookieParser from "cookie-parser";
import cors from "cors";
import session from "express-session";

import pagesRouter from "./routes/pages";
import authRouter from "./routes/auth";
import dashboardRouter from "./routes/dashboard";
import healthRouter from "./routes/health";
import agentsRouter from "./routes/agents";

// ── Type augmentation so TypeScript knows about session fields ────────────────
declare module "express-session" {
  interface SessionData {
    authenticated: boolean;
    userEmail: string;
  }
}

function rootDir(): string {
  return process.env.CSV_DATA_DIR ?? process.cwd();
}

const app = express();

// ── CORS ──────────────────────────────────────────────────────────────────────
const allowedOrigin = process.env.CORS_ORIGIN ?? "*";
app.use(
  cors({
    origin: allowedOrigin,
    credentials: true,
  })
);

// ── Static files — serve /static/* from project root's static/ folder ─────────
app.use("/static", express.static(path.join(rootDir(), "static")));

// ── Body + cookie parsing ─────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// ── Session ───────────────────────────────────────────────────────────────────
const secretKey = process.env.SECRET_KEY;
if (!secretKey) {
  console.error("[bcat-api] FATAL: SECRET_KEY env var is not set");
  process.exit(1);
}

app.use(
  session({
    secret: secretKey,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      domain: process.env.COOKIE_DOMAIN ?? undefined,
      maxAge: 8 * 60 * 60 * 1000, // 8 hours
    },
  })
);

// ── Public API routes ─────────────────────────────────────────────────────────
app.use("/api", healthRouter);   // GET /api/health
app.use("/api", authRouter);     // POST /api/login, POST /api/logout, GET /api/me

// ── Protected API routes ──────────────────────────────────────────────────────
app.use("/api", dashboardRouter); // GET /api/dashboard
app.use("/api", agentsRouter);    // GET /api/agents

// ── HTML page routes (/, /login, POST /login, POST /logout) ──────────────────
// Must come AFTER /api routes so API paths are not intercepted.
app.use("/", pagesRouter);

// ── 404 catch-all ─────────────────────────────────────────────────────────────
app.use((_req, res) => {
  res.status(404).json({ error: "Not found" });
});

export default app;
