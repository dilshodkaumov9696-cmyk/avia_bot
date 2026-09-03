import datetime as dt

from avia_bot import tickets
from avia_bot.flights import FlightService

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
DATE = dt.date(2026, 9, 17)


def test_ticket_card_embeds_airline_logo():
    svc = FlightService()
    offer = svc.search("MOW", "LBD", DATE, tick=1000, limit=1)[0]
    png = tickets.render_ticket("ru", offer)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 8000
    assert offer.itinerary.airline_iata
    from avia_bot import airlines
    assert airlines.logo_path(offer.itinerary.airline_iata) is not None


def test_ticket_card_roundtrip():
    svc = FlightService()
    out = svc.search("MOW", "LBD", DATE, tick=1000, limit=1)[0]
    back = svc.search("LBD", "MOW", DATE + dt.timedelta(days=7), tick=1000, limit=1)[0]
    png = tickets.render_ticket("en", out, back=back)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 8000
