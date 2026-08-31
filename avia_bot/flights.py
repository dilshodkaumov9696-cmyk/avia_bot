"""In-memory flight catalogue and search service.

This module deliberately avoids any external API so the bot's core behaviour is
deterministic and runnable offline (in tests, the CLI demo, and CI). Swapping in
a real flight-data provider later only requires replacing :func:`_build_catalogue`
and :meth:`FlightService.search`.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import pricing
from .pricing import Quote

# Canonical city name -> IATA-style code. Lookups are case-insensitive and also
# accept the code itself, so "london", "LONDON" and "LON" all resolve.
CITIES: Dict[str, str] = {
    "london": "LON",
    "paris": "PAR",
    "new york": "NYC",
    "tokyo": "TYO",
    "dubai": "DXB",
    "tashkent": "TAS",
    "istanbul": "IST",
    "singapore": "SIN",
}

# Non-stop routes we sell tickets for, with a representative base price (USD).
_ROUTES = [
    ("LON", "PAR", "AirFrance", 120, 80),
    ("LON", "NYC", "British Airways", 430, 415),
    ("PAR", "NYC", "Delta", 460, 490),
    ("DXB", "TAS", "Uzbekistan Airways", 210, 245),
    ("IST", "TAS", "Turkish Airlines", 180, 260),
    ("DXB", "SIN", "Emirates", 380, 400),
    ("TYO", "SIN", "Singapore Airlines", 350, 410),
    ("NYC", "TYO", "ANA", 620, 660),
    ("IST", "LON", "Turkish Airlines", 200, 190),
    ("PAR", "DXB", "Emirates", 340, 355),
]


@dataclass(frozen=True)
class Flight:
    """A single bookable flight on a given date."""

    flight_no: str
    airline: str
    origin: str
    destination: str
    date: _dt.date
    depart: str
    arrive: str
    duration_min: int
    price_usd: int
    seats_left: int

    @property
    def duration_str(self) -> str:
        hours, minutes = divmod(self.duration_min, 60)
        return f"{hours}h {minutes:02d}m"


def resolve_city(value: str) -> Optional[str]:
    """Resolve a user-supplied city name or code to an IATA-style code."""

    if not value:
        return None
    token = value.strip().lower()
    if token in CITIES:
        return CITIES[token]
    upper = value.strip().upper()
    if upper in CITIES.values():
        return upper
    return None


def parse_date(value: str) -> Optional[_dt.date]:
    """Parse a ``YYYY-MM-DD`` date string, returning ``None`` when invalid."""

    try:
        return _dt.datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _build_catalogue(days_ahead: int = 30) -> List[Flight]:
    """Generate a deterministic catalogue of flights for the next ``days_ahead`` days."""

    catalogue: List[Flight] = []
    base = _dt.date(2026, 9, 1)
    for origin, dest, airline, price_out, price_ret in _ROUTES:
        # Duration is derived deterministically from the route codes so the data
        # is stable across runs without hard-coding every leg.
        seed = (sum(ord(c) for c in origin + dest)) % 7
        duration = 90 + seed * 55
        for direction, (a, b, price) in enumerate(
            ((origin, dest, price_out), (dest, origin, price_ret))
        ):
            for day in range(days_ahead):
                date = base + _dt.timedelta(days=day)
                depart_hour = 6 + ((day + direction) % 3) * 5
                arrive_total = depart_hour * 60 + duration
                catalogue.append(
                    Flight(
                        flight_no=f"{airline[:2].upper()}{100 + direction * 400 + day}",
                        airline=airline,
                        origin=a,
                        destination=b,
                        date=date,
                        depart=f"{depart_hour:02d}:00",
                        arrive=f"{(arrive_total // 60) % 24:02d}:{arrive_total % 60:02d}",
                        duration_min=duration,
                        price_usd=price + (day % 5) * 7,
                        seats_left=3 + (day * 2 + direction) % 8,
                    )
                )
    return catalogue


class FlightService:
    """Searches the in-memory flight catalogue and prices offers dynamically."""

    def __init__(self, catalogue: Optional[List[Flight]] = None) -> None:
        self._catalogue = catalogue if catalogue is not None else _build_catalogue()

    @staticmethod
    def _tick(tick: Optional[int]) -> int:
        return pricing.current_tick() if tick is None else tick

    def _legs(
        self, origin: str, destination: str, date: Optional[_dt.date] = None
    ) -> List[Flight]:
        return [
            f
            for f in self._catalogue
            if f.origin == origin
            and f.destination == destination
            and (date is None or f.date == date)
        ]

    def search(
        self,
        origin: str,
        destination: str,
        date: Optional[_dt.date] = None,
        passengers: int = 1,
        tick: Optional[int] = None,
        limit: int = 5,
    ) -> List[Quote]:
        """Return up to ``limit`` priced offers, cheapest first, for the route.

        ``origin`` and ``destination`` must already be resolved IATA codes.
        When ``date`` is ``None`` every date on the route is considered.
        """

        tick = self._tick(tick)
        quotes = [pricing.quote(f, tick, passengers) for f in self._legs(origin, destination, date)]
        quotes.sort(key=lambda q: (q.price_total, q.date, q.depart))
        return quotes[:limit]

    def cheapest(
        self,
        origin: str,
        destination: str,
        date: _dt.date,
        passengers: int = 1,
        tick: Optional[int] = None,
    ) -> Optional[Quote]:
        """Return the single cheapest offer on a route/date, or ``None``."""

        offers = self.search(origin, destination, date=date, passengers=passengers, tick=tick, limit=1)
        return offers[0] if offers else None

    def search_range(
        self,
        origin: str,
        destination: str,
        start: _dt.date,
        end: _dt.date,
        passengers: int = 1,
        tick: Optional[int] = None,
    ) -> List[Quote]:
        """Return the cheapest offer for each date in ``[start, end]`` (sorted by date)."""

        tick = self._tick(tick)
        if end < start:
            start, end = end, start
        results: List[Quote] = []
        day = start
        while day <= end:
            best = self.cheapest(origin, destination, day, passengers=passengers, tick=tick)
            if best is not None:
                results.append(best)
            day += _dt.timedelta(days=1)
        return results

    def round_trip(
        self,
        origin: str,
        destination: str,
        out_date: _dt.date,
        back_date: _dt.date,
        passengers: int = 1,
        tick: Optional[int] = None,
    ) -> Optional[Tuple[Quote, Quote, int]]:
        """Return ``(outbound, inbound, total_price)`` for the cheapest round trip."""

        tick = self._tick(tick)
        out = self.cheapest(origin, destination, out_date, passengers=passengers, tick=tick)
        back = self.cheapest(destination, origin, back_date, passengers=passengers, tick=tick)
        if out is None or back is None:
            return None
        return out, back, out.price_total + back.price_total

    def cheapest_deals(
        self, passengers: int = 1, tick: Optional[int] = None, limit: int = 5
    ) -> List[Quote]:
        """Return the offers with the biggest current discount vs their list price."""

        tick = self._tick(tick)
        best_per_route: Dict[str, Quote] = {}
        for flight in self._catalogue:
            q = pricing.quote(flight, tick, passengers)
            key = pricing.route_key(q.origin, q.destination)
            current = best_per_route.get(key)
            if current is None or q.price_total < current.price_total:
                best_per_route[key] = q
        deals = [q for q in best_per_route.values() if q.discount_pct > 0]
        deals.sort(key=lambda q: (-q.discount_pct, q.price_total))
        return deals[:limit]

    def routes_from(self, origin: str) -> List[str]:
        """Return the sorted list of destinations reachable non-stop from ``origin``."""

        return sorted({f.destination for f in self._catalogue if f.origin == origin})
