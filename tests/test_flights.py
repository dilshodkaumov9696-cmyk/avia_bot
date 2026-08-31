import datetime as dt

from avia_bot.flights import FlightService, parse_date, resolve_city

TICK = 1000


def test_resolve_city_accepts_names_and_codes():
    assert resolve_city("London") == "LON"
    assert resolve_city("  new york ") == "NYC"
    assert resolve_city("TAS") == "TAS"
    assert resolve_city("Atlantis") is None
    assert resolve_city("") is None


def test_parse_date():
    assert parse_date("2026-09-05") == dt.date(2026, 9, 5)
    assert parse_date("not-a-date") is None
    assert parse_date("2026-13-40") is None


def test_search_returns_cheapest_first_and_respects_limit():
    service = FlightService()
    results = service.search("LON", "PAR", passengers=1, tick=TICK, limit=3)
    assert results
    assert len(results) <= 3
    prices = [q.price_total for q in results]
    assert prices == sorted(prices)
    for q in results:
        assert q.origin == "LON" and q.destination == "PAR"


def test_search_filters_by_date():
    service = FlightService()
    date = dt.date(2026, 9, 3)
    results = service.search("LON", "NYC", date=date, tick=TICK)
    assert results
    assert all(q.date == date for q in results)


def test_passengers_scale_price():
    service = FlightService()
    one = service.cheapest("LON", "PAR", dt.date(2026, 9, 5), passengers=1, tick=TICK)
    three = service.cheapest("LON", "PAR", dt.date(2026, 9, 5), passengers=3, tick=TICK)
    assert three.price_total == one.price_total * 3
    assert three.passengers == 3


def test_search_unknown_route_is_empty():
    service = FlightService()
    assert service.search("LON", "SIN", tick=TICK) == []


def test_search_range_one_quote_per_date_cheapest():
    service = FlightService()
    start, end = dt.date(2026, 9, 1), dt.date(2026, 9, 5)
    offers = service.search_range("LON", "NYC", start, end, tick=TICK)
    dates = [q.date for q in offers]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    for q in offers:
        same_day = service.search("LON", "NYC", date=q.date, tick=TICK)
        assert q.price_total == min(x.price_total for x in same_day)


def test_round_trip_total_is_sum():
    service = FlightService()
    out_d, back_d = dt.date(2026, 9, 5), dt.date(2026, 9, 12)
    trip = service.round_trip("LON", "NYC", out_d, back_d, tick=TICK)
    assert trip is not None
    out, back, total = trip
    assert out.origin == "LON" and back.origin == "NYC"
    assert total == out.price_total + back.price_total


def test_cheapest_deals_have_positive_discount():
    service = FlightService()
    deals = service.cheapest_deals(tick=TICK, limit=5)
    assert deals
    assert all(q.discount_pct > 0 for q in deals)
    pcts = [q.discount_pct for q in deals]
    assert pcts == sorted(pcts, reverse=True)


def test_routes_from_returns_sorted_destinations():
    service = FlightService()
    routes = service.routes_from("LON")
    assert routes == sorted(routes)
    assert "PAR" in routes and "NYC" in routes
