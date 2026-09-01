"""Language-aware reply builders shared by the bot and the offline demo.

Text is looked up per language via :mod:`avia_bot.i18n` (with Russian fallback)
and prices are converted to the user's currency. Assembled strings use a tiny
markup (*bold*, `code`) rendered to Telegram-safe HTML by :func:`render_html`.
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re
from typing import Optional, Sequence, Tuple

from . import i18n, pricing
from .flights import Filters, Priced, fmt_duration
from .geo import Airport
from .i18n import fmt_date, fmt_dt, money, t

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


# --- prompts ---------------------------------------------------------------

def welcome(lang: str) -> str:
    return t(lang, "welcome")


def help_text(lang: str) -> str:
    return t(lang, "help")


def route_line(origin: Airport, destination: Airport) -> str:
    return f"📍 {origin.city} ({origin.code}) → {destination.city} ({destination.code})"


def route_line_from(origin: Airport) -> str:
    return f"📍 {origin.city} ({origin.code})"


def dates_prompt(lang: str, dep: Optional[_dt.date], ret: Optional[_dt.date]) -> str:
    dep_s = fmt_date(lang, dep) if dep else "─────"
    ret_s = fmt_date(lang, ret) if ret else "─────"
    return (t(lang, "dates_hint") + "\n"
            + f"{t(lang, 'label_depart')}: {dep_s}\n"
            + f"{t(lang, 'label_return')}: {ret_s}")


_PROVIDERS = ["Nebo.Travel", "Superkassa", "Aviasales", "Kupibilet"]


def searching_bar(lang: str, step: int, total: int = 4) -> str:
    filled = "🟢" * step
    empty = "⚪" * max(0, total - step)
    provider = _PROVIDERS[min(step, len(_PROVIDERS)) - 1] if step else _PROVIDERS[0]
    return f"{filled}{empty} " + t(lang, "searching", p=provider)


# --- passengers ------------------------------------------------------------

def cabin_label(lang: str, cabin: str) -> str:
    return t(lang, "business" if cabin == "business" else "economy")


def pax_summary(lang: str, pax: pricing.Passengers) -> str:
    parts = [f"{pax.adults} {t(lang, 'ab_adult')}"]
    if pax.children:
        parts.append(f"{pax.children} {t(lang, 'ab_child')}")
    if pax.infants:
        parts.append(f"{pax.infants} {t(lang, 'ab_infant')}")
    return ", ".join(parts) + f", {cabin_label(lang, pax.cabin)}"


# --- result cards ----------------------------------------------------------

def offer_buy_label(lang: str, priced: Priced) -> str:
    return f"{t(lang, 'btn_buy')} ({t(lang, 'seats_left')}: {priced.itinerary.seats_left})"


def format_offer(lang: str, priced: Priced) -> str:
    it = priced.itinerary
    lines = []
    tags = []
    if priced.is_fastest:
        tags.append(t(lang, "tag_fastest"))
    if priced.is_cheapest:
        tags.append(t(lang, "tag_cheapest"))
    if tags:
        lines.append(" · ".join(tags))

    price = f"💰 *{money(lang, priced.price_total)}*"
    if priced.discount_pct > 0:
        price += f"   🔥 -{priced.discount_pct}%"
    lines.append(price)
    if priced.pax.total > 1:
        lines.append(f"👥 {pax_summary(lang, priced.pax)} · " + t(lang, "per_adult", m=money(lang, priced.per_adult)))
    lines.append(f"🛫 {it.airline}")
    lines.append(t(lang, "bag_yes") if it.baggage else t(lang, "bag_no"))
    lines.append("")
    lines.append(t(lang, "leg_there"))
    lines.append(f"📅 {fmt_dt(lang, it.dep)} — {fmt_dt(lang, it.arr)}")
    if it.is_direct:
        lines.append(f"🕐 {it.duration_str} ➡️ {t(lang, 'direct')}")
    else:
        stops = it.stop_infos()
        info = ", ".join(f"{city} {fmt_duration(lay)}" for city, lay in stops)
        lines.append(t(lang, "transfers", n=len(stops), info=info))
        lines.append(f"⏱ {it.duration_str}")
    return "\n".join(lines)


def results_header(lang: str, origin: str, destination: str, date: _dt.date,
                   pax: pricing.Passengers, page: int, total_pages: int, filters: Filters) -> str:
    head = f"📍 {origin} → {destination} · {fmt_date(lang, date)} · {pax_summary(lang, pax)}"
    if filters.active:
        flags = []
        if filters.direct_only:
            flags.append(t(lang, "flt_direct").lower())
        if filters.with_baggage:
            flags.append(t(lang, "flt_bag").lower())
        head += "\n" + t(lang, "filters_label", f=", ".join(flags))
    head += "\n" + t(lang, "variant", i=page + 1, n=total_pages)
    return head


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


# --- range / hot / tracking ------------------------------------------------

def range_text(lang: str, origin: str, destination: str,
               points: Sequence[Tuple[_dt.date, int]], pax: pricing.Passengers) -> str:
    if not points:
        return no_results_text(lang, False)
    cheapest = min(points, key=lambda p: p[1])
    start, end = points[0][0], points[-1][0]
    lines = [t(lang, "range_title", o=origin, d=destination,
               start=fmt_date(lang, start), end=fmt_date(lang, end), pax=pax_summary(lang, pax)), ""]
    for date, price in points:
        mark = f" 👑 {t(lang, 'mark_cheapest')}" if (date, price) == cheapest else ""
        lines.append(f"{fmt_date(lang, date)}: *{money(lang, price)}*{mark}")
    lines.append("")
    lines.append(t(lang, "cheapest_day", d=fmt_date(lang, cheapest[0]), m=money(lang, cheapest[1])))
    return "\n".join(lines)


def hot_text(lang: str, deals: Sequence[Priced]) -> str:
    if not deals:
        return t(lang, "hot_none")
    lines = [t(lang, "hot_title"), ""]
    for p in deals:
        it = p.itinerary
        lines.append(f"• {it.origin} → {it.destination} {fmt_date(lang, it.dep.date())}: "
                     f"*{money(lang, p.price_total)}* (−{p.discount_pct}%, {it.airline})")
    return "\n".join(lines)


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
    lines = [t(lang, "mytracks_title"), ""]
    for i, tr in enumerate(tracks, start=1):
        last = money(lang, tr.last_price) if tr.last_price is not None else "—"
        best = money(lang, tr.best_price) if tr.best_price is not None else "—"
        lines.append(
            f"{i}. {tr.origin} → {tr.destination}, {fmt_date(lang, tr.date)} · {pax_summary(lang, tr.pax)}"
            f" — {t(lang, 'tr_now')} {last}, {t(lang, 'tr_min')} {best} ({len(tr.history)} {t(lang, 'tr_checks')})"
        )
    return "\n".join(lines)
