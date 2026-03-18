# BCAT Command Center — Deployment Guide

**Production URL:** https://app.tryaiden.ai
**Platform:** Replit (Python 3.11, gunicorn)
**Source of truth:** GitHub → `ai4bcat-web/bcat-command-center`

---

## Architecture

```
GitHub (code)  →  Replit (runtime)
                      ├── gunicorn  → Flask dashboard  (app.tryaiden.ai)
                      ├── thread    → Discord finance bot
                      └── thread    → Telegram bot
```

The Discord and Telegram bots start automatically as background daemon threads
when the dashboard starts. No separate processes or PM2 needed.

---

## Quick Start (Replit)

### 1 — Connect GitHub repo

In Replit Shell:
```bash
git remote add origin https://github.com/ai4bcat-web/bcat-command-center.git
git pull origin main
```

### 2 — Set Secrets

In Replit: click the **Secrets** tab (lock icon) → add each variable below.

#### Required
| Secret | Description |
|--------|-------------|
| `SECRET_KEY` | Random 64-char hex. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | `production` |
| `ADMIN_EMAIL` | Login email (e.g. `ryne@bcatcorp.com`) |
| `ADMIN_PASSWORD_HASH` | Generate: `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpass'))"` |
| `APP_BASE_URL` | `https://app.tryaiden.ai` |
| `COOKIE_DOMAIN` | `tryaiden.ai` |

#### Discord (optional — enables CSV upload via Discord)
| Secret | Description |
|--------|-------------|
| `DISCORD_BOT_TOKEN` | From Discord Developer Portal → Bot tab |

#### Telegram (optional — enables Telegram message routing)
| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | From @BotFather on Telegram |
| `TELEGRAM_ALLOWED_CHAT_ID` | Your Telegram user/chat ID (restricts who can message the bot). Get it from @userinfobot |

#### AI / Integrations (optional)
| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Enables AI content generation in Aiden tab |
| `DISCORD_BOT_TOKEN` | Discord finance file upload bot |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Best Care Google Ads sync |
| `GOOGLE_ADS_CLIENT_ID` | Best Care Google Ads sync |
| `GOOGLE_ADS_CLIENT_SECRET` | Best Care Google Ads sync |
| `GOOGLE_ADS_REFRESH_TOKEN` | Best Care Google Ads sync |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Best Care Google Ads sync |
| `BEST_CARE_GOOGLE_ADS_CUSTOMER_ID` | Best Care Google Ads sync |
| `EIGHTX8_API_KEY` | Best Care call tracking |
| `EIGHTX8_BASE_URL` | e.g. `https://api.8x8.com` |
| `EIGHTX8_ACCOUNT_ID` | Best Care call tracking |
| `DATAFORSEO_LOGIN` | Competitor intelligence |
| `DATAFORSEO_PASSWORD` | Competitor intelligence |
| `SERPAPI_KEY` | Competitor intelligence (alternative) |

### 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### 4 — Deploy
Click **Deploy** in Replit, or just **Run** for testing.

---

## Discord Setup

The Discord bot watches the **#finance** channel for CSV file uploads.

### In Discord Developer Portal (discord.com/developers/applications)
1. Select your app → **Bot** tab
2. Under **Privileged Gateway Intents**, enable:
   - ✅ **Message Content Intent**
3. Save Changes

### How to upload data via Discord
- Drop your **loads export CSV** into `#finance` — the bot splits it into brokerage and Ivan Cartage loads automatically (uses the `revenue_type_rev_type` column: `B` = brokerage, `I` = Ivan)
- Drop your **expenses CSV** into `#finance` — the bot saves it as `ivan_expenses.csv`
- The bot replies with a row count summary and any warnings
- Refresh the dashboard to see updated numbers

### Required CSV columns

**Loads export (combined file):**
```
revenue_type_rev_type, shipment_pro, customer_name, shipment_customer_total_rates,
shipment_carrier_total_rates, shipment_gross_profit, pick_stop_1_ready_or_deliver_date
```
(Many column name variants are accepted — see `csv_ingestor.py` for the full map)

**Expenses file:**
```
month, category, amount
```
(Or equivalent: date/period, category/type/description, amount/total/charge)

---

## Telegram Setup

The Telegram bot replaces the old local openclaw/macOS LaunchAgent integration.

### Steps
1. Message @BotFather on Telegram → `/newbot` → follow prompts → copy the token
2. Add `TELEGRAM_BOT_TOKEN` to Replit Secrets
3. (Recommended) Add `TELEGRAM_ALLOWED_CHAT_ID` to restrict who can message the bot
   - Get your chat ID: message @userinfobot on Telegram
4. Restart/redeploy the app — Telegram bot starts automatically

### What it does
- Receives messages in Telegram
- Routes them through CoordinatorAgent (finance queries, etc.)
- Replies in Telegram

---

## Data Files

Finance data is loaded from CSV files in the project root. These are tracked in git.

| File | Purpose |
|------|---------|
| `brokerage_loads.csv` | Brokerage load revenue (auto-generated from uploads) |
| `ivan_cartage_loads.csv` | Ivan Cartage load revenue (auto-generated from uploads) |
| `ivan_expenses.csv` | Ivan Cartage expenses by month/category |
| `amazon_loads.csv` | Amazon DSP loads (optional) |

**Updating data:** Upload via Discord `#finance` channel (recommended) or edit files directly in Replit.

---

## Health Check

Visit `/api/health` (no login required) to see system status:

```
https://app.tryaiden.ai/api/health
```

Returns JSON with:
- Which env vars are set (true/false — values never exposed)
- Which CSV files are present and their row counts
- Whether Discord and Telegram bots are running
- Whether optional services (Best Care, etc.) are available

---

## Local Development

```bash
cd /Users/adminoid/AI_WORKSPACE/MultiAgent_Operations
source .venv/bin/activate
FLASK_ENV=development python dashboard.py
# → http://127.0.0.1:5050
```

Local `.env` file (never committed):
```
ADMIN_EMAIL=ryne@bcatcorp.com
ADMIN_PASSWORD_HASH=<generate with werkzeug>
DISCORD_BOT_TOKEN=<your token>
TELEGRAM_BOT_TOKEN=<your token>
TELEGRAM_ALLOWED_CHAT_ID=<your chat id>
```

---

## Redeployment Checklist

- [ ] Code pushed to GitHub (`git push origin main`)
- [ ] Replit pulled latest (`git pull origin main` in Shell)
- [ ] All required Secrets set in Replit
- [ ] App restarted/redeployed
- [ ] `/api/health` shows green for env vars, data files, and bots
- [ ] Login works at `https://app.tryaiden.ai`
- [ ] Dashboard loads finance data
- [ ] Discord bot shows as online and responds in `#finance`
- [ ] Telegram bot responds to messages

---

## Troubleshooting

**Login shows "Invalid credentials":**
- Check `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH` in Replit Secrets
- Regenerate the hash and make sure you copied the full string

**Dashboard shows zeros / no data:**
- Check `/api/health` — are the CSV files present?
- Upload data via Discord `#finance`, or add files directly in Replit

**Discord bot offline:**
- Check `DISCORD_BOT_TOKEN` is set in Replit Secrets
- Ensure Message Content Intent is enabled in Discord Developer Portal
- Check `/api/health` → `bots.discord` should be `true`

**Telegram bot not responding:**
- Check `TELEGRAM_BOT_TOKEN` is set in Replit Secrets
- If `TELEGRAM_ALLOWED_CHAT_ID` is set, make sure you're messaging from that chat
- Check `/api/health` → `bots.telegram` should be `true`

**Session lost after restart:**
- `SECRET_KEY` must be a fixed value in Replit Secrets, not generated at runtime

**Cookies not working on app.tryaiden.ai:**
- Set `COOKIE_DOMAIN=tryaiden.ai` in Replit Secrets (root domain, no `app.` prefix)
