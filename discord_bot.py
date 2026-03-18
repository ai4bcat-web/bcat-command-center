import os
import sys
import tempfile
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from agents.coordinator_agent import CoordinatorAgent
try:
    from agents.marketing_agent import MarketingAgent
except ImportError:
    MarketingAgent = None
from agents.finance_agent import FinanceAgent
from csv_ingestor import process_uploaded_csv
import pandas as pd
from pathlib import Path

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not DISCORD_BOT_TOKEN:
    sys.exit('ERROR: DISCORD_BOT_TOKEN is not set. Add it to your .env file.')

PROJECT_ROOT = Path(__file__).resolve().parent

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

coordinator = CoordinatorAgent()
finance_agent = FinanceAgent()


@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}!')
    try:
        import agent_registry
        agent_registry.register("DiscordBot", f"Discord bot integration ({bot.user})")
    except Exception:
        pass


@bot.command()
async def test_input_expenses(ctx):
    await ctx.send("It's time to update your January expenses for Ivan Cartage. Please provide the amounts. Tolls:")


@bot.command()
async def input_expenses(ctx):
    print(f'Received command in channel: {ctx.channel.name}')
    if ctx.channel.name == 'finance':
        print('Detected /input_expenses command')
        await finance_agent.request_monthly_expenses(ctx)
    else:
        await ctx.send('This command can only be used in the finance channel.')


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ── CSV file upload handler ───────────────────────────────────────────
    if message.attachments:
        csv_attachments = [a for a in message.attachments if a.filename.lower().endswith('.csv')]
        for attachment in csv_attachments:
            await _handle_csv_upload(message, attachment)
            return  # process one file at a time

    await bot.process_commands(message)


async def _handle_csv_upload(message, attachment):
    """Download the attached CSV and route it to the correct ingestor."""
    filename = attachment.filename.lower()

    await message.channel.send(f"📥 Received `{attachment.filename}` — processing...")

    # Download the file to a temp location
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                data = await resp.read()
    except Exception as e:
        await message.channel.send(f"❌ Failed to download file: {e}")
        return

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        # ── Expense file ─────────────────────────────────────────────────
        if 'expense' in filename:
            result = _ingest_expenses(tmp_path)
            await message.channel.send(
                f"✅ **Expenses updated**\n"
                f"• {result['rows']} rows saved to `ivan_expenses.csv`\n"
                f"• Months covered: {result['months']}"
            )

        # ── Loads file (combined brokerage + Ivan) ───────────────────────
        else:
            result = process_uploaded_csv(tmp_path, output_dir=PROJECT_ROOT)
            warnings_text = ''
            if result['warnings']:
                warnings_text = '\n⚠️ ' + '\n⚠️ '.join(result['warnings'])
            await message.channel.send(
                f"✅ **Loads updated**\n"
                f"• {result['brokerage_rows']} brokerage loads saved\n"
                f"• {result['ivan_rows']} Ivan Cartage loads saved\n"
                f"• {result['skipped_rows']} rows skipped (unrecognized type)"
                + warnings_text
            )

    except ValueError as e:
        await message.channel.send(
            f"❌ **Could not process `{attachment.filename}`**\n```{e}```\n"
            f"Make sure the file has the required columns."
        )
    except Exception as e:
        await message.channel.send(f"❌ Unexpected error: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)


def _ingest_expenses(filepath):
    """Save an expense CSV to ivan_expenses.csv and return a summary."""
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding='latin-1')

    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    rename_map = {
        'month': 'month', 'date': 'month', 'expense_date': 'month',
        'category': 'category', 'expense_category': 'category', 'type': 'category',
        'amount': 'amount', 'expense': 'amount', 'total': 'amount',
    }
    for src, dst in rename_map.items():
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})

    required = ['month', 'category', 'amount']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Available: {list(df.columns)}")

    out = df[['month', 'category', 'amount']].copy()
    out_path = PROJECT_ROOT / 'ivan_expenses.csv'
    out.to_csv(out_path, index=False)

    months = sorted(out['month'].dropna().unique().tolist())
    return {'rows': len(out), 'months': ', '.join(str(m) for m in months)}


# Run the bot
bot.run(DISCORD_BOT_TOKEN)
