"""Pure response builders shared by the Telegram bot and the offline demo.

Keeping these free of any Telegram or I/O dependency means the exact text a user
sees can be unit-tested and exercised in the CLI demo without a bot token.
"""

from __future__ import annotations

from typing import List

from .flights import CITIES, Flight, FlightService, parse_date, resolve_city

WELCOME = (
    "\u2708\ufe0f Welcome to *avia_bot* \u2014 your flight search assistant!\n\n"
    "Use /search to find flights, for example:\n"
    "`/search London Dubai`\n"
    "`/search LON NYC 2026-09-05`\n\n"
    "Type /help for all commands and /cities for supported cities."
)

HELP = (
    "*avia_bot commands*\n"
    "/search <from> <to> [YYYY-MM-DD] \u2014 find flights on a route\n"
    "/cities \u2014 list supported cities\n"
    "/help \u2014 show this message\n\n"
    "Cities can be names or codes, e.g. `Tashkent` or `TAS`."
)


def cities_text() -> str:
    lines = [f"\u2022 {name.title()} (`{code}`)" for name, code in sorted(CITIES.items())]
    return "*Supported cities*\n" + "\n".join(lines)


def _format_flight(flight: Flight) -> str:
    return (
        f"\u2708\ufe0f *{flight.airline}* {flight.flight_no}\n"
        f"   {flight.origin} \u2192 {flight.destination} on {flight.date.isoformat()}\n"
        f"   {flight.depart}\u2013{flight.arrive} ({flight.duration_str})\n"
        f"   *${flight.price_usd}* \u00b7 {flight.seats_left} seats left"
    )


def format_results(flights: List[Flight]) -> str:
    return "\n\n".join(_format_flight(f) for f in flights)


def search_response(service: FlightService, args: List[str]) -> str:
    """Build the reply for a ``/search`` command given its raw argument list."""

    if len(args) < 2:
        return (
            "Please tell me where you want to fly, e.g.\n"
            "`/search London Dubai` or `/search LON NYC 2026-09-05`."
        )

    # The optional trailing token is a date; everything else forms the two cities.
    date = None
    tokens = list(args)
    maybe_date = parse_date(tokens[-1])
    if maybe_date is not None:
        date = maybe_date
        tokens = tokens[:-1]

    if len(tokens) < 2:
        return "I need both a departure and an arrival city."

    # Support multi-word city names by splitting the remaining tokens in half only
    # when a clean single-token split does not resolve.
    origin_raw, dest_raw = _split_cities(tokens)
    origin = resolve_city(origin_raw)
    destination = resolve_city(dest_raw)

    unknown = [
        raw
        for raw, code in ((origin_raw, origin), (dest_raw, destination))
        if code is None
    ]
    if unknown:
        joined = ", ".join(unknown)
        return (
            f"Sorry, I don't recognise: *{joined}*.\n"
            "Send /cities to see everywhere I can search."
        )

    if origin == destination:
        return "Departure and arrival cities must be different."

    flights = service.search(origin, destination, date=date)
    if flights:
        header = f"Found {len(flights)} flight(s) {origin} \u2192 {destination}"
        if date is not None:
            header += f" on {date.isoformat()}"
        return header + ":\n\n" + format_results(flights)

    # No direct flights: offer the destinations we do serve from the origin.
    reachable = service.routes_from(origin)
    if reachable:
        options = ", ".join(reachable)
        return (
            f"No direct flights {origin} \u2192 {destination}"
            + (f" on {date.isoformat()}" if date else "")
            + f".\nFrom {origin} you can fly non-stop to: {options}."
        )
    return f"Sorry, I don't currently sell any flights departing from {origin}."


def _split_cities(tokens: List[str]) -> tuple[str, str]:
    """Split remaining tokens into an origin and destination string.

    Tries the simple two-token case first, then falls back to splitting a
    multi-word input down the middle (handles names like "New York").
    """

    if len(tokens) == 2:
        return tokens[0], tokens[1]

    # Prefer a split where both halves resolve to a known city.
    for cut in range(1, len(tokens)):
        left = " ".join(tokens[:cut])
        right = " ".join(tokens[cut:])
        if resolve_city(left) and resolve_city(right):
            return left, right

    mid = len(tokens) // 2
    return " ".join(tokens[:mid]), " ".join(tokens[mid:])
