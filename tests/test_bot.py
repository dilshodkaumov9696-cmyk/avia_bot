"""Async tests for the Telegram handler layer using mocked Update/Context.

These drive the real handlers in :mod:`avia_bot.bot` (keyboards, the chart
callback and the price-drop job) without a network or a bot token.
"""

import asyncio
import datetime as dt
from unittest.mock import AsyncMock, MagicMock

from avia_bot import bot


def _make_update(args=None, chat_id=1):
    update = MagicMock()
    update.message = AsyncMock()
    update.effective_chat = MagicMock(id=chat_id)
    context = MagicMock()
    context.args = args or []
    context.bot = AsyncMock()
    return update, context


def test_search_handler_attaches_track_button():
    update, context = _make_update(["London", "Paris", "2026-09-05"])
    asyncio.run(bot.search(update, context))
    update.message.reply_text.assert_called_once()
    markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    assert markup is not None
    assert "trk|LON|PAR|2026-09-05" in markup.inline_keyboard[0][0].callback_data


def test_range_handler_attaches_chart_button():
    update, context = _make_update(["LON", "NYC", "2026-09-01", "2026-09-05"])
    asyncio.run(bot.range_search(update, context))
    markup = update.message.reply_text.call_args.kwargs["reply_markup"]
    assert markup is not None
    assert markup.inline_keyboard[0][0].callback_data.startswith("rc|LON|NYC|")


def test_callback_range_chart_sends_photo():
    update, context = _make_update(chat_id=55)
    query = AsyncMock()
    query.data = "rc|LON|NYC|2026-09-01|2026-09-05|1"
    query.message = MagicMock()
    query.message.chat_id = 55
    update.callback_query = query
    asyncio.run(bot.on_callback(update, context))
    query.answer.assert_awaited()
    context.bot.send_photo.assert_awaited_once()


def test_track_and_mytracks_handlers():
    update, context = _make_update(["LON", "PAR", "2026-09-05"], chat_id=777)
    asyncio.run(bot.track(update, context))
    update.message.reply_text.assert_called()
    assert bot._tracker.list_for(777)

    update2, context2 = _make_update(chat_id=777)
    asyncio.run(bot.mytracks(update2, context2))
    text = update2.message.reply_text.call_args.args[0]
    assert "LON \u2192 PAR" in text


def test_poll_prices_job_sends_drop_notification(monkeypatch):
    service = bot._service
    date = dt.date(2026, 9, 5)
    prices = {t: service.cheapest("LON", "PAR", date, tick=t).price_total for t in range(0, 60)}
    high = next(t for t in range(0, 59) if prices[t + 1] < prices[t])
    low = high + 1

    bot._tracker.add(9090, "LON", "PAR", date, tick=high)
    monkeypatch.setattr(bot, "_now_tick", lambda: low)

    context = MagicMock()
    context.bot = AsyncMock()
    asyncio.run(bot._poll_prices(context))

    context.bot.send_message.assert_awaited()
    sent_text = context.bot.send_message.call_args.args[1]
    assert "\u0426\u0435\u043d\u0430 \u0443\u043f\u0430\u043b\u0430" in sent_text  # "Price dropped"
