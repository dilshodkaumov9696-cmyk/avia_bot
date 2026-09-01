import datetime as dt

from avia_bot import responses
from avia_bot.flights import Filters, FlightService
from avia_bot.pricing import Passengers

DATE = dt.date(2026, 9, 17)
TICK = 1000


def test_format_offer_direct_and_stops_localized():
    svc = FlightService()
    res = svc.search("MOW", "LBD", DATE, tick=TICK)
    direct = next(p for p in res if p.itinerary.is_direct)
    conn = next(p for p in res if not p.itinerary.is_direct)

    # Tajik -> currency TJS
    dtext = responses.format_offer("tg", direct)
    assert "TJS" in dtext and "🛫" in dtext and "Мустақим" in dtext  # "Direct" in Tajik

    ctext = responses.format_offer("en", conn)
    assert "USD" in ctext and "stop" in ctext.lower()


def test_offer_buy_label_localized():
    svc = FlightService()
    offer = svc.search("MOW", "LBD", DATE, tick=TICK, limit=1)[0]
    assert "Купить билет" in responses.offer_buy_label("ru", offer)
    assert "Buy ticket" in responses.offer_buy_label("en", offer)


def test_pax_summary_localized():
    pax = Passengers(2, 1, 0, "business")
    assert "взр." in responses.pax_summary("ru", pax) and "Бизнес" in responses.pax_summary("ru", pax)
    assert "ad." in responses.pax_summary("en", pax) and "Business" in responses.pax_summary("en", pax)


def test_results_header_shows_filters():
    header = responses.results_header("ru", "Москва", "Худжанд", DATE, Passengers(2),
                                      0, 5, Filters(direct_only=True))
    assert "Москва → Худжанд" in header and "1 из 5" in header


def test_range_text_marks_cheapest():
    svc = FlightService()
    points = svc.search_range("MOW", "LBD", DATE, DATE + dt.timedelta(days=4), tick=TICK)
    text = responses.range_text("tg", "Москва", "Худжанд", points, Passengers())
    assert "арзонтарин" in text  # 'cheapest' in Tajik


def test_drop_text_localized_currency():
    txt = responses.drop_text("en", "Москва", "Худжанд", DATE, 6000, 5000, 17)
    assert "Price dropped" in txt and "USD" in txt and "−17%" in txt


def test_flexible_text_suggests_cheaper_day():
    points = [(DATE, 6000), (DATE + dt.timedelta(days=1), 4000)]
    txt = responses.flexible_text("ru", points, DATE)
    assert txt and "18" in txt
