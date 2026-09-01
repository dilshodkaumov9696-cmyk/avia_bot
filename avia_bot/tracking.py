"""In-memory price-tracking store.

Each :class:`Track` remembers a route/date/passenger watch for a chat and the
history of cheapest prices seen. :meth:`PriceTracker.poll` re-prices every active
track at a new market tick and reports drops (which drive "price fell!" alerts).
In-memory by design; swapping in a DB only touches this module.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .flights import FlightService
from .pricing import Passengers


@dataclass
class Track:
    chat_id: int
    origin: str
    destination: str
    date: _dt.date
    pax: Passengers
    lang: str = "ru"
    history: List[Tuple[int, int]] = field(default_factory=list)  # (tick, price)

    @property
    def key(self) -> str:
        p = self.pax
        return f"{self.origin}-{self.destination}:{self.date.isoformat()}:{p.adults}-{p.children}-{p.infants}-{p.cabin}"

    @property
    def last_price(self) -> Optional[int]:
        return self.history[-1][1] if self.history else None

    @property
    def best_price(self) -> Optional[int]:
        return min((p for _, p in self.history), default=None)


@dataclass
class DropEvent:
    track: Track
    previous_price: int
    new_price: int

    @property
    def delta(self) -> int:
        return self.previous_price - self.new_price

    @property
    def drop_pct(self) -> int:
        if self.previous_price <= 0:
            return 0
        return round(self.delta / self.previous_price * 100)


class PriceTracker:
    def __init__(self, service: Optional[FlightService] = None) -> None:
        self._service = service or FlightService()
        self._tracks: Dict[int, Dict[str, Track]] = {}

    def add(self, chat_id: int, origin: str, destination: str, date: _dt.date,
            pax: Optional[Passengers] = None, tick: Optional[int] = None,
            lang: str = "ru") -> Tuple[Track, Optional[int]]:
        track = Track(chat_id, origin, destination, date, pax or Passengers(), lang)
        chat = self._tracks.setdefault(chat_id, {})
        track = chat.setdefault(track.key, track)
        track.lang = lang

        price = self._service.cheapest_price(origin, destination, date, pax=track.pax, tick=tick)
        if price is not None:
            eff_tick = tick if tick is not None else (track.history[-1][0] + 1 if track.history else 0)
            if not track.history or track.history[-1][0] != eff_tick:
                track.history.append((eff_tick, price))
        return track, price

    def remove(self, chat_id: int, key: str) -> bool:
        chat = self._tracks.get(chat_id)
        if chat and key in chat:
            del chat[key]
            return True
        return False

    def list_for(self, chat_id: int) -> List[Track]:
        return list(self._tracks.get(chat_id, {}).values())

    def all_tracks(self) -> List[Track]:
        return [t for chat in self._tracks.values() for t in chat.values()]

    def poll(self, tick: int) -> List[DropEvent]:
        drops: List[DropEvent] = []
        for track in self.all_tracks():
            price = self._service.cheapest_price(track.origin, track.destination, track.date, pax=track.pax, tick=tick)
            if price is None:
                continue
            if track.history and track.history[-1][0] == tick:
                continue
            previous = track.last_price
            track.history.append((tick, price))
            if previous is not None and price < previous:
                drops.append(DropEvent(track, previous, price))
        return drops
