"""Telegram bot: AviaGram-style guided flight search.

Flow (a ConversationHandler): city *from* → pick airport → city *to* → pick
airport → passengers & cabin (−/+ buttons) → calendar (outbound + optional
return) → animated multi-provider search → paginated result cards with filters,
price advice, flexible dates, buy links and one-tap price tracking.

Runs live with ``TELEGRAM_BOT_TOKEN``; all logic is covered offline by the demo
and tests. Replies are rendered to emoji-safe HTML.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import io
import logging
import os
import re
from typing import List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from . import calendar_ui, charts, geo, pricing, responses
from .flights import Filters, FlightService
from .pricing import Passengers
from .search_flow import adjust_pax, cycle_cabin, paginate
from .tracking import PriceTracker

logger = logging.getLogger("avia_bot")

TRACK_INTERVAL_SECONDS = int(os.environ.get("AVIA_TRACK_INTERVAL_SECONDS", str(pricing.DEFAULT_INTERVAL_SECONDS)))

_service = FlightService()
_tracker = PriceTracker(_service)

# Conversation states
FROM, TO, PAX, DATES = range(4)

# Reply-keyboard button labels
BTN_SEARCH = "🔎 Поиск"
BTN_RANGE = "🔎🗓 По диапазону"
BTN_TRACK = "➕👀 Добавить отслеживание"


def _now_tick() -> int:
    return pricing.current_tick(TRACK_INTERVAL_SECONDS)


# --- keyboards -------------------------------------------------------------


def _main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(BTN_SEARCH)], [KeyboardButton(BTN_RANGE), KeyboardButton(BTN_TRACK)]],
        resize_keyboard=True,
    )


def _city_kb(options, prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(a.option_text, callback_data=f"{prefix}:{a.code}")] for a in options]
    )


def _pax_kb(pax: Passengers) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("−", callback_data="px:a:-"),
         InlineKeyboardButton(f"Взрослые: {pax.adults}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:a:+")],
        [InlineKeyboardButton("−", callback_data="px:c:-"),
         InlineKeyboardButton(f"Дети: {pax.children}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:c:+")],
        [InlineKeyboardButton("−", callback_data="px:i:-"),
         InlineKeyboardButton(f"Младенцы: {pax.infants}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:i:+")],
        [InlineKeyboardButton("◀️", callback_data="px:cab:-"),
         InlineKeyboardButton(f"💺 {pricing.cabin_name(pax.cabin)}", callback_data="px:x"),
         InlineKeyboardButton("▶️", callback_data="px:cab:+")],
        [InlineKeyboardButton("✅ Далее", callback_data="px:go")],
    ])


def _calendar_kb(year: int, month: int, selected) -> InlineKeyboardMarkup:
    rows = calendar_ui.build_calendar(year, month, selected)
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows]
    )


def _results_kb(search: dict) -> InlineKeyboardMarkup:
    results = search["results"]
    page = search["page"]
    offer = results[page]
    pax = search["pax"]
    buy_url = responses.aviasales_url(
        search["o_code"], search["d_code"], search["dep"], back_date=search.get("ret"),
        passengers=max(1, pax.adults + pax.children),
    )
    total = len(results)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(responses.offer_buy_label(offer), url=buy_url)],
        [InlineKeyboardButton("«", callback_data="res:prev"),
         InlineKeyboardButton(f"{page + 1} / {total}", callback_data="res:x"),
         InlineKeyboardButton("»", callback_data="res:next")],
        [InlineKeyboardButton("🗓 ±3 дня", callback_data="res:flex"),
         InlineKeyboardButton("🔄 Обновить", callback_data="res:refresh"),
         InlineKeyboardButton("⚙️ Фильтры", callback_data="res:filters")],
        [InlineKeyboardButton("➕👀 Отслеживать цену", callback_data="res:track")],
    ])


def _filters_kb(f: Filters) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if f.direct_only else '⬜'} Только прямые", callback_data="flt:direct")],
        [InlineKeyboardButton(f"{'✅' if f.with_baggage else '⬜'} С багажом", callback_data="flt:bag")],
        [InlineKeyboardButton("Применить", callback_data="flt:apply"),
         InlineKeyboardButton("Сбросить", callback_data="flt:reset")],
    ])


# --- send helpers ----------------------------------------------------------


async def _reply(update: Update, text: str, markup=None) -> None:
    if update.message is not None:
        await update.message.reply_text(responses.render_html(text), parse_mode=ParseMode.HTML, reply_markup=markup)


async def _edit(query, text: str, markup=None) -> None:
    await query.edit_message_text(responses.render_html(text), parse_mode=ParseMode.HTML, reply_markup=markup)


async def _send_photo(bot, chat_id: int, png: bytes, caption: Optional[str] = None) -> None:
    await bot.send_photo(chat_id=chat_id, photo=InputFile(io.BytesIO(png), filename="chart.png"),
                         caption=responses.render_html(caption) if caption else None, parse_mode=ParseMode.HTML)


# --- simple commands -------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.WELCOME, _main_kb())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.HELP, _main_kb())


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deals = _service.cheapest_deals(tick=_now_tick())
    await _reply(update, responses.hot_text(deals))


async def mytracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    tracks = _tracker.list_for(update.effective_chat.id)
    await _reply(update, responses.mytracks_text(tracks))


# --- guided search conversation -------------------------------------------


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["draft"] = {"pax": Passengers()}
    await _reply(update, responses.ASK_FROM, _main_kb())
    return FROM


async def _handle_city_text(update, context, prefix):
    options = geo.search_cities(update.message.text)
    if not options:
        await _reply(update, responses.CITY_NOT_FOUND)
        return None
    prompt = responses.CHOOSE_FROM if prefix == "cf" else responses.CHOOSE_TO
    await _reply(update, prompt, _city_kb(options, prefix))
    return options


async def from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_city_text(update, context, "cf")
    return FROM


async def from_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":")[1]
    context.user_data["draft"]["o"] = geo.airport(code)
    await _edit(query, f"{responses.route_line_from(context.user_data['draft']['o'])}\n\n{responses.ASK_TO}")
    return TO


async def to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_city_text(update, context, "ct")
    return TO


async def to_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":")[1]
    draft = context.user_data["draft"]
    draft["d"] = geo.airport(code)
    text = responses.route_line(draft["o"], draft["d"]) + "\n\n" + responses.PAX_PROMPT
    await _edit(query, text, _pax_kb(draft["pax"]))
    return PAX


async def pax_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = context.user_data["draft"]
    pax: Passengers = draft["pax"]
    data = query.data

    if data == "px:x":
        return PAX
    if data == "px:go":
        today = _dt.date.today()
        draft.update({"y": today.year, "m": today.month, "dep": None, "ret": None})
        await _edit(query, responses.dates_prompt(None, None), _calendar_kb(today.year, today.month, []))
        return DATES

    field = {"a": "adults", "c": "children", "i": "infants"}.get(data.split(":")[1])
    if field:
        pax = adjust_pax(pax, field, 1 if data.endswith("+") else -1)
    elif data.startswith("px:cab"):
        pax = cycle_cabin(pax, 1 if data.endswith("+") else -1)
    draft["pax"] = pax
    await query.edit_message_reply_markup(_pax_kb(pax))
    return PAX


async def dates_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = context.user_data["draft"]
    data = query.data

    if data == "cal:x":
        return DATES
    if data.startswith("cal:nav:"):
        y, m = map(int, data.split(":")[2].split("-"))
        draft["y"], draft["m"] = y, m
        selected = [d for d in (draft.get("dep"), draft.get("ret")) if d]
        await query.edit_message_reply_markup(_calendar_kb(y, m, selected))
        return DATES
    if data.startswith("cal:day:"):
        day = _dt.date.fromisoformat(data.split(":", 2)[2])
        if not draft.get("dep") or (draft.get("dep") and draft.get("ret")):
            draft["dep"], draft["ret"] = day, None      # (re)start selection
        elif day < draft["dep"]:
            draft["dep"] = day
        else:
            draft["ret"] = day
        selected = [d for d in (draft.get("dep"), draft.get("ret")) if d]
        await _edit(query, responses.dates_prompt(draft.get("dep"), draft.get("ret")),
                    _calendar_kb(draft["y"], draft["m"], selected))
        return DATES
    if data == "cal:done":
        if not draft.get("dep"):
            await query.answer("Выберите дату вылета", show_alert=True)
            return DATES
        return await _run_search(update, context)
    return DATES


async def _run_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data["draft"]
    # Animated multi-provider search.
    for step in range(1, 4):
        await _edit(query, responses.searching_bar(step))
        await asyncio.sleep(0.4)

    pax: Passengers = draft["pax"]
    results = _service.search(draft["o"].code, draft["d"].code, draft["dep"], pax=pax, tick=_now_tick())
    context.user_data["search"] = {
        "o_code": draft["o"].code, "o_city": draft["o"].city,
        "d_code": draft["d"].code, "d_city": draft["d"].city,
        "dep": draft["dep"], "ret": draft.get("ret"), "pax": pax,
        "filters": Filters(), "results": results, "page": 0,
    }
    await _show_results(query, context, edit=True)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, "Отменил. Нажмите 🔎 Поиск, чтобы начать заново.", _main_kb())
    return ConversationHandler.END


# --- results (post-conversation) ------------------------------------------


def _results_text(search: dict) -> str:
    results = search["results"]
    if not results:
        return responses.no_results_text(search["filters"].active)
    page = search["page"]
    offer = results[page]
    header = responses.results_header(search["o_city"], search["d_city"], search["dep"],
                                      search["pax"], page, len(results), search["filters"])
    body = responses.format_offer(offer)
    advice = responses.price_advice_text(
        search["o_code"], search["d_code"],
        pricing.price_trend(pricing.route_key(offer.itinerary.origin, offer.itinerary.destination), offer.tick),
    )
    text = header + "\n\n" + body
    if advice:
        text += "\n\n" + advice
    return text


async def _show_results(query, context, edit: bool):
    search = context.user_data["search"]
    markup = _results_kb(search) if search["results"] else None
    text = _results_text(search)
    if edit:
        await _edit(query, text, markup)
    else:
        await query.message.reply_text(responses.render_html(text), parse_mode=ParseMode.HTML, reply_markup=markup)


async def results_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    search = context.user_data.get("search")
    if not search:
        await query.answer("Начните новый поиск 🔎", show_alert=True)
        return
    data = query.data

    if data == "res:x":
        return
    if data in ("res:next", "res:prev"):
        _, search["page"], _ = paginate(search["results"], search["page"] + (1 if data == "res:next" else -1))
        await _show_results(query, context, edit=True)
    elif data == "res:refresh":
        search["results"] = _service.search(search["o_code"], search["d_code"], search["dep"],
                                             pax=search["pax"], tick=_now_tick(), filters=search["filters"])
        _, search["page"], _ = paginate(search["results"], search["page"])
        await _show_results(query, context, edit=True)
    elif data == "res:filters":
        await _edit(query, "⚙️ Фильтры поиска:", _filters_kb(search["filters"]))
    elif data == "res:flex":
        await _send_flex(query, context)
    elif data == "res:track":
        await _add_track_from_search(query.message.chat_id, context)
        await query.message.reply_text(
            responses.render_html("Готово! " + responses.mytracks_hint()), parse_mode=ParseMode.HTML)


async def filters_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    search = context.user_data.get("search")
    if not search:
        return
    f: Filters = search["filters"]
    data = query.data
    if data == "flt:direct":
        f.direct_only = not f.direct_only
        await query.edit_message_reply_markup(_filters_kb(f))
    elif data == "flt:bag":
        f.with_baggage = not f.with_baggage
        await query.edit_message_reply_markup(_filters_kb(f))
    elif data in ("flt:apply", "flt:reset"):
        if data == "flt:reset":
            search["filters"] = Filters()
        search["results"] = _service.search(search["o_code"], search["d_code"], search["dep"],
                                             pax=search["pax"], tick=_now_tick(), filters=search["filters"])
        search["page"] = 0
        await _show_results(query, context, edit=True)


async def _send_flex(query, context):
    search = context.user_data["search"]
    points = _service.flexible_dates(search["o_code"], search["d_code"], search["dep"],
                                     pax=search["pax"], tick=_now_tick())
    text = responses.flexible_text(points, search["dep"]) or "Рядом дешевле не нашлось."
    await query.message.reply_text(responses.render_html(text), parse_mode=ParseMode.HTML)
    if points:
        png = charts.render_range_chart(search["o_city"], search["d_city"], points)
        await _send_photo(context.bot, query.message.chat_id, png)


async def _add_track_from_search(chat_id: int, context) -> Optional[int]:
    search = context.user_data.get("search")
    if not search:
        return None
    _, price = _tracker.add(chat_id, search["o_code"], search["d_code"], search["dep"],
                            pax=search["pax"], tick=_now_tick())
    return price


# --- reply-keyboard shortcuts ---------------------------------------------


async def range_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search = context.user_data.get("search")
    if not search:
        await _reply(update, "Сначала выполните поиск 🔎, потом смотрите цены по диапазону.")
        return
    start = search["dep"] - _dt.timedelta(days=3)
    end = search["dep"] + _dt.timedelta(days=7)
    points = _service.search_range(search["o_code"], search["d_code"], start, end,
                                   pax=search["pax"], tick=_now_tick())
    await _reply(update, responses.range_text(search["o_city"], search["d_city"], points, search["pax"]))
    if points and update.effective_chat is not None:
        png = charts.render_range_chart(search["o_city"], search["d_city"], points)
        await _send_photo(context.bot, update.effective_chat.id, png)


async def track_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None:
        return
    price = await _add_track_from_search(update.effective_chat.id, context)
    if price is None:
        await _reply(update, "Сначала выполните поиск 🔎 — потом добавлю отслеживание маршрута.")
        return
    s = context.user_data["search"]
    await _reply(update, responses.track_added_text(s["o_city"], s["d_city"], s["dep"], s["pax"], price))


# --- price-tracking job ----------------------------------------------------


async def _poll_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    for event in _tracker.poll(_now_tick()):
        t = event.track
        o_city = geo.city_of(t.origin) or t.origin
        d_city = geo.city_of(t.destination) or t.destination
        text = responses.drop_text(o_city, d_city, t.date, event.previous_price, event.new_price, event.drop_pct)
        try:
            await context.bot.send_message(t.chat_id, responses.render_html(text), parse_mode=ParseMode.HTML)
            if len(t.history) >= 2:
                await _send_photo(context.bot, t.chat_id, charts.render_history_chart(t))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to notify chat %s", t.chat_id)


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error while processing update", exc_info=context.error)


async def _post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id=%s)", me.username, me.id)
    if application.job_queue is not None:
        application.job_queue.run_repeating(_poll_prices, interval=TRACK_INTERVAL_SECONDS, first=TRACK_INTERVAL_SECONDS)
        logger.info("Price tracking every %ss", TRACK_INTERVAL_SECONDS)


def build_application(token: str) -> Application:
    application = Application.builder().token(token).post_init(_post_init).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_start),
            MessageHandler(filters.Regex(f"^{re.escape(BTN_SEARCH)}$"), search_start),
        ],
        states={
            FROM: [
                CallbackQueryHandler(from_pick, pattern="^cf:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, from_text),
            ],
            TO: [
                CallbackQueryHandler(to_pick, pattern="^ct:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, to_text),
            ],
            PAX: [CallbackQueryHandler(pax_cb, pattern="^px:")],
            DATES: [CallbackQueryHandler(dates_cb, pattern="^cal:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("hot", hot))
    application.add_handler(CommandHandler("mytracks", mytracks))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_RANGE)}$"), range_shortcut))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_TRACK)}$"), track_shortcut))
    application.add_handler(CallbackQueryHandler(results_cb, pattern="^res:"))
    application.add_handler(CallbackQueryHandler(filters_cb, pattern="^flt:"))
    application.add_error_handler(_on_error)
    return application


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # keep bot token out of logs
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Export it (see .env.example) to run the live bot. "
            "The engine still works offline via `python -m avia_bot.demo`."
        )
    logger.info("Starting avia_bot in polling mode")
    build_application(token).run_polling()


if __name__ == "__main__":
    main()
