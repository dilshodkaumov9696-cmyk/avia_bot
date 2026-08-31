"""Offline demo of the guided-search engine (no Telegram token needed).

    python -m avia_bot.demo
    python -m avia_bot.demo --charts-dir DIR

Walks the same steps the bot's conversation does — city lookup, passengers,
date, search, results, filters, flexible dates, tracking — using the pure engine.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from typing import Optional

from . import charts, geo, pricing, responses
from .flights import Filters, FlightService
from .pricing import Passengers
from .tracking import PriceTracker

TICK = 1000
CHAT = 424242
DEP = _dt.date(2026, 9, 17)


def _p(title: str) -> None:
    print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60)


def _show(text: str) -> None:
    for line in responses.render_plain(text).splitlines():
        print("   " + line)


def run(charts_dir: Optional[str] = None) -> None:
    service = FlightService()
    tracker = PriceTracker(service)

    _p("Шаг 1. Город откуда")
    print("user: Москва")
    for a in geo.search_cities("Москва"):
        print("   [", a.option_text, "]")
    origin = geo.airport("MOW")
    print("выбрано:", origin.option_text)

    _p("Шаг 2. Город куда")
    print("user: Худжанд")
    for a in geo.search_cities("Худжанд"):
        print("   [", a.option_text, "]")
    dest = geo.airport("LBD")
    print("выбрано:", dest.option_text)

    _p("Шаг 3. Пассажиры и класс")
    pax = Passengers(adults=2, children=1, infants=0, cabin="economy")
    print("выбрано:", pax.summary)

    _p(f"Шаг 4. Дата вылета: {responses.fmt_date(DEP)}")

    _p("Результаты поиска (Москва → Худжанд)")
    results = service.search(origin.code, dest.code, DEP, pax=pax, tick=TICK)
    for i, offer in enumerate(results):
        print(f"\n--- Вариант {i + 1} из {len(results)} ---")
        _show(responses.format_offer(offer))
        print("   [", responses.offer_buy_label(offer), "]")

    _p("Фильтр: только прямые")
    direct = service.search(origin.code, dest.code, DEP, pax=pax, tick=TICK, filters=Filters(direct_only=True))
    print(f"прямых рейсов: {len(direct)} (из {len(results)})")

    _p("Гибкие даты ±3 дня")
    flex = service.flexible_dates(origin.code, dest.code, DEP, pax=pax, tick=TICK)
    for d, price in flex:
        print(f"   {responses.fmt_date(d)}: {pricing.format_money(price)}")
    _show(responses.flexible_text(flex, DEP) or "")

    _p("Поиск по диапазону")
    points = service.search_range(origin.code, dest.code, DEP, DEP + _dt.timedelta(days=6), pax=pax, tick=TICK)
    _show(responses.range_text(origin.city, dest.city, points, pax))

    _p("Отслеживание цены (симуляция падения)")
    prices = {t: service.cheapest_price(origin.code, dest.code, DEP, pax=pax, tick=t) for t in range(0, 60)}
    start = next((t for t in range(0, 59) if prices[t + 1] < prices[t]), 0)
    _, seed = tracker.add(CHAT, origin.code, dest.code, DEP, pax=pax, tick=start)
    print(f"Проверка #1: {pricing.format_money(seed)}")
    for off in range(1, 6):
        tick = start + off
        drops = tracker.poll(tick)
        track = tracker.list_for(CHAT)[0]
        note = ""
        for e in drops:
            note = "   " + responses.render_plain(
                responses.drop_text(origin.city, dest.city, DEP, e.previous_price, e.new_price, e.drop_pct)
            ).replace("\n", " ")
        print(f"Проверка #{off + 1} (tick {tick}): {pricing.format_money(track.last_price)}{note}")

    _p("Горящие билеты")
    _show(responses.hot_text(service.cheapest_deals(tick=TICK)))

    if charts_dir:
        os.makedirs(charts_dir, exist_ok=True)
        with open(os.path.join(charts_dir, "range_chart.png"), "wb") as fh:
            fh.write(charts.render_range_chart(origin.city, dest.city, points))
        track = tracker.list_for(CHAT)[0]
        with open(os.path.join(charts_dir, "history_chart.png"), "wb") as fh:
            fh.write(charts.render_history_chart(track))
        print(f"\nSaved charts to {charts_dir}")

    print("\n" + "=" * 60)
    print("Демо завершено — весь сценарий как у AviaGram отработал.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="avia_bot offline demo")
    parser.add_argument("--charts-dir", default=None)
    args = parser.parse_args()
    run(charts_dir=args.charts_dir)


if __name__ == "__main__":
    main()
