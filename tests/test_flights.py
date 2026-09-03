import datetime as dt

from avia_bot.flights import Filters, FlightService, fmt_duration
from avia_bot.pricing import Passengers

DATE = dt.date(2026, 9, 17)
TICK = 1000


def test_search_sorted_and_labelled():
    svc = FlightService()
    res = svc.search("MOW", "LBD", DATE, tick=TICK)
    assert res
    prices = [p.price_total for p in res]
    assert prices == sorted(prices)
    assert sum(p.is_cheapest for p in res) == 1
    assert sum(p.is_fastest for p in res) == 1
    assert res[0].is_cheapest  # cheapest sorts first


def test_results_are_deterministic():
    a = FlightService().search("MOW", "LBD", DATE, tick=TICK)
    b = FlightService().search("MOW", "LBD", DATE, tick=TICK)
    assert [p.price_total for p in a] == [p.price_total for p in b]


def test_direct_filter():
    svc = FlightService()
    direct = svc.search("MOW", "LBD", DATE, tick=TICK, filters=Filters(direct_only=True))
    assert direct
    assert all(p.itinerary.is_direct for p in direct)


def test_baggage_filter():
    svc = FlightService()
    bag = svc.search("MOW", "LBD", DATE, tick=TICK, filters=Filters(with_baggage=True))
    assert all(p.itinerary.baggage for p in bag)
    nobag = svc.search("MOW", "LBD", DATE, tick=TICK, filters=Filters(without_baggage=True))
    assert nobag
    assert all(not p.itinerary.baggage for p in nobag)


def test_connecting_filter():
    svc = FlightService()
    hops = svc.search("MOW", "LBD", DATE, tick=TICK, filters=Filters(connecting_only=True))
    assert hops
    assert all(not p.itinerary.is_direct for p in hops)


def test_has_connections_with_layover_info():
    svc = FlightService()
    res = svc.search("MOW", "LBD", DATE, tick=TICK)
    connecting = [p for p in res if not p.itinerary.is_direct]
    assert connecting
    infos = connecting[0].itinerary.stop_infos()
    assert infos and infos[0][1] > 0  # layover minutes


def test_passenger_totals_scale():
    svc = FlightService()
    one = svc.search("MOW", "LBD", DATE, pax=Passengers(1), tick=TICK, limit=1)[0]
    three = svc.search("MOW", "LBD", DATE, pax=Passengers(3), tick=TICK, limit=1)[0]
    assert three.price_total > one.price_total


def test_cheapest_price_and_range():
    svc = FlightService()
    assert isinstance(svc.cheapest_price("MOW", "LBD", DATE, tick=TICK), int)
    points = svc.search_range("MOW", "LBD", DATE, DATE + dt.timedelta(days=4), tick=TICK)
    assert len(points) == 5
    assert [d for d, _ in points] == sorted(d for d, _ in points)


def test_cheapest_deals_positive_discount():
    deals = FlightService().cheapest_deals(tick=TICK)
    assert deals
    assert all(p.discount_pct > 0 for p in deals)


def test_fmt_duration():
    assert fmt_duration(65) == "1ч 5м"
    assert fmt_duration(1440 + 90) == "1д 1ч 30м"
