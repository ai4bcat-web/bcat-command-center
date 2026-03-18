"""
telegram_bot.py

Polling-based Telegram bot that replaces the local openclaw/macOS LaunchAgent.
Routes messages to CoordinatorAgent and replies in Telegram.

Required env vars:
  TELEGRAM_BOT_TOKEN  — from @BotFather
  TELEGRAM_ALLOWED_CHAT_ID  — (optional) restrict to one chat/user ID

Run directly:  python telegram_bot.py
Or started as a background thread by dashboard.py.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
POLL_TIMEOUT = 30  # seconds for long-polling


def _api(token: str, method: str, **kwargs):
    url = TELEGRAM_API.format(token=token, method=method)
    resp = requests.post(url, timeout=POLL_TIMEOUT + 5, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _send(token: str, chat_id: int, text: str):
    try:
        _api(token, "sendMessage", json={"chat_id": chat_id, "text": text})
    except Exception as e:
        logger.error("Telegram sendMessage failed: %s", e)


def _handle_message(token: str, message: dict, allowed_chat_id: int | None):
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    if allowed_chat_id and chat_id != allowed_chat_id:
        logger.debug("Ignored message from unauthorized chat %s", chat_id)
        return

    logger.info("Telegram [%s]: %s", chat_id, text[:80])

    try:
        from agents.coordinator_agent import CoordinatorAgent
        coordinator = CoordinatorAgent()
        response = coordinator.handle(text, channel_name="telegram")
        reply = response if response else "I don't have an answer for that right now."
    except Exception as e:
        logger.error("CoordinatorAgent error: %s", e)
        reply = "Sorry, I ran into an error processing that."

    _send(token, chat_id, reply)


def run():
    """Start long-polling loop. Blocks until stopped or fatal error."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot will not start.")
        return

    raw_allowed = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
    allowed_chat_id = int(raw_allowed) if raw_allowed.lstrip("-").isdigit() else None

    logger.info("Telegram bot starting (polling)…")
    if allowed_chat_id:
        logger.info("Restricted to chat ID: %s", allowed_chat_id)

    offset = None
    consecutive_errors = 0

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset

            data = _api(token, "getUpdates", json=params)
            updates = data.get("result", [])
            consecutive_errors = 0

            for update in updates:
                offset = update["update_id"] + 1
                if "message" in update:
                    _handle_message(token, update["message"], allowed_chat_id)

        except requests.exceptions.RequestException as e:
            consecutive_errors += 1
            wait = min(60, 5 * consecutive_errors)
            logger.warning("Telegram poll error (%s), retrying in %ds: %s", consecutive_errors, wait, e)
            time.sleep(wait)
        except Exception as e:
            logger.error("Telegram bot unexpected error: %s", e, exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
