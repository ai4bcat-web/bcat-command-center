"""
bot/discord_bot.py

Discord finance upload bot — LOCAL Flask BCAT dashboard only.

All CSV routing is content-based (never filename-based, except amazon_loads.csv).
Upload any CSV in the configured finance channel; the bot detects the type from
columns and row values.

Schema types (detected in this order):
  "export"           — has a B/I marker column + load indicator → B/I split via csv_ingestor
  "amazon_relay"     — has driver_name/trip_id/estimated_cost/load_execution_status → amazon_relay.csv
  "brokerage_direct" — has gross_revenue + carrier_pay, no marker → brokerage_loads.csv
  "ivan_direct"      — has revenue, no gross_revenue/carrier_pay, no marker → ivan_cartage_loads.csv
  "expenses"         — has month/category/amount (or variants) → ivan_expenses.csv
  "amazon_loads.csv" — matched by filename only (no B/I concept) → amazon_loads.csv

Configuration (all via .env):
  DISCORD_BOT_TOKEN            — required
  DISCORD_FINANCE_CHANNEL      — channel name to watch (default: "finance")
  DISCORD_FINANCE_CHANNEL_ID   — channel ID to watch (overrides name if set)
"""

import os
import sys
import csv
import shutil
import logging
import inspect
import tempfile
from pathlib import Path

import discord
from discord.ext import commands

# Allow importing project-root modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

import csv_ingestor
import finance_csv_parser

# =========================
# CONFIG
# =========================

# Load .env from project root (works both direct run and via PM2)
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_BOT_TOKEN       = os.getenv("DISCORD_BOT_TOKEN")
IVAN_EXPENSES_PATH      = PROJECT_ROOT / "ivan_expenses.csv"
BROKERAGE_LOADS_PATH    = PROJECT_ROOT / "brokerage_loads.csv"
IVAN_CARTAGE_LOADS_PATH = PROJECT_ROOT / "ivan_cartage_loads.csv"
AMAZON_LOADS_PATH       = PROJECT_ROOT / "amazon_loads.csv"
AMAZON_RELAY_PATH       = PROJECT_ROOT / "amazon_relay.csv"

# Channel the bot watches for CSV uploads.
# Override via DISCORD_FINANCE_CHANNEL (name) or DISCORD_FINANCE_CHANNEL_ID (numeric ID).
# Default: any channel named "finance".
FINANCE_CHANNEL_NAME = os.getenv("DISCORD_FINANCE_CHANNEL", "finance").strip().lstrip("#")
_raw_channel_id      = os.getenv("DISCORD_FINANCE_CHANNEL_ID", "").strip()
FINANCE_CHANNEL_ID   = int(_raw_channel_id) if _raw_channel_id.isdigit() else None

# Bot accounts that are explicitly trusted to upload CSVs.
# Prevents reply loops from random bots while still allowing a known
# upload-automation bot (e.g. the bot account used to post files).
# Set in .env:  DISCORD_TRUSTED_BOT_IDS=123456789,987654321
_raw_trusted = os.getenv("DISCORD_TRUSTED_BOT_IDS", "").strip()
TRUSTED_BOT_IDS: set[int] = {
    int(x) for x in _raw_trusted.split(",") if x.strip().isdigit()
}

# ---------------------------------------------------------------------------
# Direct-replacement files: exact filename → (required columns, dest path, label)
#
# These files have no B/I marker concept, so schema detection alone cannot
# route them. Routing for these is still filename-based, but only because
# content detection genuinely cannot distinguish them.
#
# Brokerage and Ivan Cartage loads are NO LONGER here — they are now handled
# by content-based detection in finance_csv_parser ("brokerage_direct" and
# "ivan_direct" schema types) regardless of upload filename.
# ---------------------------------------------------------------------------
CANONICAL_CSV_FILES: dict[str, dict] = {
    "amazon_loads.csv": {
        "required": {"week", "driver", "gross_load_revenue", "bcat_revenue"},
        "dest":     AMAZON_LOADS_PATH,
        "label":    "Amazon loads",
    },
}

# =========================
# LOGGING
# =========================

# Use a fixed name so the logger is always identifiable regardless of how
# this module was imported (importlib path-load gives __name__ == the spec
# name, not a stable dotted path).
logger = logging.getLogger("bcat_discord_bot")
logger.setLevel(logging.DEBUG)

# Attach a dedicated StreamHandler directly to THIS logger with propagate=False.
# This guarantees our logs always reach stdout regardless of how the root
# logger was configured by Flask, Werkzeug, or any other caller.
logger.propagate = False
if not logger.handlers:
    _bot_handler = logging.StreamHandler()
    _bot_handler.setLevel(logging.DEBUG)
    _bot_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    )
    logger.addHandler(_bot_handler)

# Quiet down noisy discord.py internals
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.INFO)

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# FILE OPERATIONS
# =========================

def replace_file_atomic(temp_file: Path, dest_file: Path) -> None:
    """Replace dest_file with temp_file atomically, keeping a .bak backup."""
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    if dest_file.exists():
        backup = dest_file.with_suffix(".csv.bak")
        shutil.copy2(dest_file, backup)
        logger.info(f"Backed up {dest_file.name} → {backup.name}")

    tmp = dest_file.with_suffix(".csv.tmp")
    shutil.copy2(temp_file, tmp)
    tmp.replace(dest_file)
    logger.info(f"Saved {dest_file}")


def merge_amazon_relay_csv(new_path: Path, existing_path: Path) -> tuple[Path, int, int]:
    """
    Merge a newly uploaded Amazon Relay CSV with the existing saved file.

    Dedup strategy: Trip ID is the unique key.
      - All rows from the new file are included.
      - Rows from the existing file whose Trip IDs are NOT in the new file are preserved.
      - If the same Trip ID appears in both files, the new file's row wins.

    This means:
      - Uploading a new week → keeps all prior weeks intact
      - Re-uploading the same week → replaces only that week's rows

    Returns (merged_temp_path, preserved_count, new_count).
    Falls back to (new_path, 0, new_count) if existing file is unreadable.
    """
    # Read new file
    try:
        with open(new_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            new_headers: list[str] = list(reader.fieldnames or [])
            new_rows: list[dict]   = list(reader)
    except Exception as e:
        logger.warning(f"[merge] Cannot read new file: {e} — using as-is")
        return new_path, 0, 0

    # Find the Trip ID column (case-insensitive)
    trip_id_col = next(
        (h for h in new_headers if h.strip().lower() == "trip id"), None
    )
    new_trip_ids: set[str] = set()
    if trip_id_col:
        new_trip_ids = {
            str(r.get(trip_id_col, "")).strip()
            for r in new_rows
            if str(r.get(trip_id_col, "")).strip()
        }

    # Read existing file and keep rows whose Trip IDs are not in the new upload
    preserved: list[dict] = []
    if existing_path.exists() and trip_id_col:
        try:
            with open(existing_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tid = str(row.get(trip_id_col, "")).strip()
                    if tid and tid not in new_trip_ids:
                        preserved.append(row)
            logger.info(f"[merge] Preserved {len(preserved)} rows from prior weeks")
        except Exception as e:
            logger.warning(f"[merge] Cannot read existing file: {e} — no rows preserved")

    # Write merged content to a temp file alongside the new upload
    merged_rows = preserved + new_rows
    tmp = new_path.with_suffix(".merged.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=new_headers, extrasaction="ignore")
            writer.writeheader()
            for row in merged_rows:
                writer.writerow({k: row.get(k, "") for k in new_headers})
        logger.info(
            f"[merge] Wrote merged file: {len(preserved)} preserved + "
            f"{len(new_rows)} new = {len(merged_rows)} total rows"
        )
        return tmp, len(preserved), len(new_rows)
    except Exception as e:
        logger.warning(f"[merge] Failed to write merged file: {e} — using new file as-is")
        return new_path, 0, len(new_rows)


def write_normalized_expenses(rows: list[dict], dest_file: Path) -> None:
    """Write normalized expense rows (month, category, amount) to dest_file."""
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    tmp = dest_file.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["month", "category", "amount"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "month":    row.get("month", ""),
                "category": row.get("category", ""),
                "amount":   row.get("amount", ""),
            })
    tmp.replace(dest_file)
    logger.info(f"Written {len(rows)} expense rows → {dest_file}")


_DISCORD_CONTENT_LIMIT = 1900   # hard cap; Discord's actual limit is 2000
_EMERGENCY_FALLBACK    = "Response too long — see bot logs for full details."


def _truncate(content, max_len: int = _DISCORD_CONTENT_LIMIT) -> str:
    """
    Coerce content to str and hard-cap it.
    Handles None, exceptions, and non-string types safely.
    """
    if content is None:
        return "(empty response)"
    if not isinstance(content, str):
        content = str(content)
    if len(content) <= max_len:
        return content
    omitted = len(content) - max_len
    return content[:max_len] + f"\n… ({omitted} chars omitted — see bot logs)"


async def _safe_send(
    channel,
    content,
    *,
    file=None,
) -> None:
    """
    Centralized Discord send with:
      - automatic coercion + truncation to ≤ 1900 chars
      - callsite detection via inspect
      - full debug logging (callsite, raw len, final len, preview, file name)
      - emergency fallback if content is somehow still > 1900 after truncation
    """
    # ── Callsite detection ─────────────────────────────────────────────────
    frame = inspect.currentframe()
    caller = frame.f_back if frame else None
    if caller:
        callsite = (
            f"{Path(caller.f_code.co_filename).name}"
            f":{caller.f_lineno}"
            f" in {caller.f_code.co_name}()"
        )
    else:
        callsite = "unknown"

    # ── Coerce + measure ───────────────────────────────────────────────────
    raw_type = type(content).__name__
    if not isinstance(content, str):
        content = str(content) if content is not None else "(empty response)"
    raw_len = len(content)

    # ── Truncate ───────────────────────────────────────────────────────────
    content = _truncate(content)

    # ── Emergency guard ────────────────────────────────────────────────────
    # Shouldn't be reachable, but guards against suffix math edge cases.
    if len(content) > _DISCORD_CONTENT_LIMIT + 100:
        logger.error(
            f"[send] EMERGENCY GUARD — content still {len(content)} chars after truncate. "
            f"callsite={callsite}  raw_len={raw_len}  replacing with fallback."
        )
        content = _EMERGENCY_FALLBACK

    # ── Debug log ─────────────────────────────────────────────────────────
    file_name = getattr(file, "filename", None)
    logger.info(
        f"[send] callsite={callsite}  type={raw_type}  "
        f"raw_len={raw_len}  final_len={len(content)}  "
        f"file={file_name}  "
        f"preview={repr(content[:200])}"
    )

    # ── Actual send ────────────────────────────────────────────────────────
    try:
        if file is not None:
            await channel.send(content, file=file)
        else:
            await channel.send(content)
    except Exception as exc:
        logger.error(
            f"[send] FAILED  callsite={callsite}  final_len={len(content)}  "
            f"file={file_name}  error={exc}"
        )
        raise


def is_csv_attachment(attachment: discord.Attachment) -> bool:
    return attachment.filename.lower().endswith(".csv")


def _read_csv_headers(file_path: Path) -> list[str]:
    """Return normalized (lowercased, stripped, spaces→underscores) column names."""
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", newline="", encoding=enc) as f:
                reader = csv.reader(f)
                raw = next(reader, [])
                return [h.strip().lower().replace(" ", "_") for h in raw if h.strip()]
        except UnicodeDecodeError:
            continue
        except StopIteration:
            return []
    return []


async def process_canonical_csv(
    channel: discord.TextChannel,
    temp_path: Path,
    filename: str,
) -> bool:
    """
    Handle a direct-replacement upload for a known canonical BCAT CSV file.
    Validates required columns then atomically replaces the target file.
    Returns True on success, False on failure.
    """
    spec = CANONICAL_CSV_FILES[filename]
    required: set[str] = spec["required"]
    dest: Path         = spec["dest"]
    label: str         = spec["label"]

    logger.info(f"[{filename}] direct-replacement upload — validating columns")

    headers = _read_csv_headers(temp_path)
    if not headers:
        await _safe_send(
            channel,
            f"**{filename}** — Could not read headers. Is the file a valid CSV with a header row?"
        )
        logger.warning(f"[{filename}] no headers found")
        return False

    # Count data rows (quick pass)
    row_count = 0
    try:
        with open(temp_path, "r", newline="", encoding="utf-8-sig") as f:
            row_count = sum(1 for _ in f) - 1  # subtract header
    except Exception:
        pass

    header_set = set(headers)
    missing = required - header_set
    if missing:
        await _safe_send(
            channel,
            f"**{filename}** — Upload rejected. Missing required columns: "
            f"`{', '.join(sorted(missing))}`\n"
            f"Required: `{', '.join(sorted(required))}`"
        )
        logger.warning(f"[{filename}] missing columns: {sorted(missing)}")
        return False

    # Atomic replace
    try:
        replace_file_atomic(temp_path, dest)
    except Exception as e:
        await _safe_send(channel, f"**{filename}** — Save failed: `{e}`")
        logger.error(f"[{filename}] save failed: {e}")
        return False

    await _safe_send(
        channel,
        f"**{label}** updated — **{max(row_count, 0)}** rows saved.\n"
        f"Refresh the dashboard to see updated numbers."
    )
    logger.info(f"[{filename}] saved {row_count} rows → {dest}")
    return True


# =========================
# PROCESSORS
# =========================

async def process_single_csv(
    channel: discord.TextChannel,
    temp_path: Path,
    filename: str,
) -> bool:
    """
    Run the full content-based detection pipeline for one uploaded CSV file.
    Routing is based entirely on file contents, not the upload filename.
    Returns True on success, False on failure.

    Schema types handled:
      "export"           — B/I marker column detected; split and ingest via csv_ingestor
      "brokerage_direct" — pre-processed brokerage CSV; save directly to brokerage_loads.csv
      "ivan_direct"      — pre-processed Ivan CSV; save directly to ivan_cartage_loads.csv
      "expenses"         — expense CSV; normalize and save to ivan_expenses.csv
      "unknown"          — return helpful error
    """
    result = finance_csv_parser.parse_csv(temp_path)

    logger.info(
        f"[{filename}] schema={result.schema_type} "
        f"rows={result.row_count} skipped={result.skipped_count} "
        f"warnings={len(result.warnings)} errors={len(result.errors)}"
    )

    # ── EXPORT: B/I marker detected → split into brokerage + Ivan ─────────
    if result.schema_type == "export":
        try:
            ingest_result = csv_ingestor.process_uploaded_csv(str(temp_path))
            brokerage_rows  = ingest_result.get("brokerage_rows", 0)
            ivan_rows       = ingest_result.get("ivan_rows", 0)
            skipped         = ingest_result.get("skipped_rows", 0)
            marker_col      = ingest_result.get("marker_column", "rev_type")
            ingest_warnings = ingest_result.get("warnings", [])

            logger.info(
                f"[{filename}] export split complete: "
                f"{brokerage_rows} brokerage (B), {ivan_rows} Ivan (I), "
                f"{skipped} skipped — marker column: '{marker_col}'"
            )

            msg = (
                f"Export file split by `{marker_col}` column.\n"
                f"Brokerage (B): **{brokerage_rows}** rows → `brokerage_loads.csv`\n"
                f"Ivan Cartage (I): **{ivan_rows}** rows → `ivan_cartage_loads.csv`\n"
            )
            if skipped:
                msg += f"Skipped (unrecognized marker): {skipped}\n"
            if ingest_warnings:
                for w in ingest_warnings[:3]:
                    msg += f"⚠ {w}\n"
            msg += "Refresh the dashboard to see updated numbers."
            await _safe_send(channel, msg)
            return True

        except Exception as e:
            await _safe_send(channel, f"**{filename}** — Export ingestion error: `{e}`")
            logger.error(f"Export ingestion failed for {filename}: {e}")
            return False

    # ── AMAZON RELAY: Amazon Relay DSP trip export ────────────────────────
    if result.schema_type == "amazon_relay":
        try:
            merged_path, preserved, new_count = merge_amazon_relay_csv(temp_path, AMAZON_RELAY_PATH)
            replace_file_atomic(merged_path, AMAZON_RELAY_PATH)
            # Clean up the merge temp file (replace_file_atomic already made its own .tmp copy)
            if merged_path != temp_path and merged_path.exists():
                try:
                    merged_path.unlink()
                except Exception:
                    pass
        except Exception as e:
            await _safe_send(channel, f"**{filename}** — Save failed: `{e}`")
            logger.error(f"[{filename}] amazon_relay save failed: {e}")
            return False

        total_rows = preserved + new_count

        # ── Persist to database so data survives deploys ──────────────────
        db_count = 0
        try:
            import sys
            sys.path.insert(0, str(PROJECT_ROOT))
            from finance_agent import parse_amazon_relay_csv
            from models import upsert_amazon_trips
            from dashboard import app as _app
            trips = parse_amazon_relay_csv(str(AMAZON_RELAY_PATH))
            with _app.app_context():
                db_count = upsert_amazon_trips(trips)
            logger.info(f"[{filename}] amazon_relay: {db_count} trips saved to database")
        except Exception as e:
            logger.warning(f"[{filename}] DB save skipped (no DB or error): {e}")

        logger.info(
            f"[{filename}] amazon_relay: {new_count} new rows + "
            f"{preserved} preserved from prior weeks = {total_rows} total"
        )
        summary = (
            f"Amazon Relay trips updated — **{new_count}** new rows added.\n"
            + (f"**{preserved}** rows from prior weeks preserved.\n" if preserved else "")
            + f"Total on file: **{total_rows}** rows.\n"
            + (f"**{db_count}** trips saved to database.\n" if db_count else "")
            + f"Refresh the dashboard to see updated Amazon DSP numbers."
        )
        try:
            await _safe_send(channel, summary, file=discord.File(AMAZON_RELAY_PATH))
        except Exception as e:
            logger.warning(f"[{filename}] could not attach file to confirmation: {e}")
            await _safe_send(channel, summary)
        return True

    # ── BROKERAGE DIRECT: already-processed brokerage CSV ─────────────────
    if result.schema_type == "brokerage_direct":
        try:
            replace_file_atomic(temp_path, BROKERAGE_LOADS_PATH)
        except Exception as e:
            await _safe_send(channel, f"**{filename}** — Save failed: `{e}`")
            logger.error(f"[{filename}] brokerage_direct save failed: {e}")
            return False

        await _safe_send(
            channel,
            f"Brokerage loads updated — **{result.row_count}** rows saved to `brokerage_loads.csv`.\n"
            f"Refresh the dashboard to see updated numbers."
        )
        logger.info(f"[{filename}] brokerage_direct: {result.row_count} rows → {BROKERAGE_LOADS_PATH}")
        return True

    # ── IVAN DIRECT: already-processed Ivan Cartage CSV ───────────────────
    if result.schema_type == "ivan_direct":
        try:
            replace_file_atomic(temp_path, IVAN_CARTAGE_LOADS_PATH)
        except Exception as e:
            await _safe_send(channel, f"**{filename}** — Save failed: `{e}`")
            logger.error(f"[{filename}] ivan_direct save failed: {e}")
            return False

        await _safe_send(
            channel,
            f"Ivan Cartage loads updated — **{result.row_count}** rows saved to `ivan_cartage_loads.csv`.\n"
            f"Refresh the dashboard to see updated numbers."
        )
        logger.info(f"[{filename}] ivan_direct: {result.row_count} rows → {IVAN_CARTAGE_LOADS_PATH}")
        return True

    # ── EXPENSES ──────────────────────────────────────────────────────────
    if result.schema_type == "expenses":
        if result.errors:
            report = finance_csv_parser.format_parse_report(result, filename)
            await _safe_send(channel, f"Upload failed — expense file could not be parsed:\n{report}")
            return False

        if result.row_count == 0:
            await _safe_send(channel, f"**{filename}** — No valid expense rows found after normalization.")
            return False

        # Backup existing and write normalized version
        if IVAN_EXPENSES_PATH.exists():
            backup = IVAN_EXPENSES_PATH.with_suffix(".csv.bak")
            shutil.copy2(IVAN_EXPENSES_PATH, backup)

        write_normalized_expenses(result.rows, IVAN_EXPENSES_PATH)

        await _safe_send(
            channel,
            f"Ivan expenses updated — **{result.row_count}** rows saved to `ivan_expenses.csv`.\n"
            f"Refresh the dashboard to see updated numbers."
        )
        return True

    # ── UNKNOWN ───────────────────────────────────────────────────────────
    report = finance_csv_parser.format_parse_report(result, filename)
    await _safe_send(channel, f"**{filename}** — Could not identify CSV type from contents.\n{report}")
    await _safe_send(
        channel,
        f"**Accepted formats (all detected by content, not filename):**\n"
        f"• **Amazon Relay** — `Driver Name`, `Trip ID`, `Estimated Cost`, "
        f"`Load Execution Status` (any 2 of 4) → `amazon_relay.csv`\n"
        f"• **Export/mixed** — B/I marker column + load/revenue column "
        f"→ split: B=brokerage, I=Ivan\n"
        f"• **Brokerage direct** — `gross_revenue` + `carrier_pay` → `brokerage_loads.csv`\n"
        f"• **Ivan direct** — `revenue`, no `gross_revenue`/`carrier_pay` → `ivan_cartage_loads.csv`\n"
        f"• **Expenses** — `month`/`category`/`amount` → `ivan_expenses.csv`"
    )
    logger.warning(f"Unknown CSV schema for {filename}: {result.errors}")
    return False


# =========================
# HELPERS
# =========================

def _is_finance_channel(channel) -> bool:
    """
    Return True if the channel is the configured finance channel.
    Matches by numeric ID first (if DISCORD_FINANCE_CHANNEL_ID is set),
    then by name (case-insensitive).
    """
    if channel is None:
        return False
    if FINANCE_CHANNEL_ID and getattr(channel, "id", None) == FINANCE_CHANNEL_ID:
        return True
    ch_name = getattr(channel, "name", None)
    if ch_name and ch_name.lower() == FINANCE_CHANNEL_NAME.lower():
        return True
    return False


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    logger.warning("=" * 60)
    logger.warning("BCAT DISCORD BOT — READY")
    logger.warning("=" * 60)
    # Token
    token_present = bool(DISCORD_BOT_TOKEN)
    logger.warning(f"Token        : {'SET' if token_present else 'MISSING — bot cannot run'}")
    # Identity
    logger.warning(f"Bot user     : {bot.user}  (ID: {bot.user.id})")
    # Intents
    mc = bot.intents.message_content
    logger.warning(f"Intents      : message_content={mc}  guilds={bot.intents.guilds}  messages={bot.intents.messages}")
    if not mc:
        logger.warning(
            "*** CRITICAL: message_content intent is False! ***\n"
            "  message.content and message.attachments will be EMPTY for all guild messages.\n"
            "  Fix: Discord Developer Portal → your app → Bot → Privileged Gateway Intents\n"
            "       → enable 'Message Content Intent', then restart the bot."
        )
    else:
        logger.warning(
            "Intents OK   : message_content=True — content and attachments are visible.\n"
            "  (Reminder: this must ALSO be enabled in Discord Developer Portal → Bot → Privileged Gateway Intents)"
        )
    # Channel config
    logger.warning(f"Channel name : #{FINANCE_CHANNEL_NAME}  (env: DISCORD_FINANCE_CHANNEL)")
    logger.warning(f"Channel ID   : {FINANCE_CHANNEL_ID or 'not set'}  (env: DISCORD_FINANCE_CHANNEL_ID)")
    if FINANCE_CHANNEL_ID:
        logger.warning("Matching by  : channel ID (ID takes priority over name)")
    else:
        logger.warning("Matching by  : channel NAME — make sure the channel is exactly named "
                       f"'{FINANCE_CHANNEL_NAME}' (case-insensitive)")
    # Trusted bots
    if TRUSTED_BOT_IDS:
        logger.warning(f"Trusted bots : {TRUSTED_BOT_IDS}")
    else:
        logger.warning("Trusted bots : none (only human accounts may upload)")
    # Project root
    logger.warning(f"Project root : {PROJECT_ROOT}")
    logger.warning("Routing      : content-based (export / brokerage_direct / ivan_direct / expenses)")
    logger.warning("=" * 60)
    logger.warning("Bot is ONLINE and listening for messages.")


@bot.event
async def on_message(message: discord.Message):
    # ── Step 0: log EVERY message before any filtering ────────────────────
    ch_name    = getattr(message.channel, "name", f"DM/{message.channel.id}")
    ch_id      = getattr(message.channel, "id", "?")
    guild_name = getattr(message.guild, "name", "DM") if message.guild else "DM"
    auth_name  = str(message.author)
    auth_id    = message.author.id
    is_bot     = message.author.bot
    att_count  = len(message.attachments)
    att_names  = [a.filename for a in message.attachments]
    logger.warning(
        f"[MSG] guild={guild_name!r}  channel=#{ch_name}(id={ch_id})\n"
        f"      author={auth_name!r}(id={auth_id})  bot={is_bot}\n"
        f"      attachments={att_count} {att_names}\n"
        f"      content={repr(message.content[:120])}"
    )

    # ── Step 1: bot filter — ignore bots unless explicitly trusted ────────
    if is_bot:
        if auth_id in TRUSTED_BOT_IDS:
            logger.info(
                f"[on_message] TRUSTED BOT — {auth_name!r} (id={auth_id}) "
                f"is in DISCORD_TRUSTED_BOT_IDS, allowing through"
            )
        else:
            logger.warning(
                f"[on_message] IGNORED — {auth_name!r} (id={auth_id}) "
                f"has bot=True and is not in DISCORD_TRUSTED_BOT_IDS.  "
                f"To allow this account to upload, add its ID to "
                f"DISCORD_TRUSTED_BOT_IDS in .env"
            )
            return

    # ── Step 2: let discord.py dispatch prefix commands (!, etc.) ─────────
    await bot.process_commands(message)

    # ── Step 3: wrap everything else in a top-level handler so exceptions
    #            always produce a Discord reply instead of silent failure ───
    try:
        await _handle_finance_message(message)
    except Exception as exc:
        logger.error(
            f"[on_message] Unhandled exception for message {message.id} "
            f"in #{ch_name}: {exc}",
            exc_info=True,
        )
        try:
            await _safe_send(
                message.channel,
                f"Internal error while processing your message: `{exc}`\n"
                f"Check the bot terminal for the full traceback."
            )
        except Exception:
            pass  # If we can't even send the error, give up silently


async def _handle_finance_message(message: discord.Message):
    """
    Core message handler.  All logic lives here so on_message stays clean
    and every path is covered by the top-level try/except.
    """
    ch_name = getattr(message.channel, "name", f"DM/{message.channel.id}")
    ch_id   = getattr(message.channel, "id", "?")

    # ── Check 1: is this the finance channel? ─────────────────────────────
    if not _is_finance_channel(message.channel):
        logger.warning(
            f"[FILTER] WRONG CHANNEL — ignoring.\n"
            f"  Message was in : #{ch_name} (id={getattr(message.channel, 'id', '?')})\n"
            f"  Bot is watching: "
            + (f"channel ID {FINANCE_CHANNEL_ID}" if FINANCE_CHANNEL_ID
               else f"channel name '{FINANCE_CHANNEL_NAME}' (case-insensitive)")
            + "\n  Fix: rename the channel or set DISCORD_FINANCE_CHANNEL / DISCORD_FINANCE_CHANNEL_ID in .env"
        )
        return

    logger.info(
        f"[handler] Message in #{ch_name} from {message.author} — "
        f"{len(message.attachments)} attachment(s), "
        f"content={repr(message.content[:120])}"
    )

    # ── Check 2: handle "update dashboard" text command (no attachment) ───
    content_lower = message.content.strip().lower()
    is_update_cmd = any(
        kw in content_lower
        for kw in ("update dashboard", "update data", "refresh dashboard", "reload data")
    )

    if not message.attachments:
        if is_update_cmd:
            logger.warning("[handler] 'update dashboard' command — no attachment found in message")
            await _safe_send(
                message.channel,
                "To update the dashboard, attach a CSV file to your message.\n"
                "The file type is detected automatically from its contents:\n"
                "• **Amazon Relay** — `Driver Name`/`Trip ID`/`Estimated Cost`/`Load Execution Status`\n"
                "• **Export** (B/I marker column) → brokerage + Ivan Cartage\n"
                "• **Brokerage direct** (`gross_revenue` + `carrier_pay`) → `brokerage_loads.csv`\n"
                "• **Ivan direct** (`revenue` only) → `ivan_cartage_loads.csv`\n"
                "• **Expenses** (`month`/`category`/`amount`) → `ivan_expenses.csv`"
            )
        elif not message.content:
            # content AND attachments are both empty — almost certainly means
            # the MESSAGE_CONTENT privileged intent is not enabled in the
            # Discord Developer Portal.
            logger.warning(
                "[FILTER] message.content is empty AND message.attachments is empty.\n"
                "  This almost certainly means the MESSAGE_CONTENT privileged intent\n"
                "  is not enabled in the Discord Developer Portal.\n"
                "  Fix: Developer Portal → your app → Bot → Privileged Gateway Intents\n"
                "       → enable 'Message Content Intent', then restart the bot."
            )
        else:
            logger.warning(
                f"[FILTER] Finance channel message ignored — no attachments.\n"
                f"  content={repr(message.content[:120])}\n"
                f"  To trigger the bot, attach a .csv file."
            )
        return

    # ── Check 3: filter to CSV attachments ────────────────────────────────
    csv_attachments = [a for a in message.attachments if is_csv_attachment(a)]
    non_csv = [a for a in message.attachments if not is_csv_attachment(a)]

    logger.info(
        f"[handler] Attachments: {len(csv_attachments)} CSV, {len(non_csv)} non-CSV"
    )

    if non_csv:
        names = ", ".join(f"`{a.filename}`" for a in non_csv)
        logger.info(f"[handler] Non-CSV attachments ignored: {names}")

    if not csv_attachments:
        logger.info("[handler] No CSV attachments — sending help message")
        await _safe_send(
            message.channel,
            "Attachment received but no `.csv` files found.\n"
            "Upload a CSV — type is detected from **contents**, not the filename.\n"
            "• **Amazon Relay** — `Driver Name`/`Trip ID`/`Estimated Cost`/`Load Execution Status`\n"
            "• **Export/mixed** — B/I marker column + load/revenue column\n"
            "• **Brokerage direct** — `gross_revenue` + `carrier_pay`\n"
            "• **Ivan direct** — `revenue`, no `gross_revenue`/`carrier_pay`\n"
            "• **Expenses** — `month`/`category`/`amount`"
        )
        return

    # ── Step 4: process each CSV attachment ───────────────────────────────
    logger.info(
        f"[on_message] ACCEPTED — human upload from {message.author!r} "
        f"in #{ch_name}: {len(csv_attachments)} CSV file(s) will be processed"
    )
    results = []

    for attachment in csv_attachments:
        logger.info(
            f"[handler] Processing attachment: {attachment.filename!r} "
            f"({attachment.size} bytes)"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / attachment.filename

            # Download
            try:
                await attachment.save(temp_path)
                logger.info(
                    f"[handler] Downloaded {attachment.filename!r} "
                    f"→ {temp_path} ({temp_path.stat().st_size} bytes on disk)"
                )
            except Exception as e:
                logger.error(f"[handler] Download failed for {attachment.filename!r}: {e}", exc_info=True)
                await _safe_send(message.channel, f"**{attachment.filename}** — Download failed: `{e}`")
                results.append((attachment.filename, False))
                continue

            # Route: amazon by filename, everything else by content
            fname_lower = attachment.filename.lower()
            if fname_lower in CANONICAL_CSV_FILES:
                logger.info(
                    f"[handler] {attachment.filename!r} → canonical direct-replacement route"
                )
                ok = await process_canonical_csv(message.channel, temp_path, fname_lower)
            else:
                logger.info(
                    f"[handler] {attachment.filename!r} → content-based schema detection"
                )
                ok = await process_single_csv(message.channel, temp_path, attachment.filename)

            logger.info(
                f"[handler] {attachment.filename!r} → {'SUCCESS' if ok else 'FAILED'}"
            )
            results.append((attachment.filename, ok))

    # ── Step 5: batch summary (only when multiple files uploaded) ─────────
    if len(results) > 1:
        succeeded = [n for n, ok in results if ok]
        failed    = [n for n, ok in results if not ok]
        summary = (
            f"**Batch complete**: {len(succeeded)}/{len(results)} files processed successfully."
        )
        if failed:
            summary += f"\nFailed: {', '.join(f'`{f}`' for f in failed)}"
        await _safe_send(message.channel, summary)
        logger.info(
            f"[handler] Batch done — {len(succeeded)} succeeded, {len(failed)} failed"
        )


# =========================
# START
# =========================

def _log_pre_connect_config() -> None:
    """Log config before attempting Discord connection (visible even if login fails)."""
    logger.warning("=" * 60)
    logger.warning("BCAT DISCORD BOT — PRE-CONNECT CONFIG CHECK")
    logger.warning("=" * 60)
    logger.warning(f"Token        : {'SET (' + str(len(DISCORD_BOT_TOKEN)) + ' chars)' if DISCORD_BOT_TOKEN else 'MISSING — bot cannot connect'}")
    logger.warning(f"Channel name : #{FINANCE_CHANNEL_NAME}")
    logger.warning(f"Channel ID   : {FINANCE_CHANNEL_ID or 'not set'}")
    logger.warning(f"Trusted bots : {TRUSTED_BOT_IDS or 'none'}")
    logger.warning(f"Project root : {PROJECT_ROOT}")
    logger.warning(
        "Intents configured in code: "
        f"message_content={bot.intents.message_content}  "
        f"guilds={bot.intents.guilds}  "
        f"messages={bot.intents.messages}"
    )
    logger.warning(
        "REMINDER: message_content intent must ALSO be enabled in:\n"
        "  Discord Developer Portal → your app → Bot → Privileged Gateway Intents\n"
        "  → Message Content Intent = ON\n"
        "  Without this, message.attachments will be empty for all guild messages."
    )
    logger.warning("=" * 60)
    logger.warning("Connecting to Discord...")


if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable is not set.\n"
            "Add it to .env:  DISCORD_BOT_TOKEN=your_token_here"
        )
    _log_pre_connect_config()
    bot.run(DISCORD_BOT_TOKEN)
