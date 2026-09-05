"""Dynamic pricing: market fluctuation over time, cabin class, passenger mix.

Prices are quoted in TJS (to match AviaGram). A flight's base fare is multiplied
by a deterministic, smoothly oscillating *market factor* (per route and ``tick``)
plus a seasonal factor and a cabin-class factor. Passenger totals combine adults,
children (75%) and infants (10%).
"""

from __future__ import annotations

import datetime as _dt
import math
import time
from dataclasses import dataclass

DEFAULT_INTERVAL_SECONDS = 30 * 60
CURRENCY = "TJS"

# cabin key -> (display name, price factor)
CABINS = {
    "economy": ("Эконом", 1.0),
    "business": ("Бизнес", 2.8),
}
CABIN_ORDER = ["economy", "business"]

CHILD_FACTOR = 0.75
INFANT_FACTOR = 0.10


def current_tick(interval_seconds: int = DEFAULT_INTERVAL_SECONDS, now: float | None = None) -> int:
    now = time.time() if now is None else now
    return int(now // max(1, interval_seconds))


def _route_seed(route_key: str) -> int:
    return sum((i + 1) * ord(c) for i, c in enumerate(route_key))


def market_factor(route_key: str, tick: int) -> float:
    """Deterministic multiplier ~[0.75, 1.25] for a route at a tick."""

    seed = _route_seed(route_key)
    wave = 0.18 * math.sin(0.6 * tick + seed) + 0.06 * math.sin(0.23 * tick + seed * 1.7)
    return 1.0 + wave


def seasonal_factor(date: _dt.date) -> float:
    return 1.12 if date.weekday() >= 5 else 1.0


def route_key(origin: str, destination: str) -> str:
    return f"{origin}-{destination}"


def cabin_name(cabin: str) -> str:
    return CABINS.get(cabin, CABINS["economy"])[0]


def cabin_factor(cabin: str) -> float:
    return CABINS.get(cabin, CABINS["economy"])[1]


@dataclass(frozen=True)
class Passengers:
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin: str = "economy"

    @property
    def total(self) -> int:
        return self.adults + self.children + self.infants

    @property
    def summary(self) -> str:
        parts = [f"{self.adults} взр."]
        if self.children:
            parts.append(f"{self.children} дет.")
        if self.infants:
            parts.append(f"{self.infants} млад.")
        return ", ".join(parts) + f", {cabin_name(self.cabin)}"


def per_adult_price(base: int, key: str, date: _dt.date, tick: int, cabin: str) -> int:
    price = base * market_factor(key, tick) * seasonal_factor(date) * cabin_factor(cabin)
    return int(round(price))


def total_price(base: int, key: str, date: _dt.date, tick: int, pax: Passengers) -> int:
    per = per_adult_price(base, key, date, tick, pax.cabin)
    total = per * pax.adults + per * CHILD_FACTOR * pax.children + per * INFANT_FACTOR * pax.infants
    return int(round(total))


def format_money(amount: int, currency: str = CURRENCY) -> str:
    return f"{amount:,}".replace(",", "\u00a0") + f" {currency}"


def price_trend(key: str, tick: int) -> str:
    """A light 'advice' hint: is the fare likely to rise or fall next tick?"""

    now = market_factor(key, tick)
    nxt = market_factor(key, tick + 1)
    if nxt < now - 0.01:
        return "падает"
    if nxt > now + 0.01:
        return "растёт"
    return "стабильна"
