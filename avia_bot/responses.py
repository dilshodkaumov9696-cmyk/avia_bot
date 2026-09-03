"""Language-aware reply builders shared by the bot and the offline demo.

Ticket cards are receipts: price, cities with flags, times, airline.
Markup is ``*bold*`` / `` `code` ``, rendered to Telegram-safe HTML by
:func:`render_html`.
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re
from typing import Optional, Sequence, Tuple

from . import airlines, geo, i18n, pricing
from .flights import Filters, Priced, fmt_duration
from .geo import Airport
from .i18n import fmt_date, fmt_date_short, fmt_time, money, t

_BOLD = _re.compile(r"\*(.+?)\*", _re.S)
_CODE = _re.compile(r"`(.+?)`", _re.S)


def render_html(text: str) -> str:
    escaped = _html.escape(text, quote=False)
    escaped = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)
    return escaped


def render_plain(text: str) -> str:
    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _CODE.sub(lambda m: m.group(1), text)
    return text


def aviasales_url(origin: str, destination: str, out_date: _dt.date,
                  back_date: Optional[_dt.date] = None, passengers: int = 1) -> str:
    def ddmm(d: _dt.date) -> str:
        return f"{d.day:02d}{d.month:02d}"

    url = f"https://www.aviasales.com/search/{origin}{ddmm(out_date)}{destination}"
    if back_date is not None:
        url += ddmm(back_date)
    return url + str(max(1, passengers))


def welcome(lang: str) -> str:
    return t(lang, "welcome")


def help_text(lang: str) -> str:
    return t(lang, "help")


def route_line(origin: Airport, destination: Airport, roundtrip: bool = False) -> str:
    arrow = "⇄" if roundtrip else "→"
    return f"{origin.flag} {origin.display_city} {arrow} {destination.flag} {destination.display_city}"


def route_line_from(origin: Airport) -> str:
    return f"{origin.flag} {origin.display_city}  ({origin.code})"


def airport_choice_text(lang: str, query: str, n: int, *, departing: bool) -> str:
    prompt = t(lang, "choose_from" if departing else "choose_to")
    q = (query or "").strip()
    if not q:
        return prompt
    return f"*{q}*\n{prompt}"


def dates_prompt(lang: str, dep: Optional[_dt.date], ret: Optional[_dt.date],
                 roundtrip: bool = False, origin: Optional[Airport] = None,
                 destination: Optional[Airport] = None) -> str:
    lines = [f"*{t(lang, 'dates_hint')}*"]
    if origin and destination:
        lines.append(route_line(origin, destination, roundtrip=roundtrip))
    lines.append("")
    dep_s = fmt_date(lang, dep) if dep else "—"
    lines.append(f"{t(lang, 'label_depart')}     {dep_s}")
    if roundtrip:
        ret_s = fmt_date(lang, ret) if ret else "—"
        lines.append(f"{t(lang, 'label_return')}  {ret_s}")
        if not ret:
            lines.append("")
            lines.append(t(lang, "dates_rt_hint"))
    return "\n".join(lines)


_PROVIDERS = ["Nebo.Travel", "Superkassa", "Aviasales", "Kupibilet"]


def searching_bar(lang: str, step: int, total: int = 4) -> str:
    filled = "●" * step
    empty = "○" * max(0, total - step)
    provider = _PROVIDERS[min(step, len(_PROVIDERS)) - 1] if step else _PROVIDERS[0]
    return f"{filled}{empty}  {t(lang, 'searching', p=provider)}"


def cabin_label(lang: str, cabin: str) -> str:
    return t(lang, "business" if cabin == "business" else "economy")


def pax_summary(lang: str, pax: pricing.Passengers) -> str:
    parts = [f"{pax.adults} {t(lang, 'ab_adult')}"]
    if pax.children:
        parts.append(f"{pax.children} {t(lang, 'ab_child')}")
    if pax.infants:
        parts.append(f"{pax.infants} {t(lang, 'ab_infant')}")
    return ", ".join(parts) + f", {cabin_label(lang, pax.cabin)}"


def pax_card(lang: str, pax: pricing.Passengers) -> str:
    used = pax.total
    left = max(0, 9 - used)
    return "\n".join([
        f"*{t(lang, 'pax_prompt')}*",
        "",
        f"{t(lang, 'adults')}     {pax.adults}",
        f"{t(lang, 'children')}         {pax.children}",
        f"{t(lang, 'infants')}     {pax.infants}",
        f"{cabin_label(lang, pax.cabin)}",
        "",
        t(lang, "pax_total", n=used),
        t(lang, "pax_left", n=left),
    ])


def _place(code: str) -> str:
    apt = geo.airport(code)
    if not apt:
        return code
    return f"{apt.flag} {apt.display_city}"


def _apt_name(code: str) -> str:
    apt = geo.airport(code)
    if not apt:
        return code
    if apt.is_metro:
        return apt.display_city
    name = apt.display_name
    if name and name.casefold() != apt.display_city.casefold():
        return f"{name} ({code})"
    return f"{apt.display_city} ({code})"


def _leg_block(lang: str, it) -> str:
    stop_label = t(lang, "direct") if it.is_direct else t(lang, "stops_n", n=it.stops)
    lines = [
        f"{fmt_time(it.dep)}  {_apt_name(it.origin)}",
        f"{fmt_time(it.arr)}  {_apt_name(it.destination)}",
        f"{t(lang, 'in_flight', t=it.duration_str)}  ·  {stop_label}",
    ]
    if not it.is_direct:
        bits = [t(lang, "layover_in", t=fmt_duration(lay), city=city) for city, lay in it.stop_infos()]
        if bits:
            lines.insert(2, " · ".join(bits))
    return "\n".join(lines)


def offer_buy_label(lang: str, priced: Priced) -> str:
    return f"{t(lang, 'btn_buy')} · {money(lang, priced.price_total)}"


def format_offer(lang: str, priced: Priced, back: Optional[Priced] = None) -> str:
    it = priced.itinerary
    tags = []
    if priced.is_cheapest:
        tags.append(t(lang, "tag_cheapest"))
    if priced.is_fastest:
        tags.append(t(lang, "tag_fastest"))

    arrow = "⇄" if back is not None else "→"
    lines = [f"*{money(lang, priced.price_total)}*"]
    if tags:
        lines.append(" · ".join(tags))
    lines.append("")
    lines.append(f"{_place(it.origin)} {arrow} {_place(it.destination)}")

    date_line = fmt_date_short(lang, it.dep.date())
    if back is not None:
        date_line += f"  →  {fmt_date_short(lang, back.itinerary.dep.date())}"
    if priced.pax.total > 1:
        date_line += f"  ·  {pax_summary(lang, priced.pax)}"
    lines.append(date_line)
    lines.append("")
    if back is not None:
        lines.append(t(lang, "label_depart"))
    lines.append(_leg_block(lang, it))
    if back is not None:
        lines.append("")
        lines.append(t(lang, "label_return"))
        lines.append(_leg_block(lang, back.itinerary))

    bag = t(lang, "bag_yes") if it.baggage else t(lang, "bag_no")
    carrier = airlines.display_name(it.airline_iata or it.airline, lang)
    iata = airlines.iata_of(it.airline_iata or it.airline)
    fn = it.flight_no
    flight = f"{iata} {fn[len(iata):]}" if iata and fn.startswith(iata) else fn
    lines.append("")
    lines.append(f"{carrier}  ·  {flight}  ·  {bag}")
    return "\n".join(lines)


def results_header(lang: str, origin: str, destination: str, date: _dt.date,
                   pax: pricing.Passengers, page: int, total_pages: int, filters: Filters) -> str:
    if not filters.active:
        return ""
    flags = []
    if filters.direct_only:
        flags.append(t(lang, "flt_direct").lower())
    if filters.with_baggage:
        flags.append(t(lang, "flt_bag").lower())
    return t(lang, "filters_label", f=", ".join(flags))


def no_results_text(lang: str, filters_active: bool) -> str:
    return t(lang, "no_results_filters") if filters_active else t(lang, "no_results")


def price_advice_text(lang: str, trend: str) -> Optional[str]:
    if trend == "падает":
        return t(lang, "advice_down")
    if trend == "растёт":
        return t(lang, "advice_up")
    return None


def flexible_text(lang: str, points: Sequence[Tuple[_dt.date, int]], chosen: _dt.date) -> Optional[str]:
    if not points:
        return None
    best_date, best_price = min(points, key=lambda p: p[1])
    if best_date == chosen:
        return None
    return t(lang, "flex_line", d=fmt_date(lang, best_date), m=money(lang, best_price))


def range_text(lang: str, origin: str, destination: str,
               points: Sequence[Tuple[_dt.date, int]], pax: pricing.Passengers) -> str:
    if not points:
        return no_results_text(lang, False)
    cheapest = min(points, key=lambda p: p[1])
    start, end = points[0][0], points[-1][0]
    lines = [f"*{t(lang, 'range_title', o=origin, d=destination, start=fmt_date(lang, start), end=fmt_date(lang, end), pax=pax_summary(lang, pax))}*", ""]
    for date, price in points:
        mark = f"  · {t(lang, 'mark_cheapest')}" if (date, price) == cheapest else ""
        lines.append(f"{fmt_date(lang, date)}    *{money(lang, price)}*{mark}")
    lines.append("")
    lines.append(t(lang, "cheapest_day", d=fmt_date(lang, cheapest[0]), m=money(lang, cheapest[1])))
    return "\n".join(lines)


def hot_text(lang: str, deals: Sequence[Priced]) -> str:
    if not deals:
        return t(lang, "hot_none")
    lines = [f"*{t(lang, 'discover_title')}*", ""]
    for p in deals:
        it = p.itinerary
        lines.append(
            f"{_place(it.origin)} → {_place(it.destination)}"
            f"    *{money(lang, p.price_total)}*"
            + (f"  −{p.discount_pct}%" if p.discount_pct > 0 else "")
        )
    return "\n".join(lines)


def discover_text(lang: str, origin_city: str, deals: Sequence[Priced]) -> str:
    if not deals:
        return t(lang, "hot_none")
    lines = [f"*{t(lang, 'discover_title')}*", origin_city, ""]
    for p in deals:
        it = p.itinerary
        lines.append(f"{_place(it.destination)}    *{money(lang, p.price_total)}*")
    return "\n".join(lines)


def cabinet_text(lang: str, tracks_n: int) -> str:
    return "\n".join([
        f"*{t(lang, 'cabinet_title')}*",
        "",
        t(lang, "cabinet_lang", name=i18n.language_label(lang)),
        t(lang, "cabinet_cur", cur=i18n.currency_of(lang)),
        t(lang, "mytracks_title") + f" {tracks_n}",
    ])


def track_added_text(lang: str, origin: str, destination: str, date: _dt.date,
                     pax: pricing.Passengers, price: int) -> str:
    return t(lang, "track_added", o=origin, d=destination, date=fmt_date(lang, date),
             pax=pax_summary(lang, pax), m=money(lang, price))


def drop_text(lang: str, origin: str, destination: str, date: _dt.date,
              previous: int, new: int, pct: int) -> str:
    return t(lang, "drop", o=origin, d=destination, date=fmt_date(lang, date),
             prev=money(lang, previous), new=money(lang, new), pct=pct)


def mytracks_text(lang: str, tracks) -> str:
    if not tracks:
        return t(lang, "mytracks_empty")
    lines = [f"*{t(lang, 'mytracks_title')}*", ""]
    for i, tr in enumerate(tracks, start=1):
        last = money(lang, tr.last_price) if tr.last_price is not None else "—"
        best = money(lang, tr.best_price) if tr.best_price is not None else "—"
        lines.append(
            f"{i}. {tr.origin} → {tr.destination}, {fmt_date(lang, tr.date)}"
            f" — {last}  ({t(lang, 'tr_min')} {best})"
        )
    return "\n".join(lines)


def premium_text(lang: str) -> str:
    return t(lang, "premium_text")
