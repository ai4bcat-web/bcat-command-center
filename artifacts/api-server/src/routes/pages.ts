/**
 * pages.ts — HTML page routes
 *
 * GET  /          → dashboard (redirect to /login if not authenticated)
 * GET  /login     → login page
 * POST /login     → authenticate, redirect to / on success or /login?error=... on failure
 * POST /logout    → destroy session, redirect to /login
 *
 * Static assets (/static/*) are served by Express static middleware in app.ts.
 */

import { Router, Request, Response } from "express";
import path from "path";
import fs from "fs";
import bcrypt from "bcryptjs";

const router = Router();

function rootDir(): string {
  return process.env.CSV_DATA_DIR ?? process.cwd();
}

function sendHtml(res: Response, filename: string): void {
  const filePath = path.join(rootDir(), "templates", filename);
  if (!fs.existsSync(filePath)) {
    res.status(404).send(`Template not found: ${filename}`);
    return;
  }
  res.sendFile(filePath);
}

// ── GET / — dashboard (protected) ────────────────────────────────────────────
router.get("/", (req: Request, res: Response) => {
  if (!req.session?.authenticated) {
    res.redirect("/login");
    return;
  }
  sendHtml(res, "dashboard.html");
});

// ── GET /login ────────────────────────────────────────────────────────────────
router.get("/login", (req: Request, res: Response) => {
  if (req.session?.authenticated) {
    res.redirect("/");
    return;
  }
  sendHtml(res, "login.html");
});

// ── POST /login — HTML form submission ────────────────────────────────────────
router.post("/login", async (req: Request, res: Response) => {
  const { email, password, next } = req.body as {
    email?: string;
    password?: string;
    next?: string;
  };

  const safeNext = (next ?? "").startsWith("/") ? next! : "/";

  if (!email || !password) {
    res.redirect(
      `/login?error=missing_fields&email=${encodeURIComponent(email ?? "")}&next=${encodeURIComponent(safeNext)}`
    );
    return;
  }

  const adminEmail = process.env.ADMIN_EMAIL ?? "";
  const adminHash = process.env.ADMIN_PASSWORD_HASH ?? "";

  if (!adminEmail || !adminHash) {
    console.error("[pages] ADMIN_EMAIL or ADMIN_PASSWORD_HASH not set");
    res.redirect(`/login?error=server_error`);
    return;
  }

  const emailMatch =
    email.trim().toLowerCase() === adminEmail.trim().toLowerCase();

  let passwordMatch = false;
  try {
    passwordMatch = await bcrypt.compare(password, adminHash);
  } catch {
    passwordMatch = password === adminHash; // plain-text fallback (dev only)
  }

  if (!emailMatch || !passwordMatch) {
    res.redirect(
      `/login?error=invalid_credentials&email=${encodeURIComponent(email.trim())}&next=${encodeURIComponent(safeNext)}`
    );
    return;
  }

  req.session.authenticated = true;
  req.session.userEmail = email.trim().toLowerCase();
  res.redirect(safeNext);
});

// ── POST /logout ──────────────────────────────────────────────────────────────
router.post("/logout", (req: Request, res: Response) => {
  req.session.destroy(() => {
    res.redirect("/login");
  });
});

export default router;
