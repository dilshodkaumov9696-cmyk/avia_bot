"""Telegram bot: AviaGram-style guided flight search, multilingual.

Flow (ConversationHandler): city from → pick airport → city to → pick airport →
passengers & cabin → calendar → animated search → paginated result cards with
filters, price advice, flexible dates, buy links and price tracking.

UI is localized via :mod:`avia_bot.i18n` (per-user language + currency). Runs live
with ``TELEGRAM_BOT_TOKEN``; all logic is covered offline by the demo and tests.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import io
import logging
import os
import re
from typing import Optional

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    InputMediaPhoto,
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

from . import calendar_ui, charts, geo, i18n, pricing, responses, tickets
from .flights import Filters, FlightService
from .i18n import t
from .pricing import Passengers
from .search_flow import adjust_pax, cycle_cabin, paginate
from .tracking import PriceTracker

logger = logging.getLogger("avia_bot")

TRACK_INTERVAL_SECONDS = int(os.environ.get("AVIA_TRACK_INTERVAL_SECONDS", str(pricing.DEFAULT_INTERVAL_SECONDS)))

_service = FlightService()
_tracker = PriceTracker(_service)

FROM, TO, PAX, DATES = range(4)


def _lang(context) -> str:
    return i18n.normalize(context.user_data.get("lang")) if context.user_data else i18n.DEFAULT_LANG


def _any_lang_regex(key: str) -> str:
    variants = {i18n.t(l, key) for l in i18n.LANGS}
    return "^(" + "|".join(re.escape(v) for v in variants) + ")$"


# --- keyboards -------------------------------------------------------------


def _main_kb(lang: str, placeholder: Optional[str] = None) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t(lang, "kb_search")), KeyboardButton(t(lang, "kb_discover"))],
            [KeyboardButton(t(lang, "kb_alerts")), KeyboardButton(t(lang, "kb_calendar"))],
            [KeyboardButton(t(lang, "kb_cabinet")), KeyboardButton(t(lang, "kb_premium"))],
            [KeyboardButton(t(lang, "kb_lang")), KeyboardButton(t(lang, "kb_help"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholder or i18n.placeholder_search(lang),
    )


def _lang_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for code, label in i18n.LANG_META.items():
        row.append(InlineKeyboardButton(label, callback_data=f"lng:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _city_kb(options, prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(a.option_text, callback_data=f"{prefix}:{a.code}")] for a in options]
    )


def _pax_kb(lang: str, pax: Passengers) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("−", callback_data="px:a:-"),
         InlineKeyboardButton(f"{t(lang, 'adults')}  {pax.adults}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:a:+")],
        [InlineKeyboardButton("−", callback_data="px:c:-"),
         InlineKeyboardButton(f"{t(lang, 'children')}  {pax.children}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:c:+")],
        [InlineKeyboardButton("−", callback_data="px:i:-"),
         InlineKeyboardButton(f"{t(lang, 'infants')}  {pax.infants}", callback_data="px:x"),
         InlineKeyboardButton("+", callback_data="px:i:+")],
        [InlineKeyboardButton("‹", callback_data="px:cab:-"),
         InlineKeyboardButton(responses.cabin_label(lang, pax.cabin), callback_data="px:x"),
         InlineKeyboardButton("›", callback_data="px:cab:+")],
        [InlineKeyboardButton(t(lang, "btn_go"), callback_data="px:go")],
    ])


def _cal_labels(lang: str) -> calendar_ui.Labels:
    return calendar_ui.Labels(
        ow=t(lang, "cal_ow"),
        rt=t(lang, "cal_rt"),
        today=t(lang, "cal_today"),
        tomorrow=t(lang, "cal_tomorrow"),
        plus3=t(lang, "cal_plus3"),
        plus7=t(lang, "cal_plus7"),
        clear=t(lang, "cal_clear"),
        done=t(lang, "cal_done"),
        weekdays=tuple(i18n.weekdays(lang)),
        months=tuple(i18n.months_cal(lang)),
    )


def _calendar_kb(lang: str, draft: dict) -> InlineKeyboardMarkup:
    dep, ret = draft.get("dep"), draft.get("ret")
    done = t(lang, "cal_find", d=i18n.fmt_date(lang, dep)) if dep else t(lang, "cal_pick")
    rows = calendar_ui.build_calendar(
        draft["y"], draft["m"],
        roundtrip=bool(draft.get("roundtrip")),
        dep=dep, ret=ret,
        labels=_cal_labels(lang),
        done_label=done,
    )
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in rows]
    )


def _results_kb(lang: str, search: dict) -> InlineKeyboardMarkup:
    results, page, pax = search["results"], search["page"], search["pax"]
    offer = results[page]
    buy_url = responses.aviasales_url(search["o_code"], search["d_code"], search["dep"],
                                      back_date=search.get("ret"), passengers=max(1, pax.adults + pax.children))
    n = len(results)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("‹", callback_data="res:prev"),
         InlineKeyboardButton(f"{page + 1} / {n}", callback_data="res:x"),
         InlineKeyboardButton("›", callback_data="res:next")],
        [InlineKeyboardButton(responses.offer_buy_label(lang, offer), url=buy_url)],
        [InlineKeyboardButton(t(lang, "btn_track"), callback_data="res:track"),
         InlineKeyboardButton(t(lang, "btn_new_search"), callback_data="res:new")],
        [InlineKeyboardButton(t(lang, "btn_flex"), callback_data="res:flex"),
         InlineKeyboardButton(t(lang, "btn_filters"), callback_data="res:filters")],
    ])


def _filters_kb(lang: str, f: Filters) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if f.direct_only else '⬜'} {t(lang, 'flt_direct')}", callback_data="flt:direct")],
        [InlineKeyboardButton(f"{'✅' if f.with_baggage else '⬜'} {t(lang, 'flt_bag')}", callback_data="flt:bag")],
        [InlineKeyboardButton(t(lang, "flt_apply"), callback_data="flt:apply"),
         InlineKeyboardButton(t(lang, "flt_reset"), callback_data="flt:reset")],
    ])


# --- send helpers ----------------------------------------------------------


async def _reply(update: Update, text: str, markup=None) -> None:
    if update.message is not None:
        await update.message.reply_text(responses.render_html(text), parse_mode=ParseMode.HTML, reply_markup=markup)


def _is_photo_message(message) -> bool:
    return bool(getattr(message, "photo", None))


async def _edit(query, text: str, markup=None) -> None:
    html = responses.render_html(text)
    message = query.message
    if _is_photo_message(message):
        if message is not None:
            try:
                await message.delete()
            except Exception:  # noqa: BLE001
                logger.debug("Could not delete photo message before text replace")
            chat = getattr(message, "chat", None)
            if chat is not None:
                await chat.send_message(html, parse_mode=ParseMode.HTML, reply_markup=markup)
                return
    await query.edit_message_text(html, parse_mode=ParseMode.HTML, reply_markup=markup)


async def _send_photo(bot, chat_id: int, png: bytes, caption: Optional[str] = None) -> None:
    await bot.send_photo(chat_id=chat_id, photo=InputFile(io.BytesIO(png), filename="chart.png"),
                         caption=responses.render_html(caption) if caption else None, parse_mode=ParseMode.HTML)


# --- simple commands -------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context)
    await _reply(update, responses.welcome(lang), _main_kb(lang))
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, responses.help_text(_lang(context)), _main_kb(_lang(context)))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, t(_lang(context), "choose_language"), _lang_kb())


async def language_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code = i18n.normalize(query.data.split(":")[1])
    context.user_data["lang"] = code
    await _edit(query, t(code, "language_set", name=i18n.language_label(code), cur=i18n.currency_of(code)))
    if query.message is not None:
        await query.message.reply_text(responses.render_html(responses.welcome(code)),
                                        parse_mode=ParseMode.HTML, reply_markup=_main_kb(code))


async def hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context)
    await _reply(update, responses.hot_text(lang, _service.cheapest_deals(tick=_now_tick())), _main_kb(lang))


async def mytracks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    lang = _lang(context)
    await _reply(update, responses.mytracks_text(lang, _tracker.list_for(update.effective_chat.id)),
                 _main_kb(lang))


def _now_tick() -> int:
    return pricing.current_tick(TRACK_INTERVAL_SECONDS)


# --- guided search conversation -------------------------------------------


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang(context)
    context.user_data["draft"] = {"pax": Passengers(), "roundtrip": False}
    text = t(lang, "ask_from")
    if update.message is not None:
        await _reply(update, text, _main_kb(lang))
    elif update.callback_query is not None:
        await update.callback_query.answer()
        await _edit(update.callback_query, text)
    return FROM


async def _city_step(update, context, prefix):
    lang = _lang(context)
    options = geo.search_cities(update.message.text)
    if not options:
        await _reply(update, t(lang, "city_not_found"), _main_kb(lang))
        return
    text = responses.airport_choice_text(
        lang, update.message.text, len(options), departing=prefix == "cf")
    await _reply(update, text, _city_kb(options, prefix))


async def from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _city_step(update, context, "cf")
    return FROM


async def from_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["draft"]["o"] = geo.airport(query.data.split(":")[1])
    lang = _lang(context)
    await _edit(query, f"{responses.route_line_from(context.user_data['draft']['o'])}\n\n{t(lang, 'ask_to')}")
    return TO


async def to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _city_step(update, context, "ct")
    return TO


async def to_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = context.user_data["draft"]
    draft["d"] = geo.airport(query.data.split(":")[1])
    lang = _lang(context)
    text = responses.route_line(draft["o"], draft["d"]) + "\n\n" + responses.pax_card(lang, draft["pax"])
    await _edit(query, text, _pax_kb(lang, draft["pax"]))
    return PAX


async def pax_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = _lang(context)
    draft = context.user_data["draft"]
    pax: Passengers = draft["pax"]
    data = query.data

    if data == "px:x":
        return PAX
    if data == "px:go":
        today = _dt.date.today()
        draft.update({"y": today.year, "m": today.month, "dep": None, "ret": None,
                      "roundtrip": draft.get("roundtrip", False)})
        await _edit(query, _dates_text(lang, draft), _calendar_kb(lang, draft))
        return DATES

    field = {"a": "adults", "c": "children", "i": "infants"}.get(data.split(":")[1])
    if field:
        pax = adjust_pax(pax, field, 1 if data.endswith("+") else -1)
    elif data.startswith("px:cab"):
        pax = cycle_cabin(pax, 1 if data.endswith("+") else -1)
    draft["pax"] = pax
    route = ""
    if draft.get("o") and draft.get("d"):
        route = responses.route_line(draft["o"], draft["d"]) + "\n\n"
    await _edit(query, route + responses.pax_card(lang, pax), _pax_kb(lang, pax))
    return PAX


def _dates_text(lang: str, draft: dict) -> str:
    return responses.dates_prompt(
        lang, draft.get("dep"), draft.get("ret"), bool(draft.get("roundtrip")),
        origin=draft.get("o"), destination=draft.get("d"),
    )


async def dates_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = _lang(context)
    draft = context.user_data["draft"]
    data = query.data

    if data == "cal:done" and not draft.get("dep"):
        await query.answer(t(lang, "pick_date_alert"), show_alert=True)
        return DATES
    await query.answer()

    if data == "cal:x":
        return DATES
    if data in ("cal:trip:ow", "cal:trip:rt"):
        draft["roundtrip"] = data.endswith("rt")
        if not draft["roundtrip"]:
            draft["ret"] = None
        await _edit(query, _dates_text(lang, draft), _calendar_kb(lang, draft))
        return DATES
    if data == "cal:clear":
        draft["dep"] = draft["ret"] = None
        await _edit(query, _dates_text(lang, draft), _calendar_kb(lang, draft))
        return DATES
    if data in ("cal:today", "cal:tomorrow") or data.startswith("cal:plus:"):
        if data == "cal:today":
            delta = 0
        elif data == "cal:tomorrow":
            delta = 1
        else:
            delta = int(data.split(":")[2])
        day = _dt.date.today() + _dt.timedelta(days=delta)
        draft["dep"] = day
        if not draft.get("roundtrip"):
            draft["ret"] = None
        draft["y"], draft["m"] = day.year, day.month
        await _edit(query, _dates_text(lang, draft), _calendar_kb(lang, draft))
        return DATES
    if data.startswith("cal:nav:"):
        y, m = map(int, data.split(":")[2].split("-"))
        draft["y"], draft["m"] = y, m
        await query.edit_message_reply_markup(_calendar_kb(lang, draft))
        return DATES
    if data.startswith("cal:day:"):
        day = _dt.date.fromisoformat(data.split(":", 2)[2])
        if not draft.get("roundtrip"):
            draft["dep"], draft["ret"] = day, None
        elif not draft.get("dep") or (draft.get("dep") and draft.get("ret")):
            draft["dep"], draft["ret"] = day, None
        elif day < draft["dep"]:
            draft["dep"] = day
        else:
            draft["ret"] = day
        draft["y"], draft["m"] = day.year, day.month
        await _edit(query, _dates_text(lang, draft), _calendar_kb(lang, draft))
        return DATES
    if data == "cal:done":
        if not draft.get("dep"):
            await query.answer(t(lang, "pick_date_alert"), show_alert=True)
            return DATES
        return await _run_search(update, context)
    return DATES


async def _run_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang = _lang(context)
    draft = context.user_data["draft"]
    for step in range(1, 4):
        await _edit(query, responses.searching_bar(lang, step))
        await asyncio.sleep(0.4)

    pax: Passengers = draft["pax"]
    results = _service.search(draft["o"].code, draft["d"].code, draft["dep"], pax=pax, tick=_now_tick())
    back = []
    if draft.get("ret"):
        back = _service.search(draft["d"].code, draft["o"].code, draft["ret"], pax=pax, tick=_now_tick())
    context.user_data["search"] = {
        "o_code": draft["o"].code, "o_city": draft["o"].display_city,
        "d_code": draft["d"].code, "d_city": draft["d"].display_city,
        "dep": draft["dep"], "ret": draft.get("ret"), "pax": pax,
        "filters": Filters(), "results": results, "back": back, "page": 0,
    }
    await _show_results(query, context, edit=True)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang(context)
    await _reply(update, t(lang, "cancel"), _main_kb(lang))
    return ConversationHandler.END


# --- results (post-conversation) ------------------------------------------


def _results_text(lang: str, search: dict) -> str:
    results = search["results"]
    if not results:
        return responses.no_results_text(lang, search["filters"].active)
    page = search["page"]
    offer = results[page]
    back_list = search.get("back") or []
    back = back_list[min(page, len(back_list) - 1)] if back_list else None
    header = responses.results_header(lang, search["o_city"], search["d_city"], search["dep"],
                                      search["pax"], page, len(results), search["filters"])
    body = responses.format_offer(lang, offer, back=back)
    trend = pricing.price_trend(pricing.route_key(offer.itinerary.origin, offer.itinerary.destination), offer.tick)
    advice = responses.price_advice_text(lang, trend)
    parts = [p for p in (header, body, advice) if p]
    return "\n\n".join(parts)


async def _show_results(query, context, edit: bool):
    lang = _lang(context)
    search = context.user_data["search"]
    text = _results_text(lang, search)
    html = responses.render_html(text)
    if len(html) > 1024:
        html = html[:1020] + "…"
    if not search["results"]:
        if edit:
            await _edit(query, text)
        else:
            await query.message.reply_text(html, parse_mode=ParseMode.HTML)
        return

    page = search["page"]
    offer = search["results"][page]
    back_list = search.get("back") or []
    back = back_list[min(page, len(back_list) - 1)] if back_list else None
    png = tickets.render_ticket(lang, offer, back=back)
    markup = _results_kb(lang, search)
    message = query.message

    if edit and _is_photo_message(message):
        await query.edit_message_media(
            InputMediaPhoto(media=InputFile(io.BytesIO(png), filename="ticket.png"),
                            caption=html, parse_mode=ParseMode.HTML),
            reply_markup=markup,
        )
        return

    if edit and message is not None:
        try:
            await message.delete()
        except Exception:  # noqa: BLE001
            logger.debug("Could not delete search-progress message")
        await context.bot.send_photo(
            chat_id=message.chat_id,
            photo=InputFile(io.BytesIO(png), filename="ticket.png"),
            caption=html,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
        return

    await message.reply_photo(
        photo=InputFile(io.BytesIO(png), filename="ticket.png"),
        caption=html,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


async def results_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = _lang(context)
    search = context.user_data.get("search")
    if not search:
        await query.answer(t(lang, "start_search_first"), show_alert=True)
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
        await _edit(query, t(lang, "flt_title"), _filters_kb(lang, search["filters"]))
    elif data == "res:flex":
        await _send_flex(query, context)
    elif data == "res:track":
        await _add_track_from_search(query.message.chat_id, context)
        s = search
        await query.message.reply_text(
            responses.render_html(responses.track_added_text(
                lang, s["o_city"], s["d_city"], s["dep"], s["pax"], s["results"][s["page"]].price_total)),
            parse_mode=ParseMode.HTML)


async def filters_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = _lang(context)
    search = context.user_data.get("search")
    if not search:
        return
    f: Filters = search["filters"]
    data = query.data
    if data == "flt:direct":
        f.direct_only = not f.direct_only
        await query.edit_message_reply_markup(_filters_kb(lang, f))
    elif data == "flt:bag":
        f.with_baggage = not f.with_baggage
        await query.edit_message_reply_markup(_filters_kb(lang, f))
    elif data in ("flt:apply", "flt:reset"):
        if data == "flt:reset":
            search["filters"] = Filters()
        search["results"] = _service.search(search["o_code"], search["d_code"], search["dep"],
                                             pax=search["pax"], tick=_now_tick(), filters=search["filters"])
        search["page"] = 0
        await _show_results(query, context, edit=True)


async def _send_flex(query, context):
    lang = _lang(context)
    search = context.user_data["search"]
    points = _service.flexible_dates(search["o_code"], search["d_code"], search["dep"],
                                     pax=search["pax"], tick=_now_tick())
    text = responses.flexible_text(lang, points, search["dep"]) or t(lang, "flex_none")
    await query.message.reply_text(responses.render_html(text), parse_mode=ParseMode.HTML)
    if points:
        png = charts.render_range_chart(search["o_city"], search["d_city"], points)
        await _send_photo(context.bot, query.message.chat_id, png)


async def _add_track_from_search(chat_id: int, context) -> Optional[int]:
    search = context.user_data.get("search")
    if not search:
        return None
    _, price = _tracker.add(chat_id, search["o_code"], search["d_code"], search["dep"],
                            pax=search["pax"], tick=_now_tick(), lang=_lang(context))
    return price


# --- reply-keyboard shortcuts ---------------------------------------------


async def range_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang(context)
    search = context.user_data.get("search")
    if not search:
        await _reply(update, t(lang, "start_search_first"), _main_kb(lang))
        return
    start = search["dep"] - _dt.timedelta(days=3)
    end = search["dep"] + _dt.timedelta(days=7)
    points = _service.search_range(search["o_code"], search["d_code"], start, end, pax=search["pax"], tick=_now_tick())
    await _reply(update, responses.range_text(lang, search["o_city"], search["d_city"], points, search["pax"]),
                 _main_kb(lang))
    if points and update.effective_chat is not None:
        await _send_photo(context.bot, update.effective_chat.id,
                          charts.render_range_chart(search["o_city"], search["d_city"], points))


async def discover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .flights import DISCOVER_DESTS
    lang = _lang(context)
    origin, city = "MOW", "Москва"
    search = context.user_data.get("search")
    draft = context.user_data.get("draft") or {}
    if search:
        origin, city = search["o_code"], search["o_city"]
    elif draft.get("o") is not None:
        origin, city = draft["o"].code, draft["o"].display_city
    date = _dt.date.today() + _dt.timedelta(days=21)
    deals = []
    for dest in DISCOVER_DESTS:
        if dest == origin:
            continue
        if not geo.airport(dest) and dest not in geo.resolve_airports(dest):
            continue
        offers = _service.search(origin, dest, date, tick=_now_tick(), limit=1)
        if offers:
            deals.append(offers[0])
    deals.sort(key=lambda p: p.price_total)
    await _reply(update, responses.discover_text(lang, city, deals[:8]), _main_kb(lang))


async def cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _lang(context)
    n = 0
    if update.effective_chat is not None:
        n = len(_tracker.list_for(update.effective_chat.id))
    await _reply(update, responses.cabinet_text(lang, n), _main_kb(lang))


async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply(update, responses.premium_text(_lang(context)), _main_kb(_lang(context)))


# --- price-tracking job ----------------------------------------------------


async def _poll_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    for event in _tracker.poll(_now_tick()):
        tr = event.track
        o_city = geo.city_of(tr.origin) or tr.origin
        d_city = geo.city_of(tr.destination) or tr.destination
        text = responses.drop_text(tr.lang, o_city, d_city, tr.date, event.previous_price, event.new_price, event.drop_pct)
        try:
            await context.bot.send_message(tr.chat_id, responses.render_html(text), parse_mode=ParseMode.HTML)
            if len(tr.history) >= 2:
                await _send_photo(context.bot, tr.chat_id, charts.render_history_chart(tr))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to notify chat %s", tr.chat_id)


async def _on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error while processing update", exc_info=context.error)


async def _post_init(application: Application) -> None:
    me = await application.bot.get_me()
    logger.info("Connected to Telegram as @%s (id=%s)", me.username, me.id)
    await application.bot.set_my_commands([
        BotCommand("start", "Главное меню"),
        BotCommand("search", "Найти билеты"),
        BotCommand("discover", "Куда улететь дешево"),
        BotCommand("alerts", "Мои алерты"),
        BotCommand("calendar", "Календарь цен"),
        BotCommand("cabinet", "Кабинет"),
        BotCommand("premium", "Подписка"),
        BotCommand("language", "Язык"),
        BotCommand("help", "Помощь"),
        BotCommand("cancel", "Отмена"),
    ])
    if application.job_queue is not None:
        application.job_queue.run_repeating(_poll_prices, interval=TRACK_INTERVAL_SECONDS, first=TRACK_INTERVAL_SECONDS)
        logger.info("Price tracking every %ss", TRACK_INTERVAL_SECONDS)


def build_application(token: str) -> Application:
    application = Application.builder().token(token).post_init(_post_init).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_start),
            MessageHandler(filters.Regex(_any_lang_regex("kb_search")), search_start),
            CallbackQueryHandler(search_start, pattern="^res:new$"),
        ],
        states={
            FROM: [CallbackQueryHandler(from_pick, pattern="^cf:"),
                   MessageHandler(filters.TEXT & ~filters.COMMAND, from_text)],
            TO: [CallbackQueryHandler(to_pick, pattern="^ct:"),
                 MessageHandler(filters.TEXT & ~filters.COMMAND, to_text)],
            PAX: [CallbackQueryHandler(pax_cb, pattern="^px:")],
            DATES: [CallbackQueryHandler(dates_cb, pattern="^cal:")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            MessageHandler(filters.Regex(_any_lang_regex("kb_help")), help_command),
            MessageHandler(filters.Regex(_any_lang_regex("kb_lang")), language_command),
            MessageHandler(filters.Regex(_any_lang_regex("kb_discover")), discover),
            MessageHandler(filters.Regex(_any_lang_regex("kb_alerts")), mytracks),
            MessageHandler(filters.Regex(_any_lang_regex("kb_calendar")), range_shortcut),
            MessageHandler(filters.Regex(_any_lang_regex("kb_cabinet")), cabinet),
            MessageHandler(filters.Regex(_any_lang_regex("kb_premium")), premium),
        ],
        allow_reentry=True,
    )

    application.add_handler(conv)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("hot", hot))
    application.add_handler(CommandHandler("discover", discover))
    application.add_handler(CommandHandler("alerts", mytracks))
    application.add_handler(CommandHandler("mytracks", mytracks))
    application.add_handler(CommandHandler("calendar", range_shortcut))
    application.add_handler(CommandHandler("cabinet", cabinet))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_discover")), discover))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_alerts")), mytracks))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_calendar")), range_shortcut))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_cabinet")), cabinet))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_premium")), premium))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_help")), help_command))
    application.add_handler(MessageHandler(filters.Regex(_any_lang_regex("kb_lang")), language_command))
    application.add_handler(CallbackQueryHandler(language_cb, pattern="^lng:"))
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
