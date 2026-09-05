import datetime as dt

from avia_bot import pricing
from avia_bot.pricing import Passengers


def test_market_factor_deterministic_bounded_varies():
    vals = [pricing.market_factor("MOW-LBD", t) for t in range(0, 30)]
    assert all(0.6 < v < 1.4 for v in vals)
    assert pricing.market_factor("MOW-LBD", 5) == pricing.market_factor("MOW-LBD", 5)
    assert len(set(vals)) > 5


def test_current_tick():
    assert pricing.current_tick(interval_seconds=100, now=1000) == 10
    assert pricing.current_tick(interval_seconds=100, now=1199) == 11


def test_passengers_summary_and_total():
    pax = Passengers(2, 1, 1, "business")
    assert pax.total == 4
    assert "2 взр." in pax.summary and "Бизнес" in pax.summary


def test_cabin_factor_business_pricier():
    assert pricing.cabin_factor("business") > pricing.cabin_factor("economy")


def test_total_price_child_infant_discounts():
    key, date, tick = "MOW-LBD", dt.date(2026, 9, 17), 3
    per = pricing.per_adult_price(3000, key, date, tick, "economy")
    total = pricing.total_price(3000, key, date, tick, Passengers(1, 1, 1, "economy"))
    expected = int(round(per + per * 0.75 + per * 0.10))
    assert total == expected


def test_format_money_groups_thousands():
    assert pricing.format_money(3080) == "3\u00a0080 TJS"


def test_price_trend_values():
    assert pricing.price_trend("MOW-LBD", 3) in {"падает", "растёт", "стабильна"}
