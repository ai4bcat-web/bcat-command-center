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
        # Load bot/discord_bot.py by file path to avoid name collision with this file
        import importlib.util
        spec = importlib.util.spec_from_file_location("_finance_discord_bot", BOT_DIR / "discord_bot.py")
        _bot_module = importlib.util.module_from_spec(spec)
        sys.modules["_finance_discord_bot"] = _bot_module
        spec.loader.exec_module(_bot_module)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _bot_module.bot.run(token)
    except Exception as e:
        logger.error("Discord bot crashed: %s", e, exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
