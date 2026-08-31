"""avia_bot — an AviaGram-style flight-search & price-tracking Telegram bot.

The engine is pure and synchronous so it runs without a live Telegram connection:

- ``geo``         — cities & airports + fuzzy city search.
- ``flights``     — itinerary engine (direct/connecting, baggage, seats, filters).
- ``pricing``     — market/season/cabin pricing, passenger mix, TJS, trend.
- ``calendar_ui`` — inline calendar model.
- ``search_flow`` — passenger/cabin math + pagination.
- ``tracking``    — price-tracking store + drop detection.
- ``charts``      — matplotlib price charts.
- ``responses``   — RU prompts + result cards (rendered to HTML).
- ``bot``         — the Telegram wiring (guided ConversationHandler).
- ``demo``        — an offline walkthrough of the whole scenario.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
