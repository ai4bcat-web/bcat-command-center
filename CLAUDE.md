# MultiAgent Operations — CLAUDE.md

Project context for AI assistants working in this repository.

---

## Running the Dashboard

The active dashboard is `dashboard.py` at the project root.

```bash
cd /Users/adminoid/AI_WORKSPACE/MultiAgent_Operations
source .venv/bin/activate
python3 dashboard.py
```

- Runs on `http://localhost:5050`
- Serves `GET /` → renders `templates/dashboard.html`
- Serves `GET /api/dashboard` → returns JSON metrics from `FinanceAgent`

To run the Discord bot separately:

```bash
python3 discord_bot.py
```

---

## PM2 Process Management

There is **no PM2 configuration in this project**. Processes are started manually.

If PM2 is ever added, the conventional entry point would be:

```bash
pm2 start dashboard.py --interpreter python3 --name bcat-dashboard
pm2 start discord_bot.py --interpreter python3 --name bcat-discord
```

No `ecosystem.config.js` currently exists. The gateway service (openclaw) runs as a macOS LaunchAgent, not via PM2.

---

## Key Services and Agents

### FinanceAgent (`finance_agent.py` — root)
The primary data engine. Ingests CSV files and computes all financial metrics.

- `ingest_data()` — loads brokerage, Ivan Cartage, and Amazon CSVs
- `calculate_brokerage_metrics()` — gross revenue, carrier pay, gross profit, margin
- `get_monthly_brokerage_summary()` — month-by-month brokerage breakdown
- `get_brokerage_top_customers_by_month()` — top 10 customers per month
- `get_ivan_top_customers_by_month()` — top 10 Ivan customers per month
- `get_ivan_expense_metrics()` (module-level) — revenue, expenses, profit, per-mile rates

### CoordinatorAgent (`agents/coordinator_agent.py`)
Routes messages and orchestrates agents. Handles Discord finance channel commands, runs terminal commands via `tools/terminal_executor.py`.

### Discord Bot (`discord_bot.py`)
Connects CoordinatorAgent and FinanceAgent to Discord. Reads `DISCORD_BOT_TOKEN` from `.env`.
- `/input_expenses` — triggers expense ingestion in #finance channel
- `/test_input_expenses` — dry-run version

### Email Service (`email_service.py`)
Gmail API integration using OAuth2. Requires `credentials.json` and `token.json` (not committed).

### CSV Ingestor (`csv_ingestor.py`)
Processes uploaded CSV files, validates required columns, and splits records into brokerage vs. Ivan Cartage categories.

### Openclaw Gateway
Runs as a macOS LaunchAgent on `127.0.0.1:18789`. Connects Telegram (`@big_ron_bot`) to the local agent system. Managed via `openclaw` CLI, not part of this Python codebase. Config: `~/.openclaw/openclaw.json`.

---

## Folder Structure

```
MultiAgent_Operations/
├── dashboard.py                  # PRIMARY entry point (Flask, port 5050)
├── finance_agent.py              # PRIMARY FinanceAgent + module-level helpers
├── coordinator_agent.py          # Thin wrapper around agents/coordinator_agent.py
├── discord_bot.py                # Discord bot (primary)
├── email_service.py              # Gmail API integration
├── csv_ingestor.py               # CSV upload processor
├── request_expenses.py           # Async expense request handler
│
├── agents/                       # Full agent implementations
│   ├── coordinator_agent.py      # CoordinatorAgent (canonical implementation)
│   └── finance_agent.py          # Simplified FinanceAgent (secondary, not primary)
│
├── bot/
│   └── discord_bot.py            # Alternate bot entry (secondary)
│
├── tools/
│   └── terminal_executor.py      # Shell execution wrapper for agents
│
├── templates/
│   └── dashboard.html            # Active Flask template (served by dashboard.py)
│
├── static/
│   ├── dashboard.css             # Dashboard styles
│   ├── dashboard.js              # Dashboard frontend logic (fetches /api/dashboard)
│   ├── marketing.css             # Placeholder (not implemented)
│   └── marketing.js              # Placeholder (not implemented)
│
├── memory/                       # Project notes and architecture context
│
├── dashboard/                    # LEGACY — do not use
│   ├── app.py                    # Legacy Flask app (marked, non-functional)
│   └── dashboard.py              # Legacy intermediate version
│
├── [CSV data files]
│   ├── brokerage_loads.csv
│   ├── ivan_cartage_loads.csv
│   ├── amazon_loads.csv
│   ├── ivan_expenses.csv
│   └── ivan_cartage_expenses.csv (fallback)
│
├── .env                          # Discord bot token (not committed)
├── .env.example                  # Template for .env
├── credentials.json              # Google OAuth credentials (not committed)
├── token.json                    # Cached OAuth token (not committed)
└── .venv/                        # Python 3.14 virtual environment
```

---

## Important Dependencies

All dependencies live in `.venv/` (Python 3.14). There is no `requirements.txt` — install manually if rebuilding:

```bash
pip install flask pandas numpy discord.py python-dotenv google-api-python-client google-auth-oauthlib schedule
```

Key packages:

| Package | Version | Purpose |
|---|---|---|
| Flask | 3.1.3 | Web framework for dashboard |
| pandas | current | CSV ingestion and all data analysis |
| discord.py | 2.7.1 | Discord bot |
| python-dotenv | 1.2.2 | Load `.env` variables |
| google-api-python-client | current | Gmail API |
| google-auth-oauthlib | current | Gmail OAuth2 flow |
| schedule | 1.2.2 | Task scheduling |
| aiohttp | 3.13.3 | Async HTTP (discord.py dependency) |

Frontend uses Chart.js loaded from CDN — no npm/node required.

---

## Development Conventions

### Root-level files are canonical
When both a root-level file and an `agents/` subdirectory version exist (e.g. `finance_agent.py` vs `agents/finance_agent.py`), the **root-level file is the active one**. The subdirectory versions are older or simplified.

### CSV column normalization
Every loader normalizes columns the same way before any other processing:

```python
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
```

Then renames to standard field names (`date`, `revenue`, `miles`, `category`, `amount`) via a `rename_map` dict.

### Numeric parsing
Always use `pd.to_numeric(..., errors="coerce").fillna(0)`. Currency strings (`$`, `,`) are stripped before conversion.

### Flask API pattern
Routes call `agent.ingest_data()` on every request (no caching), then compute and return `jsonify({...})`. No ORM or database — CSVs are the source of truth.

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Methods: `snake_case`
- Environment variables: `ALL_CAPS` in `.env`

### Legacy files
Files confirmed as non-functional or superseded are marked with a `# LEGACY FILE — DO NOT USE` header at the top. Do not delete without checking git history.

### Secrets
Never commit `.env`, `credentials.json`, or `token.json`. The `.env.example` is the safe template.

### No test suite
Test files (`test_finance.py`, `test_email.py`, `finance_agent_tests.py`) are interactive/manual scripts, not pytest suites. Run them directly to spot-check behavior.
