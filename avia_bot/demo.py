"""Offline demo of the multilingual guided-search engine (no token needed).

    python -m avia_bot.demo
    python -m avia_bot.demo --charts-dir DIR
    python -m avia_bot.demo --lang uz     # ru (default) / tg / uz / ky / kk / tk / az / be / en

Walks the same steps the bot's conversation does and prints result cards in the
chosen language with its currency.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
from typing import Optional

from . import charts, geo, i18n, pricing, responses, tickets
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


def _run_lang(service, tracker, lang: str, charts_dir: Optional[str]) -> None:
    origin, dest = geo.airport("MOW"), geo.airport("LBD")
    pax = Passengers(adults=2, children=1, cabin="economy")

    _p(f"[{i18n.language_label(lang)} · {i18n.currency_of(lang)}]  Результаты (Москва → Худжанд)")
    results = service.search(origin.code, dest.code, DEP, pax=pax, tick=TICK)
    for offer in results[:3]:
        print()
        _show(responses.format_offer(lang, offer))
        print("   [", responses.offer_buy_label(lang, offer), "]")

    _p(f"[{lang}] Диапазон / Range")
    points = service.search_range(origin.code, dest.code, DEP, DEP + _dt.timedelta(days=6), pax=pax, tick=TICK)
    _show(responses.range_text(lang, origin.display_city, dest.display_city, points, pax))

    if charts_dir:
        os.makedirs(charts_dir, exist_ok=True)
        with open(os.path.join(charts_dir, f"range_{lang}.png"), "wb") as fh:
            fh.write(charts.render_range_chart(origin.display_city, dest.display_city, points))
        offer = results[0]
        with open(os.path.join(charts_dir, f"ticket_{lang}.png"), "wb") as fh:
            fh.write(tickets.render_ticket(lang, offer))


def run(charts_dir: Optional[str] = None, langs=("ru", "uz", "en")) -> None:
    service = FlightService()
    tracker = PriceTracker(service)

    _p("Шаг 1–4. Города, пассажиры, дата (как в боте)")
    print("Откуда: Москва →", [a.option_text for a in geo.search_cities("Москва")])
    print("Куда:   Худжанд →", [a.code for a in geo.search_cities("Худжанд")])
    print("IATA:   LED →", [a.code for a in geo.search_cities("LED")])
    print("Страна: Япония →", [a.code for a in geo.search_cities("Япония")][:5])
    print("Пассажиры:", responses.pax_summary("ru", Passengers(2, 1, cabin="economy")))
    print("Дата:", responses.render_plain(responses.dates_prompt("ru", DEP, None)))

    for lang in langs:
        _run_lang(service, tracker, lang, charts_dir)

    _p("Фильтр «только прямые» (ru)")
    direct = service.search("MOW", "LBD", DEP, pax=Passengers(2, 1), tick=TICK, filters=Filters(direct_only=True))
    print(f"прямых: {len(direct)}")

    _p("Отслеживание цены (ru, симуляция падения)")
    prices = {tk: service.cheapest_price("MOW", "LBD", DEP, pax=Passengers(2, 1), tick=tk) for tk in range(0, 60)}
    start = next((tk for tk in range(0, 59) if prices[tk + 1] < prices[tk]), 0)
    tracker.add(CHAT, "MOW", "LBD", DEP, pax=Passengers(2, 1), tick=start, lang="ru")
    for off in range(1, 6):
        tk = start + off
        drops = tracker.poll(tk)
        track = tracker.list_for(CHAT)[0]
        note = ""
        for e in drops:
            note = "   " + responses.render_plain(
                responses.drop_text("ru", "Москва", "Худжанд", DEP, e.previous_price, e.new_price, e.drop_pct)
            ).replace("\n", " ")
        print(f"Проверка #{off + 1}: {pricing.format_money(track.last_price)} TJS{note}")

    _p("Языки и валюты")
    for code in i18n.LANGS:
        print(f"   {i18n.language_label(code):<22} → {i18n.currency_of(code):<4} "
              f"(пример 3000 TJS = {i18n.money(code, 3000)})")

    print("\n" + "=" * 60)
    print("Демо завершено — мультиязычность и валюты работают.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="avia_bot offline demo")
    parser.add_argument("--charts-dir", default=None)
    parser.add_argument("--lang", default=None, help="show only this language")
    args = parser.parse_args()
    langs = (args.lang,) if args.lang else ("ru", "uz", "en")
    run(charts_dir=args.charts_dir, langs=langs)


if __name__ == "__main__":
    main()
