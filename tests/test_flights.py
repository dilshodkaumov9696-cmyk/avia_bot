import datetime as dt

from avia_bot.flights import FlightService, parse_date, resolve_city


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
    results = service.search("LON", "PAR", limit=3)
    assert results, "expected flights on a known route"
    assert len(results) <= 3
    prices = [f.price_usd for f in results]
    assert prices == sorted(prices)
    for flight in results:
        assert flight.origin == "LON"
        assert flight.destination == "PAR"


def test_search_filters_by_date():
    service = FlightService()
    date = dt.date(2026, 9, 3)
    results = service.search("LON", "NYC", date=date)
    assert results
    assert all(f.date == date for f in results)


def test_search_unknown_route_is_empty():
    service = FlightService()
    assert service.search("LON", "SIN") == []


def test_routes_from_returns_sorted_destinations():
    service = FlightService()
    routes = service.routes_from("LON")
    assert routes == sorted(routes)
    assert "PAR" in routes and "NYC" in routes


def test_flight_duration_str():
    service = FlightService()
    flight = service.search("LON", "PAR", limit=1)[0]
    assert "h" in flight.duration_str and "m" in flight.duration_str
