import datetime as dt

from avia_bot import pricing
from avia_bot.flights import FlightService


def test_market_factor_is_deterministic_and_bounded():
    for tick in range(0, 50):
        f = pricing.market_factor("LON-PAR", tick)
        assert 0.6 < f < 1.4
        assert pricing.market_factor("LON-PAR", tick) == f  # deterministic


def test_market_factor_varies_over_time():
    values = {pricing.market_factor("LON-NYC", t) for t in range(0, 20)}
    assert len(values) > 5  # prices actually move


def test_current_tick_advances_with_time():
    assert pricing.current_tick(interval_seconds=100, now=1000) == 10
    assert pricing.current_tick(interval_seconds=100, now=1150) == 11


def test_quote_discount_matches_baseline():
    service = FlightService()
    q = service.cheapest("LON", "PAR", dt.date(2026, 9, 5), tick=7)
    expected = round((q.baseline_total - q.price_total) / q.baseline_total * 100)
    assert q.discount_pct == expected


def test_seasonal_weekend_is_pricier():
    saturday = dt.date(2026, 9, 5)
    monday = dt.date(2026, 9, 7)
    assert pricing.seasonal_factor(saturday) > pricing.seasonal_factor(monday)
