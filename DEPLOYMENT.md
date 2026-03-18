# BCAT Command Center — Replit Deployment Guide

**Production URL:** https://app.tryaiden.ai
**Platform:** Replit (Python 3.11, gunicorn)
**Auth:** Email + bcrypt password via environment variables

---

## Quick Start (new Replit project)

### Step 1 — Import the repo into Replit

1. Go to [replit.com](https://replit.com) → **Create Repl**
2. Choose **Import from GitHub** (or upload the folder as a zip)
3. Select **Python** as the language — Replit will detect `.replit` automatically

### Step 2 — Install dependencies

Open the Replit Shell and run:

```bash
pip install -r requirements.txt
```

### Step 3 — Set Secrets

In Replit: click the **Secrets** tab (lock icon, left sidebar) → add each variable below.

**Required secrets:**

| Key | Value |
|-----|-------|
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | `production` |
| `ADMIN_EMAIL` | Your login email, e.g. `admin@tryaiden.ai` |
| `ADMIN_PASSWORD_HASH` | Generate below |
| `APP_BASE_URL` | `https://app.tryaiden.ai` |
| `COOKIE_DOMAIN` | `tryaiden.ai` |

**Optional secrets** (only needed for specific features):

| Key | Feature |
|-----|---------|
| `ANTHROPIC_API_KEY` | AI content generation in Aiden tab |
| `DISCORD_BOT_TOKEN` | Discord bot |
| `GOOGLE_ADS_*` | Best Care Google Ads sync |
| `EIGHTX8_*` | Best Care call tracking |
| `DATAFORSEO_*` / `SERPAPI_KEY` | Competitor intelligence |

### Step 4 — Generate your password hash

In the Replit Shell:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_PASSWORD_HERE'))"
```

Copy the output (starts with `scrypt:` or `pbkdf2:`) and paste it as the value of `ADMIN_PASSWORD_HASH`.

### Step 5 — Generate your SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as `SECRET_KEY`.

### Step 6 — Run

Click the **Run** button. Replit executes:

```
gunicorn dashboard:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

The app will be live at your Replit URL (e.g. `https://your-repl-name.repl.co`).

---

## Connect app.tryaiden.ai (Custom Domain)

### Step 1 — Deploy on Replit

Use **Replit Deployments** (not just "Run") for a stable URL:

1. In your Repl → click **Deploy** (top right)
2. Choose **Reserved VM** or **Autoscale**
3. After deployment completes, Replit gives you a deployment URL like:
   `https://bcat-command-center.yourusername.repl.co`

### Step 2 — Add custom domain in Replit

1. In your Repl → **Deployments** tab → **Custom domains**
2. Click **Add domain**
3. Enter: `app.tryaiden.ai`
4. Replit shows you a CNAME target — copy it (e.g. `bcat-command-center.yourusername.repl.co`)

### Step 3 — Add DNS record in GoDaddy

1. Log in to GoDaddy → **My Domains** → `tryaiden.ai` → **DNS**
2. Click **Add New Record**:

   | Type | Name | Value | TTL |
   |------|------|-------|-----|
   | `CNAME` | `app` | `<value from Replit>` | 1 Hour |

3. Save. DNS propagates in 5–30 minutes (up to 48 hours max).

### Step 4 — Verify

Replit will automatically detect DNS propagation and provision an SSL certificate.

Once complete:
- `https://app.tryaiden.ai` → loads login page
- `https://app.tryaiden.ai/login` → explicit login URL

---

## How Authentication Works

1. Any request to `/` or `/api/*` without a valid session → redirected to `/login`
2. `POST /login` with email + password → verified against `ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH`
3. On success → session cookie set (`bcat_session`, 7-day lifetime, HttpOnly, Secure in production)
4. `POST /logout` → clears session → redirect to `/login`
5. All 40+ API routes return `401 JSON` for unauthenticated requests

**Login credentials:**
- Email: value of `ADMIN_EMAIL` secret
- Password: the plaintext password you hashed with `generate_password_hash()`

---

## Environment Variables Reference

```
# ── Required in production ────────────────────────────────────
SECRET_KEY=<64-char random hex>
FLASK_ENV=production
ADMIN_EMAIL=admin@tryaiden.ai
ADMIN_PASSWORD_HASH=scrypt:32768:8:1$...<full hash>
APP_BASE_URL=https://app.tryaiden.ai
COOKIE_DOMAIN=tryaiden.ai

# ── Optional ──────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...
DISCORD_BOT_TOKEN=...
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_LOGIN_CUSTOMER_ID=...
BEST_CARE_GOOGLE_ADS_CUSTOMER_ID=...
EIGHTX8_API_KEY=...
EIGHTX8_BASE_URL=https://api.8x8.com
EIGHTX8_ACCOUNT_ID=...
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...
SERPAPI_KEY=...
```

---

## Local Development

```bash
# From project root
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt

# Dev mode — HTTP, debug on, no SECRET_KEY required
FLASK_ENV=development python dashboard.py
# → http://127.0.0.1:5050
```

Local `.env` file (never committed):
```
ADMIN_EMAIL=admin@tryaiden.ai
ADMIN_PASSWORD_HASH=scrypt:32768:8:1$...
```

---

## Production vs Development Behaviour

| Setting | Local dev | Replit production |
|---------|-----------|------------------|
| `FLASK_ENV` | `development` | `production` |
| Debug mode | On | Off |
| Server | Flask dev server | gunicorn |
| Cookie `Secure` flag | Off (HTTP ok) | On (HTTPS only) |
| `SECRET_KEY` missing | Uses insecure fallback | Raises `RuntimeError` at startup |

---

## Verify Deployment Checklist

- [ ] `https://app.tryaiden.ai` → redirects to login page (not 404, not app content)
- [ ] `https://app.tryaiden.ai/api/dashboard` → returns `{"error": "Unauthorized"}` (not finance data)
- [ ] Login with correct credentials → redirects to dashboard
- [ ] Login with wrong credentials → shows error on login page (no crash)
- [ ] Dashboard loads all company tabs (BCAT, Ivan Cartage, Best Care, Aiden, Agents)
- [ ] Logout button returns to login page
- [ ] Session persists after page refresh
- [ ] HTTPS certificate valid (green padlock)

---

## Project Structure (relevant files)

```
MultiAgent_Operations/
├── dashboard.py          ← Flask app — all routes, auth-protected
├── config.py             ← Environment-aware config (reads .env / Replit Secrets)
├── auth.py               ← login_required decorator + verify_credentials()
├── requirements.txt      ← Python dependencies (includes gunicorn)
├── Procfile              ← gunicorn start command (Heroku-compatible)
├── .replit               ← Replit run/deploy config
├── .env                  ← Local secrets (never commit)
├── .env.example          ← Template — copy to .env and fill in
├── DEPLOYMENT.md         ← This file
├── templates/
│   ├── login.html        ← Login page (dark-themed, branded)
│   └── dashboard.html    ← Main app shell
└── static/
    ├── dashboard.js/css  ← Finance dashboard
    ├── marketing.js/css  ← Marketing module
    ├── sales.js/css      ← Sales module
    └── aiden.js/css      ← Aiden content + system memory
```

---

## Troubleshooting

**App crashes immediately on Replit:**
- Check that `SECRET_KEY` is set in Secrets. The app raises `RuntimeError` if missing in production.

**Login page shows "Invalid email or password":**
- Verify `ADMIN_EMAIL` matches exactly what you're typing
- Regenerate `ADMIN_PASSWORD_HASH` — make sure you copied the full hash (no truncation)

**Session lost after each request:**
- `SECRET_KEY` is probably different between restarts. Set it as a fixed Replit Secret, not generated at runtime.

**Cookies not working on custom domain:**
- Set `COOKIE_DOMAIN=tryaiden.ai` (root domain, no `app.` prefix)

**HTTPS / Secure cookie errors locally:**
- Leave `FLASK_ENV` unset or set to `development` for local dev — this disables the Secure cookie flag.
