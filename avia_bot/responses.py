"""Reply text builders shared by the bot and the offline demo.

Text is authored in a tiny markup (*bold*, `code`) and rendered to Telegram-safe
HTML by :func:`render_html` (emoji-safe, unlike legacy Markdown). Nothing here
imports python-telegram-bot, so every string is unit-testable.
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re
from typing import Iterable, List, Optional, Sequence, Tuple

from . import pricing
from .flights import Filters, Priced, fmt_duration
from .geo import Airport
from .pricing import Passengers, format_money

_BOLD = _re.compile(r"\*(.+?)\*", _re.S)
_CODE = _re.compile(r"`(.+?)`", _re.S)

MONTH_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def render_html(text: str) -> str:
    escaped = _html.escape(text, quote=False)
    escaped = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)
    return escaped


def render_plain(text: str) -> str:
    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _CODE.sub(lambda m: m.group(1), text)
    return text


def fmt_date(date: _dt.date) -> str:
    return f"{date.day} {MONTH_GEN[date.month]}"


def fmt_dt(value: _dt.datetime) -> str:
    return f"{value.day} {MONTH_GEN[value.month]} {value:%H:%M}"


def aviasales_url(origin: str, destination: str, out_date: _dt.date,
                  back_date: Optional[_dt.date] = None, passengers: int = 1) -> str:
    def ddmm(d: _dt.date) -> str:
        return f"{d.day:02d}{d.month:02d}"

    url = f"https://www.aviasales.com/search/{origin}{ddmm(out_date)}{destination}"
    if back_date is not None:
        url += ddmm(back_date)
    return url + str(max(1, passengers))


# --- static prompts --------------------------------------------------------

WELCOME = (
    "✈️ *AviaBot* — поиск и отслеживание авиабилетов.\n\n"
    "Я помогу найти дешёвые билеты по датам и диапазону, туда-обратно, "
    "для нескольких пассажиров, и буду следить за ценой. 🔥\n\n"
    "Нажмите *🔎 Поиск* внизу, чтобы начать, или /help."
)

HELP = (
    "*Как пользоваться*\n"
    "🔎 *Поиск* — пошаговый поиск: город откуда → куда → пассажиры и класс → даты.\n"
    "🔎🗓 *По диапазону* — самый дешёвый день в диапазоне дат.\n"
    "👀 *Добавить отслеживание* — следить за ценой (уведомлю о падении).\n"
    "🔥 /hot — горящие предложения.\n"
    "🗂 /mytracks — мои отслеживания.\n\n"
    "Команды: /search, /range, /hot, /mytracks, /cancel."
)

ASK_FROM = "🏠 Введите город откуда летите (Пример: Москва)"
CHOOSE_FROM = "Выберите из списка откуда отправляетесь"
ASK_TO = "🛫 Введите город куда вы летите (Пример: Худжанд)"
CHOOSE_TO = "Выберите из списка куда летите"
PAX_PROMPT = "Выберите кол-во пассажиров и класс"
CITY_NOT_FOUND = "Не нашёл такой город. Попробуйте ещё раз (например: Москва, Ташкент, Дубай)."


def route_line(origin: Airport, destination: Airport) -> str:
    return f"📍 {origin.city} ({origin.code}) → {destination.city} ({destination.code})"


def route_line_from(origin: Airport) -> str:
    return f"📍 Откуда: {origin.city} ({origin.code})"


def mytracks_hint() -> str:
    return "Слежу за ценой — сообщу о падении. /mytracks — список."


def dates_prompt(dep: Optional[_dt.date], ret: Optional[_dt.date]) -> str:
    dep_s = fmt_date(dep) if dep else "─────"
    ret_s = fmt_date(ret) if ret else "─────"
    return (
        "🗓 Выберите день вылета и обратно (если нужно).\n"
        f"🚀 Вылет: {dep_s}\n"
        f"🔄 Обратно: {ret_s}"
    )


_PROVIDERS = ["Nebo.Travel", "Superkassa", "Aviasales", "Kupibilet"]


def searching_bar(step: int, total: int = 4) -> str:
    filled = "🟢" * step
    empty = "⚪" * max(0, total - step)
    provider = _PROVIDERS[min(step, len(_PROVIDERS)) - 1] if step else _PROVIDERS[0]
    return f"{filled}{empty} Ищу на {provider}…"


# --- result formatting -----------------------------------------------------


def offer_buy_label(priced: Priced) -> str:
    return f"Купить билет (Осталось: {priced.itinerary.seats_left})"


def format_offer(priced: Priced) -> str:
    it = priced.itinerary
    lines: List[str] = []
    tags = []
    if priced.is_fastest:
        tags.append("🔴 Самый быстрый 🏎")
    if priced.is_cheapest:
        tags.append("🟢 Самый дешёвый 💸")
    if tags:
        lines.append(" · ".join(tags))

    money = f"💰 *{format_money(priced.price_total)}*"
    if priced.discount_pct > 0:
        money += f"   🔥 -{priced.discount_pct}%"
    lines.append(money)
    if priced.pax.total > 1:
        lines.append(f"👥 {priced.pax.summary} · {format_money(priced.per_adult)}/взр.")
    lines.append(f"🛫 {it.airline}")
    lines.append("🧳 С багажом" if it.baggage else "🎒 Без багажа")
    lines.append("")
    lines.append("— Туда:")
    lines.append(f"📅 {fmt_dt(it.dep)} — {fmt_dt(it.arr)}")
    if it.is_direct:
        lines.append(f"🕐 {it.duration_str} ➡️ Прямой")
    else:
        stops = it.stop_infos()
        joined = ", ".join(f"{city} {fmt_duration(lay)}" for city, lay in stops)
        word = "пересадка" if len(stops) == 1 else "пересадки"
        lines.append(f"🔀 {len(stops)} {word}: {joined}")
        lines.append(f"⏱ {it.duration_str}")
    return "\n".join(lines)


def results_header(origin: str, destination: str, date: _dt.date, pax: Passengers,
                   page: int, total_pages: int, filters: Filters) -> str:
    head = f"📍 {origin} → {destination} · {fmt_date(date)} · {pax.summary}"
    if filters.active:
        flags = []
        if filters.direct_only:
            flags.append("только прямые")
        if filters.with_baggage:
            flags.append("с багажом")
        head += f"\n⚙️ Фильтры: {', '.join(flags)}"
    head += f"\nВариант {page + 1} из {total_pages}"
    return head


def no_results_text(filters_active: bool) -> str:
    if filters_active:
        return "По этим фильтрам рейсов нет. Нажмите «Фильтры», чтобы смягчить условия."
    return "На эту дату рейсов не нашлось. Попробуйте другую дату или город."


def price_advice_text(origin: str, destination: str, trend: str) -> Optional[str]:
    if trend == "падает":
        return "💡 Совет: цена сейчас снижается — можно немного подождать или включить отслеживание."
    if trend == "растёт":
        return "💡 Совет: цена растёт — брать выгоднее сейчас."
    return None


def flexible_text(points: Sequence[Tuple[_dt.date, int]], chosen: _dt.date) -> Optional[str]:
    if not points:
        return None
    best_date, best_price = min(points, key=lambda p: p[1])
    if best_date == chosen:
        return None
    return (
        f"📅 Гибкие даты: дешевле всего *{fmt_date(best_date)}* — "
        f"{format_money(best_price)}."
    )


# --- range / hot / tracking ------------------------------------------------


def range_text(origin: str, destination: str, points: Sequence[Tuple[_dt.date, int]],
               pax: Passengers) -> str:
    if not points:
        return no_results_text(False)
    cheapest = min(points, key=lambda p: p[1])
    start, end = points[0][0], points[-1][0]
    lines = [f"📅 {origin} → {destination}, {fmt_date(start)} — {fmt_date(end)} · {pax.summary}:", ""]
    for date, price in points:
        mark = " 👑 самый дешёвый" if (date, price) == cheapest else ""
        lines.append(f"{fmt_date(date)}: *{format_money(price)}*{mark}")
    lines.append("")
    lines.append(f"Дешевле всего — *{fmt_date(cheapest[0])}* за *{format_money(cheapest[1])}*.")
    return "\n".join(lines)


def hot_text(deals: Sequence[Priced]) -> str:
    if not deals:
        return "Сейчас нет заметных скидок — загляните позже. 🙂"
    lines = ["🔥 *Горящие билеты* (макс. скидка сейчас):", ""]
    for p in deals:
        it = p.itinerary
        lines.append(
            f"• {it.origin} → {it.destination} {fmt_date(it.dep.date())}: "
            f"*{format_money(p.price_total)}* (−{p.discount_pct}%, {it.airline})"
        )
    return "\n".join(lines)


def track_added_text(origin: str, destination: str, date: _dt.date, pax: Passengers, price: int) -> str:
    return (
        "👀 Отслеживаю цену:\n"
        f"📍 {origin} → {destination}, {fmt_date(date)} · {pax.summary}\n"
        f"💰 Сейчас: *{format_money(price)}*\n\n"
        "Сообщу, как только цена упадёт. /mytracks — список."
    )


def drop_text(origin: str, destination: str, date: _dt.date, previous: int, new: int, pct: int) -> str:
    return (
        f"🔥 Цена упала! {origin} → {destination}, {fmt_date(date)}\n"
        f"Было {format_money(previous)} → стало *{format_money(new)}* (−{pct}%)."
    )


def mytracks_text(tracks) -> str:
    if not tracks:
        return "У вас нет отслеживаний. Нажмите «➕👀 Добавить отслеживание» после поиска."
    lines = ["👀 *Ваши отслеживания:*", ""]
    for i, t in enumerate(tracks, start=1):
        last = format_money(t.last_price) if t.last_price is not None else "—"
        best = format_money(t.best_price) if t.best_price is not None else "—"
        lines.append(
            f"{i}. {t.origin} → {t.destination}, {fmt_date(t.date)} · {t.pax.summary}"
            f" — сейчас {last}, мин. {best} ({len(t.history)} пров.)"
        )
    return "\n".join(lines)
