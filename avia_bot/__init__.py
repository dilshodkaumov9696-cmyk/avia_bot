"""avia_bot — a simple flight-search Telegram bot.

The package is split so the flight-search core and message formatting are pure,
synchronous functions that can be exercised without a live Telegram connection:

- ``flights``    — flight data model and the in-memory search service.
- ``responses``  — pure functions that turn parsed user input into reply text.
- ``bot``        — the thin Telegram wiring built on top of ``responses``.
- ``demo``       — an offline CLI that drives ``responses`` like a real chat.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
