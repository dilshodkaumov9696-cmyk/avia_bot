"""Offline demo driving the same builders the Telegram bot uses.

    python -m avia_bot.demo                 # scripted conversation
    python -m avia_bot.demo --interactive   # type your own commands
    python -m avia_bot.demo --charts-dir DIR  # also save example PNG charts

Proves search, date-range, round-trip, passengers, hot deals and price
tracking (with drop notifications) end-to-end without a Telegram token.
"""

from __future__ import annotations

import argparse
import os
import shlex
from typing import List, Optional

from . import charts, responses
from .flights import FlightService, parse_date, resolve_city
from .tracking import PriceTracker

# Fixed tick so the scripted transcript is deterministic run-to-run.
DEMO_TICK = 1000
DEMO_CHAT = 424242


class Session:
    def __init__(self) -> None:
        self.service = FlightService()
        self.tracker = PriceTracker(self.service)

    def respond(self, message: str) -> str:
        text = message.strip()
        if not text:
            return responses.HELP
        if text.startswith("/"):
            parts = shlex.split(text)
            command = parts[0].lstrip("/").lower()
            args = parts[1:]
        else:
            return responses.HELP

        if command == "start":
            return responses.WELCOME
        if command == "help":
            return responses.HELP
        if command == "cities":
            return responses.cities_text()
        if command == "search":
            return responses.search_response(self.service, args, tick=DEMO_TICK)
        if command == "range":
            return responses.range_response(self.service, args, tick=DEMO_TICK)[0]
        if command == "rt":
            return responses.roundtrip_response(self.service, args, tick=DEMO_TICK)
        if command == "hot":
            return responses.hot_response(self.service, args, tick=DEMO_TICK)
        if command == "track":
            return self._track(args)
        if command == "mytracks":
            return responses.mytracks_text(self.tracker.list_for(DEMO_CHAT))
        return responses.HELP

    def _track(self, args: List[str]) -> str:
        parsed = responses.parse_args(args)
        if len(parsed.cities) < 2 or not parsed.dates:
            return "\u0424\u043e\u0440\u043c\u0430\u0442: /track \u043e\u0442\u043a\u0443\u0434\u0430 \u043a\u0443\u0434\u0430 \u0414\u0410\u0422\u0410 [\u043f\u0430\u0441\u0441.]"
        origin, destination, unknown = responses._resolve_pair(parsed.cities)
        if unknown:
            return responses._unknown_msg(unknown)
        _, quote = self.tracker.add(DEMO_CHAT, origin, destination, parsed.dates[0], parsed.passengers, tick=DEMO_TICK)
        return responses.track_added_text(quote) if quote else "\u041d\u0435\u0442 \u0440\u0435\u0439\u0441\u043e\u0432."


_SCRIPT: List[str] = [
    "/start",
    "/cities",
    "/search London Paris 2026-09-05",
    "/search New York Tokyo 2026-09-06 2",
    "/range LON NYC 2026-09-01 2026-09-07",
    "/rt LON NYC 2026-09-05 2026-09-12 2",
    "/hot",
    "/search Mars Venus",
]


def _print_exchange(message: str, reply: str) -> None:
    print(f"\n\U0001f464 user: {message}")
    print("\U0001f916 avia_bot:")
    for line in reply.splitlines():
        print(f"    {line}")


def _simulate_tracking(session: Session) -> None:
    """Register a track, then poll across ticks to trigger a real drop notice."""

    print("\n" + "-" * 60)
    print("Price tracking simulation (route LON \u2192 PAR, 2026-09-05)")
    print("-" * 60)

    origin, destination = "LON", "PAR"
    date = parse_date("2026-09-05")

    # Find two ticks where the cheapest price falls, to demonstrate a drop.
    prices = {t: session.service.cheapest(origin, destination, date, tick=t).price_total for t in range(0, 40)}
    start_tick = next((t for t in range(0, 39) if prices[t + 1] < prices[t]), 0)

    _, seed = session.tracker.add(DEMO_CHAT, origin, destination, date, tick=start_tick)
    print(f"\nRegistered track at check #1: ${seed.price_total}")

    for offset in range(1, 6):
        tick = start_tick + offset
        drops = session.tracker.poll(tick)
        track = session.tracker.list_for(DEMO_CHAT)[0]
        note = ""
        for event in drops:
            note = "  \U0001f525 " + responses.drop_text(
                event.track.origin, event.track.destination, event.track.date,
                event.previous_price, event.new_price, event.drop_pct,
            ).replace("\n", " ")
        print(f"Check #{offset + 1} (tick {tick}): ${track.last_price}{note}")

    print("\n" + responses.mytracks_text(session.tracker.list_for(DEMO_CHAT)))


def _save_charts(session: Session, charts_dir: str) -> None:
    os.makedirs(charts_dir, exist_ok=True)
    offers = session.service.search_range("LON", "NYC", parse_date("2026-09-01"), parse_date("2026-09-10"), tick=DEMO_TICK)
    range_path = os.path.join(charts_dir, "range_chart.png")
    with open(range_path, "wb") as fh:
        fh.write(charts.render_range_chart(offers))

    track = session.tracker.list_for(DEMO_CHAT)
    hist_path = None
    if track:
        hist_path = os.path.join(charts_dir, "history_chart.png")
        with open(hist_path, "wb") as fh:
            fh.write(charts.render_history_chart(track[0]))
    print(f"\nSaved charts: {range_path}" + (f", {hist_path}" if hist_path else ""))


def run_scripted(charts_dir: Optional[str] = None) -> None:
    session = Session()
    print("=" * 60)
    print("avia_bot offline demo (scripted conversation)")
    print("=" * 60)
    for message in _SCRIPT:
        _print_exchange(message, session.respond(message))
    _simulate_tracking(session)
    if charts_dir:
        _save_charts(session, charts_dir)
    print("\n" + "=" * 60)
    print("Demo complete \u2014 search, range, round-trip, hot deals & tracking exercised.")
    print("=" * 60)


def run_interactive() -> None:
    session = Session()
    print("avia_bot interactive demo. Type a command (or 'quit').")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"quit", "exit"}:
            break
        print(session.respond(message))


def main() -> None:
    parser = argparse.ArgumentParser(description="avia_bot offline demo")
    parser.add_argument("--interactive", action="store_true", help="interactive chat session")
    parser.add_argument("--charts-dir", default=None, help="directory to save example PNG charts")
    args = parser.parse_args()
    if args.interactive:
        run_interactive()
    else:
        run_scripted(charts_dir=args.charts_dir)


if __name__ == "__main__":
    main()
