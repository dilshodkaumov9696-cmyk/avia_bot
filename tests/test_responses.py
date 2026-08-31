import datetime as dt

from avia_bot.flights import FlightService
from avia_bot.responses import (
    cities_text,
    hot_response,
    parse_args,
    range_response,
    roundtrip_response,
    search_response,
)

TICK = 1000


def make_service():
    return FlightService()


def test_parse_args_splits_cities_dates_passengers():
    parsed = parse_args(["LON", "NYC", "2026-09-05", "3"])
    assert parsed.cities == ["LON", "NYC"]
    assert parsed.dates == [dt.date(2026, 9, 5)]
    assert parsed.passengers == 3


def test_search_direct_route_shows_prices():
    reply = search_response(make_service(), ["London", "Paris", "2026-09-05"], tick=TICK)
    assert "LON \u2192 PAR" in reply
    assert "$" in reply


def test_search_multiword_city_and_passengers():
    reply = search_response(make_service(), ["New", "York", "Tokyo", "2026-09-06", "2"], tick=TICK)
    assert "NYC \u2192 TYO" in reply
    assert "\u043f\u0430\u0441\u0441" in reply  # mentions passengers


def test_search_unknown_city():
    reply = search_response(make_service(), ["Mars", "Venus"], tick=TICK)
    assert "\u0440\u0430\u0441\u043f\u043e\u0437\u043d" in reply.lower()


def test_search_no_direct_route_suggests_alternatives():
    reply = search_response(make_service(), ["London", "Singapore"], tick=TICK)
    assert "\u043f\u0440\u044f\u043c" in reply.lower()


def test_range_response_marks_cheapest_and_returns_offers():
    reply, offers = range_response(
        make_service(), ["LON", "NYC", "2026-09-01", "2026-09-07"], tick=TICK
    )
    assert offers
    assert "\u0441\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439" in reply.lower()
    # cheapest mentioned price equals min of offers
    cheapest = min(o.price_total for o in offers)
    assert f"${cheapest}" in reply


def test_roundtrip_response_shows_total():
    reply = roundtrip_response(
        make_service(), ["LON", "NYC", "2026-09-05", "2026-09-12", "2"], tick=TICK
    )
    assert "\u0422\u0443\u0434\u0430" in reply and "\u041e\u0431\u0440\u0430\u0442\u043d\u043e" in reply
    assert "\u0418\u0442\u043e\u0433\u043e" in reply


def test_hot_response_lists_deals():
    reply = hot_response(make_service(), [], tick=TICK)
    assert "\u0413\u043e\u0440\u044f\u0449\u0438\u0435" in reply
    assert "%" in reply


def test_cities_text_contains_known_city():
    text = cities_text()
    assert "Tashkent" in text and "TAS" in text
