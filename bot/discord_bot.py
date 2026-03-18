"""
bot/discord_bot.py

Discord finance upload bot.

Accepted file types in #finance:
  • Ivan expenses CSV  — any file where month/category/amount can be mapped
  • Brokerage export   — any file with load shipment signature columns

Pipeline order (enforced by finance_csv_parser):
  download → normalize headers → apply column map → detect schema type
  → derive missing fields → validate internal schema → save/ingest
"""

import os
import sys
import csv
import shutil
import logging
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

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
IVAN_EXPENSES_PATH = PROJECT_ROOT / "ivan_expenses.csv"
FINANCE_CHANNEL_NAME = "finance"

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

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


def is_csv_attachment(attachment: discord.Attachment) -> bool:
    return attachment.filename.lower().endswith(".csv")


# =========================
# PROCESSORS
# =========================

async def process_single_csv(
    channel: discord.TextChannel,
    temp_path: Path,
    filename: str,
) -> bool:
    """
    Run the full parse pipeline for one uploaded CSV file.
    Returns True on success, False on failure.
    """
    result = finance_csv_parser.parse_csv(temp_path)

    logger.info(
        f"[{filename}] schema={result.schema_type} "
        f"rows={result.row_count} skipped={result.skipped_count} "
        f"warnings={len(result.warnings)} errors={len(result.errors)}"
    )

    # ── EXPENSES ──────────────────────────────────────────────────────────
    if result.schema_type == "expenses":
        if result.errors:
            report = finance_csv_parser.format_parse_report(result, filename)
            await channel.send(f"Upload failed — expense file could not be parsed:\n{report}")
            return False

        if result.row_count == 0:
            await channel.send(f"**{filename}** — No valid expense rows found after normalization.")
            return False

        # Backup existing and write normalized version
        if IVAN_EXPENSES_PATH.exists():
            backup = IVAN_EXPENSES_PATH.with_suffix(".csv.bak")
            shutil.copy2(IVAN_EXPENSES_PATH, backup)

        write_normalized_expenses(result.rows, IVAN_EXPENSES_PATH)

        report = finance_csv_parser.format_parse_report(result, filename)
        await channel.send(
            f"Ivan expenses updated.\n{report}\n"
            f"Saved to: `{IVAN_EXPENSES_PATH}`\n"
            f"Refresh the dashboard to see updated numbers."
        )
        return True

    # ── EXPORT (loads) ────────────────────────────────────────────────────
    if result.schema_type == "export":
        try:
            ingest_result = csv_ingestor.process_uploaded_csv(str(temp_path))
            brokerage_rows = ingest_result.get("brokerage_rows", 0)
            ivan_rows = ingest_result.get("ivan_rows", 0)
            skipped = ingest_result.get("skipped_rows", 0)
            ingest_warnings = ingest_result.get("warnings", [])

            logger.info(
                f"[{filename}] export ingested: "
                f"{brokerage_rows} brokerage, {ivan_rows} Ivan, {skipped} skipped"
            )

            msg = (
                f"**{filename}** — Load export ingested.\n"
                f"Raw headers: `{', '.join(result.raw_headers[:8])}{'…' if len(result.raw_headers) > 8 else ''}`\n"
                f"Brokerage rows: **{brokerage_rows}** → `brokerage_loads.csv`\n"
                f"Ivan Cartage rows: **{ivan_rows}** → `ivan_cartage_loads.csv`\n"
            )
            if skipped:
                msg += f"Skipped rows: {skipped}\n"
            if ingest_warnings:
                for w in ingest_warnings[:3]:
                    msg += f"⚠ {w}\n"
            msg += "Refresh the dashboard to see updated numbers."
            await channel.send(msg)
            return True

        except Exception as e:
            await channel.send(f"**{filename}** — Export ingestion error: {e}")
            logger.error(f"Export ingestion failed for {filename}: {e}")
            return False

    # ── UNKNOWN ───────────────────────────────────────────────────────────
    report = finance_csv_parser.format_parse_report(result, filename)
    await channel.send(
        f"**{filename}** — Could not identify CSV schema.\n{report}\n\n"
        f"**Accepted formats:**\n"
        f"• Expenses file: needs columns mappable to `month`, `category`, `amount`\n"
        f"  (e.g. Date/Month, Category/Type/Description, Amount/Total/Charge)\n"
        f"• Brokerage export: needs `revenue_type_rev_type`, `shipment_pro`, etc."
    )
    logger.warning(f"Unknown CSV schema for {filename}: {result.errors}")
    return False


# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Project root: {PROJECT_ROOT}")
    print("Watching #finance for CSV uploads (expenses + brokerage export).")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not message.attachments:
        return

    if not message.channel or getattr(message.channel, "name", None) != FINANCE_CHANNEL_NAME:
        return

    csv_attachments = [a for a in message.attachments if is_csv_attachment(a)]

    if not csv_attachments:
        await message.channel.send(
            "Attachment received but it is not a CSV. Upload either:\n"
            "• An expenses file (any CSV with month/category/amount or equivalent columns)\n"
            "• A brokerage export (e.g. `export_*.csv` from the TMS)"
        )
        return

    results = []

    for attachment in csv_attachments:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / attachment.filename

            try:
                await attachment.save(temp_path)
                logger.info(f"Downloaded {attachment.filename} ({attachment.size} bytes)")
            except Exception as e:
                await message.channel.send(f"**{attachment.filename}** — Download failed: {e}")
                logger.error(f"Download failed: {e}")
                results.append((attachment.filename, False))
                continue

            ok = await process_single_csv(message.channel, temp_path, attachment.filename)
            results.append((attachment.filename, ok))

    if len(results) > 1:
        succeeded = [n for n, ok in results if ok]
        failed = [n for n, ok in results if not ok]
        summary = f"**Batch**: {len(succeeded)}/{len(results)} files processed successfully."
        if failed:
            summary += f"\nFailed: {', '.join(f'`{f}`' for f in failed)}"
        await message.channel.send(summary)


# =========================
# START
# =========================

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is not set.")
    bot.run(DISCORD_BOT_TOKEN)
