import datetime as dt

from avia_bot import responses
from avia_bot.flights import Filters, FlightService
from avia_bot.pricing import Passengers

DATE = dt.date(2026, 9, 17)
TICK = 1000


def test_format_offer_direct_and_stops():
    svc = FlightService()
    res = svc.search("MOW", "LBD", DATE, tick=TICK)
    direct = next(p for p in res if p.itinerary.is_direct)
    conn = next(p for p in res if not p.itinerary.is_direct)

    dtext = responses.format_offer(direct)
    assert "TJS" in dtext and "Прямой" in dtext and "🛫" in dtext

    ctext = responses.format_offer(conn)
    assert "пересадк" in ctext


def test_offer_buy_label_has_seats():
    svc = FlightService()
    offer = svc.search("MOW", "LBD", DATE, tick=TICK, limit=1)[0]
    assert "Осталось" in responses.offer_buy_label(offer)


def test_results_header_shows_filters():
    header = responses.results_header("Москва", "Худжанд", DATE, Passengers(2),
                                      0, 5, Filters(direct_only=True))
    assert "Москва → Худжанд" in header
    assert "только прямые" in header
    assert "1 из 5" in header


def test_range_text_marks_cheapest():
    svc = FlightService()
    points = svc.search_range("MOW", "LBD", DATE, DATE + dt.timedelta(days=4), tick=TICK)
    text = responses.range_text("Москва", "Худжанд", points, Passengers())
    assert "самый дешёвый" in text
    cheapest = min(p[1] for p in points)
    from avia_bot.pricing import format_money
    assert format_money(cheapest) in text


def test_dates_prompt_and_searching_bar():
    assert "Вылет" in responses.dates_prompt(DATE, None)
    assert "🟢" in responses.searching_bar(2)


def test_drop_text():
    txt = responses.drop_text("Москва", "Худжанд", DATE, 6000, 5000, 17)
    assert "Цена упала" in txt and "−17%" in txt


def test_flexible_text_suggests_cheaper_day():
    points = [(DATE, 6000), (DATE + dt.timedelta(days=1), 4000)]
    txt = responses.flexible_text(points, DATE)
    assert txt and "18 сентября" in txt
