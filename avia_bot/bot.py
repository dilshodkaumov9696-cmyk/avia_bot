"""Telegram wiring for avia_bot.

This module is intentionally thin: every command delegates to the pure builders
in :mod:`avia_bot.responses`, which are covered by tests and the offline demo.
Running the live bot requires a ``TELEGRAM_BOT_TOKEN`` and outbound access to the
Telegram API; the rest of the application works without either.
"""

from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import responses
from .flights import FlightService

logger = logging.getLogger("avia_bot")

_service = FlightService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.HELP)


async def cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.cities_text())


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.search_response(_service, context.args or []))


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.HELP)


async def _reply(update: Update, text: str) -> None:
    if update.message is not None:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def _post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id=%s)", me.username, me.id)


def build_application(token: str) -> Application:
    """Create the Telegram application with all handlers registered."""

    application = Application.builder().token(token).post_init(_post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cities", cities))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    return application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    # httpx logs each request URL at INFO, and Telegram embeds the bot token in
    # the URL path, so keep it at WARNING to avoid leaking the token into logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Export it (see .env.example) to run the "
            "live bot. The flight search core still works offline via `python -m "
            "avia_bot.demo`."
        )
    logger.info("Starting avia_bot in polling mode")
    build_application(token).run_polling()


if __name__ == "__main__":
    main()
