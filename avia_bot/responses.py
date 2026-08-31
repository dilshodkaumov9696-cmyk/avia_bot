"""Pure response builders shared by the Telegram bot and the offline demo.

Keeping these free of any Telegram or I/O dependency means the exact text a user
sees can be unit-tested and exercised in the CLI demo without a bot token.
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re
from typing import List, Optional, Sequence, Tuple

from .flights import CITIES, FlightService, parse_date, resolve_city
from .pricing import Quote

# Reply builders author text in a tiny markup: *bold* and `monospace`.
# Telegram's legacy Markdown miscomputes entity offsets around emoji, so the
# bot renders to HTML instead (emoji-safe). These helpers do that conversion.
_BOLD = _re.compile(r"\*(.+?)\*", _re.S)
_CODE = _re.compile(r"`(.+?)`", _re.S)


def render_html(text: str) -> str:
    """Convert the internal *bold*/`code` markup to Telegram-safe HTML."""

    escaped = _html.escape(text, quote=False)
    escaped = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _BOLD.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)
    return escaped


def render_plain(text: str) -> str:
    """Strip the markup markers for plain-text contexts (e.g. the CLI demo)."""

    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _CODE.sub(lambda m: m.group(1), text)
    return text


def aviasales_url(
    origin: str,
    destination: str,
    out_date: _dt.date,
    back_date: Optional[_dt.date] = None,
    passengers: int = 1,
) -> str:
    """Build a real Aviasales deep-link search URL for a route/date/pax.

    Aviasales encodes a search as ``ORIGIN`` + ``DDMM`` + ``DEST`` + optional
    return ``DDMM`` + passenger count, e.g. ``LON0509NYC1``.
    """

    def ddmm(d: _dt.date) -> str:
        return f"{d.day:02d}{d.month:02d}"

    url = f"https://www.aviasales.com/search/{origin}{ddmm(out_date)}{destination}"
    if back_date is not None:
        url += ddmm(back_date)
    return url + str(max(1, passengers))

WELCOME = (
    "\u2708\ufe0f *AviaBot* \u2014 \u043f\u043e\u0438\u0441\u043a \u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u0430\u0432\u0438\u0430\u0431\u0438\u043b\u0435\u0442\u043e\u0432.\n\n"
    "\u0427\u0442\u043e \u044f \u0443\u043c\u0435\u044e:\n"
    "\U0001f50e \u041f\u043e\u0438\u0441\u043a \u0431\u0438\u043b\u0435\u0442\u043e\u0432 \u043f\u043e \u0434\u0430\u0442\u0435\n"
    "\U0001f4c5 \u041f\u043e\u0438\u0441\u043a \u043f\u043e \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0443 \u0434\u0430\u0442 (\u0441\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439 \u0434\u0435\u043d\u044c)\n"
    "\U0001f501 \u0411\u0438\u043b\u0435\u0442\u044b \u0442\u0443\u0434\u0430-\u043e\u0431\u0440\u0430\u0442\u043d\u043e \u0438 \U0001f465 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043f\u0430\u0441\u0441\u0430\u0436\u0438\u0440\u043e\u0432\n"
    "\U0001f440 \u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u0446\u0435\u043d\u044b \u0441 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435\u043c \u043e \u043f\u0430\u0434\u0435\u043d\u0438\u0438\n"
    "\U0001f4ca \u0413\u0440\u0430\u0444\u0438\u043a \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0446\u0435\u043d\u044b \u0438 \U0001f525 \u0433\u043e\u0440\u044f\u0449\u0438\u0435 \u0431\u0438\u043b\u0435\u0442\u044b\n\n"
    "\u041f\u0440\u0438\u043c\u0435\u0440\u044b:\n"
    "`/search London Dubai 2026-09-05`\n"
    "`/range LON NYC 2026-09-01 2026-09-10`\n\n"
    "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0443 \u043d\u0438\u0436\u0435 \u0438\u043b\u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 /help."
)

HELP = (
    "*\u041a\u043e\u043c\u0430\u043d\u0434\u044b AviaBot*\n"
    "/search <\u043e\u0442\u043a\u0443\u0434\u0430> <\u043a\u0443\u0434\u0430> [\u0414\u0410\u0422\u0410] [\u043f\u0430\u0441\u0441.] \u2014 \u043f\u043e\u0438\u0441\u043a \u0440\u0435\u0439\u0441\u043e\u0432\n"
    "/range <\u043e\u0442\u043a\u0443\u0434\u0430> <\u043a\u0443\u0434\u0430> <\u0421 \u0414\u0410\u0422\u0410> <\u041f\u041e \u0414\u0410\u0422\u0410> [\u043f\u0430\u0441\u0441.] \u2014 \u0441\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439 \u0434\u0435\u043d\u044c\n"
    "/rt <\u043e\u0442\u043a\u0443\u0434\u0430> <\u043a\u0443\u0434\u0430> <\u0422\u0423\u0414\u0410> <\u041e\u0411\u0420\u0410\u0422\u041d\u041e> [\u043f\u0430\u0441\u0441.] \u2014 \u0442\u0443\u0434\u0430-\u043e\u0431\u0440\u0430\u0442\u043d\u043e\n"
    "/hot [\u043f\u0430\u0441\u0441.] \u2014 \U0001f525 \u0433\u043e\u0440\u044f\u0449\u0438\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f\n"
    "/track <\u043e\u0442\u043a\u0443\u0434\u0430> <\u043a\u0443\u0434\u0430> <\u0414\u0410\u0422\u0410> [\u043f\u0430\u0441\u0441.] \u2014 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u0446\u0435\u043d\u0443\n"
    "/mytracks \u2014 \u043c\u043e\u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u044f\n"
    "/cities \u2014 \u0441\u043f\u0438\u0441\u043e\u043a \u0433\u043e\u0440\u043e\u0434\u043e\u0432\n\n"
    "\u0413\u043e\u0440\u043e\u0434\u0430 \u2014 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f \u0438\u043b\u0438 \u043a\u043e\u0434\u044b (`Tashkent` \u0438\u043b\u0438 `TAS`). \u0414\u0430\u0442\u044b \u0432 \u0444\u043e\u0440\u043c\u0430\u0442\u0435 \u0413\u0413\u0413\u0413-\u041c\u041c-\u0414\u0414."
)


def cities_text() -> str:
    lines = [f"\u2022 {name.title()} (`{code}`)" for name, code in sorted(CITIES.items())]
    return "*\u0413\u043e\u0440\u043e\u0434\u0430*\n" + "\n".join(lines)


def format_quote(quote: Quote, show_discount: bool = True) -> str:
    price = f"*${quote.price_total}*"
    if quote.passengers > 1:
        price += f" \u0437\u0430 {quote.passengers} \u043f\u0430\u0441\u0441. (${quote.price_per}/\u0447\u0435\u043b)"
    lines = [
        f"\u2708\ufe0f *{quote.airline}* {quote.flight_no}",
        f"   {quote.origin} \u2192 {quote.destination}, {quote.date.isoformat()}",
        f"   {quote.depart}\u2013{quote.arrive} ({quote.duration_str})",
        f"   {price} \u00b7 {quote.seats_left} \u043c\u0435\u0441\u0442",
    ]
    if show_discount and quote.discount_pct > 0:
        lines.append(f"   \U0001f525 -{quote.discount_pct}% \u043e\u0442 ${quote.baseline_total}")
    return "\n".join(lines)


def format_quotes(quotes: Sequence[Quote]) -> str:
    return "\n\n".join(format_quote(q) for q in quotes)


# --- argument parsing ------------------------------------------------------


class ParsedArgs:
    def __init__(self, cities: List[str], dates: List[_dt.date], passengers: int) -> None:
        self.cities = cities
        self.dates = dates
        self.passengers = passengers


def parse_args(args: Sequence[str]) -> ParsedArgs:
    """Split raw tokens into cities, dates (YYYY-MM-DD) and a passenger count.

    A bare integer token is treated as the passenger count; ``YYYY-MM-DD``
    tokens are dates; everything else is part of a (possibly multi-word) city.
    """

    cities: List[str] = []
    dates: List[_dt.date] = []
    passengers = 1
    for token in args:
        date = parse_date(token)
        if date is not None:
            dates.append(date)
            continue
        if token.isdigit():
            passengers = max(1, min(9, int(token)))
            continue
        cities.append(token)
    return ParsedArgs(cities, dates, passengers)


def _resolve_pair(city_tokens: List[str]) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Resolve city tokens into (origin, destination, unknown_raw_names)."""

    if len(city_tokens) < 2:
        return None, None, []
    origin_raw, dest_raw = _split_cities(city_tokens)
    origin = resolve_city(origin_raw)
    destination = resolve_city(dest_raw)
    unknown = [raw for raw, code in ((origin_raw, origin), (dest_raw, destination)) if code is None]
    return origin, destination, unknown


def _unknown_msg(unknown: List[str]) -> str:
    joined = ", ".join(unknown)
    return (
        f"\u041d\u0435 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043b \u0433\u043e\u0440\u043e\u0434(\u0430): *{joined}*.\n"
        "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 /cities \u2014 \u043f\u043e\u043a\u0430\u0436\u0443 \u0432\u0441\u0435 \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f."
    )


# --- command responses -----------------------------------------------------


def search_response(service: FlightService, args: Sequence[str], tick: Optional[int] = None) -> str:
    parsed = parse_args(args)
    if len(parsed.cities) < 2:
        return (
            "\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u043e\u0442\u043a\u0443\u0434\u0430 \u0438 \u043a\u0443\u0434\u0430, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440:\n"
            "`/search London Dubai` \u0438\u043b\u0438 `/search LON NYC 2026-09-05 2`."
        )
    origin, destination, unknown = _resolve_pair(parsed.cities)
    if unknown:
        return _unknown_msg(unknown)
    if origin == destination:
        return "\u0413\u043e\u0440\u043e\u0434 \u0432\u044b\u043b\u0435\u0442\u0430 \u0438 \u043f\u0440\u0438\u043b\u0451\u0442\u0430 \u0434\u043e\u043b\u0436\u043d\u044b \u043e\u0442\u043b\u0438\u0447\u0430\u0442\u044c\u0441\u044f."

    date = parsed.dates[0] if parsed.dates else None
    offers = service.search(origin, destination, date=date, passengers=parsed.passengers, tick=tick)
    if offers:
        header = f"\u041d\u0430\u0448\u0451\u043b {len(offers)} \u0440\u0435\u0439\u0441(\u043e\u0432) {origin} \u2192 {destination}"
        if date is not None:
            header += f" \u043d\u0430 {date.isoformat()}"
        if parsed.passengers > 1:
            header += f", {parsed.passengers} \u043f\u0430\u0441\u0441."
        return header + ":\n\n" + format_quotes(offers)

    reachable = service.routes_from(origin)
    if reachable:
        options = ", ".join(reachable)
        return (
            f"\u041d\u0435\u0442 \u043f\u0440\u044f\u043c\u044b\u0445 \u0440\u0435\u0439\u0441\u043e\u0432 {origin} \u2192 {destination}"
            + (f" \u043d\u0430 {date.isoformat()}" if date else "")
            + f".\n\u0418\u0437 {origin} \u0435\u0441\u0442\u044c \u043f\u0440\u044f\u043c\u044b\u0435 \u0440\u0435\u0439\u0441\u044b \u0432: {options}."
        )
    return f"\u041a \u0441\u043e\u0436\u0430\u043b\u0435\u043d\u0438\u044e, \u0438\u0437 {origin} \u043d\u0435\u0442 \u0440\u0435\u0439\u0441\u043e\u0432."


def range_response(
    service: FlightService, args: Sequence[str], tick: Optional[int] = None
) -> Tuple[str, List[Quote]]:
    parsed = parse_args(args)
    if len(parsed.cities) < 2 or len(parsed.dates) < 2:
        return (
            "\u0424\u043e\u0440\u043c\u0430\u0442: `/range \u043e\u0442\u043a\u0443\u0434\u0430 \u043a\u0443\u0434\u0430 \u0421_\u0414\u0410\u0422\u0410 \u041f\u041e_\u0414\u0410\u0422\u0410 [\u043f\u0430\u0441\u0441.]`\n"
            "\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: `/range LON NYC 2026-09-01 2026-09-10`.",
            [],
        )
    origin, destination, unknown = _resolve_pair(parsed.cities)
    if unknown:
        return _unknown_msg(unknown), []
    if origin == destination:
        return "\u0413\u043e\u0440\u043e\u0434 \u0432\u044b\u043b\u0435\u0442\u0430 \u0438 \u043f\u0440\u0438\u043b\u0451\u0442\u0430 \u0434\u043e\u043b\u0436\u043d\u044b \u043e\u0442\u043b\u0438\u0447\u0430\u0442\u044c\u0441\u044f.", []

    start, end = sorted(parsed.dates[:2])
    offers = service.search_range(origin, destination, start, end, passengers=parsed.passengers, tick=tick)
    if not offers:
        return f"\u041d\u0435\u0442 \u0440\u0435\u0439\u0441\u043e\u0432 {origin} \u2192 {destination} \u0432 \u044d\u0442\u043e\u043c \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0435.", []

    cheapest = min(offers, key=lambda q: q.price_total)
    lines = [
        f"\U0001f4c5 {origin} \u2192 {destination}, {start.isoformat()} \u2014 {end.isoformat()}"
        + (f", {parsed.passengers} \u043f\u0430\u0441\u0441." if parsed.passengers > 1 else "")
        + ":",
        "",
    ]
    for q in offers:
        mark = " \U0001f451 \u0441\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439" if q is cheapest else ""
        lines.append(f"{q.date.isoformat()}: *${q.price_total}* ({q.airline}){mark}")
    lines.append("")
    lines.append(
        f"\u0421\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439 \u0434\u0435\u043d\u044c \u2014 *{cheapest.date.isoformat()}* \u0437\u0430 *${cheapest.price_total}*."
    )
    return "\n".join(lines), offers


def roundtrip_response(service: FlightService, args: Sequence[str], tick: Optional[int] = None) -> str:
    parsed = parse_args(args)
    if len(parsed.cities) < 2 or len(parsed.dates) < 2:
        return (
            "\u0424\u043e\u0440\u043c\u0430\u0442: `/rt \u043e\u0442\u043a\u0443\u0434\u0430 \u043a\u0443\u0434\u0430 \u0422\u0423\u0414\u0410 \u041e\u0411\u0420\u0410\u0422\u041d\u041e [\u043f\u0430\u0441\u0441.]`\n"
            "\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: `/rt LON NYC 2026-09-05 2026-09-12 2`."
        )
    origin, destination, unknown = _resolve_pair(parsed.cities)
    if unknown:
        return _unknown_msg(unknown)
    if origin == destination:
        return "\u0413\u043e\u0440\u043e\u0434 \u0432\u044b\u043b\u0435\u0442\u0430 \u0438 \u043f\u0440\u0438\u043b\u0451\u0442\u0430 \u0434\u043e\u043b\u0436\u043d\u044b \u043e\u0442\u043b\u0438\u0447\u0430\u0442\u044c\u0441\u044f."

    out_date, back_date = sorted(parsed.dates[:2])
    trip = service.round_trip(origin, destination, out_date, back_date, passengers=parsed.passengers, tick=tick)
    if trip is None:
        return f"\u041d\u0435 \u043d\u0430\u0448\u0451\u043b \u0440\u0435\u0439\u0441\u044b \u0442\u0443\u0434\u0430-\u043e\u0431\u0440\u0430\u0442\u043d\u043e {origin} \u21c4 {destination} \u043d\u0430 \u044d\u0442\u0438 \u0434\u0430\u0442\u044b."
    out, back, total = trip
    return (
        f"\U0001f501 \u0422\u0443\u0434\u0430-\u043e\u0431\u0440\u0430\u0442\u043d\u043e {origin} \u21c4 {destination}"
        + (f", {parsed.passengers} \u043f\u0430\u0441\u0441." if parsed.passengers > 1 else "")
        + ":\n\n"
        + "\u2708\ufe0f \u0422\u0443\u0434\u0430:\n" + format_quote(out, show_discount=False) + "\n\n"
        + "\U0001f6ec \u041e\u0431\u0440\u0430\u0442\u043d\u043e:\n" + format_quote(back, show_discount=False) + "\n\n"
        + f"\U0001f4b0 \u0418\u0442\u043e\u0433\u043e: *${total}*"
    )


def hot_response(service: FlightService, args: Sequence[str], tick: Optional[int] = None) -> str:
    parsed = parse_args(args)
    deals = service.cheapest_deals(passengers=parsed.passengers, tick=tick)
    if not deals:
        return "\u0421\u0435\u0439\u0447\u0430\u0441 \u043d\u0435\u0442 \u0437\u0430\u043c\u0435\u0442\u043d\u044b\u0445 \u0441\u043a\u0438\u0434\u043e\u043a \u2014 \u0437\u0430\u0433\u043b\u044f\u043d\u0438\u0442\u0435 \u043f\u043e\u0437\u0436\u0435. \U0001f643"
    return "\U0001f525 *\u0413\u043e\u0440\u044f\u0449\u0438\u0435 \u0431\u0438\u043b\u0435\u0442\u044b* (\u043c\u0430\u043a\u0441. \u0441\u043a\u0438\u0434\u043a\u0430 \u0441\u0435\u0439\u0447\u0430\u0441):\n\n" + format_quotes(deals)


def track_added_text(quote: Quote) -> str:
    return (
        "\U0001f440 \u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u044e \u0446\u0435\u043d\u0443:\n\n"
        + format_quote(quote, show_discount=False)
        + "\n\n\u0421\u043e\u043e\u0431\u0449\u0443, \u043a\u0430\u043a \u0442\u043e\u043b\u044c\u043a\u043e \u0446\u0435\u043d\u0430 \u0443\u043f\u0430\u0434\u0451\u0442. /mytracks \u2014 \u0441\u043f\u0438\u0441\u043e\u043a."
    )


def drop_text(origin: str, destination: str, date: _dt.date, previous: int, new: int, pct: int) -> str:
    return (
        f"\U0001f525 \u0426\u0435\u043d\u0430 \u0443\u043f\u0430\u043b\u0430! {origin} \u2192 {destination} \u043d\u0430 {date.isoformat()}\n"
        f"\u0411\u044b\u043b\u043e ${previous} \u2192 \u0441\u0442\u0430\u043b\u043e *${new}* (\u2212{pct}%)."
    )


def mytracks_text(tracks) -> str:
    if not tracks:
        return "\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0439. \u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435: `/track LON NYC 2026-09-05`."
    lines = ["\U0001f440 *\u0412\u0430\u0448\u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u044f:*", ""]
    for i, t in enumerate(tracks, start=1):
        last = f"${t.last_price}" if t.last_price is not None else "\u2014"
        best = f"${t.best_price}" if t.best_price is not None else "\u2014"
        lines.append(
            f"{i}. {t.origin} \u2192 {t.destination}, {t.date.isoformat()}"
            + (f", {t.passengers} \u043f\u0430\u0441\u0441." if t.passengers > 1 else "")
            + f" \u2014 \u0442\u0435\u043a\u0443\u0449\u0430\u044f {last}, \u043c\u0438\u043d. {best} ({len(t.history)} \u043f\u0440\u043e\u0432\u0435\u0440\u043e\u043a)"
        )
    return "\n".join(lines)


def _split_cities(tokens: List[str]) -> Tuple[str, str]:
    """Split remaining tokens into an origin and destination string.

    Tries the simple two-token case first, then falls back to splitting a
    multi-word input down the middle (handles names like "New York").
    """

    if len(tokens) == 2:
        return tokens[0], tokens[1]

    for cut in range(1, len(tokens)):
        left = " ".join(tokens[:cut])
        right = " ".join(tokens[cut:])
        if resolve_city(left) and resolve_city(right):
            return left, right

    mid = len(tokens) // 2
    return " ".join(tokens[:mid]), " ".join(tokens[mid:])
