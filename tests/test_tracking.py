import datetime as dt

from avia_bot.flights import FlightService
from avia_bot.tracking import PriceTracker

DATE = dt.date(2026, 9, 5)


def _find_drop_ticks(service):
    prices = {t: service.cheapest("LON", "PAR", DATE, tick=t).price_total for t in range(0, 60)}
    for t in range(0, 59):
        if prices[t + 1] < prices[t]:
            return t, t + 1
    raise AssertionError("no price drop found in tick range")


def test_add_seeds_history():
    service = FlightService()
    tracker = PriceTracker(service)
    track, quote = tracker.add(1, "LON", "PAR", DATE, tick=5)
    assert quote is not None
    assert track.history[-1] == (5, quote.price_total)
    assert tracker.list_for(1) == [track]


def test_poll_detects_drop_and_records_history():
    service = FlightService()
    tracker = PriceTracker(service)
    high, low = _find_drop_ticks(service)

    tracker.add(1, "LON", "PAR", DATE, tick=high)
    drops = tracker.poll(low)

    assert len(drops) == 1
    event = drops[0]
    assert event.new_price < event.previous_price
    assert event.drop_pct > 0
    track = tracker.list_for(1)[0]
    assert [t for t, _ in track.history] == [high, low]


def test_poll_same_tick_is_noop():
    service = FlightService()
    tracker = PriceTracker(service)
    tracker.add(1, "LON", "PAR", DATE, tick=5)
    assert tracker.poll(5) == []  # no duplicate point / drop for same tick


def test_remove_track():
    service = FlightService()
    tracker = PriceTracker(service)
    track, _ = tracker.add(1, "LON", "PAR", DATE, tick=5)
    assert tracker.remove(1, track.key) is True
    assert tracker.list_for(1) == []
    assert tracker.remove(1, track.key) is False
