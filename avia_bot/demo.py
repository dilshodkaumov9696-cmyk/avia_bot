"""Offline demo that drives the same response builders the Telegram bot uses.

Run a scripted conversation:      python -m avia_bot.demo
Run an interactive chat session:  python -m avia_bot.demo --interactive

This proves the flight-search core end-to-end without a Telegram token.
"""

from __future__ import annotations

import argparse
import shlex
from typing import List

from . import responses
from .flights import FlightService


def handle(service: FlightService, message: str) -> str:
    """Route a raw chat message to the matching response builder."""

    text = message.strip()
    if not text:
        return responses.HELP

    if text.startswith("/"):
        parts = shlex.split(text)
        command = parts[0].lstrip("/").lower()
        args = parts[1:]
    else:
        command, args = "", []

    if command == "start":
        return responses.WELCOME
    if command == "help":
        return responses.HELP
    if command == "cities":
        return responses.cities_text()
    if command == "search":
        return responses.search_response(service, args)
    return responses.HELP


_SCRIPT: List[str] = [
    "/start",
    "/cities",
    "/search London Dubai",
    "/search LON NYC 2026-09-05",
    "/search New York Tokyo",
    "/search Paris Tashkent",
    "/search Mars Venus",
]


def _print_exchange(message: str, reply: str) -> None:
    print(f"\n\U0001f464 user: {message}")
    print("\U0001f916 avia_bot:")
    for line in reply.splitlines():
        print(f"    {line}")


def run_scripted() -> None:
    service = FlightService()
    print("=" * 60)
    print("avia_bot offline demo (scripted conversation)")
    print("=" * 60)
    for message in _SCRIPT:
        _print_exchange(message, handle(service, message))
    print("\n" + "=" * 60)
    print("Demo complete \u2014 flight-search core exercised end-to-end.")
    print("=" * 60)


def run_interactive() -> None:
    service = FlightService()
    print("avia_bot interactive demo. Type a command (or 'quit').")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.lower() in {"quit", "exit"}:
            break
        print(handle(service, message))


def main() -> None:
    parser = argparse.ArgumentParser(description="avia_bot offline demo")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="start an interactive chat session instead of the scripted demo",
    )
    args = parser.parse_args()
    if args.interactive:
        run_interactive()
    else:
        run_scripted()


if __name__ == "__main__":
    main()
