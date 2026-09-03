"""Async tests for the conversation handlers using mocked Update/Context."""

import asyncio
import datetime as dt
from unittest.mock import AsyncMock, MagicMock

from avia_bot import bot, geo
from avia_bot.flights import Filters, FlightService
from avia_bot.pricing import Passengers

DATE = dt.date(2026, 9, 17)


def _ctx():
    context = MagicMock()
    context.user_data = {}
    context.bot = AsyncMock()
    return context


def _msg_update(text="Москва", chat_id=1):
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = text
    update.effective_chat = MagicMock(id=chat_id)
    return update


def _cb_update(data, chat_id=1):
    update = MagicMock()
    query = AsyncMock()
    query.data = data
    query.message = MagicMock()
    query.message.chat_id = chat_id
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    update.message = None
    update.effective_chat = MagicMock(id=chat_id)
    return update, query


def test_search_start_asks_from():
    update, context = _msg_update(), _ctx()
    state = asyncio.run(bot.search_start(update, context))
    assert state == bot.FROM
    update.message.reply_text.assert_called()


def test_from_text_offers_cities():
    update, context = _msg_update("Москва"), _ctx()
    context.user_data["draft"] = {"pax": Passengers()}
    state = asyncio.run(bot.from_text(update, context))
    assert state == bot.FROM
    markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    labels = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("🇷🇺" in lb and "SVO" in lb for lb in labels)
    assert any("MOW" in lb for lb in labels)


def test_main_keyboard_stays_pretty_and_persistent():
    kb = bot._main_kb("ru")
    assert kb.is_persistent is True
    texts = [btn.text for row in kb.keyboard for btn in row]
    assert any("Мои алерты" in x for x in texts)
    assert any("Кабинет" in x for x in texts)
    assert any("Помощь" in x for x in texts)
    assert len(kb.keyboard) == 4 and all(len(row) == 2 for row in kb.keyboard)


def test_from_pick_then_to_pick_reach_pax():
    context = _ctx()
    context.user_data["draft"] = {"pax": Passengers()}

    u1, q1 = _cb_update("cf:MOW")
    assert asyncio.run(bot.from_pick(u1, context)) == bot.TO
    assert context.user_data["draft"]["o"].code == "MOW"

    u2, q2 = _cb_update("ct:LBD")
    assert asyncio.run(bot.to_pick(u2, context)) == bot.PAX
    assert context.user_data["draft"]["d"].code == "LBD"
    q2.edit_message_text.assert_awaited()


def test_pax_increment_and_go():
    context = _ctx()
    context.user_data["draft"] = {"o": geo.airport("MOW"), "d": geo.airport("LBD"), "pax": Passengers()}

    u, q = _cb_update("px:a:+")
    assert asyncio.run(bot.pax_cb(u, context)) == bot.PAX
    assert context.user_data["draft"]["pax"].adults == 2
    q.edit_message_text.assert_awaited()

    u2, q2 = _cb_update("px:go")
    assert asyncio.run(bot.pax_cb(u2, context)) == bot.DATES
    q2.edit_message_text.assert_awaited()


def test_calendar_roundtrip_and_quick_buttons():
    context = _ctx()
    context.user_data["draft"] = {
        "o": geo.airport("MOW"), "d": geo.airport("LBD"), "pax": Passengers(),
        "y": 2026, "m": 9, "dep": None, "ret": None, "roundtrip": False,
    }
    u, q = _cb_update("cal:trip:rt")
    assert asyncio.run(bot.dates_cb(u, context)) == bot.DATES
    assert context.user_data["draft"]["roundtrip"] is True

    u2, q2 = _cb_update("cal:plus:3")
    assert asyncio.run(bot.dates_cb(u2, context)) == bot.DATES
    assert context.user_data["draft"]["dep"] == dt.date.today() + dt.timedelta(days=3)

    u3, q3 = _cb_update("cal:clear")
    assert asyncio.run(bot.dates_cb(u3, context)) == bot.DATES
    assert context.user_data["draft"]["dep"] is None


def test_dates_pick_and_done_runs_search():
    context = _ctx()
    context.user_data["draft"] = {
        "o": geo.airport("MOW"), "d": geo.airport("LBD"), "pax": Passengers(),
        "y": 2026, "m": 9, "dep": None, "ret": None,
    }
    u, q = _cb_update("cal:day:2026-09-17")
    assert asyncio.run(bot.dates_cb(u, context)) == bot.DATES
    assert context.user_data["draft"]["dep"] == DATE

    u2, q2 = _cb_update("cal:done")
    state = asyncio.run(bot.dates_cb(u2, context))
    assert state == bot.ConversationHandler.END
    assert context.user_data["search"]["results"]


def _make_search(chat_id=1):
    svc = FlightService()
    results = svc.search("MOW", "LBD", DATE, tick=1000)
    return {
        "o_code": "MOW", "o_city": "Москва", "d_code": "LBD", "d_city": "Худжанд",
        "dep": DATE, "ret": None, "pax": Passengers(), "filters": Filters(),
        "results": results, "page": 0,
    }


def test_results_pagination():
    context = _ctx()
    context.user_data["search"] = _make_search()
    u, q = _cb_update("res:next")
    asyncio.run(bot.results_cb(u, context))
    assert context.user_data["search"]["page"] == 1
    q.edit_message_text.assert_awaited()


def test_filters_apply_rebuilds_results():
    context = _ctx()
    search = _make_search()
    search["filters"] = Filters(direct_only=True)
    context.user_data["search"] = search
    u, q = _cb_update("flt:apply")
    asyncio.run(bot.filters_cb(u, context))
    assert all(p.itinerary.is_direct for p in context.user_data["search"]["results"])


def test_language_callback_sets_language():
    context = _ctx()
    u, q = _cb_update("lng:uz")
    asyncio.run(bot.language_cb(u, context))
    assert context.user_data["lang"] == "uz"
    q.edit_message_text.assert_awaited()
    q.message.reply_text.assert_awaited()  # welcome resent in new language


def test_poll_prices_sends_drop(monkeypatch):
    svc = bot._service
    prices = {t: svc.cheapest_price("MOW", "LBD", DATE, tick=t) for t in range(0, 60)}
    high = next(t for t in range(0, 59) if prices[t + 1] < prices[t])
    low = high + 1
    bot._tracker.add(555, "MOW", "LBD", DATE, tick=high)
    monkeypatch.setattr(bot, "_now_tick", lambda: low)

    context = _ctx()
    asyncio.run(bot._poll_prices(context))
    context.bot.send_message.assert_awaited()
    assert "Цена упала" in context.bot.send_message.call_args.args[1]
