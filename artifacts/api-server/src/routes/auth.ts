/**
 * auth.ts — Login and logout routes
 *
 * POST /api/login   { email, password } → sets session, returns { ok: true }
 * POST /api/logout  → clears session, returns { ok: true }
 * GET  /api/me      → returns { email } if authenticated, 401 otherwise
 *
 * Password hash: generate with bcryptjs, store in ADMIN_PASSWORD_HASH secret.
 *
 * One-liner to generate a new hash (run in Replit Shell):
 *   node -e "require('bcryptjs').hash('yourpassword', 10).then(h => console.log(h))"
 */

import { Router, Request, Response } from "express";
import bcrypt from "bcryptjs";

const router = Router();

function getCredentials() {
  return {
    email: process.env.ADMIN_EMAIL ?? "",
    hash: process.env.ADMIN_PASSWORD_HASH ?? "",
  };
}

router.post("/login", async (req: Request, res: Response) => {
  const { email, password } = req.body as { email?: string; password?: string };

  if (!email || !password) {
    res.status(400).json({ error: "Email and password are required" });
    return;
  }

  const creds = getCredentials();

  if (!creds.email || !creds.hash) {
    console.error("[auth] ADMIN_EMAIL or ADMIN_PASSWORD_HASH not set");
    res.status(500).json({ error: "Server auth configuration missing" });
    return;
  }

  const emailMatch = email.trim().toLowerCase() === creds.email.trim().toLowerCase();

  let passwordMatch = false;
  try {
    // Try bcrypt first (new Node-compatible hash format)
    passwordMatch = await bcrypt.compare(password, creds.hash);
  } catch {
    // Fall back to plain equality (dev convenience only — never use in prod)
    passwordMatch = password === creds.hash;
  }

  if (!emailMatch || !passwordMatch) {
    res.status(401).json({ error: "Invalid email or password" });
    return;
  }

  req.session.authenticated = true;
  req.session.userEmail = email.trim().toLowerCase();

  res.json({ ok: true, email: req.session.userEmail });
});

router.post("/logout", (req: Request, res: Response) => {
  req.session.destroy(() => {
    res.json({ ok: true });
  });
});

router.get("/me", (req: Request, res: Response) => {
  if (!req.session.authenticated) {
    res.status(401).json({ error: "Not authenticated" });
    return;
  }
  res.json({ email: req.session.userEmail });
});

export default router;
