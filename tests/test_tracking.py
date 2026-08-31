import datetime as dt

from avia_bot.flights import FlightService
from avia_bot.pricing import Passengers
from avia_bot.tracking import PriceTracker

DATE = dt.date(2026, 9, 17)


def _drop_ticks(svc):
    prices = {t: svc.cheapest_price("MOW", "LBD", DATE, tick=t) for t in range(0, 60)}
    for t in range(0, 59):
        if prices[t + 1] < prices[t]:
            return t, t + 1
    raise AssertionError("no drop found")


def test_add_seeds_history():
    svc = FlightService()
    tr = PriceTracker(svc)
    track, price = tr.add(1, "MOW", "LBD", DATE, pax=Passengers(), tick=5)
    assert price is not None
    assert track.history[-1] == (5, price)


def test_poll_detects_drop():
    svc = FlightService()
    tr = PriceTracker(svc)
    high, low = _drop_ticks(svc)
    tr.add(1, "MOW", "LBD", DATE, tick=high)
    drops = tr.poll(low)
    assert len(drops) == 1
    assert drops[0].new_price < drops[0].previous_price
    assert drops[0].drop_pct > 0


def test_remove():
    svc = FlightService()
    tr = PriceTracker(svc)
    track, _ = tr.add(1, "MOW", "LBD", DATE, tick=5)
    assert tr.remove(1, track.key) is True
    assert tr.list_for(1) == []
