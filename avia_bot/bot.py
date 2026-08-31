"""Telegram wiring for AviaBot.

Thin layer over the pure builders in :mod:`avia_bot.responses`: commands and
inline-button callbacks map to the same functions the offline demo and tests
use. Price tracking runs on the JobQueue, re-pricing every ``AVIA_TRACK_INTERVAL_SECONDS``
(default 30 minutes, like AviaGram) and notifying chats when a fare drops.

Running the live bot needs ``TELEGRAM_BOT_TOKEN`` and outbound access to the
Telegram API; everything else works offline.
"""

from __future__ import annotations

import io
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import charts, pricing, responses
from .flights import FlightService, parse_date, resolve_city
from .tracking import PriceTracker

logger = logging.getLogger("avia_bot")

TRACK_INTERVAL_SECONDS = int(os.environ.get("AVIA_TRACK_INTERVAL_SECONDS", str(pricing.DEFAULT_INTERVAL_SECONDS)))

_service = FlightService()
_tracker = PriceTracker(_service)


def _now_tick() -> int:
    return pricing.current_tick(TRACK_INTERVAL_SECONDS)


def _menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("\U0001f50e \u041f\u043e\u0438\u0441\u043a", callback_data="m:search"),
             InlineKeyboardButton("\U0001f4c5 \u0414\u0438\u0430\u043f\u0430\u0437\u043e\u043d", callback_data="m:range")],
            [InlineKeyboardButton("\U0001f525 \u0413\u043e\u0440\u044f\u0449\u0438\u0435", callback_data="m:hot"),
             InlineKeyboardButton("\U0001f440 \u041c\u043e\u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u044f", callback_data="m:mytracks")],
            [InlineKeyboardButton("\U0001f3d9 \u0413\u043e\u0440\u043e\u0434\u0430", callback_data="m:cities"),
             InlineKeyboardButton("\u2139\ufe0f \u041f\u043e\u043c\u043e\u0449\u044c", callback_data="m:help")],
        ]
    )


def _track_button(quote) -> InlineKeyboardMarkup:
    data = f"trk|{quote.origin}|{quote.destination}|{quote.date.isoformat()}|{quote.passengers}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("\U0001f440 \u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u0446\u0435\u043d\u0443", callback_data=data)]]
    )


def _range_chart_button(quotes) -> InlineKeyboardMarkup:
    first, last = quotes[0], quotes[-1]
    data = f"rc|{first.origin}|{first.destination}|{first.date.isoformat()}|{last.date.isoformat()}|{first.passengers}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("\U0001f4ca \u0413\u0440\u0430\u0444\u0438\u043a \u0446\u0435\u043d", callback_data=data)]]
    )


# --- text/photo helpers ----------------------------------------------------


async def _reply(update: Update, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if update.message is not None:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)


async def _send_photo(bot, chat_id: int, png: bytes, caption: str | None = None) -> None:
    await bot.send_photo(
        chat_id=chat_id,
        photo=InputFile(io.BytesIO(png), filename="chart.png"),
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
    )


# --- command handlers ------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.WELCOME, _menu_markup())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.HELP)


async def cities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.cities_text())


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    text = responses.search_response(_service, args, tick=_now_tick())
    parsed = responses.parse_args(args)
    markup = None
    if len(parsed.cities) >= 2 and parsed.dates:
        origin = resolve_city(responses._split_cities(parsed.cities)[0])
        destination = resolve_city(responses._split_cities(parsed.cities)[1])
        if origin and destination and origin != destination:
            best = _service.cheapest(origin, destination, parsed.dates[0], passengers=parsed.passengers, tick=_now_tick())
            if best is not None:
                markup = _track_button(best)
    await _reply(update, text, markup)


async def range_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, offers = responses.range_response(_service, context.args or [], tick=_now_tick())
    await _reply(update, text, _range_chart_button(offers) if offers else None)


async def roundtrip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.roundtrip_response(_service, context.args or [], tick=_now_tick()))


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.hot_response(_service, context.args or [], tick=_now_tick()))


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    parsed = responses.parse_args(context.args or [])
    if len(parsed.cities) < 2 or not parsed.dates:
        await _reply(update, "\u0424\u043e\u0440\u043c\u0430\u0442: `/track \u043e\u0442\u043a\u0443\u0434\u0430 \u043a\u0443\u0434\u0430 \u0414\u0410\u0422\u0410 [\u043f\u0430\u0441\u0441.]`\n\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: `/track LON NYC 2026-09-05`.")
        return
    origin, destination, unknown = responses._resolve_pair(parsed.cities)
    if unknown:
        await _reply(update, responses._unknown_msg(unknown))
        return
    if origin == destination:
        await _reply(update, "\u0413\u043e\u0440\u043e\u0434 \u0432\u044b\u043b\u0435\u0442\u0430 \u0438 \u043f\u0440\u0438\u043b\u0451\u0442\u0430 \u0434\u043e\u043b\u0436\u043d\u044b \u043e\u0442\u043b\u0438\u0447\u0430\u0442\u044c\u0441\u044f.")
        return
    _, quote = _tracker.add(
        update.effective_chat.id, origin, destination, parsed.dates[0], parsed.passengers, tick=_now_tick()
    )
    if quote is None:
        await _reply(update, f"\u041d\u0435\u0442 \u0440\u0435\u0439\u0441\u043e\u0432 {origin} \u2192 {destination} \u043d\u0430 \u044d\u0442\u0443 \u0434\u0430\u0442\u0443.")
        return
    await _reply(update, responses.track_added_text(quote))


async def mytracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    tracks = _tracker.list_for(update.effective_chat.id)
    markup = None
    if tracks:
        rows = [
            [InlineKeyboardButton(f"\u274c {t.origin}\u2192{t.destination} {t.date.isoformat()}", callback_data=f"unt|{t.key}")]
            for t in tracks
        ]
        markup = InlineKeyboardMarkup(rows)
    await _reply(update, responses.mytracks_text(tracks), markup)


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.HELP, _menu_markup())


# --- callback handling -----------------------------------------------------


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id if query.message else None

    if data == "m:help":
        await query.message.reply_text(responses.HELP, parse_mode=ParseMode.MARKDOWN)
    elif data == "m:cities":
        await query.message.reply_text(responses.cities_text(), parse_mode=ParseMode.MARKDOWN)
    elif data == "m:hot":
        await query.message.reply_text(
            responses.hot_response(_service, [], tick=_now_tick()), parse_mode=ParseMode.MARKDOWN
        )
    elif data == "m:search":
        await query.message.reply_text(
            "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435: `/search London Dubai 2026-09-05`", parse_mode=ParseMode.MARKDOWN
        )
    elif data == "m:range":
        await query.message.reply_text(
            "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435: `/range LON NYC 2026-09-01 2026-09-10`", parse_mode=ParseMode.MARKDOWN
        )
    elif data == "m:mytracks":
        tracks = _tracker.list_for(chat_id) if chat_id is not None else []
        await query.message.reply_text(responses.mytracks_text(tracks), parse_mode=ParseMode.MARKDOWN)
    elif data.startswith("trk|") and chat_id is not None:
        _, o, d, date_s, pax = data.split("|")
        date = parse_date(date_s)
        _, quote = _tracker.add(chat_id, o, d, date, int(pax), tick=_now_tick())
        if quote is not None:
            await query.message.reply_text(responses.track_added_text(quote), parse_mode=ParseMode.MARKDOWN)
    elif data.startswith("rc|"):
        _, o, d, start_s, end_s, pax = data.split("|")
        offers = _service.search_range(o, d, parse_date(start_s), parse_date(end_s), passengers=int(pax), tick=_now_tick())
        if offers and chat_id is not None:
            await _send_photo(context.bot, chat_id, charts.render_range_chart(offers), caption=f"\U0001f4ca {o} \u2192 {d}")
    elif data.startswith("unt|") and chat_id is not None:
        key = data[len("unt|"):]
        removed = _tracker.remove(chat_id, key)
        await query.message.reply_text(
            "\u0423\u0434\u0430\u043b\u0438\u043b \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435." if removed else "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e."
        )


# --- price-tracking job ----------------------------------------------------


async def _poll_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    drops = _tracker.poll(_now_tick())
    for event in drops:
        text = responses.drop_text(
            event.track.origin, event.track.destination, event.track.date,
            event.previous_price, event.new_price, event.drop_pct,
        )
        try:
            await context.bot.send_message(event.track.chat_id, text, parse_mode=ParseMode.MARKDOWN)
            if len(event.track.history) >= 2:
                await _send_photo(context.bot, event.track.chat_id, charts.render_history_chart(event.track))
        except Exception:  # noqa: BLE001 - never let one bad chat kill the job
            logger.exception("Failed to notify chat %s", event.track.chat_id)


async def _post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id=%s)", me.username, me.id)
    if application.job_queue is not None:
        application.job_queue.run_repeating(_poll_prices, interval=TRACK_INTERVAL_SECONDS, first=TRACK_INTERVAL_SECONDS)
        logger.info("Price tracking every %ss", TRACK_INTERVAL_SECONDS)


def build_application(token: str) -> Application:
    application = Application.builder().token(token).post_init(_post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cities", cities))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("range", range_search))
    application.add_handler(CommandHandler("rt", roundtrip))
    application.add_handler(CommandHandler("hot", hot))
    application.add_handler(CommandHandler("track", track))
    application.add_handler(CommandHandler("mytracks", mytracks))
    application.add_handler(CallbackQueryHandler(on_callback))
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
