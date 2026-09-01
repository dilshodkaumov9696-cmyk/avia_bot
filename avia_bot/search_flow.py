"""Pure helpers for the guided-search conversation.

Passenger/cabin adjustments and result pagination live here (no Telegram
dependency) so the fiddly clamping logic is unit-tested.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple, TypeVar

from .pricing import CABIN_ORDER, Passengers

T = TypeVar("T")

MAX_PAX = 9


def adjust_pax(pax: Passengers, field: str, delta: int) -> Passengers:
    """Increment/decrement a passenger count with sensible clamps."""

    adults, children, infants = pax.adults, pax.children, pax.infants
    if field == "adults":
        adults += delta
    elif field == "children":
        children += delta
    elif field == "infants":
        infants += delta

    adults = max(1, adults)
    children = max(0, children)
    infants = max(0, infants)
    # Cap total; infants may not exceed adults (lap infants).
    if adults + children + infants > MAX_PAX:
        return pax
    infants = min(infants, adults)
    return Passengers(adults, children, infants, pax.cabin)


def cycle_cabin(pax: Passengers, delta: int) -> Passengers:
    idx = (CABIN_ORDER.index(pax.cabin) + delta) % len(CABIN_ORDER)
    return Passengers(pax.adults, pax.children, pax.infants, CABIN_ORDER[idx])


def paginate(items: Sequence[T], page: int, per_page: int = 1) -> Tuple[List[T], int, int]:
    """Return (page_items, clamped_page, total_pages) with 0-based page index."""

    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    return list(items[start:start + per_page]), page, total_pages
