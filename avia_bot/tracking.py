"""In-memory price-tracking store.

Each :class:`Track` remembers a route/date/passenger watch for a Telegram chat
and the history of prices observed for it. :meth:`PriceTracker.poll` re-prices
every active track at a new market tick and reports which ones dropped, which is
exactly what drives the bot's "price fell!" notifications.

The store is intentionally in-memory: it is process-local and resets on restart,
which is fine for a demo. Swapping in a database later only touches this module.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .flights import FlightService
from .pricing import Quote


@dataclass
class Track:
    chat_id: int
    origin: str
    destination: str
    date: _dt.date
    passengers: int
    # History of (tick, total_price) observations, oldest first.
    history: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.origin}-{self.destination}:{self.date.isoformat()}:{self.passengers}"

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
    quote: Quote

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
        # chat_id -> {track.key -> Track}
        self._tracks: Dict[int, Dict[str, Track]] = {}

    def add(
        self,
        chat_id: int,
        origin: str,
        destination: str,
        date: _dt.date,
        passengers: int = 1,
        tick: Optional[int] = None,
    ) -> Tuple[Track, Optional[Quote]]:
        """Register a track and seed it with the current price. Idempotent per key."""

        track = Track(chat_id, origin, destination, date, max(1, passengers))
        chat = self._tracks.setdefault(chat_id, {})
        existing = chat.get(track.key)
        if existing is not None:
            track = existing
        else:
            chat[track.key] = track

        quote = self._service.cheapest(origin, destination, date, passengers=track.passengers, tick=tick)
        if quote is not None and (not track.history or track.history[-1][0] != quote.tick):
            track.history.append((quote.tick, quote.price_total))
        return track, quote

    def remove(self, chat_id: int, key: str) -> bool:
        chat = self._tracks.get(chat_id)
        if chat and key in chat:
            del chat[key]
            return True
        return False

    def list_for(self, chat_id: int) -> List[Track]:
        return list(self._tracks.get(chat_id, {}).values())

    def get(self, chat_id: int, key: str) -> Optional[Track]:
        return self._tracks.get(chat_id, {}).get(key)

    def all_tracks(self) -> List[Track]:
        return [t for chat in self._tracks.values() for t in chat.values()]

    def poll(self, tick: int) -> List[DropEvent]:
        """Re-price every track at ``tick``; return a DropEvent for each price drop."""

        drops: List[DropEvent] = []
        for track in self.all_tracks():
            quote = self._service.cheapest(
                track.origin, track.destination, track.date, passengers=track.passengers, tick=tick
            )
            if quote is None:
                continue
            previous = track.last_price
            # Avoid duplicate points for the same tick (e.g. right after add()).
            if track.history and track.history[-1][0] == tick:
                continue
            track.history.append((tick, quote.price_total))
            if previous is not None and quote.price_total < previous:
                drops.append(DropEvent(track, previous, quote.price_total, quote))
        return drops
