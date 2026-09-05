"""Flight itinerary engine.

Deterministically generates realistic-looking itineraries (direct and one-stop,
with airlines, times, baggage, seats and TJS fares) between airports, so the
whole bot runs offline. The data layer is isolated here: a real provider can
replace :meth:`FlightService._itineraries` behind the same interface.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import airlines, geo, pricing
from .airlines import Airline
from .pricing import Passengers

AIRLINES = list(airlines.AIRLINES)
HUBS = ["IST", "DXB", "DOH", "FRA", "AMS", "CDG", "LHR", "JFK",
        "SIN", "LED", "TAS", "ALA", "SVO", "AUH", "DEL", "WAW"]

POPULAR_ROUTES = [
    ("MOW", "LBD"), ("MOW", "DYU"), ("MOW", "TAS"), ("MOW", "IST"),
    ("LED", "TAS"), ("MOW", "DXB"), ("TAS", "IST"), ("MOW", "AER"),
    ("MOW", "AYT"), ("MOW", "EVN"), ("MOW", "TBS"), ("MOW", "MSQ"),
]

DISCOVER_DESTS = ["AYT", "DXB", "IST", "AER", "TAS", "LED", "EVN", "TBS",
                  "ALA", "MSQ", "BKK", "HKT", "SSH", "HRG"]


def fmt_duration(minutes: int) -> str:
    days, rem = divmod(minutes, 1440)
    hours, mins = divmod(rem, 60)
    out = []
    if days:
        out.append(f"{days}д")
    if hours:
        out.append(f"{hours}ч")
    out.append(f"{mins}м")
    return " ".join(out)


@dataclass(frozen=True)
class Leg:
    airline: str
    flight_no: str
    from_code: str
    to_code: str
    dep: _dt.datetime
    arr: _dt.datetime
    airline_iata: str = ""


@dataclass(frozen=True)
class Itinerary:
    legs: Tuple[Leg, ...]
    baggage: bool
    seats_left: int
    base_price: int  # in TJS, before market/season/cabin/pax

    @property
    def origin(self) -> str:
        return self.legs[0].from_code

    @property
    def destination(self) -> str:
        return self.legs[-1].to_code

    @property
    def dep(self) -> _dt.datetime:
        return self.legs[0].dep

    @property
    def arr(self) -> _dt.datetime:
        return self.legs[-1].arr

    @property
    def stops(self) -> int:
        return len(self.legs) - 1

    @property
    def is_direct(self) -> bool:
        return self.stops == 0

    @property
    def airline(self) -> str:
        return self.legs[0].airline

    @property
    def airline_iata(self) -> str:
        return self.legs[0].airline_iata or airlines.iata_of(self.legs[0].airline)

    @property
    def flight_no(self) -> str:
        return self.legs[0].flight_no

    @property
    def duration_min(self) -> int:
        return int((self.arr - self.dep).total_seconds() // 60)

    @property
    def duration_str(self) -> str:
        return fmt_duration(self.duration_min)

    def stop_infos(self) -> List[Tuple[str, int]]:
        """Return [(city_name, layover_minutes)] for each connection."""

        infos: List[Tuple[str, int]] = []
        for i in range(len(self.legs) - 1):
            city = geo.city_of(self.legs[i].to_code) or self.legs[i].to_code
            layover = int((self.legs[i + 1].dep - self.legs[i].arr).total_seconds() // 60)
            infos.append((city, layover))
        return infos


@dataclass(frozen=True)
class Priced:
    itinerary: Itinerary
    pax: Passengers
    tick: int
    price_total: int
    per_adult: int
    baseline_total: int
    is_cheapest: bool = False
    is_fastest: bool = False

    @property
    def discount_pct(self) -> int:
        if self.baseline_total <= 0:
            return 0
        return round((self.baseline_total - self.price_total) / self.baseline_total * 100)


@dataclass
class Filters:
    direct_only: bool = False
    connecting_only: bool = False
    with_baggage: bool = False
    without_baggage: bool = False

    def matches(self, it: Itinerary) -> bool:
        if self.direct_only and not it.is_direct:
            return False
        if self.connecting_only and it.is_direct:
            return False
        if self.with_baggage and not it.baggage:
            return False
        if self.without_baggage and it.baggage:
            return False
        return True

    @property
    def active(self) -> bool:
        return self.direct_only or self.connecting_only or self.with_baggage or self.without_baggage


def _seed(*parts) -> int:
    # Stable across processes (unlike str hash() with PYTHONHASHSEED).
    digest = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:8], 16)


def _leg_minutes(a: str, b: str) -> int:
    base = (sum(ord(c) for c in a + b) % 6) * 45 + 90
    return base


class FlightService:
    def __init__(self) -> None:
        self._cache: Dict[tuple, List[Itinerary]] = {}

    # -- generation ---------------------------------------------------------

    def _itineraries(self, origin: str, destination: str, date: _dt.date) -> List[Itinerary]:
        """Deterministic set of itineraries for an airport pair on a date."""

        cache_key = (origin, destination, date)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if origin == destination:
            self._cache[cache_key] = []
            return []

        rnd = random.Random(_seed(origin, destination, date.toordinal()))
        results: List[Itinerary] = []
        direct_minutes = _leg_minutes(origin, destination)

        # 2 direct options.
        for i in range(2):
            dep_hour = (6 + i * 7 + rnd.randint(0, 3)) % 24
            dep = _dt.datetime.combine(date, _dt.time(dep_hour, rnd.choice([0, 5, 25, 30, 45])))
            arr = dep + _dt.timedelta(minutes=direct_minutes)
            carrier: Airline = rnd.choice(AIRLINES)
            results.append(
                Itinerary(
                    legs=(Leg(
                        carrier.display(),
                        f"{carrier.iata}{rnd.randint(100, 999)}",
                        origin, destination, dep, arr,
                        airline_iata=carrier.iata,
                    ),),
                    baggage=rnd.random() > 0.35,
                    seats_left=rnd.randint(2, 9),
                    base_price=rnd.randint(2600, 3600),
                )
            )

        # 1-2 one-stop options via a hub (cheaper but longer).
        hubs = [h for h in HUBS if h not in (origin, destination)]
        rnd.shuffle(hubs)
        for hub in hubs[: rnd.randint(1, 2)]:
            dep_hour = (rnd.randint(0, 23))
            dep = _dt.datetime.combine(date, _dt.time(dep_hour, rnd.choice([0, 5, 25, 30, 45])))
            m1 = _leg_minutes(origin, hub)
            arr1 = dep + _dt.timedelta(minutes=m1)
            layover = rnd.choice([90, 150, 240, 30 * 60, 13 * 60])  # includes long overnight
            dep2 = arr1 + _dt.timedelta(minutes=layover)
            m2 = _leg_minutes(hub, destination)
            arr2 = dep2 + _dt.timedelta(minutes=m2)
            carrier: Airline = rnd.choice(AIRLINES)
            results.append(
                Itinerary(
                    legs=(
                        Leg(carrier.display(), f"{carrier.iata}{rnd.randint(100, 999)}",
                            origin, hub, dep, arr1, airline_iata=carrier.iata),
                        Leg(carrier.display(), f"{carrier.iata}{rnd.randint(100, 999)}",
                            hub, destination, dep2, arr2, airline_iata=carrier.iata),
                    ),
                    baggage=rnd.random() > 0.5,
                    seats_left=rnd.randint(2, 9),
                    base_price=rnd.randint(2000, 2900),
                )
            )

        self._cache[cache_key] = results
        return results

    # -- search -------------------------------------------------------------

    @staticmethod
    def _tick(tick: Optional[int]) -> int:
        return pricing.current_tick() if tick is None else tick

    def _price(self, it: Itinerary, pax: Passengers, tick: int) -> Priced:
        key = pricing.route_key(it.origin, it.destination)
        date = it.dep.date()
        per = pricing.per_adult_price(it.base_price, key, date, tick, pax.cabin)
        total = pricing.total_price(it.base_price, key, date, tick, pax)
        # Baseline = list price with a neutral market (factor 1.0), for discounts.
        base_per = int(round(it.base_price * pricing.seasonal_factor(date) * pricing.cabin_factor(pax.cabin)))
        baseline = int(round(
            base_per * pax.adults
            + base_per * pricing.CHILD_FACTOR * pax.children
            + base_per * pricing.INFANT_FACTOR * pax.infants
        ))
        return Priced(it, pax, tick, total, per, baseline)

    def search(
        self,
        origin: str,
        destination: str,
        date: _dt.date,
        pax: Optional[Passengers] = None,
        tick: Optional[int] = None,
        filters: Optional[Filters] = None,
        limit: Optional[int] = None,
    ) -> List[Priced]:
        pax = pax or Passengers()
        tick = self._tick(tick)
        origins = geo.resolve_airports(origin)
        dests = geo.resolve_airports(destination)
        itineraries: List[Itinerary] = []
        for o in origins:
            for d in dests:
                itineraries.extend(self._itineraries(o, d, date))
        if filters is not None:
            itineraries = [it for it in itineraries if filters.matches(it)]
        priced = [self._price(it, pax, tick) for it in itineraries]
        priced.sort(key=lambda p: (p.price_total, p.itinerary.duration_min))
        priced = self._label(priced)
        return priced[:limit] if limit else priced

    @staticmethod
    def _label(priced: List[Priced]) -> List[Priced]:
        if not priced:
            return priced
        cheapest = min(range(len(priced)), key=lambda i: priced[i].price_total)
        fastest = min(range(len(priced)), key=lambda i: priced[i].itinerary.duration_min)
        out = []
        for i, p in enumerate(priced):
            out.append(
                Priced(p.itinerary, p.pax, p.tick, p.price_total, p.per_adult, p.baseline_total,
                       is_cheapest=(i == cheapest), is_fastest=(i == fastest))
            )
        return out

    def cheapest_price(
        self, origin: str, destination: str, date: _dt.date,
        pax: Optional[Passengers] = None, tick: Optional[int] = None,
        filters: Optional[Filters] = None,
    ) -> Optional[int]:
        offers = self.search(origin, destination, date, pax=pax, tick=tick, filters=filters, limit=1)
        return offers[0].price_total if offers else None

    def search_range(
        self, origin: str, destination: str, start: _dt.date, end: _dt.date,
        pax: Optional[Passengers] = None, tick: Optional[int] = None,
    ) -> List[Tuple[_dt.date, int]]:
        tick = self._tick(tick)
        if end < start:
            start, end = end, start
        out: List[Tuple[_dt.date, int]] = []
        day = start
        while day <= end:
            price = self.cheapest_price(origin, destination, day, pax=pax, tick=tick)
            if price is not None:
                out.append((day, price))
            day += _dt.timedelta(days=1)
        return out

    def flexible_dates(
        self, origin: str, destination: str, date: _dt.date, span: int = 3,
        pax: Optional[Passengers] = None, tick: Optional[int] = None,
    ) -> List[Tuple[_dt.date, int]]:
        return self.search_range(origin, destination, date - _dt.timedelta(days=span),
                                 date + _dt.timedelta(days=span), pax=pax, tick=tick)

    def cheapest_deals(
        self, date: Optional[_dt.date] = None, pax: Optional[Passengers] = None,
        tick: Optional[int] = None, limit: int = 6,
    ) -> List[Priced]:
        tick = self._tick(tick)
        date = date or _dt.date(2026, 9, 1)
        best: List[Priced] = []
        for o, d in POPULAR_ROUTES:
            offers = self.search(o, d, date, pax=pax, tick=tick, limit=1)
            if offers and offers[0].discount_pct > 0:
                best.append(offers[0])
        best.sort(key=lambda p: (-p.discount_pct, p.price_total))
        return best[:limit]
