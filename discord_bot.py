"""
discord_bot.py  (project root — launcher)

Starts the finance upload bot defined in bot/discord_bot.py.
Run directly:   python discord_bot.py
Or imported by dashboard.py to start as a background thread.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure project root and bot/ are both on the path
PROJECT_ROOT = Path(__file__).resolve().parent
BOT_DIR = PROJECT_ROOT / "bot"
for p in [str(PROJECT_ROOT), str(BOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def run():
    """Import and run the bot. Blocks until the bot exits."""
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("DISCORD_BOT_TOKEN not set — Discord bot will not start.")
        return

    try:
        # Import the proper bot module from bot/
        # bot/discord_bot.py defines `bot` but guards run() behind __name__
        import discord_bot as _bot_module  # resolves to bot/discord_bot.py via sys.path
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _bot_module.bot.run(token)
    except Exception as e:
        logger.error("Discord bot crashed: %s", e, exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
