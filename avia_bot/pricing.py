"""Dynamic pricing engine.

Real flight prices move over time; to mirror that (and make price tracking,
history charts and "hot deals" meaningful) each quote is derived from a flight's
base fare multiplied by a deterministic, smoothly oscillating *market factor*
that depends on the route and a monotonic ``tick``.

``tick`` is a coarse clock: in the live bot it advances once per tracking
interval (see :func:`current_tick`), so every poll produces a slightly different
price. Tests pass an explicit ``tick`` to get deterministic results.
"""

from __future__ import annotations

import datetime as _dt
import math
import time
from dataclasses import dataclass

# Default price-tracking cadence. AviaGram checks every 30 minutes; the live bot
# uses the same default but can be overridden (e.g. for demos) via env var.
DEFAULT_INTERVAL_SECONDS = 30 * 60


def current_tick(interval_seconds: int = DEFAULT_INTERVAL_SECONDS, now: float | None = None) -> int:
    """Return the market tick for the current (or given) wall-clock time."""

    now = time.time() if now is None else now
    return int(now // max(1, interval_seconds))


def _route_seed(route_key: str) -> int:
    return sum((i + 1) * ord(c) for i, c in enumerate(route_key))


def market_factor(route_key: str, tick: int) -> float:
    """Deterministic multiplier in roughly ``[0.75, 1.25]`` for a route at a tick."""

    seed = _route_seed(route_key)
    wave = 0.18 * math.sin(0.6 * tick + seed) + 0.06 * math.sin(0.23 * tick + seed * 1.7)
    return 1.0 + wave


def seasonal_factor(date: _dt.date) -> float:
    """Weekends are a little pricier."""

    return 1.12 if date.weekday() >= 5 else 1.0


def route_key(origin: str, destination: str) -> str:
    return f"{origin}-{destination}"


@dataclass(frozen=True)
class Quote:
    """A priced offer for a specific flight, passenger count and market tick."""

    origin: str
    destination: str
    date: _dt.date
    airline: str
    flight_no: str
    depart: str
    arrive: str
    duration_str: str
    seats_left: int
    passengers: int
    tick: int
    price_per: int
    price_total: int
    baseline_total: int

    @property
    def discount_pct(self) -> int:
        """Positive when the current price is below the list (baseline) price."""

        if self.baseline_total <= 0:
            return 0
        return round((self.baseline_total - self.price_total) / self.baseline_total * 100)


def quote(flight, tick: int, passengers: int = 1) -> Quote:
    """Build a :class:`Quote` for a flight at a given market tick."""

    passengers = max(1, int(passengers))
    key = route_key(flight.origin, flight.destination)
    season = seasonal_factor(flight.date)
    per = flight.price_usd * market_factor(key, tick) * season
    per_int = int(round(per))
    baseline_per = int(round(flight.price_usd * season))
    return Quote(
        origin=flight.origin,
        destination=flight.destination,
        date=flight.date,
        airline=flight.airline,
        flight_no=flight.flight_no,
        depart=flight.depart,
        arrive=flight.arrive,
        duration_str=flight.duration_str,
        seats_left=flight.seats_left,
        passengers=passengers,
        tick=tick,
        price_per=per_int,
        price_total=per_int * passengers,
        baseline_total=baseline_per * passengers,
    )
