from avia_bot.demo import handle
from avia_bot.flights import FlightService
from avia_bot.responses import cities_text, search_response


def make_service():
    return FlightService()


def test_search_response_lists_flights():
    reply = search_response(make_service(), ["London", "Dubai"])
    # Route LON->DXB is not direct; ensure we still respond helpfully.
    assert "LON" in reply


def test_search_direct_route_shows_prices():
    reply = search_response(make_service(), ["London", "Paris"])
    assert "LON \u2192 PAR" in reply
    assert "$" in reply


def test_search_with_date():
    reply = search_response(make_service(), ["LON", "NYC", "2026-09-05"])
    assert "2026-09-05" in reply
    assert "$" in reply


def test_search_multiword_city():
    reply = search_response(make_service(), ["New", "York", "Tokyo"])
    assert "NYC \u2192 TYO" in reply


def test_search_unknown_city():
    reply = search_response(make_service(), ["Mars", "Venus"])
    assert "don't recognise" in reply.lower() or "recognise" in reply.lower()


def test_search_same_city_rejected():
    reply = search_response(make_service(), ["London", "London"])
    assert "different" in reply.lower()


def test_search_missing_args():
    reply = search_response(make_service(), ["London"])
    assert "/search" in reply


def test_no_direct_route_suggests_alternatives():
    reply = search_response(make_service(), ["London", "Singapore"])
    assert "non-stop" in reply.lower()


def test_cities_text_contains_known_city():
    text = cities_text()
    assert "Tashkent" in text and "TAS" in text


def test_handle_routes_commands():
    service = make_service()
    assert "Welcome" in handle(service, "/start")
    assert "commands" in handle(service, "/help")
    assert "Tashkent" in handle(service, "/cities")
    assert "PAR" in handle(service, "/search London Paris")
    # Unknown / free text falls back to help.
    assert "commands" in handle(service, "hello there")
