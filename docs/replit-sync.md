# GitHub ↔ Replit Sync Workflow

## Current Reality (Read This First)

The GitHub repo currently contains **Python/Flask** code from the original local version.
The live Replit app runs **Node.js/Express + React** — a different codebase built separately.

**These must be unified before any sync workflow works.**

---

## Step 0 — One-Time Setup: Push Replit Code to GitHub

Do this once to make GitHub the source of truth for the live app.

### In Replit Shell:

```bash
# 1. Initialize git if not already done
git init

# 2. Connect to your GitHub repo
git remote add origin https://github.com/ai4bcat-web/bcat-command-center.git

# 3. Check what branch you're on
git branch

# 4. Stage all current Replit files
git add .

# 5. Commit
git commit -m "chore: push Replit Node.js app to GitHub as source of truth"

# 6. Push — this REPLACES the current GitHub contents with the Replit codebase
#    Use --force only for this one-time unification
git push --force origin main
```

> ⚠️ After this push, GitHub contains the Node.js/Express app.
> The old Python/Flask code will be overwritten.
> This is intentional — Replit is the live app, so Replit's code becomes canonical.

---

## Recommended Workflow (Day-to-Day)

```
Claude Code (local) → edits files → git commit + push to GitHub → Replit pulls → redeploy
```

### Step-by-step:

**1. Claude Code makes changes locally**
- Claude edits files in the local repo clone
- Changes are committed and pushed to GitHub:
  ```bash
  git add .
  git commit -m "your message"
  git push origin main
  ```

**2. Replit pulls from GitHub**
- Open Replit Shell and run:
  ```bash
  git pull origin main
  ```

**3. Rebuild if needed**
- If TypeScript/frontend files changed:
  ```bash
  cd artifacts/api-server && npm run build
  cd ../bcat-command-center && npm run build
  ```

**4. Redeploy**
- Click **Deploy** → **Redeploy** in Replit UI
- Or use the Replit Shell deploy command if available

---

## Does True Auto-Sync Exist?

**Yes — Replit supports GitHub auto-sync** via its built-in Git integration.

To enable it:
1. In Replit: click the **Git** tab (branch icon in left sidebar)
2. Connect to `ai4bcat-web/bcat-command-center`
3. Enable **"Pull on deploy"** if available in your plan

Once connected, every `git push` from Claude Code can trigger Replit to pull automatically.

> If auto-sync is not available on your Replit plan, the manual `git pull` in Shell is the fallback (takes ~10 seconds).

---

## What Lives Where

| Thing | Where it lives |
|-------|---------------|
| App source code | GitHub repo (source of truth) |
| Secrets / env vars | Replit Secrets tab only — never in repo |
| CSV data files | Replit filesystem (uploaded via Discord bot) |
| Compiled build | Replit only (`artifacts/api-server/dist/`) |
| Domain config | Replit Deployments settings |

---

## What NOT to Edit Directly in Replit

Avoid editing source files directly in Replit's editor. If you do:
- Those changes will be **overwritten** on the next `git pull`
- Secrets are the only exception — always set those in Replit Secrets, not code

**Rule:** Edit in Claude Code → push to GitHub → pull in Replit.

---

## Required Replit Secrets

Set these in Replit → Secrets tab (never in the repo):

| Secret | Required | Description |
|--------|----------|-------------|
| `SECRET_KEY` | ✅ | Session secret — generate with `openssl rand -hex 32` |
| `ADMIN_EMAIL` | ✅ | Login email |
| `ADMIN_PASSWORD_HASH` | ✅ | Hashed password |
| `NODE_ENV` | ✅ | Set to `production` |
| `DISCORD_BOT_TOKEN` | optional | Enables Discord finance bot |
| `TELEGRAM_BOT_TOKEN` | optional | Enables Telegram integration |
| `ANTHROPIC_API_KEY` | optional | Enables AI content features |
| `APP_BASE_URL` | optional | e.g. `https://app.tryaiden.ai` |
| `COOKIE_DOMAIN` | optional | e.g. `tryaiden.ai` |

---

## Quick Reference Commands

```bash
# Pull latest from GitHub (run in Replit Shell)
git pull origin main

# Rebuild API server after code changes
cd artifacts/api-server && npm run build

# Rebuild frontend after UI changes
cd artifacts/bcat-command-center && npm run build

# Check health after deploy
curl https://app.tryaiden.ai/api/health

# Verify env vars are set (run in Replit Shell)
node -e "['SECRET_KEY','ADMIN_EMAIL','ADMIN_PASSWORD_HASH','NODE_ENV'].forEach(k => console.log(k, process.env[k] ? '✅' : '❌ MISSING'))"
```
